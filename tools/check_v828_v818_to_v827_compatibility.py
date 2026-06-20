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
        "v818_master_tick": "/api/automation/master-tick" in app and "v818_master_tick" in app,
        "v819_dedup": "data-v819-shell" in base and "V819 REFERENCE UI DEDUP" in css,
        "v820_crests": "data-v820-shell" in base and "V820 REAL CRESTS" in css,
        "v821_hotfix": "data-v821-shell" in base and "last_502_hotfix" in app,
        "v822_stability": "data-v822-shell" in base and "v822_runtime_stability_snapshot" in app,
        "v823_visual": "data-v823-shell" in base,
        "v824_visual": "data-v824-shell" in base,
        "v825_identity": "data-v825-shell" in base and "V825 SHARK IDENTITY" in css,
        "v826_screen": "data-v826-shell" in base and "V826 FULL REFERENCE EXPERIENCE" in css,
        "v827_design": "data-v827-shell" in base and "V827 REFERENCE PHOTO REBUILD DESIGN SYSTEM" in css,
        "db_path_preserved": 'DB_PATH = os.getenv("DB_PATH", "/data/database.db")' in app or "/data/database.db" in app,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


