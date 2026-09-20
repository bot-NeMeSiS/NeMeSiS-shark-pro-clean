"""SIMULATED_QA: valid numeric evidence survives; non-finite scores never escape."""
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json

import pytest

from engines.realtime_state_engine import build_realtime_match_state
from engines.realtime_surface_adapter import build_live_surface_state

NOW = datetime(2026, 9, 15, 20, tzinfo=ZoneInfo("Europe/Madrid"))


def match(**overrides):
    value = dict(id="numeric-safety-qa", fixture_id="numeric-safety-qa",
                 source="provider-cache", home_team="Local QA", away_team="Visitante QA",
                 competition_name="Liga QA", kickoff_iso="2026-09-15T19:00:00+02:00",
                 status="LIVE", minute="67", home_score=1, away_score=0,
                 last_synced_at=(NOW - timedelta(seconds=30)).isoformat())
    value.update(overrides)
    return value


@pytest.mark.parametrize("invalid", ["NaN", "Infinity", "-Infinity", "1e999", float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("side", ["home", "away"])
def test_non_finite_scores_become_unknown_and_strict_json_remains_valid(invalid, side):
    raw = match(**{f"{side}_score": invalid})
    state = build_realtime_match_state(raw, now=NOW)
    card = build_live_surface_state(raw, now=NOW)
    assert state[f"score_{side}"] is None
    assert card["realtime_state"][f"score_{side}"] is None
    assert card["is_pending"] is True
    assert card["score_label"] == "Resultado pendiente"
    json.dumps(state, allow_nan=False)
    json.dumps(card, allow_nan=False)


@pytest.mark.parametrize("invalid", ["NaN", "Infinity", "-1", "not-a-score", True])
def test_invalid_numeric_pair_cannot_resurrect_an_old_display_score(invalid):
    card = build_live_surface_state(match(home_score=invalid, away_score=invalid, score="9-9"), now=NOW)
    assert card["realtime_state"]["score_home"] is None
    assert card["realtime_state"]["score_away"] is None
    assert card["score_label"] == "Resultado pendiente"
    assert card["is_pending"] is True


@pytest.mark.parametrize("value", [0, "0"])
def test_observed_zero_minute_and_zero_score_are_not_discarded(value):
    card = build_live_surface_state(match(minute=value, home_score=value, away_score=value), now=NOW)
    assert card["realtime_state"]["minute"] == "0"
    assert card["minute_label"] == "0'"
    assert card["score_label"] == "0-0" and card["is_pending"] is False


@pytest.mark.parametrize("status,age", [("FT", 30), ("LIVE", 300)])
def test_zero_minute_does_not_make_finished_or_stale_match_live(status, age):
    card = build_live_surface_state(match(status=status, minute=0,
        last_synced_at=(NOW - timedelta(seconds=age)).isoformat()), now=NOW)
    assert card["is_live"] is False and card["minute_label"] == ""
    assert card["realtime_state"]["minute"] is None


def test_raw_score_string_still_works_when_numeric_fields_are_absent():
    raw = match(score="2-0")
    del raw["home_score"], raw["away_score"]
    card = build_live_surface_state(raw, now=NOW)
    assert card["score_label"] == "2-0" and card["is_pending"] is False


def test_absent_flat_minute_preserves_nested_provider_elapsed_value():
    raw = match(minute=None, fixture={"status": {"short": "2H", "elapsed": 67}})
    card = build_live_surface_state(raw, now=NOW)
    assert card["minute_label"] == "67'"


def test_valid_input_and_nested_coverage_remain_immutable():
    raw = match(minute=0, lineups={"state": "NOT_REQUESTED", "available": False})
    original = deepcopy(raw)
    build_live_surface_state(raw, now=NOW)
    assert raw == original
