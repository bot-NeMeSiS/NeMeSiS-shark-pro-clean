"""Safe API-SPORTS/API-Football provider facade for V847.

This module does not replace the existing API-Football live tracker. It wraps
the paid provider with conservative status, cache and credit-guard helpers so
runtime/admin can show the truth without spending credits on every page render.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Mapping

API_SPORTS_BASE_URL = "https://v3.football.api-sports.io"
DEFAULT_TTL_SECONDS = 900
_MEMORY_CACHE: dict[str, dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, "")).strip() or default)
    except Exception:
        return default


def _provider_key() -> str:
    return (
        os.getenv("API_FOOTBALL_KEY")
        or os.getenv("API_FOOTBALL_API_KEY")
        or os.getenv("API_SPORTS_KEY")
        or os.getenv("APISPORTS_KEY")
        or ""
    )


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    try:
        return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())
    except sqlite3.Error:
        return False


def _count(conn: sqlite3.Connection, table: str) -> int:
    if not _table_exists(conn, table):
        return 0
    try:
        return int((conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone() or [0])[0] or 0)
    except sqlite3.Error:
        return 0


def _one_value(conn: sqlite3.Connection, table: str, column: str, order: str = "rowid") -> str:
    if not _table_exists(conn, table):
        return ""
    try:
        row = conn.execute(f"SELECT {column} FROM {table} ORDER BY {order} DESC LIMIT 1").fetchone()
        return str(row[0] or "") if row else ""
    except sqlite3.Error:
        return ""


def is_api_sports_configured() -> bool:
    return bool(_provider_key())


def usage_guard() -> dict[str, Any]:
    return {
        "enabled": True,
        "cache_first": True,
        "no_page_render_calls": True,
        "dry_run_supported": True,
        "timeout_seconds": _env_int("API_SPORTS_TIMEOUT_SECONDS", 12),
        "default_ttl_seconds": _env_int("API_SPORTS_CACHE_TTL_SECONDS", DEFAULT_TTL_SECONDS),
        "daily_call_budget": _env_int("API_FOOTBALL_DAILY_CALL_BUDGET", _env_int("API_SPORTS_DAILY_CALL_BUDGET", 100)),
        "network_enabled": _env_bool("ENABLE_API_SPORTS_NETWORK_CALLS", True),
    }


SAFE_PROVIDER_EMPTY_STATES = {
    "no_real_data": "Sin datos reales",
    "waiting_provider": "Esperando proveedor",
    "pending_odds": "Cuotas pendientes",
    "pending_result": "Resultado pendiente",
    "no_active_picks": "Sin picks activos",
    "not_enough_data": "No hay datos suficientes",
    "not_configured": "API-SPORTS no configurada",
}


def sanitize_provider_error(value: Any, limit: int = 220) -> str:
    text = str(value or "")[: int(limit)]
    text = text.replace("\r", "").replace("\n", "").replace("\\r", "").replace("\\n", "").strip()
    if "Invalid header value" in text:
        return "Invalid header value histórico saneado; validar cabeceras tras deploy."
    return text


def get_api_sports_status(db_path: str | None = None) -> dict[str, Any]:
    configured = is_api_sports_configured()
    enabled = configured and _env_bool("ENABLE_API_FOOTBALL_PROVIDER", True)
    provider_active = "api-sports/api-football" if enabled else ("configured_disabled" if configured else "not_configured")
    summary = {
        "ok": True,
        "provider": "API-SPORTS / API-Football",
        "provider_active": provider_active,
        "api_sports_configured": configured,
        "api_football_configured": bool(os.getenv("API_FOOTBALL_KEY") or os.getenv("API_FOOTBALL_API_KEY")),
        "api_sports_provider_available": enabled,
        "api_sports_cache_enabled": True,
        "api_sports_credit_guard_enabled": True,
        "last_sync": "",
        "last_error": "",
        "fixtures_cached": 0,
        "live_cached": 0,
        "events_cached": 0,
        "stats_cached": 0,
        "tables_detected": [],
        "usage_guard": usage_guard(),
    }
    if not db_path:
        return summary
    try:
        conn = _connect(db_path)
        try:
            tables = [
                "api_football_live_sync_state",
                "api_football_live_snapshots",
                "api_football_live_events",
                "api_football_live_stats",
                "api_football_fixture_index",
                "api_exploitation_runs",
            ]
            summary["tables_detected"] = [table for table in tables if _table_exists(conn, table)]
            summary["live_cached"] = _count(conn, "api_football_live_snapshots")
            summary["events_cached"] = _count(conn, "api_football_live_events")
            summary["stats_cached"] = _count(conn, "api_football_live_stats")
            summary["fixtures_cached"] = max(_count(conn, "api_football_fixture_index"), summary["live_cached"])
            sync_times = [
                _one_value(conn, "api_football_live_sync_state", "last_sync_at", "last_sync_at"),
                _one_value(conn, "api_exploitation_runs", "finished_at", "id"),
            ]
            summary["last_sync"] = next((item for item in sync_times if item), "")
            errors = [
                _one_value(conn, "api_football_live_sync_state", "error", "last_sync_at"),
                _one_value(conn, "api_exploitation_runs", "error_message", "id"),
            ]
            summary["last_error"] = sanitize_provider_error(next((item for item in errors if item), ""))
        finally:
            conn.close()
    except Exception as exc:
        summary["ok"] = False
        summary["last_error"] = sanitize_provider_error(exc)
    return summary


def _cache_get(cache_key: str) -> dict[str, Any] | None:
    item = _MEMORY_CACHE.get(cache_key)
    if not item:
        return None
    if float(item.get("expires_at") or 0) < time.time():
        _MEMORY_CACHE.pop(cache_key, None)
        return None
    return dict(item.get("payload") or {})


def _cache_set(cache_key: str, payload: Mapping[str, Any], ttl: int) -> None:
    _MEMORY_CACHE[cache_key] = {"expires_at": time.time() + max(1, ttl), "payload": dict(payload)}


def api_sports_safe_request(
    endpoint: str,
    params: Mapping[str, Any] | None = None,
    cache_key: str | None = None,
    ttl: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    guard = usage_guard()
    clean_endpoint = endpoint.strip("/")
    key = cache_key or f"{clean_endpoint}:{json.dumps(dict(params or {}), sort_keys=True, default=str)}"
    cached = _cache_get(key)
    if cached:
        cached["cache_hit"] = True
        return cached
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "cache_hit": False,
            "endpoint": clean_endpoint,
            "params": dict(params or {}),
            "would_call_provider": is_api_sports_configured() and guard["network_enabled"],
            "usage_guard": guard,
        }
    if not is_api_sports_configured():
        return {"ok": False, "status": "not_configured", "error": "API-SPORTS no configurada.", "usage_guard": guard}
    if not guard["network_enabled"]:
        return {"ok": False, "status": "network_disabled", "error": "Llamadas API desactivadas por guard.", "usage_guard": guard}
    query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v not in (None, "")})
    url = f"{API_SPORTS_BASE_URL.rstrip('/')}/{clean_endpoint}"
    if query:
        url += "?" + query
    req = urllib.request.Request(url, headers={"x-apisports-key": _provider_key(), "User-Agent": "NeMeSiS-SHARK-PRO/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=int(guard["timeout_seconds"])) as resp:
            payload = json.loads(resp.read().decode("utf-8", "replace"))
        result = {
            "ok": not bool(payload.get("errors")),
            "endpoint": clean_endpoint,
            "cache_hit": False,
            "response": payload.get("response") or [],
            "results": payload.get("results") or 0,
            "errors": payload.get("errors") or {},
            "paging": payload.get("paging") or {},
            "synced_at": _now_iso(),
            "usage_guard": guard,
        }
        _cache_set(key, result, ttl or int(guard["default_ttl_seconds"]))
        return result
    except Exception as exc:  # pragma: no cover - network dependent
        return {"ok": False, "endpoint": clean_endpoint, "error": str(exc)[:260], "usage_guard": guard}


def sync_api_sports_fixtures(days: int = 2, dry_run: bool = True) -> dict[str, Any]:
    return api_sports_safe_request("fixtures", {"next": max(1, int(days)), "timezone": "Europe/Madrid"}, "fixtures-next", 900, dry_run=dry_run)


def sync_api_sports_live(dry_run: bool = True) -> dict[str, Any]:
    return api_sports_safe_request("fixtures", {"live": "all", "timezone": "Europe/Madrid"}, "fixtures-live", 120, dry_run=dry_run)


def get_cached_api_sports_matches(db_path: str | None = None) -> list[dict[str, Any]]:
    if not db_path:
        return []
    try:
        conn = _connect(db_path)
        try:
            if not _table_exists(conn, "api_football_fixture_index"):
                return []
            rows = conn.execute("SELECT * FROM api_football_fixture_index ORDER BY kickoff_iso DESC LIMIT 40").fetchall()
            return [{key: row[key] for key in row.keys()} for row in rows]
        finally:
            conn.close()
    except Exception:
        return []


def get_cached_api_sports_live(db_path: str | None = None) -> list[dict[str, Any]]:
    if not db_path:
        return []
    try:
        conn = _connect(db_path)
        try:
            if not _table_exists(conn, "api_football_live_snapshots"):
                return []
            rows = conn.execute("SELECT * FROM api_football_live_snapshots ORDER BY last_synced_at DESC LIMIT 40").fetchall()
            return [{key: row[key] for key in row.keys()} for row in rows]
        finally:
            conn.close()
    except Exception:
        return []


def get_cached_api_sports_provider_summary(db_path: str | None = None) -> dict[str, Any]:
    return get_api_sports_status(db_path)


def explain_api_sports_provider_state(db_path: str | None = None) -> dict[str, Any]:
    status = get_api_sports_status(db_path)
    if not status["api_sports_configured"]:
        label = "API-SPORTS no configurada"
        message = "Render debe incluir API_FOOTBALL_KEY o API_SPORTS_KEY para activar fixtures/live reales."
    elif status["last_error"]:
        label = "Esperando proveedor"
        message = "La clave existe, pero el último estado del proveedor tiene error seguro. Se mantiene caché/fallback."
    elif status["fixtures_cached"] or status["live_cached"]:
        label = "Proveedor activo con caché"
        message = "La app tiene datos API-SPORTS/API-Football cacheados y no necesita llamar al proveedor en cada render."
    else:
        label = "Proveedor configurado sin caché visible"
        message = "La clave está configurada, pero aún no hay fixtures/live cacheados en las tablas detectadas."
    return {"label": label, "message": message, "status": status}
