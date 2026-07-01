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
        "v833_shell": "data-v833-shell" in base,
        "bottom_nav_unique": base.count('class="bottom-nav bottom-nav-clean"') == 1,
        "bottom_nav_v830_fixed": "left:50%!important" in css and "--v830-bottom-nav-width" in css,
        "five_links": all(h in base for h in ['href="/app"', 'href="/partidos"', 'href="/live"', 'href="/picks"', 'href="/shark"']),
        "no_mobile_scroll_top": "body[data-v830-shell=\"true\"] .ns-scroll-top" in css and "display:none!important" in css,
        "safe_area": "env(safe-area-inset-bottom" in css,
        "shark_routes_hidden": all(r in css for r in ['data-ns-route="/shark"', 'data-ns-route="/shark-ai"', 'data-ns-route="/shark-core"']),
        "mobile_breakpoints": "@media(max-width:768px)" in css and "@media(max-width:430px)" in css,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
