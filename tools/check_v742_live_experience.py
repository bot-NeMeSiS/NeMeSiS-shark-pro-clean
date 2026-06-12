#!/usr/bin/env python3
"""Static/runtime QA for V742 Live experience."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.live_experience_engine import build_live_experience, live_experience_snapshot  # noqa: E402


def main() -> int:
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
    sample = [
        {"id": "1", "home_team": "Sevilla", "away_team": "Betis", "competition_name": "LaLiga", "madrid_time": "21:00", "live_depth": {"badge": "live", "label": "En directo", "minute": "55'"}},
        {"id": "2", "home_team": "Arsenal", "away_team": "Chelsea", "competition_name": "Premier League", "madrid_time": "18:30", "live_depth": {"badge": "upcoming", "label": "Próximo"}},
    ]
    built = build_live_experience(sample, lane="live")
    snap = live_experience_snapshot(app_version=version)
    result = {"ok": snap.get("ok") and built["counts"]["live"] == 1 and built["filtered"] == 1, "snapshot": snap, "sample": built}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
