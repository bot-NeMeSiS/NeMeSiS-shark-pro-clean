#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "templates" / "base.html"
CSS = ROOT / "static" / "app.css"


def main() -> int:
    base = BASE.read_text(encoding="utf-8", errors="replace")
    css = CSS.read_text(encoding="utf-8", errors="replace")
    nav_match = re.search(r'<nav class="bottom-nav bottom-nav-clean".*?</nav>', base, re.S)
    nav = nav_match.group(0) if nav_match else ""
    checks = {
        "single_bottom_nav_markup": base.count('class="bottom-nav bottom-nav-clean"') == 1,
        "client_has_five_links": all(href in nav for href in ['href="/app"', 'href="/partidos"', 'href="/live"', 'href="/picks"', 'href="/shark"']),
        "v830_centered_fixed": "left:50%!important" in css and "transform:translateX(-50%)!important" in css,
        "v830_width_controlled": "--v830-bottom-nav-width" in css and "max-width:430px!important" in css,
        "v830_five_columns": "grid-template-columns:repeat(5,minmax(0,1fr))!important" in css,
        "admin_bottom_hidden": 'body[data-v830-shell="true"].ns-admin .bottom-nav-clean' in css,
        "desktop_bottom_hidden": '@media(min-width:769px)' in css and "ns-authenticated:not(.ns-admin) .bottom-nav-clean" in css,
        "shark_route_no_floating": 'data-ns-route="/shark"] .shark-widget' in css,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
