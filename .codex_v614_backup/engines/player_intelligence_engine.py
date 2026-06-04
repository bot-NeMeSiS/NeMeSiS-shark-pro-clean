"""V602 - Player Intelligence Engine.

Capa ligera para convertir datos de jugadores autorizados (API-Football Pro y
warehouse interno) en señales propias de NeMeSiS SHARK.

No redistribuye feeds crudos: conserva datos para operar la app, mejorar los
pronósticos y crear métricas derivadas propias.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

LEGAL_NOTE = "Datos recibidos mediante API autorizada. Uso interno NeMeSiS/SHARK; no redistribuir feed crudo sin licencia."


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


def _load_json(value: Any, default: Any = None) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    try:
        return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())
    except sqlite3.Error:
        return False


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(conn, table):
        return set()
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except Exception:
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", ".").replace("%", ""))
    except Exception:
        return default


def _rowdict(row: sqlite3.Row | Mapping[str, Any] | None) -> Dict[str, Any]:
    if not row:
        return {}
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    return dict(row)


def _upsert_profile(conn: sqlite3.Connection, *, player_id: str, player_name: str, team_id: str = "", team_name: str = "", position: str = "", source: str = "api_football") -> int:
    if not (player_id or player_name):
        return 0
    now = _now_iso()
    profile_id = player_id or f"name:{player_name.lower()}:{team_id or team_name.lower()}"
    before = conn.total_changes
    conn.execute(
        """
        INSERT INTO player_profiles(id, player_id, player_name, team_id, team_name, position, source, payload_json, first_seen_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            player_name=COALESCE(NULLIF(excluded.player_name,''), player_profiles.player_name),
            team_id=COALESCE(NULLIF(excluded.team_id,''), player_profiles.team_id),
            team_name=COALESCE(NULLIF(excluded.team_name,''), player_profiles.team_name),
            position=COALESCE(NULLIF(excluded.position,''), player_profiles.position),
            source=COALESCE(NULLIF(excluded.source,''), player_profiles.source),
            payload_json=excluded.payload_json,
            last_seen_at=excluded.last_seen_at
        """,
        (profile_id, player_id or "", player_name or "", team_id or "", team_name or "", position or "", source, _json({"legal_note": LEGAL_NOTE}), now, now),
    )
    return 1 if conn.total_changes > before else 0


def ensure_player_intelligence_schema(db_path: str) -> Dict[str, Any]:
    conn = _connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS player_profiles (
                id TEXT PRIMARY KEY,
                player_id TEXT,
                player_name TEXT,
                team_id TEXT,
                team_name TEXT,
                position TEXT,
                age INTEGER,
                nationality TEXT,
                source TEXT DEFAULT 'api_football',
                payload_json TEXT,
                first_seen_at TEXT,
                last_seen_at TEXT
            );

            CREATE TABLE IF NOT EXISTS player_availability_history (
                id TEXT PRIMARY KEY,
                player_id TEXT,
                player_name TEXT,
                team_id TEXT,
                team_name TEXT,
                match_id TEXT,
                fixture_id TEXT,
                status TEXT,
                reason TEXT,
                severity TEXT,
                impact_score REAL DEFAULT 0,
                payload_json TEXT,
                captured_at TEXT,
                UNIQUE(player_id, player_name, team_id, fixture_id, status, reason, captured_at)
            );

            CREATE TABLE IF NOT EXISTS player_match_stat_snapshots (
                id TEXT PRIMARY KEY,
                player_id TEXT,
                player_name TEXT,
                team_id TEXT,
                team_name TEXT,
                fixture_id TEXT,
                position TEXT,
                is_starting INTEGER DEFAULT 0,
                minutes INTEGER DEFAULT 0,
                goals INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                cards INTEGER DEFAULT 0,
                rating REAL DEFAULT 0,
                payload_json TEXT,
                captured_at TEXT,
                UNIQUE(player_id, player_name, team_id, fixture_id, captured_at)
            );

            CREATE TABLE IF NOT EXISTS player_team_impact_signals (
                id TEXT PRIMARY KEY,
                team_id TEXT,
                team_name TEXT,
                fixture_id TEXT,
                signal_type TEXT,
                title TEXT,
                impact_score REAL DEFAULT 0,
                confidence INTEGER DEFAULT 0,
                sample_size INTEGER DEFAULT 0,
                payload_json TEXT,
                updated_at TEXT,
                UNIQUE(team_id, fixture_id, signal_type)
            );

            CREATE TABLE IF NOT EXISTS player_intelligence_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT,
                finished_at TEXT,
                status TEXT,
                profiles_upserted INTEGER DEFAULT 0,
                availability_inserted INTEGER DEFAULT 0,
                stat_snapshots_inserted INTEGER DEFAULT 0,
                impact_signals_inserted INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                error_message TEXT,
                payload_json TEXT
            );
            """
        )
        conn.commit()
        return {"ok": True, "schema": "player_intelligence_ready"}
    finally:
        conn.close()


def _import_profiles_from_lineups(conn: sqlite3.Connection, limit: int = 1000) -> int:
    if not _table_exists(conn, "api_football_lineups_deep"):
        return 0
    inserted = 0
    rows = conn.execute(
        """
        SELECT player_id, player_name, team_id, team_name, position, fixture_id, is_starting, payload_json
        FROM api_football_lineups_deep
        ORDER BY captured_at DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    captured = _now_iso()
    for row in rows:
        r = _rowdict(row)
        inserted += _upsert_profile(
            conn,
            player_id=str(r.get("player_id") or ""),
            player_name=r.get("player_name") or "",
            team_id=str(r.get("team_id") or ""),
            team_name=r.get("team_name") or "",
            position=r.get("position") or "",
        )
        sid = f"pms:{r.get('fixture_id') or ''}:{r.get('team_id') or ''}:{r.get('player_id') or r.get('player_name')}:{captured}"
        conn.execute(
            """
            INSERT OR IGNORE INTO player_match_stat_snapshots(id, player_id, player_name, team_id, team_name, fixture_id, position, is_starting, payload_json, captured_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sid, str(r.get("player_id") or ""), r.get("player_name") or "", str(r.get("team_id") or ""), r.get("team_name") or "", str(r.get("fixture_id") or ""), r.get("position") or "", _as_int(r.get("is_starting"), 0), r.get("payload_json") or _json(r), captured),
        )
    return inserted


def _import_availability_from_injuries(conn: sqlite3.Connection, limit: int = 1000) -> int:
    if not _table_exists(conn, "api_football_injuries_history"):
        return 0
    inserted = 0
    rows = conn.execute(
        """
        SELECT fixture_id, team_id, team_name, player_id, player_name, type, reason, payload_json, captured_at
        FROM api_football_injuries_history
        ORDER BY captured_at DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    for row in rows:
        r = _rowdict(row)
        inserted += _upsert_profile(
            conn,
            player_id=str(r.get("player_id") or ""),
            player_name=r.get("player_name") or "",
            team_id=str(r.get("team_id") or ""),
            team_name=r.get("team_name") or "",
            position="",
        )
        reason = r.get("reason") or r.get("type") or "baja"
        severity = "alta" if any(w in str(reason).lower() for w in ["ruptura", "sanc", "suspend", "injury", "lesión", "lesion"]) else "media"
        impact = -6.0 if severity == "alta" else -3.0
        aid = f"avail:{r.get('fixture_id') or ''}:{r.get('team_id') or ''}:{r.get('player_id') or r.get('player_name')}:{reason}:{r.get('captured_at') or _now_iso()}"
        before = conn.total_changes
        conn.execute(
            """
            INSERT OR IGNORE INTO player_availability_history(id, player_id, player_name, team_id, team_name, fixture_id, status, reason, severity, impact_score, payload_json, captured_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (aid, str(r.get("player_id") or ""), r.get("player_name") or "", str(r.get("team_id") or ""), r.get("team_name") or "", str(r.get("fixture_id") or ""), "baja", reason, severity, impact, r.get("payload_json") or _json(r), r.get("captured_at") or _now_iso()),
        )
        inserted += 1 if conn.total_changes > before else 0
    return inserted


def _build_impact_signals(conn: sqlite3.Connection, limit: int = 500) -> int:
    inserted = 0
    now = _now_iso()
    if _table_exists(conn, "player_availability_history"):
        rows = conn.execute(
            """
            SELECT fixture_id, team_id, team_name, COUNT(*) AS total_absences, SUM(impact_score) AS total_impact
            FROM player_availability_history
            WHERE status IN ('baja','duda','sancionado','lesionado')
            GROUP BY fixture_id, team_id, team_name
            ORDER BY ABS(COALESCE(SUM(impact_score),0)) DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        for row in rows:
            r = _rowdict(row)
            total = _as_int(r.get("total_absences"), 0)
            impact = round(_as_float(r.get("total_impact"), 0.0), 2)
            if total <= 0:
                continue
            title = f"{total} baja(s) detectada(s) en {r.get('team_name') or 'equipo'}"
            signal_id = f"pis:availability:{r.get('fixture_id') or ''}:{r.get('team_id') or r.get('team_name')}"
            before = conn.total_changes
            conn.execute(
                """
                INSERT INTO player_team_impact_signals(id, team_id, team_name, fixture_id, signal_type, title, impact_score, confidence, sample_size, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(team_id, fixture_id, signal_type) DO UPDATE SET
                    title=excluded.title,
                    impact_score=excluded.impact_score,
                    confidence=excluded.confidence,
                    sample_size=excluded.sample_size,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (signal_id, str(r.get("team_id") or ""), r.get("team_name") or "", str(r.get("fixture_id") or ""), "availability", title, impact, min(95, 50 + total * 10), total, _json({"legal_note": LEGAL_NOTE, "source": "player_availability_history", **r}), now),
            )
            inserted += 1 if conn.total_changes > before else 0
    if _table_exists(conn, "player_match_stat_snapshots"):
        rows = conn.execute(
            """
            SELECT fixture_id, team_id, team_name, SUM(is_starting) AS starters, COUNT(*) AS players
            FROM player_match_stat_snapshots
            GROUP BY fixture_id, team_id, team_name
            HAVING COUNT(*) >= 7
            ORDER BY players DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        for row in rows:
            r = _rowdict(row)
            players = _as_int(r.get("players"), 0)
            starters = _as_int(r.get("starters"), 0)
            title = f"Alineación detectada: {starters or players} jugador(es) registrados"
            signal_id = f"pis:lineup:{r.get('fixture_id') or ''}:{r.get('team_id') or r.get('team_name')}"
            before = conn.total_changes
            conn.execute(
                """
                INSERT INTO player_team_impact_signals(id, team_id, team_name, fixture_id, signal_type, title, impact_score, confidence, sample_size, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(team_id, fixture_id, signal_type) DO UPDATE SET
                    title=excluded.title,
                    impact_score=excluded.impact_score,
                    confidence=excluded.confidence,
                    sample_size=excluded.sample_size,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (signal_id, str(r.get("team_id") or ""), r.get("team_name") or "", str(r.get("fixture_id") or ""), "lineup_depth", title, min(8.0, players / 2.0), min(90, 40 + players * 3), players, _json({"legal_note": LEGAL_NOTE, "source": "player_match_stat_snapshots", **r}), now),
            )
            inserted += 1 if conn.total_changes > before else 0
    return inserted


def rebuild_player_intelligence(db_path: str, limit: int = 1000) -> Dict[str, Any]:
    ensure_player_intelligence_schema(db_path)
    conn = _connect(db_path)
    started = _now_iso()
    errors: List[str] = []
    profiles = availability = stats = signals = 0
    try:
        run_id = None
        try:
            cur = conn.execute("INSERT INTO player_intelligence_runs(started_at, status) VALUES (?, ?)", (started, "running"))
            run_id = cur.lastrowid
        except sqlite3.Error:
            run_id = None
        try:
            profiles = _import_profiles_from_lineups(conn, limit=limit)
        except Exception as exc:
            errors.append(f"lineups: {str(exc)[:160]}")
        try:
            availability = _import_availability_from_injuries(conn, limit=limit)
        except Exception as exc:
            errors.append(f"injuries: {str(exc)[:160]}")
        # snapshots se insertan dentro de lineups; se cuenta total reciente para informe.
        try:
            signals = _build_impact_signals(conn, limit=limit)
        except Exception as exc:
            errors.append(f"signals: {str(exc)[:160]}")
        stats = _count(conn, "player_match_stat_snapshots")
        status = "OK" if not errors else "PARTIAL"
        finished = _now_iso()
        if run_id:
            conn.execute(
                """
                UPDATE player_intelligence_runs
                SET finished_at=?, status=?, profiles_upserted=?, availability_inserted=?, stat_snapshots_inserted=?, impact_signals_inserted=?, errors_count=?, error_message=?, payload_json=?
                WHERE id=?
                """,
                (finished, status, profiles, availability, stats, signals, len(errors), "; ".join(errors[:3]), _json({"legal_note": LEGAL_NOTE}), run_id),
            )
        conn.commit()
        return {"ok": not errors, "status": status, "profiles_upserted": profiles, "availability_inserted": availability, "stat_snapshots_total": stats, "impact_signals_inserted": signals, "errors": errors}
    finally:
        conn.close()


def _count(conn: sqlite3.Connection, table: str, where: str = "", params: Iterable[Any] = ()) -> int:
    if not _table_exists(conn, table):
        return 0
    try:
        sql = f"SELECT COUNT(*) AS total FROM {table}"
        if where:
            sql += " WHERE " + where
        row = conn.execute(sql, tuple(params)).fetchone()
        return _as_int(row["total"] if row else 0, 0)
    except sqlite3.Error:
        return 0


def player_intelligence_for_fixture(db_path: str, fixture_id: str = "", team_id: str = "") -> Dict[str, Any]:
    ensure_player_intelligence_schema(db_path)
    conn = _connect(db_path)
    try:
        params: List[Any] = []
        where = []
        if fixture_id:
            where.append("fixture_id=?"); params.append(str(fixture_id))
        if team_id:
            where.append("team_id=?"); params.append(str(team_id))
        clause = " AND ".join(where) if where else "1=1"
        signals = [_rowdict(r) for r in conn.execute(f"SELECT * FROM player_team_impact_signals WHERE {clause} ORDER BY ABS(impact_score) DESC LIMIT 12", params).fetchall()]
        availability = [_rowdict(r) for r in conn.execute(f"SELECT * FROM player_availability_history WHERE {clause} ORDER BY captured_at DESC LIMIT 12", params).fetchall()]
        lineups = [_rowdict(r) for r in conn.execute(f"SELECT * FROM player_match_stat_snapshots WHERE {clause} ORDER BY is_starting DESC, player_name ASC LIMIT 30", params).fetchall()]
        total_impact = round(sum(_as_float(s.get("impact_score"), 0.0) for s in signals), 2)
        return {"ok": True, "fixture_id": fixture_id, "team_id": team_id, "impact_score": total_impact, "signals": signals, "availability": availability, "lineups": lineups}
    finally:
        conn.close()


def player_intelligence_summary(db_path: str) -> Dict[str, Any]:
    ensure_player_intelligence_schema(db_path)
    conn = _connect(db_path)
    try:
        profiles = _count(conn, "player_profiles")
        availability = _count(conn, "player_availability_history")
        stat_snapshots = _count(conn, "player_match_stat_snapshots")
        signals = _count(conn, "player_team_impact_signals")
        lineups_source = _count(conn, "api_football_lineups_deep")
        injuries_source = _count(conn, "api_football_injuries_history")
        last_run = _rowdict(conn.execute("SELECT * FROM player_intelligence_runs ORDER BY id DESC LIMIT 1").fetchone()) if _table_exists(conn, "player_intelligence_runs") else {}
        readiness = 0
        if lineups_source or injuries_source:
            readiness += 25
        if profiles:
            readiness += 25
        if availability:
            readiness += 20
        if signals:
            readiness += 20
        if last_run:
            readiness += 10
        readiness = min(100, readiness)
        top_signals = [_rowdict(r) for r in conn.execute("SELECT team_name, fixture_id, signal_type, title, impact_score, confidence, sample_size FROM player_team_impact_signals ORDER BY ABS(impact_score) DESC, updated_at DESC LIMIT 8").fetchall()] if _table_exists(conn, "player_team_impact_signals") else []
        return {
            "ok": True,
            "status": "activo" if readiness >= 50 else "pendiente de datos",
            "readiness_score": readiness,
            "profiles_total": profiles,
            "availability_total": availability,
            "stat_snapshots_total": stat_snapshots,
            "impact_signals_total": signals,
            "source_lineups_total": lineups_source,
            "source_injuries_total": injuries_source,
            "top_signals": top_signals,
            "last_run": last_run,
            "legal_note": LEGAL_NOTE,
        }
    finally:
        conn.close()
