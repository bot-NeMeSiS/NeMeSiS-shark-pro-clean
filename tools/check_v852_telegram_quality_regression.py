from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.telegram_quality_filter_engine import is_blocked_telegram_competition, filter_telegram_candidates


def main():
    assert is_blocked_telegram_competition({"sport_key": "basketball_nba", "competition_name": "NBA"}) is True
    assert is_blocked_telegram_competition({"competition_name": "U19 Regional Youth"}) is True
    assert filter_telegram_candidates([], limit=3) == []
    print("V852 Telegram quality regression OK")


if __name__ == "__main__":
    main()
