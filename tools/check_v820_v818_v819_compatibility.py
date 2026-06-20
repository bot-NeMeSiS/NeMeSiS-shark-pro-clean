#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def has_route(app: str, route: str) -> bool:
    q = re.escape(route)
    return bool(re.search(rf"@app\.(?:route|get|post)\(\s*['\"]{q}['\"]", app))


def main() -> int:
    app = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    checks = {
        "v818_master_tick": has_route(app, "/api/automation/master-tick"),
        "v818_health": has_route(app, "/api/automation/health-check"),
        "v818_admin_pages": has_route(app, "/admin/daily-automation") and has_route(app, "/admin/automation-os"),
        "v818_engines": "daily_automation_engine" in app and "telegram_professional_scheduler" in app,
        "secret_guard": "automation_cron_access_allowed" in app,
        "v819_shell_kept": 'data-v819-shell="true"' in base and "has_v819_shell" in app,
        "v819_dedup_css_kept": ".v811-top-actions" in css and ".v797-session-pills" in css and ".v808-admin-dock" in css,
        "v820_shell_added": 'data-v820-shell="true"' in base and "has_v820_shell" in app,
        "db_path_untouched": 'DB_PATH = os.getenv("DB_PATH", "/data/database.db")' in app,
    }
    failed = [k for k, v in checks.items() if not v]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


