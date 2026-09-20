"""Calendar history must come from persisted matches, never invented provider data."""
from __future__ import annotations


def _empty_summary():
    return {
        "all_valid_matches": [],
        "valid_upcoming_matches": [],
        "valid_matches_today": [],
        "valid_live_events": [],
        "valid_active_picks": [],
        "finished_matches": [],
        "incident_matches": [],
        "incomplete_matches": [],
        "raw_matches_count": 0,
        "safe_message": "Sin snapshot actual para la fecha solicitada.",
        "provider_status": "NOT_REQUESTED",
    }


def _persist(app_module, match_id, match_date, *, home_score=None, away_score=None, status="FT"):
    row = {
        "id": match_id,
        "external_id": match_id,
        "home_team": "Celta de Vigo",
        "away_team": "Racing de Santander",
        "competition_id": "4335",
        "competition_key": "laliga",
        "competition_name": "LaLiga EA Sports",
        "league_name": "LaLiga EA Sports",
        "country": "Spain",
        "round": "7",
        "match_date": match_date,
        "kickoff_time": "18:30",
        "match_time": "18:30",
        "kickoff_iso": f"{match_date}T18:30:00+02:00",
        "status": status,
        "home_score": home_score,
        "away_score": away_score,
        "score": (
            f"{home_score}-{away_score}"
            if home_score is not None and away_score is not None
            else ""
        ),
        "source": "PERSISTED_HISTORY_QA",
        "last_synced_at": f"{match_date}T20:30:00+02:00",
        "raw_json": "{}",
    }
    result = app_module.upsert_sportsdb_matches([row])
    assert result["inserted"] + result["updated"] == 1


def _prepare_db(app_module, tmp_path, monkeypatch):
    db_path = tmp_path / "calendar-history.sqlite"
    monkeypatch.setattr(app_module, "DB_PATH", str(db_path))
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(app_module, "_SEEDING_DB_PATH", None)
    app_module.init_db()
    monkeypatch.setattr(
        app_module,
        "today_iso",
        lambda offset=0: {
            -1: "2026-09-19",
            0: "2026-09-20",
            1: "2026-09-21",
        }.get(offset, "2026-09-20"),
    )


def test_past_calendar_date_reads_persisted_match_and_keeps_match_center(
    app_module, tmp_path, monkeypatch
):
    _prepare_db(app_module, tmp_path, monkeypatch)
    _persist(app_module, "history-final-1", "2026-09-19", home_score=2, away_score=1)

    with app_module.app.test_request_context("/calendar?lane=today&date=2026-09-19"):
        summary = app_module._v940_calendar_with_persisted_history(
            _empty_summary(), "today", "2026-09-19"
        )
        calendar = app_module.v940_calendar_context(summary, "today", "2026-09-19")

    assert calendar["history_status"] == "PERSISTED_DB"
    assert calendar["external_calls"] == 0
    assert calendar["database_written"] is False
    assert [item["id"] for item in calendar["matches"]] == ["history-final-1"]
    item = calendar["matches"][0]
    assert str(item["home_score"]) == "2"
    assert str(item["away_score"]) == "1"
    assert item["status_info"]["is_finished"] is True
    assert item["status_info"]["is_live"] is False
    assert item["has_pick"] is False
    assert item["id"] == "history-final-1"


def test_past_calendar_never_turns_missing_score_into_zero_zero(
    app_module, tmp_path, monkeypatch
):
    _prepare_db(app_module, tmp_path, monkeypatch)
    _persist(app_module, "history-pending-1", "2026-09-19", home_score=None, away_score=None)

    with app_module.app.test_request_context("/calendar?lane=today&date=2026-09-19"):
        summary = app_module._v940_calendar_with_persisted_history(
            _empty_summary(), "today", "2026-09-19"
        )
        calendar = app_module.v940_calendar_context(summary, "today", "2026-09-19")

    assert calendar["history_status"] == "PERSISTED_DB"
    assert len(calendar["matches"]) == 1
    item = calendar["matches"][0]
    assert item.get("home_score") in (None, "")
    assert item.get("away_score") in (None, "")
    assert str(item.get("score") or "").replace(" ", "") != "0-0"


def test_finished_lane_reads_bounded_persisted_history(
    app_module, tmp_path, monkeypatch
):
    _prepare_db(app_module, tmp_path, monkeypatch)
    _persist(app_module, "history-final-older", "2026-09-18", home_score=3, away_score=0)
    _persist(app_module, "history-final-yesterday", "2026-09-19", home_score=1, away_score=1)

    with app_module.app.test_request_context("/calendar?lane=finished&date=2026-09-19"):
        summary = app_module._v940_calendar_with_persisted_history(
            _empty_summary(), "finished", "2026-09-19"
        )
        calendar = app_module.v940_calendar_context(summary, "finished", "2026-09-19")

    ids = {item["id"] for item in calendar["matches"]}
    assert {"history-final-older", "history-final-yesterday"} <= ids
    assert calendar["history_status"] == "PERSISTED_DB"
    assert calendar["history_date"] == "2026-09-19"


def test_calendar_api_uses_the_same_persisted_history_snapshot(
    app_module, tmp_path, monkeypatch
):
    _prepare_db(app_module, tmp_path, monkeypatch)
    _persist(app_module, "history-api-1", "2026-09-19", home_score=4, away_score=2)

    monkeypatch.setattr(
        app_module,
        "v932_safe_dashboard_data",
        lambda *args, **kwargs: ({}, _empty_summary()),
    )

    response = app_module.app.test_client().get(
        "/api/calendar?lane=today&date=2026-09-19"
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["calendar"]["history_status"] == "PERSISTED_DB"
    assert payload["calendar"]["external_calls"] == 0
    assert [item["id"] for item in payload["matches"]] == ["history-api-1"]
    assert str(payload["matches"][0]["home_score"]) == "4"
    assert str(payload["matches"][0]["away_score"]) == "2"


def test_past_scheduled_match_without_score_becomes_result_pending(
    app_module, tmp_path, monkeypatch
):
    _prepare_db(app_module, tmp_path, monkeypatch)
    _persist(
        app_module,
        "history-result-pending",
        "2026-09-19",
        home_score=None,
        away_score=None,
        status="NS",
    )

    with app_module.app.test_request_context("/calendar?lane=today&date=2026-09-19"):
        summary = app_module._v940_calendar_with_persisted_history(
            _empty_summary(), "today", "2026-09-19"
        )
        calendar = app_module.v940_calendar_context(summary, "today", "2026-09-19")

    item = next(row for row in calendar["matches"] if row["id"] == "history-result-pending")
    assert item["status_info"]["is_result_pending"] is True
    assert item["status_info"]["is_upcoming"] is False
    assert item["status_info"]["is_live"] is False
    assert item.get("home_score") in (None, "")
    assert item.get("away_score") in (None, "")
    assert str(item.get("score") or "").replace(" ", "") != "0-0"
    assert item["has_pick"] is False
