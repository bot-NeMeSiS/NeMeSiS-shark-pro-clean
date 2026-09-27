from engines.telegram_user_preferences_engine import (
    TELEGRAM_USER_PREFERENCES_CONTRACT,
    default_telegram_user_preferences,
    destination_allows_message,
    destination_daily_limit,
    filter_candidate_for_destination,
    filter_items_for_preferences,
    global_channel_allows,
    sanitize_telegram_user_preferences,
    telegram_preference_options,
)


def test_free_is_essential_and_cannot_select_custom_leagues():
    prefs = sanitize_telegram_user_preferences(
        {},
        {
            "selected_leagues": ["laliga", "champions"],
            "message_types": ["summaries", "picks", "live"],
            "daily_limit": 9,
        },
        "FREE",
    )
    assert prefs["contract"] == TELEGRAM_USER_PREFERENCES_CONTRACT
    assert prefs["custom_leagues"] is False
    assert prefs["selected_leagues"] == []
    assert prefs["message_types"] == ["summaries"]
    assert prefs["daily_limit"] == 2


def test_pro_can_focus_leagues_types_and_daily_budget():
    prefs = sanitize_telegram_user_preferences(
        {},
        {
            "intensity": "focus",
            "selected_leagues": ["laliga", "champions", "premier"],
            "message_types": ["summaries", "picks", "results", "live"],
            "daily_limit": 4,
        },
        "PRO",
    )
    assert prefs["selection_mode"] == "selected_leagues"
    assert prefs["selected_leagues"] == ["laliga", "champions", "premier"]
    assert prefs["message_types"] == ["summaries", "picks", "results"]
    assert prefs["daily_limit"] == 4


def test_elite_can_receive_live_and_more_granular_types():
    prefs = sanitize_telegram_user_preferences(
        {},
        {
            "selected_leagues": ["laliga"],
            "message_types": ["summaries", "picks", "live", "prematch", "highlights", "combis"],
            "daily_limit": 10,
        },
        "ELITE",
    )
    assert "live" in prefs["message_types"]
    assert "prematch" in prefs["message_types"]
    assert prefs["daily_limit"] == 10


def test_private_destination_rejects_non_selected_league_and_message_type():
    prefs = sanitize_telegram_user_preferences(
        {},
        {
            "selected_leagues": ["laliga"],
            "message_types": ["summaries", "picks"],
            "daily_limit": 4,
        },
        "PRO",
    )
    dest = {"target_kind": "private", "telegram_preferences": prefs}
    premier_pick = {"competition_name": "Premier League", "selection": "Arsenal"}
    laliga_pick = {"competition_name": "LaLiga", "selection": "Real Madrid"}

    assert destination_allows_message(dest, "auto_pick", laliga_pick) == (True, "")
    assert destination_allows_message(dest, "auto_pick", premier_pick)[0] is False
    assert destination_allows_message(dest, "live_alert", laliga_pick)[0] is False


def test_global_channel_is_curated_not_event_mirror():
    assert global_channel_allows("daily_summary") is True
    assert global_channel_allows("daily_matches") is True
    assert global_channel_allows("daily_picks") is True
    assert global_channel_allows("evening_recap") is True
    for kind in ("live_alert", "prematch_reminder", "result_final", "highlight_available", "pick_alert", "auto_pick"):
        assert global_channel_allows(kind) is False


def test_daily_limits_are_hard_budgets():
    pro = {"target_kind": "private", "telegram_preferences": sanitize_telegram_user_preferences({}, {"daily_limit": 3}, "PRO")}
    elite = {"target_kind": "private", "telegram_preferences": sanitize_telegram_user_preferences({}, {"daily_limit": 9}, "ELITE")}
    channel = {"target_kind": "channel"}
    assert destination_daily_limit(pro) == 3
    assert destination_daily_limit(elite) == 9
    assert destination_daily_limit(channel) == 4


def test_summary_candidate_is_reduced_to_selected_leagues():
    prefs = sanitize_telegram_user_preferences(
        {},
        {"selected_leagues": ["champions"], "message_types": ["summaries"], "daily_limit": 3},
        "PRO",
    )
    dest = {"target_kind": "private", "telegram_preferences": prefs}
    candidate = {
        "kind": "daily_summary",
        "payload": {
            "matches": [
                {"id": "m1", "competition_name": "UEFA Champions League"},
                {"id": "m2", "competition_name": "LaLiga"},
            ]
        },
    }
    filtered, reason = filter_candidate_for_destination(candidate, dest)
    assert reason == ""
    assert [item["id"] for item in filtered["payload"]["matches"]] == ["m1"]


def test_paused_user_receives_no_automatic_private_candidate():
    prefs = sanitize_telegram_user_preferences({}, {"intensity": "paused", "pause_all": "1"}, "ELITE")
    dest = {"target_kind": "private", "telegram_preferences": prefs}
    candidate = {"kind": "pick_alert", "payload": {"pick": {"competition_name": "LaLiga"}}}
    filtered, reason = filter_candidate_for_destination(candidate, dest)
    assert filtered is None
    assert reason == "telegram_usuario_pausado"


def test_options_expose_plan_limits_without_hidden_upgrade():
    pro = telegram_preference_options("PRO")
    elite = telegram_preference_options("ELITE")
    free = telegram_preference_options("FREE")
    assert pro["custom_leagues"] is True and pro["league_limit"] == 8
    assert elite["custom_leagues"] is True and elite["league_limit"] == 15
    assert free["custom_leagues"] is False and free["league_limit"] == 0


def test_filter_items_uses_selected_league_only():
    prefs = sanitize_telegram_user_preferences({}, {"selected_leagues": ["laliga"]}, "PRO")
    rows = filter_items_for_preferences(
        [
            {"id": "a", "competition_name": "LaLiga"},
            {"id": "b", "competition_name": "Premier League"},
        ],
        prefs,
    )
    assert [item["id"] for item in rows] == ["a"]


def test_defaults_are_low_volume_by_plan():
    assert default_telegram_user_preferences("FREE")["daily_limit"] == 2
    assert default_telegram_user_preferences("PRO")["daily_limit"] == 6
    assert default_telegram_user_preferences("ELITE")["daily_limit"] == 10
