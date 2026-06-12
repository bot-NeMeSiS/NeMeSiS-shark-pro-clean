"""Payment readiness and webhook audit foundation for NeMeSiS SHARK PRO.

V734 is intentionally safe: it does not charge users and does not require the
Stripe SDK. It prepares the operational layer needed before enabling real
payments: environment checks, webhook audit storage, provider status and clear
admin blockers without exposing secrets.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable


PROVIDER_ENV = {
    "stripe_secret_key": "STRIPE_SECRET_KEY",
    "stripe_webhook_secret": "STRIPE_WEBHOOK_SECRET",
    "stripe_price_pro": "STRIPE_PRICE_PRO",
    "stripe_price_elite": "STRIPE_PRICE_ELITE",
    "public_url": "APP_PUBLIC_URL",
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


def env_present(name: str) -> bool:
    return bool(str(os.getenv(name) or "").strip())


def stable_event_id(provider: str, event_type: str, payload_text: str) -> str:
    digest = hashlib.sha1(f"{provider}:{event_type}:{payload_text[:1000]}:{utc_now()}".encode("utf-8")).hexdigest()[:24]
    return f"pay:{digest}"


def safe_json(payload: Any) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, default=str)[:20000]


def ensure_payment_schema(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS payment_webhook_events(
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
    cur.execute("""CREATE TABLE IF NOT EXISTS payment_readiness_daily(
        metric_date TEXT PRIMARY KEY,
        readiness_score INTEGER DEFAULT 0,
        provider TEXT DEFAULT 'stripe',
        configured INTEGER DEFAULT 0,
        webhooks_ready INTEGER DEFAULT 0,
        checkout_ready INTEGER DEFAULT 0,
        blockers_json TEXT,
        updated_at TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_events_received ON payment_webhook_events(received_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_events_type ON payment_webhook_events(provider,event_type,status)")
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "payments_v734"}


def provider_flags() -> Dict[str, bool]:
    public_url = env_present("APP_PUBLIC_URL") or env_present("RENDER_EXTERNAL_URL")
    return {
        "stripe_secret_key": env_present("STRIPE_SECRET_KEY"),
        "stripe_webhook_secret": env_present("STRIPE_WEBHOOK_SECRET"),
        "stripe_price_pro": env_present("STRIPE_PRICE_PRO"),
        "stripe_price_elite": env_present("STRIPE_PRICE_ELITE"),
        "public_url": public_url,
    }


def payment_readiness_snapshot(db_path: str) -> Dict[str, Any]:
    ensure_payment_schema(db_path)
    flags = provider_flags()
    checkout_ready = bool(flags["stripe_secret_key"] and flags["stripe_price_pro"] and flags["stripe_price_elite"] and flags["public_url"])
    webhooks_ready = bool(flags["stripe_webhook_secret"])
    configured = bool(checkout_ready and webhooks_ready)
    blockers = []
    labels = {
        "stripe_secret_key": "Falta STRIPE_SECRET_KEY para checkout real.",
        "stripe_webhook_secret": "Falta STRIPE_WEBHOOK_SECRET para validar webhooks.",
        "stripe_price_pro": "Falta STRIPE_PRICE_PRO.",
        "stripe_price_elite": "Falta STRIPE_PRICE_ELITE.",
        "public_url": "Falta APP_PUBLIC_URL o RENDER_EXTERNAL_URL para URLs de retorno.",
    }
    for key, ok in flags.items():
        if not ok:
            blockers.append({"key": key, "message": labels[key], "priority": 90 if key in {"stripe_secret_key", "stripe_webhook_secret"} else 75})
    conn = connect(db_path)
    events_total = scalar(conn, "SELECT COUNT(*) FROM payment_webhook_events", default=0)
    events_recent = rows(conn, "SELECT provider,event_type,verified,processed,status,plan,amount,currency,received_at FROM payment_webhook_events ORDER BY received_at DESC LIMIT 12")
    score = 25
    score += 20 if flags["stripe_secret_key"] else 0
    score += 15 if flags["stripe_webhook_secret"] else 0
    score += 15 if flags["stripe_price_pro"] else 0
    score += 15 if flags["stripe_price_elite"] else 0
    score += 10 if flags["public_url"] else 0
    score = max(0, min(100, score))
    today = utc_now()[:10]
    conn.execute(
        """INSERT OR REPLACE INTO payment_readiness_daily
           (metric_date,readiness_score,provider,configured,webhooks_ready,checkout_ready,blockers_json,updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (today, score, "stripe", int(configured), int(webhooks_ready), int(checkout_ready), safe_json(blockers), utc_now()),
    )
    conn.commit()
    conn.close()
    return {
        "ok": True,
        "schema": "payments_v734",
        "provider": "stripe",
        "status": "LISTO_PARA_CONFIGURAR" if not configured else "CONFIGURADO",
        "configured": configured,
        "checkout_ready": checkout_ready,
        "webhooks_ready": webhooks_ready,
        "readiness_score": score,
        "env_present": flags,
        "blockers": blockers,
        "events_total": events_total,
        "recent_events": events_recent,
        "safety_note": "V734 no cobra ni cambia membresías automáticamente: prepara auditoría y configuración segura antes del modo pago real.",
    }


def record_payment_webhook_event(db_path: str, provider: str, payload: Dict[str, Any], signature_present: bool = False) -> Dict[str, Any]:
    ensure_payment_schema(db_path)
    provider = str(provider or "stripe").lower()[:40]
    event_type = str(payload.get("type") or payload.get("event_type") or "unknown")[:120]
    event_id = str(payload.get("id") or "")[:160]
    data_obj = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    obj = data_obj.get("object") if isinstance(data_obj.get("object"), dict) else {}
    metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
    user_id = str(metadata.get("user_id") or payload.get("user_id") or "")[:120]
    plan = str(metadata.get("plan") or payload.get("plan") or "").upper()[:20]
    amount = 0.0
    try:
        amount = float(obj.get("amount_total") or obj.get("amount_paid") or payload.get("amount") or 0) / (100 if obj.get("amount_total") or obj.get("amount_paid") else 1)
    except Exception:
        amount = 0.0
    currency = str(obj.get("currency") or payload.get("currency") or "eur").upper()[:10]
    verified = bool(signature_present and env_present("STRIPE_WEBHOOK_SECRET"))
    status = "verified_stored" if verified else "stored_unverified"
    payload_text = safe_json({"id": event_id, "type": event_type, "metadata": metadata, "object_keys": sorted(list(obj.keys()))[:40]})
    row_id = event_id or stable_event_id(provider, event_type, payload_text)
    conn = connect(db_path)
    conn.execute(
        """INSERT OR REPLACE INTO payment_webhook_events
           (id,provider,event_type,event_id,verified,processed,status,user_id,plan,amount,currency,reason,payload_json,received_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (row_id, provider, event_type, event_id, int(verified), 0, status, user_id, plan, round(amount, 2), currency, "Modo auditoría V734: no aplica membresía automáticamente.", payload_text, utc_now()),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "stored": True, "provider": provider, "event_type": event_type, "verified": verified, "status": status}
