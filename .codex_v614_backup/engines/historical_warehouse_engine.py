"""Historical Data Warehouse engine for NeMeSiS SHARK PRO.

V572 turns the existing operational database into a compact learning layer.
It never deletes production data and it only uses INSERT OR REPLACE / IGNORE
snapshots, so it is safe to run from Render scheduler or manually from admin.
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


def row_dict(row: sqlite3.Row | None) -> Dict[str, Any]:
    return dict(row) if row else {}


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


def ensure_warehouse_schema(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS warehouse_match_facts(
        id TEXT PRIMARY KEY,
        match_id TEXT,
        match_date TEXT,
        kickoff_iso TEXT,
        league_name TEXT,
        country TEXT,
        home_team TEXT,
        away_team TEXT,
        status TEXT,
        minute TEXT,
        home_score REAL,
        away_score REAL,
        result_label TEXT,
        has_live INTEGER DEFAULT 0,
        has_odds INTEGER DEFAULT 0,
        has_pick INTEGER DEFAULT 0,
        source TEXT,
        payload_json TEXT,
        snapshot_at TEXT,
        updated_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS warehouse_odds_facts(
        id TEXT PRIMARY KEY,
        match_id TEXT,
        external_id TEXT,
        league_name TEXT,
        bookmaker TEXT,
        market TEXT,
        home_team TEXT,
        away_team TEXT,
        home_price REAL,
        draw_price REAL,
        away_price REAL,
        implied_home REAL,
        implied_draw REAL,
        implied_away REAL,
        commence_time TEXT,
        payload_json TEXT,
        snapshot_at TEXT,
        created_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS warehouse_pick_facts(
        id TEXT PRIMARY KEY,
        pick_id TEXT,
        match_id TEXT,
        match_date TEXT,
        league_name TEXT,
        home_team TEXT,
        away_team TEXT,
        selection TEXT,
        market TEXT,
        odds REAL,
        confidence INTEGER,
        stake REAL,
        status TEXT,
        result_status TEXT,
        profit REAL,
        payload_json TEXT,
        snapshot_at TEXT,
        updated_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS warehouse_user_facts(
        id TEXT PRIMARY KEY,
        user_id TEXT,
        membership TEXT,
        favorites_count INTEGER DEFAULT 0,
        activity_count INTEGER DEFAULT 0,
        last_activity_at TEXT,
        payload_json TEXT,
        snapshot_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS warehouse_daily_metrics(
        metric_date TEXT PRIMARY KEY,
        matches_total INTEGER DEFAULT 0,
        live_total INTEGER DEFAULT 0,
        finished_total INTEGER DEFAULT 0,
        odds_total INTEGER DEFAULT 0,
        picks_total INTEGER DEFAULT 0,
        users_active INTEGER DEFAULT 0,
        telegram_queue_pending INTEGER DEFAULT 0,
        data_quality_score INTEGER DEFAULT 0,
        payload_json TEXT,
        updated_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS warehouse_sync_runs(
        id TEXT PRIMARY KEY,
        run_type TEXT,
        status TEXT,
        inserted INTEGER DEFAULT 0,
        updated INTEGER DEFAULT 0,
        skipped INTEGER DEFAULT 0,
        details_json TEXT,
        started_at TEXT,
        finished_at TEXT
    )""")
    for stmt in [
        "CREATE INDEX IF NOT EXISTS idx_wh_match_date ON warehouse_match_facts(match_date, status)",
        "CREATE INDEX IF NOT EXISTS idx_wh_match_id ON warehouse_match_facts(match_id)",
        "CREATE INDEX IF NOT EXISTS idx_wh_odds_match ON warehouse_odds_facts(match_id, snapshot_at)",
        "CREATE INDEX IF NOT EXISTS idx_wh_pick_match ON warehouse_pick_facts(match_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_wh_user_snapshot ON warehouse_user_facts(snapshot_at, membership)",
    ]:
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "warehouse_v572"}


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def implied(price: Any) -> float:
    p = as_float(price, 0.0)
    return round(100 / p, 2) if p > 0 else 0.0


def result_label(home: Any, away: Any) -> str:
    h, a = as_float(home, None), as_float(away, None)
    if h is None or a is None:
        return "unknown"
    if h > a:
        return "home"
    if a > h:
        return "away"
    return "draw"


def snapshot_warehouse(db_path: str, limit: int = 250) -> Dict[str, Any]:
    ensure_warehouse_schema(db_path)
    started = utc_now()
    conn = connect(db_path)
    cur = conn.cursor()
    counts = {"matches": 0, "odds": 0, "picks": 0, "users": 0, "daily": 0}

    match_rows = rows(conn, "SELECT * FROM matches ORDER BY COALESCE(updated_at,kickoff_iso,match_date,'') DESC LIMIT ?", (int(limit),))
    for m in match_rows:
        match_id = m.get("id") or m.get("external_id")
        home_score = m.get("home_score")
        away_score = m.get("away_score")
        has_live = 1 if scalar(conn, "SELECT COUNT(*) FROM live_matches WHERE match_id=? OR id=?", (match_id, match_id), 0) else 0
        has_odds = 1 if scalar(conn, "SELECT COUNT(*) FROM odds_snapshots WHERE match_id=? OR external_id=?", (match_id, m.get("external_id")), 0) else 0
        has_pick = 1 if scalar(conn, "SELECT COUNT(*) FROM picks WHERE match_id=?", (match_id,), 0) else 0
        cur.execute("""INSERT OR REPLACE INTO warehouse_match_facts
            (id,match_id,match_date,kickoff_iso,league_name,country,home_team,away_team,status,minute,home_score,away_score,result_label,has_live,has_odds,has_pick,source,payload_json,snapshot_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (stable_id("wm", match_id), match_id, m.get("match_date"), m.get("kickoff_iso"), m.get("league_name") or m.get("competition_name"), m.get("country"), m.get("home_team"), m.get("away_team"), m.get("status"), m.get("minute"), as_float(home_score), as_float(away_score), result_label(home_score, away_score), has_live, has_odds, has_pick, m.get("source"), json_dumps(m), started, m.get("updated_at") or started))
        counts["matches"] += 1

    for o in rows(conn, "SELECT * FROM odds_snapshots ORDER BY created_at DESC LIMIT ?", (int(limit),)):
        cur.execute("""INSERT OR IGNORE INTO warehouse_odds_facts
            (id,match_id,external_id,league_name,bookmaker,market,home_team,away_team,home_price,draw_price,away_price,implied_home,implied_draw,implied_away,commence_time,payload_json,snapshot_at,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (stable_id("wo", o.get("id"), o.get("match_id"), o.get("bookmaker"), o.get("created_at")), o.get("match_id"), o.get("external_id"), o.get("league_name"), o.get("bookmaker"), o.get("market"), o.get("home_team"), o.get("away_team"), as_float(o.get("home_price")), as_float(o.get("draw_price")), as_float(o.get("away_price")), implied(o.get("home_price")), implied(o.get("draw_price")), implied(o.get("away_price")), o.get("commence_time"), json_dumps(o), started, o.get("created_at") or started))
        counts["odds"] += 1 if cur.rowcount else 0

    for p in rows(conn, "SELECT * FROM picks ORDER BY COALESCE(updated_at,created_at,'') DESC LIMIT ?", (int(limit),)):
        odds = as_float(p.get("odds"), 0.0)
        stake = as_float(p.get("stake_units") or p.get("stake"), 1.0)
        status = (p.get("result_status") or p.get("status") or "").lower()
        profit = round((odds - 1) * stake, 2) if status in {"won", "win", "ganado"} and odds else (-stake if status in {"lost", "loss", "perdido"} else 0.0)
        cur.execute("""INSERT OR REPLACE INTO warehouse_pick_facts
            (id,pick_id,match_id,match_date,league_name,home_team,away_team,selection,market,odds,confidence,stake,status,result_status,profit,payload_json,snapshot_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (stable_id("wp", p.get("id")), p.get("id"), p.get("match_id"), p.get("match_date"), p.get("competition_name") or p.get("league_name"), p.get("home_team"), p.get("away_team"), p.get("selection"), p.get("market") or p.get("pick_type"), odds, int(as_float(p.get("confidence"), 50)), stake, p.get("status"), p.get("result_status") or p.get("status"), profit, json_dumps(p), started, p.get("updated_at") or p.get("created_at") or started))
        counts["picks"] += 1

    user_rows = rows(conn, "SELECT id, membership, role, created_at, last_login FROM users LIMIT ?", (int(limit),))
    for u in user_rows:
        uid = u.get("id")
        favs = scalar(conn, "SELECT COUNT(*) FROM favorites WHERE user_id=?", (uid,), 0)
        acts = scalar(conn, "SELECT COUNT(*) FROM user_activity WHERE user_id=?", (uid,), 0)
        last_act = scalar(conn, "SELECT MAX(created_at) FROM user_activity WHERE user_id=?", (uid,), "")
        cur.execute("""INSERT OR REPLACE INTO warehouse_user_facts
            (id,user_id,membership,favorites_count,activity_count,last_activity_at,payload_json,snapshot_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (stable_id("wu", uid), uid, u.get("membership") or u.get("role") or "FREE", favs, acts, last_act, json_dumps(u), started))
        counts["users"] += 1

    metric_date = datetime.now().date().isoformat()
    metrics = {
        "matches_total": scalar(conn, "SELECT COUNT(*) FROM matches", default=0),
        "live_total": scalar(conn, "SELECT COUNT(*) FROM matches WHERE lower(coalesce(status,'')) IN ('live','1h','2h','ht','in_play')", default=0),
        "finished_total": scalar(conn, "SELECT COUNT(*) FROM matches WHERE lower(coalesce(status,'')) IN ('ft','final','finished','finalizado')", default=0),
        "odds_total": scalar(conn, "SELECT COUNT(*) FROM odds_snapshots", default=0),
        "picks_total": scalar(conn, "SELECT COUNT(*) FROM picks", default=0),
        "users_active": scalar(conn, "SELECT COUNT(DISTINCT user_id) FROM user_activity WHERE created_at >= date('now','-7 day')", default=0),
        "telegram_queue_pending": scalar(conn, "SELECT COUNT(*) FROM telegram_queue WHERE lower(coalesce(status,''))='pending'", default=0),
    }
    quality_parts = [metrics["matches_total"] > 0, metrics["odds_total"] > 0, metrics["picks_total"] > 0, counts["matches"] > 0, counts["users"] >= 0]
    metrics["data_quality_score"] = round(100 * sum(1 for x in quality_parts if x) / len(quality_parts))
    cur.execute("""INSERT OR REPLACE INTO warehouse_daily_metrics
        (metric_date,matches_total,live_total,finished_total,odds_total,picks_total,users_active,telegram_queue_pending,data_quality_score,payload_json,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (metric_date, metrics["matches_total"], metrics["live_total"], metrics["finished_total"], metrics["odds_total"], metrics["picks_total"], metrics["users_active"], metrics["telegram_queue_pending"], metrics["data_quality_score"], json_dumps(metrics), started))
    counts["daily"] = 1

    run_id = stable_id("wr", started, json_dumps(counts))
    cur.execute("""INSERT INTO warehouse_sync_runs(id,run_type,status,inserted,updated,skipped,details_json,started_at,finished_at)
        VALUES (?,?,?,?,?,?,?,?,?)""", (run_id, "snapshot", "OK", sum(counts.values()), counts["matches"], 0, json_dumps(counts), started, utc_now()))
    conn.commit()
    conn.close()
    return {"ok": True, "warehouse_v572": True, "run_id": run_id, "inserted": sum(counts.values()), "updated": counts["matches"], "skipped": 0, "counts": counts, "metrics": metrics}


def warehouse_summary(db_path: str) -> Dict[str, Any]:
    ensure_warehouse_schema(db_path)
    conn = connect(db_path)
    latest = row_dict(conn.execute("SELECT * FROM warehouse_daily_metrics ORDER BY metric_date DESC LIMIT 1").fetchone())
    recent_runs = rows(conn, "SELECT * FROM warehouse_sync_runs ORDER BY started_at DESC LIMIT 8")
    summary = {
        "schema": "warehouse_v572",
        "match_facts": scalar(conn, "SELECT COUNT(*) FROM warehouse_match_facts", default=0),
        "odds_facts": scalar(conn, "SELECT COUNT(*) FROM warehouse_odds_facts", default=0),
        "pick_facts": scalar(conn, "SELECT COUNT(*) FROM warehouse_pick_facts", default=0),
        "user_facts": scalar(conn, "SELECT COUNT(*) FROM warehouse_user_facts", default=0),
        "daily_metrics": scalar(conn, "SELECT COUNT(*) FROM warehouse_daily_metrics", default=0),
        "quality_score": latest.get("data_quality_score", 0),
        "latest_metrics": latest,
        "recent_runs": recent_runs,
    }
    conn.close()
    return summary
