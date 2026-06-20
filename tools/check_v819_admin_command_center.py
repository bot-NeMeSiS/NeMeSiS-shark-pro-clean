#!/usr/bin/env python3
"""V819 admin command center and V818 automation compatibility checks."""
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
    admin_templates = {p.name for p in (ROOT / "templates").glob("admin*.html")}

    required_routes = [
        "/admin/dashboard", "/admin/control-center", "/admin/map", "/admin/users",
        "/admin/data-center", "/admin/matches-sync", "/admin/picks",
        "/admin/telegram/command-center", "/admin/daily-automation", "/admin/automation-os",
        "/api/automation/master-tick", "/api/automation/health-check",
    ]
    missing = [route for route in required_routes if not has_route(app, route)]
    checks = {
        "admin_routes_present": not missing,
        "daily_automation_template": "admin_daily_automation.html" in admin_templates,
        "automation_os_template": "admin_daily_automation.html" in admin_templates and "/admin/automation-os" in app,
        "admin_topbar_compact": "/admin/telegram/pro-preview" not in base.split("{% elif current_user %}", 1)[0],
        "admin_rail_hidden_on_v819": ".v808-admin-dock" in css and "display:none!important" in css,
        "admin_bottom_nav_hidden": ".ns-admin .bottom-nav-clean" in css,
        "v818_engine_imports_preserved": "daily_automation_engine" in app and "telegram_professional_scheduler" in app,
        "secret_guard_preserved": "automation_cron_access_allowed" in app,
    }
    failed = [name for name, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "missing": missing, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


