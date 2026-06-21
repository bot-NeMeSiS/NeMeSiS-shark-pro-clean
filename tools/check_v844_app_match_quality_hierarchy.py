import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.telegram_quality_filter_engine import telegram_match_quality_score

top = {"competition_name": "Champions League", "home_team": "Real Madrid", "away_team": "PSG", "kickoff_iso": "2026-06-21T21:00:00+02:00"}
weak = {"competition_name": "Regional Amateur League", "home_team": "A", "away_team": "B", "kickoff_iso": "2026-06-21T21:00:00+02:00"}
ok = telegram_match_quality_score(top) > telegram_match_quality_score(weak)
print({"ok": ok, "top_score": telegram_match_quality_score(top), "weak_score": telegram_match_quality_score(weak)})
raise SystemExit(0 if ok else 1)
