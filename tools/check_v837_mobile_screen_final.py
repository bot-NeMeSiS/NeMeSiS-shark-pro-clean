#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")


def main() -> int:
    checks = {
        "safe_area": "safe-area-inset-bottom" in CSS and "safe-area-inset-top" in CSS,
        "no_overflow": "overflow-x:hidden" in CSS,
        "bottom_nav_5": "grid-template-columns:repeat(5" in CSS,
        "bottom_nav_center": "left:50%" in CSS and "translateX(-50%)" in CSS,
        "floating_shark_safe": ".shark-widget" in CSS and "bottom:calc(82px" in CSS,
        "shark_pages_hide_floating": 'data-ns-route="/shark"' in CSS and 'data-ns-route="/shark-core"' in CSS,
        "admin_hidden_mobile_rails": "v808-admin-rail" in BASE and "display:none!important" in CSS,
        "touch_buttons": "min-height:44px" in CSS,
        "templates_marked": len(list((ROOT / "templates").rglob("*.html"))) > 0 and "data-v837-template" in "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (ROOT / "templates").rglob("*.html")),
    }
    missing = [k for k, v in checks.items() if not v]
    print(json.dumps({"ok": not missing, "missing": missing}, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
