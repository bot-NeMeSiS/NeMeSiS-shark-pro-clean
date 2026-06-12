from engines.telegram_reliability_engine import explain_telegram_state
from engines.telegram_sport_filter_engine import is_telegram_football_item, telegram_sport_filter_reason


def test_football_only_blocks_nba():
    item = {"sport_key": "basketball_nba", "league_name": "NBA", "home_team": "Lakers", "away_team": "Celtics"}
    assert telegram_sport_filter_reason(item) == "deporte_no_futbol"
    assert not is_telegram_football_item(item)


def test_football_only_allows_uefa_laliga_fifa():
    assert is_telegram_football_item({"league_name": "UEFA Champions League", "sport": "Soccer"})
    assert is_telegram_football_item({"competition_name": "LaLiga", "home_team": "Barcelona", "away_team": "Real Madrid"})
    assert is_telegram_football_item({"league_name": "FIFA World Cup", "sport_key": "soccer_fifa_world_cup"})


def test_missing_chat_id_explains_configuration():
    result = explain_telegram_state({
        "env": {"bot_token_configured": True, "chat_id_configured": False},
        "counts": {},
        "reason_counts": {},
        "limits": {},
    })
    assert result["status"] == "MISSING_CHAT_ID"


def test_daily_limit_explains_blocking():
    result = explain_telegram_state({
        "env": {"bot_token_configured": True, "chat_id_configured": True},
        "counts": {"candidate_picks": 4, "football_candidates": 4, "premium_eligible": 4},
        "reason_counts": {},
        "limits": {"sent_today": 8, "max_per_day": 8, "sent_last_hour": 0, "max_per_hour": 2},
    })
    assert result["status"] == "BLOCKED_BY_DAILY_LIMIT"


def test_no_odds_explains_no_send():
    result = explain_telegram_state({
        "env": {"bot_token_configured": True, "chat_id_configured": True},
        "counts": {"candidate_picks": 3, "football_candidates": 3, "premium_eligible": 0},
        "reason_counts": {"sin_cuota_real": 3},
        "limits": {"sent_today": 0, "max_per_day": 8, "sent_last_hour": 0, "max_per_hour": 2},
    })
    assert result["status"] == "ALL_DISCARDED_NO_ODDS"
