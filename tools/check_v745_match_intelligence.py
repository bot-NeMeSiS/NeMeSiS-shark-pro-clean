#!/usr/bin/env python3
"""V745 Match Intelligence engine check."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.match_intelligence_engine import build_match_intelligence, match_intelligence_snapshot


def main() -> int:
    sample = {"id": "m1", "home_team": "Local", "away_team": "Visitante", "competition_name": "Liga", "kickoff_time": "20:00", "status": "UPCOMING"}
    result = build_match_intelligence(sample, [{"match_id": "m1", "market": "1X2"}])
    payload = {"ok": bool(result.get("ok") and match_intelligence_snapshot().get("ok")), "title": result.get("title"), "no_fake_data": result.get("no_fake_data")}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
