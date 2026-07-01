#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    app = read("app.py")
    checks = {
        "master_tick_route": '@app.route("/api/automation/master-tick"' in app,
        "health_check_route": '@app.route("/api/automation/health-check"' in app,
        "admin_daily_route": '@app.route("/admin/daily-automation")' in app and '@app.route("/admin/automation-os")' in app,
        "secret_guard": "automation_cron_access_allowed" in app and "automation_json_forbidden" in app,
        "dry_run_present": "dry_run" in app and "v818_run_master_tick" in app,
        "v818_engines_imported": all(token in app for token in ["v818_run_master_tick", "v818_system_health", "professional_telegram_summary"]),
        "health_has_runtime_stability": "runtime_stability" in app and "db_accessible" in app and "last_master_tick" in app,
        "madrid_time": "Europe/Madrid" in app and "madrid_time_engine" in app,
        "no_secret_exposure": "AUTOMATION_SECRET" not in read("templates/admin_daily_automation.html"),
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


