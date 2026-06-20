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
    checks = {f"template_{name}_v825": f'data-v825-template="{name}"' in read(path) for name, path in TEMPLATES.items()}
    checks.update({
        "css_identity_marker": "V825 SHARK IDENTITY FLOATING BACKGROUND REFERENCE START" in css,
        "css_shark_background": ".v825-shark-background" in css and ".shark-dot-watermark" in css,
        "css_floating_shark": ".shark-fab" in css and ".v825-public-floating-shark" in css,
        "css_client_surfaces": all(token in css for token in [".v812-hero-shell", ".v799-appbar", ".v774-client-hero"]),
        "css_cards_depth": "backdrop-filter" in css and "box-shadow" in css,
        "no_fake_data_terms": all(term not in css.lower() for term in ["fake-match", "demo-only", "invented"]),
    })
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

