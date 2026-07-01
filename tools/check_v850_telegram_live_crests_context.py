from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.telegram_quality_filter_engine import filter_telegram_candidates, telegram_match_quality_score
from engines.live_match_experience_engine import build_live_card_payload


def main():
    assert telegram_match_quality_score({"competition_name": "Premier League", "home_team": "Arsenal", "away_team": "Chelsea", "sport": "football"}) >= 0
    assert filter_telegram_candidates([{"sport": "basketball", "competition_name": "NBA", "home_team": "A", "away_team": "B"}]) == []
    live = build_live_card_payload({"home_team": "Arsenal", "away_team": "Chelsea", "status": "LIVE", "home_score": 1, "away_score": 1})
    assert live["score_label"] == "1-1"
    print("check_v850_telegram_live_crests_context OK")


if __name__ == "__main__":
    main()
