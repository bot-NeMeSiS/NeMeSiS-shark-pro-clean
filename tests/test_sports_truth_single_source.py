from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import sqlite3
from zoneinfo import ZoneInfo

import pytest

from engines.live_experience_engine import state_bucket
from engines.live_match_experience_engine import (
    build_live_card_payload,
    get_score_label,
    get_match_status_label,
    normalize_live_match,
)
from engines.api_football_live_tracker_engine import (
    LIVE_STATUS_SHORT,
    _live_tracker_matches_from_conn,
    _upsert_fixture,
    ensure_live_tracker_schema,
)
from engines.sports_domain_model_engine import normalize_match_entity
from engines.v934_realtime_sports_engine import build_realtime_snapshot, normalize_match
from engines.v935_launch_trust_engine import (
    match_status_truth,
    normalize_match_lifecycle,
)


MADRID = ZoneInfo("Europe/Madrid")


def _live_match(now: datetime, match_id: str = "single-truth-live") -> dict:
    return {
        "id": match_id,
        "match_id": match_id,
        "match_date": now.date().isoformat(),
        "kickoff_time": "20:00",
        "home_team": "Equipo local",
        "away_team": "Equipo visitante",
        "competition_name": "Liga de prueba",
        "source": "persisted-provider-cache",
        "status": "LIVE",
        "minute": "67",
        "home_score": 1,
        "away_score": 0,
        "score": "1-0",
        "last_synced_at": (now - timedelta(seconds=30)).isoformat(),
    }


def _summary(match: dict) -> dict:
    return {
        "all_valid_matches": [match],
        "valid_matches_today": [match],
        "valid_upcoming_matches": [match],
        "valid_live_events": [match],
        "valid_active_picks": [],
        "finished_matches": [],
        "incident_matches": [],
        "incomplete_matches": [],
        "raw_matches_count": 1,
    }


def test_last_synced_at_is_the_canonical_live_freshness_clock():
    now = datetime(2026, 9, 5, 20, 0, tzinfo=MADRID)
    fresh = _live_match(now)
    stale = {**fresh, "last_synced_at": (now - timedelta(minutes=5)).isoformat()}

    fresh_truth = match_status_truth(fresh, now=now)
    stale_truth = match_status_truth(stale, now=now)

    assert fresh_truth["is_live"] is True
    assert fresh_truth["live_timestamp_source"] == "last_synced_at"
    assert stale_truth["lifecycle"] == "STALE"
    assert stale_truth["is_live"] is False
    assert stale_truth["stale_reason"] == "LIVE_EVIDENCE_TOO_OLD"


def test_provider_progress_terminal_signal_wins_over_live_status():
    truth = match_status_truth(
        {
            "status": "LIVE",
            "strProgress": "FT",
            "home_score": 2,
            "away_score": 1,
        }
    )

    assert truth["lifecycle"] == "FINISHED"
    assert truth["is_live"] is False
    assert truth["status_conflict"] is True
    assert truth["conflict_type"] == "LIVE_TERMINAL"


def test_generic_updated_at_cannot_rejuvenate_provider_live_evidence():
    now = datetime(2026, 9, 5, 20, 0, tzinfo=MADRID)
    match = _live_match(now, "generic-cache-clock")
    match.pop("last_synced_at")
    match["updated_at"] = (now - timedelta(seconds=10)).isoformat()

    truth = match_status_truth(match, now=now)
    normalized = normalize_live_match(match)
    realtime = normalize_match(match, now=now)

    assert truth["lifecycle"] == "STALE"
    assert truth["is_live"] is False
    assert truth["stale_reason"] == "LIVE_TIMESTAMP_MISSING"
    assert truth["live_timestamp_source"] == ""
    assert normalized["live_updated_at"] == ""
    assert normalized["provider_updated_at"] == ""
    assert realtime is not None and realtime["is_stale"] is True


def test_anomalous_future_provider_timestamp_is_fail_closed():
    now = datetime(2026, 9, 5, 20, 0, tzinfo=MADRID)
    match = {
        **_live_match(now, "future-provider-clock"),
        "last_synced_at": (now + timedelta(minutes=15)).isoformat(),
    }

    truth = match_status_truth(match, now=now)

    assert truth["lifecycle"] == "STALE"
    assert truth["is_live"] is False
    assert truth["stale_reason"] == "LIVE_TIMESTAMP_IN_FUTURE"
    assert truth["live_timestamp_in_future"] is True


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("HT", "HALFTIME"),
        ("ET", "LIVE"),
        ("P", "LIVE"),
        ("AET", "FINISHED"),
        ("PEN", "FINISHED"),
        ("RESULT_PENDING", "RESULT_PENDING"),
        ("SUSP", "SUSPENDED"),
        ("INT", "SUSPENDED"),
        ("POSTPONED", "POSTPONED"),
    ],
)
def test_provider_specific_pause_extra_time_penalties_and_suspension(status, expected):
    payload = {"status": status, "home_score": 1, "away_score": 1}

    truth = match_status_truth(payload)

    assert truth["lifecycle"] == expected
    assert truth["is_live"] is (expected in {"LIVE", "HALFTIME"})


def test_past_kickoff_and_score_do_not_infer_finished(app_module):
    now = datetime(2026, 9, 5, 20, 0, tzinfo=MADRID)
    match = {
        **_live_match(now, "score-without-terminal"),
        "status": "",
        "match_date": "2026-09-04",
        "kickoff_time": "20:00",
        "home_score": 2,
        "away_score": 1,
        "score": "2-1",
    }

    truth = match_status_truth(match, now=now)
    canonical = app_module.canonical_match_status(match)
    domain = app_module.canonical_match_for_domain_context(match)

    assert truth["lifecycle"] == "RESULT_PENDING"
    assert truth["is_finished"] is False
    assert canonical["is_result_pending"] is True
    assert canonical["is_finished"] is False
    assert domain["status"] == "TBD"
    assert normalize_match_lifecycle(match, now=now) == "RESULT_PENDING"
    assert app_module.sportsdb_match_status({"strStatus": "RESULT_PENDING"}) == "RESULT_PENDING"


def test_partial_score_is_never_completed_with_an_invented_zero(app_module):
    assert get_score_label({"status": "LIVE", "home_score": 2, "away_score": None}) == "Resultado pendiente"
    assert get_score_label({"status": "NS", "home_score": None, "away_score": 1}) == "VS"
    assert app_module.sportsdb_score(2, None) == ""
    assert app_module.sportsdb_score(None, 1) == ""
    assert app_module.sportsdb_score(0, 0) == "0-0"


def test_sports_truth_is_pure_and_does_not_mutate_nested_input():
    now = datetime(2026, 9, 5, 20, 0, tzinfo=MADRID)
    match = {
        **_live_match(now, "pure-helper"),
        "fixture": {"status": {"short": "2H"}},
        "freshness": {"is_stale": False},
    }
    before = deepcopy(match)

    match_status_truth(match, now=now)

    assert match == before


def test_suspended_state_stays_non_live_across_public_adapters(app_module):
    match = {
        "id": "suspended-cross-surface",
        "match_id": "suspended-cross-surface",
        "match_date": "2026-09-05",
        "kickoff_time": "20:00",
        "home_team": "Equipo local",
        "away_team": "Equipo visitante",
        "competition_name": "Liga de prueba",
        "source": "provider-cache",
        "status": "SUSP",
        "home_score": 1,
        "away_score": 0,
    }

    truth = match_status_truth(match)
    canonical = app_module.canonical_match_status(match)
    realtime = normalize_match(match)

    assert truth["lifecycle"] == "SUSPENDED"
    assert truth["is_live"] is False
    assert canonical["key"] == "SUSPENDED"
    assert canonical["label"] == "Suspendido"
    assert realtime is not None and realtime["status"] == "suspended"
    assert state_bucket(match) == "postponed"


def test_data_confidence_cannot_be_high_for_stale_unknown_or_conflicting_match(app_module):
    now = datetime.now(MADRID)
    stale = {
        **_live_match(now, "confidence-stale"),
        "last_synced_at": (now - timedelta(minutes=5)).isoformat(),
        "venue": "Estadio",
    }
    unknown_clock = {
        **_live_match(now, "confidence-unknown-clock"),
        "status": "NS",
    }
    unknown_clock.pop("last_synced_at")
    conflicting = {
        **_live_match(now, "confidence-conflict"),
        "match_status": "FT",
    }

    stale_confidence = app_module.get_v937_nemesis_data_confidence(stale)
    unknown_confidence = app_module.get_v937_nemesis_data_confidence(unknown_clock)
    conflicting_confidence = app_module.get_v937_nemesis_data_confidence(conflicting)

    assert stale_confidence["score"] <= 49
    assert stale_confidence["label"] == "Insuficiente"
    assert stale_confidence["limit_reason"] == "STATUS_EVIDENCE_UNSAFE"
    assert unknown_confidence["score"] <= 69
    assert unknown_confidence["label"] != "Alta"
    assert unknown_confidence["limit_reason"] == "PROVIDER_TIMESTAMP_UNKNOWN"
    assert conflicting_confidence["score"] <= 49
    assert conflicting_confidence["label"] == "Insuficiente"


def test_realtime_snapshot_delegates_live_and_stale_to_sports_truth():
    now = datetime(2026, 9, 5, 20, 0, tzinfo=MADRID)
    fresh = _live_match(now, "fresh-realtime")
    stale = {
        **_live_match(now, "stale-realtime"),
        "last_synced_at": (now - timedelta(minutes=5)).isoformat(),
    }
    normalized_fresh = normalize_match(fresh, now=now)
    normalized_stale = normalize_match(stale, now=now)
    snapshot = build_realtime_snapshot(
        {
            "valid_matches_today": [fresh, stale],
            "valid_upcoming_matches": [],
            "valid_active_picks": [],
        },
        now=now,
    )

    assert normalized_fresh is not None and normalized_fresh["is_live"] is True
    assert normalized_stale is not None and normalized_stale["is_live"] is False
    assert normalized_stale["is_stale"] is True
    assert [item["id"] for item in snapshot["live"]] == ["fresh-realtime"]
    assert [item["id"] for item in snapshot["stale_live"]] == ["stale-realtime"]
    assert snapshot["counts"]["live"] == 1
    assert snapshot["counts"]["stale_live"] == 1


def test_calendar_cannot_restore_stale_live_from_legacy_live_depth(app_module):
    now = datetime.now(MADRID)
    stale = {
        **_live_match(now, "calendar-stale-live"),
        "last_synced_at": (now - timedelta(minutes=5)).isoformat(),
        "live_depth": {
            "state": "LIVE",
            "badge": "live",
            "label": "En directo",
            "minute": "88'",
            "score": "1-0",
        },
    }
    summary = _summary(stale)

    with app_module.app.test_request_context("/calendar?lane=live"):
        live_calendar = app_module.v940_calendar_context(
            summary,
            "live",
            now.date().isoformat(),
        )
    with app_module.app.test_request_context("/calendar?lane=week"):
        week_calendar = app_module.v940_calendar_context(
            summary,
            "week",
            now.date().isoformat(),
        )

    assert live_calendar["matches"] == []
    assert live_calendar["counts"]["live"] == 0
    assert len(week_calendar["matches"]) == 1
    calendar_match = week_calendar["matches"][0]
    assert calendar_match["status_info"]["is_live"] is False
    assert calendar_match["status_info"]["is_stale"] is True
    assert "directo" not in calendar_match["calendar_status"].lower()
    assert calendar_match["calendar_time"] != "88'"


def test_one_match_keeps_the_same_live_truth_across_public_adapters(app_module):
    now = datetime.now(MADRID)
    match = _live_match(now, "cross-surface-live")
    truth = match_status_truth(match, now=now)
    realtime = normalize_match(match, now=now)
    client = app_module.client_match_display_context(match, now_madrid=now)
    card = build_live_card_payload(match)

    assert truth["is_live"] is True
    assert realtime is not None and realtime["is_live"] is True
    assert client["status_info"]["is_live"] is True
    assert client["client_live_minute"] == "67"
    assert card["is_live"] is True
    assert card["minute_label"] == "67'"
    assert {truth["contract"], realtime["status_truth"]["contract"], client["status_info"]["contract"]} == {
        "MATCH-STATUS-TRUTH-V2"
    }


def test_sportsdb_provider_clock_survives_persistence_and_converter_is_read_only(
    app_module,
    monkeypatch,
    tmp_path,
):
    db_path = tmp_path / "sportsdb-clock.sqlite"
    monkeypatch.setattr(app_module, "DB_PATH", str(db_path), raising=False)
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", None, raising=False)
    monkeypatch.setattr(app_module, "_SEEDING_DB_PATH", None, raising=False)
    app_module.init_db()
    cache_calls = []
    monkeypatch.setattr(
        app_module,
        "cache_sportsdb_event_team",
        lambda *args, **kwargs: cache_calls.append((args, kwargs)),
    )
    event = {
        "idEvent": "provider-clock-1",
        "strSport": "Soccer",
        "strHomeTeam": "Real Madrid",
        "strAwayTeam": "FC Barcelona",
        "strLeague": "Liga real",
        "dateEvent": "2026-09-05",
        "strTime": "20:00:00",
        "strStatus": "LIVE",
        "strProgress": "2H",
        "intHomeScore": "0",
        "intAwayScore": "1",
    }

    read_only = app_module.sportsdb_event_to_match(event)
    assert read_only is not None
    assert read_only["last_synced_at"] == ""
    assert cache_calls == []

    observed_at = datetime.now(MADRID).isoformat()
    persisted = app_module.sportsdb_event_to_match(
        event,
        provider_observed_at=observed_at,
        cache_teams=True,
    )
    assert persisted is not None
    assert len(cache_calls) == 2
    app_module.upsert_sportsdb_matches([persisted])

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = dict(conn.execute("SELECT * FROM matches WHERE id=?", (persisted["id"],)).fetchone())
    finally:
        conn.close()

    assert row["last_synced_at"] == observed_at
    assert row["score"] == "0-1"
    assert match_status_truth(row)["is_live"] is True


def test_api_football_clock_and_scores_survive_tracker_to_matches(
    app_module,
    monkeypatch,
    tmp_path,
):
    db_path = tmp_path / "api-football-clock.sqlite"
    monkeypatch.setattr(app_module, "DB_PATH", str(db_path), raising=False)
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", None, raising=False)
    monkeypatch.setattr(app_module, "_SEEDING_DB_PATH", None, raising=False)
    app_module.init_db()
    ensure_live_tracker_schema(str(db_path))

    def fixture(fixture_id, home_score, away_score):
        return {
            "fixture": {
                "id": fixture_id,
                "date": datetime.now(MADRID).isoformat(),
                "status": {"short": "2H", "long": "Second Half", "elapsed": 67},
            },
            "league": {"id": 140, "name": "La Liga", "country": "Spain", "season": 2026},
            "teams": {
                "home": {"id": 1, "name": "Equipo A", "logo": ""},
                "away": {"id": 2, "name": "Equipo B", "logo": ""},
            },
            "goals": {"home": home_score, "away": away_score},
        }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        _upsert_fixture(conn, fixture(1001, 0, 1))
        _upsert_fixture(conn, fixture(1002, 2, None))
        conn.commit()
        complete = dict(conn.execute("SELECT * FROM matches WHERE id='af-1001'").fetchone())
        partial = dict(conn.execute("SELECT * FROM matches WHERE id='af-1002'").fetchone())
        tracker_rows = {item["id"]: item for item in _live_tracker_matches_from_conn(conn)}
    finally:
        conn.close()

    assert complete["last_synced_at"]
    assert complete["score"] == "0-1"
    assert match_status_truth(complete)["is_live"] is True
    assert partial["score"] in {None, ""}
    assert tracker_rows["af-1001"]["score"] == "0-1"
    assert tracker_rows["af-1002"]["score"] == ""
    assert tracker_rows["af-1001"]["last_synced_at"]


def test_domain_model_delegates_live_truth_and_never_uses_generic_updated_at():
    now = datetime.now(MADRID)
    raw = {
        **_live_match(now, "domain-clock"),
        "external_id": "domain-clock-provider",
        "kickoff_iso": now.isoformat(),
    }
    raw.pop("last_synced_at")
    raw["updated_at"] = now.isoformat()

    unsafe = normalize_match_entity(raw, now_madrid=now.isoformat())
    safe_timestamp = (now - timedelta(seconds=20)).isoformat()
    safe = normalize_match_entity(
        {**raw, "last_synced_at": safe_timestamp},
        now_madrid=now.isoformat(),
    )

    assert unsafe["status"] != "live"
    assert unsafe["freshness"]["state"] == "stale"
    assert unsafe["source_timestamp"] is None
    assert unsafe["status_truth"]["stale_reason"] == "LIVE_TIMESTAMP_MISSING"
    assert safe["status"] == "live"
    assert safe["freshness"]["usable_for_live"] is True
    assert safe["source_timestamp"] == safe_timestamp


def test_upcoming_confidence_is_capped_for_old_or_future_provider_clock(app_module):
    now = datetime.now(MADRID)
    base = {
        "id": "upcoming-clock-quality",
        "match_date": (now + timedelta(days=1)).date().isoformat(),
        "kickoff_time": "20:00",
        "home_team": "Equipo A",
        "away_team": "Equipo B",
        "competition_name": "Liga real",
        "source": "provider-cache",
        "status": "NS",
    }

    old = app_module.get_v937_nemesis_data_confidence(
        {**base, "last_synced_at": (now - timedelta(days=2)).isoformat()}
    )
    future = app_module.get_v937_nemesis_data_confidence(
        {**base, "last_synced_at": (now + timedelta(hours=2)).isoformat()}
    )

    assert old["score"] <= 49
    assert old["limit_reason"] == "EVIDENCE_STALE"
    assert future["score"] <= 49
    assert future["limit_reason"] == "EVIDENCE_TIMESTAMP_IN_FUTURE"


@pytest.mark.parametrize("status", ["SUSP", "INT"])
def test_suspended_api_status_is_never_counted_or_labelled_live(status):
    assert status not in LIVE_STATUS_SHORT
    assert get_match_status_label({"status": status}) == "Suspendido"
    assert match_status_truth({"status": status})["is_live"] is False
