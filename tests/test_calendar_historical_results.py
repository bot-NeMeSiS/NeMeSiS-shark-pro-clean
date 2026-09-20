"""Calendar historical results read-path regressions.

These tests never call a sports provider. Historical rows are supplied through
the existing persisted-results reader boundary.
"""
from datetime import date, timedelta


def _today_factory(anchor):
    current = date.fromisoformat(anchor)
    return lambda offset=0: (current + timedelta(days=offset)).isoformat()


def _empty_summary(app_module):
    summary = {
        "all_valid_matches": [],
        "valid_matches_today": [],
        "valid_upcoming_matches": [],
        "valid_matches_available": [],
        "valid_live_events": [],
        "valid_active_picks": [],
        "finished_matches": [],
        "result_pending_matches": [],
        "archived_matches": [],
        "incident_matches": [],
        "incomplete_matches": [],
        "raw_matches_count": 0,
        "provider_status": "data_available",
        "last_sync": "",
        "safe_message": "Persisted sports data.",
    }
    summary["sports_metrics"] = app_module.build_sports_metrics_contract(summary)
    return summary


def _finished(match_id="hist-result-1", match_date="2026-09-18"):
    return {
        "id": match_id,
        "external_id": match_id,
        "home_team": "Histórico Local",
        "away_team": "Histórico Visitante",
        "competition_name": "Liga Histórica",
        "league_name": "Liga Histórica",
        "country": "Spain",
        "match_date": match_date,
        "kickoff_time": "20:00",
        "kickoff_iso": f"{match_date}T20:00:00+02:00",
        "status": "FT",
        "home_score": 2,
        "away_score": 1,
        "score": "2-1",
        "source": "PERSISTED_DB_QA",
        "last_synced_at": f"{match_date}T22:00:00+02:00",
    }


def test_past_date_hydrates_persisted_results_missing_from_main_snapshot(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "today_iso", _today_factory("2026-09-20"))
    calls = []

    def persisted(start_date=None, days_back=14, limit=150):
        calls.append((start_date, days_back, limit))
        return [_finished()]

    monkeypatch.setattr(app_module, "get_results_matches", persisted)
    base = _empty_summary(app_module)
    hydrated = app_module._v940_hydrate_selected_date_results(base, "2026-09-18")

    assert calls == [("2026-09-18", 0, 400)]
    assert hydrated["historical_results_source"] == "local_db_read_only"
    assert hydrated["historical_results_count"] == 1
    assert [item["id"] for item in hydrated["all_valid_matches"]] == ["hist-result-1"]
    assert [item["id"] for item in hydrated["finished_matches"]] == ["hist-result-1"]

    with app_module.app.test_request_context("/calendar?lane=today&date=2026-09-18"):
        calendar = app_module.v940_calendar_context(hydrated, "today", "2026-09-18")
    assert calendar["counts"]["visible"] == 1
    assert calendar["matches"][0]["id"] == "hist-result-1"
    assert calendar["matches"][0]["home_score"] == 2
    assert calendar["matches"][0]["away_score"] == 1
    assert calendar["external_calls"] == 0
    assert calendar["database_written"] is False


def test_historical_reader_keeps_only_the_selected_day(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "today_iso", _today_factory("2026-09-20"))
    monkeypatch.setattr(
        app_module,
        "get_results_matches",
        lambda *a, **k: [_finished("selected", "2026-09-18"), _finished("other", "2026-09-17")],
    )
    hydrated = app_module._v940_hydrate_selected_date_results(
        _empty_summary(app_module), "2026-09-18"
    )
    assert [item["id"] for item in hydrated["all_valid_matches"]] == ["selected"]


def test_today_and_future_dates_do_not_use_historical_reader(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "today_iso", _today_factory("2026-09-20"))

    def forbidden(*args, **kwargs):
        raise AssertionError("current/future calendar must stay on the normal snapshot path")

    monkeypatch.setattr(app_module, "get_results_matches", forbidden)
    summary = _empty_summary(app_module)
    assert app_module._v940_hydrate_selected_date_results(summary, "2026-09-20") is summary
    assert app_module._v940_hydrate_selected_date_results(summary, "2026-09-21") is summary


def test_historical_db_lock_falls_back_without_fabricating_results(app_module, monkeypatch):
    import sqlite3

    monkeypatch.setattr(app_module, "today_iso", _today_factory("2026-09-20"))

    def locked(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(app_module, "get_results_matches", locked)
    summary = _empty_summary(app_module)
    assert app_module._v940_hydrate_selected_date_results(summary, "2026-09-18") is summary


def test_historical_provider_state_matches_visible_results(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "_v931_provider_context",
        lambda summary: {
            "has_real_data": False,
            "provider_status": "waiting_for_sync",
            "safe_message": "No hay partidos completos disponibles ahora.",
        },
    )
    context = app_module._v940_calendar_provider_context(
        {"historical_results_count": 2}
    )
    assert context["has_real_data"] is True
    assert context["provider_status"] == "data_available"
    assert "Resultados persistidos" in context["safe_message"]


def test_calendar_provider_state_is_unchanged_without_historical_results(app_module, monkeypatch):
    expected = {
        "has_real_data": False,
        "provider_status": "waiting_for_sync",
        "safe_message": "Sin agenda actual.",
    }
    monkeypatch.setattr(app_module, "_v931_provider_context", lambda summary: dict(expected))
    assert app_module._v940_calendar_provider_context({}) == expected


def test_finished_lane_and_counter_are_scoped_to_selected_date(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "today_iso", _today_factory("2026-09-20"))
    selected = _finished("selected-day", "2026-09-18")
    other = _finished("other-day", "2026-09-17")
    summary = _empty_summary(app_module)
    summary["all_valid_matches"] = [selected, other]
    summary["finished_matches"] = [selected, other]
    summary["sports_metrics"] = app_module.build_sports_metrics_contract(summary)

    with app_module.app.test_request_context("/calendar?lane=finished&date=2026-09-18"):
        calendar = app_module.v940_calendar_context(summary, "finished", "2026-09-18")

    assert [item["id"] for item in calendar["matches"]] == ["selected-day"]
    assert calendar["counts"]["finished"] == 1


def test_calendar_api_hydrates_same_persisted_history_as_page(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "today_iso", _today_factory("2026-09-20"))
    monkeypatch.setattr(app_module, "get_results_matches", lambda *a, **k: [_finished()])
    monkeypatch.setattr(
        app_module,
        "v932_safe_dashboard_data",
        lambda *a, **k: ({}, _empty_summary(app_module)),
    )

    response = app_module.app.test_client().get(
        "/api/calendar?lane=today&date=2026-09-18"
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert [item["id"] for item in payload["matches"]] == ["hist-result-1"]
    assert payload["calendar"]["external_calls"] == 0
    assert payload["calendar"]["database_written"] is False


def test_calendar_page_provider_state_uses_hydrated_history(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "today_iso", _today_factory("2026-09-20"))
    monkeypatch.setattr(app_module, "get_results_matches", lambda *a, **k: [_finished()])
    monkeypatch.setattr(
        app_module,
        "v932_safe_dashboard_data",
        lambda *a, **k: ({}, _empty_summary(app_module)),
    )
    captured = {}

    def render(name, **kwargs):
        captured["name"] = name
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(app_module, "render_template", render)
    with app_module.app.test_request_context("/calendar?lane=today&date=2026-09-18"):
        assert app_module.calendar_page() == "ok"

    assert captured["name"] == "calendar.html"
    state = captured["data"]["v925_calendar"]
    assert state["has_real_data"] is True
    assert state["provider_status"] == "data_available"
    assert "Resultados persistidos" in state["safe_message"]
