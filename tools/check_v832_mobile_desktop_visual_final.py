#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "templates" / "base.html"
CSS = ROOT / "static" / "app.css"


def main() -> int:
    base = BASE.read_text(encoding="utf-8", errors="replace")
    css = CSS.read_text(encoding="utf-8", errors="replace")
    checks = {
        "v832_shell": "data-v832-shell" in base,
        "v832_css": "V832 FULL APP REFERENCE VISUAL GITHUB RENDER WORKFLOW START" in css,
        "mobile_bottom_nav_v830_preserved": "V830 MOBILE BOTTOM NAV PIXEL QA START" in css and "left:50%!important" in css,
        "desktop_bottom_hidden": "@media(min-width:769px)" in css and ".bottom-nav-clean" in css,
        "admin_separated": 'body[data-v832-shell="true"].ns-admin' in css and "display:none!important" in css,
        "floating_shark_controlled": ".shark-widget" in css and 'data-ns-route="/shark"' in css,
        "forms_premium": ":is(input,select,textarea)" in css,
        "cards_premium": ":is(.card,.panel" in css,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
