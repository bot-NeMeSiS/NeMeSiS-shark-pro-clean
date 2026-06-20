#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
BASE = ROOT / "templates" / "base.html"
CSS = ROOT / "static" / "app.css"


def main() -> int:
    app = APP.read_text(encoding="utf-8", errors="replace")
    base = BASE.read_text(encoding="utf-8", errors="replace")
    css = CSS.read_text(encoding="utf-8", errors="replace")
    checks = {
        "v818_master_tick": "/api/automation/master-tick" in app and "daily_automation_engine" in app,
        "v819_dedup": "data-v819-shell" in base and "V819 REFERENCE UI DEDUP LAYER PURGE START" in css,
        "v820_crests": "data-v820-shell" in base and "V820 REAL CRESTS REFERENCE VISUAL PIXEL POLISH START" in css,
        "v821_hotfix": "data-v821-shell" in base and "last_502_hotfix" in app,
        "v822_stability": "data-v822-shell" in base and "V822 PRODUCTION STABILITY RUNTIME AUTOMATION CRESTS START" in css,
        "v827_design": "data-v827-shell" in base and "V827 REFERENCE PHOTO REBUILD DESIGN SYSTEM START" in css,
        "v828_reference": "data-v828-shell" in base and "V828 REFERENCE PIXEL PARITY FULL ECOSYSTEM START" in css,
        "v829_mobile": "data-v829-shell" in base and "V829 MOBILE LINKED ECOSYSTEM EXPERIENCE START" in css,
        "v830_runtime": "data-v830-shell" in base and "V830 MOBILE BOTTOM NAV PIXEL QA START" in css,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
