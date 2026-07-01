import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.telegram_quality_filter_engine import explain_telegram_filter_decision, filter_telegram_candidates

cases = [
    ("champions", {"sport_key": "soccer_uefa_champs_league", "competition_name": "Champions League", "home_team": "Real Madrid", "away_team": "Bayern", "kickoff_iso": "2026-06-21T21:00:00+02:00"}, True),
    ("premier", {"sport_key": "soccer_epl", "competition_name": "Premier League", "home_team": "Liverpool", "away_team": "Arsenal", "kickoff_iso": "2026-06-21T18:30:00+02:00"}, True),
    ("nba", {"sport_key": "basketball_nba", "competition_name": "NBA", "home_team": "Lakers", "away_team": "Celtics", "kickoff_iso": "2026-06-21T03:00:00+02:00"}, False),
    ("youth", {"sport_key": "soccer", "competition_name": "U19 Youth League", "home_team": "Club A U19", "away_team": "Club B U19", "kickoff_iso": "2026-06-21T17:00:00+02:00"}, False),
    ("reserves", {"sport_key": "soccer", "competition_name": "Reserve League", "home_team": "Team Reserves", "away_team": "Other Reserves", "kickoff_iso": "2026-06-21T17:00:00+02:00"}, False),
    ("regional", {"sport_key": "soccer", "competition_name": "Regional District League", "home_team": "Local A", "away_team": "Local B", "kickoff_iso": "2026-06-21T17:00:00+02:00"}, False),
    ("weak_foreign_second", {"sport_key": "soccer", "competition_name": "Second Division Minor Country", "home_team": "Unknown A", "away_team": "Unknown B", "kickoff_iso": "2026-06-21T17:00:00+02:00"}, False),
    ("segunda_relevant", {"sport_key": "soccer_spain_segunda_division", "competition_name": "Segunda División", "home_team": "Deportivo La Coruña", "away_team": "Real Zaragoza", "kickoff_iso": "2026-06-21T17:00:00+02:00"}, True),
]

results = []
for name, item, expected in cases:
    decision = explain_telegram_filter_decision(item)
    results.append({"case": name, "expected": expected, "allowed": bool(decision.get("allowed")), "decision": decision})

no_filler = filter_telegram_candidates([cases[2][1], cases[3][1], cases[5][1]])
ok = all(row["expected"] == row["allowed"] for row in results) and no_filler == []
print({"ok": ok, "results": results, "no_filler_count": len(no_filler)})
raise SystemExit(0 if ok else 1)
