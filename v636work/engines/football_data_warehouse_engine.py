"""V597 - Football Data Warehouse Pro.

Almacén propio de NeMeSiS para conservar desde hoy el rastro deportivo que la
aplicación recibe de fuentes autorizadas. No está pensado para revender datos
crudos de terceros: crea memoria operativa, snapshots y métricas derivadas para
SHARK, picks, ROI y futuras capas comerciales propias.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
DEFAULT_DAYS_BACK = 3
DEFAULT_DAYS_AHEAD = 7


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return json.dumps({"value": str(value)}, ensure_ascii=False)


def _safe_load(value: Any, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except Exception:
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _row_to_dict(row: sqlite3.Row | Mapping[str, Any] | None) -> Dict[str, Any]:
    if not row:
        return {}
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    return dict(row)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    try:
        return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())
    except sqlite3.Error:
        return False


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(conn, table):
        return set()
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _select_columns(conn: sqlite3.Connection, table: str, candidates: Iterable[str]) -> str:
    cols = _columns(conn, table)
    selected = [c for c in candidates if c in cols]
    return ", ".join(selected) if selected else "*"


def _order_expr(conn: sqlite3.Connection, table: str, candidates: Iterable[str], fallback: str = "rowid") -> str:
    cols = _columns(conn, table)
    selected = [c for c in candidates if c in cols]
    if not selected:
        return fallback
    return "COALESCE(" + ", ".join(selected) + ")" if len(selected) > 1 else selected[0]


def _hash_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(p or "") for p in parts)
    return f"{prefix}-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:18]


def ensure_football_warehouse_schema(db_path: str) -> Dict[str, Any]:
    conn = _connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS football_dw_sync_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT,
                source TEXT,
                scope TEXT,
                days_back INTEGER DEFAULT 0,
                days_ahead INTEGER DEFAULT 0,
                matches_inserted INTEGER DEFAULT 0,
                matches_updated INTEGER DEFAULT 0,
                events_inserted INTEGER DEFAULT 0,
                odds_inserted INTEGER DEFAULT 0,
                teams_inserted INTEGER DEFAULT 0,
                signals_inserted INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                error_message TEXT,
                payload_json TEXT
            );

            CREATE TABLE IF NOT EXISTS football_matches_history (
                id TEXT PRIMARY KEY,
                provider TEXT,
                external_id TEXT,
                internal_match_id TEXT,
                league_id TEXT,
                league_name TEXT,
                season TEXT,
                round_name TEXT,
                match_date TEXT,
                kickoff_iso TEXT,
                status TEXT,
                minute TEXT,
                home_team_id TEXT,
                away_team_id TEXT,
                home_team TEXT,
                away_team TEXT,
                home_score INTEGER,
                away_score INTEGER,
                venue TEXT,
                country TEXT,
                home_logo TEXT,
                away_logo TEXT,
                source_legal_note TEXT,
                payload_json TEXT,
                first_seen_at TEXT,
                last_seen_at TEXT,
                UNIQUE(provider, external_id)
            );

            CREATE TABLE IF NOT EXISTS football_match_events_history (
                id TEXT PRIMARY KEY,
                provider TEXT,
                external_match_id TEXT,
                internal_match_id TEXT,
                minute TEXT,
                event_type TEXT,
                team_name TEXT,
                player_name TEXT,
                assist_name TEXT,
                detail TEXT,
                payload_json TEXT,
                created_at TEXT,
                UNIQUE(provider, external_match_id, minute, event_type, team_name, player_name, detail)
            );

            CREATE TABLE IF NOT EXISTS football_lineups_history (
                id TEXT PRIMARY KEY,
                provider TEXT,
                external_match_id TEXT,
                internal_match_id TEXT,
                team_name TEXT,
                formation TEXT,
                player_name TEXT,
                position TEXT,
                shirt_number TEXT,
                is_starting INTEGER DEFAULT 0,
                payload_json TEXT,
                created_at TEXT,
                UNIQUE(provider, external_match_id, team_name, player_name, position)
            );

            CREATE TABLE IF NOT EXISTS football_standings_history (
                id TEXT PRIMARY KEY,
                provider TEXT,
                league_id TEXT,
                league_name TEXT,
                season TEXT,
                team_id TEXT,
                team_name TEXT,
                rank INTEGER,
                points INTEGER,
                played INTEGER,
                wins INTEGER,
                draws INTEGER,
                losses INTEGER,
                goals_for INTEGER,
                goals_against INTEGER,
                form TEXT,
                payload_json TEXT,
                snapshot_at TEXT,
                UNIQUE(provider, league_id, season, team_id, snapshot_at)
            );

            CREATE TABLE IF NOT EXISTS football_team_snapshots (
                id TEXT PRIMARY KEY,
                provider TEXT,
                team_id TEXT,
                team_name TEXT,
                league_name TEXT,
                country TEXT,
                stadium TEXT,
                logo_url TEXT,
                rating_snapshot REAL DEFAULT 70,
                payload_json TEXT,
                snapshot_at TEXT,
                UNIQUE(provider, team_id, snapshot_at)
            );

            CREATE TABLE IF NOT EXISTS football_odds_history (
                id TEXT PRIMARY KEY,
                provider TEXT,
                external_id TEXT,
                internal_match_id TEXT,
                league_name TEXT,
                market TEXT,
                bookmaker TEXT,
                home_team TEXT,
                away_team TEXT,
                home_price REAL,
                draw_price REAL,
                away_price REAL,
                payload_json TEXT,
                snapshot_at TEXT,
                UNIQUE(provider, external_id, market, bookmaker, snapshot_at)
            );

            CREATE TABLE IF NOT EXISTS football_shark_signals_history (
                id TEXT PRIMARY KEY,
                signal_type TEXT,
                internal_match_id TEXT,
                pick_id TEXT,
                league_name TEXT,
                market TEXT,
                selection TEXT,
                confidence INTEGER DEFAULT 0,
                shark_score INTEGER DEFAULT 0,
                value_pct REAL DEFAULT 0,
                risk_level TEXT,
                result_status TEXT,
                profit REAL DEFAULT 0,
                payload_json TEXT,
                created_at TEXT,
                UNIQUE(signal_type, pick_id, internal_match_id, market, selection, created_at)
            );

            CREATE TABLE IF NOT EXISTS football_derived_assets (
                id TEXT PRIMARY KEY,
                asset_type TEXT,
                entity_key TEXT,
                title TEXT,
                metric_value REAL DEFAULT 0,
                confidence INTEGER DEFAULT 0,
                sample_size INTEGER DEFAULT 0,
                payload_json TEXT,
                updated_at TEXT,
                UNIQUE(asset_type, entity_key)
            );
            """
        )
        conn.commit()
        return {"ok": True, "schema": "football_warehouse_ready"}
    finally:
        conn.close()


def _api_football_key() -> str:
    return os.getenv("API_FOOTBALL_KEY") or os.getenv("API_FOOTBALL_API_KEY") or ""


def _api_football_get(path: str, params: Optional[Mapping[str, Any]] = None, timeout: int = 18) -> Dict[str, Any]:
    key = _api_football_key()
    if not key:
        return {"ok": False, "error": "Falta API_FOOTBALL_KEY.", "response": []}
    query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v not in (None, "")})
    url = API_FOOTBALL_BASE_URL.rstrip("/") + "/" + path.strip("/")
    if query:
        url += "?" + query
    req = urllib.request.Request(url, headers={"x-apisports-key": key, "User-Agent": "NeMeSiS-SHARK-PRO/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", "replace"))
        return {"ok": not bool(payload.get("errors")), "payload": payload, "response": payload.get("response") or [], "errors": payload.get("errors") or []}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300], "response": []}


def _normalize_api_football_fixture(item: Mapping[str, Any]) -> Dict[str, Any]:
    fixture = item.get("fixture") or {}
    league = item.get("league") or {}
    teams = item.get("teams") or {}
    goals = item.get("goals") or {}
    status = fixture.get("status") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    venue = fixture.get("venue") or {}
    return {
        "provider": "api_football",
        "external_id": str(fixture.get("id") or ""),
        "internal_match_id": "",
        "league_id": str(league.get("id") or ""),
        "league_name": league.get("name") or "",
        "season": str(league.get("season") or ""),
        "round_name": league.get("round") or "",
        "match_date": str(fixture.get("date") or "")[:10],
        "kickoff_iso": fixture.get("date") or "",
        "status": status.get("short") or status.get("long") or "",
        "minute": str(status.get("elapsed") or ""),
        "home_team_id": str(home.get("id") or ""),
        "away_team_id": str(away.get("id") or ""),
        "home_team": home.get("name") or "Local",
        "away_team": away.get("name") or "Visitante",
        "home_score": goals.get("home"),
        "away_score": goals.get("away"),
        "venue": venue.get("name") or "",
        "country": league.get("country") or "",
        "home_logo": home.get("logo") or "",
        "away_logo": away.get("logo") or "",
        "source_legal_note": "API-Football via contrato/API autorizada. Uso interno NeMeSiS; no redistribuir feed crudo sin licencia.",
        "payload_json": _json(item),
    }


def _normalize_api_football_event(fixture_id: str, item: Mapping[str, Any]) -> Dict[str, Any]:
    time = item.get("time") or {}
    team = item.get("team") or {}
    player = item.get("player") or {}
    assist = item.get("assist") or {}
    return {
        "provider": "api_football",
        "external_match_id": str(fixture_id or ""),
        "internal_match_id": "",
        "minute": str(time.get("elapsed") or ""),
        "event_type": item.get("type") or "evento",
        "team_name": team.get("name") or "",
        "player_name": player.get("name") or "",
        "assist_name": assist.get("name") or "",
        "detail": item.get("detail") or item.get("comments") or "",
        "payload_json": _json(item),
    }


def _upsert_match(conn: sqlite3.Connection, item: Mapping[str, Any]) -> Tuple[int, int]:
    now = _now_iso()
    external_id = str(item.get("external_id") or item.get("internal_match_id") or _hash_id("match", item.get("home_team"), item.get("away_team"), item.get("kickoff_iso")))
    provider = str(item.get("provider") or "local")
    row_id = _hash_id("fdw-match", provider, external_id)
    exists = conn.execute("SELECT id FROM football_matches_history WHERE provider=? AND external_id=?", (provider, external_id)).fetchone()
    conn.execute(
        """
        INSERT INTO football_matches_history(id, provider, external_id, internal_match_id, league_id, league_name, season, round_name, match_date, kickoff_iso, status, minute, home_team_id, away_team_id, home_team, away_team, home_score, away_score, venue, country, home_logo, away_logo, source_legal_note, payload_json, first_seen_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(provider, external_id) DO UPDATE SET
          internal_match_id=excluded.internal_match_id,
          league_name=excluded.league_name,
          season=excluded.season,
          round_name=excluded.round_name,
          match_date=excluded.match_date,
          kickoff_iso=excluded.kickoff_iso,
          status=excluded.status,
          minute=excluded.minute,
          home_score=excluded.home_score,
          away_score=excluded.away_score,
          venue=excluded.venue,
          home_logo=COALESCE(NULLIF(excluded.home_logo,''), football_matches_history.home_logo),
          away_logo=COALESCE(NULLIF(excluded.away_logo,''), football_matches_history.away_logo),
          payload_json=excluded.payload_json,
          last_seen_at=excluded.last_seen_at
        """,
        (
            row_id, provider, external_id, item.get("internal_match_id") or "", item.get("league_id") or "", item.get("league_name") or "",
            item.get("season") or "", item.get("round_name") or "", item.get("match_date") or "", item.get("kickoff_iso") or "",
            item.get("status") or "", item.get("minute") or "", item.get("home_team_id") or "", item.get("away_team_id") or "",
            item.get("home_team") or "", item.get("away_team") or "", _as_int(item.get("home_score"), None), _as_int(item.get("away_score"), None),
            item.get("venue") or "", item.get("country") or "", item.get("home_logo") or "", item.get("away_logo") or "",
            item.get("source_legal_note") or "Fuente autorizada/cache interno NeMeSiS.", item.get("payload_json") or _json(item), now, now,
        ),
    )
    return (0, 1) if exists else (1, 0)


def _upsert_event(conn: sqlite3.Connection, item: Mapping[str, Any]) -> int:
    provider = str(item.get("provider") or "local")
    external_match_id = str(item.get("external_match_id") or item.get("internal_match_id") or "")
    row_id = _hash_id("fdw-event", provider, external_match_id, item.get("minute"), item.get("event_type"), item.get("team_name"), item.get("player_name"), item.get("detail"))
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO football_match_events_history(id, provider, external_match_id, internal_match_id, minute, event_type, team_name, player_name, assist_name, detail, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (row_id, provider, external_match_id, item.get("internal_match_id") or "", item.get("minute") or "", item.get("event_type") or "evento", item.get("team_name") or "", item.get("player_name") or "", item.get("assist_name") or "", item.get("detail") or "", item.get("payload_json") or _json(item), _now_iso()),
        )
        return 1 if conn.total_changes else 0
    except sqlite3.IntegrityError:
        return 0


def _upsert_team(conn: sqlite3.Connection, item: Mapping[str, Any]) -> int:
    snapshot = _now_iso()[:10]
    provider = str(item.get("provider") or "local")
    team_id = str(item.get("team_id") or item.get("id") or item.get("name") or item.get("team_name") or "")
    row_id = _hash_id("fdw-team", provider, team_id, snapshot)
    conn.execute(
        """
        INSERT OR IGNORE INTO football_team_snapshots(id, provider, team_id, team_name, league_name, country, stadium, logo_url, rating_snapshot, payload_json, snapshot_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (row_id, provider, team_id, item.get("team_name") or item.get("name") or "", item.get("league_name") or item.get("league") or "", item.get("country") or "", item.get("stadium") or item.get("venue") or "", item.get("logo_url") or item.get("logo") or "", _as_float(item.get("rating_snapshot"), 70.0), item.get("payload_json") or _json(item), snapshot),
    )
    return 1 if conn.total_changes else 0


def _snapshot_local_matches(conn: sqlite3.Connection, limit: int) -> Tuple[int, int]:
    if not _table_exists(conn, "matches"):
        return 0, 0
    cols = _select_columns(conn, "matches", ["id", "external_id", "league_name", "competition_name", "competition_id", "season", "round", "match_date", "kickoff_iso", "match_time", "kickoff_time", "status", "minute", "home_team_id", "away_team_id", "home_team", "away_team", "home_score", "away_score", "venue", "country", "home_logo", "away_logo", "source", "raw_json"])
    inserted = updated = 0
    order_by = _order_expr(conn, "matches", ["kickoff_iso", "match_date", "match_time", "updated_at", "id"])
    for row in conn.execute(f"SELECT {cols} FROM matches ORDER BY {order_by} DESC LIMIT ?", (limit,)).fetchall():
        r = _row_to_dict(row)
        payload = _safe_load(r.get("raw_json"), r)
        item = {
            "provider": r.get("source") or "internal_matches",
            "external_id": r.get("external_id") or r.get("id"),
            "internal_match_id": r.get("id") or "",
            "league_id": r.get("competition_id") or "",
            "league_name": r.get("league_name") or r.get("competition_name") or "",
            "season": r.get("season") or "",
            "round_name": r.get("round") or "",
            "match_date": str(r.get("match_date") or r.get("kickoff_iso") or r.get("match_time") or "")[:10],
            "kickoff_iso": r.get("kickoff_iso") or r.get("match_time") or r.get("kickoff_time") or "",
            "status": r.get("status") or "",
            "minute": r.get("minute") or "",
            "home_team_id": r.get("home_team_id") or "",
            "away_team_id": r.get("away_team_id") or "",
            "home_team": r.get("home_team") or "",
            "away_team": r.get("away_team") or "",
            "home_score": r.get("home_score"),
            "away_score": r.get("away_score"),
            "venue": r.get("venue") or "",
            "country": r.get("country") or "",
            "home_logo": r.get("home_logo") or "",
            "away_logo": r.get("away_logo") or "",
            "source_legal_note": "Snapshot interno desde matches. Mantener según licencia de la fuente original.",
            "payload_json": _json(payload),
        }
        ins, upd = _upsert_match(conn, item)
        inserted += ins
        updated += upd
    return inserted, updated


def _snapshot_local_events(conn: sqlite3.Connection, limit: int) -> int:
    total = 0
    for table in ("live_event_history", "match_timeline"):
        if not _table_exists(conn, table):
            continue
        cols = _select_columns(conn, table, ["match_id", "minute", "event_type", "title", "detail", "source", "payload_json", "created_at"])
        order_by = _order_expr(conn, table, ["created_at"], "rowid")
        for row in conn.execute(f"SELECT {cols} FROM {table} ORDER BY {order_by} DESC LIMIT ?", (limit,)).fetchall():
            r = _row_to_dict(row)
            total += _upsert_event(conn, {
                "provider": r.get("source") or table,
                "external_match_id": r.get("match_id") or "",
                "internal_match_id": r.get("match_id") or "",
                "minute": r.get("minute") or "",
                "event_type": r.get("event_type") or r.get("title") or "evento",
                "team_name": "",
                "player_name": "",
                "assist_name": "",
                "detail": r.get("detail") or r.get("title") or "",
                "payload_json": r.get("payload_json") or _json(r),
            })
    return total


def _snapshot_local_teams(conn: sqlite3.Connection, limit: int) -> int:
    if not _table_exists(conn, "teams"):
        return 0
    cols = _select_columns(conn, "teams", ["id", "external_id", "name", "league", "country", "stadium", "logo_url", "raw_json"])
    total = 0
    order_by = _order_expr(conn, "teams", ["updated_at", "last_sync_at", "id"])
    for row in conn.execute(f"SELECT {cols} FROM teams ORDER BY {order_by} DESC LIMIT ?", (limit,)).fetchall():
        r = _row_to_dict(row)
        total += _upsert_team(conn, {
            "provider": "internal_teams",
            "team_id": r.get("external_id") or r.get("id") or r.get("name"),
            "team_name": r.get("name") or "",
            "league_name": r.get("league") or "",
            "country": r.get("country") or "",
            "stadium": r.get("stadium") or "",
            "logo_url": r.get("logo_url") or "",
            "payload_json": r.get("raw_json") or _json(r),
        })
    return total


def _snapshot_local_odds(conn: sqlite3.Connection, limit: int) -> int:
    if not _table_exists(conn, "odds_snapshots"):
        return 0
    cols = _select_columns(conn, "odds_snapshots", ["match_id", "external_id", "source", "league_name", "bookmaker", "market", "home_team", "away_team", "home_price", "draw_price", "away_price", "payload_json", "created_at"])
    total = 0
    order_by = _order_expr(conn, "odds_snapshots", ["created_at"], "rowid")
    for row in conn.execute(f"SELECT {cols} FROM odds_snapshots ORDER BY {order_by} DESC LIMIT ?", (limit,)).fetchall():
        r = _row_to_dict(row)
        snapshot = str(r.get("created_at") or _now_iso())[:19]
        row_id = _hash_id("fdw-odds", r.get("source") or "odds", r.get("external_id") or r.get("match_id"), r.get("market"), r.get("bookmaker"), snapshot)
        conn.execute(
            """
            INSERT OR IGNORE INTO football_odds_history(id, provider, external_id, internal_match_id, league_name, market, bookmaker, home_team, away_team, home_price, draw_price, away_price, payload_json, snapshot_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (row_id, r.get("source") or "the_odds_api", r.get("external_id") or "", r.get("match_id") or "", r.get("league_name") or "", r.get("market") or "h2h", r.get("bookmaker") or "", r.get("home_team") or "", r.get("away_team") or "", _as_float(r.get("home_price"), 0), _as_float(r.get("draw_price"), 0), _as_float(r.get("away_price"), 0), r.get("payload_json") or _json(r), snapshot),
        )
        total += 1 if conn.total_changes else 0
    return total


def _snapshot_shark_signals(conn: sqlite3.Connection, limit: int) -> int:
    total = 0
    if _table_exists(conn, "picks"):
        cols = _select_columns(conn, "picks", ["id", "match_id", "league_name", "market", "selection", "confidence", "score", "odds", "risk_level", "result_status", "status", "profit", "raw_json", "created_at", "published_at"])
        order_by = _order_expr(conn, "picks", ["published_at", "created_at", "id"])
        for row in conn.execute(f"SELECT {cols} FROM picks ORDER BY {order_by} DESC LIMIT ?", (limit,)).fetchall():
            r = _row_to_dict(row)
            created = str(r.get("published_at") or r.get("created_at") or _now_iso())[:19]
            row_id = _hash_id("fdw-signal", "pick", r.get("id"), r.get("match_id"), r.get("market"), r.get("selection"), created)
            conn.execute(
                """
                INSERT OR IGNORE INTO football_shark_signals_history(id, signal_type, internal_match_id, pick_id, league_name, market, selection, confidence, shark_score, value_pct, risk_level, result_status, profit, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (row_id, "pick", r.get("match_id") or "", r.get("id") or "", r.get("league_name") or "", r.get("market") or "", r.get("selection") or "", _as_int(r.get("confidence"), 0), _as_int(r.get("score"), _as_int(r.get("confidence"), 0)), 0.0, r.get("risk_level") or "", r.get("result_status") or r.get("status") or "", _as_float(r.get("profit"), 0), r.get("raw_json") or _json(r), created),
            )
            total += 1 if conn.total_changes else 0
    return total


def _sync_api_football_fixtures(conn: sqlite3.Connection, days_back: int, days_ahead: int, limit: int) -> Tuple[int, int, int, List[str]]:
    if not _api_football_key() or not _env_bool("ENABLE_API_FOOTBALL_PROVIDER", True):
        return 0, 0, 0, []
    inserted = updated = events = 0
    errors: List[str] = []
    today = date.today()
    max_days = max(0, min(14, int(days_back))) + max(0, min(21, int(days_ahead))) + 1
    per_day_limit = max(10, int(limit / max(1, max_days)))
    days = [today + timedelta(days=offset) for offset in range(-max(0, min(14, days_back)), max(0, min(21, days_ahead)) + 1)]
    processed = 0
    for day in days:
        if processed >= limit:
            break
        payload = _api_football_get("fixtures", {"date": day.isoformat(), "timezone": os.getenv("APP_TIMEZONE", "Europe/Madrid")})
        if not payload.get("ok"):
            errors.append(str(payload.get("error") or payload.get("errors") or "error_api_football")[:220])
            continue
        for fixture in (payload.get("response") or [])[:per_day_limit]:
            if processed >= limit:
                break
            normalized = _normalize_api_football_fixture(fixture)
            ins, upd = _upsert_match(conn, normalized)
            inserted += ins
            updated += upd
            processed += 1
            status = str(normalized.get("status") or "").upper()
            # Solo pedimos eventos si el partido está en directo/finalizado para no gastar llamadas innecesarias.
            if normalized.get("external_id") and status in {"1H", "2H", "HT", "FT", "AET", "PEN", "LIVE"} and events < max(10, limit // 2):
                ev_payload = _api_football_get("fixtures/events", {"fixture": normalized["external_id"]})
                if ev_payload.get("ok"):
                    for event in ev_payload.get("response") or []:
                        events += _upsert_event(conn, _normalize_api_football_event(normalized["external_id"], event))
                else:
                    errors.append(str(ev_payload.get("error") or ev_payload.get("errors") or "error_eventos")[:180])
    return inserted, updated, events, errors[:12]


def rebuild_derived_assets(db_path: str) -> Dict[str, Any]:
    ensure_football_warehouse_schema(db_path)
    conn = _connect(db_path)
    now = _now_iso()
    created = 0
    try:
        # Activos propios por liga: volumen + señales SHARK.
        league_rows = conn.execute(
            """
            SELECT COALESCE(league_name,'Sin liga') AS league_name,
                   COUNT(*) AS matches_total,
                   SUM(CASE WHEN status IN ('FT','Finalizado','Match Finished') THEN 1 ELSE 0 END) AS finished_total
            FROM football_matches_history
            GROUP BY COALESCE(league_name,'Sin liga')
            ORDER BY matches_total DESC
            LIMIT 50
            """
        ).fetchall()
        for row in league_rows:
            key = row["league_name"] or "Sin liga"
            sample = int(row["matches_total"] or 0)
            score = min(100, 35 + sample)
            conn.execute(
                """
                INSERT INTO football_derived_assets(id, asset_type, entity_key, title, metric_value, confidence, sample_size, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(asset_type, entity_key) DO UPDATE SET metric_value=excluded.metric_value, confidence=excluded.confidence, sample_size=excluded.sample_size, payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """,
                (_hash_id("asset", "league_depth", key), "league_depth", key, f"Profundidad histórica {key}", float(sample), score, sample, _json(dict(row)), now),
            )
            created += 1

        market_rows = conn.execute(
            """
            SELECT COALESCE(market,'Sin mercado') AS market,
                   COUNT(*) AS sample_size,
                   AVG(CASE WHEN lower(result_status) IN ('won','ganado','win') THEN 1.0 WHEN lower(result_status) IN ('lost','perdido','loss') THEN 0.0 ELSE NULL END) AS winrate,
                   SUM(COALESCE(profit,0)) AS profit
            FROM football_shark_signals_history
            GROUP BY COALESCE(market,'Sin mercado')
            ORDER BY sample_size DESC
            LIMIT 50
            """
        ).fetchall()
        for row in market_rows:
            key = row["market"] or "Sin mercado"
            sample = int(row["sample_size"] or 0)
            profit = float(row["profit"] or 0)
            confidence = min(100, 40 + sample + (10 if profit > 0 else 0))
            conn.execute(
                """
                INSERT INTO football_derived_assets(id, asset_type, entity_key, title, metric_value, confidence, sample_size, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(asset_type, entity_key) DO UPDATE SET metric_value=excluded.metric_value, confidence=excluded.confidence, sample_size=excluded.sample_size, payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """,
                (_hash_id("asset", "market_signal", key), "market_signal", key, f"Señal SHARK {key}", profit, confidence, sample, _json(dict(row)), now),
            )
            created += 1
        conn.commit()
        return {"ok": True, "derived_assets": created}
    finally:
        conn.close()


def sync_football_data_warehouse(db_path: str, limit: int = 500, days_back: int = DEFAULT_DAYS_BACK, days_ahead: int = DEFAULT_DAYS_AHEAD, include_api_football: bool = True) -> Dict[str, Any]:
    """Sincroniza el warehouse propio con datos locales y, si está configurado, API-Football.

    La función está diseñada para ejecutarse de forma repetida por scheduler: usa
    UPSERT/IGNORE, conserva snapshots y evita romper si falta una tabla antigua.
    """
    ensure_football_warehouse_schema(db_path)
    conn = _connect(db_path)
    started = _now_iso()
    run_id = None
    errors: List[str] = []
    metrics = {
        "matches_inserted": 0,
        "matches_updated": 0,
        "events_inserted": 0,
        "odds_inserted": 0,
        "teams_inserted": 0,
        "signals_inserted": 0,
        "api_football_matches_inserted": 0,
        "api_football_matches_updated": 0,
        "api_football_events_inserted": 0,
    }
    try:
        cur = conn.execute(
            "INSERT INTO football_dw_sync_runs(started_at, status, source, scope, days_back, days_ahead, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (started, "RUNNING", "football_dw", "full", int(days_back), int(days_ahead), _json({"limit": limit, "include_api_football": include_api_football})),
        )
        run_id = cur.lastrowid
        ins, upd = _snapshot_local_matches(conn, limit)
        metrics["matches_inserted"] += ins
        metrics["matches_updated"] += upd
        metrics["events_inserted"] += _snapshot_local_events(conn, limit)
        metrics["teams_inserted"] += _snapshot_local_teams(conn, limit)
        metrics["odds_inserted"] += _snapshot_local_odds(conn, limit)
        metrics["signals_inserted"] += _snapshot_shark_signals(conn, limit)

        if include_api_football:
            api_ins, api_upd, api_events, api_errors = _sync_api_football_fixtures(conn, days_back, days_ahead, limit)
            metrics["api_football_matches_inserted"] = api_ins
            metrics["api_football_matches_updated"] = api_upd
            metrics["api_football_events_inserted"] = api_events
            metrics["matches_inserted"] += api_ins
            metrics["matches_updated"] += api_upd
            metrics["events_inserted"] += api_events
            errors.extend(api_errors)
        conn.commit()
    except Exception as exc:
        errors.append(str(exc)[:300])
    finally:
        finished = _now_iso()
        try:
            status = "OK" if not errors else ("PARTIAL" if any(metrics.values()) else "ERROR")
            conn.execute(
                """
                UPDATE football_dw_sync_runs
                SET finished_at=?, status=?, matches_inserted=?, matches_updated=?, events_inserted=?, odds_inserted=?, teams_inserted=?, signals_inserted=?, errors_count=?, error_message=?, payload_json=?
                WHERE id=?
                """,
                (finished, status, metrics["matches_inserted"], metrics["matches_updated"], metrics["events_inserted"], metrics["odds_inserted"], metrics["teams_inserted"], metrics["signals_inserted"], len(errors), "; ".join(errors[:4])[:800], _json(metrics), run_id),
            )
            conn.commit()
        except Exception:
            pass
        conn.close()
    derived = rebuild_derived_assets(db_path)
    return {
        "ok": not errors,
        "source": "football_dw",
        "sync_type": "football_data_warehouse",
        "processed": sum(metrics.values()),
        "inserted": metrics["matches_inserted"] + metrics["events_inserted"] + metrics["odds_inserted"] + metrics["teams_inserted"] + metrics["signals_inserted"],
        "updated": metrics["matches_updated"],
        "skipped": 0,
        "errors": errors[:12],
        "metrics": metrics,
        "derived": derived,
        "started_at": started,
        "finished_at": _now_iso(),
        "legal_note": "Warehouse interno para operar NeMeSiS y crear métricas SHARK propias. No redistribuir datos crudos de terceros sin licencia.",
    }


def football_warehouse_summary(db_path: str) -> Dict[str, Any]:
    ensure_football_warehouse_schema(db_path)
    conn = _connect(db_path)
    try:
        def count(table: str, where: str = "1=1") -> int:
            try:
                return int(conn.execute(f"SELECT COUNT(*) AS total FROM {table} WHERE {where}").fetchone()["total"] or 0)
            except sqlite3.Error:
                return 0

        latest_run = _row_to_dict(conn.execute("SELECT * FROM football_dw_sync_runs ORDER BY id DESC LIMIT 1").fetchone())
        recent_runs = [_row_to_dict(r) for r in conn.execute("SELECT * FROM football_dw_sync_runs ORDER BY id DESC LIMIT 8").fetchall()]
        top_leagues = [_row_to_dict(r) for r in conn.execute("SELECT * FROM football_derived_assets WHERE asset_type='league_depth' ORDER BY metric_value DESC LIMIT 8").fetchall()]
        market_assets = [_row_to_dict(r) for r in conn.execute("SELECT * FROM football_derived_assets WHERE asset_type='market_signal' ORDER BY confidence DESC, sample_size DESC LIMIT 8").fetchall()]
        api_football_configured = bool(_api_football_key())
        matches_total = count("football_matches_history")
        events_total = count("football_match_events_history")
        teams_total = count("football_team_snapshots")
        odds_total = count("football_odds_history")
        signals_total = count("football_shark_signals_history")
        readiness = 20
        if matches_total:
            readiness += 20
        if teams_total:
            readiness += 10
        if odds_total:
            readiness += 15
        if signals_total:
            readiness += 15
        if events_total:
            readiness += 10
        if api_football_configured:
            readiness += 10
        return {
            "ok": True,
            "readiness_score": min(100, readiness),
            "matches_total": matches_total,
            "events_total": events_total,
            "lineups_total": count("football_lineups_history"),
            "standings_total": count("football_standings_history"),
            "teams_total": teams_total,
            "odds_total": odds_total,
            "signals_total": signals_total,
            "derived_assets_total": count("football_derived_assets"),
            "api_football_configured": api_football_configured,
            "api_football_enabled": _env_bool("ENABLE_API_FOOTBALL_PROVIDER", True),
            "latest_run": latest_run,
            "recent_runs": recent_runs,
            "top_leagues": top_leagues,
            "market_assets": market_assets,
            "recommended_env": {
                "API_FOOTBALL_KEY": "clave pro de API-Football",
                "ENABLE_API_FOOTBALL_PROVIDER": "true",
                "FOOTBALL_WAREHOUSE_REFRESH_HOURS": os.getenv("FOOTBALL_WAREHOUSE_REFRESH_HOURS", "6"),
            },
            "legal_note": "Guardar para uso interno, aprendizaje, predicciones y métricas propias. Revisar contrato si algún día se quiere redistribuir datos crudos.",
        }
    finally:
        conn.close()


__all__ = [
    "ensure_football_warehouse_schema",
    "sync_football_data_warehouse",
    "football_warehouse_summary",
    "rebuild_derived_assets",
]
