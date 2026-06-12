#!/usr/bin/env python3
"""V745 deep data foundations check."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.team_form_engine import team_form_snapshot
from engines.standings_experience_engine import standings_snapshot


def main() -> int:
    matches = [{"home_team": "A", "away_team": "B", "score": "2-1", "status": "FT"}, {"home_team": "C", "away_team": "A", "score": "0-0", "status": "FT"}]
    form = team_form_snapshot(matches, "A")
    standings = standings_snapshot([])
    result = {"ok": bool(form.get("ok") and standings.get("ok")), "form_matches": form.get("matches"), "standings_status": standings.get("status")}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
