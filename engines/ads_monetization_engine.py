"""Direct-sold advertising for FREE members; no ad network or provider dependency."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import ipaddress
import os
import re
import sqlite3
from urllib.parse import urlparse

PACKAGES = {
    7: {"amount_cents": 4900, "label": "7 días", "price": "49 €"},
    30: {"amount_cents": 14900, "label": "30 días", "price": "149 €"},
    90: {"amount_cents": 34900, "label": "90 días", "price": "349 €"},
}
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ALLOWED_PLACEMENTS = {"home", "live", "calendar", "all"}


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def stamp(value=None):
    return (value or utc_now()).isoformat()


def database_path():
    configured = os.environ.get("DB_PATH") or os.environ.get("DATABASE_PATH")
    if configured:
        return configured
    return "/data/database.db" if Path("/data").is_dir() else "database.db"


def connect(path=None):
    db_path = str(path or database_path())
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=2)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=2000")
    return conn


def ensure_schema(path=None):
    with connect(path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS ad_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            advertiser_name TEXT NOT NULL,
            company_name TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            destination_url TEXT NOT NULL,
            placement TEXT NOT NULL DEFAULT 'all',
            package_days INTEGER NOT NULL,
            amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'eur',
            status TEXT NOT NULL DEFAULT 'awaiting_payment_setup',
            stripe_session_id TEXT,
            stripe_payment_intent TEXT,
            terms_accepted_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            paid_at TEXT,
            starts_at TEXT,
            ends_at TEXT,
            impressions INTEGER NOT NULL DEFAULT 0,
            clicks INTEGER NOT NULL DEFAULT 0
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_ad_campaigns_stripe_session
            ON ad_campaigns(stripe_session_id) WHERE stripe_session_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_ad_campaigns_delivery
            ON ad_campaigns(status, placement, starts_at, ends_at);
        """)
    return True


def validate_https_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        return None
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            return None
    except ValueError:
        pass
    return value.strip()


def validate_campaign_form(form):
    advertiser = str(form.get("advertiser_name", "")).strip()
    company = str(form.get("company_name", "")).strip()
    email = str(form.get("contact_email", "")).strip().lower()
    title = str(form.get("title", "")).strip()
    body = str(form.get("body", "")).strip()
    destination = validate_https_url(str(form.get("destination_url", "")))
    try:
        days = int(form.get("package_days", "0"))
    except (TypeError, ValueError):
        days = 0
    if not 2 <= len(advertiser) <= 100:
        return None, "Indica el nombre del anunciante (2–100 caracteres)."
    if not 2 <= len(company) <= 140:
        return None, "Indica la empresa o persona facturada (2–140 caracteres)."
    if not EMAIL_RE.fullmatch(email) or len(email) > 254:
        return None, "El correo de contacto no es válido."
    if not 5 <= len(title) <= 90:
        return None, "El titular debe tener entre 5 y 90 caracteres."
    if not 15 <= len(body) <= 220:
        return None, "El texto del anuncio debe tener entre 15 y 220 caracteres."
    if not destination:
        return None, "El destino debe ser una URL HTTPS válida."
    if days not in PACKAGES:
        return None, "Selecciona un paquete publicitario válido."
    return {
        "advertiser_name": advertiser,
        "company_name": company,
        "contact_email": email,
        "title": title,
        "body": body,
        "destination_url": destination,
        "placement": "all",
        "package_days": days,
        "amount_cents": PACKAGES[days]["amount_cents"],
        "currency": "eur",
    }, None


def create_campaign(data, terms_accepted, path=None):
    if not terms_accepted:
        raise ValueError("Se requiere aceptar las condiciones publicitarias.")
    if data.get("package_days") not in PACKAGES or data.get("amount_cents") != PACKAGES[data["package_days"]]["amount_cents"]:
        raise ValueError("Paquete publicitario no válido.")
    ensure_schema(path)
    now = stamp()
    status = "pending_payment" if os.environ.get("STRIPE_SECRET_KEY") and os.environ.get("ADS_STRIPE_TAX_READY", "").lower() == "true" else "awaiting_payment_setup"
    with connect(path) as conn:
        cur = conn.execute("""
            INSERT INTO ad_campaigns
            (advertiser_name, company_name, contact_email, title, body, destination_url,
             placement, package_days, amount_cents, currency, status, terms_accepted_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["advertiser_name"], data["company_name"], data["contact_email"], data["title"],
            data["body"], data["destination_url"], data.get("placement", "all"),
            data["package_days"], data["amount_cents"], "eur", status, now, now,
        ))
        return int(cur.lastrowid)


def campaign_by_id(campaign_id, path=None):
    ensure_schema(path)
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM ad_campaigns WHERE id=?", (int(campaign_id),)).fetchone()
    return dict(row) if row else None


def campaign_by_session(session_id, path=None):
    if not session_id or len(str(session_id)) > 255:
        return None
    ensure_schema(path)
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM ad_campaigns WHERE stripe_session_id=?", (str(session_id),)).fetchone()
    return dict(row) if row else None


def save_checkout_session(campaign_id, session_id, path=None):
    if not session_id or len(str(session_id)) > 255:
        raise ValueError("Sesión de pago no válida.")
    ensure_schema(path)
    with connect(path) as conn:
        conn.execute(
            "UPDATE ad_campaigns SET stripe_session_id=?, status='pending_payment' WHERE id=? AND status IN ('pending_payment','awaiting_payment_setup')",
            (str(session_id), int(campaign_id)),
        )


def mark_paid(campaign_id, session_id, payment_intent=None, path=None):
    ensure_schema(path)
    with connect(path) as conn:
        row = conn.execute("SELECT stripe_session_id, status FROM ad_campaigns WHERE id=?", (int(campaign_id),)).fetchone()
        if not row or row["stripe_session_id"] != session_id:
            return False
        if row["status"] in ("paid_pending_review", "active", "paused", "expired"):
            return row["status"] in ("paid_pending_review", "active", "paused", "expired")
        if row["status"] != "pending_payment":
            return False
        conn.execute(
            "UPDATE ad_campaigns SET status='paid_pending_review', paid_at=?, stripe_payment_intent=? WHERE id=? AND stripe_session_id=? AND status='pending_payment'",
            (stamp(), str(payment_intent or "")[:255] or None, int(campaign_id), session_id),
        )
        return True


def mark_payment_failed(campaign_id, session_id, status="payment_failed", path=None):
    if status not in {"payment_failed", "payment_expired"}:
        return False
    ensure_schema(path)
    with connect(path) as conn:
        cur = conn.execute(
            "UPDATE ad_campaigns SET status=? WHERE id=? AND stripe_session_id=? AND status='pending_payment'",
            (status, int(campaign_id), str(session_id)),
        )
        return cur.rowcount == 1


def list_campaigns(path=None, limit=100):
    ensure_schema(path)
    with connect(path) as conn:
        rows = conn.execute("SELECT * FROM ad_campaigns ORDER BY created_at DESC, id DESC LIMIT ?", (max(1, min(int(limit), 250)),)).fetchall()
    return [dict(row) for row in rows]


def active_campaign(path=None, placement="all"):
    try:
        ensure_schema(path)
        now = stamp()
        with connect(path) as conn:
            row = conn.execute("""
                SELECT id, advertiser_name, company_name, title, body, destination_url,
                       placement, package_days, impressions, clicks
                FROM ad_campaigns
                WHERE status='active' AND starts_at <= ? AND ends_at > ?
                  AND (placement='all' OR placement=?)
                ORDER BY impressions ASC, created_at ASC, id ASC
                LIMIT 1
            """, (now, now, placement)).fetchone()
        return dict(row) if row else None
    except (sqlite3.Error, OSError, ValueError, TypeError):
        return None


def record_event(campaign_id, event_type, path=None):
    if event_type not in {"impressions", "clicks"}:
        return False
    ensure_schema(path)
    with connect(path) as conn:
        cur = conn.execute(
            f"UPDATE ad_campaigns SET {event_type}={event_type}+1 WHERE id=? AND status='active'",
            (int(campaign_id),),
        )
        return cur.rowcount == 1


def review_campaign(campaign_id, action, path=None):
    ensure_schema(path)
    now = stamp()
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM ad_campaigns WHERE id=?", (int(campaign_id),)).fetchone()
        if not row:
            return False, "Campaña no encontrada."
        if action == "activate":
            if row["status"] != "paid_pending_review":
                return False, "Solo se pueden activar campañas pagadas y pendientes de revisión."
            ends = stamp(utc_now() + timedelta(days=int(row["package_days"])))
            conn.execute(
                "UPDATE ad_campaigns SET status='active', starts_at=?, ends_at=? WHERE id=? AND status='paid_pending_review'",
                (now, ends, int(campaign_id)),
            )
            return True, "Campaña activada."
        if action == "pause":
            if row["status"] != "active":
                return False, "Solo se pueden pausar campañas activas."
            conn.execute("UPDATE ad_campaigns SET status='paused' WHERE id=? AND status='active'", (int(campaign_id),))
            return True, "Campaña pausada."
        if action == "reject":
            if row["status"] != "paid_pending_review":
                return False, "Solo se pueden rechazar campañas pagadas pendientes de revisión."
            conn.execute("UPDATE ad_campaigns SET status='refund_required' WHERE id=? AND status='paid_pending_review'", (int(campaign_id),))
            return True, "Campaña rechazada. Tramita el reembolso en Stripe y márcalo como confirmado solo después de verificarlo."
        if action == "mark_refunded":
            if row["status"] != "refund_required":
                return False, "La campaña no está pendiente de reembolso."
            conn.execute("UPDATE ad_campaigns SET status='refunded' WHERE id=? AND status='refund_required'", (int(campaign_id),))
            return True, "Reembolso marcado como confirmado. Debes haberlo verificado previamente en Stripe."
        return False, "Acción no permitida."
