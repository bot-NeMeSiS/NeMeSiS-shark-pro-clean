"""Read-only proof of the existing master Cron's persisted cycle.

This is NOT a 24/7 worker heartbeat for every configured role. An old or missing
receipt must stay visible as such. Never probes providers, writes, or reads secrets.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import sqlite3

RECEIPT_KEY = "telegram_tick_last_detail"
MAX_RECEIPT_BYTES = 65536
FRESH_MINUTES = 15


def master_cron_receipt(db_path, *, now=None):
    result = {
        "contract": "NEMESIS-COMPANY-WORKFORCE-RECEIPT-V1",
        "state": "NO_EVIDENCE",
        "source": RECEIPT_KEY,
        "last_observed_madrid": None,
        "age_minutes": None,
        "fresh_minutes": FRESH_MINUTES,
        "external_calls": 0,
        "database_writes": 0,
        "workers_certified_24x7": False,
        "description": "Solo acredita el último ciclo guardado por la web, no todos los trabajadores.",
    }
    if not db_path:
        return result
    try:
        path = Path(db_path).resolve()
        if not path.is_file():
            return result
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=.4)) as conn, conn:
            conn.execute("PRAGMA query_only=ON")
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                "AND name='automation_state'").fetchone():
                return result
            row = conn.execute(
                "SELECT value_json,updated_at FROM automation_state WHERE key=? LIMIT 1",
                (RECEIPT_KEY,),
            ).fetchone()
            if not row or not isinstance(row[0], str) or len(row[0].encode("utf-8")) > MAX_RECEIPT_BYTES:
                return result
            raw = json.loads(row[0])
            if not isinstance(raw, dict):
                return result
            observed = raw.get("finished_at") or raw.get("called_at") or row[1]
            if not isinstance(observed, str):
                return result
            stamp = datetime.fromisoformat(observed.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                return result
            clock = now or datetime.now(timezone.utc)
            if clock.tzinfo is None:
                return result
            delta = (clock.astimezone(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds()
            result["last_observed_madrid"] = stamp.astimezone(
                ZoneInfo("Europe/Madrid")).isoformat(timespec="seconds")
            if delta < -120:
                return {**result, "state": "CLOCK_UNVERIFIED"}
            result["age_minutes"] = max(0, int(delta // 60))
            result["state"] = "RECENT_RECEIPT" if delta <= FRESH_MINUTES * 60 else "STALE_RECEIPT"
            return result
    except (OSError, sqlite3.Error, ValueError, TypeError, json.JSONDecodeError):
        return {**result, "state": "READ_UNAVAILABLE"}
