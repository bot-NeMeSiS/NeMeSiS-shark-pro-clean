#!/usr/bin/env python3
"""Static QA for V741 calendar search experience."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.calendar_experience_engine import calendar_experience_snapshot  # noqa: E402


def main() -> int:
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
    snap = calendar_experience_snapshot(app_version=version)
    print(json.dumps(snap, ensure_ascii=False, indent=2))
    return 0 if snap.get("status") == "CALENDARIO_PREMIUM_LISTO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
