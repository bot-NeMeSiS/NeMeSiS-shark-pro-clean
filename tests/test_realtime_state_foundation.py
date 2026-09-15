from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from engines.realtime_state_engine import (
    REALTIME_CHANGE_CONTRACT,
    REALTIME_STATE_CONTRACT,
    build_realtime_match_state,
    build_realtime_state_snapshot,
    compare_realtime_match_state,
)

MADRID = ZoneInfo("Europe/Madrid")


def _match(now: datetime, *, status: str = "LIVE", match_id: str = "rt-1") -> dict:
    return {
        "id": match_id,
        "match_id": match_id,
        "fixture_id": match_id,
        "competition_id": "100",
        "season": "2026",
        "home_team_id": "10",
        "away_team_id": "20",
        "home_team": "NeMeSiS Azul",
        "away_team": "NeMeSiS Dorado",
        "competition_name": "Liga QA",
        "match_date": now.date().isoformat(),
        "kickoff_time": "20:00",
        "source": "provider-cache",
        "status": status,
        "home_score": 1,
        "away_score": 0,
        "minute": "67",
        "last_synced_at": (now - timedelta(seconds=30)).isoformat(),
    }


def test_live_state_delegates_to_sports_truth_and_exposes_provenance():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    state = build_realtime_match_state(_match(now), now=now)

    assert state["contract"] == REALTIME_STATE_CONTRACT
    assert state["sports_truth_contract"] == "MATCH-STATUS-TRUTH-V2"
    assert state["status_canonical"] == "LIVE"
    assert state["is_live"] is True
    assert state["is_stale"] is False
    assert state["minute"] == "67"
    assert state["provider"] == "provider-cache"
    assert state["provider_observed_at_source"] == "last_synced_at"
    assert state["freshness_seconds"] == 30
    assert state["freshness_state"] == "FRESH"
    assert state["confidence_state"] == "CURRENT"


def test_stale_live_never_remains_realtime_live():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    match = _match(now, match_id="rt-stale")
    match["last_synced_at"] = (now - timedelta(minutes=5)).isoformat()

    state = build_realtime_match_state(match, now=now)

    assert state["status_canonical"] == "STALE"
    assert state["is_live"] is False
    assert state["is_stale"] is True
    assert state["minute"] is None
    assert state["freshness_state"] == "STALE"
    assert state["confidence_state"] == "DEGRADED"
    assert state["stale_reason"] == "LIVE_EVIDENCE_TOO_OLD"


def test_finished_signal_wins_and_live_minute_is_hidden():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    match = _match(now, match_id="rt-finished")
    match["strProgress"] = "FT"

    state = build_realtime_match_state(match, now=now)

    assert state["status_canonical"] == "FINISHED"
    assert state["is_live"] is False
    assert state["is_finished"] is True
    assert state["minute"] is None
    assert state["status_conflict"] is True
    assert state["confidence_state"] == "CONFLICT"


def test_generic_updated_at_does_not_become_provider_observation_clock():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    match = _match(now, match_id="rt-generic-clock")
    match.pop("last_synced_at")
    match["updated_at"] = (now - timedelta(seconds=10)).isoformat()

    state = build_realtime_match_state(match, now=now)

    assert state["provider_observed_at"] == ""
    assert state["provider_observed_at_source"] == ""
    assert state["is_live"] is False
    assert state["is_stale"] is True
    assert state["freshness_state"] == "STALE"
    assert state["confidence_state"] == "DEGRADED"


def test_partial_score_is_preserved_as_unknown_not_invented_zero():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    match = _match(now, status="NS", match_id="rt-partial-score")
    match["home_score"] = 2
    match["away_score"] = None
    match["score"] = ""

    state = build_realtime_match_state(match, now=now)

    assert state["score_home"] == 2
    assert state["score_away"] is None
    assert state["minute"] is None


def test_capabilities_distinguish_available_empty_unavailable_and_unknown():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    match = _match(now, status="NS", match_id="rt-coverage")
    match.update(
        {
            "events": [{"type": "goal"}],
            "lineups": [],
            "stats_available": False,
            "standings_available": True,
        }
    )

    state = build_realtime_match_state(match, now=now)
    coverage = state["coverage"]

    assert coverage["events"] == {"state": "AVAILABLE", "available": True, "observed": True, "count": 1}
    assert coverage["lineups"] == {"state": "EMPTY_OBSERVED", "available": False, "observed": True, "count": 0}
    assert coverage["stats"]["state"] == "UNAVAILABLE"
    assert coverage["standings"]["state"] == "AVAILABLE"
    assert coverage["odds"]["state"] == "NOT_ESTABLISHED"
    assert coverage["odds"]["observed"] is False


def test_snapshot_counts_live_stale_finished_conflict_and_unknown_freshness():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    live = _match(now, match_id="snap-live")
    stale = _match(now, match_id="snap-stale")
    stale["last_synced_at"] = (now - timedelta(minutes=5)).isoformat()
    finished = _match(now, match_id="snap-finished")
    finished["status"] = "FT"
    finished["minute"] = ""
    upcoming_unknown = _match(now, status="NS", match_id="snap-upcoming")
    upcoming_unknown.pop("last_synced_at")

    snapshot = build_realtime_state_snapshot([live, stale, finished, upcoming_unknown], now=now)

    assert snapshot["counts"] == {
        "total": 4,
        "live": 1,
        "finished": 1,
        "stale": 1,
        "conflicted": 0,
        "freshness_not_established": 1,
    }


def test_change_detector_reports_only_same_fixture_factual_changes():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    before = build_realtime_match_state(_match(now, match_id="change-1"), now=now)
    current_match = _match(now + timedelta(seconds=20), match_id="change-1")
    current_match["home_score"] = 2
    current_match["minute"] = "68"
    after = build_realtime_match_state(current_match, now=now + timedelta(seconds=20))

    diff = compare_realtime_match_state(before, after)

    assert diff["contract"] == REALTIME_CHANGE_CONTRACT
    assert diff["same_fixture"] is True
    assert diff["changed"] is True
    fields = {change["field"] for change in diff["changes"]}
    assert "score_home" in fields
    assert "minute" in fields
    assert "provider_observed_at" in fields


def test_change_detector_never_compares_different_fixture_ids():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    before = build_realtime_match_state(_match(now, match_id="one"), now=now)
    after = build_realtime_match_state(_match(now, match_id="two"), now=now)

    diff = compare_realtime_match_state(before, after)

    assert diff["same_fixture"] is False
    assert diff["changed"] is False
    assert diff["changes"] == []


def test_realtime_projection_is_pure_and_does_not_mutate_input():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    match = _match(now, match_id="pure")
    match["coverage"] = {"events": {"state": "AVAILABLE", "count": 2}}
    before = deepcopy(match)

    build_realtime_match_state(match, now=now)
    build_realtime_state_snapshot([match], now=now)

    assert match == before
