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
        "v828_shell_marker": "data-v828-shell" in base,
        "v828_comment": "NEMESIS V828 REFERENCE PIXEL PARITY FULL ECOSYSTEM ACTIVE" in base,
        "v828_css": "V828 REFERENCE PIXEL PARITY FULL ECOSYSTEM START" in css,
        "one_client_rail_markup": base.count("v828-client-rail") == 1,
        "single_bottom_nav_markup": base.count('class="bottom-nav bottom-nav-clean"') == 1,
        "single_shark_widget_markup": base.count('class="shark-widget"') == 1,
        "no_literal_title": "{{ title or 'NeMeSiS SHARK PRO' }}" not in base,
        "shark_core_no_public_float": "'/shark-core'" in base,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


