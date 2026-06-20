#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    base = read("templates/base.html")
    css = read("static/app.css")
    checks = {
        "single_topbar": base.count('class="top ns-topbar"') == 1,
        "single_bottom_nav": base.count('bottom-nav bottom-nav-clean') == 1,
        "single_shark_widget": base.count('class="shark-widget"') == 1,
        "admin_client_nav_separated": "current_user.role == 'ADMIN'" in base and "current_user.role != 'ADMIN'" in base,
        "shark_hidden_on_page": '[data-ns-route="/shark"] .shark-widget' in css,
        "mobile_390_guard": "@media(max-width:560px)" in css and "bottom-nav-clean a" in css,
        "support_profile_logout_visible": all(token in base for token in ["/support", "/mi-cuenta", "/logout"]),
        "legacy_rails_hidden": all(token in css for token in [".v798-client-rail", ".v799-client-rail", ".client-sidebar"]),
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

