"""Stripe real subscription engine for NeMeSiS SHARK PRO.

V782 upgrades the previous audit-only payment foundation into a controlled
Stripe Checkout + webhook integration. The module is deliberately defensive:
missing SDK/secrets never crash the app, webhooks must be verified when the
webhook secret is configured, and membership changes are only applied for known
PRO/ELITE subscription events.
"""
from __future__ import annotations

import json
import os
import sqlite3
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional

MADRID_OFFSET_FALLBACK = "+01:00"
ACTIVE_STATUSES = {"active", "trialing"}
KEEP_ACCESS_STATUSES = {"active", "trialing", "past_due"}
CANCEL_STATUSES = {"canceled", "unpaid", "incomplete_expired", "paused"}
VALID_PAID_PLANS = {"PRO", "ELITE"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def utc_from_timestamp(value: Any) -> str:
    try:
        ts = int(value or 0)
        if ts <= 0:
            return ""
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")
    except Exception:
        return ""


def future_period(days: int = 31) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")


def safe_json(payload: Any, limit: int = 30000) -> str:
    try:
        text = json.dumps(payload or {}, ensure_ascii=False, default=str)
    except Exception:
        text = json.dumps({"unserializable": True}, ensure_ascii=False)
    return text[:limit]


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


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except sqlite3.OperationalError:
        return set()


def add_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if column not in table_columns(conn, table):
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        except sqlite3.OperationalError:
            pass


def rows(conn: sqlite3.Connection, query: str, params: Iterable[Any] = ()) -> list[Dict[str, Any]]:
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


def stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha1(":".join(str(p or "") for p in parts).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}:{digest}"


def checkout_idempotency_key(user_id: str, plan: str, at: Optional[datetime] = None) -> str:
    """Deduplicate accidental double submits without blocking a later purchase."""
    current = at or datetime.now(timezone.utc)
    ten_minute_bucket = int(current.timestamp()) // 600
    return stable_id("nemesis_checkout", user_id, normalize_plan(plan), ten_minute_bucket)


def normalize_plan(plan: Any) -> str:
    value = str(plan or "").strip().upper()
    if value in {"PRO", "PRO_PLUS", "PRO+"}:
        return "PRO"
    if value in {"ELITE", "ELITE_PLUS", "ELITE+"}:
        return "ELITE"
    return ""


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def env_present(name: str) -> bool:
    return bool(str(os.getenv(name) or "").strip())


def public_base_url() -> str:
    raw = os.getenv("APP_PUBLIC_URL") or os.getenv("PUBLIC_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL") or ""
    raw = raw.strip().rstrip("/")
    if raw and not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    return raw


def plan_price_id(plan: str) -> str:
    plan = normalize_plan(plan)
    return str(os.getenv(f"STRIPE_PRICE_{plan}") or "").strip()


def plan_catalog() -> Dict[str, Dict[str, Any]]:
    return {
        "FREE": {
            "plan": "FREE",
            "title": "FREE",
            "price_label": "0€",
            "price_id": "",
            "configured": True,
            "features": ["Calendario", "Directo", "Resultados", "SHARK base"],
        },
        "PRO": {
            "plan": "PRO",
            "title": "PRO",
            "price_label": os.getenv("STRIPE_PRICE_PRO_LABEL", "9,99 €/mes"),
            "price_id": plan_price_id("PRO"),
            "configured": bool(plan_price_id("PRO")),
            "features": ["Picks PRO", "Combis", "Telegram premium", "Más lectura SHARK"],
        },
        "ELITE": {
            "plan": "ELITE",
            "title": "ELITE",
            "price_label": os.getenv("STRIPE_PRICE_ELITE_LABEL", "24,99 €/mes"),
            "price_id": plan_price_id("ELITE"),
            "configured": bool(plan_price_id("ELITE")),
            "features": ["Picks ELITE", "Alertas live", "Prioridad Telegram", "SHARK contextual"],
        },
    }


def stripe_sdk():
    try:
        import stripe  # type: ignore
        return stripe
    except Exception:
        return None


def stripe_runtime_status(db_path: str = "") -> Dict[str, Any]:
    catalog = plan_catalog()
    flags = {
        "stripe_sdk": stripe_sdk() is not None,
        "secret_key": env_present("STRIPE_SECRET_KEY"),
        "webhook_secret": env_present("STRIPE_WEBHOOK_SECRET"),
        "price_pro": bool(catalog["PRO"]["price_id"]),
        "price_elite": bool(catalog["ELITE"]["price_id"]),
        "public_url": bool(public_base_url()),
        "portal_enabled": env_bool("STRIPE_CUSTOMER_PORTAL_ENABLED", True),
        "payments_enabled": env_bool("PAYMENTS_ENABLED", True),
    }
    checkout_ready = all(flags[k] for k in ["stripe_sdk", "secret_key", "price_pro", "price_elite", "public_url"]) and flags["payments_enabled"]
    webhook_ready = flags["stripe_sdk"] and flags["webhook_secret"]
    blockers = []
    labels = {
        "stripe_sdk": "Falta instalar la librería stripe en requirements.txt/Render.",
        "secret_key": "Falta STRIPE_SECRET_KEY.",
        "webhook_secret": "Falta STRIPE_WEBHOOK_SECRET para validar eventos reales.",
        "price_pro": "Falta STRIPE_PRICE_PRO.",
        "price_elite": "Falta STRIPE_PRICE_ELITE.",
        "public_url": "Falta APP_PUBLIC_URL, PUBLIC_BASE_URL o RENDER_EXTERNAL_URL.",
        "payments_enabled": "PAYMENTS_ENABLED está desactivado.",
    }
    for key, ok in flags.items():
        if key in labels and not ok:
            blockers.append({"key": key, "message": labels[key], "priority": 95 if key in {"secret_key", "webhook_secret"} else 80})
    summary = {}
    if db_path:
        try:
            ensure_stripe_schema(db_path)
            conn = connect(db_path)
            summary = {
                "events_total": scalar(conn, "SELECT COUNT(*) FROM payment_webhook_events", default=0),
                "subscriptions_total": scalar(conn, "SELECT COUNT(*) FROM stripe_subscriptions", default=0),
                "active_subscriptions": scalar(conn, "SELECT COUNT(*) FROM stripe_subscriptions WHERE status IN ('active','trialing','past_due')", default=0),
                "last_events": rows(conn, "SELECT provider,event_type,verified,processed,status,plan,amount,currency,received_at FROM payment_webhook_events ORDER BY received_at DESC LIMIT 10"),
                "subscriptions": rows(conn, "SELECT user_id,plan,status,current_period_end,last_event_at FROM stripe_subscriptions ORDER BY last_event_at DESC LIMIT 20"),
            }
            conn.close()
        except Exception as exc:
            summary = {"error": str(exc)}
    return {
        "ok": True,
        "mode": os.getenv("PAYMENTS_MODE", "stripe_real"),
        "checkout_ready": bool(checkout_ready),
        "webhook_ready": bool(webhook_ready),
        "configured": bool(checkout_ready and webhook_ready),
        "flags": flags,
        "blockers": blockers,
        "plans": catalog,
        "summary": summary,
        "public_base_url": public_base_url(),
    }


def ensure_stripe_schema(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS payment_webhook_events(
        id TEXT PRIMARY KEY,
        provider TEXT DEFAULT 'stripe',
        event_type TEXT,
        event_id TEXT,
        verified INTEGER DEFAULT 0,
        processed INTEGER DEFAULT 0,
        status TEXT DEFAULT 'stored',
        user_id TEXT,
        plan TEXT,
        amount REAL DEFAULT 0,
        currency TEXT,
        reason TEXT,
        payload_json TEXT,
        received_at TEXT
    )""")
    for col, ddl in {
        "stripe_customer_id": "TEXT",
        "stripe_subscription_id": "TEXT",
        "stripe_subscription_status": "TEXT",
        "stripe_price_id": "TEXT",
        "stripe_current_period_end": "TEXT",
        "last_payment_at": "TEXT",
        "last_payment_status": "TEXT",
    }.items():
        add_column(conn, "users", col, ddl)
    for col, ddl in {
        "stripe_customer_id": "TEXT",
        "stripe_subscription_id": "TEXT",
        "stripe_session_id": "TEXT",
    }.items():
        add_column(conn, "payment_webhook_events", col, ddl)
    conn.execute("""CREATE TABLE IF NOT EXISTS stripe_checkout_sessions(
        id TEXT PRIMARY KEY,
        user_id TEXT,
        plan TEXT,
        stripe_session_id TEXT,
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT,
        status TEXT DEFAULT 'created',
        url TEXT,
        created_at TEXT,
        completed_at TEXT,
        raw_json TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS stripe_subscriptions(
        id TEXT PRIMARY KEY,
        user_id TEXT,
        plan TEXT,
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT,
        stripe_price_id TEXT,
        status TEXT,
        current_period_start TEXT,
        current_period_end TEXT,
        cancel_at_period_end INTEGER DEFAULT 0,
        last_event_type TEXT,
        last_event_at TEXT,
        raw_json TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stripe_sub_user ON stripe_subscriptions(user_id,status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stripe_sub_subscription ON stripe_subscriptions(stripe_subscription_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_events_received ON payment_webhook_events(received_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_events_event_id ON payment_webhook_events(event_id)")
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "stripe_v782"}


def user_by_id(conn: sqlite3.Connection, user_id: str) -> Dict[str, Any]:
    try:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else {}
    except sqlite3.OperationalError:
        return {}


def user_by_stripe(conn: sqlite3.Connection, customer_id: str = "", subscription_id: str = "") -> Dict[str, Any]:
    if subscription_id:
        row = conn.execute("SELECT user_id FROM stripe_subscriptions WHERE stripe_subscription_id=? ORDER BY last_event_at DESC LIMIT 1", (subscription_id,)).fetchone()
        if row:
            return user_by_id(conn, row["user_id"])
    if customer_id:
        row = conn.execute("SELECT * FROM users WHERE stripe_customer_id=? LIMIT 1", (customer_id,)).fetchone()
        if row:
            return dict(row)
    return {}


def resolve_plan_from_price(price_id: str) -> str:
    price_id = str(price_id or "").strip()
    if price_id and price_id == plan_price_id("PRO"):
        return "PRO"
    if price_id and price_id == plan_price_id("ELITE"):
        return "ELITE"
    return ""



def stripe_object_to_dict(obj: Any) -> Dict[str, Any]:
    """Best-effort conversion for StripeObject/dict so local checks do not need Stripe installed."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    try:
        if hasattr(obj, "to_dict_recursive"):
            return dict(obj.to_dict_recursive())
    except Exception:
        pass
    try:
        return dict(obj)
    except Exception:
        return {"id": str(getattr(obj, "id", "") or ""), "object": str(getattr(obj, "object", "") or "")}

def extract_subscription_fields(subscription: Dict[str, Any]) -> Dict[str, Any]:
    sub_id = str(subscription.get("id") or "")
    customer_id = str(subscription.get("customer") or "")
    status = str(subscription.get("status") or "").lower()
    metadata = subscription.get("metadata") if isinstance(subscription.get("metadata"), dict) else {}
    user_id = str(metadata.get("user_id") or "")
    plan = normalize_plan(metadata.get("plan"))
    price_id = ""
    try:
        items = ((subscription.get("items") or {}).get("data") or []) if isinstance(subscription.get("items"), dict) else []
        if items:
            price = items[0].get("price") or {}
            price_id = str(price.get("id") or "")
    except Exception:
        price_id = ""
    plan = plan or resolve_plan_from_price(price_id)
    return {
        "subscription_id": sub_id,
        "customer_id": customer_id,
        "status": status,
        "user_id": user_id,
        "plan": plan,
        "price_id": price_id,
        "current_period_start": utc_from_timestamp(subscription.get("current_period_start")),
        "current_period_end": utc_from_timestamp(subscription.get("current_period_end")),
        "cancel_at_period_end": int(bool(subscription.get("cancel_at_period_end"))),
    }


def apply_subscription_to_user(conn: sqlite3.Connection, fields: Dict[str, Any], event_type: str, raw: Dict[str, Any] | None = None) -> Dict[str, Any]:
    user_id = str(fields.get("user_id") or "")
    subscription_id = str(fields.get("subscription_id") or "")
    customer_id = str(fields.get("customer_id") or "")
    status = str(fields.get("status") or "").lower()
    plan = normalize_plan(fields.get("plan"))
    if not user_id:
        found = user_by_stripe(conn, customer_id=customer_id, subscription_id=subscription_id)
        user_id = str(found.get("id") or "")
    if plan not in VALID_PAID_PLANS:
        return {"applied": False, "reason": "plan_desconocido", "user_id": user_id, "status": status}
    if not user_id:
        return {"applied": False, "reason": "usuario_no_resuelto", "plan": plan, "status": status}
    period_end = str(fields.get("current_period_end") or "")
    if not period_end and status in KEEP_ACCESS_STATUSES:
        period_end = future_period(31)
    conn.execute(
        """INSERT OR REPLACE INTO stripe_subscriptions
           (id,user_id,plan,stripe_customer_id,stripe_subscription_id,stripe_price_id,status,
            current_period_start,current_period_end,cancel_at_period_end,last_event_type,last_event_at,raw_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            subscription_id or stable_id("sub", user_id, plan, customer_id),
            user_id,
            plan,
            customer_id,
            subscription_id,
            str(fields.get("price_id") or ""),
            status,
            str(fields.get("current_period_start") or ""),
            period_end,
            int(fields.get("cancel_at_period_end") or 0),
            event_type,
            utc_now(),
            safe_json(raw or {}),
        ),
    )
    if status in KEEP_ACCESS_STATUSES:
        membership_status_note = "Membresía activada por Stripe."
        if status == "past_due":
            membership_status_note = "Stripe indica pago pendiente: acceso conservado temporalmente hasta resolver el cobro."
        conn.execute(
            """UPDATE users
                  SET role=?, membership=?, membership_source='stripe', membership_started_at=COALESCE(NULLIF(membership_started_at,''), ?),
                      membership_expires_at=?, membership_note=?, membership_updated_at=?, membership_updated_by='stripe_webhook',
                      membership_admin_granted=0, stripe_customer_id=?, stripe_subscription_id=?, stripe_subscription_status=?, stripe_price_id=?,
                      stripe_current_period_end=?, last_payment_status=?, last_payment_at=CASE WHEN ?='active' THEN ? ELSE last_payment_at END
                WHERE id=?""",
            (
                plan,
                plan,
                utc_now(),
                period_end,
                membership_status_note,
                utc_now(),
                customer_id,
                subscription_id,
                status,
                str(fields.get("price_id") or ""),
                period_end,
                status,
                status,
                utc_now(),
                user_id,
            ),
        )
        return {"applied": True, "action": "membership_active", "user_id": user_id, "plan": plan, "status": status}
    if status in CANCEL_STATUSES:
        current = user_by_id(conn, user_id)
        if str(current.get("membership_source") or "") == "stripe" or str(current.get("stripe_subscription_id") or "") == subscription_id:
            conn.execute(
                """UPDATE users
                      SET role='FREE', membership='FREE', membership_source='stripe_cancelled', membership_expires_at='',
                          membership_note='Suscripción Stripe cancelada o vencida. Acceso devuelto a FREE.',
                          membership_updated_at=?, membership_updated_by='stripe_webhook', stripe_subscription_status=?, last_payment_status=?
                    WHERE id=?""",
                (utc_now(), status, status, user_id),
            )
            return {"applied": True, "action": "membership_free", "user_id": user_id, "plan": "FREE", "status": status}
    return {"applied": False, "reason": "estado_no_aplica_cambio", "user_id": user_id, "plan": plan, "status": status}


def sync_checkout_session(db_path: str, user: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Synchronize a Stripe Checkout Session after return from Checkout.

    This does not replace the webhook. It is a safety net for UX: if the client
    returns before the webhook is delivered, we retrieve the Checkout Session
    with the server secret key, verify it belongs to the logged user, and apply
    the subscription state when Stripe confirms it.
    """
    ensure_stripe_schema(db_path)
    session_id = str(session_id or "").strip()
    user_id = str((user or {}).get("id") or "").strip()
    if not session_id:
        return {"ok": False, "reason": "sin_session_id"}
    if not user_id:
        return {"ok": False, "reason": "sin_usuario"}
    stripe = stripe_sdk()
    if stripe is None:
        return {"ok": False, "reason": "stripe_sdk_no_instalado"}
    if not env_present("STRIPE_SECRET_KEY"):
        return {"ok": False, "reason": "falta_stripe_secret_key"}
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    try:
        session_obj = stripe.checkout.Session.retrieve(session_id, expand=["subscription"])
        session = stripe_object_to_dict(session_obj)
    except Exception as exc:
        return {"ok": False, "reason": "stripe_session_retrieve_failed", "error": str(exc)[:500]}

    metadata = session.get("metadata") if isinstance(session.get("metadata"), dict) else {}
    ref_user_id = str(session.get("client_reference_id") or metadata.get("user_id") or "").strip()
    if ref_user_id and ref_user_id != user_id:
        return {"ok": False, "reason": "session_no_pertenece_usuario", "session_user_id": ref_user_id}

    subscription_obj = session.get("subscription")
    subscription = stripe_object_to_dict(subscription_obj)
    subscription_id = ""
    if isinstance(subscription_obj, str):
        subscription_id = subscription_obj
    else:
        subscription_id = str(subscription.get("id") or "")
    customer_id = str(session.get("customer") or subscription.get("customer") or "")
    plan = normalize_plan(metadata.get("plan"))
    price_id = ""
    if subscription:
        fields = extract_subscription_fields(subscription)
        plan = normalize_plan(fields.get("plan")) or plan
        price_id = str(fields.get("price_id") or "")
    elif subscription_id:
        try:
            sub_obj = stripe.Subscription.retrieve(subscription_id)
            subscription = stripe_object_to_dict(sub_obj)
            fields = extract_subscription_fields(subscription)
            plan = normalize_plan(fields.get("plan")) or plan
            price_id = str(fields.get("price_id") or "")
        except Exception:
            fields = {}
    else:
        fields = {}

    plan = plan or resolve_plan_from_price(price_id)
    status = str((subscription or {}).get("status") or session.get("payment_status") or "active").lower()
    if not fields:
        fields = {
            "user_id": user_id,
            "plan": plan,
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "status": "active" if status in {"paid", "complete"} else status,
            "price_id": price_id or plan_price_id(plan),
            "current_period_start": "",
            "current_period_end": "",
            "cancel_at_period_end": 0,
        }
    fields["user_id"] = str(fields.get("user_id") or user_id)
    fields["plan"] = normalize_plan(fields.get("plan")) or plan
    fields["customer_id"] = str(fields.get("customer_id") or customer_id)
    fields["subscription_id"] = str(fields.get("subscription_id") or subscription_id)
    fields["status"] = str(fields.get("status") or "active").lower()

    conn = connect(db_path)
    try:
        conn.execute(
            """UPDATE stripe_checkout_sessions
                  SET status=?, completed_at=COALESCE(completed_at, ?), stripe_customer_id=COALESCE(NULLIF(?,''), stripe_customer_id),
                      stripe_subscription_id=COALESCE(NULLIF(?,''), stripe_subscription_id)
                WHERE stripe_session_id=?""",
            ("returned_from_checkout", utc_now(), fields.get("customer_id") or "", fields.get("subscription_id") or "", session_id),
        )
        applied = apply_subscription_to_user(conn, fields, "checkout.return.sync", {"checkout_session": session, "subscription": subscription})
        event = {
            "id": stable_id("evt_checkout_return", session_id),
            "type": "checkout.return.sync",
            "data": {"object": session},
        }
        record_event(
            conn,
            event,
            True,
            "processed" if applied.get("applied") else "verified_not_applied",
            user_id=user_id,
            plan=str(fields.get("plan") or ""),
            reason=safe_json(applied, 600),
            processed=bool(applied.get("applied")),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": bool(applied.get("applied")), "plan": fields.get("plan"), "status": fields.get("status"), "applied": applied, "session_id": session_id}


def create_checkout_session(db_path: str, user: Dict[str, Any], plan: str) -> Dict[str, Any]:
    ensure_stripe_schema(db_path)
    plan = normalize_plan(plan)
    if plan not in VALID_PAID_PLANS:
        return {"ok": False, "error": "Plan no válido para pago."}
    status = stripe_runtime_status(db_path)
    if not status["checkout_ready"]:
        return {"ok": False, "error": "Stripe Checkout no está configurado completamente.", "blockers": status.get("blockers", [])}
    user_id = str(user.get("id") or "")
    if not user_id:
        return {"ok": False, "error": "Inicia sesión antes de pagar."}
    stripe = stripe_sdk()
    if stripe is None:
        return {"ok": False, "error": "La librería stripe no está instalada."}
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    base = public_base_url()
    price_id = plan_price_id(plan)
    conn = connect(db_path)
    db_user = user_by_id(conn, user_id) or user
    customer_id = str(db_user.get("stripe_customer_id") or "")
    idempotency_key = checkout_idempotency_key(user_id, plan)
    metadata = {
        "user_id": user_id,
        "plan": plan,
        "app": "nemesis_shark_pro",
        "version": "V937",
        "checkout_attempt": idempotency_key,
    }
    try:
        kwargs = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{base}/pagos/exito?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{base}/pagos/cancelado?plan={plan}",
            "client_reference_id": user_id,
            "metadata": metadata,
            "subscription_data": {"metadata": metadata},
            "allow_promotion_codes": True,
        }
        if customer_id:
            kwargs["customer"] = customer_id
        else:
            email = str(db_user.get("email") or user.get("email") or "").strip()
            if email:
                kwargs["customer_email"] = email
        session = stripe.checkout.Session.create(**kwargs, idempotency_key=idempotency_key)
        session_id = str(getattr(session, "id", "") or session.get("id"))
        url = str(getattr(session, "url", "") or session.get("url"))
        conn.execute(
            """INSERT OR REPLACE INTO stripe_checkout_sessions
               (id,user_id,plan,stripe_session_id,stripe_customer_id,status,url,created_at,raw_json)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (session_id or stable_id("checkout", user_id, plan, utc_now()), user_id, plan, session_id, customer_id, "created", url, utc_now(), safe_json(dict(session) if hasattr(session, "keys") else {"id": session_id, "url": url})),
        )
        conn.commit()
        conn.close()
        return {"ok": True, "url": url, "session_id": session_id, "plan": plan}
    except Exception as exc:
        conn.close()
        return {"ok": False, "error": f"Stripe Checkout falló: {exc}", "plan": plan}


def create_customer_portal_session(db_path: str, user: Dict[str, Any]) -> Dict[str, Any]:
    ensure_stripe_schema(db_path)
    stripe = stripe_sdk()
    if stripe is None:
        return {"ok": False, "error": "La librería stripe no está instalada."}
    if not env_present("STRIPE_SECRET_KEY"):
        return {"ok": False, "error": "Falta STRIPE_SECRET_KEY."}
    if not env_bool("STRIPE_CUSTOMER_PORTAL_ENABLED", True):
        return {"ok": False, "error": "Portal de cliente Stripe desactivado."}
    conn = connect(db_path)
    db_user = user_by_id(conn, str(user.get("id") or "")) or user
    customer_id = str(db_user.get("stripe_customer_id") or "")
    conn.close()
    if not customer_id:
        return {"ok": False, "error": "Este usuario todavía no tiene cliente Stripe asociado."}
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    try:
        session = stripe.billing_portal.Session.create(customer=customer_id, return_url=f"{public_base_url()}/mi-cuenta")
        return {"ok": True, "url": str(getattr(session, "url", "") or session.get("url"))}
    except Exception as exc:
        return {"ok": False, "error": f"No se pudo abrir el portal de Stripe: {exc}"}


def record_event(conn: sqlite3.Connection, event: Dict[str, Any], verified: bool, status: str, user_id: str = "", plan: str = "", amount: float = 0.0, currency: str = "eur", reason: str = "", processed: bool = False) -> None:
    obj = ((event.get("data") or {}).get("object") or {}) if isinstance(event.get("data"), dict) else {}
    event_id = str(event.get("id") or stable_id("evt", event.get("type"), utc_now()))
    conn.execute(
        """INSERT OR REPLACE INTO payment_webhook_events
           (id,provider,event_type,event_id,verified,processed,status,user_id,plan,amount,currency,reason,payload_json,received_at,
            stripe_customer_id,stripe_subscription_id,stripe_session_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            event_id,
            "stripe",
            str(event.get("type") or "unknown"),
            event_id,
            int(verified),
            int(processed),
            status,
            user_id,
            plan,
            round(float(amount or 0), 2),
            str(currency or "eur").upper()[:10],
            reason[:500],
            safe_json(event),
            utc_now(),
            str(obj.get("customer") or ""),
            str(obj.get("subscription") or obj.get("id") if str(obj.get("object") or "") == "subscription" else obj.get("subscription") or ""),
            str(obj.get("id") or "") if str(obj.get("object") or "") == "checkout.session" else "",
        ),
    )


def parse_webhook_event(payload_bytes: bytes, signature: str) -> Dict[str, Any]:
    stripe = stripe_sdk()
    if stripe is None:
        raise RuntimeError("La librería stripe no está instalada.")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET") or ""
    if not secret:
        raise RuntimeError("Falta STRIPE_WEBHOOK_SECRET; no se procesa el webhook real.")
    return stripe.Webhook.construct_event(payload_bytes, signature, secret)


def process_stripe_webhook(db_path: str, payload_bytes: bytes, signature: str) -> Dict[str, Any]:
    ensure_stripe_schema(db_path)
    verified = False
    try:
        event = parse_webhook_event(payload_bytes, signature)
        if not isinstance(event, dict):
            event = dict(event)
        verified = True
    except Exception as exc:
        conn = connect(db_path)
        try:
            fallback = json.loads((payload_bytes or b"{}").decode("utf-8") or "{}")
        except Exception:
            fallback = {"type": "unreadable"}
        record_event(conn, fallback, False, "invalid_signature", reason=str(exc), processed=False)
        conn.commit()
        conn.close()
        return {"ok": False, "verified": False, "processed": False, "error": str(exc), "status": "invalid_signature"}

    event_type = str(event.get("type") or "unknown")
    obj = ((event.get("data") or {}).get("object") or {}) if isinstance(event.get("data"), dict) else {}
    metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
    user_id = str(metadata.get("user_id") or obj.get("client_reference_id") or "")
    plan = normalize_plan(metadata.get("plan"))
    amount = 0.0
    try:
        amount = float(obj.get("amount_total") or obj.get("amount_paid") or 0) / 100
    except Exception:
        amount = 0.0
    currency = str(obj.get("currency") or "eur")
    conn = connect(db_path)
    event_id = str(event.get("id") or "").strip()
    if event_id:
        existing = conn.execute(
            "SELECT processed,status FROM payment_webhook_events WHERE event_id=? LIMIT 1",
            (event_id,),
        ).fetchone()
        if existing and int(existing["processed"] or 0) == 1:
            conn.close()
            return {
                "ok": True,
                "verified": True,
                "processed": False,
                "duplicate": True,
                "event_type": event_type,
                "status": "idempotent_duplicate",
            }
    applied: Dict[str, Any] = {"applied": False, "reason": "evento_solo_auditado"}
    status = "verified_stored"
    processed = False
    try:
        if event_type == "checkout.session.completed":
            session_id = str(obj.get("id") or "")
            customer_id = str(obj.get("customer") or "")
            subscription_id = str(obj.get("subscription") or "")
            if user_id:
                conn.execute(
                    """UPDATE users SET stripe_customer_id=COALESCE(NULLIF(?,''), stripe_customer_id),
                                      stripe_subscription_id=COALESCE(NULLIF(?,''), stripe_subscription_id)
                       WHERE id=?""",
                    (customer_id, subscription_id, user_id),
                )
                conn.execute(
                    """UPDATE stripe_checkout_sessions SET status='completed', completed_at=?, stripe_customer_id=?, stripe_subscription_id=?
                       WHERE stripe_session_id=?""",
                    (utc_now(), customer_id, subscription_id, session_id),
                )
            fields = {
                "user_id": user_id,
                "plan": plan,
                "customer_id": customer_id,
                "subscription_id": subscription_id,
                "status": "active",
                "price_id": plan_price_id(plan),
                "current_period_end": "",
                "current_period_start": "",
                "cancel_at_period_end": 0,
            }
            # Try to retrieve the subscription for accurate period end.
            stripe = stripe_sdk()
            if stripe is not None and subscription_id and env_present("STRIPE_SECRET_KEY"):
                try:
                    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
                    subscription = stripe.Subscription.retrieve(subscription_id)
                    fields.update(extract_subscription_fields(dict(subscription)))
                    fields["user_id"] = fields.get("user_id") or user_id
                    fields["plan"] = fields.get("plan") or plan
                except Exception:
                    pass
            applied = apply_subscription_to_user(conn, fields, event_type, obj)
            processed = bool(applied.get("applied"))
            status = "processed" if processed else "verified_not_applied"
        elif event_type.startswith("customer.subscription."):  # handles customer.subscription.created/updated/deleted
            fields = extract_subscription_fields(obj)
            applied = apply_subscription_to_user(conn, fields, event_type, obj)
            user_id = user_id or str(applied.get("user_id") or fields.get("user_id") or "")
            plan = plan or str(applied.get("plan") or fields.get("plan") or "")
            processed = bool(applied.get("applied"))
            status = "processed" if processed else "verified_not_applied"
        elif event_type in {"invoice.payment_succeeded", "invoice.paid"}:
            subscription_id = str(obj.get("subscription") or "")
            customer_id = str(obj.get("customer") or "")
            found = user_by_stripe(conn, customer_id=customer_id, subscription_id=subscription_id)
            user_id = user_id or str(found.get("id") or "")
            if user_id:
                conn.execute("UPDATE users SET last_payment_status='paid', last_payment_at=?, membership_note='Último pago Stripe confirmado.' WHERE id=?", (utc_now(), user_id))
                processed = True
                status = "payment_recorded"
        elif event_type in {"invoice.payment_failed", "invoice.payment_action_required"}:
            subscription_id = str(obj.get("subscription") or "")
            customer_id = str(obj.get("customer") or "")
            found = user_by_stripe(conn, customer_id=customer_id, subscription_id=subscription_id)
            user_id = user_id or str(found.get("id") or "")
            if user_id:
                conn.execute("UPDATE users SET last_payment_status='payment_failed', membership_note='Stripe indica incidencia de pago. Revisar portal de cliente.' WHERE id=?", (user_id,))
                processed = True
                status = "payment_issue_recorded"
        record_event(conn, event, verified, status, user_id=user_id, plan=plan, amount=amount, currency=currency, reason=safe_json(applied, 600), processed=processed)
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "verified": True, "processed": processed, "event_type": event_type, "status": status, "applied": applied}


def client_payments_context(db_path: str, user: Dict[str, Any]) -> Dict[str, Any]:
    ensure_stripe_schema(db_path)
    status = stripe_runtime_status(db_path)
    plan = str(user.get("membership") or user.get("role") or "FREE").upper()
    conn = connect(db_path)
    uid = str(user.get("id") or "")
    db_user = user_by_id(conn, uid) if uid else {}
    subs = rows(conn, "SELECT plan,status,current_period_end,cancel_at_period_end,last_event_at FROM stripe_subscriptions WHERE user_id=? ORDER BY last_event_at DESC LIMIT 5", (uid,)) if uid else []
    conn.close()
    return {
        "ok": True,
        "current_plan": plan,
        "stripe_customer_id_present": bool(db_user.get("stripe_customer_id")),
        "stripe_subscription_status": db_user.get("stripe_subscription_status") or "",
        "stripe_current_period_end": db_user.get("stripe_current_period_end") or user.get("membership_expires_at") or "",
        "plans": status.get("plans", {}),
        "checkout_ready": status.get("checkout_ready"),
        "portal_ready": bool(status.get("flags", {}).get("stripe_sdk") and status.get("flags", {}).get("secret_key") and db_user.get("stripe_customer_id")),
        "blockers": status.get("blockers", []),
        "subscriptions": subs,
    }
# QA token: customer.subscription.deleted
