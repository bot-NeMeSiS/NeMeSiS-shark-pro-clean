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
        "public_float_shark_core_hidden": "'/shark-core'" in base,
        "shark_routes_hidden": all(route in css for route in ['data-ns-route="/shark"', 'data-ns-route="/shark-ai"', 'data-ns-route="/shark-core"']),
        "admin_hidden": "body[data-v829-shell=\"true\"].ns-admin .shark-widget" in css,
        "mobile_safe_position": "bottom:calc(84px + var(--v829-safe-bottom))" in css,
        "panel_not_tapping_bottom_nav": "bottom:calc(144px + var(--v829-safe-bottom))" in css,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

