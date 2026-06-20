#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = {
    "app": "templates/client_app_center.html",
    "calendar": "templates/calendar.html",
    "live": "templates/live.html",
    "picks": "templates/picks.html",
    "match_detail": "templates/match_detail.html",
}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    css = read("static/app.css")
    template_checks = {
        name: f'data-v823-template="{name if name != "app" else "client_app_center"}"' in read(path)
        for name, path in TEMPLATES.items()
    }
    checks = {
        **{f"template_{name}_marked": ok for name, ok in template_checks.items()},
        "app_screen_css": ".v823-app-screen" in css or ".v823-certified-screen" in css,
        "calendar_screen_css": ".v823-calendar-screen" in css or ".v801-agenda-row" in css,
        "live_screen_css": ".v823-live-screen" in css or ".v799-live-card" in css,
        "picks_screen_css": ".v823-picks-screen" in css or ".v799-pick-card" in css,
        "match_screen_css": ".v823-match-screen" in css or ".v799-match-hero" in css,
        "compact_mobile_media": "@media(max-width:560px)" in css and "bottom-nav-clean" in css,
        "no_new_fake_data_terms": all(term not in css.lower() for term in ["demo-only", "fake-match"]),
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

