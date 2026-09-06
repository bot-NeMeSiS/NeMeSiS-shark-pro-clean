"""API-Football live tracker integration for NeMeSiS SHARK PRO V805.

This module is intentionally conservative:
- It only uses API-Football when the paid key is configured in Render.
- It caches live calls to avoid burning credits/request limits.
- It stores only normalized match/event/stat rows needed by the app.
- It never fabricates ball coordinates or dangerous attacks when the provider does not send them.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
DEFAULT_TIMEZONE = "Europe/Madrid"
LIVE_STATUS_SHORT = {"1H", "2H", "ET", "BT", "P", "LIVE", "HT"}
FINISHED_STATUS_SHORT = {"FT", "AET", "PEN"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hash(*parts: Any) -> str:
    raw = "|".join(str(p or "") for p in parts)
    return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()[:32]


def _json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return "{}"


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _connect_readonly(db_path: str) -> sqlite3.Connection:
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        raise sqlite3.OperationalError("database_not_available")
    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA busy_timeout=300")
    return conn


def _rowdict(row: sqlite3.Row | Mapping[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {}
    if isinstance(row, sqlite3.Row):
        return {k: row[k] for k in row.keys()}
    return dict(row)


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def api_key_configured() -> bool:
    return bool(os.getenv("API_FOOTBALL_KEY") or os.getenv("API_FOOTBALL_API_KEY"))


def tracker_enabled() -> bool:
    return api_key_configured() and _env_bool("ENABLE_API_FOOTBALL_LIVE_TRACKER", True) and _env_bool("ENABLE_API_FOOTBALL_PROVIDER", True)


def _api_key() -> str:
    return str(os.getenv("API_FOOTBALL_KEY") or os.getenv("API_FOOTBALL_API_KEY") or "").strip()


def _api_get(path: str, params: Optional[Mapping[str, Any]] = None, timeout: int = 18) -> dict[str, Any]:
    key = _api_key()
    if not key:
        return {"ok": False, "response": [], "error": "Falta API_FOOTBALL_KEY."}
    clean_params = {k: v for k, v in (params or {}).items() if v not in (None, "")}
    query = urllib.parse.urlencode(clean_params)
    url = f"{API_FOOTBALL_BASE_URL.rstrip('/')}/{path.strip('/')}"
    if query:
        url += "?" + query
    req = urllib.request.Request(
        url,
        headers={
            "x-apisports-key": key,
            "User-Agent": "NeMeSiS-SHARK-PRO/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", "replace"))
        errors = payload.get("errors") or []
        return {
            "ok": not bool(errors),
            "response": payload.get("response") or [],
            "payload": payload,
            "errors": errors,
            "requests": payload.get("paging") or {},
        }
    except Exception as exc:  # pragma: no cover - network dependent
        return {"ok": False, "response": [], "error": str(exc)[:300]}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).replace("%", "").strip()))
    except Exception:
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace("%", "").strip())
    except Exception:
        return default


def _stat_numeric(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("%", "").strip()
    try:
        return float(text)
    except Exception:
        return 0.0


def ensure_live_tracker_schema(db_path: str) -> dict[str, Any]:
    conn = _connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS api_football_live_sync_state(
                key TEXT PRIMARY KEY,
                last_sync_at TEXT,
                status TEXT,
                fixtures_count INTEGER DEFAULT 0,
                events_count INTEGER DEFAULT 0,
                stats_count INTEGER DEFAULT 0,
                external_calls INTEGER DEFAULT 0,
                error TEXT,
                payload_json TEXT
            );

            CREATE TABLE IF NOT EXISTS api_football_live_snapshots(
                fixture_id TEXT PRIMARY KEY,
                match_id TEXT,
                league_id TEXT,
                league_name TEXT,
                country TEXT,
                season TEXT,
                round_name TEXT,
                kickoff_iso TEXT,
                match_date TEXT,
                status_short TEXT,
                status_long TEXT,
                elapsed INTEGER,
                home_team_id TEXT,
                away_team_id TEXT,
                home_team TEXT,
                away_team TEXT,
                home_logo TEXT,
                away_logo TEXT,
                home_score INTEGER,
                away_score INTEGER,
                venue TEXT,
                payload_json TEXT,
                first_seen_at TEXT,
                last_synced_at TEXT
            );

            CREATE TABLE IF NOT EXISTS api_football_live_events(
                id TEXT PRIMARY KEY,
                fixture_id TEXT,
                elapsed INTEGER,
                extra INTEGER,
                team_id TEXT,
                team_name TEXT,
                player_id TEXT,
                player_name TEXT,
                assist_id TEXT,
                assist_name TEXT,
                event_type TEXT,
                detail TEXT,
                comments TEXT,
                payload_json TEXT,
                captured_at TEXT
            );

            CREATE TABLE IF NOT EXISTS api_football_live_stats(
                id TEXT PRIMARY KEY,
                fixture_id TEXT,
                team_id TEXT,
                team_name TEXT,
                stat_name TEXT,
                stat_value TEXT,
                numeric_value REAL DEFAULT 0,
                payload_json TEXT,
                captured_at TEXT,
                UNIQUE(fixture_id, team_id, stat_name)
            );
            """
        )
        matches_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='matches'"
        ).fetchone()
        if matches_exists:
            match_columns = {
                str(row[1]) for row in conn.execute("PRAGMA table_info(matches)").fetchall()
            }
            if "last_synced_at" not in match_columns:
                conn.execute("ALTER TABLE matches ADD COLUMN last_synced_at TEXT")
        conn.commit()
        return {"ok": True, "schema": "api_football_live_tracker_ready"}
    finally:
        conn.close()


def _match_id_for_fixture(fixture_id: str) -> str:
    return f"af-{fixture_id}"


def _normalize_fixture(item: Mapping[str, Any]) -> dict[str, Any]:
    fixture = item.get("fixture") or {}
    league = item.get("league") or {}
    teams = item.get("teams") or {}
    goals = item.get("goals") or {}
    status = fixture.get("status") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    venue = fixture.get("venue") or {}
    fixture_id = str(fixture.get("id") or "")
    kickoff = fixture.get("date") or ""
    return {
        "fixture_id": fixture_id,
        "match_id": _match_id_for_fixture(fixture_id) if fixture_id else "",
        "league_id": str(league.get("id") or ""),
        "league_name": league.get("name") or "",
        "country": league.get("country") or "",
        "season": str(league.get("season") or ""),
        "round_name": league.get("round") or "",
        "kickoff_iso": kickoff,
        "match_date": str(kickoff)[:10],
        "status_short": status.get("short") or "",
        "status_long": status.get("long") or "",
        "elapsed": _as_int(status.get("elapsed"), 0),
        "home_team_id": str(home.get("id") or ""),
        "away_team_id": str(away.get("id") or ""),
        "home_team": home.get("name") or "Local",
        "away_team": away.get("name") or "Visitante",
        "home_logo": home.get("logo") or "",
        "away_logo": away.get("logo") or "",
        "home_score": goals.get("home"),
        "away_score": goals.get("away"),
        "venue": venue.get("name") or "",
        "payload_json": _json(item),
    }


def _upsert_fixture(conn: sqlite3.Connection, item: Mapping[str, Any]) -> int:
    now = _now_iso()
    f = _normalize_fixture(item)
    if not f.get("fixture_id"):
        return 0
    conn.execute(
        """
        INSERT INTO api_football_live_snapshots(fixture_id, match_id, league_id, league_name, country, season, round_name, kickoff_iso, match_date, status_short, status_long, elapsed, home_team_id, away_team_id, home_team, away_team, home_logo, away_logo, home_score, away_score, venue, payload_json, first_seen_at, last_synced_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(fixture_id) DO UPDATE SET
          match_id=excluded.match_id,
          league_id=excluded.league_id,
          league_name=excluded.league_name,
          country=excluded.country,
          season=excluded.season,
          round_name=excluded.round_name,
          kickoff_iso=excluded.kickoff_iso,
          match_date=excluded.match_date,
          status_short=excluded.status_short,
          status_long=excluded.status_long,
          elapsed=excluded.elapsed,
          home_team_id=excluded.home_team_id,
          away_team_id=excluded.away_team_id,
          home_team=excluded.home_team,
          away_team=excluded.away_team,
          home_logo=COALESCE(NULLIF(excluded.home_logo,''), api_football_live_snapshots.home_logo),
          away_logo=COALESCE(NULLIF(excluded.away_logo,''), api_football_live_snapshots.away_logo),
          home_score=excluded.home_score,
          away_score=excluded.away_score,
          venue=excluded.venue,
          payload_json=excluded.payload_json,
          last_synced_at=excluded.last_synced_at
        """,
        (
            f["fixture_id"], f["match_id"], f["league_id"], f["league_name"], f["country"], f["season"], f["round_name"],
            f["kickoff_iso"], f["match_date"], f["status_short"], f["status_long"], f["elapsed"], f["home_team_id"], f["away_team_id"],
            f["home_team"], f["away_team"], f["home_logo"], f["away_logo"], f["home_score"], f["away_score"], f["venue"], f["payload_json"], now, now,
        ),
    )
    _upsert_match_row(conn, f, provider_observed_at=now)
    return 1


def _upsert_match_row(
    conn: sqlite3.Connection,
    f: Mapping[str, Any],
    *,
    provider_observed_at: str = "",
) -> None:
    """Mirror live fixture into existing matches table so /match/<id> works."""
    now = _now_iso()
    score = ""
    if f.get("home_score") is not None and f.get("away_score") is not None:
        score = f"{f.get('home_score')}-{f.get('away_score')}"
    synced_at = str(provider_observed_at or "").strip()
    try:
        conn.execute(
            """
            INSERT INTO matches(id, external_id, sport_key, match_date, kickoff_time, match_time, kickoff_iso, competition_id, competition_key, competition_name, league_name, country, home_team, away_team, home_team_id, away_team_id, home_logo, away_logo, status, minute, score, home_score, away_score, venue, season, round, priority, source, legal_note, raw_json, sync_status, last_synced_at, updated_at)
            VALUES (?, ?, 'soccer', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 92, 'api_football_live', ?, ?, 'live_tracker', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              external_id=excluded.external_id,
              match_date=excluded.match_date,
              kickoff_time=COALESCE(NULLIF(excluded.kickoff_time,''), matches.kickoff_time),
              match_time=COALESCE(NULLIF(excluded.match_time,''), matches.match_time),
              kickoff_iso=COALESCE(NULLIF(excluded.kickoff_iso,''), matches.kickoff_iso),
              competition_id=COALESCE(NULLIF(excluded.competition_id,''), matches.competition_id),
              competition_key=COALESCE(NULLIF(excluded.competition_key,''), matches.competition_key),
              competition_name=COALESCE(NULLIF(excluded.competition_name,''), matches.competition_name),
              league_name=COALESCE(NULLIF(excluded.league_name,''), matches.league_name),
              country=COALESCE(NULLIF(excluded.country,''), matches.country),
              home_team=COALESCE(NULLIF(excluded.home_team,''), matches.home_team),
              away_team=COALESCE(NULLIF(excluded.away_team,''), matches.away_team),
              home_team_id=COALESCE(NULLIF(excluded.home_team_id,''), matches.home_team_id),
              away_team_id=COALESCE(NULLIF(excluded.away_team_id,''), matches.away_team_id),
              home_logo=COALESCE(NULLIF(excluded.home_logo,''), matches.home_logo),
              away_logo=COALESCE(NULLIF(excluded.away_logo,''), matches.away_logo),
              status=excluded.status,
              minute=excluded.minute,
              score=COALESCE(NULLIF(excluded.score,''), matches.score),
              home_score=excluded.home_score,
              away_score=excluded.away_score,
              venue=COALESCE(NULLIF(excluded.venue,''), matches.venue),
              season=COALESCE(NULLIF(excluded.season,''), matches.season),
              round=COALESCE(NULLIF(excluded.round,''), matches.round),
              source=excluded.source,
              legal_note=excluded.legal_note,
              raw_json=excluded.raw_json,
              sync_status=excluded.sync_status,
              last_synced_at=excluded.last_synced_at,
              updated_at=excluded.updated_at
            """,
            (
                f.get("match_id"), f.get("fixture_id"), f.get("match_date") or now[:10], _time_from_iso(f.get("kickoff_iso")), _time_from_iso(f.get("kickoff_iso")), f.get("kickoff_iso") or "",
                f.get("league_id") or "", _competition_key(f.get("league_name"), f.get("country")), f.get("league_name") or "", f.get("league_name") or "", f.get("country") or "",
                f.get("home_team") or "Local", f.get("away_team") or "Visitante", f.get("home_team_id") or "", f.get("away_team_id") or "", f.get("home_logo") or "", f.get("away_logo") or "",
                f.get("status_short") or f.get("status_long") or "UNKNOWN", str(f.get("elapsed") or ""), score, str(f.get("home_score") if f.get("home_score") is not None else ""), str(f.get("away_score") if f.get("away_score") is not None else ""),
                f.get("venue") or "", f.get("season") or "", f.get("round_name") or "", "API-Football autorizado: livescore, eventos y estadísticas. NeMeSiS guarda caché normalizada; no se inventan coordenadas de balón.", f.get("payload_json") or "{}", synced_at, now,
            ),
        )
    except sqlite3.OperationalError:
        # Some legacy local DBs may have older schema; the app schema migration will handle production.
        pass


def _competition_key(name: Any, country: Any = "") -> str:
    raw = f"{name or ''}-{country or ''}".lower()
    raw = "".join(ch if ch.isalnum() else "-" for ch in raw)
    while "--" in raw:
        raw = raw.replace("--", "-")
    return raw.strip("-")[:80] or "api-football"


def _time_from_iso(value: Any) -> str:
    text = str(value or "")
    if "T" in text and len(text.split("T", 1)[1]) >= 5:
        return text.split("T", 1)[1][:5]
    return ""


def _upsert_events(conn: sqlite3.Connection, fixture_id: str, events: Iterable[Mapping[str, Any]]) -> int:
    now = _now_iso()
    inserted = 0
    for item in events or []:
        time = item.get("time") or {}
        team = item.get("team") or {}
        player = item.get("player") or {}
        assist = item.get("assist") or {}
        elapsed = _as_int(time.get("elapsed"), 0)
        extra = _as_int(time.get("extra"), 0)
        event_type = str(item.get("type") or "Evento")
        detail = str(item.get("detail") or "")
        row_id = _hash("af-live-event", fixture_id, elapsed, extra, team.get("id"), player.get("id"), event_type, detail)
        before = conn.total_changes
        conn.execute(
            """
            INSERT OR IGNORE INTO api_football_live_events(id, fixture_id, elapsed, extra, team_id, team_name, player_id, player_name, assist_id, assist_name, event_type, detail, comments, payload_json, captured_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id, fixture_id, elapsed, extra, str(team.get("id") or ""), team.get("name") or "", str(player.get("id") or ""), player.get("name") or "",
                str(assist.get("id") or ""), assist.get("name") or "", event_type, detail, item.get("comments") or "", _json(item), now,
            ),
        )
        inserted += 1 if conn.total_changes > before else 0
    return inserted


def persist_api_football_events(
    conn: sqlite3.Connection,
    fixture_id: str,
    events: Iterable[Mapping[str, Any]],
) -> int:
    """Persist already-authorized provider events in the canonical live cache."""
    return _upsert_events(conn, str(fixture_id or ""), events)


def _upsert_statistics(conn: sqlite3.Connection, fixture_id: str, stats_payload: Iterable[Mapping[str, Any]]) -> int:
    now = _now_iso()
    inserted = 0
    for team_block in stats_payload or []:
        team = team_block.get("team") or {}
        team_id = str(team.get("id") or "")
        team_name = team.get("name") or ""
        for stat in team_block.get("statistics") or []:
            stat_name = str(stat.get("type") or "").strip()
            if not stat_name:
                continue
            stat_value_raw = stat.get("value")
            stat_value = "" if stat_value_raw is None else str(stat_value_raw)
            row_id = _hash("af-live-stat", fixture_id, team_id, stat_name)
            before = conn.total_changes
            conn.execute(
                """
                INSERT INTO api_football_live_stats(id, fixture_id, team_id, team_name, stat_name, stat_value, numeric_value, payload_json, captured_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fixture_id, team_id, stat_name) DO UPDATE SET
                  team_name=excluded.team_name,
                  stat_value=excluded.stat_value,
                  numeric_value=excluded.numeric_value,
                  payload_json=excluded.payload_json,
                  captured_at=excluded.captured_at
                """,
                (row_id, fixture_id, team_id, team_name, stat_name, stat_value, _stat_numeric(stat_value_raw), _json(stat), now),
            )
            inserted += 1 if conn.total_changes > before else 0
    return inserted


def _last_sync_age_for_key(conn: sqlite3.Connection, key: str) -> int:
    row = conn.execute("SELECT last_sync_at FROM api_football_live_sync_state WHERE key=?", (str(key or "live"),)).fetchone()
    if not row or not row["last_sync_at"]:
        return 10**9
    try:
        raw = str(row["last_sync_at"]).replace("Z", "+00:00")
        last = datetime.fromisoformat(raw)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - last).total_seconds()))
    except Exception:
        return 10**9


def _last_sync_age(conn: sqlite3.Connection) -> int:
    return _last_sync_age_for_key(conn, "live")


def sync_api_football_live_tracker(db_path: str, force: bool = False, deep_limit: Optional[int] = None) -> dict[str, Any]:
    ensure_live_tracker_schema(db_path)
    conn = _connect(db_path)
    try:
        cache_seconds = _as_int(os.getenv("API_FOOTBALL_LIVE_CACHE_SECONDS", "55"), 55)
        age = _last_sync_age(conn)
        if not tracker_enabled():
            state = {"ok": False, "configured": api_key_configured(), "enabled": tracker_enabled(), "status": "pendiente_api_football", "message": "API-Football live tracker no configurado o desactivado."}
            _write_sync_state(conn, state, 0, 0, 0, 0, "")
            conn.commit()
            state["matches"] = live_tracker_matches(db_path, limit=80)
            return state
        if not force and age < cache_seconds:
            matches = _live_tracker_matches_from_conn(conn, limit=100)
            return {"ok": True, "configured": True, "enabled": True, "status": "cache", "cache_age_seconds": age, "matches": matches, "fixtures_count": len(matches), "external_calls": 0, "message": "Caché live API-Football reutilizada."}

        deep_limit = deep_limit if deep_limit is not None else _as_int(os.getenv("API_FOOTBALL_LIVE_DEEP_LIMIT", "8"), 8)
        timezone_name = os.getenv("APP_TIMEZONE") or os.getenv("TZ") or DEFAULT_TIMEZONE
        live_payload = _api_get("fixtures", {"live": "all", "timezone": timezone_name})
        external_calls = 1
        fixtures = live_payload.get("response") or []
        fixtures_count = events_count = stats_count = 0
        errors: list[str] = []
        if not live_payload.get("ok"):
            errors.append(str(live_payload.get("error") or live_payload.get("errors") or "Error API-Football live")[:220])
        for item in fixtures:
            fixtures_count += _upsert_fixture(conn, item)
        conn.commit()
        for item in fixtures[: max(0, int(deep_limit))]:
            fixture = item.get("fixture") or {}
            fixture_id = str(fixture.get("id") or "")
            if not fixture_id:
                continue
            ev_payload = _api_get("fixtures/events", {"fixture": fixture_id})
            external_calls += 1
            if ev_payload.get("ok"):
                events_count += _upsert_events(conn, fixture_id, ev_payload.get("response") or [])
            else:
                errors.append(str(ev_payload.get("error") or ev_payload.get("errors") or "Eventos no disponibles")[:180])
            st_payload = _api_get("fixtures/statistics", {"fixture": fixture_id})
            external_calls += 1
            if st_payload.get("ok"):
                stats_count += _upsert_statistics(conn, fixture_id, st_payload.get("response") or [])
            else:
                errors.append(str(st_payload.get("error") or st_payload.get("errors") or "Estadísticas no disponibles")[:180])
        status = "ok" if not errors else "partial"
        state = {
            "ok": True,
            "configured": True,
            "enabled": True,
            "status": status,
            "fixtures_count": fixtures_count,
            "events_count": events_count,
            "stats_count": stats_count,
            "external_calls": external_calls,
            "cache_age_seconds": 0,
            "errors": errors[:8],
            "message": "API-Football live sincronizado con caché y límites." if fixtures_count else "Sin partidos live devueltos por API-Football ahora mismo.",
        }
        _write_sync_state(conn, state, fixtures_count, events_count, stats_count, external_calls, "; ".join(errors[:3]))
        conn.commit()
        state["matches"] = _live_tracker_matches_from_conn(conn, limit=100)
        return state
    finally:
        conn.close()


def _write_sync_state(conn: sqlite3.Connection, state: Mapping[str, Any], fixtures: int, events: int, stats: int, calls: int, error: str = "") -> None:
    conn.execute(
        """
        INSERT INTO api_football_live_sync_state(key, last_sync_at, status, fixtures_count, events_count, stats_count, external_calls, error, payload_json)
        VALUES ('live', ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
          last_sync_at=excluded.last_sync_at,
          status=excluded.status,
          fixtures_count=excluded.fixtures_count,
          events_count=excluded.events_count,
          stats_count=excluded.stats_count,
          external_calls=excluded.external_calls,
          error=excluded.error,
          payload_json=excluded.payload_json
        """,
        (_now_iso(), state.get("status") or "unknown", fixtures, events, stats, calls, error or "", _json(state)),
    )


def _stat_key(name: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "_", str(name or "").lower()).strip("_")
    aliases = {
        "ball_possession": "possession",
        "possession": "possession",
        "shots_on_goal": "shots_on_goal",
        "shots_on_target": "shots_on_goal",
        "shots_off_goal": "shots_off_goal",
        "shots_off_target": "shots_off_goal",
        "total_shots": "total_shots",
        "blocked_shots": "blocked_shots",
        "shots_insidebox": "shots_inside_box",
        "shots_inside_box": "shots_inside_box",
        "shots_outsidebox": "shots_outside_box",
        "shots_outside_box": "shots_outside_box",
        "corner_kicks": "corners",
        "corners": "corners",
        "fouls": "fouls",
        "offsides": "offsides",
        "yellow_cards": "yellow_cards",
        "red_cards": "red_cards",
        "goalkeeper_saves": "saves",
        "saves": "saves",
        "total_passes": "total_passes",
        "passes_accurate": "passes_accurate",
        "passes": "total_passes",
        "passes_percentage": "passes_pct",
        "passes_percent": "passes_pct",
        "passes_accuracy": "passes_pct",
        "expected_goals": "expected_goals",
        "xg": "expected_goals",
        "attacks": "attacks",
        "dangerous_attacks": "dangerous_attacks",
        "dangerous_attack": "dangerous_attacks",
    }
    return aliases.get(clean, clean)


def _stats_for_fixture(conn: sqlite3.Connection, fixture_id: str) -> dict[str, Any]:
    rows = conn.execute("SELECT * FROM api_football_live_stats WHERE fixture_id=? ORDER BY team_name, stat_name", (fixture_id,)).fetchall()
    teams: dict[str, dict[str, Any]] = {}
    for row in rows:
        r = _rowdict(row)
        team = r.get("team_name") or r.get("team_id") or "Equipo"
        key = _stat_key(r.get("stat_name") or "")
        teams.setdefault(team, {"team": team, "stats": {}, "raw": []})
        teams[team]["stats"][key] = {"label": r.get("stat_name"), "value": r.get("stat_value"), "numeric": r.get("numeric_value")}
        teams[team]["raw"].append(r)
    return {"teams": list(teams.values()), "available": bool(rows), "total": len(rows)}


def _events_for_fixture(conn: sqlite3.Connection, fixture_id: str, limit: int = 12) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM api_football_live_events WHERE fixture_id=? ORDER BY elapsed DESC, extra DESC LIMIT ?", (fixture_id, int(limit))).fetchall()
    return [_rowdict(r) for r in rows]



def _team_blocks(stats: Mapping[str, Any], home_name: str = "", away_name: str = "") -> tuple[dict[str, Any], dict[str, Any]]:
    teams = list(stats.get("teams") or [])
    if not teams:
        return {}, {}
    home = away = None
    for team in teams:
        name = str(team.get("team") or "").lower()
        if home_name and name == str(home_name).lower():
            home = team
        if away_name and name == str(away_name).lower():
            away = team
    if home is None:
        home = teams[0] if teams else {}
    if away is None:
        away = teams[1] if len(teams) > 1 else {}
    return dict(home or {}), dict(away or {})


def _stat_obj(team: Mapping[str, Any], key: str) -> dict[str, Any]:
    stats = team.get("stats") or {}
    return dict(stats.get(key) or {})


def _stat_display(team: Mapping[str, Any], key: str) -> str:
    obj = _stat_obj(team, key)
    value = obj.get("value")
    if value is None or value == "":
        return ""
    return str(value)


def _has_stat(stats: Mapping[str, Any], key: str) -> bool:
    for team in stats.get("teams") or []:
        if key in (team.get("stats") or {}):
            return True
    return False


def _stat_cards(stats: Mapping[str, Any], home_name: str, away_name: str) -> list[dict[str, Any]]:
    if not stats.get("available"):
        return []
    home, away = _team_blocks(stats, home_name, away_name)
    definitions = [
        ("possession", "Posesión"),
        ("shots_on_goal", "Tiros a puerta"),
        ("total_shots", "Tiros totales"),
        ("shots_inside_box", "Tiros en área"),
        ("corners", "Córners"),
        ("expected_goals", "xG"),
        ("fouls", "Faltas"),
        ("yellow_cards", "Amarillas"),
        ("red_cards", "Rojas"),
        ("saves", "Paradas"),
        ("attacks", "Ataques"),
        ("dangerous_attacks", "Ataques peligrosos"),
        ("passes_accurate", "Pases buenos"),
        ("passes_pct", "Precisión pase"),
    ]
    cards: list[dict[str, Any]] = []
    for key, label in definitions:
        hv = _stat_display(home, key)
        av = _stat_display(away, key)
        if not hv and not av:
            continue
        hn = _as_float(_stat_obj(home, key).get("numeric"), 0)
        an = _as_float(_stat_obj(away, key).get("numeric"), 0)
        leader = "even"
        if hn > an:
            leader = "home"
        elif an > hn:
            leader = "away"
        cards.append({
            "key": key,
            "label": label,
            "home": hv or "—",
            "away": av or "—",
            "home_numeric": hn,
            "away_numeric": an,
            "leader": leader,
        })
    return cards


def _event_minute(event: Mapping[str, Any]) -> int:
    return _as_int(event.get("elapsed"), 0)


def _game_flow(stats: Mapping[str, Any], events: list[dict[str, Any]], pressure: Mapping[str, Any], home_name: str, away_name: str) -> dict[str, Any]:
    cards = _stat_cards(stats, home_name, away_name)
    event_count = len(events or [])
    latest = max([_event_minute(e) for e in events or []] or [0])
    recent = [e for e in (events or []) if latest and _event_minute(e) >= max(0, latest - 15)]
    title = pressure.get("label") or "Lectura pendiente"
    if pressure.get("available"):
        diff = abs(int(pressure.get("home_pct") or 50) - int(pressure.get("away_pct") or 50))
        phase = "Dominio claro" if diff >= 24 else "Presión ligera" if diff >= 10 else "Equilibrado"
    elif event_count:
        phase = "Eventos sincronizados"
        title = "Timeline real disponible"
    else:
        phase = "Esperando datos live"
    evidence = []
    for key, label in [("possession", "posesión"), ("shots_on_goal", "tiros a puerta"), ("corners", "córners"), ("dangerous_attacks", "ataques peligrosos"), ("attacks", "ataques")]:
        if _has_stat(stats, key):
            evidence.append(label)
    return {
        "available": bool(cards or events or pressure.get("available")),
        "title": title,
        "phase": phase,
        "event_count": event_count,
        "recent_event_count": len(recent),
        "evidence": evidence,
        "latest_minute": latest,
    }



def _tracker_quality_payload(stats: Mapping[str, Any], events: list[dict[str, Any]], pressure: Mapping[str, Any]) -> dict[str, Any]:
    """Readable real-data quality label for client UI.

    This is intentionally evidence-based. It never upgrades a tracker to a high
    level unless the normalized API-Football payload really contains stats/events.
    """
    evidence: list[str] = []
    if stats.get("available"):
        evidence.append("estadísticas")
    if events:
        evidence.append("eventos")
    if pressure.get("available"):
        evidence.append("presión")
    if _has_stat(stats, "possession"):
        evidence.append("posesión")
    if _has_stat(stats, "shots_on_goal") or _has_stat(stats, "total_shots"):
        evidence.append("tiros")
    if _has_stat(stats, "dangerous_attacks"):
        evidence.append("ataques peligrosos")
    if _has_stat(stats, "attacks"):
        evidence.append("ataques")
    if len(evidence) >= 5:
        level = "premium"
        label = "Live profundo"
        message = "Eventos y estadísticas avanzadas reales disponibles."
    elif len(evidence) >= 3:
        level = "advanced"
        label = "Live avanzado"
        message = "Datos suficientes para lectura SHARK real."
    elif len(evidence) >= 1:
        level = "basic_plus"
        label = "Live con señales"
        message = "Hay datos reales parciales; faltan algunas estadísticas del feed."
    else:
        level = "basic"
        label = "Marcador básico"
        message = "Esperando eventos/estadísticas avanzadas del proveedor."
    return {
        "level": level,
        "label": label,
        "message": message,
        "evidence": evidence,
        "evidence_count": len(evidence),
        "ball_position_policy": "No se muestra balón exacto si API-Football no entrega coordenadas reales.",
        "safe_to_show": True,
    }

def _last_event_label(events: list[dict[str, Any]]) -> str:
    if not events:
        return "Sin evento reciente"
    ev = events[0]
    minute = str(ev.get("elapsed") or "").strip()
    etype = str(ev.get("event_type") or "Evento").strip()
    detail = str(ev.get("detail") or ev.get("comments") or ev.get("player_name") or "").strip()
    team = str(ev.get("team_name") or "").strip()
    prefix = (minute + "' · ") if minute else ""
    middle = f"{etype}" + (f" · {detail}" if detail else "")
    return f"{prefix}{team} · {middle}" if team else f"{prefix}{middle}"


def _stat_pair(stats: Mapping[str, Any], key: str) -> tuple[float, float]:
    block = stats.get(key) if isinstance(stats, Mapping) else None
    if not isinstance(block, Mapping):
        return 0.0, 0.0
    return _stat_numeric((block.get("home") or {}).get("numeric")), _stat_numeric((block.get("away") or {}).get("numeric"))


def _field_state(stats: Mapping[str, Any], events: list[dict[str, Any]], pressure: Mapping[str, Any], home_name: str, away_name: str) -> dict[str, Any]:
    """Client field interpretation from real API-Football signals only.

    API-Football does not provide exact ball x/y coordinates in this integration, so
    NeMeSiS shows pressure zone, latest real event and stat evidence instead of an invented ball marker.
    """
    home_p = int(pressure.get("home_pct") or 50)
    away_p = int(pressure.get("away_pct") or 50)
    dominant = home_name if home_p >= away_p else away_name
    side = "home" if home_p >= away_p else "away"
    diff = abs(home_p - away_p)
    da_home, da_away = _stat_pair(stats, "dangerous_attacks")
    attacks_home, attacks_away = _stat_pair(stats, "attacks")
    corners_home, corners_away = _stat_pair(stats, "corners")
    latest = _last_event_label(events)
    if da_home or da_away:
        if da_home > da_away:
            headline = f"Ataque peligroso: {home_name}"
            side = "home"
        elif da_away > da_home:
            headline = f"Ataque peligroso: {away_name}"
            side = "away"
        else:
            headline = "Ataques peligrosos equilibrados"
        mode = "danger"
    elif corners_home or corners_away:
        headline = "Córners reales disponibles"
        mode = "corner"
    elif pressure.get("available"):
        headline = f"Presión de {dominant}" if diff >= 8 else "Partido equilibrado"
        mode = "pressure"
    elif events:
        headline = "Últimos eventos reales disponibles"
        mode = "events"
    else:
        headline = "Tracker básico: esperando estadísticas"
        mode = "basic"
    chips = []
    if da_home or da_away:
        chips.append(f"Ataques peligrosos {int(da_home)}-{int(da_away)}")
    if attacks_home or attacks_away:
        chips.append(f"Ataques {int(attacks_home)}-{int(attacks_away)}")
    if corners_home or corners_away:
        chips.append(f"Córners {int(corners_home)}-{int(corners_away)}")
    if events:
        chips.append(f"{len(events)} eventos reales")
    if pressure.get("available"):
        chips.append(f"Presión {home_p}-{away_p}")
    return {
        "available": bool(chips or pressure.get("available") or events),
        "mode": mode,
        "headline": headline,
        "dominant_team": dominant,
        "dominant_side": side,
        "home_pressure_pct": home_p,
        "away_pressure_pct": away_p,
        "last_event_label": latest,
        "dangerous_attacks_available": bool(da_home or da_away),
        "attacks_available": bool(attacks_home or attacks_away),
        "corners_available": bool(corners_home or corners_away),
        "chips": chips,
        "ball_position_available": False,
        "ball_note": "Balón exacto no disponible en el feed actual: no se dibuja marcador de balón inventado.",
    }


def _build_tracker_payload(row: Mapping[str, Any], stats: Mapping[str, Any], events: list[dict[str, Any]], pressure: Mapping[str, Any]) -> dict[str, Any]:
    home_name = str(row.get("home_team") or "")
    away_name = str(row.get("away_team") or "")
    cards = _stat_cards(stats, home_name, away_name)
    flow = _game_flow(stats, events, pressure, home_name, away_name)
    field_state = _field_state(stats, events, pressure, home_name, away_name)
    dangerous_available = _has_stat(stats, "dangerous_attacks")
    attacks_available = _has_stat(stats, "attacks")
    quality = _tracker_quality_payload(stats, events, pressure)
    return {
        "provider": "api_football",
        "source_label": "API-Football Pro",
        "fixture_id": row.get("fixture_id"),
        "updated_at": row.get("last_synced_at"),
        "last_synced_at": row.get("last_synced_at"),
        "stats": stats,
        "events": events,
        "pressure": pressure,
        "stat_cards": cards,
        "game_flow": flow,
        "field_state": field_state,
        "quality": quality,
        "quality_label": quality.get("label"),
        "quality_level": quality.get("level"),
        "evidence": quality.get("evidence") or [],
        "has_advanced_stats": bool(stats.get("available")),
        "has_events": bool(events),
        "stats_count": stats.get("total") or 0,
        "events_count": len(events or []),
        "dangerous_attacks_available": dangerous_available,
        "attacks_available": attacks_available,
        "ball_position_available": False,
        "message": "Live tracker real disponible" if (stats.get("available") or events) else "Marcador live disponible, esperando eventos/estadísticas.",
        "legal_note": "API-Football autorizado. Campo SHARK calculado con estadísticas/eventos reales; no se inventa ubicación exacta de balón.",
    }

def _pressure_from_stats(stats: Mapping[str, Any], home_name: str, away_name: str) -> dict[str, Any]:
    teams = stats.get("teams") or []
    if len(teams) < 2:
        return {"available": False, "label": "Presión pendiente", "home_pct": 50, "away_pct": 50, "source": "sin_estadisticas"}

    def score(team: Mapping[str, Any]) -> float:
        s = team.get("stats") or {}
        possession = _as_float((s.get("possession") or {}).get("numeric"), 0)
        shots = _as_float((s.get("shots_on_goal") or {}).get("numeric"), 0) * 8 + _as_float((s.get("total_shots") or {}).get("numeric"), 0) * 2
        box = _as_float((s.get("shots_inside_box") or {}).get("numeric"), 0) * 3
        corners = _as_float((s.get("corners") or {}).get("numeric"), 0) * 3
        attacks = _as_float((s.get("attacks") or {}).get("numeric"), 0) * 0.8
        dangerous = _as_float((s.get("dangerous_attacks") or {}).get("numeric"), 0) * 1.8
        xg = _as_float((s.get("expected_goals") or {}).get("numeric"), 0) * 12
        red = _as_float((s.get("red_cards") or {}).get("numeric"), 0) * -9
        yellow = _as_float((s.get("yellow_cards") or {}).get("numeric"), 0) * -1
        return max(0.0, possession + shots + box + corners + attacks + dangerous + xg + red + yellow)

    home = None
    away = None
    for team in teams:
        name = str(team.get("team") or "")
        if home_name and name.lower() == home_name.lower():
            home = team
        if away_name and name.lower() == away_name.lower():
            away = team
    home = home or teams[0]
    away = away or teams[1]
    hs, as_ = score(home), score(away)
    total = hs + as_
    if total <= 0:
        return {"available": False, "label": "Presión pendiente", "home_pct": 50, "away_pct": 50, "source": "estadisticas_sin_valor"}
    home_pct = round((hs / total) * 100)
    away_pct = 100 - home_pct
    diff = home_pct - away_pct
    if abs(diff) < 9:
        label = "Partido equilibrado"
    elif diff > 0:
        label = f"{home_name or 'Local'} presiona"
    else:
        label = f"{away_name or 'Visitante'} presiona"
    return {"available": True, "label": label, "home_pct": home_pct, "away_pct": away_pct, "source": "estadisticas_api_football"}


def _live_tracker_matches_from_conn(conn: sqlite3.Connection, limit: int = 80) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM api_football_live_snapshots
        ORDER BY CASE WHEN status_short IN ('1H','2H','HT','ET','BT','P','LIVE') THEN 0 ELSE 1 END, elapsed DESC, league_name, home_team
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        r = _rowdict(row)
        fixture_id = str(r.get("fixture_id") or "")
        stats = _stats_for_fixture(conn, fixture_id)
        events = _events_for_fixture(conn, fixture_id, limit=10)
        pressure = _pressure_from_stats(stats, r.get("home_team") or "", r.get("away_team") or "")
        score = ""
        if r.get("home_score") is not None and r.get("away_score") is not None:
            score = f"{r.get('home_score')}-{r.get('away_score')}"
        tracker = _build_tracker_payload(r, stats, events, pressure)
        out.append(
            {
                "id": r.get("match_id") or _match_id_for_fixture(fixture_id),
                "external_id": fixture_id,
                "sport_key": "soccer",
                "match_date": r.get("match_date") or str(r.get("kickoff_iso") or "")[:10],
                "kickoff_iso": r.get("kickoff_iso") or "",
                "kickoff_time": _time_from_iso(r.get("kickoff_iso")),
                "match_time": _time_from_iso(r.get("kickoff_iso")),
                "competition_id": r.get("league_id") or "",
                "competition_key": _competition_key(r.get("league_name"), r.get("country")),
                "competition_name": r.get("league_name") or "Competición",
                "league_name": r.get("league_name") or "Competición",
                "country": r.get("country") or "Global",
                "home_team": r.get("home_team") or "Local",
                "away_team": r.get("away_team") or "Visitante",
                "home_team_id": r.get("home_team_id") or "",
                "away_team_id": r.get("away_team_id") or "",
                "home_logo": r.get("home_logo") or "",
                "away_logo": r.get("away_logo") or "",
                "status": r.get("status_short") or r.get("status_long") or "UNKNOWN",
                "minute": str(r.get("elapsed") or ""),
                "score": score,
                "home_score": r.get("home_score"),
                "away_score": r.get("away_score"),
                "venue": r.get("venue") or "",
                "source": "api_football_live",
                "last_synced_at": r.get("last_synced_at") or "",
                "legal_note": tracker["legal_note"],
                "raw_json": r.get("payload_json") or "{}",
                "api_football_live_tracker": tracker,
                "live_tracker": tracker,
            }
        )
    return out


def live_tracker_matches(db_path: str, limit: int = 80) -> list[dict[str, Any]]:
    ensure_live_tracker_schema(db_path)
    conn = _connect(db_path)
    try:
        return _live_tracker_matches_from_conn(conn, limit=limit)
    finally:
        conn.close()


def live_tracker_for_match(db_path: str, match_id: str) -> dict[str, Any]:
    """Read one persisted tracker snapshot without schema writes or provider calls."""
    text = str(match_id or "")
    fixture_id = text[3:] if text.startswith("af-") else text
    try:
        conn = _connect_readonly(db_path)
    except (OSError, sqlite3.Error):
        return {
            "available": False,
            "provider": "api_football",
            "message": "No disponible: el caché local del tracker no está accesible.",
            "read_only": True,
        }
    try:
        try:
            row = conn.execute(
                "SELECT * FROM api_football_live_snapshots WHERE match_id=? OR fixture_id=? LIMIT 1",
                (text, fixture_id),
            ).fetchone()
        except sqlite3.OperationalError:
            return {
                "available": False,
                "provider": "api_football",
                "message": "No disponible: el tracker aún no tiene una instantánea local.",
                "read_only": True,
            }
        if not row:
            return {
                "available": False,
                "provider": "api_football",
                "message": "No disponible: no existe tracker para este partido.",
                "read_only": True,
            }
        r = _rowdict(row)
        stats = _stats_for_fixture(conn, str(r.get("fixture_id") or ""))
        events = _events_for_fixture(conn, str(r.get("fixture_id") or ""), limit=18)
        pressure = _pressure_from_stats(
            stats,
            r.get("home_team") or "",
            r.get("away_team") or "",
        )
        tracker = _build_tracker_payload(r, stats, events, pressure)
        tracker.update({"available": True, "read_only": True})
        return tracker
    finally:
        conn.close()


def sync_api_football_fixture_detail(db_path: str, match_id: str, force: bool = False) -> dict[str, Any]:
    """Deep-sync one API-Football fixture when the user opens its detail.

    This keeps /live cheap while allowing the selected match to load events/statistics.
    It never calls the provider if the tracker is disabled or the short per-fixture cache is fresh.
    """
    ensure_live_tracker_schema(db_path)
    text = str(match_id or "")
    fixture_id = text[3:] if text.startswith("af-") else text
    if not fixture_id:
        return {"ok": False, "status": "missing_fixture_id", "message": "Sin id de fixture API-Football."}
    conn = _connect(db_path)
    key = f"fixture:{fixture_id}"
    try:
        cache_seconds = _as_int(os.getenv("API_FOOTBALL_LIVE_DETAIL_CACHE_SECONDS", "75"), 75)
        age = _last_sync_age_for_key(conn, key)
        if not tracker_enabled():
            state = {"ok": False, "configured": api_key_configured(), "enabled": tracker_enabled(), "status": "pendiente_api_football", "message": "Detalle live API-Football no configurado o desactivado."}
            _write_sync_state(conn, state, 0, 0, 0, 0, "")
            conn.commit()
            return state
        if not force and age < cache_seconds:
            cached = live_tracker_for_match(db_path, text)
            cached.update({"ok": True, "status": "cache_detail", "cache_age_seconds": age, "external_calls": 0})
            return cached
        existing = conn.execute("SELECT fixture_id FROM api_football_live_snapshots WHERE fixture_id=? OR match_id=? LIMIT 1", (fixture_id, text)).fetchone()
        external_calls = 0
        fixtures_count = 0
        errors: list[str] = []
        if not existing:
            timezone_name = os.getenv("APP_TIMEZONE") or os.getenv("TZ") or DEFAULT_TIMEZONE
            fixture_payload = _api_get("fixtures", {"id": fixture_id, "timezone": timezone_name})
            external_calls += 1
            if fixture_payload.get("ok"):
                for item in fixture_payload.get("response") or []:
                    fixtures_count += _upsert_fixture(conn, item)
            else:
                errors.append(str(fixture_payload.get("error") or fixture_payload.get("errors") or "Fixture no disponible")[:180])
        ev_payload = _api_get("fixtures/events", {"fixture": fixture_id})
        external_calls += 1
        events_count = 0
        if ev_payload.get("ok"):
            events_count = _upsert_events(conn, fixture_id, ev_payload.get("response") or [])
        else:
            errors.append(str(ev_payload.get("error") or ev_payload.get("errors") or "Eventos no disponibles")[:180])
        st_payload = _api_get("fixtures/statistics", {"fixture": fixture_id})
        external_calls += 1
        stats_count = 0
        if st_payload.get("ok"):
            stats_count = _upsert_statistics(conn, fixture_id, st_payload.get("response") or [])
        else:
            errors.append(str(st_payload.get("error") or st_payload.get("errors") or "Estadísticas no disponibles")[:180])
        state = {
            "ok": True,
            "configured": True,
            "enabled": True,
            "status": "ok" if not errors else "partial",
            "fixtures_count": fixtures_count,
            "events_count": events_count,
            "stats_count": stats_count,
            "external_calls": external_calls,
            "cache_age_seconds": 0,
            "errors": errors[:6],
            "message": "Detalle live API-Football sincronizado con caché por partido.",
        }
        _write_sync_state(conn, {**state, "status": state["status"]}, fixtures_count, events_count, stats_count, external_calls, "; ".join(errors[:3]))
        conn.execute(
            "INSERT INTO api_football_live_sync_state(key, last_sync_at, status, fixtures_count, events_count, stats_count, external_calls, error, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET last_sync_at=excluded.last_sync_at,status=excluded.status,fixtures_count=excluded.fixtures_count,events_count=excluded.events_count,stats_count=excluded.stats_count,external_calls=excluded.external_calls,error=excluded.error,payload_json=excluded.payload_json",
            (key, _now_iso(), state["status"], fixtures_count, events_count, stats_count, external_calls, "; ".join(errors[:3]), _json(state)),
        )
        conn.commit()
    finally:
        conn.close()
    tracker = live_tracker_for_match(db_path, text)
    tracker.update({"ok": True, "status": "detail_synced", "external_calls": external_calls, "errors": errors[:6]})
    return tracker



def _state_key_for_window() -> str:
    return "match_window"


def _date_range(days_back: int, days_ahead: int) -> list[str]:
    today = datetime.now(timezone.utc).date()
    back = max(0, min(5, int(days_back)))
    ahead = max(0, min(7, int(days_ahead)))
    return [(today + timedelta(days=offset)).isoformat() for offset in range(-back, ahead + 1)]


def sync_api_football_match_window(
    db_path: str,
    days_back: int = 2,
    days_ahead: int = 2,
    force: bool = False,
    deep_limit: Optional[int] = None,
) -> dict[str, Any]:
    """Refresh nearby fixtures/results using API-Football with a conservative cache.

    Purpose: a match played at dawn should stop appearing as upcoming and move to
    results once API-Football returns FT/score. This updates only normalized cache
    and the matches table; it never invents scores.
    """
    ensure_live_tracker_schema(db_path)
    cache_seconds = _as_int(os.getenv("API_FOOTBALL_MATCH_WINDOW_CACHE_SECONDS", "21600"), 21600)
    conn = _connect(db_path)
    try:
        if not tracker_enabled():
            state = {"ok": False, "configured": api_key_configured(), "enabled": tracker_enabled(), "status": "pendiente_api_football", "message": "API-Football no configurado o desactivado para ventana de partidos."}
            conn.execute("INSERT OR REPLACE INTO api_football_live_sync_state(key,last_sync_at,status,fixtures_count,events_count,stats_count,external_calls,error,payload_json) VALUES (?,?,?,?,?,?,?,?,?)", (_state_key_for_window(), _now_iso(), state["status"], 0, 0, 0, 0, state.get("message"), _json(state)))
            conn.commit()
            return state
        age = _cache_age_seconds(conn, _state_key_for_window())
        if not force and age is not None and age < cache_seconds:
            return {"ok": True, "configured": True, "enabled": True, "status": "cache", "cache_age_seconds": age, "external_calls": 0, "message": "Ventana API-Football reutilizada para proteger créditos."}
        dates = _date_range(days_back, days_ahead)
        fixtures_count = stats_count = events_count = calls = 0
        errors = []
        all_fixtures = []
        for date_value in dates:
            payload = _api_get("fixtures", {"date": date_value, "timezone": os.getenv("APP_TIMEZONE", DEFAULT_TIMEZONE)})
            calls += 1
            if not payload.get("ok"):
                errors.append(str(payload.get("error") or payload.get("errors") or f"error_fixtures_{date_value}")[:220])
                continue
            fixtures = [_normalize_fixture(item) for item in (payload.get("response") or [])]
            all_fixtures.extend(fixtures)
        fixtures_count = len(all_fixtures)
        if all_fixtures:
            fixtures_count = _upsert_snapshots(conn, all_fixtures)
            _upsert_matches(conn, all_fixtures)
        # Deep data only for live/recent finished fixtures to avoid wasting calls.
        deep_limit = (
            _as_int(os.getenv("API_FOOTBALL_MATCH_WINDOW_DEEP_LIMIT", "10"), 10)
            if deep_limit is None
            else max(0, int(deep_limit))
        )
        deep_done = 0
        for f in all_fixtures:
            if deep_done >= deep_limit:
                break
            status = str(f.get("status_short") or "").upper()
            if status not in LIVE_STATUS_SHORT and status not in FINISHED_STATUS_SHORT:
                continue
            fixture_id = str(f.get("fixture_id") or "")
            if not fixture_id:
                continue
            ev_payload = _api_get("fixtures/events", {"fixture": fixture_id})
            calls += 1
            if ev_payload.get("ok"):
                events_count += _upsert_events(conn, fixture_id, ev_payload.get("response") or [])
            st_payload = _api_get("fixtures/statistics", {"fixture": fixture_id})
            calls += 1
            if st_payload.get("ok"):
                stats_count += _upsert_statistics(conn, fixture_id, st_payload.get("response") or [])
            deep_done += 1
        state = {
            "ok": not bool(errors),
            "configured": True,
            "enabled": True,
            "status": "OK" if not errors else "PARTIAL",
            "fixtures_count": fixtures_count,
            "events_count": events_count,
            "stats_count": stats_count,
            "external_calls": calls,
            "cache_seconds": cache_seconds,
            "dates": dates,
            "message": "Ventana API-Football sincronizada: resultados/minutos/caché actualizados sin inventar datos.",
            "errors": errors[:8],
        }
        conn.execute("""
            INSERT INTO api_football_live_sync_state(key,last_sync_at,status,fixtures_count,events_count,stats_count,external_calls,error,payload_json)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(key) DO UPDATE SET last_sync_at=excluded.last_sync_at,status=excluded.status,fixtures_count=excluded.fixtures_count,events_count=excluded.events_count,stats_count=excluded.stats_count,external_calls=excluded.external_calls,error=excluded.error,payload_json=excluded.payload_json
        """, (_state_key_for_window(), _now_iso(), state["status"], fixtures_count, events_count, stats_count, calls, "; ".join(errors[:4])[:500], _json(state)))
        conn.commit()
        return state
    except Exception as exc:
        return {"ok": False, "configured": api_key_configured(), "enabled": tracker_enabled(), "status": "ERROR", "error": str(exc)[:220]}
    finally:
        conn.close()


def live_tracker_quality_summary(db_path: str) -> dict[str, Any]:
    """Return a no-network quality summary for the API-Football live tracker.

    The UI and admin can call this safely; it reads normalized cache only and does
    not consume API-Football credits.
    """
    ensure_live_tracker_schema(db_path)
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT * FROM api_football_live_snapshots ORDER BY last_synced_at DESC LIMIT 300").fetchall()
        live_rows = [r for r in rows if str(r["status_short"] or "").upper() in LIVE_STATUS_SHORT]
        finished_rows = [r for r in rows if str(r["status_short"] or "").upper() in FINISHED_STATUS_SHORT]
        with_stats = with_events = with_pressure = with_dangerous = with_attacks = 0
        evidence_counter = {"estadísticas": 0, "eventos": 0, "presión": 0, "posesión": 0, "tiros": 0, "ataques": 0, "ataques peligrosos": 0}
        sample: list[dict[str, Any]] = []
        for row in rows:
            r = _rowdict(row)
            fid = str(r.get("fixture_id") or "")
            stats = _stats_for_fixture(conn, fid)
            events = _events_for_fixture(conn, fid, limit=8)
            pressure = _pressure_from_stats(stats, r.get("home_team") or "", r.get("away_team") or "")
            quality = _tracker_quality_payload(stats, events, pressure)
            if stats.get("available"):
                with_stats += 1
            if events:
                with_events += 1
            if pressure.get("available"):
                with_pressure += 1
            if _has_stat(stats, "dangerous_attacks"):
                with_dangerous += 1
            if _has_stat(stats, "attacks"):
                with_attacks += 1
            for item in quality.get("evidence") or []:
                evidence_counter[item] = evidence_counter.get(item, 0) + 1
            if len(sample) < 6:
                sample.append({
                    "match_id": r.get("match_id") or _match_id_for_fixture(fid),
                    "fixture_id": fid,
                    "home_team": r.get("home_team") or "Local",
                    "away_team": r.get("away_team") or "Visitante",
                    "status": r.get("status_short") or r.get("status_long") or "",
                    "minute": r.get("elapsed") or 0,
                    "quality": quality,
                    "pressure_label": pressure.get("label") or "Presión pendiente",
                })
        total = len(rows)
        advanced = len([s for s in sample if (s.get("quality") or {}).get("level") in {"premium", "advanced"}])
        status_row = conn.execute("SELECT * FROM api_football_live_sync_state WHERE key='live'").fetchone()
        state = _rowdict(status_row)
        if total and (with_stats or with_events):
            status = "REAL_LIVE_DATA_READY"
            message = "API-Football live aporta datos reales aprovechables para directo premium."
        elif total:
            status = "BASIC_LIVE_READY"
            message = "Hay marcador live real; faltan eventos/estadísticas avanzadas en el feed actual."
        elif tracker_enabled():
            status = "WAITING_FOR_LIVE_FIXTURES"
            message = "API-Football está configurada; no hay partidos live cacheados ahora mismo."
        elif api_key_configured():
            status = "PROVIDER_DISABLED"
            message = "La key existe, pero el live tracker o proveedor está desactivado por variable de entorno."
        else:
            status = "MISSING_API_FOOTBALL_KEY"
            message = "Falta API_FOOTBALL_KEY en Render para usar el live avanzado."
        return {
            "ok": True,
            "provider": "api_football",
            "configured": api_key_configured(),
            "enabled": tracker_enabled(),
            "status": status,
            "message": message,
            "last_sync_at": state.get("last_sync_at") or "",
            "cache_age_seconds": _last_sync_age(conn),
            "external_calls_last_sync": state.get("external_calls") or 0,
            "fixtures_total": total,
            "fixtures_live": len(live_rows),
            "fixtures_finished": len(finished_rows),
            "fixtures_with_stats": with_stats,
            "fixtures_with_events": with_events,
            "fixtures_with_pressure": with_pressure,
            "fixtures_with_attacks": with_attacks,
            "fixtures_with_dangerous_attacks": with_dangerous,
            "ball_position_available": False,
            "advanced_sample_count": advanced,
            "evidence_counter": evidence_counter,
            "sample": sample,
            "credit_policy": {
                "live_cache_seconds": _as_int(os.getenv("API_FOOTBALL_LIVE_CACHE_SECONDS", "55"), 55),
                "detail_cache_seconds": _as_int(os.getenv("API_FOOTBALL_LIVE_DETAIL_CACHE_SECONDS", "75"), 75),
                "deep_limit": _as_int(os.getenv("API_FOOTBALL_LIVE_DEEP_LIMIT", "8"), 8),
                "note": "La pantalla lee caché y solo refresca proveedor si se fuerza o expira la ventana configurada.",
            },
            "safe_rules": [
                "No se inventa posición exacta del balón.",
                "No se inventan ataques peligrosos si el feed no los trae.",
                "No se inventan eventos, estadísticas, resultados, cuotas ni picks.",
            ],
        }
    finally:
        conn.close()


def live_tracker_status(db_path: str) -> dict[str, Any]:
    ensure_live_tracker_schema(db_path)
    conn = _connect(db_path)
    try:
        row = conn.execute("SELECT * FROM api_football_live_sync_state WHERE key='live'").fetchone()
        state = _rowdict(row)
        return {
            "ok": True,
            "configured": api_key_configured(),
            "enabled": tracker_enabled(),
            "status": state.get("status") or ("ready" if tracker_enabled() else "pending"),
            "last_sync_at": state.get("last_sync_at") or "",
            "fixtures_count": state.get("fixtures_count") or 0,
            "events_count": state.get("events_count") or 0,
            "stats_count": state.get("stats_count") or 0,
            "external_calls": state.get("external_calls") or 0,
            "error": state.get("error") or "",
        }
    finally:
        conn.close()
