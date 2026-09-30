from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from engines.realtime_change_summary_engine import build_factual_change_summary
from engines.realtime_state_engine import build_realtime_match_state

MADRID = ZoneInfo("Europe/Madrid")


def _match(now: datetime, *, match_id: str = "change-qa", status: str = "LIVE") -> dict:
    return {
        "id": match_id,
        "fixture_id": match_id,
        "match_date": now.date().isoformat(),
        "kickoff_time": "20:00",
        "home_team": "Local QA",
        "away_team": "Visitante QA",
        "competition_name": "Liga QA",
        "source": "provider-cache",
        "status": status,
        "home_score": 1,
        "away_score": 0,
        "minute": "67",
        "last_synced_at": (now - timedelta(seconds=30)).isoformat(),
    }


def test_score_change_is_factual_update_not_invented_goal():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    before = build_realtime_match_state(_match(now), now=now)
    changed = _match(now + timedelta(seconds=20))
    changed["home_score"] = 2
    after = build_realtime_match_state(changed, now=now + timedelta(seconds=20))

    result = build_factual_change_summary(before, after)

    score_event = next(event for event in result["events"] if event["code"] == "SCORE_UPDATE")
    assert score_event["message"] == "Marcador actualizado: 1-0 → 2-0."
    assert "gol" not in score_event["message"].casefold()


def test_status_transition_to_live_is_reported_without_betting_inference():
    now = datetime(2026, 9, 15, 19, 59, tzinfo=MADRID)
    upcoming_match = _match(now, status="NS")
    upcoming_match["match_date"] = now.date().isoformat()
    upcoming_match["kickoff_time"] = "20:00"
    upcoming_match.pop("minute")
    before = build_realtime_match_state(upcoming_match, now=now)

    live_match = _match(now + timedelta(minutes=2))
    after = build_realtime_match_state(live_match, now=now + timedelta(minutes=2))

    result = build_factual_change_summary(before, after)

    messages = " ".join(event["message"] for event in result["events"])
    assert "En directo" in messages
    assert "apuesta" not in messages.casefold()
    assert "probabilidad" not in messages.casefold()


def test_capability_becoming_available_is_reported():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    before = build_realtime_match_state(_match(now), now=now)
    after_match = _match(now + timedelta(seconds=20))
    after_match["lineups"] = [{"team": "Local QA"}]
    after = build_realtime_match_state(after_match, now=now + timedelta(seconds=20))

    result = build_factual_change_summary(before, after)

    event = next(event for event in result["events"] if event["code"] == "CAPABILITY_AVAILABLE")
    assert event["message"] == "Alineaciones disponibles."


def test_stale_transition_is_high_importance_and_does_not_claim_live():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    before = build_realtime_match_state(_match(now), now=now)
    stale_match = _match(now + timedelta(minutes=5))
    stale_match["last_synced_at"] = now.isoformat()
    after = build_realtime_match_state(stale_match, now=now + timedelta(minutes=5))

    result = build_factual_change_summary(before, after)

    event = next(event for event in result["events"] if event["code"] == "FRESHNESS_CHANGE")
    assert event["importance"] == "HIGH"
    assert "perdido frescura" in event["message"]
    assert after["is_live"] is False


def test_recovery_from_stale_is_reported_without_reconstructing_events():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    stale_match = _match(now)
    stale_match["last_synced_at"] = (now - timedelta(minutes=5)).isoformat()
    before = build_realtime_match_state(stale_match, now=now)
    fresh_match = _match(now + timedelta(seconds=20))
    after = build_realtime_match_state(fresh_match, now=now + timedelta(seconds=20))

    result = build_factual_change_summary(before, after)

    assert any(event["code"] == "FRESHNESS_CHANGE" and "vuelve" in event["message"] for event in result["events"])
    assert not any(event["code"] == "GOAL" for event in result["events"])


def test_different_fixtures_are_never_compared():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    before = build_realtime_match_state(_match(now, match_id="fixture-a"), now=now)
    after = build_realtime_match_state(_match(now, match_id="fixture-b"), now=now)

    result = build_factual_change_summary(before, after)

    assert result["same_fixture"] is False
    assert result["changed"] is False
    assert result["events"] == []


def test_identical_states_return_no_changes():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    state = build_realtime_match_state(_match(now), now=now)

    result = build_factual_change_summary(state, state)

    assert result["same_fixture"] is True
    assert result["changed"] is False
    assert result["headline"] == "Sin cambios relevantes"
