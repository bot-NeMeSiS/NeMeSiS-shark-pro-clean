#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    base = read("templates/base.html")
    css = read("static/app.css")
    checks = {
        "single_topbar": base.count('class="top ns-topbar"') == 1,
        "single_bottom_nav": len(re.findall(r'<nav[^>]+class="[^"]*bottom-nav-clean', base)) == 1,
        "single_shark_widget": base.count('class="shark-widget"') == 1,
        "admin_bottom_nav_hidden": ".ns-admin .bottom-nav-clean" in css,
        "shark_hidden_on_shark_page": 'data-ns-route="/shark"' in css and ".shark-widget" in css,
        "old_rails_hidden": ".v798-client-rail" in css and ".v812-client-rail" in css,
        "corrupt_icons_neutralized": ".nav-clean a::before" in css and "content:none!important" in css,
        "support_visible": 'href="/support"' in base,
        "logout_visible": 'href="/logout"' in base,
        "crest_size_controlled": ".crest.v820-crest" in css and "contain: layout paint" in css,
        "no_horizontal_overflow_intent": "overflow-x:hidden" in css or "overflow-x: hidden" in css,
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


