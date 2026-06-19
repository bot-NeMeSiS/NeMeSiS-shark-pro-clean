#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ["home.html", "client_login.html", "client_app_center.html", "calendar.html", "live.html", "picks.html", "match_detail.html", "shark.html", "profile.html", "telegram.html"]


def main() -> int:
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
    template_results = {}
    for name in TEMPLATES:
        text = (ROOT / "templates" / name).read_text(encoding="utf-8", errors="replace")
        template_results[name] = "data-v820-template=" in text
    checks = {
        "templates_v820": all(template_results.values()),
        "screen_class": "v820-certified-screen" in css,
        "premium_cards": "v820-card" in css and "box-shadow" in css,
        "match_cards_polished": ".v799-agenda-row" in css and ".v799-live-card" in css,
        "picks_polished": ".v799-feature-pick" in css,
        "topbar_single_preserved": ".top.ns-topbar" in css,
        "shark_single_preserved": 'data-ns-route="/shark"' in css and ".shark-widget" in css,
    }
    failed = [k for k, v in checks.items() if not v]
    print(json.dumps({"ok": not failed, "failed": failed, "templates": template_results, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
