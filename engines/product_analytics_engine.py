"""Privacy-minimized product and business analytics for V939."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from engines.company_intelligence_engine import (
    MADRID_TZ,
    classify_freshness,
    readonly_connection,
    safe_rows,
    table_columns,
    table_exists,
)


FUNNEL_STAGES = (
    "visitor",
    "registered",
    "active",
    "pro_interest",
    "checkout_started",
    "pro_customer",
    "elite_customer",
    "renewed",
    "cancelled",
)
ALLOWED_ACTIVITY_GROUPS = {
    "register": "registered",
    "registration": "registered",
    "login": "active",
    "session": "active",
    "view_app": "app",
    "app_view": "app",
    "view_matches": "matches",
    "calendar_view": "matches",
    "view_picks": "picks",
    "view_shark": "shark",
    "view_telegram": "telegram",
    "view_memberships": "pro_interest",
    "checkout_started": "checkout_started",
    "support": "support",
}


def _first(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        if row.get(name) not in (None, ""):
            return row.get(name)
    return None


def _normalized_plan(value: Any) -> str:
    text = str(value or "FREE").strip().upper().replace(" ", "")
    if text in {"ELITE+", "ELITEPLUS", "ELITE_PLUS"}:
        return "ELITE+"
    if text in {"PRO", "ELITE", "FREE"}:
        return text
    return "OTHER"


def _activity_snapshot(conn) -> dict[str, Any]:
    rows = safe_rows(conn, "user_activity", 5000)
    grouped: Counter[str] = Counter()
    latest = ""
    devices: Counter[str] = Counter()
    for row in rows:
        activity = str(_first(row, "activity_type", "event_type", "action", "type") or "").strip().lower()
        group = ALLOWED_ACTIVITY_GROUPS.get(activity)
        if group:
            grouped[group] += 1
        timestamp = str(_first(row, "created_at", "occurred_at", "timestamp", "updated_at") or "")
        if timestamp > latest:
            latest = timestamp
        payload = str(_first(row, "payload_json", "metadata_json") or "").lower()
        if "mobile" in payload:
            devices["mobile"] += 1
        elif "desktop" in payload:
            devices["desktop"] += 1
        elif "tablet" in payload:
            devices["tablet"] += 1
    return {
        "events_observed": len(rows),
        "event_groups": dict(grouped),
        "device_groups": dict(devices),
        "last_event_at": latest,
    }


def _user_snapshot(conn) -> dict[str, Any]:
    users = safe_rows(conn, "users", 10000)
    plans: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    latest_created = ""
    for row in users:
        plans[_normalized_plan(_first(row, "membership", "plan", "membership_type"))] += 1
        status = str(_first(row, "status", "account_status", "membership_status") or "unknown").strip().lower()
        statuses[status] += 1
        created = str(_first(row, "created_at", "registered_at") or "")
        latest_created = max(latest_created, created)
    return {
        "registered_users": len(users),
        "memberships": dict(plans),
        "account_statuses": dict(statuses),
        "last_registration_at": latest_created,
    }


def _checkout_counts(conn) -> dict[str, Any]:
    tables = (
        "stripe_checkout_sessions",
        "payment_checkout_sessions",
        "checkout_sessions",
        "stripe_events",
        "payment_events",
    )
    result = {"checkout_started": 0, "payments_confirmed": 0, "renewals": 0, "cancellations": 0, "failed": 0}
    evidence_tables: list[str] = []
    latest = ""
    for table in tables:
        if not table_exists(conn, table):
            continue
        evidence_tables.append(table)
        for row in safe_rows(conn, table, 5000):
            event = str(_first(row, "event_type", "type", "status", "event_name") or "").lower()
            if "checkout" in event or table.endswith("checkout_sessions"):
                result["checkout_started"] += 1
            if any(token in event for token in ("payment_succeeded", "checkout.session.completed", "invoice.paid", "paid")):
                result["payments_confirmed"] += 1
            if any(token in event for token in ("renew", "invoice.paid")):
                result["renewals"] += 1
            if any(token in event for token in ("cancel", "deleted")):
                result["cancellations"] += 1
            if any(token in event for token in ("fail", "declin", "error")):
                result["failed"] += 1
            timestamp = str(_first(row, "created_at", "received_at", "updated_at", "occurred_at") or "")
            latest = max(latest, timestamp)
    result["evidence_tables"] = evidence_tables
    result["last_event_at"] = latest
    return result


def _safe_rate(numerator: int, denominator: int, minimum_denominator: int = 10) -> dict[str, Any]:
    if denominator < minimum_denominator:
        return {"value": None, "state": "INSUFFICIENT_DATA", "numerator": numerator, "denominator": denominator}
    return {
        "value": round((numerator / denominator) * 100.0, 2),
        "state": "PARTIALLY_VERIFIED",
        "numerator": numerator,
        "denominator": denominator,
    }


def build_product_analytics_snapshot(db_path: str, app_version: str, environment: str = "local") -> dict[str, Any]:
    conn = readonly_connection(db_path)
    if conn is None:
        return {
            "version": app_version,
            "environment": environment,
            "certification_state": "NOT_CONFIGURED",
            "confidence": None,
            "funnel": {stage: None for stage in FUNNEL_STAGES},
            "limitations": ["DB local no disponible en modo read-only."],
            "pii_returned": False,
            "database_written": False,
        }
    try:
        users = _user_snapshot(conn)
        activity = _activity_snapshot(conn)
        commerce = _checkout_counts(conn)
        registered = int(users.get("registered_users") or 0)
        active_events = int((activity.get("event_groups") or {}).get("active") or 0)
        memberships = users.get("memberships") or {}
        funnel = {
            "visitor": None,
            "registered": registered,
            "active": active_events if activity.get("events_observed") else None,
            "pro_interest": (activity.get("event_groups") or {}).get("pro_interest"),
            "checkout_started": commerce.get("checkout_started"),
            "pro_customer": memberships.get("PRO", 0),
            "elite_customer": memberships.get("ELITE", 0) + memberships.get("ELITE+", 0),
            "renewed": commerce.get("renewals"),
            "cancelled": commerce.get("cancellations"),
        }
        sample = registered + int(activity.get("events_observed") or 0) + int(commerce.get("checkout_started") or 0)
        state = "PARTIALLY_VERIFIED" if sample >= 10 else "INSUFFICIENT_DATA"
        latest = max(str(activity.get("last_event_at") or ""), str(users.get("last_registration_at") or ""), str(commerce.get("last_event_at") or ""))
        return {
            "version": app_version,
            "environment": environment,
            "certification_state": state,
            "confidence": 0.7 if state == "PARTIALLY_VERIFIED" else None,
            "freshness": classify_freshness(latest, fresh_minutes=1440, stale_minutes=10080),
            "users": users,
            "activity": activity,
            "commerce": commerce,
            "funnel": funnel,
            "conversion_registered_to_paid": _safe_rate(
                int(memberships.get("PRO", 0)) + int(memberships.get("ELITE", 0)) + int(memberships.get("ELITE+", 0)),
                registered,
            ),
            "retention": {"value": None, "state": "INSUFFICIENT_DATA", "reason": "No existe cohorte certificada suficiente."},
            "churn": {"value": None, "state": "INSUFFICIENT_DATA", "reason": "No existe denominador de renovaciones certificadas suficiente."},
            "privacy": {
                "aggregated_only": True,
                "pii_returned": False,
                "full_ip_stored_by_v939": False,
                "fingerprinting": False,
                "event_payloads_returned": False,
            },
            "database_written": False,
            "external_calls": 0,
            "limitations": [
                "Las visitas anonimas no se estiman sin una senal consentida.",
                "Eventos historicos pueden no usar el vocabulario V939.",
                "No se atribuyen conversiones sin una relacion persistida y verificable.",
            ],
        }
    finally:
        conn.close()


def build_revenue_analytics_snapshot(db_path: str, app_version: str, environment: str = "local") -> dict[str, Any]:
    conn = readonly_connection(db_path)
    if conn is None:
        return {
            "version": app_version,
            "certification_state": "NOT_CONFIGURED",
            "mrr": None,
            "revenue": None,
            "limitations": ["DB local no disponible."],
            "payment_executed": False,
        }
    try:
        users = _user_snapshot(conn)
        commerce = _checkout_counts(conn)
        confirmed = int(commerce.get("payments_confirmed") or 0)
        state = "PARTIALLY_VERIFIED" if confirmed else "INSUFFICIENT_DATA"
        return {
            "version": app_version,
            "environment": environment,
            "certification_state": state,
            "confidence": 0.6 if confirmed else None,
            "memberships": users.get("memberships", {}),
            "payment_event_counts": commerce,
            "revenue": None,
            "mrr": None,
            "arpu": None,
            "currency": None,
            "freshness": classify_freshness(commerce.get("last_event_at"), fresh_minutes=1440, stale_minutes=10080),
            "payment_executed": False,
            "external_calls": 0,
            "limitations": [
                "No se calcula ingreso ni MRR sin importes, moneda, estado de pago e intervalo certificados.",
                "Esta lectura no consulta Stripe y no valida configuracion de produccion.",
            ],
        }
    finally:
        conn.close()


def product_analytics_event_contract() -> dict[str, Any]:
    return {
        "allowed": sorted(set(ALLOWED_ACTIVITY_GROUPS.values())),
        "prohibited": ["password", "token", "payment_card", "message_content", "full_ip", "device_fingerprint"],
        "retention": "REQUIRES_REVIEW",
        "consent_required_when_applicable": True,
        "automatic_experiments": False,
    }

