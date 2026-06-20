#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (ROOT / "templates").rglob("*.html"))

PAIRS = {
    "app_to_sports": "/partidos",
    "app_to_live": "/live",
    "app_to_picks": "/picks",
    "app_to_shark": "/shark",
    "profile_to_telegram": "/telegram",
    "profile_to_support": "/support",
    "track_record": "/track-record",
    "admin_to_client": "/sports-hub",
    "admin_to_health": "/admin/route-health",
}


def main() -> int:
    missing = [name for name, href in PAIRS.items() if href not in TEXT]
    print(json.dumps({"ok": not missing, "missing": missing}, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
