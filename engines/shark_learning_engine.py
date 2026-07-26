"""SHARK Learning Engine for NeMeSiS SHARK PRO.

V585 builds a safe learning layer from historical pick performance. It only
creates and updates its own SQLite tables, then returns confidence adjustments
that the app can apply to picks/recommendations without changing core flows.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable


MIN_SAMPLE = 5


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


def normalize_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"won", "win", "ganado", "green", "acertado"}:
        return "won"
    if text in {"lost", "loss", "perdido", "red", "fallado"}:
        return "lost"
    if text in {"void", "push", "nulo", "cancelled", "cancelado"}:
        return "void"
    return "pending"


def odds_range(odds: Any) -> str:
    price = as_float(odds, 0.0)
    if price <= 0:
        return "sin-cuota"
    if price < 1.50:
        return "1.01-1.49"
    if price < 1.90:
        return "1.50-1.89"
    if price < 2.50:
        return "1.90-2.49"
    if price < 3.50:
        return "2.50-3.49"
    return "3.50+"


def score_range(score: Any) -> str:
    value = as_int(score, 0)
    if value >= 85:
        return "85-100"
    if value >= 70:
        return "70-84"
    if value >= 55:
        return "55-69"
    return "0-54"


def ensure_shark_learning_schema(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS shark_learning_profiles(
        id TEXT PRIMARY KEY,
        profile_key TEXT,
        sample_size INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        voids INTEGER DEFAULT 0,
        pending INTEGER DEFAULT 0,
        winrate REAL DEFAULT 0,
        roi REAL DEFAULT 0,
        yield_pct REAL DEFAULT 0,
        reliability_score INTEGER DEFAULT 0,
        confidence_adjustment INTEGER DEFAULT 0,
        favorable_patterns TEXT,
        unfavorable_patterns TEXT,
        payload_json TEXT,
        rebuilt_at TEXT
    )""")
    for table, key_col in [
        ("shark_learning_market_stats", "market"),
        ("shark_learning_league_stats", "league_name"),
        ("shark_learning_odds_ranges", "odds_range"),
    ]:
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {table}(
            id TEXT PRIMARY KEY,
            {key_col} TEXT,
            sample_size INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            voids INTEGER DEFAULT 0,
            pending INTEGER DEFAULT 0,
            winrate REAL DEFAULT 0,
            roi REAL DEFAULT 0,
            yield_pct REAL DEFAULT 0,
            reliability_score INTEGER DEFAULT 0,
            confidence_adjustment INTEGER DEFAULT 0,
            pattern_label TEXT,
            explanation TEXT,
            payload_json TEXT,
            rebuilt_at TEXT
        )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shark_learning_market ON shark_learning_market_stats(market)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shark_learning_league ON shark_learning_league_stats(league_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shark_learning_odds ON shark_learning_odds_ranges(odds_range)")
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "shark_learning_v585"}


def _profit(row: Dict[str, Any]) -> float:
    status = normalize_status(row.get("result_status") or row.get("status"))
    if status == "void":
        return 0.0
    existing = as_float(row.get("profit"), 0.0)
    if existing:
        return round(existing, 2)
    stake = as_float(row.get("stake"), as_float(row.get("stake_units"), 1.0))
    odds = as_float(row.get("odds"), 0.0)
    if status == "won" and odds > 1:
        return round((odds - 1) * stake, 2)
    if status == "lost":
        return round(-stake, 2)
    return 0.0


def _load_pick_rows(conn: sqlite3.Connection, limit: int) -> list[Dict[str, Any]]:
    warehouse = rows(conn, """SELECT pick_id, match_id, match_date, league_name, home_team, away_team, selection, market, odds, confidence, stake, status, result_status, profit, payload_json, snapshot_at
                              FROM warehouse_pick_facts ORDER BY COALESCE(updated_at,snapshot_at,'') DESC LIMIT ?""", (int(limit),))
    if warehouse:
        return warehouse
    historical_raw = rows(conn, "SELECT * FROM historical_picks LIMIT ?", (int(limit),))
    if historical_raw:
        historical = []
        for item in historical_raw:
            historical.append(
                {
                    "pick_id": item.get("pick_id") or item.get("id"),
                    "match_id": item.get("match_id"),
                    "match_date": item.get("match_date") or item.get("event_date"),
                    "league_name": item.get("league_name") or item.get("competition_name"),
                    "home_team": item.get("home_team") or "",
                    "away_team": item.get("away_team") or "",
                    "selection": item.get("selection"),
                    "market": item.get("market") or item.get("pick_type"),
                    "odds": item.get("odds") or item.get("odds_value"),
                    "confidence": item.get("confidence") or item.get("shark_score"),
                    "stake": item.get("stake") or item.get("stake_units"),
                    "status": item.get("status"),
                    "result_status": item.get("result_status") or item.get("outcome"),
                    "profit": item.get("profit") or item.get("profit_units") or item.get("benefit_units"),
                    "payload_json": item.get("payload_json") or item.get("raw_json") or "",
                    "snapshot_at": item.get("updated_at") or item.get("created_at") or item.get("snapshot_at"),
                }
            )
        return historical
    return rows(conn, """SELECT id AS pick_id, match_id, match_date, competition_name AS league_name, home_team, away_team, selection,
                                COALESCE(market,pick_type) AS market, odds, confidence, stake_units AS stake, status, result_status, 0 AS profit, raw_json AS payload_json, updated_at AS snapshot_at
                         FROM picks ORDER BY COALESCE(updated_at,created_at,'') DESC LIMIT ?""", (int(limit),))


def _stats(items: list[Dict[str, Any]]) -> Dict[str, Any]:
    sample = len(items)
    wins = losses = voids = pending = 0
    stake_total = profit_total = 0.0
    for item in items:
        status = normalize_status(item.get("result_status") or item.get("status"))
        wins += 1 if status == "won" else 0
        losses += 1 if status == "lost" else 0
        voids += 1 if status == "void" else 0
        pending += 1 if status == "pending" else 0
        stake_total += as_float(item.get("stake"), 1.0)
        profit_total += _profit(item)
    settled = wins + losses
    winrate = round((wins / settled) * 100, 2) if settled else 0.0
    roi = round((profit_total / stake_total) * 100, 2) if stake_total else 0.0
    yield_pct = roi
    sample_score = min(35, sample * 4)
    roi_score = max(-20, min(25, roi / 2))
    win_score = max(-20, min(25, winrate - 50)) if settled else 0
    reliability = int(max(0, min(100, 35 + sample_score + roi_score + win_score)))
    if sample < MIN_SAMPLE or settled < 3:
        adjustment = 0
        pattern = "histórico insuficiente"
        explanation = "Histórico insuficiente: confianza sin ajuste avanzado."
    elif roi >= 12 and winrate >= 50:
        adjustment = min(8, max(2, int(round(roi / 8))))
        pattern = "favorable"
        explanation = "Patrón favorable detectado."
    elif roi <= -10 or winrate < 42:
        adjustment = max(-8, min(-2, int(round(roi / 8))))
        pattern = "desfavorable"
        explanation = "Patrón desfavorable detectado."
    else:
        adjustment = 0
        pattern = "neutral"
        explanation = "Histórico estable: confianza sin cambio fuerte."
    return {
        "sample_size": sample,
        "wins": wins,
        "losses": losses,
        "voids": voids,
        "pending": pending,
        "winrate": winrate,
        "roi": roi,
        "yield_pct": yield_pct,
        "reliability_score": reliability,
        "confidence_adjustment": adjustment,
        "pattern_label": pattern,
        "explanation": explanation,
        "stake_total": round(stake_total, 2),
        "profit_total": round(profit_total, 2),
        "settled": settled,
    }


def _insert_stat(cur: sqlite3.Cursor, table: str, key_col: str, key_value: str, items: list[Dict[str, Any]], rebuilt_at: str) -> Dict[str, Any]:
    stats = _stats(items)
    row_id = stable_id("sl", table, key_value)
    cur.execute(
        f"""INSERT OR REPLACE INTO {table}
           (id,{key_col},sample_size,wins,losses,voids,pending,winrate,roi,yield_pct,reliability_score,confidence_adjustment,pattern_label,explanation,payload_json,rebuilt_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            row_id,
            key_value,
            stats["sample_size"],
            stats["wins"],
            stats["losses"],
            stats["voids"],
            stats["pending"],
            stats["winrate"],
            stats["roi"],
            stats["yield_pct"],
            stats["reliability_score"],
            stats["confidence_adjustment"],
            stats["pattern_label"],
            stats["explanation"],
            json_dumps(stats),
            rebuilt_at,
        ),
    )
    return stats


def rebuild_shark_learning_engine(db_path: str, limit: int = 1000) -> Dict[str, Any]:
    ensure_shark_learning_schema(db_path)
    started = utc_now()
    conn = connect(db_path)
    cur = conn.cursor()
    picks = _load_pick_rows(conn, limit)
    cur.execute("DELETE FROM shark_learning_profiles")
    cur.execute("DELETE FROM shark_learning_market_stats")
    cur.execute("DELETE FROM shark_learning_league_stats")
    cur.execute("DELETE FROM shark_learning_odds_ranges")

    market_groups: dict[str, list[Dict[str, Any]]] = {}
    league_groups: dict[str, list[Dict[str, Any]]] = {}
    odds_groups: dict[str, list[Dict[str, Any]]] = {}
    score_groups: dict[str, list[Dict[str, Any]]] = {}
    for pick in picks:
        market_groups.setdefault(str(pick.get("market") or "Principal"), []).append(pick)
        league_groups.setdefault(str(pick.get("league_name") or "Sin liga"), []).append(pick)
        odds_groups.setdefault(odds_range(pick.get("odds")), []).append(pick)
        score_groups.setdefault(score_range(pick.get("confidence")), []).append(pick)

    built = {"markets": 0, "leagues": 0, "odds_ranges": 0, "score_ranges": 0}
    favorable = []
    unfavorable = []
    for key, items in market_groups.items():
        stat = _insert_stat(cur, "shark_learning_market_stats", "market", key, items, started)
        built["markets"] += 1
        if stat["pattern_label"] == "favorable":
            favorable.append(f"Mercado {key}")
        if stat["pattern_label"] == "desfavorable":
            unfavorable.append(f"Mercado {key}")
    for key, items in league_groups.items():
        stat = _insert_stat(cur, "shark_learning_league_stats", "league_name", key, items, started)
        built["leagues"] += 1
        if stat["pattern_label"] == "favorable":
            favorable.append(f"Liga {key}")
        if stat["pattern_label"] == "desfavorable":
            unfavorable.append(f"Liga {key}")
    for key, items in odds_groups.items():
        stat = _insert_stat(cur, "shark_learning_odds_ranges", "odds_range", key, items, started)
        built["odds_ranges"] += 1
        if stat["pattern_label"] == "favorable":
            favorable.append(f"Cuotas {key}")
        if stat["pattern_label"] == "desfavorable":
            unfavorable.append(f"Cuotas {key}")

    profile_stats = _stats(picks)
    profile_payload = {"built": built, "score_ranges": {k: _stats(v) for k, v in score_groups.items()}}
    cur.execute("""INSERT OR REPLACE INTO shark_learning_profiles
        (id,profile_key,sample_size,wins,losses,voids,pending,winrate,roi,yield_pct,reliability_score,confidence_adjustment,favorable_patterns,unfavorable_patterns,payload_json,rebuilt_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "global",
            "global",
            profile_stats["sample_size"],
            profile_stats["wins"],
            profile_stats["losses"],
            profile_stats["voids"],
            profile_stats["pending"],
            profile_stats["winrate"],
            profile_stats["roi"],
            profile_stats["yield_pct"],
            profile_stats["reliability_score"],
            profile_stats["confidence_adjustment"],
            json_dumps(favorable[:20]),
            json_dumps(unfavorable[:20]),
            json_dumps(profile_payload),
            started,
        ))
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "shark_learning_v585", "picks_read": len(picks), "built": built, "global": profile_stats, "favorable_patterns": favorable[:20], "unfavorable_patterns": unfavorable[:20]}


def build_shark_learning_profile(db_path: str, limit: int = 1000) -> Dict[str, Any]:
    ensure_shark_learning_schema(db_path)
    conn = connect(db_path)
    profile = one(conn, "SELECT * FROM shark_learning_profiles WHERE profile_key='global' LIMIT 1")
    if not profile:
        conn.close()
        rebuild_shark_learning_engine(db_path, limit=limit)
        return build_shark_learning_profile(db_path, limit=limit)
    market_best = rows(conn, "SELECT * FROM shark_learning_market_stats ORDER BY roi DESC, reliability_score DESC LIMIT 8")
    market_risk = rows(conn, "SELECT * FROM shark_learning_market_stats ORDER BY roi ASC, reliability_score DESC LIMIT 8")
    league_best = rows(conn, "SELECT * FROM shark_learning_league_stats ORDER BY roi DESC, reliability_score DESC LIMIT 8")
    league_risk = rows(conn, "SELECT * FROM shark_learning_league_stats ORDER BY roi ASC, reliability_score DESC LIMIT 8")
    odds = rows(conn, "SELECT * FROM shark_learning_odds_ranges ORDER BY odds_range")
    conn.close()
    return {
        "ok": True,
        "schema": "shark_learning_v585",
        "profile": profile,
        "market_best": market_best,
        "market_risk": market_risk,
        "league_best": league_best,
        "league_risk": league_risk,
        "best_markets": market_best,
        "risk_markets": market_risk,
        "best_leagues": league_best,
        "risk_leagues": league_risk,
        "odds_ranges": odds,
        "readiness_score": profile.get("reliability_score", 0),
        "status": "activo" if profile.get("sample_size", 0) >= MIN_SAMPLE else "histórico insuficiente",
    }


def _lookup(conn: sqlite3.Connection, table: str, key_col: str, value: Any) -> Dict[str, Any]:
    value = str(value or "").strip()
    if not value:
        return {}
    return one(conn, f"SELECT * FROM {table} WHERE lower({key_col})=lower(?) LIMIT 1", (value,))


def apply_shark_learning_adjustment(pick_or_recommendation: Dict[str, Any], db_path: str | None = None) -> Dict[str, Any]:
    item = dict(pick_or_recommendation or {})
    base_confidence = as_int(item.get("confidence") or item.get("score") or item.get("shark_score"), 50)
    db_path = db_path or os.getenv("DB_PATH", "/data/database.db")
    ensure_shark_learning_schema(db_path)
    conn = connect(db_path)
    signals = []
    total_adjustment = 0
    lookups = [
        ("market", _lookup(conn, "shark_learning_market_stats", "market", item.get("market") or item.get("pick_type"))),
        ("league", _lookup(conn, "shark_learning_league_stats", "league_name", item.get("league_name") or item.get("competition_name"))),
        ("odds_range", _lookup(conn, "shark_learning_odds_ranges", "odds_range", odds_range(item.get("odds") or item.get("odds_value")))),
    ]
    for label, stat in lookups:
        if not stat:
            continue
        sample = as_int(stat.get("sample_size"), 0)
        adjustment = as_int(stat.get("confidence_adjustment"), 0)
        if sample < MIN_SAMPLE:
            signals.append({"type": label, "adjustment": 0, "message": "Histórico insuficiente: confianza sin ajuste avanzado.", "stat": stat})
            continue
        total_adjustment += adjustment
        if adjustment > 0:
            msg = "SHARK aumenta la confianza por buen rendimiento histórico en este mercado." if label == "market" else "Patrón favorable detectado."
        elif adjustment < 0:
            msg = "SHARK reduce la confianza por baja fiabilidad reciente en esta liga." if label == "league" else "Patrón desfavorable detectado."
        else:
            msg = stat.get("explanation") or "Histórico estable: confianza sin cambio fuerte."
        signals.append({"type": label, "adjustment": adjustment, "message": msg, "stat": stat})
    conn.close()
    total_adjustment = max(-12, min(12, total_adjustment))
    adjusted = max(1, min(100, base_confidence + total_adjustment))
    if not signals:
        signals = [{"type": "global", "adjustment": 0, "message": "Histórico insuficiente: confianza sin ajuste avanzado.", "stat": {}}]
    item["confidence_original"] = base_confidence
    item["confidence"] = adjusted
    item["shark_score"] = adjusted
    item["score"] = adjusted
    item["learning_adjustment"] = total_adjustment
    item["learning_signals"] = signals
    item["learning_explanation"] = " ".join(dict.fromkeys(signal["message"] for signal in signals))
    return item


# V939 governance layer. The legacy V585 functions above remain available for
# compatibility, but this path is deliberately read-only and never applies a
# recommendation to production weights.
V939_MIN_GLOBAL_SAMPLE = 30
V939_MIN_SEGMENT_SAMPLE = 20
V939_ALLOWED_DEFAULT_LEVELS = ("OBSERVE", "RECOMMEND")


def _v939_first(item: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if item.get(key) not in (None, ""):
            return item.get(key)
    return None


def _v939_closed_rows(db_path: str, limit: int = 5000) -> list[Dict[str, Any]]:
    from engines.company_intelligence_engine import readonly_connection, safe_rows

    conn = readonly_connection(db_path)
    if conn is None:
        return []
    try:
        source = safe_rows(conn, "historical_picks", limit)
        if not source:
            source = safe_rows(conn, "picks", limit)
    finally:
        conn.close()
    closed = []
    for row in source:
        status = normalize_status(_v939_first(row, "result_status", "outcome", "status"))
        if status not in {"won", "lost", "void"}:
            continue
        odds = as_float(_v939_first(row, "odds", "odds_value", "price"), 0.0)
        stake = as_float(_v939_first(row, "stake", "stake_units"), 0.0)
        explicit_profit = _v939_first(row, "profit", "profit_units", "benefit_units")
        profit_value = as_float(explicit_profit, 0.0) if explicit_profit not in (None, "") else None
        closed.append({
            "pick_id": str(_v939_first(row, "pick_id", "id") or ""),
            "match_id": str(_v939_first(row, "match_id", "fixture_id") or ""),
            "competition": str(_v939_first(row, "competition_name", "league_name", "competition") or "unclassified"),
            "market": str(_v939_first(row, "market", "pick_type", "market_name") or "unclassified"),
            "selection": str(_v939_first(row, "selection", "tip") or ""),
            "odds": odds if odds > 1.0 else None,
            "closing_odds": as_float(_v939_first(row, "closing_odds", "close_odds"), 0.0) or None,
            "stake": stake if stake > 0 else None,
            "risk": str(_v939_first(row, "risk", "risk_level") or "unclassified"),
            "confidence": as_float(_v939_first(row, "confidence", "shark_score", "score"), 0.0) or None,
            "estimated_value": as_float(_v939_first(row, "value", "estimated_value", "expected_value"), 0.0) or None,
            "result": status,
            "profit": profit_value,
            "profit_certified": profit_value is not None,
            "reason": str(_v939_first(row, "reason", "reasoning", "rationale") or "")[:1000],
            "risks": str(_v939_first(row, "risks", "risk_notes", "counterargument") or "")[:1000],
            "sent_at": str(_v939_first(row, "sent_at", "published_at", "created_at") or ""),
            "kickoff_at": str(_v939_first(row, "kickoff_at", "match_date", "event_date") or ""),
            "provider": str(_v939_first(row, "provider", "source", "data_source") or "unclassified"),
            "membership": str(_v939_first(row, "membership", "membership_required", "audience") or "unclassified"),
            "telegram_format": str(_v939_first(row, "telegram_format", "message_format") or "unclassified"),
            "engine_version": str(_v939_first(row, "engine_version", "version", "app_version") or "unknown"),
        })
    return closed


def _v939_segment_key(item: Dict[str, Any], dimension: str) -> str:
    if dimension == "odds_range":
        return odds_range(item.get("odds"))
    if dimension == "stake_range":
        stake = as_float(item.get("stake"), 0.0)
        if stake <= 0:
            return "unclassified"
        if stake <= 1:
            return "0-1"
        if stake <= 2:
            return "1-2"
        return "2+"
    if dimension == "hour":
        text = str(item.get("sent_at") or "")
        try:
            return f"{datetime.fromisoformat(text.replace('Z', '+00:00')).hour:02d}:00"
        except (TypeError, ValueError):
            return "unclassified"
    return str(item.get(dimension) or "unclassified")


def _v939_observed_stats(items: list[Dict[str, Any]], minimum_sample: int) -> Dict[str, Any]:
    wins = sum(1 for item in items if item.get("result") == "won")
    losses = sum(1 for item in items if item.get("result") == "lost")
    voids = sum(1 for item in items if item.get("result") == "void")
    evaluable = wins + losses
    profit_rows = [item for item in items if item.get("profit_certified") and item.get("stake")]
    stake_total = sum(float(item["stake"]) for item in profit_rows)
    profit_total = sum(float(item["profit"]) for item in profit_rows)
    sufficient = evaluable >= minimum_sample
    return {
        "sample_size": len(items),
        "evaluable": evaluable,
        "wins": wins,
        "losses": losses,
        "voids": voids,
        "winrate": round((wins / evaluable) * 100, 2) if sufficient and evaluable else None,
        "roi": round((profit_total / stake_total) * 100, 2) if sufficient and len(profit_rows) >= minimum_sample and stake_total > 0 else None,
        "profit_sample_size": len(profit_rows),
        "sample_state": "PARTIALLY_VERIFIED" if sufficient else "INSUFFICIENT_DATA",
        "minimum_sample": minimum_sample,
        "metrics_not_available_are_null": True,
    }


def _v939_grouped_performance(rows: list[Dict[str, Any]], dimension: str) -> list[Dict[str, Any]]:
    groups: dict[str, list[Dict[str, Any]]] = {}
    for item in rows:
        groups.setdefault(_v939_segment_key(item, dimension), []).append(item)
    return [
        {"segment": key, **_v939_observed_stats(items, V939_MIN_SEGMENT_SAMPLE)}
        for key, items in sorted(groups.items())
    ]


def _v939_calibration(rows: list[Dict[str, Any]]) -> dict[str, Any]:
    with_confidence = [item for item in rows if item.get("confidence") is not None and item.get("result") in {"won", "lost"}]
    if len(with_confidence) < V939_MIN_GLOBAL_SAMPLE:
        return {
            "state": "INSUFFICIENT_DATA",
            "sample_size": len(with_confidence),
            "minimum_sample": V939_MIN_GLOBAL_SAMPLE,
            "confidence_bias": None,
        }
    expected = sum(float(item["confidence"]) for item in with_confidence) / len(with_confidence)
    observed = sum(1 for item in with_confidence if item.get("result") == "won") / len(with_confidence) * 100.0
    return {
        "state": "PARTIALLY_VERIFIED",
        "sample_size": len(with_confidence),
        "average_recorded_confidence": round(expected, 2),
        "observed_winrate": round(observed, 2),
        "confidence_bias": round(expected - observed, 2),
        "not_a_causal_claim": True,
    }


def build_v939_shark_learning_snapshot(
    db_path: str,
    app_version: str,
    *,
    limit: int = 5000,
    minimum_global_sample: int = V939_MIN_GLOBAL_SAMPLE,
) -> Dict[str, Any]:
    closed = _v939_closed_rows(db_path, limit)
    global_stats = _v939_observed_stats(closed, minimum_global_sample)
    state = global_stats["sample_state"]
    dimensions = ("market", "competition", "odds_range", "risk", "stake_range", "hour", "provider")
    performance = {dimension: _v939_grouped_performance(closed, dimension) for dimension in dimensions}
    calibration = _v939_calibration(closed)
    recommendations: list[dict[str, Any]] = []
    if state != "INSUFFICIENT_DATA":
        for dimension, segments in performance.items():
            for segment in segments:
                if segment.get("sample_state") != "PARTIALLY_VERIFIED" or segment.get("roi") is None:
                    continue
                if abs(float(segment["roi"])) < 10:
                    continue
                recommendations.append({
                    "recommendation_id": stable_id("v939", dimension, segment.get("segment")),
                    "level": "RECOMMEND",
                    "dimension": dimension,
                    "segment": segment.get("segment"),
                    "observation": "Rendimiento observado por encima del umbral." if float(segment["roi"]) > 0 else "Rendimiento observado por debajo del umbral.",
                    "evidence": segment,
                    "proposed_weight_change": None,
                    "requires_explicit_approval": True,
                })
    return {
        "ok": True,
        "version": app_version,
        "mode": "OBSERVE",
        "allowed_default_levels": list(V939_ALLOWED_DEFAULT_LEVELS),
        "approved_change_available_only_after_explicit_approval": True,
        "automatic_weight_changes": False,
        "database_written": False,
        "external_calls": 0,
        "certification_state": state,
        "global": global_stats,
        "performance": performance,
        "calibration": calibration,
        "recommendations": recommendations,
        "winning_patterns": [item for item in recommendations if "encima" in item.get("observation", "")],
        "losing_patterns": [item for item in recommendations if "debajo" in item.get("observation", "")],
        "limitations": [
            "Asociacion historica no implica causalidad ni garantiza resultados futuros.",
            "ROI solo aparece cuando beneficio y stake reales alcanzan la muestra minima.",
            "Ninguna recomendacion modifica pesos, picks, Telegram o produccion.",
        ],
    }
