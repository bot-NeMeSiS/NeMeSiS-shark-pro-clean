"""Memoria deportiva persistente para NeMeSiS SHARK PRO.

Este módulo guarda histórico normalizado de sincronizaciones, partidos,
cuotas, live, picks, descartes y Telegram sin bloquear el flujo principal.
No almacena secrets ni tokens y recorta JSON para evitar crecimiento excesivo.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Mapping

TZ = ZoneInfo("Europe/Madrid")
MAX_JSON_CHARS = int(os.getenv("DATA_MEMORY_MAX_JSON_CHARS", "6000"))


def _now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _enabled() -> bool:
    return str(os.getenv("DATA_MEMORY_ENABLED", "true")).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _safe_json(value: Any, limit: int = MAX_JSON_CHARS) -> str:
    try:
        text = json.dumps(_scrub(value), ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        text = json.dumps({"repr": str(value)[:1000]}, ensure_ascii=False)
    return text[: int(limit)]


def _hash(value: Any) -> str:
    return hashlib.sha256(_safe_json(value, limit=20000).encode("utf-8", errors="ignore")).hexdigest()[:24]


def _scrub(value: Any) -> Any:
    """Elimina claves sensibles antes de persistir metadatos."""
    if isinstance(value, Mapping):
        out = {}
        for key, item in value.items():
            lk = str(key).lower()
            if any(s in lk for s in ("secret", "token", "api_key", "apikey", "password", "chat_id", "authorization")):
                out[key] = "***hidden***"
            else:
                out[key] = _scrub(item)
        return out
    if isinstance(value, list):
        return [_scrub(v) for v in value[:200]]
    if isinstance(value, tuple):
        return tuple(_scrub(v) for v in value[:200])
    return value


def _conn(db_or_conn: str | sqlite3.Connection) -> tuple[sqlite3.Connection, bool]:
    if isinstance(db_or_conn, sqlite3.Connection):
        return db_or_conn, False
    conn = sqlite3.connect(db_or_conn)
    conn.row_factory = sqlite3.Row
    return conn, True


def ensure_data_memory_schema(db_or_conn: str | sqlite3.Connection) -> None:
    conn, should_close = _conn(db_or_conn)
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS data_memory_errors(
            id TEXT PRIMARY KEY,
            created_at TEXT,
            context TEXT,
            error_summary TEXT,
            payload_json TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS api_sync_runs(
            id TEXT PRIMARY KEY,
            source TEXT,
            started_at TEXT,
            finished_at TEXT,
            status TEXT,
            matches_count INTEGER DEFAULT 0,
            odds_count INTEGER DEFAULT 0,
            picks_count INTEGER DEFAULT 0,
            sent_count INTEGER DEFAULT 0,
            error_summary TEXT,
            meta_json TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS match_snapshots(
            id TEXT PRIMARY KEY,
            match_id TEXT,
            source TEXT,
            captured_at TEXT,
            competition TEXT,
            home_team TEXT,
            away_team TEXT,
            kickoff_iso TEXT,
            status TEXT,
            home_score TEXT,
            away_score TEXT,
            raw_hash TEXT,
            normalized_json TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS odds_memory_snapshots(
            id TEXT PRIMARY KEY,
            match_id TEXT,
            source TEXT,
            bookmaker TEXT,
            market TEXT,
            selection TEXT,
            price REAL,
            captured_at TEXT,
            raw_hash TEXT,
            meta_json TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS live_memory_snapshots(
            id TEXT PRIMARY KEY,
            match_id TEXT,
            source TEXT,
            captured_at TEXT,
            minute TEXT,
            status TEXT,
            home_score TEXT,
            away_score TEXT,
            momentum_home TEXT,
            momentum_away TEXT,
            risk_level TEXT,
            normalized_json TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS pick_decisions(
            id TEXT PRIMARY KEY,
            pick_id TEXT,
            match_id TEXT,
            created_at TEXT,
            decision TEXT,
            selection TEXT,
            market TEXT,
            odds REAL,
            shark_score INTEGER,
            confidence INTEGER,
            risk TEXT,
            stake REAL,
            reason TEXT,
            caution TEXT,
            sent_to_telegram INTEGER DEFAULT 0,
            result_status TEXT,
            meta_json TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS pick_discards(
            id TEXT PRIMARY KEY,
            match_id TEXT,
            created_at TEXT,
            reason TEXT,
            market TEXT,
            selection TEXT,
            odds REAL,
            shark_score INTEGER,
            source TEXT,
            meta_json TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS telegram_delivery_memory(
            id TEXT PRIMARY KEY,
            created_at TEXT,
            message_type TEXT,
            target_type TEXT,
            status TEXT,
            match_id TEXT,
            pick_id TEXT,
            error_summary TEXT,
            dedupe_key TEXT,
            meta_json TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS team_identity_cache(
            id TEXT PRIMARY KEY,
            team_name TEXT,
            canonical_name TEXT,
            country TEXT,
            logo_url TEXT,
            badge_url TEXT,
            source TEXT,
            updated_at TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS data_memory_retention_runs(
            id TEXT PRIMARY KEY,
            created_at TEXT,
            keep_days INTEGER,
            deleted_rows INTEGER DEFAULT 0,
            meta_json TEXT
        )""")
        for idx in (
            "CREATE INDEX IF NOT EXISTS idx_api_sync_runs_source_time ON api_sync_runs(source, started_at)",
            "CREATE INDEX IF NOT EXISTS idx_match_snapshots_match_time ON match_snapshots(match_id, captured_at)",
            "CREATE INDEX IF NOT EXISTS idx_match_snapshots_source_time ON match_snapshots(source, captured_at)",
            "CREATE INDEX IF NOT EXISTS idx_odds_memory_match_time ON odds_memory_snapshots(match_id, captured_at)",
            "CREATE INDEX IF NOT EXISTS idx_live_memory_match_time ON live_memory_snapshots(match_id, captured_at)",
            "CREATE INDEX IF NOT EXISTS idx_pick_decisions_match_time ON pick_decisions(match_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_pick_discards_reason_time ON pick_discards(reason, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_telegram_memory_dedupe ON telegram_delivery_memory(dedupe_key, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_team_identity_cache_name ON team_identity_cache(team_name, canonical_name)",
        ):
            cur.execute(idx)
        conn.commit()
    finally:
        if should_close:
            conn.close()


def _record_error(db_path: str, context: str, exc: Exception, payload: Any = None) -> None:
    try:
        ensure_data_memory_schema(db_path)
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        eid = hashlib.md5(f"memerr-{context}-{_now()}-{exc}".encode()).hexdigest()[:18]
        cur.execute(
            "INSERT OR REPLACE INTO data_memory_errors(id,created_at,context,error_summary,payload_json) VALUES (?,?,?,?,?)",
            (eid, _now(), context, str(exc)[:500], _safe_json(payload, 2000)),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def safe_memory_call(db_path: str, context: str, fn, *args, **kwargs) -> dict[str, Any]:
    if not _enabled():
        return {"ok": True, "enabled": False, "skipped": True}
    try:
        ensure_data_memory_schema(db_path)
        return fn(db_path, *args, **kwargs) or {"ok": True}
    except Exception as exc:  # nunca debe romper app
        _record_error(db_path, context, exc, {"args": args, "kwargs": kwargs})
        return {"ok": False, "error": str(exc)[:300], "context": context}


def record_api_sync_run(db_path: str, source: str, status: str, counts: Mapping[str, Any] | None = None, error: str | None = None, meta: Any = None) -> dict[str, Any]:
    counts = counts or {}
    now = _now()
    run_id = hashlib.md5(f"sync-{source}-{now}".encode()).hexdigest()[:18]
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO api_sync_runs
           (id,source,started_at,finished_at,status,matches_count,odds_count,picks_count,sent_count,error_summary,meta_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            run_id,
            str(source or "unknown")[:80],
            counts.get("started_at") or now,
            counts.get("finished_at") or now,
            str(status or "UNKNOWN")[:60],
            int(counts.get("matches") or counts.get("matches_synced") or 0),
            int(counts.get("odds") or counts.get("odds_count") or 0),
            int(counts.get("picks") or counts.get("picks_generated") or 0),
            int(counts.get("sent") or counts.get("picks_sent") or 0),
            str(error or "")[:500],
            _safe_json(meta or counts, 4000),
        ),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "run_id": run_id}


def remember_match_snapshot(db_path: str, match: Mapping[str, Any], source: str = "app") -> dict[str, Any]:
    now = _now()
    match_id = str(match.get("id") or match.get("match_id") or _hash(match))[:80]
    sid = hashlib.md5(f"match-{match_id}-{source}-{now}".encode()).hexdigest()[:18]
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO match_snapshots
           (id,match_id,source,captured_at,competition,home_team,away_team,kickoff_iso,status,home_score,away_score,raw_hash,normalized_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            sid,
            match_id,
            str(source)[:80],
            now,
            str(match.get("safe_competition") or match.get("competition_name") or match.get("league_name") or "")[:160],
            str(match.get("safe_home") or match.get("home_team") or "")[:160],
            str(match.get("safe_away") or match.get("away_team") or "")[:160],
            str(match.get("kickoff_iso") or "")[:80],
            str(match.get("status") or "")[:60],
            str(match.get("home_score") or "")[:20],
            str(match.get("away_score") or "")[:20],
            _hash(match),
            _safe_json(match),
        ),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "snapshot_id": sid}


def remember_pick_decision(db_path: str, pick: Mapping[str, Any], decision: str = "premium", reason: str = "") -> dict[str, Any]:
    now = _now()
    pick_id = str(pick.get("id") or _hash(pick))[:80]
    did = hashlib.md5(f"pickdec-{pick_id}-{decision}-{now}".encode()).hexdigest()[:18]
    odds = pick.get("odds") or pick.get("price") or 0
    try:
        odds = float(odds or 0)
    except Exception:
        odds = 0.0
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO pick_decisions
           (id,pick_id,match_id,created_at,decision,selection,market,odds,shark_score,confidence,risk,stake,reason,caution,sent_to_telegram,result_status,meta_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            did,
            pick_id,
            str(pick.get("match_id") or "")[:80],
            now,
            str(decision or "premium")[:60],
            str(pick.get("safe_selection") or pick.get("selection") or "")[:160],
            str(pick.get("safe_market") or pick.get("market") or pick.get("pick_type") or "")[:160],
            odds,
            int(pick.get("shark_score") or pick.get("quality_score") or pick.get("confidence") or 0),
            int(pick.get("confidence") or 0),
            str(pick.get("risk") or pick.get("risk_level") or "")[:60],
            float(pick.get("stake") or pick.get("stake_units") or 0),
            str(reason or pick.get("reasoning") or pick.get("motivo") or "")[:800],
            str(pick.get("caution") or pick.get("precaution") or pick.get("precaucion") or "")[:800],
            1 if pick.get("sent_to_telegram") else 0,
            str(pick.get("result_status") or pick.get("status") or "")[:80],
            _safe_json(pick),
        ),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "decision_id": did}


def remember_pick_discard(db_path: str, candidate: Mapping[str, Any], reason: str = "unknown") -> dict[str, Any]:
    now = _now()
    mid = str(candidate.get("match_id") or candidate.get("id") or "")[:80]
    did = hashlib.md5(f"discard-{mid}-{reason}-{_hash(candidate)}-{now}".encode()).hexdigest()[:18]
    odds = candidate.get("odds") or candidate.get("price") or 0
    try:
        odds = float(odds or 0)
    except Exception:
        odds = 0.0
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO pick_discards
           (id,match_id,created_at,reason,market,selection,odds,shark_score,source,meta_json)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            did,
            mid,
            now,
            str(reason or "unknown")[:100],
            str(candidate.get("safe_market") or candidate.get("market") or candidate.get("pick_type") or "")[:160],
            str(candidate.get("safe_selection") or candidate.get("selection") or "")[:160],
            odds,
            int(candidate.get("shark_score") or candidate.get("quality_score") or candidate.get("confidence") or 0),
            str(candidate.get("source") or "app")[:80],
            _safe_json(candidate),
        ),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "discard_id": did}


def remember_telegram_delivery(db_path: str, message_type: str, target: str, status: str, meta: Any = None) -> dict[str, Any]:
    now = _now()
    meta = meta or {}
    dedupe = ""
    if isinstance(meta, Mapping):
        dedupe = str(meta.get("dedupe_key") or meta.get("signature") or "")[:160]
    tid = hashlib.md5(f"tgmem-{message_type}-{status}-{dedupe}-{now}".encode()).hexdigest()[:18]
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO telegram_delivery_memory
           (id,created_at,message_type,target_type,status,match_id,pick_id,error_summary,dedupe_key,meta_json)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            tid,
            now,
            str(message_type or "unknown")[:80],
            "channel" if target else "unknown",
            str(status or "UNKNOWN")[:80],
            str(meta.get("match_id") if isinstance(meta, Mapping) else "")[:80],
            str(meta.get("pick_id") if isinstance(meta, Mapping) else "")[:80],
            str(meta.get("error") if isinstance(meta, Mapping) else "")[:500],
            dedupe,
            _safe_json({"target_configured": bool(target), "meta": meta}, 3000),
        ),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "telegram_memory_id": tid}


def remember_team_identity(db_path: str, team_name: str, logo_url: str = "", country: str = "", source: str = "app", badge_url: str = "", canonical_name: str = "") -> dict[str, Any]:
    if not team_name:
        return {"ok": False, "error": "team_name_required"}
    now = _now()
    canonical = canonical_name or team_name.strip().lower()
    tid = hashlib.md5(f"team-{canonical}".encode()).hexdigest()[:18]
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO team_identity_cache
           (id,team_name,canonical_name,country,logo_url,badge_url,source,updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (tid, team_name[:160], canonical[:160], country[:120], str(logo_url or "")[:500], str(badge_url or "")[:500], source[:80], now),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "team_identity_id": tid}


def data_memory_summary(db_path: str) -> dict[str, Any]:
    ensure_data_memory_schema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    def count(table: str, where: str = "1=1") -> int:
        try:
            return int(cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0])
        except Exception:
            return 0

    def latest(table: str, order_col: str, limit: int = 8):
        try:
            return [dict(r) for r in cur.execute(f"SELECT * FROM {table} ORDER BY {order_col} DESC LIMIT ?", (limit,)).fetchall()]
        except Exception:
            return []

    try:
        discards = [dict(r) for r in cur.execute("SELECT reason, COUNT(*) AS total FROM pick_discards GROUP BY reason ORDER BY total DESC LIMIT 8").fetchall()]
    except Exception:
        discards = []
    try:
        table_sizes = []
        for table in ("api_sync_runs", "match_snapshots", "odds_memory_snapshots", "live_memory_snapshots", "pick_decisions", "pick_discards", "telegram_delivery_memory", "team_identity_cache", "data_memory_errors"):
            table_sizes.append({"table": table, "rows": count(table)})
    except Exception:
        table_sizes = []
    summary = {
        "enabled": _enabled(),
        "retention": {
            "DATA_MEMORY_KEEP_DAYS": int(os.getenv("DATA_MEMORY_KEEP_DAYS", "180")),
            "ODDS_SNAPSHOT_KEEP_DAYS": int(os.getenv("ODDS_SNAPSHOT_KEEP_DAYS", "90")),
            "LIVE_SNAPSHOT_KEEP_DAYS": int(os.getenv("LIVE_SNAPSHOT_KEEP_DAYS", "30")),
            "TELEGRAM_LOG_KEEP_DAYS": int(os.getenv("TELEGRAM_LOG_KEEP_DAYS", "90")),
            "DATA_MEMORY_RAW_JSON": str(os.getenv("DATA_MEMORY_RAW_JSON", "false")).lower() in {"1", "true", "yes", "on"},
        },
        "counts": {item["table"]: item["rows"] for item in table_sizes},
        "table_sizes": table_sizes,
        "discard_reasons": discards,
        "latest_sync_runs": latest("api_sync_runs", "started_at"),
        "latest_pick_decisions": latest("pick_decisions", "created_at"),
        "latest_telegram": latest("telegram_delivery_memory", "created_at"),
        "latest_errors": latest("data_memory_errors", "created_at"),
        "policy": "Memoria interna normalizada para análisis SHARK. No almacena secrets ni tokens y no expone raw externo al cliente.",
    }
    conn.close()
    return summary


def cleanup_old_memory(db_path: str) -> dict[str, Any]:
    keep_days = int(os.getenv("DATA_MEMORY_KEEP_DAYS", "180"))
    cutoff = (datetime.now(TZ) - timedelta(days=keep_days)).isoformat(timespec="seconds")
    ensure_data_memory_schema(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    deleted = 0
    for table, col in (
        ("match_snapshots", "captured_at"),
        ("api_sync_runs", "started_at"),
        ("pick_decisions", "created_at"),
        ("pick_discards", "created_at"),
        ("telegram_delivery_memory", "created_at"),
        ("data_memory_errors", "created_at"),
    ):
        try:
            cur.execute(f"DELETE FROM {table} WHERE {col} < ?", (cutoff,))
            deleted += int(cur.rowcount or 0)
        except Exception:
            pass
    rid = hashlib.md5(f"retention-{_now()}".encode()).hexdigest()[:18]
    cur.execute(
        "INSERT OR REPLACE INTO data_memory_retention_runs(id,created_at,keep_days,deleted_rows,meta_json) VALUES (?,?,?,?,?)",
        (rid, _now(), keep_days, deleted, _safe_json({"cutoff": cutoff})),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "deleted_rows": deleted, "keep_days": keep_days, "cutoff": cutoff}
