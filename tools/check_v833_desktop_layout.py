#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "static" / "app.css"


def main() -> int:
    css = CSS.read_text(encoding="utf-8", errors="replace")
    checks = {
        "v833_css": "V833 REFERENCE ECOSYSTEM VISUAL COMPLETION START" in css,
        "desktop_media": "@media(min-width:1024px)" in css,
        "bottom_nav_desktop_hidden": "@media(min-width:769px)" in css and ".bottom-nav-clean" in css,
        "admin_shell": 'body[data-v833-shell="true"].ns-admin' in css,
        "admin_no_client_float": '.ns-admin :is(.bottom-nav-clean,.shark-widget' in css,
        "cards_transition": "transition:border-color" in css,
        "desktop_grid_gap": ":is(.admin-grid" in css or ".admin-grid" in css,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
