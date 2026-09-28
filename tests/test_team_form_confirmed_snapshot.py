"""Shared recent-form evidence: no provider access and no provisional outcomes."""
from __future__ import annotations

import copy
import socket
from unittest.mock import patch

import pytest

from engines.team_form_engine import team_form_snapshot


def recorded(n=1, **changes):
    value = dict(id=f"qa-{n}", external_id=f"event-{n}", source="api_football_cache",
                 home_team="Club QA", away_team=f"Rival {n}", home_score=0,
                 away_score=0, status="FT", competition_id="140", season="2026-2027",
                 kickoff_iso=f"2026-09-{n:02d}T20:00:00+02:00")
    value.update(changes)
    return value


@pytest.mark.parametrize("status", ["NS", "LIVE", "HT", "POSTPONED", "SUSPENDED", "CANCELLED", "ABANDONED", "RESULT_PENDING", ""])
def test_non_final_rows_are_not_recent_form(status):
    snapshot = team_form_snapshot([recorded(status=status)], "Club QA")
    assert snapshot["matches_found"] == 0
    assert snapshot["form_available"] is False
    assert snapshot["form"] == snapshot["last_matches"] == snapshot["results"] == []
    assert snapshot["omitted_count"] == 1
    assert snapshot["omissions"]


@pytest.mark.parametrize("changes", [dict(), dict(home_score=None, away_score=None, score="0-0"), dict(home_score=0.0, away_score="0")])
def test_final_zero_is_a_real_draw(changes):
    snapshot = team_form_snapshot([recorded(**changes)], "Club QA")
    assert snapshot["form"] == ["D"]
    assert snapshot["matches_found"] == snapshot["sample_size"] == 1
    assert snapshot["results"][0]["home_score"] == snapshot["results"][0]["away_score"] == 0
    assert snapshot["results"][0]["href"] == "/match/qa-1"


@pytest.mark.parametrize("value", [-1, 1.5, True, False, float("inf"), float("nan"), "1.5", "null", [], {}, "-1"])
def test_invalid_score_is_excluded_not_truncated(value):
    snapshot = team_form_snapshot([recorded(home_score=value)], "Club QA")
    assert not snapshot["form_available"]
    assert snapshot["goals_for"] == snapshot["goals_against"] == 0


def test_five_most_recent_not_first_five_or_entire_season():
    snapshot = team_form_snapshot([recorded(n) for n in range(1, 8)], "Club QA")
    assert [row["id"] for row in snapshot["last_matches"]] == ["qa-7", "qa-6", "qa-5", "qa-4", "qa-3"]
    assert snapshot["valid_loaded_results"] == 7
    assert snapshot["matches_found"] == snapshot["requested_sample_size"] == 5
    assert snapshot["draws"] == 5 and snapshot["wins"] == snapshot["losses"] == 0
    assert snapshot["season_complete"] is False and snapshot["expected_played"] is None
    assert snapshot["coverage_state"] == "LOADED_SAMPLE_ONLY"


def test_team_side_and_score_order_remain_distinct():
    snapshot = team_form_snapshot([recorded(home_team="Rival", away_team="Club QA", home_score=2, away_score=0)], "Club QA")
    assert snapshot["form"] == ["L"]
    assert snapshot["goals_for"] == 0 and snapshot["goals_against"] == 2
    assert snapshot["results"][0]["home_score"] == 2


def test_ambiguous_duplicates_do_not_become_a_result():
    snapshot = team_form_snapshot([recorded(), recorded(home_score=3)], "Club QA")
    assert not snapshot["form_available"]
    assert snapshot["omissions"]["conflicting_records"] == 2


def test_equivalent_provider_duplicate_is_counted_once():
    snapshot = team_form_snapshot([recorded(), recorded(id="second-local-id")], "Club QA")
    assert snapshot["matches_found"] == 1
    assert snapshot["omissions"]["duplicate_rows"] == 1


def test_sorting_uses_absolute_instant_in_madrid_fold():
    snapshot = team_form_snapshot([recorded(1, kickoff_iso="2025-10-26T02:50:00+02:00"),
                                   recorded(2, kickoff_iso="2025-10-26T02:10:00+01:00")], "Club QA")
    assert [row["id"] for row in snapshot["last_matches"]] == ["qa-2", "qa-1"]


@pytest.mark.parametrize("changes", [dict(is_fake=True), dict(is_demo=True), dict(simulated=True), dict(kickoff_iso=None), dict(home_team="Other"), dict(id=None, external_id=None)])
def test_missing_identity_date_or_fake_data_not_counted(changes):
    assert not team_form_snapshot([recorded(**changes)], "Club QA")["form_available"]


@pytest.mark.parametrize("rows,team", [(None,"Club QA"), ([],"Club QA"), ({},"Club QA"), ([None,42],"Club QA"), ([recorded()],""), ([recorded()],None)])
def test_empty_or_invalid_input_has_honest_empty_state(rows, team):
    snapshot = team_form_snapshot(rows, team)
    assert snapshot["ok"] and not snapshot["form_available"]
    assert snapshot["sample_size"] == 0 and snapshot["external_calls"] == 0


def test_never_opens_network_and_preserves_input():
    original = [recorded(1), recorded(2,status="LIVE")]
    before = copy.deepcopy(original)
    with patch.object(socket, "create_connection", side_effect=AssertionError("unexpected network")):
        snapshot = team_form_snapshot(original,"Club QA")
    assert original == before
    snapshot["last_matches"][0]["home_score"] = 100
    assert original == before


def test_round_and_mixed_season_never_claim_a_season_total():
    snapshot = team_form_snapshot([recorded(1,round=7),recorded(2,season="2025-2026")],"Club QA")
    assert snapshot["matches_found"] == 2 and snapshot["expected_played"] is None
    assert snapshot["scope"] == "RECENT_LOADED_RESULTS_ALL_COMPETITIONS"
