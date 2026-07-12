"""Read-only V934 realtime sports worker. Dry-run is the default mode."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.v934_realtime_sports_engine import build_realtime_snapshot  # noqa: E402
from engines.v935_launch_trust_engine import (  # noqa: E402
    build_data_trust_snapshot,
    enrich_match_lifecycle,
    enrich_pick_lifecycle,
)


def _db_path(value: str = "") -> Path:
    configured = value or os.getenv("DB_PATH") or str(ROOT / "data" / "database.db")
    return Path(configured).expanduser().resolve()


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return bool(row)


def _read_rows(connection: sqlite3.Connection, table: str, limit: int = 250) -> list[dict[str, Any]]:
    if not _table_exists(connection, table):
        return []
    safe_limit = max(1, min(int(limit), 500))
    cursor = connection.execute(f'SELECT * FROM "{table}" LIMIT ?', (safe_limit,))
    columns = [item[0] for item in cursor.description or []]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _last_sync(connection: sqlite3.Connection) -> str:
    if not _table_exists(connection, "sync_logs"):
        return ""
    columns = {row[1] for row in connection.execute("PRAGMA table_info(sync_logs)").fetchall()}
    for column in ("finished_at", "started_at", "created_at", "updated_at"):
        if column in columns:
            row = connection.execute(
                f'SELECT "{column}" FROM sync_logs WHERE "{column}" IS NOT NULL ORDER BY "{column}" DESC LIMIT 1'
            ).fetchone()
            if row and row[0]:
                return str(row[0])[:80]
    return ""


def collect(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        snapshot = build_realtime_snapshot({})
        return {**snapshot, "worker_status": "db_missing_safe", "db_available": False}
    uri = f"file:{db_path.as_posix()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=1.5) as connection:
            matches = _read_rows(connection, "matches")
            picks = _read_rows(connection, "picks")
            last_sync = _last_sync(connection)
    except sqlite3.OperationalError as exc:
        snapshot = build_realtime_snapshot({})
        locked = "locked" in str(exc).lower()
        return {
            **snapshot,
            "worker_status": "db_locked_safe" if locked else "db_read_unavailable_safe",
            "db_available": True,
        }
    normalized_matches = [enrich_match_lifecycle(item) for item in matches]
    normalized_picks = [enrich_pick_lifecycle(item) for item in picks]
    summary = {
        "valid_matches_today": [item for item in normalized_matches if (item.get("v935_surface") or {}).get("home")],
        "valid_upcoming_matches": [item for item in normalized_matches if item.get("v935_lifecycle") == "UPCOMING"],
        "valid_live_events": [item for item in normalized_matches if item.get("v935_lifecycle") in {"LIVE", "HALFTIME"}],
        "valid_active_picks": [item for item in normalized_picks if item.get("v935_publishable")],
        "incomplete_matches": [],
        "provider_status": "local_db_read_only",
        "last_sync": last_sync,
    }
    snapshot = build_realtime_snapshot(summary)
    snapshot["data_trust"] = build_data_trust_snapshot(
        normalized_matches,
        normalized_picks,
        provider_status="local_db_read_only",
        last_sync=last_sync,
    )
    snapshot["worker_status"] = "ok" if snapshot.get("matches") or snapshot.get("picks") else "waiting_for_real_data"
    snapshot["db_available"] = True
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="NeMeSiS V934 read-only realtime sports worker")
    parser.add_argument("--dry-run", action="store_true", help="Explicitly confirm read-only execution")
    parser.add_argument("--db-path", default="", help="Optional local DB path")
    parser.add_argument("--write-json", action="store_true", help="Write sanitized runtime evidence")
    args = parser.parse_args()
    snapshot = collect(_db_path(args.db_path))
    status = str(snapshot.get("worker_status") or "safe_unavailable")
    result = {
        "status": status,
        "ok": status in {"ok", "waiting_for_real_data", "db_missing_safe", "db_locked_safe"},
        "dry_run": True,
        "safe_message": snapshot.get("safe_message") or "Estado realtime leído de forma segura.",
        "next_action": "review_realtime_center" if status == "ok" else "run_authorized_sports_sync",
        "report_path": "reports/V935_REALTIME_CACHE_QA.md",
        "counts": snapshot.get("counts") or {},
        "realtime_match_status": snapshot.get("realtime_match_status"),
        "realtime_live_status": snapshot.get("realtime_live_status"),
        "odds_freshness_status": snapshot.get("odds_freshness_status"),
        "generated_at_madrid": snapshot.get("generated_at_madrid"),
        "external_calls": 0,
        "database_writes": 0,
        "secrets_visible": False,
    }
    if args.write_json:
        output = ROOT / "data" / "runtime" / "automation_workforce" / "v935_workers" / "realtime_sports_worker.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
