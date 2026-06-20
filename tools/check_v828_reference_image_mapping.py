#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "V828_REFERENCE_IMAGE_TO_SCREEN_MAPPING.md"


def main() -> int:
    text = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    lower = text.lower()
    required = {
        "dashboard/panel de control": ["dashboard", "panel de control"],
        "Telegram command center": ["telegram command center"],
        "pagos/membresias/pricing": ["pagos", "membres", "pricing"],
        "centro de automatizacion": ["automatiz"],
        "data marketplace/data center": ["data marketplace", "data center"],
        "picks y partidos": ["picks", "partidos"],
        "home/app cliente": ["home", "app cliente"],
        "directo/live": ["directo", "live"],
        "detalle partido": ["detalle partido"],
        "historico/track record": ["hist", "track record"],
        "mi cuenta/profile": ["profile"],
        "Telegram cliente": ["telegram cliente"],
        "soporte": ["soporte"],
    }
    missing = [label for label, needles in required.items() if not all(needle in lower for needle in needles)]
    ok = not missing
    print(json.dumps({"ok": ok, "missing": missing}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


