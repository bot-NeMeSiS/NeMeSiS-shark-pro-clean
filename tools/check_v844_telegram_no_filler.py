import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.telegram_quality_filter_engine import filter_telegram_candidates

weak = [
    {"sport_key": "basketball_nba", "competition_name": "NBA", "home_team": "A", "away_team": "B", "kickoff_iso": "2026-06-21T20:00:00+02:00"},
    {"sport_key": "soccer", "competition_name": "Regional Amateur League", "home_team": "Village A", "away_team": "Village B", "kickoff_iso": "2026-06-21T20:00:00+02:00"},
    {"sport_key": "soccer", "competition_name": "U21 Friendly", "home_team": "Youth A", "away_team": "Youth B", "kickoff_iso": "2026-06-21T20:00:00+02:00"},
]
allowed = filter_telegram_candidates(weak)
payload = {"ok": allowed == [], "allowed_count": len(allowed), "expected_status": "skipped_no_top_matches"}
print(payload)
raise SystemExit(0 if payload["ok"] else 1)
