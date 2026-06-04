"""SHARK Accuracy Engine V600.

Capa conservadora para medir precision real, calibrar confianza y ordenar
mercados con datos guardados. No llama APIs externas ni inventa resultados: solo
lee SQLite y genera métricas propias de NeMeSiS para mejorar los pronósticos.
"""

from __future__ import annotations

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


def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def json_dumps(payload: Any) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, default=str)[:30000]


def ensure_shark_accuracy_schema(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS shark_accuracy_predictions(
        id TEXT PRIMARY KEY,
        pick_id TEXT,
        match_id TEXT,
        league_name TEXT,
        market TEXT,
        selection TEXT,
        predicted_score INTEGER DEFAULT 0,
        predicted_confidence INTEGER DEFAULT 0,
        odds REAL DEFAULT 0,
        result_status TEXT,
        profit_units REAL DEFAULT 0,
        accuracy_bucket TEXT,
        quality_points INTEGER DEFAULT 0,
        payload_json TEXT,
        created_at TEXT,
        evaluated_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS shark_accuracy_calibration(
        bucket TEXT PRIMARY KEY,
        sample_size INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        winrate REAL DEFAULT 0,
        expected_confidence REAL DEFAULT 0,
        calibration_gap REAL DEFAULT 0,
        reliability_score INTEGER DEFAULT 0,
        recommendation TEXT,
        rebuilt_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS shark_accuracy_market_rankings(
        market TEXT PRIMARY KEY,
        sample_size INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        winrate REAL DEFAULT 0,
        roi REAL DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        accuracy_score INTEGER DEFAULT 0,
        rank_label TEXT,
        recommendation TEXT,
        rebuilt_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS shark_accuracy_profiles(
        id TEXT PRIMARY KEY,
        picks_analyzed INTEGER DEFAULT 0,
        settled_picks INTEGER DEFAULT 0,
        winrate REAL DEFAULT 0,
        roi REAL DEFAULT 0,
        profit_units REAL DEFAULT 0,
        calibration_score INTEGER DEFAULT 0,
        market_score INTEGER DEFAULT 0,
        sqi INTEGER DEFAULT 0,
        status TEXT,
        payload_json TEXT,
        rebuilt_at TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_accuracy_predictions_market ON shark_accuracy_predictions(market)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_accuracy_predictions_result ON shark_accuracy_predictions(result_status)")
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "shark_accuracy_v600"}


def normalize_result(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"won", "win", "ganado", "acertado", "green", "success"} or "gan" in text or "acert" in text:
        return "won"
    if text in {"lost", "loss", "perdido", "fallado", "red", "fail"} or "perd" in text or "fall" in text:
        return "lost"
    if text in {"void", "push", "nul", "nulo", "cancelled", "cancelado"}:
        return "void"
    return "pending"


def pick_value(row: Dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row and row.get(name) not in (None, ""):
            return row.get(name)
    return default


def load_pick_rows(conn: sqlite3.Connection, limit: int) -> list[Dict[str, Any]]:
    candidates = []
    for table in ["picks", "warehouse_pick_facts", "historical_picks"]:
        data = rows(conn, f"SELECT * FROM {table} ORDER BY COALESCE(created_at, updated_at, snapshot_at, '') DESC LIMIT ?", (int(limit),))
        if data:
            candidates.extend(data)
    # dedupe by id/signature preserving order
    seen = set()
    out = []
    for item in candidates:
        key = str(pick_value(item, "id", "pick_id", "signature", default="")) or json_dumps(item)[:120]
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out[: int(limit)]


def market_name(row: Dict[str, Any]) -> str:
    return str(pick_value(row, "market", "market_name", "bet_type", "prediction_type", default="General") or "General").strip()[:80]


def prediction_score(row: Dict[str, Any]) -> int:
    return clamp(as_float(pick_value(row, "shark_score", "score", "confidence", "confidence_score", "predicted_score", default=70), 70), 1, 100)


def confidence_bucket(score: int) -> str:
    if score >= 90:
        return "90-100"
    if score >= 80:
        return "80-89"
    if score >= 70:
        return "70-79"
    if score >= 60:
        return "60-69"
    return "0-59"


def profit_for(row: Dict[str, Any], result: str) -> float:
    explicit = pick_value(row, "profit_units", "profit", "benefit_units", "net_units", default=None)
    if explicit not in (None, ""):
        return round(as_float(explicit, 0), 3)
    stake = max(1.0, as_float(pick_value(row, "stake", "stake_units", "recommended_stake", default=1), 1))
    odds = as_float(pick_value(row, "odds", "odd", "price", "quota", "cuota", default=0), 0)
    if result == "won" and odds > 1:
        return round((odds - 1) * stake, 3)
    if result == "lost":
        return round(-stake, 3)
    return 0.0


def rebuild_shark_accuracy_engine(db_path: str, limit: int = 1500) -> Dict[str, Any]:
    ensure_shark_accuracy_schema(db_path)
    conn = connect(db_path)
    now = utc_now()
    pick_rows = load_pick_rows(conn, limit)
    conn.execute("DELETE FROM shark_accuracy_predictions")
    conn.execute("DELETE FROM shark_accuracy_calibration")
    conn.execute("DELETE FROM shark_accuracy_market_rankings")

    by_bucket: Dict[str, Dict[str, float]] = {}
    by_market: Dict[str, Dict[str, float]] = {}
    analyzed = 0
    settled = 0
    wins = 0
    profit = 0.0
    stake_total = 0.0

    for idx, row in enumerate(pick_rows, start=1):
        result = normalize_result(pick_value(row, "result_status", "status", "outcome", "result", "grading_status", default="pending"))
        score = prediction_score(row)
        bucket = confidence_bucket(score)
        market = market_name(row)
        odds = as_float(pick_value(row, "odds", "odd", "price", "quota", "cuota", default=0), 0)
        item_profit = profit_for(row, result)
        stake = max(1.0, as_float(pick_value(row, "stake", "stake_units", "recommended_stake", default=1), 1)) if result in {"won", "lost"} else 0
        quality = score
        if result == "won":
            quality += 10
        elif result == "lost":
            quality -= 14
        elif result == "pending":
            quality -= 2
        quality = clamp(quality)
        pick_id = str(pick_value(row, "id", "pick_id", default=f"accuracy-{idx}"))
        conn.execute("""INSERT OR REPLACE INTO shark_accuracy_predictions
            (id,pick_id,match_id,league_name,market,selection,predicted_score,predicted_confidence,odds,result_status,profit_units,accuracy_bucket,quality_points,payload_json,created_at,evaluated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            f"acc-{pick_id}", pick_id, str(pick_value(row, "match_id", "event_id", default="")),
            str(pick_value(row, "league", "league_name", "competition", default="") or ""), market,
            str(pick_value(row, "selection", "pick", "recommended_pick", "prediction", default="") or ""),
            score, score, odds, result, item_profit, bucket, quality, json_dumps(row),
            str(pick_value(row, "created_at", "snapshot_at", default=now) or now), now,
        ))
        analyzed += 1
        if result in {"won", "lost"}:
            settled += 1
            stake_total += stake
            profit += item_profit
            if result == "won":
                wins += 1
            b = by_bucket.setdefault(bucket, {"sample": 0, "wins": 0, "score_sum": 0})
            b["sample"] += 1; b["score_sum"] += score; b["wins"] += 1 if result == "won" else 0
            m = by_market.setdefault(market, {"sample": 0, "wins": 0, "profit": 0.0, "stake": 0.0, "score_sum": 0})
            m["sample"] += 1; m["wins"] += 1 if result == "won" else 0; m["profit"] += item_profit; m["stake"] += stake; m["score_sum"] += score

    for bucket, s in sorted(by_bucket.items()):
        sample = int(s["sample"])
        winrate = round((s["wins"] / max(1, sample)) * 100, 2)
        expected = round(s["score_sum"] / max(1, sample), 2)
        gap = round(winrate - expected, 2)
        reliability = clamp(min(100, sample * 8) - abs(gap) * 0.7)
        recommendation = "Calibración correcta" if abs(gap) <= 8 else ("SHARK está siendo conservador" if gap > 0 else "Reducir confianza en este rango")
        conn.execute("""INSERT OR REPLACE INTO shark_accuracy_calibration
            (bucket,sample_size,wins,losses,winrate,expected_confidence,calibration_gap,reliability_score,recommendation,rebuilt_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", (bucket, sample, int(s["wins"]), sample-int(s["wins"]), winrate, expected, gap, reliability, recommendation, now))

    for market, s in sorted(by_market.items(), key=lambda kv: kv[1]["sample"], reverse=True):
        sample = int(s["sample"])
        winrate = round((s["wins"] / max(1, sample)) * 100, 2)
        roi = round((s["profit"] / max(1.0, s["stake"])) * 100, 2)
        avg_conf = round(s["score_sum"] / max(1, sample), 2)
        score = clamp((winrate * 0.42) + (max(-20, min(30, roi)) * 0.8) + (avg_conf * 0.28) + min(12, sample * 0.45))
        label = "Excelente" if score >= 82 else "Fuerte" if score >= 72 else "Observación" if score >= 60 else "Riesgo"
        recommendation = "Priorizar si hay value" if score >= 72 else "Usar con prudencia" if score >= 60 else "Evitar salvo señal muy clara"
        conn.execute("""INSERT OR REPLACE INTO shark_accuracy_market_rankings
            (market,sample_size,wins,losses,winrate,roi,avg_confidence,accuracy_score,rank_label,recommendation,rebuilt_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (market, sample, int(s["wins"]), sample-int(s["wins"]), winrate, roi, avg_conf, score, label, recommendation, now))

    winrate_total = round((wins / max(1, settled)) * 100, 2) if settled else 0
    roi_total = round((profit / max(1.0, stake_total)) * 100, 2) if stake_total else 0
    avg_calibration = as_float(scalar(conn, "SELECT AVG(reliability_score) FROM shark_accuracy_calibration", default=0), 0)
    avg_market = as_float(scalar(conn, "SELECT AVG(accuracy_score) FROM shark_accuracy_market_rankings", default=0), 0)
    data_depth = clamp(min(100, settled * 2.2), 0, 100)
    sqi = clamp((winrate_total * 0.30) + (max(-10, min(25, roi_total)) * 0.85) + (avg_calibration * 0.25) + (avg_market * 0.25) + (data_depth * 0.20))
    status = "maduro" if sqi >= 82 else "fuerte" if sqi >= 70 else "en aprendizaje" if analyzed else "sin datos"
    payload = {
        "top_markets": rows(conn, "SELECT * FROM shark_accuracy_market_rankings ORDER BY accuracy_score DESC, sample_size DESC LIMIT 6"),
        "calibration": rows(conn, "SELECT * FROM shark_accuracy_calibration ORDER BY bucket DESC"),
        "note": "Métricas derivadas propias de NeMeSiS. No redistribuye datos crudos de terceros.",
    }
    conn.execute("""INSERT OR REPLACE INTO shark_accuracy_profiles
        (id,picks_analyzed,settled_picks,winrate,roi,profit_units,calibration_score,market_score,sqi,status,payload_json,rebuilt_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", ("global", analyzed, settled, winrate_total, roi_total, round(profit, 3), clamp(avg_calibration), clamp(avg_market), sqi, status, json_dumps(payload), now))
    conn.commit()
    summary = shark_accuracy_summary(db_path, auto_rebuild=False)
    conn.close()
    return {"ok": True, "version": "V600", "processed": analyzed, "settled": settled, "summary": summary}


def shark_accuracy_summary(db_path: str, auto_rebuild: bool = True) -> Dict[str, Any]:
    ensure_shark_accuracy_schema(db_path)
    conn = connect(db_path)
    profile = one(conn, "SELECT * FROM shark_accuracy_profiles WHERE id='global'")
    if not profile and auto_rebuild:
        conn.close()
        return rebuild_shark_accuracy_engine(db_path, limit=1200).get("summary", {})
    payload = {}
    try:
        payload = json.loads(profile.get("payload_json") or "{}") if profile else {}
    except Exception:
        payload = {}
    summary = {
        "status": profile.get("status", "sin datos") if profile else "sin datos",
        "picks_analyzed": as_int(profile.get("picks_analyzed") if profile else 0),
        "settled_picks": as_int(profile.get("settled_picks") if profile else 0),
        "winrate": as_float(profile.get("winrate") if profile else 0),
        "roi": as_float(profile.get("roi") if profile else 0),
        "profit_units": as_float(profile.get("profit_units") if profile else 0),
        "calibration_score": as_int(profile.get("calibration_score") if profile else 0),
        "market_score": as_int(profile.get("market_score") if profile else 0),
        "sqi": as_int(profile.get("sqi") if profile else 0),
        "top_markets": rows(conn, "SELECT * FROM shark_accuracy_market_rankings ORDER BY accuracy_score DESC, sample_size DESC LIMIT 8"),
        "calibration": rows(conn, "SELECT * FROM shark_accuracy_calibration ORDER BY bucket DESC"),
        "latest_predictions": rows(conn, "SELECT * FROM shark_accuracy_predictions ORDER BY evaluated_at DESC LIMIT 8"),
        "note": payload.get("note") or "Mide si la confianza SHARK se corresponde con la realidad y qué mercados conviene priorizar.",
        "rebuilt_at": profile.get("rebuilt_at") if profile else None,
    }
    conn.close()
    return summary


def apply_accuracy_adjustment(item: Dict[str, Any], db_path: str) -> Dict[str, Any]:
    """Añade lectura de precisión sin romper el item original."""
    payload = dict(item or {})
    ensure_shark_accuracy_schema(db_path)
    conn = connect(db_path)
    market = str(payload.get("market") or payload.get("market_name") or "General")[:80]
    ranking = one(conn, "SELECT * FROM shark_accuracy_market_rankings WHERE market=?", (market,))
    calibration = one(conn, "SELECT * FROM shark_accuracy_calibration WHERE bucket=?", (confidence_bucket(prediction_score(payload)),))
    adjustment = 0
    reasons = []
    if ranking:
        score = as_int(ranking.get("accuracy_score"), 70)
        if score >= 82:
            adjustment += 4; reasons.append("Mercado históricamente excelente para SHARK.")
        elif score >= 72:
            adjustment += 2; reasons.append("Mercado con comportamiento histórico favorable.")
        elif score < 55:
            adjustment -= 5; reasons.append("Mercado con bajo rendimiento histórico.")
    if calibration:
        gap = as_float(calibration.get("calibration_gap"), 0)
        if gap < -10:
            adjustment -= 3; reasons.append("Calibración histórica recomienda prudencia.")
        elif gap > 10:
            adjustment += 2; reasons.append("SHARK ha sido conservador en este rango de confianza.")
    base = prediction_score(payload)
    payload["accuracy_adjustment"] = adjustment
    payload["accuracy_confidence"] = clamp(base + adjustment, 1, 100)
    payload["accuracy_reasons"] = reasons or ["Histórico de precisión todavía en construcción."]
    conn.close()
    return payload
