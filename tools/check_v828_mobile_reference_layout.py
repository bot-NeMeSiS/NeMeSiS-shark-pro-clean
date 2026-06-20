#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "static" / "app.css"


def main() -> int:
    css = CSS.read_text(encoding="utf-8", errors="replace")
    checks = {
        "mobile_breakpoint": "@media(max-width:1120px)" in css and "@media(max-width:620px)" in css,
        "rail_hidden_mobile": ".v828-client-rail{display:none!important;}" in css,
        "bottom_nav_mobile": ".bottom-nav-clean" in css and "grid-template-columns:repeat(5" in css,
        "no_horizontal_hint": "grid-template-columns:1fr!important" in css,
        "floating_shark_mobile": "bottom:calc(84px + env(safe-area-inset-bottom,0px))" in css,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

