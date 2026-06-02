"""V596 - capa profesional de proveedores de datos deportivos.

Esta capa no sustituye TheSportsDB ni The Odds API. Normaliza el estado de las
fuentes disponibles y deja preparada la aplicación para activar API-Football,
Sportmonks o Sportradar desde Render sin rehacer la app.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

PROVIDER_LABELS = {
    "thesportsdb": "TheSportsDB",
    "api_football": "API-Football",
    "sportmonks": "Sportmonks",
    "sportradar": "Sportradar",
    "the_odds_api": "The Odds API",
}

PROVIDER_FEATURES = {
    "thesportsdb": ["calendario", "resultados", "equipos", "escudos", "ligas", "highlights", "eventos"],
    "api_football": ["marcador en directo", "minuto real", "eventos", "alineaciones", "estadísticas", "clasificaciones", "calendario"],
    "sportmonks": ["marcador en directo", "eventos", "alineaciones", "estadísticas", "clasificaciones", "jugadores", "históricos"],
    "sportradar": ["datos enterprise", "live avanzado", "estadísticas profundas", "calendario", "eventos", "alineaciones"],
    "the_odds_api": ["cuotas", "mercados", "bookmakers", "value", "comparativa de precios"],
}

PROVIDER_ENV_KEYS = {
    "thesportsdb": ["THESPORTSDB_KEY", "THESPORTSDB_API_KEY"],
    "api_football": ["API_FOOTBALL_KEY", "API_FOOTBALL_API_KEY"],
    "sportmonks": ["SPORTMONKS_API_KEY", "SPORTMONKS_TOKEN"],
    "sportradar": ["SPORTRADAR_API_KEY"],
    "the_odds_api": ["THE_ODDS_API_KEY"],
}

DEFAULT_PROVIDER_ORDER = ["thesportsdb", "api_football", "sportmonks", "sportradar"]
DEFAULT_PRIMARY_PROVIDER = "thesportsdb"

NORMALIZED_MATCH_FIELDS = [
    "external_id", "provider", "league_name", "league_id", "season", "match_date",
    "kickoff", "status", "minute", "home_team", "away_team", "home_score",
    "away_score", "home_logo", "away_logo", "stadium", "country", "raw_payload",
]

NORMALIZED_EVENT_FIELDS = [
    "external_match_id", "provider", "minute", "event_type", "team_name", "player_name",
    "assist_name", "detail", "raw_payload",
]

NORMALIZED_LINEUP_FIELDS = [
    "external_match_id", "provider", "team_name", "formation", "player_name",
    "position", "shirt_number", "is_starting", "raw_payload",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _first_env(keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        value = os.getenv(key)
        if value:
            return key
    return None


def _json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        return json.dumps({"value": str(value)}, ensure_ascii=False)


def provider_order() -> List[str]:
    raw = os.getenv("FOOTBALL_DATA_PROVIDER_ORDER") or os.getenv("DATA_PROVIDER_ORDER") or ""
    if raw.strip():
        order = [item.strip().lower().replace("-", "_") for item in raw.split(",") if item.strip()]
        return [item for item in order if item in PROVIDER_LABELS]
    primary = primary_provider()
    order = [primary] + [p for p in DEFAULT_PROVIDER_ORDER if p != primary]
    return order


def primary_provider() -> str:
    raw = (os.getenv("PRIMARY_FOOTBALL_DATA_PROVIDER") or DEFAULT_PRIMARY_PROVIDER).strip().lower().replace("-", "_")
    return raw if raw in PROVIDER_LABELS else DEFAULT_PRIMARY_PROVIDER


def provider_status(provider: str) -> Dict[str, Any]:
    keys = PROVIDER_ENV_KEYS.get(provider, [])
    active_key = _first_env(keys)
    enabled = _env_flag(f"ENABLE_{provider.upper()}_PROVIDER", default=provider in {"thesportsdb", "the_odds_api"})
    configured = bool(active_key) or provider == "thesportsdb" and bool(_first_env(PROVIDER_ENV_KEYS["thesportsdb"]))
    return {
        "provider": provider,
        "name": PROVIDER_LABELS.get(provider, provider),
        "enabled": enabled,
        "configured": configured,
        "active_key": active_key or "",
        "env_keys": keys,
        "features": PROVIDER_FEATURES.get(provider, []),
        "role": "cuotas" if provider == "the_odds_api" else "datos deportivos",
        "priority": provider_order().index(provider) + 1 if provider in provider_order() else 99,
    }


def ensure_data_provider_schema(db_path: str) -> Dict[str, Any]:
    conn = _connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS data_provider_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                matches_found INTEGER DEFAULT 0,
                events_found INTEGER DEFAULT 0,
                lineups_found INTEGER DEFAULT 0,
                standings_found INTEGER DEFAULT 0,
                error_message TEXT,
                meta_json TEXT
            );
            CREATE TABLE IF NOT EXISTS data_provider_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                cache_key TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                external_id TEXT,
                payload_json TEXT,
                normalized_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(provider, cache_key)
            );
            CREATE TABLE IF NOT EXISTS data_provider_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                external_id TEXT NOT NULL,
                internal_type TEXT NOT NULL,
                internal_id TEXT,
                confidence INTEGER DEFAULT 70,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(provider, external_id, internal_type)
            );
            CREATE TABLE IF NOT EXISTS provider_health_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                primary_provider TEXT,
                fallback_order_json TEXT,
                configured_providers INTEGER DEFAULT 0,
                enabled_providers INTEGER DEFAULT 0,
                ready_score INTEGER DEFAULT 0,
                payload_json TEXT
            );
            """
        )
        conn.commit()
        return {"ok": True, "schema": "ready"}
    finally:
        conn.close()


def normalize_match(provider: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Devuelve un contrato común para partidos aunque la fuente sea distinta."""
    provider = (provider or "unknown").lower().replace("-", "_")
    home = payload.get("home_team") or payload.get("strHomeTeam") or payload.get("home") or payload.get("localteam_name")
    away = payload.get("away_team") or payload.get("strAwayTeam") or payload.get("away") or payload.get("visitorteam_name")
    return {
        "external_id": str(payload.get("id") or payload.get("idEvent") or payload.get("fixture_id") or payload.get("external_id") or ""),
        "provider": provider,
        "league_name": payload.get("league_name") or payload.get("strLeague") or payload.get("league") or "",
        "league_id": str(payload.get("league_id") or payload.get("idLeague") or ""),
        "season": payload.get("season") or payload.get("strSeason") or "",
        "match_date": payload.get("match_date") or payload.get("dateEvent") or payload.get("date") or "",
        "kickoff": payload.get("kickoff") or payload.get("strTimestamp") or payload.get("timeEvent") or "",
        "status": payload.get("status") or payload.get("strStatus") or payload.get("statusShort") or "",
        "minute": payload.get("minute") or payload.get("intTime") or "",
        "home_team": home or "Local",
        "away_team": away or "Visitante",
        "home_score": payload.get("home_score") if payload.get("home_score") is not None else payload.get("intHomeScore"),
        "away_score": payload.get("away_score") if payload.get("away_score") is not None else payload.get("intAwayScore"),
        "home_logo": payload.get("home_logo") or payload.get("strHomeTeamBadge") or "",
        "away_logo": payload.get("away_logo") or payload.get("strAwayTeamBadge") or "",
        "stadium": payload.get("stadium") or payload.get("strVenue") or "",
        "country": payload.get("country") or payload.get("strCountry") or "",
        "raw_payload": _json(payload),
    }


def normalize_event(provider: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "external_match_id": str(payload.get("external_match_id") or payload.get("idEvent") or payload.get("fixture_id") or ""),
        "provider": (provider or "unknown").lower().replace("-", "_"),
        "minute": payload.get("minute") or payload.get("intTime") or "",
        "event_type": payload.get("event_type") or payload.get("type") or payload.get("strEvent") or "evento",
        "team_name": payload.get("team_name") or payload.get("strTeam") or "",
        "player_name": payload.get("player_name") or payload.get("strPlayer") or "",
        "assist_name": payload.get("assist_name") or payload.get("strAssist") or "",
        "detail": payload.get("detail") or payload.get("strDescriptionEN") or "",
        "raw_payload": _json(payload),
    }


def record_provider_run(db_path: str, provider: str, action: str, status: str = "ok", **meta: Any) -> Dict[str, Any]:
    ensure_data_provider_schema(db_path)
    conn = _connect(db_path)
    now = _now_iso()
    try:
        conn.execute(
            """
            INSERT INTO data_provider_runs(provider, action, status, started_at, finished_at, matches_found, events_found, lineups_found, standings_found, error_message, meta_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider,
                action,
                status,
                now,
                now,
                int(meta.get("matches_found", 0) or 0),
                int(meta.get("events_found", 0) or 0),
                int(meta.get("lineups_found", 0) or 0),
                int(meta.get("standings_found", 0) or 0),
                str(meta.get("error_message") or ""),
                _json(meta),
            ),
        )
        conn.commit()
        return {"ok": True, "provider": provider, "action": action, "status": status, "meta": meta}
    finally:
        conn.close()


def data_provider_summary(db_path: str) -> Dict[str, Any]:
    ensure_data_provider_schema(db_path)
    providers = [provider_status(p) for p in ["thesportsdb", "api_football", "sportmonks", "sportradar", "the_odds_api"]]
    configured = sum(1 for item in providers if item["configured"])
    enabled = sum(1 for item in providers if item["enabled"])
    primary = primary_provider()
    order = provider_order()
    live_ready = any(item["configured"] and item["provider"] in {"api_football", "sportmonks", "sportradar"} for item in providers)
    odds_ready = bool(provider_status("the_odds_api")["configured"])
    sportsdb_ready = bool(provider_status("thesportsdb")["configured"])
    ready_score = 25
    if sportsdb_ready:
        ready_score += 20
    if odds_ready:
        ready_score += 20
    if live_ready:
        ready_score += 25
    if enabled >= 2:
        ready_score += 10
    ready_score = min(100, ready_score)

    conn = _connect(db_path)
    try:
        runs = [dict(r) for r in conn.execute("SELECT * FROM data_provider_runs ORDER BY id DESC LIMIT 8").fetchall()]
        cache_total = conn.execute("SELECT COUNT(*) AS total FROM data_provider_cache").fetchone()["total"]
        mappings_total = conn.execute("SELECT COUNT(*) AS total FROM data_provider_mapping").fetchone()["total"]
        payload = {
            "ok": True,
            "primary_provider": primary,
            "provider_order": order,
            "providers": providers,
            "configured_providers": configured,
            "enabled_providers": enabled,
            "live_ready": live_ready,
            "odds_ready": odds_ready,
            "sportsdb_ready": sportsdb_ready,
            "ready_score": ready_score,
            "cache_total": cache_total,
            "mappings_total": mappings_total,
            "recent_runs": runs,
            "normalized_contracts": {
                "match": NORMALIZED_MATCH_FIELDS,
                "event": NORMALIZED_EVENT_FIELDS,
                "lineup": NORMALIZED_LINEUP_FIELDS,
            },
            "recommendation": provider_recommendation(live_ready, sportsdb_ready, odds_ready),
            "legal_note": "Usar APIs, feeds autorizados y caché propia. Evitar scraping de webs oficiales o apps de terceros sin licencia clara.",
        }
        conn.execute(
            """
            INSERT INTO provider_health_snapshots(created_at, primary_provider, fallback_order_json, configured_providers, enabled_providers, ready_score, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (_now_iso(), primary, _json(order), configured, enabled, ready_score, _json(payload)),
        )
        conn.commit()
        return payload
    finally:
        conn.close()


def provider_recommendation(live_ready: bool, sportsdb_ready: bool, odds_ready: bool) -> str:
    if live_ready and sportsdb_ready and odds_ready:
        return "Capa profesional preparada: datos live especializados, enriquecimiento TheSportsDB y cuotas The Odds API."
    if sportsdb_ready and odds_ready:
        return "Base sólida: TheSportsDB + The Odds API. Para acercarse a Flashscore/Sofascore falta activar API-Football, Sportmonks o Sportradar."
    if sportsdb_ready:
        return "TheSportsDB listo. Falta confirmar cuotas y proveedor live profesional."
    return "Configura THESPORTSDB_KEY como base legal de enriquecimiento y añade un proveedor live cuando tengas licencia."


def provider_check(db_path: str) -> Dict[str, Any]:
    summary = data_provider_summary(db_path)
    record_provider_run(
        db_path,
        summary.get("primary_provider") or DEFAULT_PRIMARY_PROVIDER,
        "provider_check",
        "ok",
        configured_providers=summary.get("configured_providers", 0),
        enabled_providers=summary.get("enabled_providers", 0),
        ready_score=summary.get("ready_score", 0),
    )
    return summary


__all__ = [
    "ensure_data_provider_schema",
    "data_provider_summary",
    "provider_check",
    "record_provider_run",
    "normalize_match",
    "normalize_event",
    "primary_provider",
    "provider_order",
]
