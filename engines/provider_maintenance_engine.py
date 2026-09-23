"""Read-only provider maintenance plus explicit one-call connectivity checks.

Opening admin pages never contacts a provider. Network access only happens through an
authenticated POST initiated by the administrator. No secret value is returned.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

PROVIDERS = ("api_football", "the_odds_api", "thesportsdb")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _env_present(*names: str) -> bool:
    return any(bool(str(os.getenv(name) or "").strip()) for name in names)


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _safe_text(value: Any, limit: int = 120) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    return text[:limit]


def _json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _connect_readonly(db_path: str | None) -> sqlite3.Connection | None:
    if not db_path:
        return None
    path = Path(db_path)
    if not path.is_file():
        return None
    try:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=.5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        return conn
    except sqlite3.Error:
        return None


def _table(conn: sqlite3.Connection | None, name: str) -> bool:
    if conn is None:
        return False
    try:
        return bool(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone())
    except sqlite3.Error:
        return False


def _automation(conn: sqlite3.Connection | None, key: str) -> dict[str, Any]:
    if not _table(conn, "automation_state"):
        return {}
    try:
        row = conn.execute(
            "SELECT value_json,updated_at FROM automation_state WHERE key=? LIMIT 1", (key,)
        ).fetchone()
    except sqlite3.Error:
        return {}
    if not row:
        return {}
    payload = _json(row["value_json"])
    payload.setdefault("_updated_at", row["updated_at"] or "")
    return payload


def _latest_sync(conn: sqlite3.Connection | None, source_like: str) -> dict[str, Any]:
    if not _table(conn, "api_sync_logs"):
        return {}
    try:
        row = conn.execute(
            "SELECT source,sync_type,started_at,finished_at,status,total_items "
            "FROM api_sync_logs WHERE lower(source) LIKE ? ORDER BY started_at DESC LIMIT 1",
            (f"%{source_like.lower()}%",),
        ).fetchone()
    except sqlite3.Error:
        return {}
    return dict(row) if row else {}


def _api_football_evidence(conn: sqlite3.Connection | None) -> dict[str, Any]:
    sync = {}
    if _table(conn, "api_football_live_sync_state"):
        try:
            row = conn.execute(
                "SELECT key,last_sync_at,status,fixtures_count,error "
                "FROM api_football_live_sync_state ORDER BY last_sync_at DESC LIMIT 1"
            ).fetchone()
            sync = dict(row) if row else {}
        except sqlite3.Error:
            sync = {}
    account = {}
    observed_at = ""
    if _table(conn, "api_exploitation_runs"):
        try:
            row = conn.execute(
                "SELECT finished_at,payload_json FROM api_exploitation_runs "
                "WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                account = _json(row["payload_json"]).get("account") or {}
                observed_at = str(row["finished_at"] or "")
        except sqlite3.Error:
            pass
    return {"sync": sync, "account": account if isinstance(account, dict) else {}, "account_observed_at": observed_at}


def _api_football_row(conn: sqlite3.Connection | None) -> dict[str, Any]:
    configured = _env_present("API_FOOTBALL_KEY", "API_FOOTBALL_API_KEY", "API_SPORTS_KEY", "APISPORTS_KEY")
    enabled = configured and _env_bool("ENABLE_API_FOOTBALL_PROVIDER", True)
    evidence = _api_football_evidence(conn)
    sync = evidence["sync"]
    account = evidence["account"]
    plan = _safe_text(account.get("plan") or "")
    active = account.get("active")
    status = _safe_text(sync.get("status") or "")
    if not configured:
        connection = "NOT_CONFIGURED"
    elif not enabled:
        connection = "DISABLED"
    elif any(token in status.upper() for token in ("RESTRICTED", "FAILURE", "ERROR")):
        connection = "RESTRICTED"
    elif status:
        connection = "OBSERVED"
    else:
        connection = "NO_CURRENT_EVIDENCE"
    if plan.lower() == "free":
        billing = "FREE_PLAN"
        billing_label = "Plan gratuito/restringido confirmado"
    elif active is False:
        billing = "INACTIVE_PLAN"
        billing_label = f"Plan inactivo{': ' + plan if plan else ''}"
    elif plan and plan.upper() != "INACCESSIBLE":
        billing = "PLAN_REPORTED"
        billing_label = f"Plan reportado por proveedor: {plan}"
    else:
        billing = "UNVERIFIED"
        billing_label = "Plan/pago no verificado actualmente"
    attention = (not configured) or connection in {"RESTRICTED", "DISABLED"} or billing in {"FREE_PLAN", "INACTIVE_PLAN"}
    return {
        "key": "api_football",
        "name": "API-Football / API-SPORTS",
        "role": "Directo, eventos y estadísticas",
        "configured": configured,
        "enabled": enabled,
        "connection_state": connection,
        "billing_state": billing,
        "billing_label": billing_label,
        "plan": plan or "Sin evidencia actual",
        "plan_active": active if isinstance(active, bool) else None,
        "plan_end": _safe_text(account.get("end") or ""),
        "quota": account.get("quota") if isinstance(account.get("quota"), dict) else {},
        "last_observed_at": evidence["account_observed_at"] or _safe_text(sync.get("last_sync_at") or ""),
        "last_status": status or "Sin observación",
        "cached_items": int(sync.get("fixtures_count") or 0),
        "attention": attention,
        "test_supported": True,
        "test_cost_note": "1 llamada al endpoint /status; no descarga partidos.",
    }


def _odds_row(conn: sqlite3.Connection | None) -> dict[str, Any]:
    configured = _env_present("THE_ODDS_API_KEY", "ODDS_API_KEY")
    enabled = configured and _env_bool("ENABLE_ODDS_API", True)
    state = _automation(conn, "odds_events_sync")
    quota = state.get("quota") if isinstance(state.get("quota"), dict) else {}
    status = _safe_text(state.get("status") or "")
    if not configured:
        connection = "NOT_CONFIGURED"
    elif not enabled:
        connection = "DISABLED"
    elif status in {"OK", "CACHE_REUSED"} or state.get("ok") is True:
        connection = "OBSERVED"
    elif status:
        connection = "PROVIDER_ERROR"
    else:
        connection = "NO_CURRENT_EVIDENCE"
    quota_seen = any(int(quota.get(key) or 0) > 0 for key in ("requests_remaining", "requests_used", "requests_last_total"))
    billing = "QUOTA_REPORTED" if quota_seen else "UNVERIFIED"
    billing_label = (
        "Autenticación/cuota observada; el endpoint no certifica el tipo de plan"
        if quota_seen else "Plan/pago no verificable desde la API guardada"
    )
    return {
        "key": "the_odds_api",
        "name": "The Odds API",
        "role": "Cuotas, mercados y bookmakers",
        "configured": configured,
        "enabled": enabled,
        "connection_state": connection,
        "billing_state": billing,
        "billing_label": billing_label,
        "plan": "No expuesto por este endpoint",
        "plan_active": None,
        "plan_end": "",
        "quota": quota,
        "last_observed_at": _safe_text(state.get("last_sync") or state.get("time") or state.get("_updated_at") or ""),
        "last_status": status or "Sin observación",
        "cached_items": int(state.get("processed") or state.get("cached_processed") or 0),
        "attention": (not configured) or connection in {"DISABLED", "PROVIDER_ERROR"},
        "test_supported": True,
        "test_cost_note": "1 llamada controlada a /sports para validar autenticación y cabeceras de cuota.",
    }


def _sportsdb_row(conn: sqlite3.Connection | None) -> dict[str, Any]:
    configured = _env_present("THESPORTSDB_KEY", "THESPORTSDB_API_KEY")
    enabled = configured and _env_bool("ENABLE_THESPORTSDB_PROVIDER", True)
    sync = _latest_sync(conn, "sportsdb")
    status = _safe_text(sync.get("status") or "")
    if not configured:
        connection = "NOT_CONFIGURED"
    elif not enabled:
        connection = "DISABLED"
    elif status.upper() in {"OK", "PARTIAL"}:
        connection = "OBSERVED"
    elif status:
        connection = "PROVIDER_ERROR"
    else:
        connection = "NO_CURRENT_EVIDENCE"
    return {
        "key": "thesportsdb",
        "name": "TheSportsDB",
        "role": "Calendario, resultados, equipos y escudos",
        "configured": configured,
        "enabled": enabled,
        "connection_state": connection,
        "billing_state": "UNVERIFIED",
        "billing_label": "Plan/pago no verificado por la integración actual",
        "plan": "No expuesto por la integración",
        "plan_active": None,
        "plan_end": "",
        "quota": {},
        "last_observed_at": _safe_text(sync.get("finished_at") or sync.get("started_at") or ""),
        "last_status": status or "Sin observación",
        "cached_items": int(sync.get("total_items") or 0),
        "attention": not configured or connection in {"DISABLED", "PROVIDER_ERROR"},
        "test_supported": True,
        "test_cost_note": "1 llamada de lectura de ligas; no modifica datos.",
    }


def _service_rows() -> list[dict[str, Any]]:
    return [
        {
            "name": "OpenAI / SHARK",
            "configured": _env_present("OPENAI_API_KEY"),
            "note": "Clave configurada" if _env_present("OPENAI_API_KEY") else "Sin clave configurada",
        },
        {
            "name": "Stripe",
            "configured": _env_present("STRIPE_SECRET_KEY"),
            "note": "Backend de pagos configurado" if _env_present("STRIPE_SECRET_KEY") else "Pagos sin clave backend",
        },
        {
            "name": "Telegram",
            "configured": _env_present("TELEGRAM_BOT_TOKEN") and _env_present("TELEGRAM_CHAT_ID"),
            "note": "Bot y destino configurados" if _env_present("TELEGRAM_BOT_TOKEN") and _env_present("TELEGRAM_CHAT_ID") else "Configuración incompleta",
        },
    ]


def provider_maintenance_snapshot(db_path: str | None) -> dict[str, Any]:
    """No-network snapshot suitable for page render."""
    conn = _connect_readonly(db_path)
    try:
        providers = [_api_football_row(conn), _odds_row(conn), _sportsdb_row(conn)]
    finally:
        if conn is not None:
            conn.close()
    attention = [item for item in providers if item.get("attention")]
    configured = sum(1 for item in providers if item.get("configured"))
    observed = sum(1 for item in providers if item.get("connection_state") == "OBSERVED")
    return {
        "ok": True,
        "generated_at": _now_iso(),
        "network_calls": 0,
        "writes": 0,
        "providers": providers,
        "services": _service_rows(),
        "configured_count": configured,
        "observed_count": observed,
        "attention_count": len(attention),
        "attention": [{"key": item["key"], "name": item["name"], "state": item["connection_state"], "billing": item["billing_state"]} for item in attention],
        "truth_contract": {
            "configured_is_not_paid": True,
            "page_render_calls_provider": False,
            "manual_test_calls": 1,
            "secrets_visible": False,
        },
    }


def _provider_error(exc: BaseException) -> dict[str, Any]:
    code = int(getattr(exc, "code", 0) or 0)
    return {
        "ok": False,
        "connected": False,
        "http_status": code,
        "error_class": type(exc).__name__[:80],
        "external_calls": 1,
        "secret_exposed": False,
    }


def _read_json(req: urllib.request.Request, timeout: int = 12) -> tuple[dict[str, Any] | list[Any], Any, int]:
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8", "replace"))
        return payload, response.headers, int(getattr(response, "status", 200) or 200)


def _test_api_football() -> dict[str, Any]:
    key = str(os.getenv("API_FOOTBALL_KEY") or os.getenv("API_FOOTBALL_API_KEY") or os.getenv("API_SPORTS_KEY") or os.getenv("APISPORTS_KEY") or "").strip()
    if not key:
        return {"ok": False, "connected": False, "status": "NOT_CONFIGURED", "external_calls": 0, "secret_exposed": False}
    req = urllib.request.Request(
        "https://v3.football.api-sports.io/status",
        headers={"x-apisports-key": key, "User-Agent": "NeMeSiS-SHARK-PRO/Maintenance"},
    )
    try:
        payload, headers, code = _read_json(req)
    except Exception as exc:
        return _provider_error(exc)
    payload = payload if isinstance(payload, dict) else {}
    response = payload.get("response") or {}
    if isinstance(response, list) and response and isinstance(response[0], dict):
        response = response[0]
    if not isinstance(response, dict):
        response = {}
    subscription = response.get("subscription") if isinstance(response.get("subscription"), dict) else {}
    requests = response.get("requests") if isinstance(response.get("requests"), dict) else {}
    plan = _safe_text(subscription.get("plan") or "")
    active = subscription.get("active")
    connected = code < 400 and not bool(payload.get("errors"))
    billing = "FREE_PLAN" if plan.lower() == "free" else "PLAN_REPORTED" if plan else "UNVERIFIED"
    return {
        "ok": connected,
        "connected": connected,
        "http_status": code,
        "status": "CONNECTED" if connected else "PROVIDER_REJECTED",
        "plan": plan or "No reportado",
        "plan_active": active if isinstance(active, bool) else None,
        "plan_end": _safe_text(subscription.get("end") or ""),
        "billing_state": billing,
        "quota": {
            "daily_limit": int(requests.get("limit_day") or 0),
            "daily_used": int(requests.get("current") or 0),
            "requests_remaining_header": int(headers.get("x-ratelimit-requests-remaining") or 0),
        },
        "external_calls": 1,
        "secret_exposed": False,
        "checked_at": _now_iso(),
    }


def _test_the_odds_api() -> dict[str, Any]:
    key = str(os.getenv("THE_ODDS_API_KEY") or os.getenv("ODDS_API_KEY") or "").strip()
    if not key:
        return {"ok": False, "connected": False, "status": "NOT_CONFIGURED", "external_calls": 0, "secret_exposed": False}
    query = urllib.parse.urlencode({"apiKey": key})
    req = urllib.request.Request(
        "https://api.the-odds-api.com/v4/sports/?" + query,
        headers={"User-Agent": "NeMeSiS-SHARK-PRO/Maintenance"},
    )
    try:
        payload, headers, code = _read_json(req)
    except Exception as exc:
        return _provider_error(exc)
    connected = code < 400 and isinstance(payload, list)
    return {
        "ok": connected,
        "connected": connected,
        "http_status": code,
        "status": "CONNECTED" if connected else "PROVIDER_REJECTED",
        "sports_visible": len(payload) if isinstance(payload, list) else 0,
        "billing_state": "QUOTA_REPORTED" if connected else "UNVERIFIED",
        "billing_note": "La conexión y la cuota se verifican; este endpoint no certifica el nombre del plan.",
        "quota": {
            "requests_remaining": int(headers.get("x-requests-remaining") or 0),
            "requests_used": int(headers.get("x-requests-used") or 0),
            "requests_last": int(headers.get("x-requests-last") or 0),
        },
        "external_calls": 1,
        "secret_exposed": False,
        "checked_at": _now_iso(),
    }


def _test_thesportsdb() -> dict[str, Any]:
    key = str(os.getenv("THESPORTSDB_KEY") or os.getenv("THESPORTSDB_API_KEY") or "").strip()
    if not key:
        return {"ok": False, "connected": False, "status": "NOT_CONFIGURED", "external_calls": 0, "secret_exposed": False}
    url = "https://www.thesportsdb.com/api/v1/json/" + urllib.parse.quote(key) + "/search_all_leagues.php?" + urllib.parse.urlencode({"c": "England", "s": "Soccer"})
    req = urllib.request.Request(url, headers={"User-Agent": "NeMeSiS-SHARK-PRO/Maintenance"})
    try:
        payload, _headers, code = _read_json(req)
    except Exception as exc:
        return _provider_error(exc)
    leagues = payload.get("countries") if isinstance(payload, dict) else None
    connected = code < 400 and isinstance(leagues, list)
    return {
        "ok": connected,
        "connected": connected,
        "http_status": code,
        "status": "CONNECTED" if connected else "PROVIDER_REJECTED",
        "records_visible": len(leagues or []),
        "billing_state": "UNVERIFIED",
        "billing_note": "La integración confirma acceso, no el tipo de plan contratado.",
        "external_calls": 1,
        "secret_exposed": False,
        "checked_at": _now_iso(),
    }


def test_provider_connection(provider: str) -> dict[str, Any]:
    """Exactly one explicit provider request, or zero when not configured."""
    key = str(provider or "").strip().lower()
    if key == "api_football":
        return {"provider": key, **_test_api_football()}
    if key == "the_odds_api":
        return {"provider": key, **_test_the_odds_api()}
    if key == "thesportsdb":
        return {"provider": key, **_test_thesportsdb()}
    return {
        "provider": key,
        "ok": False,
        "connected": False,
        "status": "UNSUPPORTED_PROVIDER",
        "external_calls": 0,
        "secret_exposed": False,
    }


__all__ = ["PROVIDERS", "provider_maintenance_snapshot", "test_provider_connection"]
