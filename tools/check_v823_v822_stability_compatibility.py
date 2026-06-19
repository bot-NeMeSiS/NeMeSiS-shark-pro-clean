#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    app = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    checks = {
        "v818_master_tick_preserved": "/api/automation/master-tick" in app and "api_v818_automation_master_tick" in app,
        "v818_health_check_preserved": "/api/automation/health-check" in app and "api_v818_automation_health_check" in app,
        "v819_dedup_preserved": "dedupe_matches_for_display" in app or "V819 REFERENCE UI DEDUP LAYER PURGE" in css,
        "v820_crests_preserved": all(token in app for token in ["/asset/team-logo/", "/asset/league-logo/", "/team-crest.svg"]),
        "v821_502_hotfix_preserved": "last_502_hotfix" in app and "LIGHT_STARTUP_ENDPOINTS" in app,
        "v822_runtime_stability_preserved": "v822_runtime_stability_snapshot" in app and "runtime_stability" in app,
        "v823_is_additive_shell": 'data-v822-shell="true"' in base and 'data-v823-shell="true"' in base,
        "no_db_path_change": 'DB_PATH = os.getenv("DB_PATH", "/data/database.db")' in app,
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
