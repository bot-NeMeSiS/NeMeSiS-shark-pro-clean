#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "templates" / "base.html"
CSS = ROOT / "static" / "app.css"
TEMPLATES = ROOT / "templates"


def main() -> int:
    base = BASE.read_text(encoding="utf-8", errors="replace")
    css = CSS.read_text(encoding="utf-8", errors="replace")
    templates = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in TEMPLATES.glob("*.html"))
    checks = {
        "single_bottom_nav": base.count('class="bottom-nav bottom-nav-clean"') == 1,
        "single_shark_widget": base.count('class="shark-widget"') == 1,
        "v833_marker": "V833 REFERENCE ECOSYSTEM VISUAL COMPLETION START" in css,
        "v830_scroll_fix": "body[data-v830-shell=\"true\"] .ns-scroll-top" in css,
        "admin_separated": 'body[data-v833-shell="true"].ns-admin' in css,
        "no_broken_title_literal": "{{ title or 'NeMeSiS SHARK PRO' }}" not in templates,
        "no_known_mojibake": not any(x in templates for x in ["Espa?a", "Andaluc?a", "top mundal"]),
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
