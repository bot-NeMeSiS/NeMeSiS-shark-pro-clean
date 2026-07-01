#!/usr/bin/env python3
"""V819 route, template and navigation checks."""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V819_REFERENCE_UI_DEDUP_LAYER_PURGE_CLIENT_ADMIN_FINAL"
CURRENT = "V820_REAL_CRESTS_REFERENCE_VISUAL_PIXEL_POLISH_FINAL"
CURRENT_V821 = "V821_PRODUCTION_502_CRESTS_RUNTIME_HOTFIX"
CURRENT_V822 = "V822_PRODUCTION_STABILITY_RUNTIME_AUTOMATION_CRESTS_FINAL"
ACCEPTED_ACTIVE = {VERSION, CURRENT, CURRENT_V821, CURRENT_V822}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def route_exists(app_text: str, route: str) -> bool:
    route_escaped = re.escape(route)
    patterns = [
        rf"@app\.route\(\s*['\"]{route_escaped}['\"]",
        rf"@app\.get\(\s*['\"]{route_escaped}['\"]",
        rf"@app\.post\(\s*['\"]{route_escaped}['\"]",
    ]
    return any(re.search(pattern, app_text) for pattern in patterns)


def main() -> int:
    app = read("app.py")
    base = read("templates/base.html")
    templates = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (ROOT / "templates").glob("*.html"))

    client_routes = [
        "/", "/cliente-login", "/registro", "/app", "/sports-hub", "/calendar", "/partidos",
        "/live", "/picks", "/shark", "/profile", "/telegram", "/favorites", "/combis",
        "/track-record", "/support", "/legal",
    ]
    admin_routes = [
        "/admin/dashboard", "/admin/map", "/admin/control-center", "/admin/daily-automation",
        "/admin/automation-os", "/admin/telegram/command-center", "/admin/users",
        "/admin/memberships", "/admin/matches-sync", "/admin/data-center", "/admin/payments",
        "/admin/final-certification",
    ]
    api_routes = [
        "/api/runtime-version", "/api/health", "/api/automation/master-tick",
        "/api/automation/health-check",
    ]

    missing_client = [r for r in client_routes if not route_exists(app, r)]
    missing_admin = [r for r in admin_routes if not route_exists(app, r)]
    missing_api = [r for r in api_routes if not route_exists(app, r)]

    checks = {
        "version_v819_or_newer": read("VERSION.txt").strip() in ACCEPTED_ACTIVE and any(value in app for value in ACCEPTED_ACTIVE),
        "nav_has_support": 'href="/support"' in base,
        "nav_has_logout": 'href="/logout"' in base,
        "nav_no_client_admin_mix": "/admin/control-center" in base and "/sports-hub" in base,
        "templates_marked_v819": templates.count("data-v819-template=") >= 10,
        "master_tick_present": not missing_api,
        "client_routes_present": not missing_client,
        "admin_routes_present": not missing_admin,
    }
    failed = [name for name, ok in checks.items() if not ok]
    print(json.dumps({
        "ok": not failed,
        "failed": failed,
        "missing_client": missing_client,
        "missing_admin": missing_admin,
        "missing_api": missing_api,
        "checks": checks,
    }, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


