#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
    checks = {
        "mobile_media": "@media(max-width:760px)" in css,
        "compact_topbar": "body[data-v820-shell=\"true\"] .topin" in css,
        "bottom_nav_unique": base.count('class="bottom-nav bottom-nav-clean"') == 1,
        "bottom_nav_grid": "repeat(5,minmax(0,1fr))" in css,
        "crest_mobile_size": "34px" in css,
        "no_horizontal_intent": "overflow-x:auto" in css and "scrollbar-width:none" in css,
        "shark_not_on_shark_page": 'data-ns-route="/shark"' in css,
    }
    failed = [k for k, v in checks.items() if not v]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


