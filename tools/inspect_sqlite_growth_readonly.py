"""Read-only SQLite growth inventory for issue #327.

Run on the Render persistent disk only when explicitly authorized.
No VACUUM, checkpoint, DELETE, migrations, temp DB copies or API calls.
Outputs table sizes via dbstat when supported; otherwise table counts only.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path


def inspect_database(db_path: str, limit: int = 20) -> dict:
    path = Path(db_path).expanduser()
    result = {"ok": False, "readonly": True, "writes": 0, "db_size_bytes": 0,
              "wal_size_bytes": 0, "shm_size_bytes": 0, "tables": [],
              "dbstat_available": False, "error_code": ""}
    if not path.is_file():
        result["error_code"] = "DB_NOT_FOUND"
        return result
    try:
        result["db_size_bytes"] = path.stat().st_size
        for suffix, field in (("-wal", "wal_size_bytes"), ("-shm", "shm_size_bytes")):
            linked = Path(str(path) + suffix)
            result[field] = linked.stat().st_size if linked.is_file() else 0
        # Read-only connection. No explicit checkpoint, journal operation or writes.
        with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2) as db:
            db.execute("PRAGMA query_only=ON")
            result["page_size"] = int(db.execute("PRAGMA page_size").fetchone()[0])
            result["page_count"] = int(db.execute("PRAGMA page_count").fetchone()[0])
            result["freelist_count"] = int(db.execute("PRAGMA freelist_count").fetchone()[0])
            result["allocated_bytes"] = result["page_size"] * result["page_count"]
            try:
                records = db.execute(
                    "SELECT name, SUM(pgsize) AS size_bytes FROM dbstat "
                    "GROUP BY name ORDER BY size_bytes DESC LIMIT ?", (max(1, min(100, limit)),)
                ).fetchall()
                result["dbstat_available"] = True
                result["tables"] = [{"name": str(name), "bytes": int(size)}
                                    for name, size in records
                                    if not str(name).startswith("sqlite_")]
            except sqlite3.Error:
                # No guesses: exact per-table sizes require dbstat support.
                result["error_code"] = "DBSTAT_UNAVAILABLE"
            result["ok"] = True
    except (OSError, sqlite3.Error) as exc:
        result["error_code"] = "READ_ONLY_INSPECTION_FAILED"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.getenv("DB_PATH", ""))
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if not args.db:
        print(json.dumps({"ok": False, "readonly": True, "error_code": "DB_PATH_NOT_SET"}))
        return 2
    print(json.dumps(inspect_database(args.db, args.limit), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
