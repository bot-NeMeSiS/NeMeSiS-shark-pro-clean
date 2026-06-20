#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "templates" / "base.html"
APP = ROOT / "templates" / "client_app_center.html"
MATCH = ROOT / "templates" / "match_detail.html"
ADMIN = ROOT / "templates" / "admin_dashboard.html"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def main() -> int:
    base, app, match, admin = read(BASE), read(APP), read(MATCH), read(ADMIN)
    combined = "\n".join([base, app, match, admin])
    checks = {
        "client_core_links": all(h in combined for h in ["/app", "/calendar", "/live", "/picks", "/shark", "/telegram", "/support"]),
        "profile_support_logout": all(h in combined for h in ["/profile", "/support", "/logout"]),
        "match_detail_links": all(h in match for h in ["/calendar", "/picks", "/shark"]),
        "admin_core_links": all(h in base + admin for h in ["/admin/users", "/admin/data-center", "/admin/telegram/command-center", "/admin/memberships"]),
        "view_client_link": "/sports-hub" in base or "/app" in base,
        "automation_link": "/admin/automation-center" in base or "/admin/daily-automation" in combined,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

