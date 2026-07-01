#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V829_MOBILE_LINKED_ECOSYSTEM_FINAL_APP_EXPERIENCE"
CURRENT_VERSION = "V833_REFERENCE_ECOSYSTEM_VISUAL_COMPLETION_FINAL"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    app = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    version_txt = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
    checks = {
        "version_v829_or_current": version_txt in {VERSION, CURRENT_VERSION} and (f"APP_VERSION = '{VERSION}'" in app or f"APP_VERSION = '{CURRENT_VERSION}'" in app),
        "v818_master_tick": "/api/automation/master-tick" in app and "v818_master_tick" in app,
        "v819_dedup": "data-v819-shell" in base and "V819" in css,
        "v820_crests": "data-v820-shell" in base and "team-crest.svg" in app,
        "v821_hotfix": "data-v821-shell" in base and "last_502_hotfix" in app,
        "v822_stability": "data-v822-shell" in base and "v822_runtime_stability_snapshot" in app,
        "v825_identity": "data-v825-shell" in base and "V825 SHARK IDENTITY" in css,
        "v827_design": "data-v827-shell" in base and "V827 REFERENCE PHOTO" in css,
        "v828_parity": "data-v828-shell" in base and "V828 REFERENCE PIXEL" in css,
        "db_path_preserved": "/data/database.db" in app,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

