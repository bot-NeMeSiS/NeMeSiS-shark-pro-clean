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
        "v818_master_tick": "/api/automation/master-tick" in app and "api_v818_automation_master_tick" in app,
        "v818_health_check": "/api/automation/health-check" in app and "api_v818_automation_health_check" in app,
        "v819_dedup": "V819 REFERENCE UI DEDUP LAYER PURGE" in css or "dedupe_matches_for_display" in app,
        "v820_crests": all(token in app for token in ["/asset/team-logo/", "/asset/league-logo/", "/team-crest.svg"]),
        "v821_hotfix": "last_502_hotfix" in app and "LIGHT_STARTUP_ENDPOINTS" in app,
        "v822_stability": "v822_runtime_stability_snapshot" in app and "runtime_stability" in app,
        "v823_visual": 'data-v823-shell="true"' in base and "V823 RENDER VIDEO REFERENCE REAL CRESTS PIXEL EXPERIENCE START" in css,
        "v824_visual": 'data-v824-shell="true"' in base and "V824 RENDER VIDEO PIXEL MATCH FINAL APP EXPERIENCE START" in css,
        "v825_additive": 'data-v825-shell="true"' in base and 'DB_PATH = os.getenv("DB_PATH", "/data/database.db")' in app,
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

