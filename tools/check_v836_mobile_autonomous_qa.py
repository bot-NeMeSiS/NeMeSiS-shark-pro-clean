#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")


def main() -> int:
    required = {
        "data-v836-shell": "data-v836-shell" in BASE,
        "css_block": "V836 AUTONOMOUS REFERENCE VISUAL REVIEW FINAL QA START" in CSS,
        "safe_area": "safe-area-inset-bottom" in CSS and "safe-area-inset-top" in CSS,
        "bottom_nav_fixed": ".bottom-nav-clean" in CSS and "grid-template-columns:repeat(5" in CSS,
        "mobile_bottom_centered": "left:50%" in CSS and "translateX(-50%)" in CSS,
        "scroll_top_hidden_mobile": ".ns-scroll-top" in CSS and "display:none!important" in CSS,
        "floating_shark_safe": ".shark-widget" in CSS and "bottom:calc(82px" in CSS,
        "shark_page_no_floating": 'data-ns-route="/shark"' in CSS,
        "no_horizontal_guard": "overflow-x:hidden" in CSS,
        "mobile_templates_marked": BASE.count("data-v836-shell") >= 1,
    }
    missing = [name for name, ok in required.items() if not ok]
    print(json.dumps({"ok": not missing, "missing": missing}, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
