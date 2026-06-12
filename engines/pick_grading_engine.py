"""Smart Pick Grading & Auto Validation engine for NeMeSiS SHARK PRO.

V577 adds a safe grading layer: it reads existing picks/matches/results, calculates
settlement candidates, creates audit records and gives SHARK a quality score for
each pick without deleting or rewriting core data blindly.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable

try:
    from engines.team_identity_engine import identity_payload
except Exception:  # pragma: no cover - keeps grading standalone in minimal environments
    identity_payload = None


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


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_status(value: Any) -> str:
    text = normalize_text(value)
    if text in {"won", "win", "ganado", "green", "acertado"}:
        return "won"
    if text in {"lost", "loss", "perdido", "red", "fallado"}:
        return "lost"
    if text in {"void", "push", "nulo", "cancelled", "cancelado"}:
        return "void"
    if any(x in text for x in ["final", "finished", "ft", "aet", "pen", "terminado", "acabado"]):
        return "finished"
    return "pending"


def parse_score(value: Any, home_score: Any = None, away_score: Any = None) -> tuple[int | None, int | None]:
    if home_score not in (None, "") and away_score not in (None, ""):
        return as_int(home_score), as_int(away_score)
    text = str(value or "")
    for sep in ["-", ":", "–"]:
        if sep in text:
            left, right = text.split(sep, 1)
            return as_int(left), as_int(right)
    return None, None


def ensure_pick_grading_schema(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS pick_grading_results(
        id TEXT PRIMARY KEY,
        pick_id TEXT NOT NULL,
        match_id TEXT,
        grading_status TEXT,
        result_status TEXT,
        confidence_before INTEGER DEFAULT 50,
        confidence_after INTEGER DEFAULT 50,
        odds REAL DEFAULT 0,
        stake REAL DEFAULT 1,
        profit REAL DEFAULT 0,
        grading_score INTEGER DEFAULT 0,
        auto_validated INTEGER DEFAULT 0,
        reason TEXT,
        payload_json TEXT,
        graded_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS pick_grading_runs(
        id TEXT PRIMARY KEY,
        status TEXT,
        picks_checked INTEGER DEFAULT 0,
        auto_validated INTEGER DEFAULT 0,
        pending INTEGER DEFAULT 0,
        won INTEGER DEFAULT 0,
        lost INTEGER DEFAULT 0,
        voids INTEGER DEFAULT 0,
        profit REAL DEFAULT 0,
        details_json TEXT,
        started_at TEXT,
        finished_at TEXT
    )""")
    for stmt in [
        "CREATE INDEX IF NOT EXISTS idx_pick_grading_pick ON pick_grading_results(pick_id)",
        "CREATE INDEX IF NOT EXISTS idx_pick_grading_status ON pick_grading_results(result_status, graded_at)",
        "CREATE INDEX IF NOT EXISTS idx_pick_grading_score ON pick_grading_results(grading_score)",
    ]:
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "pick_grading_v577"}


def _load_candidates(conn: sqlite3.Connection, limit: int) -> list[Dict[str, Any]]:
    query = """SELECT p.id AS pick_id, p.match_id, p.match_date, p.competition_name, p.home_team, p.away_team,
                      p.pick_type, p.selection, p.odds, p.confidence, p.stake_units, p.status AS pick_status,
                      m.status AS match_status, m.score, m.home_score, m.away_score, m.updated_at AS match_updated_at
               FROM picks p
               LEFT JOIN matches m ON m.id = p.match_id
               ORDER BY COALESCE(p.updated_at,p.created_at,p.match_date,'') DESC
               LIMIT ?"""
    items = rows(conn, query, (int(limit),))
    if items:
        return items
    return rows(conn, """SELECT pick_id, match_id, league_name AS competition_name, home_team, away_team,
                              market AS pick_type, selection, odds, confidence, stake AS stake_units,
                              status AS pick_status, result_status, snapshot_at AS match_updated_at
                       FROM warehouse_pick_facts ORDER BY COALESCE(updated_at,snapshot_at,'') DESC LIMIT ?""", (int(limit),))


def _settle_1x2(selection: str, home_goals: int, away_goals: int, home: str, away: str) -> str:
    sel = normalize_text(selection)
    if home_goals == away_goals:
        outcome = "draw"
    elif home_goals > away_goals:
        outcome = "home"
    else:
        outcome = "away"
    home_t = normalize_text(home)
    away_t = normalize_text(away)
    if sel in {"x", "draw", "empate"}:
        wanted = "draw"
    elif home_t and home_t in sel:
        wanted = "home"
    elif away_t and away_t in sel:
        wanted = "away"
    elif sel in {"1", "home", "local"}:
        wanted = "home"
    elif sel in {"2", "away", "visitante"}:
        wanted = "away"
    else:
        return "pending"
    return "won" if wanted == outcome else "lost"


def infer_result(pick: Dict[str, Any]) -> tuple[str, str, int]:
    explicit = normalize_status(pick.get("result_status") or pick.get("pick_status"))
    if explicit in {"won", "lost", "void"}:
        return explicit, "Resultado ya marcado en el pick.", 90
    match_status = normalize_status(pick.get("match_status"))
    home_goals, away_goals = parse_score(pick.get("score"), pick.get("home_score"), pick.get("away_score"))
    if match_status != "finished" or home_goals is None or away_goals is None:
        return "pending", "Partido sin resultado final fiable todavía.", 35
    market = normalize_text(pick.get("pick_type"))
    selection = str(pick.get("selection") or "")
    if any(x in market for x in ["1x2", "winner", "ganador", "moneyline", "resultado"]):
        res = _settle_1x2(selection, home_goals, away_goals, pick.get("home_team"), pick.get("away_team"))
        if res != "pending":
            return res, "Validado automáticamente por marcador final 1X2.", 82
    # Conservative fallback: finished match but market not understood.
    return "pending", "Marcador final detectado, pero el mercado necesita revisión manual.", 55


def profit_for(result_status: str, odds: Any, stake: Any) -> float:
    stake_f = as_float(stake, 1.0)
    odds_f = as_float(odds, 0.0)
    if result_status == "won" and odds_f > 1:
        return round((odds_f - 1) * stake_f, 2)
    if result_status == "lost":
        return round(-stake_f, 2)
    return 0.0


def grade_pick(pick: Dict[str, Any]) -> Dict[str, Any]:
    result, reason, evidence_score = infer_result(pick)
    confidence = as_int(pick.get("confidence"), 50)
    odds = as_float(pick.get("odds"), 0.0)
    stake = as_float(pick.get("stake_units"), 1.0)
    profit = profit_for(result, odds, stake)
    if result == "won":
        after = min(100, confidence + 4)
    elif result == "lost":
        after = max(0, confidence - 6)
    else:
        after = confidence
    quality_base = 35 + min(30, max(0, confidence - 50)) + min(20, max(0, evidence_score - 50))
    if result == "won":
        quality_base += 10
    elif result == "lost":
        quality_base -= 8
    grading_score = int(max(0, min(100, quality_base)))
    auto_validated = 1 if result in {"won", "lost", "void"} and evidence_score >= 80 else 0
    return {
        "result_status": result,
        "reason": reason,
        "confidence_before": confidence,
        "confidence_after": after,
        "odds": odds,
        "stake": stake,
        "profit": profit,
        "grading_score": grading_score,
        "auto_validated": auto_validated,
        "evidence_score": evidence_score,
    }


def run_pick_grading(db_path: str, limit: int = 500, apply: bool = False) -> Dict[str, Any]:
    ensure_pick_grading_schema(db_path)
    started = utc_now()
    conn = connect(db_path)
    cur = conn.cursor()
    picks = _load_candidates(conn, limit)
    stats = {"auto_validated": 0, "pending": 0, "won": 0, "lost": 0, "voids": 0, "profit": 0.0}
    for p in picks:
        grade = grade_pick(p)
        result = grade["result_status"]
        if result == "pending":
            stats["pending"] += 1
        elif result == "void":
            stats["voids"] += 1
        else:
            stats[result] += 1
        stats["auto_validated"] += int(grade["auto_validated"])
        stats["profit"] += grade["profit"]
        gid = stable_id("pgr", p.get("pick_id"), result, p.get("match_updated_at"), grade["evidence_score"])
        cur.execute("""INSERT OR REPLACE INTO pick_grading_results
            (id,pick_id,match_id,grading_status,result_status,confidence_before,confidence_after,odds,stake,profit,grading_score,auto_validated,reason,payload_json,graded_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (gid, p.get("pick_id"), p.get("match_id"), "AUTO" if grade["auto_validated"] else "REVIEW", result,
             grade["confidence_before"], grade["confidence_after"], grade["odds"], grade["stake"], grade["profit"],
             grade["grading_score"], grade["auto_validated"], grade["reason"], json_dumps({"pick": p, "grade": grade}), started))
        if apply and grade["auto_validated"] and p.get("pick_id"):
            try:
                cur.execute("UPDATE picks SET status=?, updated_at=? WHERE id=?", (result.upper(), started, p.get("pick_id")))
            except sqlite3.OperationalError:
                pass
    run_id = stable_id("pgrun", started, len(picks), stats["auto_validated"])
    cur.execute("""INSERT INTO pick_grading_runs(id,status,picks_checked,auto_validated,pending,won,lost,voids,profit,details_json,started_at,finished_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (run_id, "OK", len(picks), stats["auto_validated"], stats["pending"], stats["won"], stats["lost"], stats["voids"], round(stats["profit"], 2), json_dumps({"limit": limit, "apply": apply}), started, utc_now()))
    conn.commit()
    conn.close()
    return {"ok": True, "pick_grading_v577": True, "run_id": run_id, "picks_checked": len(picks), **stats, "profit": round(stats["profit"], 2), "applied": bool(apply)}



def _enrich_recent_result(row: Dict[str, Any]) -> Dict[str, Any]:
    """Add safe client-facing match/team context to a grading row.

    The grading table stores the original pick payload as JSON. We only surface
    fields that already exist there and use a local crest fallback; no results,
    odds or team strength are invented.
    """
    item = dict(row or {})
    payload = {}
    try:
        payload = json.loads(item.get("payload_json") or "{}") or {}
    except Exception:
        payload = {}
    pick = payload.get("pick") if isinstance(payload, dict) else {}
    if not isinstance(pick, dict):
        pick = {}
    for key in ("home_team", "away_team", "competition_name", "league_name", "selection", "pick_type", "odds", "match_id"):
        if pick.get(key) not in (None, "") and item.get(key) in (None, ""):
            item[key] = pick.get(key)
    if item.get("home_team") and identity_payload:
        item["home_identity"] = identity_payload(item.get("home_team"), source="track_record")
    if item.get("away_team") and identity_payload:
        item["away_identity"] = identity_payload(item.get("away_team"), source="track_record")
    item["safe_competition"] = item.get("competition_name") or item.get("league_name") or "Competición"
    item["pick_label"] = item.get("selection") or item.get("pick_type") or f"Pick {item.get('pick_id') or ''}".strip()
    return item

def pick_grading_summary(db_path: str) -> Dict[str, Any]:
    ensure_pick_grading_schema(db_path)
    conn = connect(db_path)
    total = scalar(conn, "SELECT COUNT(*) FROM pick_grading_results", default=0)
    auto_validated = scalar(conn, "SELECT COUNT(*) FROM pick_grading_results WHERE auto_validated=1", default=0)
    pending = scalar(conn, "SELECT COUNT(*) FROM pick_grading_results WHERE result_status='pending'", default=0)
    won = scalar(conn, "SELECT COUNT(*) FROM pick_grading_results WHERE result_status='won'", default=0)
    lost = scalar(conn, "SELECT COUNT(*) FROM pick_grading_results WHERE result_status='lost'", default=0)
    profit = scalar(conn, "SELECT ROUND(SUM(profit),2) FROM pick_grading_results", default=0) or 0
    avg_score = scalar(conn, "SELECT ROUND(AVG(grading_score),1) FROM pick_grading_results", default=0) or 0
    recent = [_enrich_recent_result(r) for r in rows(conn, "SELECT * FROM pick_grading_results ORDER BY graded_at DESC LIMIT 10")]
    runs = rows(conn, "SELECT * FROM pick_grading_runs ORDER BY started_at DESC LIMIT 6")
    checks = [total > 0, auto_validated > 0 or pending > 0, len(runs) > 0, avg_score >= 40]
    readiness = round(100 * sum(1 for x in checks if x) / len(checks))
    conn.close()
    return {
        "schema": "pick_grading_v577",
        "status": "operativo" if readiness >= 50 else "esperando picks/resultados",
        "readiness_score": readiness,
        "graded_total": total,
        "auto_validated": auto_validated,
        "pending_review": pending,
        "won": won,
        "lost": lost,
        "profit": profit,
        "avg_grading_score": avg_score,
        "recent_results": recent,
        "recent_runs": runs,
        "note": "V577 valida picks con resultados fiables, deja revisión manual cuando el mercado no es seguro y alimenta la memoria SHARK.",
    }
