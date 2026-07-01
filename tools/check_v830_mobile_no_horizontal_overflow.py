#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "static" / "app.css"


def main() -> int:
    css = CSS.read_text(encoding="utf-8", errors="replace")
    checks = {
        "global_overflow_hidden": "overflow-x:hidden!important" in css,
        "main_max_width": "max-width:100%!important" in css,
        "min_width_zero": "min-width:0!important" in css,
        "media_390": "@media(max-width:390px)" in css,
        "media_430": "@media(max-width:430px)" in css,
        "tables_scroll_safe": "overflow-x:auto" in css,
        "fixed_nav_no_left_right_pair": "left:50%!important" in css and "right:auto!important" in css,
        "shark_background_clipped": "overflow:hidden!important" in css and "pointer-events:none!important" in css,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
