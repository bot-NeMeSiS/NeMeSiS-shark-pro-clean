"""API-Football live tracker integration for NeMeSiS SHARK PRO V803.

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
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional

API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
DEFAULT_TIMEZONE = "Europe/Madrid"
LIVE_STATUS_SHORT = {"1H", "2H", "ET", "BT", "P", "SUSP", "INT", "LIVE", "HT"}
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
    return os.getenv("API_FOOTBALL_KEY") or os.getenv("API_FOOTBALL_API_KEY") or ""


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
    _upsert_match_row(conn, f)
    return 1


def _upsert_match_row(conn: sqlite3.Connection, f: Mapping[str, Any]) -> None:
    """Mirror live fixture into existing matches table so /match/<id> works."""
    now = _now_iso()
    score = ""
    if f.get("home_score") is not None or f.get("away_score") is not None:
        score = f"{f.get('home_score') if f.get('home_score') is not None else 0}-{f.get('away_score') if f.get('away_score') is not None else 0}"
    try:
        conn.execute(
            """
            INSERT INTO matches(id, external_id, sport_key, match_date, kickoff_time, match_time, kickoff_iso, competition_id, competition_key, competition_name, league_name, country, home_team, away_team, home_team_id, away_team_id, home_logo, away_logo, status, minute, score, home_score, away_score, venue, season, round, priority, source, legal_note, raw_json, sync_status, updated_at)
            VALUES (?, ?, 'soccer', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 92, 'api_football_live', ?, ?, 'live_tracker', ?)
            ON CONFLICT(id) DO UPDATE SET
              external_id=excluded.external_id,
              match_date=excluded.match_date,
              kickoff_time=COALESCE(NULLIF(excluded.kickoff_time,''), matches.kickoff_time),
              match_time=COALESCE(NULLIF(excluded.match_time,''), matches.match_time),
              kickoff_iso=COALESCE(NULLIF(excluded.kickoff_iso,''), matches.kickoff_iso),
              competition_id=COALESCE(NULLIF(excluded.competition_id,''), matches.competition_id),
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
              updated_at=excluded.updated_at
            """,
            (
                f.get("match_id"), f.get("fixture_id"), f.get("match_date") or now[:10], _time_from_iso(f.get("kickoff_iso")), _time_from_iso(f.get("kickoff_iso")), f.get("kickoff_iso") or "",
                f.get("league_id") or "", _competition_key(f.get("league_name"), f.get("country")), f.get("league_name") or "", f.get("league_name") or "", f.get("country") or "",
                f.get("home_team") or "Local", f.get("away_team") or "Visitante", f.get("home_team_id") or "", f.get("away_team_id") or "", f.get("home_logo") or "", f.get("away_logo") or "",
                f.get("status_short") or f.get("status_long") or "LIVE", str(f.get("elapsed") or ""), score, str(f.get("home_score") if f.get("home_score") is not None else ""), str(f.get("away_score") if f.get("away_score") is not None else ""),
                f.get("venue") or "", f.get("season") or "", f.get("round_name") or "", "API-Football autorizado: livescore, eventos y estadísticas. NeMeSiS guarda caché normalizada; no se inventan coordenadas de balón.", f.get("payload_json") or "{}", now,
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


def _last_sync_age(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT last_sync_at FROM api_football_live_sync_state WHERE key='live'").fetchone()
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
    clean = str(name or "").lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "ball_possession": "possession",
        "shots_on_goal": "shots_on_goal",
        "total_shots": "total_shots",
        "corner_kicks": "corners",
        "yellow_cards": "yellow_cards",
        "red_cards": "red_cards",
        "goalkeeper_saves": "saves",
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


def _pressure_from_stats(stats: Mapping[str, Any], home_name: str, away_name: str) -> dict[str, Any]:
    teams = stats.get("teams") or []
    if len(teams) < 2:
        return {"available": False, "label": "Presión pendiente", "home_pct": 50, "away_pct": 50, "source": "sin_estadisticas"}

    def score(team: Mapping[str, Any]) -> float:
        s = team.get("stats") or {}
        possession = _as_float((s.get("possession") or {}).get("numeric"), 0)
        shots = _as_float((s.get("shots_on_goal") or {}).get("numeric"), 0) * 7 + _as_float((s.get("total_shots") or {}).get("numeric"), 0) * 2
        corners = _as_float((s.get("corners") or {}).get("numeric"), 0) * 3
        red = _as_float((s.get("red_cards") or {}).get("numeric"), 0) * -8
        yellow = _as_float((s.get("yellow_cards") or {}).get("numeric"), 0) * -1
        return max(0.0, possession + shots + corners + red + yellow)

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
        ORDER BY CASE WHEN status_short IN ('1H','2H','HT','ET','BT','P','SUSP','INT','LIVE') THEN 0 ELSE 1 END, elapsed DESC, league_name, home_team
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
        if r.get("home_score") is not None or r.get("away_score") is not None:
            score = f"{r.get('home_score') if r.get('home_score') is not None else 0}-{r.get('away_score') if r.get('away_score') is not None else 0}"
        tracker = {
            "fixture_id": fixture_id,
            "provider": "api_football",
            "source_label": "API-Football Pro",
            "stats": stats,
            "events": events,
            "pressure": pressure,
            "has_advanced_stats": bool(stats.get("available")),
            "has_events": bool(events),
            "ball_position_available": False,
            "dangerous_attacks_available": any(_stat_key(((s or {}).get("label") or "")) in {"dangerous_attacks", "dangerous-attacks"} for t in stats.get("teams") or [] for s in (t.get("raw") or [])),
            "legal_note": "Live tracker construido con datos API-Football autorizados. Sin inventar coordenadas de balón.",
        }
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
                "status": r.get("status_short") or r.get("status_long") or "LIVE",
                "minute": str(r.get("elapsed") or ""),
                "score": score,
                "home_score": r.get("home_score"),
                "away_score": r.get("away_score"),
                "venue": r.get("venue") or "",
                "source": "api_football_live",
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
    ensure_live_tracker_schema(db_path)
    conn = _connect(db_path)
    try:
        text = str(match_id or "")
        fixture_id = text[3:] if text.startswith("af-") else text
        row = conn.execute(
            "SELECT * FROM api_football_live_snapshots WHERE match_id=? OR fixture_id=? LIMIT 1",
            (text, fixture_id),
        ).fetchone()
        if not row:
            return {"available": False, "provider": "api_football", "message": "Sin live tracker API-Football para este partido."}
        r = _rowdict(row)
        stats = _stats_for_fixture(conn, str(r.get("fixture_id") or ""))
        events = _events_for_fixture(conn, str(r.get("fixture_id") or ""), limit=18)
        pressure = _pressure_from_stats(stats, r.get("home_team") or "", r.get("away_team") or "")
        return {
            "available": True,
            "provider": "api_football",
            "source_label": "API-Football Pro",
            "fixture_id": r.get("fixture_id"),
            "stats": stats,
            "events": events,
            "pressure": pressure,
            "has_advanced_stats": bool(stats.get("available")),
            "has_events": bool(events),
            "ball_position_available": False,
            "message": "Live tracker real disponible" if (stats.get("available") or events) else "Marcador live disponible, esperando eventos/estadísticas.",
            "legal_note": "API-Football autorizado. No se inventa ubicación exacta de balón.",
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
