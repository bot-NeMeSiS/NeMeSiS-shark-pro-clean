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
        "single_topbar_markup": base.count('class="top ns-topbar"') == 1,
        "single_bottom_nav_markup": base.count('bottom-nav bottom-nav-clean') == 1,
        "single_shark_widget_markup": base.count('class="shark-widget"') == 1,
        "client_admin_nav_separated": "current_user.role == 'ADMIN'" in base and "current_user.role != 'ADMIN'" in base,
        "shark_hidden_on_shark_page": '[data-ns-route="/shark"] .shark-widget' in css,
        "legacy_client_rails_hidden": all(token in css for token in [".v798-client-rail", ".v799-client-rail", ".client-sidebar"]),
        "mobile_bottom_nav_defined": "grid-template-columns:repeat(5" in css and "bottom-nav-clean" in css,
        "logout_visible": "/logout" in base,
        "profile_visible": "/mi-cuenta" in base,
        "support_visible": "/support" in base,
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


