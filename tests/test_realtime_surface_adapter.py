from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from engines.realtime_surface_adapter import build_live_surface_collection, build_live_surface_state

MADRID = ZoneInfo("Europe/Madrid")


def _match(now: datetime, *, match_id: str = "surface-1", status: str = "LIVE") -> dict:
    return {
        "id": match_id,
        "match_id": match_id,
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
        "score": "1-0",
        "minute": "67",
        "last_synced_at": (now - timedelta(seconds=30)).isoformat(),
    }


def test_live_surface_exposes_canonical_realtime_state_without_losing_legacy_keys():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    card = build_live_surface_state(_match(now), now=now)

    assert card["id"] == "surface-1"
    assert card["home"] == "Local QA"
    assert card["away"] == "Visitante QA"
    assert card["score_label"] == "1-0"
    assert card["is_live"] is True
    assert card["status_canonical"] == "LIVE"
    assert card["realtime_contract"] == "NEMESIS-REALTIME-STATE-V1"
    assert card["realtime_state"]["sports_truth_contract"] == "MATCH-STATUS-TRUTH-V2"
    assert card["freshness_state"] == "FRESH"
    assert card["confidence_state"] == "CURRENT"


def test_stale_live_card_is_fail_closed_and_hides_minute_label():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    match = _match(now, match_id="surface-stale")
    match["last_synced_at"] = (now - timedelta(minutes=5)).isoformat()

    card = build_live_surface_state(match, now=now)

    assert card["is_live"] is False
    assert card["is_stale"] is True
    assert card["status_canonical"] == "STALE"
    assert card["minute_label"] == ""
    assert card["data_state"] == "Datos retrasados"
    assert card["freshness_state"] == "STALE"


def test_terminal_conflict_never_survives_as_public_live_card():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    match = _match(now, match_id="surface-conflict")
    match["strProgress"] = "FT"

    card = build_live_surface_state(match, now=now)

    assert card["is_live"] is False
    assert card["is_finished"] is True
    assert card["realtime_state"]["status_conflict"] is True
    assert card["confidence_state"] == "CONFLICT"


def test_collection_counts_live_stale_and_conflicted_separately():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    live = _match(now, match_id="collection-live")
    stale = _match(now, match_id="collection-stale")
    stale["last_synced_at"] = (now - timedelta(minutes=5)).isoformat()
    conflict = _match(now, match_id="collection-conflict")
    conflict["strProgress"] = "FT"

    result = build_live_surface_collection([live, stale, conflict], now=now)

    assert result["contract"] == "NEMESIS-LIVE-SURFACE-V1"
    assert result["counts"] == {"input": 3, "live": 1, "stale": 1, "conflicted": 1}
    assert [card["id"] for card in result["live_cards"]] == ["collection-live"]


def test_adapter_is_pure_and_does_not_mutate_match_input():
    now = datetime(2026, 9, 15, 20, 0, tzinfo=MADRID)
    match = _match(now, match_id="surface-pure")
    match["coverage"] = {"events": {"state": "AVAILABLE", "count": 2}}
    before = deepcopy(match)

    build_live_surface_state(match, now=now)
    build_live_surface_collection([match], now=now)

    assert match == before
