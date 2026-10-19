"""Experimental historical context for the future SHARK forecast pipeline.

This module is not wired to customer forecast routes. It summarizes persisted,
explicitly finished match results only. Historical ratings are not calibrated
probabilities and cannot produce a published pick; a chronological validation
step is required before any prediction score can be enabled.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, Iterable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.OperationalError:
        pass
    return conn


def rows(conn: sqlite3.Connection, query: str, params: Iterable[Any] = ()) -> list[Dict[str, Any]]:
    try:
        return [dict(r) for r in conn.execute(query, tuple(params)).fetchall()]
    except sqlite3.OperationalError:
        return []


def one(conn: sqlite3.Connection, query: str, params: Iterable[Any] = ()) -> Dict[str, Any]:
    try:
        row = conn.execute(query, tuple(params)).fetchone()
        return dict(row) if row else {}
    except sqlite3.OperationalError:
        return {}


def scalar(conn: sqlite3.Connection, query: str, params: Iterable[Any] = (), default: Any = 0) -> Any:
    row = one(conn, query, params)
    return next(iter(row.values()), default) if row else default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(as_float(value, default)))
    except Exception:
        return default


def clamp(value: float, low: int = 1, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def stable_id(prefix: str, *parts: Any) -> str:
    raw = ":".join(str(p or "") for p in parts)
    return hashlib.sha1(f"{prefix}:{raw}".encode("utf-8")).hexdigest()[:24]


def json_dumps(payload: Any) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, default=str)[:30000]


def ensure_shark_prediction_schema(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS shark_team_ratings(
        team_name TEXT PRIMARY KEY,
        rating INTEGER DEFAULT 70,
        matches_played INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        goals_for INTEGER DEFAULT 0,
        goals_against INTEGER DEFAULT 0,
        goal_diff INTEGER DEFAULT 0,
        form_points INTEGER DEFAULT 0,
        home_strength INTEGER DEFAULT 70,
        away_strength INTEGER DEFAULT 70,
        reliability_score INTEGER DEFAULT 0,
        payload_json TEXT,
        rebuilt_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS shark_league_strength(
        league_name TEXT PRIMARY KEY,
        strength_score INTEGER DEFAULT 70,
        sample_size INTEGER DEFAULT 0,
        avg_goals REAL DEFAULT 0,
        upset_index REAL DEFAULT 0,
        reliability_score INTEGER DEFAULT 0,
        payload_json TEXT,
        rebuilt_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS shark_prediction_market_scores(
        market TEXT PRIMARY KEY,
        score INTEGER DEFAULT 70,
        sample_size INTEGER DEFAULT 0,
        winrate REAL DEFAULT 0,
        roi REAL DEFAULT 0,
        confidence_adjustment INTEGER DEFAULT 0,
        explanation TEXT,
        payload_json TEXT,
        rebuilt_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS shark_prediction_profiles(
        id TEXT PRIMARY KEY,
        matches_analyzed INTEGER DEFAULT 0,
        teams_rated INTEGER DEFAULT 0,
        leagues_rated INTEGER DEFAULT 0,
        markets_rated INTEGER DEFAULT 0,
        prediction_readiness INTEGER DEFAULT 0,
        avg_team_rating REAL DEFAULT 0,
        top_team TEXT,
        payload_json TEXT,
        rebuilt_at TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shark_team_rating ON shark_team_ratings(rating)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shark_league_strength ON shark_league_strength(strength_score)")
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "shark_prediction_v592"}


def normalize_status(value: Any) -> str:
    # Statuses are provider codes or short labels. Substring checks are unsafe:
    # for example, "pending" contains "pen" but is not a finished fixture.
    text = re.sub(r"[\s_-]+", " ", str(value or "").strip().casefold())
    text = "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char))
    if text in {
        "ft", "aet", "pen", "final", "finalizado", "terminado", "archived",
        "finished", "match finished", "full time", "fulltime",
        "completed", "complete", "after extra time", "after penalties",
        "finalizado tras prorroga", "finalizado tras penaltis",
        "terminado tras prorroga", "terminado tras penaltis",
    }:
        return "finished"
    if text in {"live", "1h", "2h", "ht", "halftime", "half time", "directo", "in play", "inplay"}:
        return "live"
    return "scheduled"


def _score_pair(row: Dict[str, Any]) -> tuple[int | None, int | None]:
    def first_present(*names: str) -> Any:
        return next((row.get(name) for name in names if row.get(name) not in (None, "")), None)

    def integer_score(value: Any) -> int | None:
        if isinstance(value, bool) or value in (None, ""):
            return None
        try:
            parsed = float(str(value).replace(",", "."))
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(parsed) or parsed < 0 or not parsed.is_integer():
            return None
        return int(parsed)

    home = first_present("home_score", "score_home", "home_goals", "goals_home")
    away = first_present("away_score", "score_away", "away_goals", "goals_away")
    home_score, away_score = integer_score(home), integer_score(away)
    if home_score is not None and away_score is not None:
        return home_score, away_score

    score = str(first_present("score", "result") or "")
    match = re.fullmatch(r"\s*(\d+)\s*[-:]\s*(\d+)\s*", score)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def _finished_matches(conn: sqlite3.Connection, limit: int) -> list[Dict[str, Any]]:
    terminal_statuses = (
        "ft", "aet", "pen", "final", "finalizado", "terminado", "archived", "finished",
        "match finished", "full time", "fulltime", "completed", "complete",
        "after extra time", "after penalties", "finalizado tras prorroga",
        "finalizado tras penaltis", "terminado tras prorroga", "terminado tras penaltis",
        "finalizado tras prórroga", "terminado tras prórroga",
    )
    placeholders = ",".join("?" for _ in terminal_statuses)
    safe_limit = max(1, int(limit))

    def from_table(table: str) -> list[Dict[str, Any]]:
        # Table names are fixed internal constants; user data only enters bound parameters.
        order = "COALESCE(match_date,'') DESC, COALESCE(kickoff_time,'') DESC"
        if table == "warehouse_match_facts":
            order = "COALESCE(match_date,snapshot_at,'') DESC, COALESCE(kickoff_iso,'') DESC"
        data = rows(conn, f"""SELECT * FROM {table}
            WHERE COALESCE(home_team,'')<>'' AND COALESCE(away_team,'')<>''
              AND lower(trim(COALESCE(status,''))) IN ({placeholders})
            ORDER BY {order} LIMIT ?""", (*terminal_statuses, safe_limit))
        finished = []
        for item in data:
            if normalize_status(item.get("status")) != "finished":
                continue
            home_score, away_score = _score_pair(item)
            if home_score is None or away_score is None:
                continue
            item["_home_score"] = home_score
            item["_away_score"] = away_score
            finished.append(item)
        return finished

    finished = from_table("matches")
    return finished if finished else from_table("warehouse_match_facts")


def _blank_team() -> Dict[str, Any]:
    return {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0, "home_matches": 0, "home_points": 0, "away_matches": 0, "away_points": 0, "form_points": 0}


def _points(gf: int, ga: int) -> int:
    if gf > ga:
        return 3
    if gf == ga:
        return 1
    return 0


def _rating_from_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    matches = max(0, as_int(stats.get("matches"), 0))
    if not matches:
        return {"rating": 70, "reliability": 0, "home_strength": 70, "away_strength": 70}
    wins = as_int(stats.get("wins"), 0)
    draws = as_int(stats.get("draws"), 0)
    gf = as_int(stats.get("gf"), 0)
    ga = as_int(stats.get("ga"), 0)
    gd = gf - ga
    points = wins * 3 + draws
    ppg = points / max(1, matches)
    gd_per_match = gd / max(1, matches)
    rating = 52 + (ppg * 11) + (gd_per_match * 6) + min(8, matches * 0.35)
    reliability = clamp(min(100, matches * 8), 0, 100)
    home_matches = max(1, as_int(stats.get("home_matches"), 0))
    away_matches = max(1, as_int(stats.get("away_matches"), 0))
    home_strength = clamp(55 + (as_float(stats.get("home_points"), 0) / home_matches) * 12)
    away_strength = clamp(55 + (as_float(stats.get("away_points"), 0) / away_matches) * 12)
    return {"rating": clamp(rating), "reliability": reliability, "home_strength": home_strength, "away_strength": away_strength}


def rebuild_shark_prediction_engine(db_path: str, limit: int = 1000) -> Dict[str, Any]:
    ensure_shark_prediction_schema(db_path)
    conn = connect(db_path)
    cur = conn.cursor()
    matches = _finished_matches(conn, limit)
    if not matches:
        existing_teams = as_int(scalar(conn, "SELECT COUNT(*) FROM shark_team_ratings", default=0), 0)
        existing_profile = one(conn, "SELECT prediction_readiness FROM shark_prediction_profiles WHERE id='global'")
        conn.close()
        return {
            "ok": False,
            "rebuilt": False,
            "state": "INSUFFICIENT_FINISHED_RESULTS",
            "matches_analyzed": 0,
            "preserved_existing_model": bool(existing_teams or existing_profile),
            "summary": {},
        }
    cur.execute("DELETE FROM shark_team_ratings")
    cur.execute("DELETE FROM shark_league_strength")
    cur.execute("DELETE FROM shark_prediction_market_scores")
    teams: Dict[str, Dict[str, Any]] = {}
    leagues: Dict[str, Dict[str, Any]] = {}
    for item in matches:
        home = str(item.get("home_team") or "").strip()
        away = str(item.get("away_team") or "").strip()
        if not home or not away:
            continue
        hs = item.get("_home_score")
        aw = item.get("_away_score")
        if hs is None or aw is None:
            hs, aw = _score_pair(item)
        if hs is None or aw is None:
            continue
        league = str(item.get("competition_name") or item.get("league_name") or "Competición").strip() or "Competición"
        for team in [home, away]:
            teams.setdefault(team, _blank_team())
        hp = _points(int(hs), int(aw))
        ap = _points(int(aw), int(hs))
        teams[home]["matches"] += 1; teams[away]["matches"] += 1
        teams[home]["gf"] += int(hs); teams[home]["ga"] += int(aw)
        teams[away]["gf"] += int(aw); teams[away]["ga"] += int(hs)
        teams[home]["home_matches"] += 1; teams[home]["home_points"] += hp
        teams[away]["away_matches"] += 1; teams[away]["away_points"] += ap
        teams[home]["form_points"] += hp; teams[away]["form_points"] += ap
        if hs > aw:
            teams[home]["wins"] += 1; teams[away]["losses"] += 1
        elif hs < aw:
            teams[away]["wins"] += 1; teams[home]["losses"] += 1
        else:
            teams[home]["draws"] += 1; teams[away]["draws"] += 1
        lg = leagues.setdefault(league, {"sample": 0, "goals": 0, "draws": 0, "upsets": 0})
        lg["sample"] += 1
        lg["goals"] += int(hs) + int(aw)
        lg["draws"] += 1 if hs == aw else 0
    now = utc_now()
    for team, stats in teams.items():
        rating = _rating_from_stats(stats)
        cur.execute("""INSERT OR REPLACE INTO shark_team_ratings
            (team_name,rating,matches_played,wins,draws,losses,goals_for,goals_against,goal_diff,form_points,home_strength,away_strength,reliability_score,payload_json,rebuilt_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            team, rating["rating"], stats["matches"], stats["wins"], stats["draws"], stats["losses"], stats["gf"], stats["ga"], stats["gf"]-stats["ga"], stats["form_points"], rating["home_strength"], rating["away_strength"], rating["reliability"], json_dumps(stats), now
        ))
    for league, stats in leagues.items():
        sample = max(1, as_int(stats.get("sample"), 0))
        avg_goals = round(as_float(stats.get("goals"), 0) / sample, 2)
        draw_rate = as_float(stats.get("draws"), 0) / sample
        strength = clamp(58 + min(18, sample * 0.22) + min(12, avg_goals * 2.2) - (draw_rate * 6))
        reliability = clamp(min(100, sample * 5), 0, 100)
        cur.execute("""INSERT OR REPLACE INTO shark_league_strength
            (league_name,strength_score,sample_size,avg_goals,upset_index,reliability_score,payload_json,rebuilt_at)
            VALUES (?,?,?,?,?,?,?,?)""", (league, strength, sample, avg_goals, round(draw_rate * 100, 2), reliability, json_dumps(stats), now))
    _rebuild_markets(conn, now)
    summary = _build_summary(conn, len(matches))
    conn.commit()
    conn.close()
    return {"ok": True, "rebuilt": True, "matches_analyzed": len(matches), "summary": summary}


def _rebuild_markets(conn: sqlite3.Connection, now: str) -> None:
    market_rows = rows(conn, """SELECT market, sample_size, winrate, roi, confidence_adjustment, explanation
        FROM shark_learning_market_stats WHERE COALESCE(sample_size,0)>0""")
    for item in market_rows:
        market = item.get("market") or "Mercado"
        sample = as_int(item.get("sample_size"), 0)
        winrate = as_float(item.get("winrate"), 0)
        roi = as_float(item.get("roi"), 0)
        adj = as_int(item.get("confidence_adjustment"), 0)
        score = clamp(64 + adj + min(12, roi / 2) + min(10, max(0, winrate - 50) / 3))
        conn.execute("""INSERT OR REPLACE INTO shark_prediction_market_scores
            (market,score,sample_size,winrate,roi,confidence_adjustment,explanation,payload_json,rebuilt_at)
            VALUES (?,?,?,?,?,?,?,?,?)""", (market, score, sample, winrate, roi, adj, item.get("explanation") or "Mercado evaluado por histórico SHARK.", json_dumps(item), now))
    # An empty learning table means no measured market evidence. Do not seed
    # placeholder scores that can be mistaken for learned model performance.


def _build_summary(conn: sqlite3.Connection, matches_analyzed: int | None = None) -> Dict[str, Any]:
    teams = as_int(scalar(conn, "SELECT COUNT(*) FROM shark_team_ratings", default=0), 0)
    leagues = as_int(scalar(conn, "SELECT COUNT(*) FROM shark_league_strength", default=0), 0)
    markets = as_int(scalar(conn, "SELECT COUNT(*) FROM shark_prediction_market_scores WHERE sample_size>0", default=0), 0)
    avg_rating_value = scalar(conn, "SELECT ROUND(AVG(rating),2) FROM shark_team_ratings", default=None)
    avg_rating = as_float(avg_rating_value, None) if teams else None
    top = one(conn, "SELECT team_name, rating, reliability_score FROM shark_team_ratings ORDER BY rating DESC, reliability_score DESC LIMIT 1")
    training_matches = max(0, as_int(matches_analyzed, 0)) if matches_analyzed is not None else as_int(scalar(conn, "SELECT SUM(matches_played) FROM shark_team_ratings", default=0), 0) // 2
    coverage = 0 if training_matches <= 0 else min(60, teams * 2) + min(25, leagues * 5) + min(15, markets * 5)
    coverage = clamp(coverage, 0, 100) if coverage else 0
    top_teams = rows(conn, "SELECT * FROM shark_team_ratings ORDER BY rating DESC, reliability_score DESC LIMIT 8")
    strong_leagues = rows(conn, "SELECT * FROM shark_league_strength ORDER BY strength_score DESC, reliability_score DESC LIMIT 6")
    markets_rows = rows(conn, "SELECT * FROM shark_prediction_market_scores ORDER BY score DESC, sample_size DESC LIMIT 8")
    payload = {
        "prediction_readiness": 0,
        "historical_data_coverage": coverage,
        "prediction_validation_state": "NOT_VALIDATED",
        "matches_analyzed": matches_analyzed if matches_analyzed is not None else as_int(scalar(conn, "SELECT SUM(matches_played) FROM shark_team_ratings", default=0), 0),
        "teams_rated": teams,
        "leagues_rated": leagues,
        "markets_rated": markets,
        "avg_team_rating": avg_rating,
        "top_team": (top or {}).get("team_name") or "Sin datos suficientes",
        "top_teams": top_teams,
        "strong_leagues": strong_leagues,
        "market_scores": markets_rows,
        "readiness_type": "historical_data_coverage_not_model_accuracy",
        "note": "La preparación mide cobertura de resultados históricos y mercados evaluados; no mide precisión ni valida pronósticos.",
    }
    conn.execute("""INSERT OR REPLACE INTO shark_prediction_profiles
        (id,matches_analyzed,teams_rated,leagues_rated,markets_rated,prediction_readiness,avg_team_rating,top_team,payload_json,rebuilt_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""", ("global", payload["matches_analyzed"], teams, leagues, markets, payload["prediction_readiness"], avg_rating, payload["top_team"], json_dumps(payload), utc_now()))
    return payload


def shark_prediction_summary(db_path: str, auto_rebuild: bool = False) -> Dict[str, Any]:
    ensure_shark_prediction_schema(db_path)
    conn = connect(db_path)
    profile = one(conn, "SELECT * FROM shark_prediction_profiles WHERE id='global'")
    if auto_rebuild and not profile:
        conn.close()
        return rebuild_shark_prediction_engine(db_path, limit=1000).get("summary", {})
    if profile.get("payload_json"):
        try:
            payload = json.loads(profile.get("payload_json") or "{}")
        except json.JSONDecodeError:
            payload = {}
    else:
        payload = _build_summary(conn)
    payload.setdefault("top_teams", rows(conn, "SELECT * FROM shark_team_ratings ORDER BY rating DESC, reliability_score DESC LIMIT 8"))
    payload.setdefault("strong_leagues", rows(conn, "SELECT * FROM shark_league_strength ORDER BY strength_score DESC, reliability_score DESC LIMIT 6"))
    payload.setdefault("market_scores", rows(conn, "SELECT * FROM shark_prediction_market_scores ORDER BY score DESC LIMIT 8"))
    conn.close()
    return payload


def _team_rating(conn: sqlite3.Connection, team: Any) -> Dict[str, Any]:
    if not team:
        return {"team_name": "", "rating": None, "matches_played": 0, "reliability_score": 0, "home_strength": None, "away_strength": None}
    row = one(conn, "SELECT * FROM shark_team_ratings WHERE lower(team_name)=lower(?)", (str(team),))
    return row or {"team_name": str(team), "rating": None, "matches_played": 0, "reliability_score": 0, "home_strength": None, "away_strength": None}


def _league_strength(conn: sqlite3.Connection, league: Any) -> Dict[str, Any]:
    if not league:
        return {"league_name": "Competición", "strength_score": None, "reliability_score": 0, "sample_size": 0}
    row = one(conn, "SELECT * FROM shark_league_strength WHERE lower(league_name)=lower(?)", (str(league),))
    return row or {"league_name": str(league), "strength_score": None, "reliability_score": 0, "sample_size": 0}


def _market_scores(conn: sqlite3.Connection) -> list[Dict[str, Any]]:
    return rows(conn, "SELECT * FROM shark_prediction_market_scores WHERE sample_size>0 ORDER BY score DESC, sample_size DESC LIMIT 10")


def prediction_for_match(db_path: str, match: Dict[str, Any], value_profile: Dict[str, Any] | None = None, premium_profile: Dict[str, Any] | None = None) -> Dict[str, Any]:
    ensure_shark_prediction_schema(db_path)
    conn = connect(db_path)
    home = match.get("home_team") or "Local"
    away = match.get("away_team") or "Visitante"
    league = match.get("competition_name") or match.get("league_name") or "Competición"
    home_rating = _team_rating(conn, home)
    away_rating = _team_rating(conn, away)
    league_row = _league_strength(conn, league)
    markets = _market_scores(conn)
    conn.close()
    hr = as_int(home_rating.get("rating"), 70)
    ar = as_int(away_rating.get("rating"), 70)
    home_edge = hr - ar + 3  # descriptive rating difference, not a calibrated probability
    home_sample = as_int(home_rating.get("matches_played"), 0)
    away_sample = as_int(away_rating.get("matches_played"), 0)
    sample_ready = home_sample >= 5 and away_sample >= 5
    rating_signal = "LOCAL" if home_edge >= 8 else "VISITANTE" if home_edge <= -8 else "EQUILIBRADO"
    return {
        "available": False,
        "historical_signal_available": sample_ready,
        "state": "UNVALIDATED_HISTORICAL_SIGNAL" if sample_ready else "INSUFFICIENT_HISTORY",
        "version": "V592",
        "validated": False,
        "can_publish": False,
        "decision": "WAIT",
        "score_v2": None,
        "confidence_label": None,
        "risk_label": None,
        "recommended_market": None,
        "recommended_selection": None,
        "rating_signal": rating_signal if sample_ready else None,
        "reason": ("Contexto descriptivo de ratings históricos; todavía no está validado como pronóstico ni como pick."
                   if sample_ready else "Faltan al menos cinco resultados finalizados por equipo para mostrar una señal histórica."),
        "home_rating": {**home_rating, "rating": hr if home_sample else None, "sample_size": home_sample},
        "away_rating": {**away_rating, "rating": ar if away_sample else None, "sample_size": away_sample},
        "league_strength": league_row,
        "market_candidates": markets[:5],
        "historical_rating_difference": home_edge if sample_ready else None,
        "limitations": ["No es una probabilidad calibrada.", "No genera ni autoriza apuestas o publicaciones."],
        "summary": "Señal histórica descriptiva; sin pronóstico validado.",
    }


def apply_shark_prediction_adjustment(item: Dict[str, Any], db_path: str) -> Dict[str, Any]:
    """Adjust a pick only if a separately validated SHARK model is available."""
    payload = dict(item or {})
    match = {
        "home_team": payload.get("home_team"),
        "away_team": payload.get("away_team"),
        "competition_name": payload.get("competition_name") or payload.get("league_name"),
        "league_name": payload.get("league_name"),
    }
    try:
        prediction = prediction_for_match(db_path, match, value_profile=None, premium_profile={"shark_score": payload.get("score") or payload.get("confidence") or 70})
        old_score = as_int(payload.get("score") or payload.get("confidence"), 70)
        # An unvalidated historical signal must never alter a pick's score.
        if prediction.get("validated") is not True or prediction.get("score_v2") is None:
            payload["prediction_score_v2"] = None
            payload["prediction_adjustment"] = 0
            payload["prediction_explanation"] = prediction.get("summary")
            return payload
        delta = clamp((as_int(prediction.get("score_v2"), old_score) - 70) / 5, -6, 6)
        new_score = clamp(old_score + delta)
        payload["prediction_score_v2"] = prediction.get("score_v2")
        payload["prediction_adjustment"] = delta
        payload["prediction_explanation"] = prediction.get("summary")
        payload["score"] = max(as_int(payload.get("score"), new_score), new_score)
        payload["confidence"] = max(as_int(payload.get("confidence"), new_score), new_score)
    except Exception:
        payload.setdefault("prediction_adjustment", 0)
        payload.setdefault("prediction_explanation", "SHARK Prediction V2 pendiente de más datos.")
    return payload
