"""V850 live match presentation helpers.

Pure/cache-first helpers for live cards, match detail and provider state. This
module never performs provider calls during render and never writes SQLite.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from engines.v935_launch_trust_engine import match_status_truth


LIVE_STATUS_MAP = {
    "1H": "En directo",
    "2H": "En directo",
    "HT": "Descanso",
    "LIVE": "En directo",
    "ET": "Prórroga",
    "BT": "Descanso",
    "P": "Penaltis",
    "FT": "Finalizado",
    "AET": "Finalizado",
    "PEN": "Finalizado",
    "NS": "Próximo",
    "TBD": "Hora pendiente",
    "PST": "Aplazado",
    "CANC": "Suspendido",
    "SUSP": "Suspendido",
    "ABD": "Suspendido",
}

LIVE_EMPTY_STATES = {
    "no_live": "Sin directos reales",
    "waiting_provider": "Esperando proveedor",
    "minute_pending": "Minuto no disponible",
    "score_pending": "Resultado pendiente",
    "no_real_data": "Sin datos reales",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _first(match: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = match.get(key)
        if value not in (None, "", "None", "null", "undefined"):
            return value
    return ""


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    try:
        return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())
    except sqlite3.Error:
        return False


def _public_live_truth(match: dict[str, Any] | None) -> dict[str, Any]:
    """Canonical fail-closed truth for public LIVE publication.

    API-Football live snapshots persist between syncs.  Their freshness clock is
    ``last_synced_at``; expose it through the canonical V935 timestamp names so
    a fixture that disappears from the provider's LIVE response cannot remain
    publicly LIVE forever.
    """
    item = dict(match or {})
    sync_timestamp = _first(
        item,
        "live_updated_at",
        "provider_updated_at",
        "last_synced_at",
        "updated_at",
    )
    if sync_timestamp:
        item.setdefault("live_updated_at", sync_timestamp)
        item.setdefault("provider_updated_at", sync_timestamp)
    return match_status_truth(item)


def _keep_public_live(match: dict[str, Any] | None) -> bool:
    truth = _public_live_truth(match)
    return bool(truth.get("is_live") and not truth.get("status_conflict") and not truth.get("is_stale"))


def get_match_status_label(match: dict[str, Any] | None) -> str:
    match = dict(match or {})
    lifecycle = _public_live_truth(match).get("lifecycle")
    return {
        "LIVE": "En directo",
        "HALFTIME": "Descanso",
        "FINISHED": "Finalizado",
        "ARCHIVED": "Finalizado",
        "RESULT_PENDING": "Resultado pendiente",
        "POSTPONED": "Aplazado",
        "CANCELLED": "Cancelado",
        "ABANDONED": "Abandonado",
        "STALE": "Datos retrasados",
        "INCOMPLETE": "Estado pendiente",
        "UPCOMING": "Próximo",
    }.get(str(lifecycle), "Estado pendiente")


def get_match_minute_label(match: dict[str, Any] | None) -> str:
    match = dict(match or {})
    status = get_match_status_label(match)
    if status not in {"En directo", "Descanso"}:
        return ""
    minute = _text(_first(match, "minute", "elapsed", "live_minute"))
    extra = _text(_first(match, "extra", "stoppage_time"))
    minute = minute.strip("'\u2019")
    if minute:
        if minute.isdigit() and 0 < int(minute) <= 130:
            return f"{minute}+{extra}'" if extra and extra.isdigit() else f"{minute}'"
        if re.fullmatch(r"(?:[1-9]\d?|1[0-2]\d)\+\d{1,2}", minute):
            return f"{minute}'"
    if status == "Descanso":
        return "Descanso"
    return "En directo"


def get_score_label(match: dict[str, Any] | None) -> str:
    match = dict(match or {})
    score = _text(_first(match, "score", "safe_score", "live_score_label"))
    if score and score.lower() not in {"vs", "none", "null", "undefined", "pendiente"}:
        return score
    home_score = _first(match, "home_score", "goals_home", "home_goals")
    away_score = _first(match, "away_score", "goals_away", "away_goals")
    if home_score not in ("", None) or away_score not in ("", None):
        return f"{home_score if home_score not in ('', None) else 0}-{away_score if away_score not in ('', None) else 0}"
    status = get_match_status_label(match)
    if status in {"En directo", "Descanso", "Finalizado"}:
        return "Resultado pendiente"
    return "VS"


def normalize_live_match(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(raw or {})
    fixture = raw.get("fixture") or {}
    league = raw.get("league") or {}
    teams = raw.get("teams") or {}
    goals = raw.get("goals") or {}
    home = teams.get("home") if isinstance(teams, dict) else {}
    away = teams.get("away") if isinstance(teams, dict) else {}
    status = fixture.get("status") if isinstance(fixture, dict) else {}
    sync_timestamp = _first(raw, "live_updated_at", "provider_updated_at", "last_synced_at", "updated_at")
    item = dict(raw)
    item.update(
        {
            "id": _first(raw, "id", "match_id", "fixture_id") or fixture.get("id"),
            "external_id": _first(raw, "external_id", "fixture_id") or fixture.get("id"),
            "home_team": _first(raw, "home_team", "safe_home") or (home or {}).get("name"),
            "away_team": _first(raw, "away_team", "safe_away") or (away or {}).get("name"),
            "home_logo": _first(raw, "home_logo") or (home or {}).get("logo"),
            "away_logo": _first(raw, "away_logo") or (away or {}).get("logo"),
            "competition_name": _first(raw, "competition_name", "league_name") or league.get("name"),
            "league_logo": _first(raw, "league_logo") or league.get("logo"),
            "country": _first(raw, "country") or league.get("country"),
            "status": _first(raw, "status") or (status or {}).get("short") or (status or {}).get("long"),
            "minute": _first(raw, "minute") or (status or {}).get("elapsed"),
            "home_score": _first(raw, "home_score") or goals.get("home"),
            "away_score": _first(raw, "away_score") or goals.get("away"),
            "kickoff_iso": _first(raw, "kickoff_iso") or fixture.get("date"),
            "provider": _first(raw, "provider", "source") or "api-sports-cache",
            "live_updated_at": sync_timestamp,
            "provider_updated_at": sync_timestamp,
        }
    )
    item["v850_status_label"] = get_match_status_label(item)
    item["v850_minute_label"] = get_match_minute_label(item)
    item["v850_score_label"] = get_score_label(item)
    return item


def build_live_card_payload(match: dict[str, Any] | None) -> dict[str, Any]:
    item = normalize_live_match(match)
    truth = _public_live_truth(item)
    status = item["v850_status_label"]
    score = item["v850_score_label"]
    minute = item["v850_minute_label"]
    return {
        "id": item.get("id") or "",
        "home": _text(_first(item, "safe_home", "home_team")) or "Local",
        "away": _text(_first(item, "safe_away", "away_team")) or "Visitante",
        "competition": _text(_first(item, "live_competition_display", "competition_name", "league_name")) or "Competición",
        "status_label": status,
        "minute_label": minute,
        "score_label": score,
        "is_live": bool(truth.get("is_live") and not truth.get("status_conflict") and not truth.get("is_stale")),
        "is_finished": status == "Finalizado",
        "is_pending": score in {"VS", "Resultado pendiente"},
        "home_logo": _text(item.get("home_logo")),
        "away_logo": _text(item.get("away_logo")),
        "league_logo": _text(item.get("league_logo")),
        "provider": _text(_first(item, "provider", "source")) or "cache",
        "data_state": "Datos live reales" if truth.get("is_live") else "Datos retrasados" if truth.get("is_stale") else "Esperando proveedor",
        "status_contract": truth.get("contract"),
        "status_conflict": bool(truth.get("status_conflict")),
        "is_stale": bool(truth.get("is_stale")),
        "stale_reason": truth.get("stale_reason") or "",
        "live_age_seconds": truth.get("live_age_seconds"),
        "detail_url": f"/match/{item.get('id')}" if item.get("id") else "/partidos",
        "shark_url": f"/shark?match={item.get('id')}" if item.get("id") else "/shark",
    }


def get_live_matches_cached(db_path: str | None = None, limit: int = 40) -> list[dict[str, Any]]:
    """Return only fresh, truth-confirmed LIVE fixtures from local cache.

    Stale snapshot rows are intentionally retained in SQLite for diagnostics;
    this read path simply prevents them from leaking onto public LIVE surfaces.
    """
    if not db_path:
        return []
    try:
        conn = sqlite3.connect(db_path, timeout=0.2)
        conn.row_factory = sqlite3.Row
        try:
            if _table_exists(conn, "api_football_live_snapshots"):
                rows = conn.execute(
                    "SELECT * FROM api_football_live_snapshots ORDER BY last_synced_at DESC LIMIT ?",
                    (max(int(limit) * 3, int(limit)),),
                ).fetchall()
                items = [normalize_live_match(dict(row)) for row in rows]
                return [item for item in items if _keep_public_live(item)][: int(limit)]
            if _table_exists(conn, "matches"):
                rows = conn.execute(
                    """SELECT * FROM matches
                       WHERE lower(COALESCE(status,'')) LIKE '%live%'
                          OR lower(COALESCE(status,'')) LIKE '%directo%'
                          OR COALESCE(minute,'')!=''
                       ORDER BY match_date DESC, kickoff_time DESC LIMIT ?""",
                    (max(int(limit) * 3, int(limit)),),
                ).fetchall()
                items = [normalize_live_match(dict(row)) for row in rows]
                return [item for item in items if _keep_public_live(item)][: int(limit)]
        finally:
            conn.close()
    except Exception:
        return []
    return []


def should_refresh_live_cache(last_sync: str | None = "", ttl_seconds: int = 120) -> bool:
    if not last_sync:
        return True
    try:
        raw = str(last_sync).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() > int(ttl_seconds)
    except Exception:
        return True


def live_cache_summary(db_path: str | None = None) -> dict[str, Any]:
    items = get_live_matches_cached(db_path, limit=80)
    live_count = sum(1 for item in items if build_live_card_payload(item).get("is_live"))
    return {
        "ok": True,
        "cached_total": len(items),
        "cached_live": live_count,
        "empty_state": "Sin directos reales" if not live_count else "",
        "cache_first": True,
        "no_render_calls": True,
        "stale_publication_blocked": True,
    }


def explain_live_data_state(db_path: str | None = None) -> dict[str, Any]:
    summary = live_cache_summary(db_path)
    if summary["cached_live"]:
        return {"label": "Directo cacheado", "message": "Hay partidos live reales y recientes en caché.", "summary": summary}
    if summary["cached_total"]:
        return {"label": "Sin directos reales", "message": "Hay fixtures cacheados, pero ninguno tiene evidencia LIVE reciente.", "summary": summary}
    return {"label": "Esperando proveedor", "message": "No hay cache live reciente disponible. La app no inventa marcador ni minuto.", "summary": summary}


def get_live_matches_from_api_sports_safe(dry_run: bool = True) -> dict[str, Any]:
    from engines.api_sports_provider_engine import sync_api_sports_live

    result = sync_api_sports_live(dry_run=dry_run)
    response = result.get("response") or []
    return {
        "ok": bool(result.get("ok")),
        "dry_run": bool(result.get("dry_run", dry_run)),
        "matches": [normalize_live_match(item) for item in response],
        "usage_guard": result.get("usage_guard") or {},
        "status": result.get("status") or "",
        "error": result.get("error") or "",
    }
