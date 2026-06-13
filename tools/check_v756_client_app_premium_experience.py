#!/usr/bin/env python3
"""V756 client premium app experience static validation."""
from __future__ import annotations
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V756_CLIENT_APP_PREMIUM_EXPERIENCE_TOTAL_POLISH"

REQUIRED = {
    "VERSION.txt": [VERSION],
    "app.py": [VERSION, "build_client_app_premium_context", "client_premium"],
    "engines/client_app_premium_engine.py": ["build_client_premium_home", "build_client_premium_picks", "build_client_premium_calendar", "build_client_premium_match"],
    "templates/home.html": ["v756-command-center", "Centro cliente SHARK"],
    "templates/picks.html": ["v756-picks-command", "Centro de picks"],
    "templates/calendar.html": ["v756-calendar-guide", "Agenda inteligente"],
    "templates/match_detail.html": ["v756-match-command", "Centro del partido"],
    "static/app.css": ["V756_CLIENT_APP_PREMIUM_EXPERIENCE_TOTAL_POLISH", "v756-kpi-grid"],
    "reports/V756_CLIENT_APP_PREMIUM_EXPERIENCE_TOTAL_POLISH_REPORT.md": [VERSION],
}


def main() -> int:
    errors = []
    for rel, needles in REQUIRED.items():
        path = ROOT / rel
        if not path.exists():
            errors.append(f"missing:{rel}")
            continue
        text = path.read_text(encoding="utf-8-sig")
        for needle in needles:
            if needle not in text:
                errors.append(f"missing-token:{rel}:{needle}")
    build = ROOT / "tools" / "build_clean_release.py"
    if build.exists() and "reports/V756_" not in build.read_text(encoding="utf-8-sig"):
        errors.append("build_clean_release does not include V756 reports")
    print(json.dumps({"ok": not errors, "version": VERSION, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
