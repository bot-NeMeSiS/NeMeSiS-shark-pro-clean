"""Historical SHARK performance and ROI helpers.

Pure SQLite helpers. Flask routes and UI integration live in app.py.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn


def rows(conn: sqlite3.Connection, query: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
    try:
        cur = conn.execute(query, tuple(params))
        return [dict(row) for row in cur.fetchall()]
    except sqlite3.Error:
        return []


def one(conn: sqlite3.Connection, query: str, params: Iterable[Any] = ()) -> Dict[str, Any]:
    data = rows(conn, query, params)
    return data[0] if data else {}


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return default


def normalize_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"won", "win", "ganado", "green", "acierto"}:
        return "won"
    if text in {"lost", "loss", "perdido", "red", "fallo"}:
        return "lost"
    if text in {"void", "push", "nulo", "cancelled", "cancelado"}:
        return "void"
    return "pending"


def ensure_shark_performance_schema(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS shark_performance_daily(
            id TEXT PRIMARY KEY,
            day TEXT UNIQUE,
            picks INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            voids INTEGER DEFAULT 0,
            pending INTEGER DEFAULT 0,
            stake_units REAL DEFAULT 0,
            profit_units REAL DEFAULT 0,
            roi REAL DEFAULT 0,
            winrate REAL DEFAULT 0,
            payload_json TEXT,
            rebuilt_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS shark_performance_summary(
            id TEXT PRIMARY KEY,
            scope TEXT UNIQUE,
            sample_size INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            voids INTEGER DEFAULT 0,
            pending INTEGER DEFAULT 0,
            stake_units REAL DEFAULT 0,
            profit_units REAL DEFAULT 0,
            roi REAL DEFAULT 0,
            yield_pct REAL DEFAULT 0,
            winrate REAL DEFAULT 0,
            current_streak_type TEXT,
            current_streak_count INTEGER DEFAULT 0,
            best_win_streak INTEGER DEFAULT 0,
            worst_loss_streak INTEGER DEFAULT 0,
            by_league_json TEXT,
            by_market_json TEXT,
            recent_picks_json TEXT,
            payload_json TEXT,
            rebuilt_at TEXT
        )"""
    )
    migrations = [
        ("shark_performance_daily", "day", "TEXT"),
        ("shark_performance_daily", "picks", "INTEGER DEFAULT 0"),
        ("shark_performance_daily", "wins", "INTEGER DEFAULT 0"),
        ("shark_performance_daily", "losses", "INTEGER DEFAULT 0"),
        ("shark_performance_daily", "voids", "INTEGER DEFAULT 0"),
        ("shark_performance_daily", "pending", "INTEGER DEFAULT 0"),
        ("shark_performance_daily", "stake_units", "REAL DEFAULT 0"),
        ("shark_performance_daily", "profit_units", "REAL DEFAULT 0"),
        ("shark_performance_daily", "roi", "REAL DEFAULT 0"),
        ("shark_performance_daily", "winrate", "REAL DEFAULT 0"),
        ("shark_performance_daily", "payload_json", "TEXT"),
        ("shark_performance_daily", "rebuilt_at", "TEXT"),
        ("shark_performance_summary", "scope", "TEXT"),
        ("shark_performance_summary", "sample_size", "INTEGER DEFAULT 0"),
        ("shark_performance_summary", "wins", "INTEGER DEFAULT 0"),
        ("shark_performance_summary", "losses", "INTEGER DEFAULT 0"),
        ("shark_performance_summary", "voids", "INTEGER DEFAULT 0"),
        ("shark_performance_summary", "pending", "INTEGER DEFAULT 0"),
        ("shark_performance_summary", "stake_units", "REAL DEFAULT 0"),
        ("shark_performance_summary", "profit_units", "REAL DEFAULT 0"),
        ("shark_performance_summary", "roi", "REAL DEFAULT 0"),
        ("shark_performance_summary", "yield_pct", "REAL DEFAULT 0"),
        ("shark_performance_summary", "winrate", "REAL DEFAULT 0"),
        ("shark_performance_summary", "current_streak_type", "TEXT"),
        ("shark_performance_summary", "current_streak_count", "INTEGER DEFAULT 0"),
        ("shark_performance_summary", "best_win_streak", "INTEGER DEFAULT 0"),
        ("shark_performance_summary", "worst_loss_streak", "INTEGER DEFAULT 0"),
        ("shark_performance_summary", "by_league_json", "TEXT"),
        ("shark_performance_summary", "by_market_json", "TEXT"),
        ("shark_performance_summary", "recent_picks_json", "TEXT"),
        ("shark_performance_summary", "payload_json", "TEXT"),
        ("shark_performance_summary", "rebuilt_at", "TEXT"),
    ]
    for table, column, definition in migrations:
        try:
            existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except sqlite3.Error:
            pass
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shark_performance_daily_day ON shark_performance_daily(day)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shark_performance_summary_scope ON shark_performance_summary(scope)")
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "shark_performance_v587"}


def _read_table(conn: sqlite3.Connection, table: str, limit: int) -> List[Dict[str, Any]]:
    return rows(conn, f"SELECT * FROM {table} LIMIT ?", (int(limit),))


def _pick_profit(row: Dict[str, Any]) -> float:
    existing = row.get("profit_units")
    if existing is None:
        existing = row.get("profit")
    if existing not in (None, ""):
        return round(as_float(existing), 2)
    status = normalize_status(row.get("result_status") or row.get("status"))
    stake = as_float(row.get("stake_units") or row.get("stake"), 1.0)
    odds = as_float(row.get("odds") or row.get("odds_value"), 0.0)
    if status == "won" and odds > 1:
        return round((odds - 1) * stake, 2)
    if status == "lost":
        return round(-stake, 2)
    return 0.0


def _normalize_pick(row: Dict[str, Any]) -> Dict[str, Any]:
    status = normalize_status(row.get("result_status") or row.get("status") or row.get("outcome"))
    stake = as_float(row.get("stake_units") or row.get("stake"), 1.0)
    item = {
        "pick_id": row.get("pick_id") or row.get("id"),
        "match_id": row.get("match_id"),
        "day": str(row.get("match_date") or row.get("created_at") or row.get("snapshot_at") or "")[:10] or "sin_fecha",
        "league_name": row.get("league_name") or row.get("competition_name") or "Competición",
        "home_team": row.get("home_team") or "",
        "away_team": row.get("away_team") or "",
        "market": row.get("market") or row.get("pick_type") or "Mercado",
        "selection": row.get("selection") or row.get("title") or "Pick SHARK",
        "odds": as_float(row.get("odds") or row.get("odds_value"), 0.0),
        "stake_units": stake,
        "confidence": as_int(row.get("confidence") or row.get("shark_score"), 0),
        "result_status": status,
        "profit_units": _pick_profit(row),
    }
    item["is_settled"] = status in {"won", "lost", "void"}
    return item


def load_performance_picks(db_path: str, limit: int = 2000) -> List[Dict[str, Any]]:
    conn = connect(db_path)
    raw = _read_table(conn, "warehouse_pick_facts", limit)
    if not raw:
        raw = _read_table(conn, "historical_picks", limit)
    if not raw:
        raw = _read_table(conn, "picks", limit)
    conn.close()
    return [_normalize_pick(row) for row in raw]


def _stats(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    wins = sum(1 for item in items if item["result_status"] == "won")
    losses = sum(1 for item in items if item["result_status"] == "lost")
    voids = sum(1 for item in items if item["result_status"] == "void")
    pending = sum(1 for item in items if item["result_status"] == "pending")
    stake = round(sum(as_float(item.get("stake_units"), 1.0) for item in items), 2)
    profit = round(sum(as_float(item.get("profit_units"), 0.0) for item in items), 2)
    settled = wins + losses
    winrate = round((wins / settled) * 100, 2) if settled else 0.0
    roi = round((profit / stake) * 100, 2) if stake else 0.0
    return {
        "sample_size": len(items),
        "picks": len(items),
        "wins": wins,
        "losses": losses,
        "voids": voids,
        "pending": pending,
        "stake_units": stake,
        "profit_units": profit,
        "roi": roi,
        "yield_pct": roi,
        "winrate": winrate,
    }


def _group_stats(items: List[Dict[str, Any]], key: str, limit: int = 8) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(str(item.get(key) or "Sin dato"), []).append(item)
    data = []
    for name, values in groups.items():
        stat = _stats(values)
        stat[key] = name
        data.append(stat)
    return sorted(data, key=lambda x: (x["sample_size"], x["roi"], x["winrate"]), reverse=True)[:limit]


def _daily_stats(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(item.get("day") or "sin_fecha", []).append(item)
    data = []
    for day, values in groups.items():
        stat = _stats(values)
        stat["day"] = day
        data.append(stat)
    return sorted(data, key=lambda x: x["day"], reverse=True)


def _streaks(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    settled = [item for item in sorted(items, key=lambda x: (x.get("day") or "", x.get("pick_id") or "")) if item["result_status"] in {"won", "lost"}]
    best_win = worst_loss = cur_win = cur_loss = 0
    for item in settled:
        if item["result_status"] == "won":
            cur_win += 1
            cur_loss = 0
        else:
            cur_loss += 1
            cur_win = 0
        best_win = max(best_win, cur_win)
        worst_loss = max(worst_loss, cur_loss)
    current_type = "none"
    current_count = 0
    if settled:
        last = settled[-1]["result_status"]
        current_type = "win" if last == "won" else "loss"
        for item in reversed(settled):
            if item["result_status"] != last:
                break
            current_count += 1
    return {
        "current_streak_type": current_type,
        "current_streak_count": current_count,
        "best_win_streak": best_win,
        "worst_loss_streak": worst_loss,
    }


def rebuild_shark_performance(db_path: str, limit: int = 2000) -> Dict[str, Any]:
    ensure_shark_performance_schema(db_path)
    picks = load_performance_picks(db_path, limit=limit)
    built = utc_now()
    overall = _stats(picks)
    streaks = _streaks(picks)
    by_league = _group_stats(picks, "league_name", limit=12)
    by_market = _group_stats(picks, "market", limit=12)
    daily = _daily_stats(picks)
    recent = sorted(picks, key=lambda x: (x.get("day") or "", x.get("pick_id") or ""), reverse=True)[:20]
    payload = {
        "source": "warehouse/historical/picks",
        "readiness_score": min(100, 30 + min(60, overall["sample_size"] * 3) + (10 if overall["wins"] + overall["losses"] else 0)),
    }
    conn = connect(db_path)
    conn.execute("DELETE FROM shark_performance_daily")
    conn.execute("DELETE FROM shark_performance_summary")
    for item in daily:
        conn.execute(
            """INSERT OR REPLACE INTO shark_performance_daily
               (id,day,picks,wins,losses,voids,pending,stake_units,profit_units,roi,winrate,payload_json,rebuilt_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                f"daily-{item['day']}",
                item["day"],
                item["picks"],
                item["wins"],
                item["losses"],
                item["voids"],
                item["pending"],
                item["stake_units"],
                item["profit_units"],
                item["roi"],
                item["winrate"],
                json.dumps(item, ensure_ascii=False),
                built,
            ),
        )
    conn.execute(
        """INSERT OR REPLACE INTO shark_performance_summary
           (id,scope,sample_size,wins,losses,voids,pending,stake_units,profit_units,roi,yield_pct,winrate,
            current_streak_type,current_streak_count,best_win_streak,worst_loss_streak,by_league_json,by_market_json,recent_picks_json,payload_json,rebuilt_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "global",
            "global",
            overall["sample_size"],
            overall["wins"],
            overall["losses"],
            overall["voids"],
            overall["pending"],
            overall["stake_units"],
            overall["profit_units"],
            overall["roi"],
            overall["yield_pct"],
            overall["winrate"],
            streaks["current_streak_type"],
            streaks["current_streak_count"],
            streaks["best_win_streak"],
            streaks["worst_loss_streak"],
            json.dumps(by_league, ensure_ascii=False),
            json.dumps(by_market, ensure_ascii=False),
            json.dumps(recent, ensure_ascii=False),
            json.dumps(payload, ensure_ascii=False),
            built,
        ),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "shark_performance_v587", "rebuilt_at": built, "picks_read": len(picks), "summary": {**overall, **streaks, **payload}}


def _loads(value: Any, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def shark_performance_summary(db_path: str, limit: int = 2000) -> Dict[str, Any]:
    ensure_shark_performance_schema(db_path)
    conn = connect(db_path)
    summary = one(conn, "SELECT * FROM shark_performance_summary WHERE scope='global' LIMIT 1")
    if not summary:
        conn.close()
        rebuild_shark_performance(db_path, limit=limit)
        conn = connect(db_path)
        summary = one(conn, "SELECT * FROM shark_performance_summary WHERE scope='global' LIMIT 1")
    daily = rows(conn, "SELECT * FROM shark_performance_daily ORDER BY day DESC LIMIT 30")
    conn.close()
    payload = _loads(summary.get("payload_json"), {})
    return {
        "ok": True,
        "schema": "shark_performance_v587",
        "status": "activo" if summary.get("sample_size", 0) else "histórico insuficiente",
        "readiness_score": payload.get("readiness_score", 0),
        "summary": summary,
        "daily": daily,
        "by_league": _loads(summary.get("by_league_json"), []),
        "by_market": _loads(summary.get("by_market_json"), []),
        "recent_picks": _loads(summary.get("recent_picks_json"), []),
        "note": "Rendimiento calculado desde picks históricos, warehouse y picks actuales. No inventa resultados.",
    }
