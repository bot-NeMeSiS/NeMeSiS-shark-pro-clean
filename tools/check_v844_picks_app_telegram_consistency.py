import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.telegram_quality_filter_engine import explain_telegram_filter_decision

pick = {
    "sport_key": "soccer_epl",
    "competition_name": "Premier League",
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "kickoff_iso": "2026-06-21T18:30:00+02:00",
    "selection": "Arsenal gana",
    "market": "Resultado final",
    "odds": 2.1,
    "match_id": "fixture-1",
}
decision = explain_telegram_filter_decision(pick)
ok = decision.get("allowed") and bool(pick.get("match_id")) and bool(pick.get("selection")) and bool(pick.get("odds"))
print({"ok": ok, "decision": decision})
raise SystemExit(0 if ok else 1)
