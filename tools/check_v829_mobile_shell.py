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
        "body_marker": "data-v829-shell" in base,
        "mobile_quick_links": "v829-mobile-quick" in base and all(h in base for h in ["/profile", "/telegram", "/favorites", "/track-record", "/support"]),
        "bottom_nav_unique": base.count('class="bottom-nav bottom-nav-clean"') == 1,
        "mobile_breakpoints": "@media(max-width:768px)" in css and "@media(max-width:430px)" in css,
        "safe_area": "env(safe-area-inset-bottom" in css,
        "desktop_rail_hidden_mobile": ".v828-client-rail" in css and "display:none!important" in css,
        "admin_no_client_bottom_nav": "body[data-v829-shell=\"true\"].ns-admin .bottom-nav-clean" in css,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

