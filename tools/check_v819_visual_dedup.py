#!/usr/bin/env python3
"""V819 visual layer deduplication checks."""
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
        "single_topbar_markup": base.count('class="top ns-topbar"') == 1,
        "single_bottom_nav_markup": len(re.findall(r'<nav[^>]+class="[^"]*bottom-nav-clean', base)) == 1,
        "single_shark_widget_markup": base.count('class="shark-widget"') == 1,
        "single_app_css_link": base.count("app.css") == 1,
        "body_v819_active": 'data-v819-shell="true"' in base,
        "old_client_action_layers_hidden": ".v811-top-actions" in css and ".v812-top-actions" in css and "display:none!important" in css,
        "old_session_pills_hidden": ".v797-session-pills" in css and "display:none!important" in css,
        "old_client_rails_hidden": ".v798-client-rail" in css and ".v812-client-rail" in css,
        "admin_dock_hidden": ".v808-admin-dock" in css and ".ns-admin" in css,
        "admin_bottom_nav_hidden": ".ns-admin .bottom-nav-clean" in css,
        "shark_hidden_on_shark_page": 'data-ns-route="/shark"' in css and ".shark-widget" in css,
        "corrupt_icon_pseudo_neutralized": ".nav-clean a::before" in css and "content:none!important" in css,
        "legacy_todo_hidden_or_replaced": 'href="/support"' in base or 'a[href="/app/mapa"]' in css,
        "support_visible": 'href="/support"' in base,
    }
    failed = [name for name, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


