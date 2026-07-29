"""V598 - SHARK Historical Intelligence Platform.

Capa de inteligencia historica propia de NeMeSiS. Parte de los datos que la
app recibe de fuentes autorizadas y los convierte en memoria operativa,
metricas derivadas y activos internos para SHARK.

Nota legal: no redistribuye datos crudos de terceros. Conserva snapshots para
operar la plataforma y genera metricas propias: forma, cobertura, ratings,
mercados, confianza y trazabilidad.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping


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


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).replace(",", ".")))
    except Exception:
        return default


def _hash_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(p or "") for p in parts)
    return f"{prefix}-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:18]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    try:
        return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())
    except sqlite3.Error:
        return False


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(conn, table):
        return set()
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _count(conn: sqlite3.Connection, table: str) -> int:
    if not _table_exists(conn, table):
        return 0
    try:
        return _as_int(conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"], 0)
    except sqlite3.Error:
        return 0


def ensure_historical_intelligence_schema(db_path: str) -> Dict[str, Any]:
    conn = _connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS shark_historical_sync_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT,
                scope TEXT,
                processed INTEGER DEFAULT 0,
                inserted INTEGER DEFAULT 0,
                updated INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                error_message TEXT,
                payload_json TEXT
            );

            CREATE TABLE IF NOT EXISTS shark_historical_match_facts (
                id TEXT PRIMARY KEY,
                internal_match_id TEXT,
                provider TEXT,
                external_id TEXT,
                league_name TEXT,
                season TEXT,
                match_date TEXT,
                status TEXT,
                home_team TEXT,
                away_team TEXT,
                home_score INTEGER,
                away_score INTEGER,
                total_goals INTEGER DEFAULT 0,
                winner TEXT,
                has_events INTEGER DEFAULT 0,
                has_odds INTEGER DEFAULT 0,
                has_shark_signal INTEGER DEFAULT 0,
                source_legal_note TEXT,
                payload_json TEXT,
                first_seen_at TEXT,
                last_seen_at TEXT,
                UNIQUE(provider, external_id)
            );

            CREATE TABLE IF NOT EXISTS shark_historical_team_form (
                id TEXT PRIMARY KEY,
                team_name TEXT NOT NULL,
                league_name TEXT,
                matches_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                goals_for INTEGER DEFAULT 0,
                goals_against INTEGER DEFAULT 0,
                form_code TEXT,
                rating REAL DEFAULT 70,
                updated_at TEXT,
                payload_json TEXT,
                UNIQUE(team_name, league_name)
            );

            CREATE TABLE IF NOT EXISTS shark_historical_league_profile (
                id TEXT PRIMARY KEY,
                league_name TEXT NOT NULL UNIQUE,
                matches_total INTEGER DEFAULT 0,
                avg_goals REAL DEFAULT 0,
                home_win_pct REAL DEFAULT 0,
                draw_pct REAL DEFAULT 0,
                away_win_pct REAL DEFAULT 0,
                data_depth_score INTEGER DEFAULT 0,
                updated_at TEXT,
                payload_json TEXT
            );

            CREATE TABLE IF NOT EXISTS shark_historical_market_profile (
                id TEXT PRIMARY KEY,
                market TEXT NOT NULL UNIQUE,
                sample_size INTEGER DEFAULT 0,
                avg_confidence REAL DEFAULT 0,
                avg_value_pct REAL DEFAULT 0,
                roi REAL DEFAULT 0,
                winrate REAL DEFAULT 0,
                updated_at TEXT,
                payload_json TEXT
            );

            CREATE TABLE IF NOT EXISTS shark_historical_source_registry (
                id TEXT PRIMARY KEY,
                source_name TEXT NOT NULL UNIQUE,
                source_type TEXT,
                legal_use TEXT,
                retention_policy TEXT,
                redistribution_allowed INTEGER DEFAULT 0,
                configured INTEGER DEFAULT 0,
                updated_at TEXT,
                payload_json TEXT
            );

            CREATE TABLE IF NOT EXISTS shark_historical_data_quality (
                id TEXT PRIMARY KEY,
                metric_key TEXT NOT NULL UNIQUE,
                metric_value REAL DEFAULT 0,
                status TEXT,
                description TEXT,
                updated_at TEXT,
                payload_json TEXT
            );
            """
        )
        conn.commit()
        return {"ok": True, "schema": "shark_historical_intelligence_ready"}
    finally:
        conn.close()


def _register_sources(conn: sqlite3.Connection) -> int:
    now = _now_iso()
    sources = [
        {
            "source_name": "API-Football",
            "source_type": "sports_data_api",
            "legal_use": "Uso interno autorizado para operar NeMeSiS, cachear datos y generar metricas propias segun contrato.",
            "retention_policy": "Conservacion historica interna desde hoy. No redistribuir datos crudos sin licencia especifica.",
            "redistribution_allowed": 0,
            "configured": 1 if (os.getenv("API_FOOTBALL_KEY") or os.getenv("API_FOOTBALL_API_KEY")) else 0,
        },
        {
            "source_name": "TheSportsDB",
            "source_type": "sports_enrichment_api",
            "legal_use": "Enriquecimiento interno con escudos, ligas, equipos, eventos y highlights segun plan contratado.",
            "retention_policy": "Cache interno para mejorar experiencia, SHARK y fichas de partido.",
            "redistribution_allowed": 0,
            "configured": 1 if (os.getenv("THESPORTSDB_KEY") or os.getenv("THESPORTSDB_API_KEY")) else 0,
        },
        {
            "source_name": "The Odds API",
            "source_type": "odds_api",
            "legal_use": "Uso interno de cuotas para value, picks y analitica propia segun plan contratado.",
            "retention_policy": "Snapshots internos de cuotas y value. No revender feed original sin licencia.",
            "redistribution_allowed": 0,
            "configured": 1 if os.getenv("THE_ODDS_API_KEY") else 0,
        },
        {
            "source_name": "NeMeSiS SHARK",
            "source_type": "derived_internal_intelligence",
            "legal_use": "Inteligencia propia derivada: ratings, scores, ROI, value, confianza y aprendizaje.",
            "retention_policy": "Activo propio de NeMeSiS. Conservar indefinidamente para aprendizaje y auditoria.",
            "redistribution_allowed": 1,
            "configured": 1,
        },
    ]
    inserted = 0
    for item in sources:
        row_id = _hash_id("hist-source", item["source_name"])
        before = conn.total_changes
        conn.execute(
            """
            INSERT INTO shark_historical_source_registry(id, source_name, source_type, legal_use, retention_policy, redistribution_allowed, configured, updated_at, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_name) DO UPDATE SET
              source_type=excluded.source_type,
              legal_use=excluded.legal_use,
              retention_policy=excluded.retention_policy,
              redistribution_allowed=excluded.redistribution_allowed,
              configured=excluded.configured,
              updated_at=excluded.updated_at,
              payload_json=excluded.payload_json
            """,
            (row_id, item["source_name"], item["source_type"], item["legal_use"], item["retention_policy"], item["redistribution_allowed"], item["configured"], now, _json(item)),
        )
        inserted += 1 if conn.total_changes > before else 0
    return inserted


def _build_match_facts(conn: sqlite3.Connection, limit: int) -> Dict[str, int]:
    if not _table_exists(conn, "football_matches_history"):
        return {"processed": 0, "inserted": 0, "updated": 0}
    now = _now_iso()
    rows = conn.execute(
        """
        SELECT * FROM football_matches_history
        ORDER BY COALESCE(last_seen_at, kickoff_iso, match_date, first_seen_at, id) DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    inserted = updated = processed = 0
    has_events = _table_exists(conn, "football_match_events_history")
    has_odds = _table_exists(conn, "football_odds_history")
    has_signals = _table_exists(conn, "football_shark_signals_history")
    for row in rows:
        r = dict(row)
        provider = r.get("provider") or "unknown"
        external_id = str(r.get("external_id") or r.get("id") or "")
        internal_id = str(r.get("internal_match_id") or "")
        home_score = _as_int(r.get("home_score"), 0)
        away_score = _as_int(r.get("away_score"), 0)
        if home_score > away_score:
            winner = "home"
        elif away_score > home_score:
            winner = "away"
        elif str(r.get("status") or "").lower() in {"finalizado", "final", "ft", "match finished"}:
            winner = "draw"
        else:
            winner = "pending"
        event_count = 0
        odds_count = 0
        signal_count = 0
        if has_events and external_id:
            event_count = _as_int(conn.execute("SELECT COUNT(*) AS c FROM football_match_events_history WHERE external_match_id=? OR internal_match_id=?", (external_id, internal_id)).fetchone()["c"], 0)
        if has_odds and external_id:
            odds_count = _as_int(conn.execute("SELECT COUNT(*) AS c FROM football_odds_history WHERE external_id=? OR internal_match_id=?", (external_id, internal_id)).fetchone()["c"], 0)
        if has_signals and internal_id:
            signal_count = _as_int(conn.execute("SELECT COUNT(*) AS c FROM football_shark_signals_history WHERE internal_match_id=?", (internal_id,)).fetchone()["c"], 0)
        fact_id = _hash_id("hist-match", provider, external_id)
        exists = conn.execute("SELECT id FROM shark_historical_match_facts WHERE provider=? AND external_id=?", (provider, external_id)).fetchone()
        conn.execute(
            """
            INSERT INTO shark_historical_match_facts(id, internal_match_id, provider, external_id, league_name, season, match_date, status, home_team, away_team, home_score, away_score, total_goals, winner, has_events, has_odds, has_shark_signal, source_legal_note, payload_json, first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider, external_id) DO UPDATE SET
              internal_match_id=excluded.internal_match_id,
              league_name=excluded.league_name,
              season=excluded.season,
              match_date=excluded.match_date,
              status=excluded.status,
              home_team=excluded.home_team,
              away_team=excluded.away_team,
              home_score=excluded.home_score,
              away_score=excluded.away_score,
              total_goals=excluded.total_goals,
              winner=excluded.winner,
              has_events=excluded.has_events,
              has_odds=excluded.has_odds,
              has_shark_signal=excluded.has_shark_signal,
              source_legal_note=excluded.source_legal_note,
              payload_json=excluded.payload_json,
              last_seen_at=excluded.last_seen_at
            """,
            (
                fact_id, internal_id, provider, external_id, r.get("league_name") or "", r.get("season") or "",
                r.get("match_date") or str(r.get("kickoff_iso") or "")[:10], r.get("status") or "", r.get("home_team") or "", r.get("away_team") or "",
                home_score, away_score, home_score + away_score, winner, 1 if event_count else 0, 1 if odds_count else 0, 1 if signal_count else 0,
                "Hecho historico interno construido desde fuentes autorizadas/cache operativo. No redistribuir datos crudos sin licencia.", _json({"source": r, "events": event_count, "odds": odds_count, "signals": signal_count}), now, now,
            ),
        )
        processed += 1
        if exists:
            updated += 1
        else:
            inserted += 1
    return {"processed": processed, "inserted": inserted, "updated": updated}


def _rebuild_team_form(conn: sqlite3.Connection) -> int:
    if not _table_exists(conn, "shark_historical_match_facts"):
        return 0
    rows = conn.execute(
        """
        SELECT * FROM shark_historical_match_facts
        WHERE winner IN ('home','away','draw')
        ORDER BY COALESCE(match_date, last_seen_at) ASC
        """
    ).fetchall()
    stats: Dict[tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        r = dict(row)
        league = r.get("league_name") or "General"
        teams = [
            (r.get("home_team") or "", _as_int(r.get("home_score"), 0), _as_int(r.get("away_score"), 0), r.get("winner") == "home"),
            (r.get("away_team") or "", _as_int(r.get("away_score"), 0), _as_int(r.get("home_score"), 0), r.get("winner") == "away"),
        ]
        for team, gf, ga, won in teams:
            if not team:
                continue
            key = (team, league)
            item = stats.setdefault(key, {"team_name": team, "league_name": league, "matches_played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "form": []})
            item["matches_played"] += 1
            item["goals_for"] += gf
            item["goals_against"] += ga
            if r.get("winner") == "draw":
                item["draws"] += 1
                item["form"].append("E")
            elif won:
                item["wins"] += 1
                item["form"].append("G")
            else:
                item["losses"] += 1
                item["form"].append("P")
    now = _now_iso()
    total = 0
    for (team, league), item in stats.items():
        played = max(1, item["matches_played"])
        points = item["wins"] * 3 + item["draws"]
        goal_diff = item["goals_for"] - item["goals_against"]
        rating = 50 + (points / (played * 3)) * 35 + max(min(goal_diff / played, 2), -2) * 4
        rating = max(25, min(99, round(rating, 2)))
        form_code = "".join(item["form"][-8:])
        conn.execute(
            """
            INSERT INTO shark_historical_team_form(id, team_name, league_name, matches_played, wins, draws, losses, goals_for, goals_against, form_code, rating, updated_at, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(team_name, league_name) DO UPDATE SET
              matches_played=excluded.matches_played,
              wins=excluded.wins,
              draws=excluded.draws,
              losses=excluded.losses,
              goals_for=excluded.goals_for,
              goals_against=excluded.goals_against,
              form_code=excluded.form_code,
              rating=excluded.rating,
              updated_at=excluded.updated_at,
              payload_json=excluded.payload_json
            """,
            (_hash_id("hist-team", team, league), team, league, item["matches_played"], item["wins"], item["draws"], item["losses"], item["goals_for"], item["goals_against"], form_code, rating, now, _json(item)),
        )
        total += 1
    return total


def _rebuild_league_profiles(conn: sqlite3.Connection) -> int:
    if not _table_exists(conn, "shark_historical_match_facts"):
        return 0
    rows = conn.execute(
        """
        SELECT league_name,
               COUNT(*) AS matches_total,
               AVG(total_goals) AS avg_goals,
               SUM(CASE WHEN winner='home' THEN 1 ELSE 0 END) AS home_wins,
               SUM(CASE WHEN winner='draw' THEN 1 ELSE 0 END) AS draws,
               SUM(CASE WHEN winner='away' THEN 1 ELSE 0 END) AS away_wins,
               SUM(has_events) AS event_matches,
               SUM(has_odds) AS odds_matches,
               SUM(has_shark_signal) AS signal_matches
        FROM shark_historical_match_facts
        WHERE COALESCE(league_name,'') <> ''
        GROUP BY league_name
        ORDER BY matches_total DESC
        """
    ).fetchall()
    now = _now_iso()
    total = 0
    for row in rows:
        r = dict(row)
        n = max(1, _as_int(r.get("matches_total"), 0))
        depth = round(((_as_int(r.get("event_matches"), 0) / n) * 35) + ((_as_int(r.get("odds_matches"), 0) / n) * 35) + ((_as_int(r.get("signal_matches"), 0) / n) * 30))
        payload = {"matches_total": n, "event_matches": r.get("event_matches"), "odds_matches": r.get("odds_matches"), "signal_matches": r.get("signal_matches")}
        conn.execute(
            """
            INSERT INTO shark_historical_league_profile(id, league_name, matches_total, avg_goals, home_win_pct, draw_pct, away_win_pct, data_depth_score, updated_at, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(league_name) DO UPDATE SET
              matches_total=excluded.matches_total,
              avg_goals=excluded.avg_goals,
              home_win_pct=excluded.home_win_pct,
              draw_pct=excluded.draw_pct,
              away_win_pct=excluded.away_win_pct,
              data_depth_score=excluded.data_depth_score,
              updated_at=excluded.updated_at,
              payload_json=excluded.payload_json
            """,
            (_hash_id("hist-league", r.get("league_name")), r.get("league_name"), n, round(_as_float(r.get("avg_goals"), 0), 2), round(_as_int(r.get("home_wins"), 0) * 100 / n, 2), round(_as_int(r.get("draws"), 0) * 100 / n, 2), round(_as_int(r.get("away_wins"), 0) * 100 / n, 2), int(depth), now, _json(payload)),
        )
        total += 1
    return total


def _rebuild_market_profiles(conn: sqlite3.Connection) -> int:
    if not _table_exists(conn, "football_shark_signals_history"):
        return 0
    rows = conn.execute(
        """
        SELECT COALESCE(NULLIF(market,''),'General') AS market,
               COUNT(*) AS sample_size,
               AVG(confidence) AS avg_confidence,
               AVG(value_pct) AS avg_value_pct,
               AVG(CASE WHEN result_status IN ('won','ganado','WIN','WON') THEN 1.0 WHEN result_status IN ('lost','perdido','LOST') THEN 0.0 ELSE NULL END) AS winrate,
               SUM(profit) AS profit
        FROM football_shark_signals_history
        GROUP BY COALESCE(NULLIF(market,''),'General')
        ORDER BY sample_size DESC
        """
    ).fetchall()
    now = _now_iso()
    total = 0
    for row in rows:
        r = dict(row)
        sample = max(0, _as_int(r.get("sample_size"), 0))
        profit = _as_float(r.get("profit"), 0)
        roi = round((profit / sample) * 100, 2) if sample else 0
        winrate = _as_float(r.get("winrate"), 0) * 100 if r.get("winrate") is not None else 0
        conn.execute(
            """
            INSERT INTO shark_historical_market_profile(id, market, sample_size, avg_confidence, avg_value_pct, roi, winrate, updated_at, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(market) DO UPDATE SET
              sample_size=excluded.sample_size,
              avg_confidence=excluded.avg_confidence,
              avg_value_pct=excluded.avg_value_pct,
              roi=excluded.roi,
              winrate=excluded.winrate,
              updated_at=excluded.updated_at,
              payload_json=excluded.payload_json
            """,
            (_hash_id("hist-market", r.get("market")), r.get("market"), sample, round(_as_float(r.get("avg_confidence"), 0), 2), round(_as_float(r.get("avg_value_pct"), 0), 2), roi, round(winrate, 2), now, _json(r)),
        )
        total += 1
    return total


def _update_quality_metrics(conn: sqlite3.Connection) -> int:
    now = _now_iso()
    metrics = []
    matches = _count(conn, "shark_historical_match_facts")
    events = _count(conn, "football_match_events_history")
    odds = _count(conn, "football_odds_history")
    signals = _count(conn, "football_shark_signals_history")
    teams = _count(conn, "shark_historical_team_form")
    leagues = _count(conn, "shark_historical_league_profile")
    markets = _count(conn, "shark_historical_market_profile")
    sources = _count(conn, "shark_historical_source_registry")
    coverage = 0
    if matches:
        with_events = _as_int(conn.execute("SELECT COUNT(*) AS c FROM shark_historical_match_facts WHERE has_events=1").fetchone()["c"], 0)
        with_odds = _as_int(conn.execute("SELECT COUNT(*) AS c FROM shark_historical_match_facts WHERE has_odds=1").fetchone()["c"], 0)
        with_signals = _as_int(conn.execute("SELECT COUNT(*) AS c FROM shark_historical_match_facts WHERE has_shark_signal=1").fetchone()["c"], 0)
        coverage = round(((with_events / matches) * 35) + ((with_odds / matches) * 35) + ((with_signals / matches) * 30), 2)
    metrics.extend([
        ("matches", matches, "OK" if matches else "PENDIENTE", "Partidos convertidos en hechos historicos SHARK."),
        ("events", events, "OK" if events else "PENDIENTE", "Eventos deportivos conservados para timeline y aprendizaje."),
        ("odds", odds, "OK" if odds else "PENDIENTE", "Snapshots de cuotas disponibles para value y closing line futuro."),
        ("signals", signals, "OK" if signals else "PENDIENTE", "Señales SHARK guardadas para aprendizaje propio."),
        ("team_forms", teams, "OK" if teams else "PENDIENTE", "Forma y rating historico por equipo."),
        ("league_profiles", leagues, "OK" if leagues else "PENDIENTE", "Perfiles historicos por competicion."),
        ("market_profiles", markets, "OK" if markets else "PENDIENTE", "Perfiles derivados por mercado de apuesta."),
        ("registered_sources", sources, "OK", "Registro legal y operativo de fuentes."),
        ("data_depth_score", coverage, "OK" if coverage >= 40 else "MEJORABLE", "Profundidad combinada eventos + cuotas + senales SHARK."),
    ])
    for key, value, status, description in metrics:
        conn.execute(
            """
            INSERT INTO shark_historical_data_quality(id, metric_key, metric_value, status, description, updated_at, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(metric_key) DO UPDATE SET
              metric_value=excluded.metric_value,
              status=excluded.status,
              description=excluded.description,
              updated_at=excluded.updated_at,
              payload_json=excluded.payload_json
            """,
            (_hash_id("hist-quality", key), key, value, status, description, now, _json({"key": key, "value": value, "status": status})),
        )
    return len(metrics)


def rebuild_historical_intelligence(db_path: str, limit: int = 1000, scope: str = "full") -> Dict[str, Any]:
    ensure_historical_intelligence_schema(db_path)
    started = _now_iso()
    result: Dict[str, Any] = {"ok": True, "scope": scope, "processed": 0, "inserted": 0, "updated": 0, "errors": []}
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO shark_historical_sync_runs(started_at, status, scope, payload_json) VALUES (?, ?, ?, ?)",
            (started, "RUNNING", scope, _json({"limit": limit})),
        )
        run_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        conn.commit()
        sources = _register_sources(conn)
        facts = _build_match_facts(conn, limit=max(50, int(limit or 1000)))
        teams = _rebuild_team_form(conn)
        leagues = _rebuild_league_profiles(conn)
        markets = _rebuild_market_profiles(conn)
        quality = _update_quality_metrics(conn)
        result.update({
            "sources_registered": sources,
            "match_facts": facts,
            "team_profiles": teams,
            "league_profiles": leagues,
            "market_profiles": markets,
            "quality_metrics": quality,
        })
        result["processed"] = facts.get("processed", 0) + teams + leagues + markets + quality
        result["inserted"] = facts.get("inserted", 0)
        result["updated"] = facts.get("updated", 0) + teams + leagues + markets + quality
        conn.execute(
            """
            UPDATE shark_historical_sync_runs
            SET finished_at=?, status=?, processed=?, inserted=?, updated=?, errors_count=?, error_message=?, payload_json=?
            WHERE id=?
            """,
            (_now_iso(), "OK" if not result["errors"] else "PARTIAL", result["processed"], result["inserted"], result["updated"], len(result["errors"]), "; ".join(result["errors"][:3]), _json(result), run_id),
        )
        conn.commit()
    except Exception as exc:
        result["ok"] = False
        result["errors"].append(str(exc)[:500])
        try:
            conn.execute(
                "UPDATE shark_historical_sync_runs SET finished_at=?, status=?, errors_count=?, error_message=?, payload_json=? WHERE started_at=?",
                (_now_iso(), "ERROR", 1, str(exc)[:500], _json(result), started),
            )
            conn.commit()
        except Exception:
            pass
    finally:
        conn.close()
    return result


def historical_intelligence_summary(db_path: str) -> Dict[str, Any]:
    ensure_historical_intelligence_schema(db_path)
    conn = _connect(db_path)
    try:
        matches = _count(conn, "shark_historical_match_facts")
        teams = _count(conn, "shark_historical_team_form")
        leagues = _count(conn, "shark_historical_league_profile")
        markets = _count(conn, "shark_historical_market_profile")
        sources = _count(conn, "shark_historical_source_registry")
        quality_rows = [dict(r) for r in conn.execute("SELECT metric_key, metric_value, status, description, updated_at FROM shark_historical_data_quality ORDER BY metric_key").fetchall()]
        data_depth = 0
        for item in quality_rows:
            if item.get("metric_key") == "data_depth_score":
                data_depth = _as_float(item.get("metric_value"), 0)
                break
        top_teams = [dict(r) for r in conn.execute("SELECT team_name, league_name, matches_played, rating, form_code FROM shark_historical_team_form ORDER BY rating DESC, matches_played DESC LIMIT 8").fetchall()]
        top_leagues = [dict(r) for r in conn.execute("SELECT league_name, matches_total, avg_goals, data_depth_score FROM shark_historical_league_profile ORDER BY matches_total DESC LIMIT 8").fetchall()]
        top_markets = [dict(r) for r in conn.execute("SELECT market, sample_size, avg_confidence, avg_value_pct, roi, winrate FROM shark_historical_market_profile ORDER BY sample_size DESC LIMIT 8").fetchall()]
        recent_runs = [dict(r) for r in conn.execute("SELECT started_at, finished_at, status, processed, inserted, updated, errors_count, error_message FROM shark_historical_sync_runs ORDER BY id DESC LIMIT 5").fetchall()]
        readiness = 25
        if sources:
            readiness += 15
        if matches:
            readiness += 20
        if teams:
            readiness += 15
        if leagues:
            readiness += 10
        if markets:
            readiness += 10
        if data_depth >= 40:
            readiness += 5
        return {
            "ok": True,
            "readiness_score": min(100, readiness),
            "matches_total": matches,
            "teams_total": teams,
            "leagues_total": leagues,
            "markets_total": markets,
            "sources_total": sources,
            "data_depth_score": round(data_depth, 2),
            "quality": quality_rows,
            "top_teams": top_teams,
            "top_leagues": top_leagues,
            "top_markets": top_markets,
            "recent_runs": recent_runs,
            "legal_note": "Uso interno para operar NeMeSiS y construir inteligencia propia. No redistribuir datos crudos de terceros sin licencia especifica.",
            "next_step": "Mantener scheduler warehouse activo para que cada partido deje huella historica y SHARK aprenda de forma acumulativa.",
        }
    finally:
        conn.close()


__all__ = [
    "ensure_historical_intelligence_schema",
    "rebuild_historical_intelligence",
    "historical_intelligence_summary",
]
