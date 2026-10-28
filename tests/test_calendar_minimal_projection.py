"""Focused Calendar projection contracts for the disposable LOCAL SAFE suite.

Copy this file into the disposable checkout's tests/ and run through its original
tools/check_local_candidate.py. The shared app_module fixture imports actual App;
this file never imports or executes a source checkout itself. Branch dependencies
are deliberately mocked below. These tests do not prove production performance,
cache equivalence, fixture preparation, provider correctness, or network safety.
The separate passive actual-App probe covers the unmodified runtime bindings.
"""
from copy import deepcopy
import sqlite3

import pytest


MINIMAL_KEYS = {
    "app_name", "version", "date", "lane", "matches", "upcoming_matches",
    "available_matches", "session_user", "v931_route_guard",
}


def _summary():
    today = {"id": "calendar-today", "match_date": "2026-10-28"}
    upcoming = {"id": "calendar-upcoming", "match_date": "2026-10-29"}
    return {
        "valid_matches_today": [today],
        "valid_upcoming_matches": [upcoming],
        "valid_matches_available": [today, upcoming],
        "all_valid_matches": [today, upcoming],
        "valid_live_events": [],
        "valid_active_picks": [{"id": "unused-pick", "match_id": today["id"]}],
        "provider_status": "test_snapshot",
        "storage_status": "available",
        "sports_home": {"sentinel": "must not be projected"},
        "sports_metrics": {"sentinel": "must not be rebuilt here"},
    }


def _forbid(monkeypatch, app_module, names):
    calls = []
    for name in names:
        def forbidden(*_args, _name=name, **_kwargs):
            calls.append(_name)
            pytest.fail("Calendar minimal branch called unused builder: " + _name)
        monkeypatch.setattr(app_module, name, forbidden)
    return calls


def _forbid_unrelated_builders(monkeypatch, app_module):
    return _forbid(monkeypatch, app_module, (
        "dashboard_data", "_v931_minimal_client_data", "_v931_legacy_home_summary",
        "build_sports_home_sections", "_v931_provider_context",
        "_v940_calendar_provider_context", "get_safe_picks_context",
        "get_safe_odds_context", "get_v932_real_sports_value_context",
        "get_sports_metrics_contract", "build_sports_metrics_contract",
        "_v999_authorized_snapshot_picks", "v931_live_context",
        "_v991_prepare_summary_operation",
    ))


def test_calendar_supplied_summary_keeps_owner_rows_and_only_minimal_fields(
    app_module, monkeypatch,
):
    a = app_module
    summary = _summary()
    before = deepcopy(summary)
    user = {"id": "calendar-current-client", "role": "CLIENT"}
    forbidden = _forbid_unrelated_builders(monkeypatch, a)
    _forbid(monkeypatch, a, ("get_public_home_sports_summary",))
    monkeypatch.setattr(a, "current_session_user", lambda: user)

    with a.app.test_request_context("/calendar"):
        data, owner = a.v931_safe_dashboard_data(
            "/calendar", "today", "2026-10-28", compact=True,
            sports_summary=summary, _calendar_view=True,
        )
        assert a.request.environ["nemesis.v931.degraded"] is False

    assert owner is summary
    assert summary == before
    assert set(data) == MINIMAL_KEYS
    assert data["app_name"] == a.APP_NAME
    assert data["version"] == a.APP_VERSION
    assert data["date"] == "2026-10-28" and data["lane"] == "today"
    assert data["session_user"] is user
    for projected, source in (
        ("matches", "valid_matches_today"),
        ("upcoming_matches", "valid_upcoming_matches"),
        ("available_matches", "valid_matches_available"),
    ):
        assert len(data[projected]) == len(summary[source])
        assert all(row is original for row, original in zip(data[projected], summary[source]))
    assert data["v931_route_guard"] == {
        "status": "compact_read_only_context", "no_render_api_call": True,
        "request_scoped_db_connection": True,
    }
    assert forbidden == []


@pytest.mark.parametrize("lane,date_value,expected", [
    ("tomorrow", None, "TOMORROW"),
    ("tomorrow", "not-a-date", "TOMORROW"),
    ("today", "2026-02-30", "TODAY"),
    ("results", "2026-10-20", "2026-10-20"),
])
def test_calendar_getter_receives_normalized_date_and_prepare_only(
    app_module, monkeypatch, lane, date_value, expected,
):
    a = app_module
    summary, calls = _summary(), []
    _forbid_unrelated_builders(monkeypatch, a)
    monkeypatch.setattr(a, "current_session_user", lambda: None)

    def getter(*args, **kwargs):
        calls.append((args, kwargs))
        return summary

    monkeypatch.setattr(a, "get_public_home_sports_summary", getter)
    with a.app.test_request_context("/calendar"):
        expected_date = a.today_iso(1) if expected == "TOMORROW" else (
            a.today_iso() if expected == "TODAY" else expected
        )
        _, owner = a.v931_safe_dashboard_data(
            "/calendar", lane, date_value, compact=True,
            sports_summary=[], _calendar_view=True,
        )
    assert owner is summary
    assert calls == [((), {"selected_date": expected_date, "_prepare_only": True})]


@pytest.mark.parametrize("role,expected_scope", [
    (None, None), ("CLIENT", "client"), ("ADMIN", "admin"),
])
def test_calendar_lock_precedes_supplied_summary_and_preserves_issue_logging(
    app_module, monkeypatch, role, expected_scope,
):
    a = app_module
    supplied = _summary()
    locked = {
        "valid_matches_today": [], "valid_upcoming_matches": [],
        "valid_matches_available": [], "storage_status": "database_locked",
        "provider_status": "temporarily_unavailable",
    }
    user = {"id": "locked-calendar-current-user", "role": role} if role else None
    issues, authenticated, locked_calls = [], [], []
    forbidden = _forbid_unrelated_builders(monkeypatch, a)
    _forbid(monkeypatch, a, ("get_public_home_sports_summary",))
    monkeypatch.setattr(a, "current_session_user", lambda: user)
    monkeypatch.setattr(a, "is_admin_session", lambda: role == "ADMIN")

    def locked_summary():
        locked_calls.append(True)
        return locked

    monkeypatch.setattr(a, "_v932_locked_sports_summary", locked_summary)
    monkeypatch.setattr(a, "v931_record_client_route_issue", lambda *args: issues.append(args))
    monkeypatch.setattr(a, "v932_record_authenticated_issue", lambda *args: authenticated.append(args))
    with a.app.test_request_context("/calendar"):
        a.request.environ["nemesis.v932.database_locked"] = True
        data, owner = a.v931_safe_dashboard_data(
            "/calendar", compact=True, sports_summary=supplied, _calendar_view=True,
        )
        assert a.request.environ["nemesis.v931.degraded"] is True

    assert locked_calls == [True] and owner is locked
    assert set(data) == MINIMAL_KEYS
    assert data["session_user"] is user
    assert data["matches"] == data["upcoming_matches"] == data["available_matches"] == []
    assert data["v931_route_guard"]["status"] == "safe_fallback"
    assert data["v931_route_guard"]["provider_status"] == "temporarily_unavailable"
    assert data["v931_route_guard"]["no_render_api_call"] is True
    assert len(issues) == 1
    route, error, cause = issues[0]
    assert route == "/calendar" and cause == "sqlite_read_timeout_guard"
    assert isinstance(error, sqlite3.OperationalError) and str(error) == "database is locked"
    if expected_scope is None:
        assert authenticated == []
    else:
        assert authenticated == [(route, error, expected_scope, cause)]
    assert forbidden == []


def test_v932_calendar_flag_reaches_v931_and_skips_duplicate_metrics_and_value(
    app_module, monkeypatch,
):
    a = app_module
    summary, data, calls = _summary(), {}, []
    forbidden = _forbid(monkeypatch, a, (
        "get_sports_metrics_contract", "get_v932_real_sports_value_context",
    ))

    def safe_dashboard(*args, **kwargs):
        calls.append((args, kwargs))
        return data, summary

    monkeypatch.setattr(a, "v931_safe_dashboard_data", safe_dashboard)
    with a.app.test_request_context("/calendar"):
        result, owner = a.v932_safe_dashboard_data(
            "/calendar", "tomorrow", "2026-10-29", compact=True,
            sports_summary=summary, _calendar_view=True,
        )
    assert result is data and owner is summary
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == ("/calendar", "tomorrow", "2026-10-29")
    assert kwargs["compact"] is True and kwargs["sports_summary"] is summary
    assert kwargs["_calendar_view"] is True
    assert not kwargs.get("_shark_view") and not kwargs.get("_directo_minimal")
    assert forbidden == []


@pytest.mark.parametrize("flags", [{}, {"_calendar_view": False}])
def test_calendar_flag_off_keeps_original_compact_projection_and_default_getter(
    app_module, monkeypatch, flags,
):
    a = app_module
    summary, legacy_calls, getter_calls = _summary(), [], []
    data = {"matches": summary["valid_matches_today"], "upcoming_matches": summary["valid_upcoming_matches"],
            "home_summary": {"existing": True}, "v925_live": {"existing": True}}

    def getter(*args, **kwargs):
        getter_calls.append((args, kwargs))
        return summary

    def legacy(*args, **kwargs):
        legacy_calls.append((args, kwargs))
        return data

    monkeypatch.setattr(a, "get_public_home_sports_summary", getter)
    monkeypatch.setattr(a, "_v931_minimal_client_data", legacy)
    with a.app.test_request_context("/app"):
        result, owner = a.v931_safe_dashboard_data(
            "/app", "today", "2026-10-28", compact=True, **flags,
        )
    assert result is data and owner is summary
    assert getter_calls == [((), {})]
    assert legacy_calls == [((summary, "today", "2026-10-28"), {"_shark_view": False})]
    assert result["home_summary"] == {"existing": True}
    assert result["v925_live"] == {"existing": True}


@pytest.mark.parametrize("compact,flags,forwarded", [
    (True, {}, {}),
    (True, {"_directo_minimal": True}, {"_directo_minimal": True}),
    (True, {"_shark_view": True}, {"_shark_view": True}),
    (True, {"_calendar_view": True, "_directo_minimal": True}, {"_directo_minimal": True}),
    (True, {"_calendar_view": True, "_shark_view": True}, {"_shark_view": True}),
    (False, {"_calendar_view": True}, {}),
])
def test_v932_other_modes_keep_original_wrapper_builds(
    app_module, monkeypatch, compact, flags, forwarded,
):
    a = app_module
    summary, data, calls, built = _summary(), {}, [], []
    value, metrics = {"value": "original"}, {"metrics": "original"}

    def safe_dashboard(*args, **kwargs):
        calls.append((args, kwargs))
        return data, summary

    def value_context(owner):
        assert owner is summary
        built.append("value")
        return value

    def metrics_context(owner):
        assert owner is summary
        built.append("metrics")
        return metrics

    monkeypatch.setattr(a, "v931_safe_dashboard_data", safe_dashboard)
    monkeypatch.setattr(a, "get_v932_real_sports_value_context", value_context)
    monkeypatch.setattr(a, "get_sports_metrics_contract", metrics_context)
    with a.app.test_request_context("/app"):
        result, owner = a.v932_safe_dashboard_data(
            "/app", compact=compact, sports_summary=summary, **flags,
        )
    assert result is data and owner is summary
    assert calls == [(("/app", "today", None), {
        "compact": compact, "sports_summary": summary, **forwarded,
    })]
    assert built == ["value", "metrics"]
    assert data["v932_sports_value"] is value and data["sports_metrics"] is metrics
    assert data["v932_authenticated_scope"] == "client"


@pytest.mark.parametrize("mode", ["directo", "shark", "noncompact_fallback"])
def test_v931_calendar_flag_does_not_replace_directo_shark_or_noncompact_path(
    app_module, monkeypatch, mode,
):
    """Exercise dispatch only; the noncompact fault is explicit test injection."""
    a = app_module
    summary, getter_calls, legacy_calls, dashboard_calls, issues = _summary(), [], [], [], []
    legacy_data = {
        "matches": summary["valid_matches_today"],
        "upcoming_matches": summary["valid_upcoming_matches"],
        "legacy_branch": mode,
    }
    compact = mode != "noncompact_fallback"
    flags = {"_directo_minimal": True} if mode == "directo" else (
        {"_shark_view": True} if mode == "shark" else {}
    )
    fault = RuntimeError("controlled noncompact schema guard test")

    def getter(*args, **kwargs):
        getter_calls.append((args, kwargs))
        return summary

    def legacy(*args, **kwargs):
        legacy_calls.append((args, kwargs))
        return legacy_data

    def dashboard(*args, **kwargs):
        dashboard_calls.append((args, kwargs))
        raise fault

    monkeypatch.setattr(a, "get_public_home_sports_summary", getter)
    monkeypatch.setattr(a, "_v931_minimal_client_data", legacy)
    monkeypatch.setattr(a, "dashboard_data", dashboard)
    monkeypatch.setattr(a, "current_session_user", lambda: None)
    monkeypatch.setattr(a, "v931_record_client_route_issue", lambda *args: issues.append(args))
    _forbid(monkeypatch, a, ("_v940_calendar_filters", "v932_record_authenticated_issue"))

    with a.app.test_request_context("/app"):
        data, owner = a.v931_safe_dashboard_data(
            "/app", "today", "2026-10-28", compact=compact,
            _calendar_view=True, **flags,
        )
        assert a.request.environ["nemesis.v931.degraded"] is (not compact)

    assert owner is summary
    assert getter_calls == [((), {})]
    if mode == "directo":
        assert set(data) == MINIMAL_KEYS
        assert data["matches"][0] is summary["valid_matches_today"][0]
        assert data["upcoming_matches"][0] is summary["valid_upcoming_matches"][0]
        assert legacy_calls == []
    else:
        assert data is legacy_data
        assert legacy_calls == [((summary, "today", "2026-10-28"), {
            "_shark_view": mode == "shark",
        })]
    if compact:
        assert dashboard_calls == [] and issues == []
        assert data["v931_route_guard"]["status"] == "compact_read_only_context"
    else:
        assert dashboard_calls == [(("today", "2026-10-28"), {})]
        assert issues == [("/app", fault, "dashboard_data_schema_guard")]


def test_calendar_route_uses_flag_and_preserves_complete_context_provider_and_timing(
    app_module, monkeypatch,
):
    a = app_module
    summary, data, calls = _summary(), {}, []
    calendar_metrics = {"snapshot_id": "fresh-calendar-metrics", "matches_today": 1}
    calendar = {
        "matches": [{"id": "calendar-visible-row"}],
        "filters": {"lane": "tomorrow", "date": "2026-10-29"},
        "sports_metrics": calendar_metrics,
        "day_groups": [{"id": "day-group"}], "groups": [{"id": "group"}],
        "counts": {"visible": 1}, "facets": {"teams": [{"value": "QA"}]},
        "tabs": [{"key": "tomorrow"}], "primary_tabs": [{"key": "tomorrow"}],
        "date_navigation": [{"date": "2026-10-29"}], "day_navigation": [{"id": "day"}],
        "active_filters": [{"key": "q", "value": "QA"}],
        "identity_state": "PREPARED", "facet_identity_state": "PREPARED",
    }
    before = deepcopy(calendar)
    provider = {"provider_status": "test_snapshot", "has_real_data": True}

    def dashboard(*args, **kwargs):
        calls.append(("dashboard", args, kwargs))
        return data, summary

    def historical(owner, selected_date):
        assert owner is summary and selected_date == "not-a-date"
        calls.append(("historical",))
        return owner

    def calendar_context(owner, lane, selected_date):
        assert owner is summary and lane == "tomorrow" and selected_date == "not-a-date"
        calls.append(("calendar",))
        return calendar

    def provider_context(owner):
        assert owner is summary
        calls.append(("provider",))
        return provider

    def render(template, **context):
        assert template == "calendar.html" and context == {"data": data}
        calls.append(("render",))
        return "calendar-rendered"

    monkeypatch.setattr(a, "v932_safe_dashboard_data", dashboard)
    monkeypatch.setattr(a, "_v940_hydrate_selected_date_results", historical)
    monkeypatch.setattr(a, "v940_calendar_context", calendar_context)
    monkeypatch.setattr(a, "_v940_calendar_provider_context", provider_context)
    monkeypatch.setattr(a, "render_template", render)
    with a.app.test_request_context("/calendar?lane=tomorrow&date=not-a-date&q=QA"):
        result = a.calendar_page()
        phases = dict(a.g.v935_route_phase_metrics)
        assert a.g.v935_route_phase_namespace == "calendar"

    assert result == "calendar-rendered"
    assert calls[0] == ("dashboard", ("/calendar", "tomorrow", "not-a-date"), {
        "compact": True, "_calendar_view": True,
    })
    assert [call[0] for call in calls] == ["dashboard", "historical", "calendar", "provider", "render"]
    assert data["calendar"] is calendar and calendar == before
    assert data["matches"] is calendar["matches"]
    assert data["lane"] == "tomorrow" and data["date"] == "2026-10-29"
    assert data["v925_calendar"] is provider
    assert data["sports_metrics"] is calendar_metrics
    assert set(phases) == {"sports_context", "historical_results", "calendar_context", "template_render"}
    assert all(isinstance(elapsed, (int, float)) and elapsed >= 0 for elapsed in phases.values())
