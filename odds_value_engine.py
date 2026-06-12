"""Odds & Value Intelligence for NeMeSiS SHARK PRO.

V591 creates a safe value layer over persisted odds. It does not force API
calls; it reads SQLite snapshots/picks/recommendations and estimates whether a
price looks useful compared with SHARK confidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
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
    item = one(conn, query, params)
    return next(iter(item.values()), default) if item else default


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


def stable_id(prefix: str, *parts: Any) -> str:
    raw = ":".join(str(p or "") for p in parts)
    return hashlib.sha1(f"{prefix}:{raw}".encode("utf-8")).hexdigest()[:24]


def json_dumps(payload: Any) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, default=str)[:20000]


def ensure_odds_value_schema(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS odds_value_signals(
        id TEXT PRIMARY KEY,
        match_id TEXT,
        pick_id TEXT,
        recommendation_id TEXT,
        league_name TEXT,
        market TEXT,
        selection TEXT,
        bookmaker TEXT,
        odds REAL DEFAULT 0,
        implied_probability REAL DEFAULT 0,
        shark_probability REAL DEFAULT 0,
        value_pct REAL DEFAULT 0,
        edge_label TEXT,
        confidence INTEGER DEFAULT 0,
        risk_label TEXT,
        source TEXT,
        payload_json TEXT,
        created_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS odds_value_summary(
        id TEXT PRIMARY KEY,
        total_signals INTEGER DEFAULT 0,
        strong_value INTEGER DEFAULT 0,
        medium_value INTEGER DEFAULT 0,
        watchlist INTEGER DEFAULT 0,
        no_value INTEGER DEFAULT 0,
        avg_value_pct REAL DEFAULT 0,
        best_value_pct REAL DEFAULT 0,
        readiness_score INTEGER DEFAULT 0,
        payload_json TEXT,
        rebuilt_at TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_odds_value_match ON odds_value_signals(match_id, created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_odds_value_value ON odds_value_signals(value_pct)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_odds_value_market ON odds_value_signals(market)")
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "odds_value_v591"}


def implied_probability(odds: Any) -> float:
    price = as_float(odds, 0.0)
    if price <= 1:
        return 0.0
    return round(100.0 / price, 2)


def shark_probability_from_confidence(confidence: Any) -> float:
    conf = max(0, min(100, as_float(confidence, 0.0)))
    if conf <= 0:
        return 0.0
    # Conservative mapping: confidence is not a guaranteed probability.
    return round(max(1.0, min(92.0, conf * 0.92)), 2)


def calculate_value_signal(odds: Any, confidence: Any) -> Dict[str, Any]:
    price = as_float(odds, 0.0)
    implied = implied_probability(price)
    shark_prob = shark_probability_from_confidence(confidence)
    if price <= 1 or not shark_prob:
        return {
            "available": False,
            "odds": price,
            "implied_probability": implied,
            "shark_probability": shark_prob,
            "value_pct": 0.0,
            "edge_label": "Sin value calculable",
            "risk_label": "Contextual",
            "note": "Falta cuota o confianza suficiente para calcular value.",
        }
    value = round(shark_prob - implied, 2)
    if value >= 10:
        edge = "Value fuerte"
        risk = "Controlado"
        note = "La probabilidad SHARK supera claramente la probabilidad implícita de la cuota. Revisar contexto antes de entrar."
    elif value >= 5:
        edge = "Value moderado"
        risk = "Medio"
        note = "Hay margen positivo entre lectura SHARK y precio de mercado."
    elif value >= 1:
        edge = "En observación"
        risk = "Medio"
        note = "Value pequeño: solo interesante si el resto del contexto acompaña."
    elif value <= -8:
        edge = "Sin value"
        risk = "Alto"
        note = "La cuota no compensa el riesgo estimado por SHARK."
    else:
        edge = "Precio justo"
        risk = "Medio"
        note = "Precio cercano a la lectura SHARK; no hay ventaja clara."
    return {
        "available": True,
        "odds": price,
        "implied_probability": implied,
        "shark_probability": shark_prob,
        "value_pct": value,
        "edge_label": edge,
        "risk_label": risk,
        "note": note,
    }


def _pick_candidates(conn: sqlite3.Connection, limit: int) -> list[Dict[str, Any]]:
    candidates = rows(conn, """SELECT id AS pick_id, match_id, competition_name AS league_name, market, selection,
                                  odds, confidence, risk_level, status, updated_at AS created_at
                           FROM picks
                           WHERE COALESCE(status,'') IN ('published','PUBLISHED','pending','PENDING','won','lost','void')
                           ORDER BY COALESCE(updated_at, created_at, '') DESC LIMIT ?""", (limit,))
    if candidates:
        return candidates
    return rows(conn, """SELECT pick_id, match_id, league_name, market, selection, odds, confidence, status, snapshot_at AS created_at
                         FROM warehouse_pick_facts ORDER BY COALESCE(updated_at, snapshot_at, '') DESC LIMIT ?""", (limit,))


def _recommendation_candidates(conn: sqlite3.Connection, limit: int) -> list[Dict[str, Any]]:
    return rows(conn, """SELECT id AS recommendation_id, match_id, league_name, market, selection, odds, confidence,
                              risk_level, value_label, created_at
                       FROM recommendations ORDER BY COALESCE(created_at, '') DESC LIMIT ?""", (limit,))


def _snapshot_candidates(conn: sqlite3.Connection, limit: int) -> list[Dict[str, Any]]:
    items = rows(conn, """SELECT match_id, league_name, bookmaker, market, home_team, away_team,
                              home_price, draw_price, away_price, created_at
                       FROM odds_snapshots ORDER BY COALESCE(created_at, '') DESC LIMIT ?""", (limit,))
    expanded: list[Dict[str, Any]] = []
    for item in items:
        for key, selection in [("home_price", item.get("home_team") or "Local"), ("draw_price", "Empate"), ("away_price", item.get("away_team") or "Visitante")]:
            price = as_float(item.get(key), 0.0)
            if price > 1:
                expanded.append({
                    "match_id": item.get("match_id"),
                    "league_name": item.get("league_name"),
                    "bookmaker": item.get("bookmaker"),
                    "market": item.get("market") or "1X2",
                    "selection": selection,
                    "odds": price,
                    "confidence": 62,
                    "created_at": item.get("created_at"),
                    "source": "odds_snapshot",
                })
    return expanded[:limit]


def _upsert_signal(conn: sqlite3.Connection, item: Dict[str, Any], source: str) -> Dict[str, Any]:
    odds = as_float(item.get("odds"), 0.0)
    confidence = as_int(item.get("confidence") or item.get("shark_score"), 0)
    signal = calculate_value_signal(odds, confidence)
    sig_id = stable_id("value", source, item.get("pick_id"), item.get("recommendation_id"), item.get("match_id"), item.get("market"), item.get("selection"), odds)
    payload = {"input": item, "signal": signal}
    conn.execute("""INSERT OR REPLACE INTO odds_value_signals
        (id, match_id, pick_id, recommendation_id, league_name, market, selection, bookmaker, odds,
         implied_probability, shark_probability, value_pct, edge_label, confidence, risk_label, source, payload_json, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        sig_id,
        item.get("match_id"),
        item.get("pick_id"),
        item.get("recommendation_id"),
        item.get("league_name"),
        item.get("market") or "1X2",
        item.get("selection"),
        item.get("bookmaker") or "SHARK",
        odds,
        signal.get("implied_probability"),
        signal.get("shark_probability"),
        signal.get("value_pct"),
        signal.get("edge_label"),
        confidence,
        signal.get("risk_label"),
        source,
        json_dumps(payload),
        item.get("created_at") or utc_now(),
    ))
    return {"id": sig_id, **signal, "market": item.get("market"), "selection": item.get("selection"), "league_name": item.get("league_name")}


def rebuild_odds_value_engine(db_path: str, limit: int = 500) -> Dict[str, Any]:
    ensure_odds_value_schema(db_path)
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM odds_value_signals")
    inserted = 0
    for item in _pick_candidates(conn, limit):
        if as_float(item.get("odds"), 0.0) > 1:
            _upsert_signal(conn, item, "pick")
            inserted += 1
    for item in _recommendation_candidates(conn, limit):
        if as_float(item.get("odds"), 0.0) > 1:
            _upsert_signal(conn, item, "recommendation")
            inserted += 1
    if inserted < 10:
        for item in _snapshot_candidates(conn, limit):
            _upsert_signal(conn, item, "odds_snapshot")
            inserted += 1
    summary = _build_summary(conn)
    conn.commit()
    conn.close()
    return {"ok": True, "rebuilt": inserted, "summary": summary}


def _build_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    total = int(scalar(conn, "SELECT COUNT(*) FROM odds_value_signals", default=0) or 0)
    strong = int(scalar(conn, "SELECT COUNT(*) FROM odds_value_signals WHERE value_pct >= 10", default=0) or 0)
    medium = int(scalar(conn, "SELECT COUNT(*) FROM odds_value_signals WHERE value_pct >= 5 AND value_pct < 10", default=0) or 0)
    watch = int(scalar(conn, "SELECT COUNT(*) FROM odds_value_signals WHERE value_pct >= 1 AND value_pct < 5", default=0) or 0)
    no_value = int(scalar(conn, "SELECT COUNT(*) FROM odds_value_signals WHERE value_pct < 1", default=0) or 0)
    avg_value = as_float(scalar(conn, "SELECT ROUND(AVG(value_pct),2) FROM odds_value_signals", default=0), 0)
    best_value = as_float(scalar(conn, "SELECT ROUND(MAX(value_pct),2) FROM odds_value_signals", default=0), 0)
    best = rows(conn, "SELECT * FROM odds_value_signals ORDER BY value_pct DESC, confidence DESC LIMIT 8")
    risky = rows(conn, "SELECT * FROM odds_value_signals ORDER BY value_pct ASC LIMIT 6")
    readiness = 35
    if total:
        readiness += 25
    if strong or medium:
        readiness += 25
    if best_value > 0:
        readiness += 15
    readiness = min(100, readiness)
    payload = {
        "total_signals": total,
        "strong_value": strong,
        "medium_value": medium,
        "watchlist": watch,
        "no_value": no_value,
        "avg_value_pct": avg_value,
        "best_value_pct": best_value,
        "readiness_score": readiness,
        "best_signals": best,
        "risk_signals": risky,
        "note": "Value calculado desde cuotas guardadas y confianza SHARK; no garantiza acierto ni beneficio.",
    }
    conn.execute("""INSERT OR REPLACE INTO odds_value_summary
        (id,total_signals,strong_value,medium_value,watchlist,no_value,avg_value_pct,best_value_pct,readiness_score,payload_json,rebuilt_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
        "global", total, strong, medium, watch, no_value, avg_value, best_value, readiness, json_dumps(payload), utc_now()
    ))
    return payload


def odds_value_summary(db_path: str, auto_rebuild: bool = False) -> Dict[str, Any]:
    ensure_odds_value_schema(db_path)
    conn = connect(db_path)
    summary_row = one(conn, "SELECT * FROM odds_value_summary WHERE id='global'")
    total_signals = int(scalar(conn, "SELECT COUNT(*) FROM odds_value_signals", default=0) or 0)
    if auto_rebuild and not total_signals:
        conn.close()
        return rebuild_odds_value_engine(db_path, limit=500).get("summary", {})
    if summary_row.get("payload_json"):
        try:
            payload = json.loads(summary_row.get("payload_json") or "{}")
        except json.JSONDecodeError:
            payload = {}
    else:
        payload = _build_summary(conn)
    payload.setdefault("total_signals", total_signals)
    payload.setdefault("best_signals", rows(conn, "SELECT * FROM odds_value_signals ORDER BY value_pct DESC, confidence DESC LIMIT 8"))
    payload.setdefault("risk_signals", rows(conn, "SELECT * FROM odds_value_signals ORDER BY value_pct ASC LIMIT 6"))
    payload.setdefault("readiness_score", 0)
    conn.close()
    return payload


def value_for_pick_like(item: Dict[str, Any]) -> Dict[str, Any]:
    return calculate_value_signal(item.get("odds"), item.get("confidence") or item.get("shark_score"))
