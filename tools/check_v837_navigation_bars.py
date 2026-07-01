#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")


def main() -> int:
    checks = {
        "topbar": "ns-topbar" in BASE,
        "client_bottom_nav": "bottom-nav-clean" in BASE and "repeat(5" in CSS,
        "mobile_centered": "left:50%" in CSS and "translateX(-50%)" in CSS,
        "client_rail": "v828-client-rail" in BASE,
        "admin_rail": "v808-admin-rail" in BASE,
        "admin_no_client_nav": ".ns-admin :is(.bottom-nav-clean,.shark-widget,.v825-public-floating-shark)" in CSS,
        "scroll_top_mobile_hidden": ".ns-scroll-top" in CSS and "display:none!important" in CSS,
    }
    missing = [k for k, v in checks.items() if not v]
    print(json.dumps({"ok": not missing, "missing": missing}, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
