from engines.telegram_sport_filter_engine import (
    is_telegram_football_item,
    telegram_sport_filter_reason,
    telegram_sport_mode_summary,
)


def test_telegram_blocks_basketball_context():
    item = {
        "sport_key": "basketball_nba",
        "competition_name": "NBA",
        "home_team": "Los Angeles Lakers",
        "away_team": "Boston Celtics",
    }
    assert is_telegram_football_item(item) is False
    assert telegram_sport_filter_reason(item) == "deporte_no_futbol"


def test_telegram_allows_football_context():
    item = {
        "sport_key": "soccer_fifa_world_cup",
        "competition_name": "Mundial FIFA",
        "home_team": "Canadá",
        "away_team": "Bosnia y Herzegovina",
    }
    assert is_telegram_football_item(item) is True
    assert telegram_sport_filter_reason(item) == ""


def test_telegram_sport_mode_defaults_to_football_only():
    summary = telegram_sport_mode_summary({})
    assert summary["mode"] == "football_only"
    assert summary["football_only"] is True
