#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "templates" / "base.html"
CSS = ROOT / "static" / "app.css"
TEMPLATES = ROOT / "templates"


def main() -> int:
    base = BASE.read_text(encoding="utf-8", errors="replace")
    css = CSS.read_text(encoding="utf-8", errors="replace")
    templates = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in TEMPLATES.glob("*.html"))
    checks = {
        "single_bottom_nav_markup": base.count('class="bottom-nav bottom-nav-clean"') == 1,
        "single_shark_widget_markup": base.count('class="shark-widget"') == 1,
        "scroll_top_mobile_hidden": "body[data-v830-shell=\"true\"] .ns-scroll-top" in css and "display:none!important" in css,
        "admin_no_client_float": 'body[data-v832-shell="true"].ns-admin :is(.bottom-nav-clean,.shark-widget,.v825-public-floating-shark)' in css,
        "no_broken_title_literal": "{{ title or 'NeMeSiS SHARK PRO' }}" not in templates,
        "no_known_mojibake": not any(x in templates for x in ["Espa?a", "Andaluc?a", "top mundal"]),
        "v832_marker": "V832 FULL APP REFERENCE VISUAL GITHUB RENDER WORKFLOW START" in css,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
