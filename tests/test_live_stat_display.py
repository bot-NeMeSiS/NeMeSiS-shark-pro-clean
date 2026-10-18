from __future__ import annotations

import sqlite3

from engines.api_football_live_tracker_engine import (
    _field_state,
    _pressure_from_stats,
    _stat_cards,
    _stats_for_fixture,
    ensure_live_tracker_schema,
    live_tracker_summaries_for_matches,
)
from engines.match_context_engine import _real_statistics


def _team(team_id: str, name: str, stats: dict) -> dict:
    return {
        "team_id": team_id,
        "team": name,
        "stats": {
            key: {"label": label, "value": value, "numeric": numeric}
            for key, (label, value, numeric) in stats.items()
        },
        "raw": [],
    }


def test_fixture_stats_group_by_provider_team_id_and_keep_raw_metric_names(tmp_path):
    path = str(tmp_path / "stats.sqlite")
    ensure_live_tracker_schema(path)
    with sqlite3.connect(path) as conn:
        rows = [
            ("a", "fixture-1", "20", "Granada", "Fouls", "7", 7),
            ("b", "fixture-1", "10", "Granada", "Fouls", "12", 12),
        ]
        conn.executemany(
            "INSERT INTO api_football_live_stats(id,fixture_id,team_id,team_name,stat_name,stat_value,numeric_value) VALUES (?,?,?,?,?,?,?)",
            rows,
        )

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        result = _stats_for_fixture(conn, "fixture-1")
    finally:
        conn.close()
    assert len(result["teams"]) == 2
    assert {team["team_id"] for team in result["teams"]} == {"10", "20"}


def test_team_ids_win_over_alphabetical_names_and_optional_provider_stats_render():
    stats = {
        "available": True,
        "teams": [
            _team("20", "A Away", {
                "possession": ("Ball Possession", "39%", 39),
                "fouls": ("Fouls", "14", 14),
                "throw_ins": ("Throw-ins", "9", 9),
            }),
            _team("10", "Z Home", {
                "possession": ("Ball Possession", "61%", 61),
                "fouls": ("Fouls", "8", 8),
                "throw_ins": ("Throw-ins", "12", 12),
            }),
        ],
    }

    cards = _stat_cards(stats, "Local", "Visitante", "10", "20")
    by_key = {card["key"]: card for card in cards}
    assert by_key["possession"]["home"] == "61%"
    assert by_key["possession"]["away"] == "39%"
    assert by_key["fouls"]["home"] == "8"
    assert by_key["throw_ins"]["label"] == "Saques de banda"
    assert by_key["throw_ins"]["home"] == "12"


def test_conflicting_team_names_cannot_override_fixture_team_ids():
    stats = {
        "available": True,
        "teams": [
            _team("10", "Granada", {"fouls": ("Fouls", "7", 7)}),
            _team("20", "Rival", {"fouls": ("Fouls", "12", 12)}),
        ],
    }
    cards = _stat_cards(stats, "Rival", "Granada", "10", "20")
    assert cards[0]["home"] == "7"
    assert cards[0]["away"] == "12"


def test_field_keeps_possession_separate_from_derived_pressure_and_keeps_real_zeroes():
    stats = {
        "available": True,
        "teams": [
            _team("20", "Visitante", {
                "possession": ("Ball Possession", "100%", 100),
                "attacks": ("Attacks", "0", 0),
                "dangerous_attacks": ("Dangerous Attacks", "0", 0),
                "corners": ("Corner Kicks", "2", 2),
            }),
            _team("10", "Local", {
                "possession": ("Ball Possession", "0%", 0),
                "shots_on_goal": ("Shots on Goal", "1", 1),
                "attacks": ("Attacks", "0", 0),
                "dangerous_attacks": ("Dangerous Attacks", "0", 0),
                "corners": ("Corner Kicks", "0", 0),
            }),
        ],
    }
    pressure = _pressure_from_stats(stats, "Local", "Visitante", "10", "20")
    field = _field_state(stats, [], pressure, "Local", "Visitante", "10", "20")

    assert field["possession_available"] is True
    assert field["home_possession_pct"] == 0
    assert field["away_possession_pct"] == 100
    assert "Ataques peligrosos 0-0" in field["chips"]
    assert "Córners 0-2" in field["chips"]
    assert "Posesión 0-100%" in field["chips"]
    assert pressure["home_pct"] != field["home_possession_pct"]


def test_match_context_never_invents_missing_or_one_sided_possession():
    one_sided = _real_statistics({"provider": "api_football", "stat_cards": [
        {"key": "possession", "label": "Posesión", "home": "61%", "away": None},
    ]}, {})
    no_possession = _real_statistics({"provider": "api_football", "pressure": {
        "available": True, "home_pct": 80, "away_pct": 20,
    }, "stat_cards": [
        {"key": "fouls", "label": "Faltas", "home": "0", "away": "3"},
    ]}, {})

    assert one_sided["possession"]["available"] is False
    assert no_possession["possession"]["available"] is False


def test_directo_summaries_use_only_cached_statistics_and_are_read_only(tmp_path):
    path = tmp_path / "tracker.sqlite"
    ensure_live_tracker_schema(str(path))
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO api_football_live_snapshots(fixture_id,match_id,home_team_id,away_team_id,home_team,away_team,status_short,last_synced_at) VALUES (?,?,?,?,?,?,?,?)",
            ("777", "af-777", "10", "20", "Granada", "Rival", "2H", "2026-10-17T16:00:00Z"),
        )
        conn.executemany(
            "INSERT INTO api_football_live_stats(id,fixture_id,team_id,team_name,stat_name,stat_value,numeric_value,captured_at) VALUES (?,?,?,?,?,?,?,?)",
            [
                ("s1", "777", "10", "Granada", "Ball Possession", "61%", 61, "2026-10-17T16:01:00Z"),
                ("s2", "777", "20", "Rival", "Ball Possession", "39%", 39, "2026-10-17T16:01:00Z"),
                ("s3", "777", "10", "Granada", "Fouls", "8", 8, "2026-10-17T16:01:00Z"),
                ("s4", "777", "20", "Rival", "Fouls", "14", 14, "2026-10-17T16:01:00Z"),
            ],
        )

    before = path.read_bytes()
    summaries = live_tracker_summaries_for_matches(str(path), [{"id": "af-777", "external_id": "777"}])
    after = path.read_bytes()
    tracker = summaries["af-777"]
    assert tracker["read_only"] is True
    assert tracker["external_calls"] == 0
    assert tracker["source_label"] == "API-Football"
    assert tracker["field_state"]["home_possession_pct"] == 61
    assert tracker["field_state"]["away_possession_pct"] == 39
    assert tracker["statistics_updated_at"] == "2026-10-17T16:01:00Z"
    assert all("raw" not in team for team in tracker["stats"]["teams"])
    assert before == after


def test_directo_card_renders_cached_stats_with_provider_timestamp(app_module):
    tracker = {
        "provider": "api_football",
        "source_label": "API-Football Pro",
        "statistics_updated_at": "2026-10-17T16:01:00Z",
        "updated_at": "2026-10-17T16:01:00Z",
        "stats": {"available": True},
        "stat_cards": [
            {"key": "shots_on_goal", "label": "Tiros a puerta", "home": "5", "away": "2"},
            {"key": "fouls", "label": "Faltas", "home": "8", "away": "14"},
            {"key": "corners", "label": "Córners", "home": "4", "away": "1"},
        ],
        "field_state": {
            "possession_available": True,
            "home_possession_pct": 61,
            "away_possession_pct": 39,
        },
    }
    match = {
        "id": "af-777",
        "home_team": "Granada",
        "away_team": "Rival",
        "safe_home": "Granada",
        "safe_away": "Rival",
        "competition_name": "Liga",
        "kickoff_time": "20:30",
        "source": "api_football_live",
        "home_score": 1,
        "away_score": 0,
        "api_football_live_tracker": tracker,
        "realtime_state": {
            "contract": "NEMESIS-REALTIME-STATE-V1",
            "sports_truth_contract": "MATCH-STATUS-TRUTH-V2",
            "is_live": True,
            "is_stale": False,
            "status_conflict": False,
            "status_canonical": "LIVE",
            "minute": 61,
            "fixture_id": "777",
            "freshness_state": "fresh",
            "provider_observed_at": "2026-10-17T16:02:00Z",
            "evaluated_at_madrid": "2026-10-17T18:02:00+02:00",
        },
    }

    with app_module.app.test_request_context("/directo"):
        template = app_module.app.jinja_env.from_string(
            "{% from 'components/realtime_live_card.html' import live_card %}{{ live_card(match) }}")
        rendered = template.render(match=match)
    assert "v934-live-stats" in rendered
    assert "Granada: 61%. Rival: 39%." in rendered
    assert "Tiros a puerta" in rendered and "Faltas" in rendered and "Córners" in rendered
    assert "API-Football" in rendered
    assert "API-Football Pro" not in rendered
    assert "2026-10-17T16:01:00Z" in rendered

