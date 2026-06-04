"""SHARK Performance Memory engine for NeMeSiS SHARK PRO.

V576 converts historical picks into compact learning signals. It is safe to run
manually or from automation: only creates/updates its own tables and never
changes user, pick or match production rows.
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


def scalar(conn: sqlite3.Connection, query: str, params: Iterable[Any] = (), default: Any = 0) -> Any:
    try:
        row = conn.execute(query, tuple(params)).fetchone()
        if not row:
            return default
        return list(dict(row).values())[0]
    except sqlite3.OperationalError:
        return default


def stable_id(prefix: str, *parts: Any) -> str:
    raw = ":".join(str(p or "") for p in parts)
    return hashlib.sha1(f"{prefix}:{raw}".encode("utf-8")).hexdigest()[:24]


def json_dumps(payload: Any) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, default=str)[:20000]


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


def bucket_confidence(confidence: Any) -> str:
    c = as_int(confidence, 50)
    if c >= 85:
        return "85-100"
    if c >= 70:
        return "70-84"
    if c >= 55:
        return "55-69"
    return "0-54"


def normalize_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"won", "win", "ganado", "green", "acertado"}:
        return "won"
    if text in {"lost", "loss", "perdido", "red", "fallado"}:
        return "lost"
    if text in {"void", "push", "nulo", "cancelled", "cancelado"}:
        return "void"
    return "pending"


def ensure_shark_memory_schema(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS shark_performance_memory(
        id TEXT PRIMARY KEY,
        dimension_type TEXT NOT NULL,
        dimension_value TEXT NOT NULL,
        sample_size INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        voids INTEGER DEFAULT 0,
        pending INTEGER DEFAULT 0,
        win_rate REAL DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        avg_odds REAL DEFAULT 0,
        total_stake REAL DEFAULT 0,
        total_profit REAL DEFAULT 0,
        roi REAL DEFAULT 0,
        shark_adjustment REAL DEFAULT 0,
        reliability_score INTEGER DEFAULT 0,
        payload_json TEXT,
        rebuilt_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS shark_pick_learning_runs(
        id TEXT PRIMARY KEY,
        status TEXT,
        groups_built INTEGER DEFAULT 0,
        picks_read INTEGER DEFAULT 0,
        profitable_groups INTEGER DEFAULT 0,
        risky_groups INTEGER DEFAULT 0,
        details_json TEXT,
        started_at TEXT,
        finished_at TEXT
    )""")
    for stmt in [
        "CREATE INDEX IF NOT EXISTS idx_shark_perf_dimension ON shark_performance_memory(dimension_type, dimension_value)",
        "CREATE INDEX IF NOT EXISTS idx_shark_perf_roi ON shark_performance_memory(roi, sample_size)",
        "CREATE INDEX IF NOT EXISTS idx_shark_perf_reliability ON shark_performance_memory(reliability_score)",
    ]:
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "shark_memory_v576"}


def _load_pick_rows(conn: sqlite3.Connection, limit: int) -> list[Dict[str, Any]]:
    wh_rows = rows(conn, """SELECT pick_id, match_id, league_name, home_team, away_team, selection, market, odds, confidence, stake, status, result_status, profit, snapshot_at
                            FROM warehouse_pick_facts ORDER BY COALESCE(updated_at,snapshot_at,'') DESC LIMIT ?""", (int(limit),))
    if wh_rows:
        return wh_rows
    return rows(conn, """SELECT id AS pick_id, match_id, competition_name AS league_name, home_team, away_team, selection, pick_type AS market,
                              odds, confidence, stake_units AS stake, status, status AS result_status, 0 AS profit, updated_at AS snapshot_at
                       FROM picks ORDER BY COALESCE(updated_at,created_at,'') DESC LIMIT ?""", (int(limit),))


def _profit_for_pick(pick: Dict[str, Any]) -> float:
    status = normalize_status(pick.get("result_status") or pick.get("status"))
    if status == "void":
        return 0.0
    profit = as_float(pick.get("profit"), 0.0)
    if profit:
        return round(profit, 2)
    stake = as_float(pick.get("stake"), 1.0)
    odds = as_float(pick.get("odds"), 0.0)
    if status == "won" and odds > 1:
        return round((odds - 1) * stake, 2)
    if status == "lost":
        return round(-stake, 2)
    return 0.0


def rebuild_shark_performance_memory(db_path: str, limit: int = 500) -> Dict[str, Any]:
    ensure_shark_memory_schema(db_path)
    started = utc_now()
    conn = connect(db_path)
    cur = conn.cursor()
    picks = _load_pick_rows(conn, limit)
    groups: dict[tuple[str, str], list[Dict[str, Any]]] = {}
    for p in picks:
        market = (p.get("market") or "general").strip() or "general"
        league = (p.get("league_name") or "Sin liga").strip() or "Sin liga"
        selection = (p.get("selection") or "Sin seleccion").strip() or "Sin seleccion"
        conf_bucket = bucket_confidence(p.get("confidence"))
        dimensions = [
            ("market", market),
            ("league", league),
            ("selection", selection[:80]),
            ("confidence_bucket", conf_bucket),
            ("market_confidence", f"{market} · {conf_bucket}"),
            ("league_market", f"{league} · {market}"),
        ]
        for key in dimensions:
            groups.setdefault(key, []).append(p)

    cur.execute("DELETE FROM shark_performance_memory")
    profitable = risky = built = 0
    for (dimension_type, dimension_value), items in groups.items():
        sample = len(items)
        wins = losses = voids = pending = 0
        confidence_sum = odds_sum = stake_sum = profit_sum = 0.0
        for p in items:
            status = normalize_status(p.get("result_status") or p.get("status"))
            wins += 1 if status == "won" else 0
            losses += 1 if status == "lost" else 0
            voids += 1 if status == "void" else 0
            pending += 1 if status == "pending" else 0
            confidence_sum += as_float(p.get("confidence"), 50)
            odds_sum += as_float(p.get("odds"), 0.0)
            stake_sum += as_float(p.get("stake"), 1.0)
            profit_sum += _profit_for_pick(p)
        settled = wins + losses
        win_rate = round((wins / settled) * 100, 2) if settled else 0.0
        avg_confidence = round(confidence_sum / sample, 2) if sample else 0.0
        avg_odds = round(odds_sum / sample, 2) if sample else 0.0
        roi = round((profit_sum / stake_sum) * 100, 2) if stake_sum else 0.0
        sample_factor = min(40, sample * 4)
        roi_factor = max(-25, min(25, roi / 2))
        win_factor = max(-20, min(20, win_rate - 50)) if settled else 0
        reliability = int(max(0, min(100, 40 + sample_factor + roi_factor + win_factor)))
        adjustment = round(max(-12, min(12, (roi / 10) + ((win_rate - 50) / 8 if settled else 0))), 2)
        profitable += 1 if roi > 0 and settled else 0
        risky += 1 if roi < -10 and settled else 0
        cur.execute("""INSERT INTO shark_performance_memory
            (id,dimension_type,dimension_value,sample_size,wins,losses,voids,pending,win_rate,avg_confidence,avg_odds,total_stake,total_profit,roi,shark_adjustment,reliability_score,payload_json,rebuilt_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (stable_id("spm", dimension_type, dimension_value), dimension_type, dimension_value, sample, wins, losses, voids, pending, win_rate, avg_confidence, avg_odds, round(stake_sum, 2), round(profit_sum, 2), roi, adjustment, reliability, json_dumps({"settled": settled, "source": "warehouse_pick_facts_or_picks"}), started))
        built += 1
    run_id = stable_id("splr", started, built, len(picks))
    cur.execute("""INSERT INTO shark_pick_learning_runs(id,status,groups_built,picks_read,profitable_groups,risky_groups,details_json,started_at,finished_at)
        VALUES (?,?,?,?,?,?,?,?,?)""", (run_id, "OK", built, len(picks), profitable, risky, json_dumps({"limit": limit}), started, utc_now()))
    conn.commit()
    conn.close()
    return {"ok": True, "shark_memory_v576": True, "run_id": run_id, "picks_read": len(picks), "groups_built": built, "profitable_groups": profitable, "risky_groups": risky}


def shark_memory_summary(db_path: str) -> Dict[str, Any]:
    ensure_shark_memory_schema(db_path)
    conn = connect(db_path)
    total_groups = scalar(conn, "SELECT COUNT(*) FROM shark_performance_memory", default=0)
    picks_read = scalar(conn, "SELECT picks_read FROM shark_pick_learning_runs ORDER BY started_at DESC LIMIT 1", default=0)
    avg_reliability = scalar(conn, "SELECT ROUND(AVG(reliability_score),1) FROM shark_performance_memory", default=0) or 0
    best = rows(conn, "SELECT * FROM shark_performance_memory WHERE sample_size > 0 ORDER BY roi DESC, reliability_score DESC LIMIT 8")
    risky = rows(conn, "SELECT * FROM shark_performance_memory WHERE sample_size > 0 ORDER BY roi ASC, reliability_score DESC LIMIT 8")
    recent_runs = rows(conn, "SELECT * FROM shark_pick_learning_runs ORDER BY started_at DESC LIMIT 6")
    readiness_parts = [total_groups > 0, picks_read > 0, avg_reliability >= 40, len(best) > 0, len(recent_runs) > 0]
    readiness = round(100 * sum(1 for x in readiness_parts if x) / len(readiness_parts))
    status = "aprendiendo" if readiness >= 60 else "necesita picks resueltos"
    summary = {
        "schema": "shark_memory_v576",
        "status": status,
        "readiness_score": readiness,
        "groups_total": total_groups,
        "picks_read": picks_read,
        "avg_reliability": avg_reliability,
        "best_edges": best,
        "risk_edges": risky,
        "recent_runs": recent_runs,
        "note": "SHARK usa esta memoria como capa de ajuste: sube o baja confianza segun rendimiento real historico.",
    }
    conn.close()
    return summary
