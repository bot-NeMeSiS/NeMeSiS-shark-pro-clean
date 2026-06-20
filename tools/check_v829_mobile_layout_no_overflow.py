#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "static" / "app.css"


def main() -> int:
    css = CSS.read_text(encoding="utf-8", errors="replace")
    checks = {
        "overflow_hidden": "overflow-x:hidden!important" in css,
        "full_width_shell": "width:calc(100% - 14px)!important" in css,
        "mobile_rows_one_column": "grid-template-columns:1fr!important" in css,
        "horizontal_filters_scroll": "overflow-x:auto!important" in css,
        "touch_min_height": "--v829-touch:44px" in css,
        "tables_scroll_admin": "overflow-x:auto!important" in css and "white-space:nowrap" in css,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

