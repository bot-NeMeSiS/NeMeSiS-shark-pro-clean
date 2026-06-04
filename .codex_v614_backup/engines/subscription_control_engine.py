"""Revenue & Subscription Control engine for NeMeSiS SHARK PRO.

V575 keeps payments safe: it does not charge anyone and it does not require
Stripe. It creates the operational layer needed before real billing: subscription
state, renewals, grace periods, soft blocks, plan revenue and admin actions.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List

PLAN_PRICES = {
    "FREE": 0.0,
    "PRO": 19.99,
    "ELITE": 49.99,
}

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
    now = utc_now()
    users = rows(conn, "SELECT id, COALESCE(membership, role, 'FREE') AS tier, created_at FROM users")
    inserted = 0
    for user in users:
        user_id = str(user.get("id") or "")
        if not user_id:
            continue
        exists = scalar(conn, "SELECT COUNT(*) FROM subscription_accounts WHERE user_id=?", (user_id,), 0)
        if exists:
            continue
        tier = normalize_tier(user.get("tier"))
        status = "active" if tier in {"FREE", "PRO", "ELITE", "ADMIN"} else "inactive"
        period_start = now
        period_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(timespec="seconds") if tier in {"PRO", "ELITE"} else None
        source = "admin_manual" if tier in {"PRO", "ELITE", "ADMIN"} else "free_signup"
        conn.execute(
            """INSERT OR IGNORE INTO subscription_accounts
               (user_id,tier,status,source,current_period_start,current_period_end,grace_until,soft_block,last_payment_status,created_at,updated_at,payload_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, tier, status, source, period_start, period_end, None, 0, "not_required" if tier == "FREE" else "manual", now, now, dumps({"synced_from_users": True})),
        )
        conn.execute(
            """INSERT OR IGNORE INTO subscription_events
               (id,user_id,event_type,tier,amount,status,source,payload_json,created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (_event_id(user_id, "created"), user_id, "created", tier, PLAN_PRICES.get(tier, 0), status, source, dumps({"origin": "V575 sync"}), now),
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
                         WHERE tier IN ('PRO','ELITE') AND current_period_end IS NOT NULL AND current_period_end < ?""", (now,))
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


def subscription_summary(db_path: str, apply_rules: bool = True) -> Dict[str, Any]:
    ensure_subscription_schema(db_path)
    if apply_rules:
        apply_subscription_rules(db_path)
    conn = connect(db_path)
    subs = rows(conn, "SELECT * FROM subscription_accounts")
    by_tier = {"FREE": 0, "PRO": 0, "ELITE": 0, "ADMIN": 0}
    by_status: Dict[str, int] = {}
    active_paid = trialing = past_due = soft_blocked = churn_risk = 0
    estimated_mrr = 0.0
    for sub in subs:
        tier = normalize_tier(sub.get("tier"))
        status = str(sub.get("status") or "active").lower()
        by_tier[tier] = by_tier.get(tier, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
        if status == "trialing":
            trialing += 1
        if status in {"past_due", "grace"}:
            past_due += 1
            churn_risk += 1
        if as_int(sub.get("soft_block"), 0):
            soft_blocked += 1
        if tier in {"PRO", "ELITE"} and status in {"active", "grace", "trialing"} and not as_int(sub.get("soft_block"), 0):
            active_paid += 1
            estimated_mrr += PLAN_PRICES.get(tier, 0.0)
    estimated_mrr = round(estimated_mrr, 2)
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
        actions.append({"title": "Pagos vencidos", "detail": f"Hay {past_due} suscripciones en gracia o vencidas. Revisar antes de venta real.", "priority": 95})
    if not active_paid:
        actions.append({"title": "Sin usuarios pagados", "detail": "El MRR está en 0€. Correcto para beta, pendiente para lanzamiento comercial.", "priority": 65})
    recent_events = rows(conn, "SELECT * FROM subscription_events ORDER BY created_at DESC LIMIT 12")
    today = utc_now()[:10]
    conn.execute("""INSERT OR REPLACE INTO revenue_daily_metrics
                   (metric_date,active_paid,trialing,past_due,soft_blocked,estimated_mrr,churn_risk,payload_json,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                 (today, active_paid, trialing, past_due, soft_blocked, estimated_mrr, churn_risk, dumps({"by_tier": by_tier, "by_status": by_status, "conversion": conversion}), utc_now()))
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
        "conversion_rate": conversion,
        "by_tier": by_tier,
        "by_status": by_status,
        "plan_prices": PLAN_PRICES,
        "features": FEATURES,
        "stripe_configured": bool(os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_PRICE_PRO") or os.getenv("STRIPE_PRICE_ELITE")),
        "actions": actions,
        "recent_events": recent_events,
    }
