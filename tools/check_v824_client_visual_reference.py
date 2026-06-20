#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = {
    "client_app_center": "templates/client_app_center.html",
    "calendar": "templates/calendar.html",
    "live": "templates/live.html",
    "picks": "templates/picks.html",
    "match_detail": "templates/match_detail.html",
    "shark": "templates/shark.html",
    "profile": "templates/profile.html",
    "telegram": "templates/telegram.html",
    "support": "templates/support.html",
    "admin_dashboard": "templates/admin_dashboard.html",
}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    css = read("static/app.css")
    checks = {f"template_{name}_v824": f'data-v824-template="{name}"' in read(path) for name, path in TEMPLATES.items()}
    checks.update({
        "css_app_dashboard": "data-v824-shell" in css and ".v812-hero-shell" in css,
        "css_calendar": "data-v824-shell" in css and ".v799-agenda-row" in css,
        "css_live": "data-v824-shell" in css and ".v799-live-card.is-live" in css,
        "css_picks": "data-v824-shell" in css and ".v799-feature-pick" in css,
        "css_shark": "data-v824-shell" in css and ".shark-action-grid" in css,
        "css_profile_telegram_support": all(token in css for token in [".v824-profile-screen", ".v824-telegram-screen", ".v824-support-screen"]),
        "no_fake_data_terms": all(term not in css.lower() for term in ["fake-match", "demo-only", "invented"]),
    })
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


