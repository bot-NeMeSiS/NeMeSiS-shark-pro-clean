#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
REQUIRED = [
    "home.html",
    "client_login.html",
    "register.html",
    "client_app_center.html",
    "calendar.html",
    "live.html",
    "picks.html",
    "match_detail.html",
    "shark.html",
    "shark_core.html",
    "profile.html",
    "telegram.html",
    "support.html",
    "favorites.html",
    "track_record.html",
    "combis.html",
    "betting_markets.html",
    "highlights.html",
    "admin_dashboard.html",
    "admin_daily_automation.html",
    "admin_data_center.html",
    "admin_telegram_command_center.html",
    "admin_users.html",
    "admin_memberships.html",
]


def main() -> int:
    missing_files: list[str] = []
    missing_markers: list[str] = []
    for name in REQUIRED:
        path = TEMPLATES / name
        if not path.exists():
            missing_files.append(name)
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "data-v830-template" not in text and "v830-certified-screen" not in text:
            missing_markers.append(name)
    ok = not missing_files and not missing_markers
    print(json.dumps({"ok": ok, "missing_files": missing_files, "missing_markers": missing_markers}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
