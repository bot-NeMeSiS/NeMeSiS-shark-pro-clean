"""Revenue & Subscription Control engine for NeMeSiS SHARK PRO.

V575 keeps payments safe: it does not charge anyone and it does not require
Stripe. It creates the operational layer needed before real billing: subscription
state, renewals, grace periods, soft blocks, plan revenue and admin actions.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List

PLAN_PRICES = {
    "FREE": 0.0,
    "PRO": 9.99,
    "ELITE": 24.99,
}


def product_plan_prices() -> Dict[str, float]:
    """Use the same visible Stripe catalog for MRR estimates.

    These are product prices, not provider balance evidence. MRR is calculated
    only for active Stripe subscriptions and is explicitly marked estimated.
    """
    prices = dict(PLAN_PRICES)
    try:
        from engines.stripe_payments_engine import plan_catalog
        catalog = plan_catalog()
        for tier in ("PRO", "ELITE"):
            label = str((catalog.get(tier) or {}).get("price_label") or "")
            match = re.search(r"(\d+(?:[.,]\d+)?)", label)
            if match:
                prices[tier] = round(float(match.group(1).replace(",", ".")), 2)
    except (ImportError, TypeError, ValueError):
        pass
    return prices


FEATURES = {
    "FREE": ["calendario", "live básico", "favoritos", "picks limitados"],
    "PRO": ["picks PRO", "SHARK recomendado", "Telegram PRO", "banca", "riesgo/value básico"],
    "ELITE": ["SHARK completo", "auto picks", "combinadas", "top picks", "prioridad Telegram"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.OperationalError:
        pass
    return conn


def rows(conn: sqlite3.Connection, query: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
    try:
        return [dict(r) for r in conn.execute(query, tuple(params)).fetchall()]
    except sqlite3.OperationalError:
        return []


def scalar(conn: sqlite3.Connection, query: str, params: Iterable[Any] = (), default: Any = 0) -> Any:
    try:
        row = conn.execute(query, tuple(params)).fetchone()
        if not row:
            return default
        return list(dict(row).values())[0]
    except sqlite3.OperationalError:
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value if value is not None else default).replace(",", ".")))
    except Exception:
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value if value is not None else default).replace(",", "."))
    except Exception:
        return default


def dumps(payload: Any) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, default=str)[:20000]


def normalize_tier(value: Any) -> str:
    tier = str(value or "FREE").upper().strip()
    return tier if tier in {"FREE", "PRO", "ELITE", "ADMIN"} else "FREE"


def ensure_subscription_schema(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS subscription_accounts(
        user_id TEXT PRIMARY KEY,
        tier TEXT DEFAULT 'FREE',
        status TEXT DEFAULT 'active',
        source TEXT DEFAULT 'admin_manual',
        current_period_start TEXT,
        current_period_end TEXT,
        grace_until TEXT,
        cancel_at_period_end INTEGER DEFAULT 0,
        soft_block INTEGER DEFAULT 0,
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT,
        last_payment_status TEXT,
        notes TEXT,
        payload_json TEXT,
        created_at TEXT,
        updated_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS subscription_events(
        id TEXT PRIMARY KEY,
        user_id TEXT,
        event_type TEXT,
        tier TEXT,
        amount REAL DEFAULT 0,
        status TEXT,
        source TEXT,
        payload_json TEXT,
        created_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS revenue_daily_metrics(
        metric_date TEXT PRIMARY KEY,
        active_paid INTEGER DEFAULT 0,
        trialing INTEGER DEFAULT 0,
        past_due INTEGER DEFAULT 0,
        soft_blocked INTEGER DEFAULT 0,
        estimated_mrr REAL DEFAULT 0,
        churn_risk INTEGER DEFAULT 0,
        payload_json TEXT,
        updated_at TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscription_accounts(status,tier)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_subscription_events_created ON subscription_events(created_at)")
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "subscription_control_v575"}


def _event_id(user_id: str, event_type: str) -> str:
    stamp = utc_now().replace(":", "").replace("+", "")
    return f"sub:{user_id}:{event_type}:{stamp}"


def _sync_users(conn: sqlite3.Connection) -> int:
    """Mirror access state without inventing billing state or a 30-day period."""
    now = utc_now()
    users = rows(conn, "SELECT * FROM users")
    inserted = 0
    for user in users:
        user_id = str(user.get("id") or "")
        if not user_id:
            continue
        tier = normalize_tier(user.get("membership") or user.get("role"))
        raw_source = str(user.get("membership_source") or "").strip().lower()
        stripe_subscription_id = str(user.get("stripe_subscription_id") or "").strip()
        stripe_customer_id = str(user.get("stripe_customer_id") or "").strip()
        stripe_status = str(user.get("stripe_subscription_status") or "").strip().lower()
        is_stripe = raw_source == "stripe" and bool(stripe_subscription_id)
        source = "stripe" if is_stripe else ("admin_manual" if tier in {"PRO","ELITE","ADMIN"} else "free_signup")
        status = stripe_status if is_stripe and stripe_status else "active"
        period_start = str(user.get("membership_started_at") or user.get("created_at") or now)
        period_end = str(
            (user.get("stripe_current_period_end") if is_stripe else user.get("membership_expires_at"))
            or ""
        ) or None
        last_payment = str(user.get("last_payment_status") or ("manual" if source == "admin_manual" else "not_required"))
        exists = scalar(conn, "SELECT COUNT(*) FROM subscription_accounts WHERE user_id=?", (user_id,), 0)
        if exists:
            conn.execute(
                """UPDATE subscription_accounts
                   SET tier=?,status=?,source=?,current_period_start=?,current_period_end=?,
                       stripe_customer_id=?,stripe_subscription_id=?,last_payment_status=?,updated_at=?
                   WHERE user_id=?""",
                (tier,status,source,period_start,period_end,stripe_customer_id,stripe_subscription_id,last_payment,now,user_id),
            )
            continue
        conn.execute(
            """INSERT OR IGNORE INTO subscription_accounts
               (user_id,tier,status,source,current_period_start,current_period_end,grace_until,soft_block,
                stripe_customer_id,stripe_subscription_id,last_payment_status,created_at,updated_at,payload_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id,tier,status,source,period_start,period_end,None,0,stripe_customer_id,stripe_subscription_id,
             last_payment,now,now,dumps({"synced_from_users": True, "billing_truth": source == "stripe"})),
        )
        conn.execute(
            """INSERT OR IGNORE INTO subscription_events
               (id,user_id,event_type,tier,amount,status,source,payload_json,created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (_event_id(user_id, "created"), user_id, "created", tier, 0, status, source,
             dumps({"origin": "access_sync", "revenue_event": False}), now),
        )
        inserted += 1
    return inserted


def apply_subscription_rules(db_path: str) -> Dict[str, Any]:
    ensure_subscription_schema(db_path)
    conn = connect(db_path)
    inserted = _sync_users(conn)
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat(timespec="seconds")
    grace_dt = (now_dt + timedelta(days=3)).isoformat(timespec="seconds")

    expired = rows(conn, """SELECT user_id,tier,current_period_end,grace_until,status FROM subscription_accounts
                         WHERE source='stripe' AND tier IN ('PRO','ELITE')
                           AND status IN ('active','trialing','grace')
                           AND current_period_end IS NOT NULL AND current_period_end < ?""", (now,))
    updated = 0
    for sub in expired:
        user_id = sub.get("user_id")
        grace_until = sub.get("grace_until")
        if not grace_until:
            conn.execute("UPDATE subscription_accounts SET status='grace', grace_until=?, soft_block=0, updated_at=? WHERE user_id=?", (grace_dt, now, user_id))
            conn.execute("INSERT OR IGNORE INTO subscription_events(id,user_id,event_type,tier,amount,status,source,payload_json,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                         (_event_id(user_id, "grace_started"), user_id, "grace_started", sub.get("tier"), 0, "grace", "system", dumps({"period_end": sub.get("current_period_end")}), now))
            updated += 1
        elif grace_until < now:
            conn.execute("UPDATE subscription_accounts SET status='past_due', soft_block=1, updated_at=? WHERE user_id=?", (now, user_id))
            conn.execute("INSERT OR IGNORE INTO subscription_events(id,user_id,event_type,tier,amount,status,source,payload_json,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                         (_event_id(user_id, "soft_blocked"), user_id, "soft_blocked", sub.get("tier"), 0, "past_due", "system", dumps({"grace_until": grace_until}), now))
            updated += 1
    conn.commit()
    conn.close()
    return {"ok": True, "users_synced": inserted, "subscriptions_updated": updated}


def subscription_summary(db_path: str, apply_rules: bool = True, persist_metrics: bool = True) -> Dict[str, Any]:
    ensure_subscription_schema(db_path)
    if apply_rules:
        apply_subscription_rules(db_path)
    conn = connect(db_path)
    subs = rows(conn, "SELECT * FROM subscription_accounts")
    by_tier = {"FREE": 0, "PRO": 0, "ELITE": 0, "ADMIN": 0}
    by_status: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    manual_by_tier = {"PRO": 0, "ELITE": 0}
    soft_blocked = 0
    for sub in subs:
        tier = normalize_tier(sub.get("tier"))
        status = str(sub.get("status") or "active").lower()
        source = str(sub.get("source") or "unknown").lower()
        by_tier[tier] = by_tier.get(tier, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
        by_source[source] = by_source.get(source, 0) + 1
        if tier in {"PRO","ELITE"} and source != "stripe" and status in {"active","grace","trialing"}:
            manual_by_tier[tier] += 1
        if source == "stripe" and as_int(sub.get("soft_block"), 0):
            soft_blocked += 1

    # Billing truth comes from Stripe subscription records, not from access grants.
    stripe_rows = rows(
        conn,
        """SELECT user_id,plan,status,current_period_end,cancel_at_period_end,last_event_at
           FROM stripe_subscriptions
           ORDER BY COALESCE(last_event_at,'') DESC, rowid DESC"""
    )
    latest_by_user: Dict[str, Dict[str, Any]] = {}
    for item in stripe_rows:
        user_id = str(item.get("user_id") or "")
        if user_id and user_id not in latest_by_user:
            latest_by_user[user_id] = item

    active_paid = trialing = past_due = churn_risk = 0
    paid_by_tier = {"PRO": 0, "ELITE": 0}
    paid_by_status: Dict[str, int] = {}
    prices = product_plan_prices()
    estimated_mrr = 0.0
    for item in latest_by_user.values():
        tier = normalize_tier(item.get("plan"))
        status = str(item.get("status") or "").lower()
        paid_by_status[status or "unknown"] = paid_by_status.get(status or "unknown", 0) + 1
        if status == "trialing":
            trialing += 1
        if status == "past_due":
            past_due += 1
            churn_risk += 1
        if status == "active" and tier in {"PRO","ELITE"}:
            active_paid += 1
            paid_by_tier[tier] += 1
            estimated_mrr += prices.get(tier, 0.0)
            if as_int(item.get("cancel_at_period_end"), 0):
                churn_risk += 1

    estimated_mrr = round(estimated_mrr, 2)
    manual_access = sum(manual_by_tier.values())
    users_total = as_int(scalar(conn, "SELECT COUNT(*) FROM users", default=len(subs)))
    conversion = round((active_paid / users_total) * 100, 1) if users_total else 0.0
    readiness = 55
    readiness += min(15, active_paid * 5)
    readiness += 10 if users_total else 0
    readiness += 10 if scalar(conn, "SELECT COUNT(*) FROM commercial_launch_checks", default=0) else 0
    readiness += 10 if os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_PRICE_PRO") or os.getenv("STRIPE_PRICE_ELITE") else 0
    readiness -= min(20, past_due * 5 + soft_blocked * 8)
    readiness = max(0, min(100, readiness))
    actions = []
    if not (os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_PRICE_PRO") or os.getenv("STRIPE_PRICE_ELITE")):
        actions.append({"title": "Stripe pendiente", "detail": "La capa de suscripciones está lista, pero aún no hay claves/precios de Stripe configurados.", "priority": 80})
    if past_due:
        actions.append({"title": "Pagos vencidos", "detail": f"Hay {past_due} suscripciones Stripe con pago vencido. Revisar antes de venta real.", "priority": 95})
    if manual_access:
        actions.append({"title": "Accesos manuales", "detail": f"Hay {manual_access} accesos PRO/ELITE concedidos sin contarlos como ingresos.", "priority": 35})
    if not active_paid:
        actions.append({"title": "Sin suscripciones Stripe activas", "detail": "El MRR estimado está en 0 €. Los accesos manuales no se contabilizan como ingresos.", "priority": 65})
    recent_events = rows(conn, "SELECT * FROM subscription_events ORDER BY created_at DESC LIMIT 12")
    if persist_metrics:
        today = utc_now()[:10]
        payload = {
            "by_tier": by_tier,
            "by_status": by_status,
            "by_source": by_source,
            "paid_by_tier": paid_by_tier,
            "paid_by_status": paid_by_status,
            "manual_access": manual_access,
            "conversion": conversion,
            "revenue_scope": "active_stripe_subscriptions_only",
        }
        conn.execute(
            """INSERT OR REPLACE INTO revenue_daily_metrics
               (metric_date,active_paid,trialing,past_due,soft_blocked,estimated_mrr,churn_risk,payload_json,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (today,active_paid,trialing,past_due,soft_blocked,estimated_mrr,churn_risk,dumps(payload),utc_now()),
        )
        conn.commit()
    conn.close()
    return {
        "ok": True,
        "status": "PREPARADO" if readiness >= 75 else "EN PREPARACION",
        "readiness_score": readiness,
        "users_total": users_total,
        "active_paid": active_paid,
        "trialing": trialing,
        "past_due": past_due,
        "soft_blocked": soft_blocked,
        "churn_risk": churn_risk,
        "estimated_mrr": estimated_mrr,
        "estimated_mrr_verified_by_provider": False,
        "mrr_basis": "active_stripe_subscriptions_x_product_catalog",
        "revenue_scope": "active_stripe_subscriptions_only",
        "manual_access": manual_access,
        "manual_by_tier": manual_by_tier,
        "conversion_rate": conversion,
        "by_tier": by_tier,
        "by_status": by_status,
        "by_source": by_source,
        "paid_by_tier": paid_by_tier,
        "paid_by_status": paid_by_status,
        "plan_prices": prices,
        "features": FEATURES,
        "stripe_configured": bool(os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_PRICE_PRO") or os.getenv("STRIPE_PRICE_ELITE")),
        "actions": actions,
        "recent_events": recent_events,
    }

