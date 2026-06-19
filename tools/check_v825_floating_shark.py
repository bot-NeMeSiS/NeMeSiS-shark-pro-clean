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
        "single_authenticated_widget_markup": base.count('class="shark-widget"') == 1,
        "public_floating_anchor": 'class="v825-public-floating-shark"' in base and 'href="/shark"' in base,
        "tooltip_present": 'title="Abrir SHARK"' in base and 'aria-label="Abrir SHARK"' in base,
        "admin_excluded": "current_user.role != 'ADMIN'" in base and ".ns-admin .v825-public-floating-shark" in css,
        "shark_page_hidden": '[data-ns-route="/shark"] .shark-widget' in css and '[data-ns-route="/shark"] .v825-public-floating-shark' in css,
        "safe_area": "env(safe-area-inset-bottom)" in css and "env(safe-area-inset-right)" in css,
        "pointer_events_safe": "pointer-events:none" in css and "pointer-events:auto" in css,
        "no_legacy_extra_widgets": base.count('id="sharkFab"') == 1 and base.count('id="sharkWidget"') == 1,
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
