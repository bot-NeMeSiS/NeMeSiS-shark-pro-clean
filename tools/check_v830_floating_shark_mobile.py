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
        "single_widget_markup": base.count('class="shark-widget"') == 1,
        "admin_hidden": 'body[data-v830-shell="true"].ns-admin .shark-widget' in css,
        "shark_routes_hidden": all(route in css for route in ['data-ns-route="/shark"', 'data-ns-route="/shark-ai"', 'data-ns-route="/shark-core"']),
        "mobile_safe_bottom": "bottom:calc(76px + var(--v830-bottom-gap))" in css or "bottom:calc(74px + var(--v830-bottom-gap))" in css,
        "panel_above_nav": "bottom:calc(142px + var(--v830-safe-bottom))" in css,
        "scroll_top_hidden_mobile": "body[data-v830-shell=\"true\"] .ns-scroll-top" in css and "display:none!important" in css,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
