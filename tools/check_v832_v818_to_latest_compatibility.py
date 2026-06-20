#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
BASE = ROOT / "templates" / "base.html"
CSS = ROOT / "static" / "app.css"
VERSION = "V832_FULL_APP_REFERENCE_VISUAL_GITHUB_RENDER_WORKFLOW_FINAL"
CURRENT_VERSION = "V833_REFERENCE_ECOSYSTEM_VISUAL_COMPLETION_FINAL"


def main() -> int:
    app = APP.read_text(encoding="utf-8", errors="replace")
    base = BASE.read_text(encoding="utf-8", errors="replace")
    css = CSS.read_text(encoding="utf-8", errors="replace")
    version_txt = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
    checks = {
        "version_v832_or_current": version_txt in {VERSION, CURRENT_VERSION} and (f"APP_VERSION = '{VERSION}'" in app or f"APP_VERSION = '{CURRENT_VERSION}'" in app),
        "v818_master_tick": "/api/automation/master-tick" in app and "daily_automation_engine" in app,
        "v819_dedup": "data-v819-shell" in base and "V819" in css,
        "v820_crests": "data-v820-shell" in base and "team-crest.svg" in app,
        "v821_hotfix": "data-v821-shell" in base and "last_502_hotfix" in app,
        "v822_stability": "data-v822-shell" in base and "v822_runtime_stability_snapshot" in app,
        "v827_design": "data-v827-shell" in base and "V827 REFERENCE PHOTO" in css,
        "v828_parity": "data-v828-shell" in base and "V828 REFERENCE PIXEL" in css,
        "v829_mobile": "data-v829-shell" in base and "V829 MOBILE LINKED ECOSYSTEM EXPERIENCE START" in css,
        "v830_bottom_nav": "data-v830-shell" in base and "V830 MOBILE BOTTOM NAV PIXEL QA START" in css,
        "v832_final": "data-v832-shell" in base and "V832 FULL APP REFERENCE VISUAL GITHUB RENDER WORKFLOW START" in css,
        "db_path_preserved": "/data/database.db" in app,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
