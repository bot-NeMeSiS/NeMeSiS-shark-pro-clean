from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V932_AUTHENTICATED_PRODUCTION_CLIENT_ADMIN_AND_REAL_SPORTS_VALUE_FINAL"
SUCCESSOR_VERSION = "V933_REFERENCE_PARITY_PRODUCT_DESIGN_SPRINT_SYSTEM_FINAL"
V934_VERSION = "V934_REFERENCE_EXACTNESS_REALTIME_SPORTS_PRODUCTION_PERFECTION_FINAL"
V935_VERSION = "V935_LAUNCH_TRUST_REAL_DATA_LIFECYCLE_PERFORMANCE_REFERENCE_POLISH_FINAL"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from check_v931_production_client_routes_hotfix import create_legacy_db, mock_session, switch_db


def route_statuses(app_module, db_path: Path, profile: str) -> list[dict]:
    switch_db(app_module, db_path)
    routes = [
        ("client", "/app"), ("client", "/favorites"),
        ("admin", "/admin/dashboard"), ("admin", "/admin/data-center"),
    ]
    output = []
    for role, route in routes:
        client = app_module.app.test_client()
        mock_session(client, role)
        started = time.monotonic()
        response = client.get(route, follow_redirects=False)
        body = response.get_data(as_text=True)
        output.append({
            "profile": profile, "role": role, "route": route,
            "status": response.status_code,
            "elapsed": round(time.monotonic() - started, 3),
            "locked_visible": "database is locked" in body.lower(),
        })
    return output


def main() -> int:
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    os.environ["ENABLE_AUTOMATED_RENDER_DEPLOY"] = "0"
    with tempfile.TemporaryDirectory(prefix="nemesis_v932_sqlite_", ignore_cleanup_errors=True) as temp_dir:
        os.environ["DB_PATH"] = str(Path(temp_dir) / "normal.sqlite")
        import app as app_module

        app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
        app_module.app.logger.disabled = True
        logging.disable(logging.CRITICAL)
        original_db_path = app_module.DB_PATH
        original_init = app_module.initialize_once
        original_v931 = app_module.v931_record_client_route_issue
        original_v932 = app_module.v932_record_authenticated_issue
        app_module.v931_record_client_route_issue = lambda *args, **kwargs: True
        app_module.v932_record_authenticated_issue = lambda *args, **kwargs: True
        temp_root = Path(temp_dir)
        legacy = temp_root / "legacy.sqlite"
        modern = temp_root / "modern.sqlite"
        empty = temp_root / "empty.sqlite"
        locked = temp_root / "locked.sqlite"
        create_legacy_db(legacy)
        modern_conn = sqlite3.connect(modern)
        modern_conn.execute("CREATE TABLE matches(id TEXT PRIMARY KEY, priority INTEGER DEFAULT 0)")
        modern_conn.execute("CREATE TABLE picks(id TEXT PRIMARY KEY, priority INTEGER DEFAULT 0)")
        modern_conn.commit()
        modern_conn.close()
        sqlite3.connect(empty).close()
        lock_conn = sqlite3.connect(locked, timeout=0.1)
        lock_conn.execute("CREATE TABLE matches(id TEXT PRIMARY KEY)")
        lock_conn.execute("CREATE TABLE picks(id TEXT PRIMARY KEY)")
        lock_conn.commit()
        lock_conn.execute("BEGIN EXCLUSIVE")
        try:
            results = route_statuses(app_module, modern, "modern")
            results += route_statuses(app_module, legacy, "legacy")
            results += route_statuses(app_module, empty, "empty")
            results += route_statuses(app_module, locked, "locked")
        finally:
            lock_conn.rollback()
            lock_conn.close()

        class FailingConnection:
            def __init__(self):
                self.closed = False

            def cursor(self):
                return self

            def execute(self, *args, **kwargs):
                raise sqlite3.OperationalError("no such column: priority")

            def fetchall(self):
                return []

            def close(self):
                self.closed = True

        fake = FailingConnection()
        original_db = app_module.db
        app_module.db = lambda: fake
        rows_raised = False
        try:
            app_module.rows("SELECT priority FROM matches")
        except sqlite3.OperationalError:
            rows_raised = True
        finally:
            app_module.db = original_db
            app_module.DB_PATH = original_db_path
            app_module.initialize_once = original_init
            app_module.v931_record_client_route_issue = original_v931
            app_module.v932_record_authenticated_issue = original_v932

        retry_calls = {"count": 0}
        original_safe_read = app_module._v931_read_table_rows

        def transient_read(table, limit=600):
            retry_calls["count"] += 1
            if retry_calls["count"] == 1:
                return [], {"status": "database_locked", "error_type": "OperationalError"}
            return [], {"status": "ok", "error_type": ""}

        app_module._v931_read_table_rows = transient_read
        try:
            _records, retry_meta = app_module._v932_read_table_rows("matches", 1)
        finally:
            app_module._v931_read_table_rows = original_safe_read

    failures = [item for item in results if item["status"] >= 500 or item["locked_visible"]]
    locked_results = [item for item in results if item["profile"] == "locked"]
    checks = {
        "version_v932_or_successor": app_module.APP_VERSION in {VERSION, SUCCESSOR_VERSION, V934_VERSION, V935_VERSION},
        "priority_schema_safe": not any(item["profile"] == "modern" for item in failures),
        "legacy_schema_safe": not any(item["profile"] == "legacy" for item in failures),
        "empty_schema_safe": not any(item["profile"] == "empty" for item in failures),
        "locked_database_safe": not any(item in failures for item in locked_results),
        "locked_reads_bounded": sum(item["elapsed"] for item in locked_results) < 8.0,
        "rows_exception_preserved": rows_raised,
        "rows_connection_closed": fake.closed,
        "short_retry_guard_present": hasattr(app_module, "_v932_read_table_rows"),
        "single_retry_then_success": retry_calls["count"] == 2 and retry_meta.get("attempts") == 2,
        "no_persistent_database_locked": not failures,
    }
    failed = [name for name, ok in checks.items() if not ok]
    payload = {"version": VERSION, "ok": not failed, "checks": checks, "failed": failed, "results": results}
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
