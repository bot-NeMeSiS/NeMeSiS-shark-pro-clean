"""Normative caller tests; execute only with root's fresh guarded test profile.

No App import, AST extraction, function-body substitution or production storage.
Only the owned data-source/render/provider frontiers are supplied for Calendar.
SHARK's real collector/projection/selection/metrics stay active.
The launcher receipt defines the actual profile and all filesystem/DB guards.
"""
from functools import wraps
import math
import re
import pytest

from engines.fixture_snapshot_read_model import PreparedFixtureSnapshot
from tests.test_calendar_facet_batch_counts import _unique_primary
from tests.test_v957_calendar_fixture_deduplication import _prepare, _summary

CALENDAR = (
    "context_metrics", "context_prepare_rows", "context_source_selection",
    "context_filtered_selection", "context_grouping", "context_date_lane_counts",
    "context_facets",
)
SHARK = (
    "collection_projection", "collection_live_context",
    "collection_agenda", "collection_favorites",
)
SHARK_PARENTS = frozenset({
    "input", "sports_context", "admission", "briefing", "provider_state",
    "assistant_context", "assistant_answer", "template", "view_total",
    "nested_selection", "nested_telegram", "nested_recent_picks", "nested_summary",
    "nested_collections", "nested_briefing", "nested_intelligence", "nested_compose",
    "nested_provider", "nested_json",
})
PARENTS = (
    "sports_context", "historical_results", "calendar_context",
    "provider_context", "template_render",
)

def _owned_summary(a, monkeypatch):
    rows = [_unique_primary(a, 7100 + i) for i in range(2)]
    summary = _summary(rows)
    summary.update(storage_status="ok", raw_matches_count=2,
                   metrics_generated_at_madrid="2026-11-02T00:00:00+01:00")
    _prepare(a, monkeypatch, summary)
    return summary

def _trace_real_calls(a, monkeypatch):
    trace = []
    real = PreparedFixtureSnapshot.select_rows
    @wraps(real)
    def selected(self, rows, *args, **kwargs):
        trace.append(("selection", tuple(id(row) for row in rows),
                      kwargs.get("limit"), bool(kwargs.get("rank_for")),
                      bool(kwargs.get("predicate"))))
        return real(self, rows, *args, **kwargs)
    monkeypatch.setattr(PreparedFixtureSnapshot, "select_rows", selected)
    import engines.fixture_snapshot_read_model as snapshots
    project = snapshots.project_fixture_identity
    @wraps(project)
    def identity(row, *args, **kwargs):
        callback = kwargs["kickoff_for"]
        assert callback is a.match_kickoff_madrid_dt, "OWNED fixture callback precondition changed"
        trace.append(("c3", id(row), callback))
        return project(row, *args, **kwargs)
    monkeypatch.setattr(snapshots, "project_fixture_identity", identity)
    return trace

def _header(a, body):
    response = a.app.make_response(body)
    return a.apply_security_headers_and_csrf(response).headers["Server-Timing"]

def test_actual_calendar_caller_preserves_bodies_calls_and_five_parents(app_module, monkeypatch):
    a = app_module
    with a.app.test_request_context("/calendar?lane=week"):
        summary = _owned_summary(a, monkeypatch)
        captured = []
        monkeypatch.setattr(a, "v932_safe_dashboard_data", lambda *x, **kw: ({}, summary))
        monkeypatch.setattr(a, "_v940_hydrate_selected_date_results", lambda owner, day: owner)
        monkeypatch.setattr(a, "_v940_calendar_provider_context", lambda owner: {"owned": True})
        monkeypatch.setattr(a, "current_session_user", lambda: None)
        def render(template, **kwargs):
            assert template == "calendar.html"
            captured.append(kwargs["data"]["calendar"])
            return "owned-calendar"
        monkeypatch.setattr(a, "render_template", render)
        trace = _trace_real_calls(a, monkeypatch)
        with monkeypatch.context() as disabled:
            disabled.setattr(a, "_context_subphase_started", lambda *x: None)
            original = a.calendar_page()
            unobserved_calls = list(trace)
            assert tuple(a.g.v935_route_phase_metrics) == PARENTS
        trace.clear()
        result = a.calendar_page()
        assert result == original
        assert captured[0] == captured[1]
        assert trace == unobserved_calls
        assert tuple(a.g.v935_route_phase_metrics) == PARENTS + CALENDAR
        assert all(math.isfinite(value) and value >= 0
                   for value in a.g.v935_route_phase_metrics.values())
        assert not hasattr(a.g, "_calendar_context_phase_collector")
        header = _header(a, result)
        all_names = re.findall(r"(?:^|,\s*)([a-z0-9_]+);dur=", header)
        assert len(all_names) == len(set(all_names))
        assert {name for name in all_names if name.startswith("calendar_")} == {
            "calendar_" + name for name in PARENTS + CALENDAR}
        assert len(header.encode("latin1")) <= 2000
        for name in PARENTS + CALENDAR:
            assert len(re.findall(r"(?:^|,\s*)calendar_" + name + r";dur=", header)) == 1
        # Parent and children overlap; no parent-plus-child latency sum.
        child_total = sum(a.g.v935_route_phase_metrics[name] for name in CALENDAR)
        assert a.g.v935_route_phase_metrics["calendar_context"] + 1 >= child_total

def test_calendar_business_error_closes_current_child_without_running_later_children(app_module, monkeypatch):
    a = app_module
    fault = ValueError("OWNED-business-marker-never-a-header")
    with a.app.test_request_context("/calendar?lane=week"):
        summary = _owned_summary(a, monkeypatch)
        monkeypatch.setattr(a, "v932_safe_dashboard_data", lambda *x, **kw: ({}, summary))
        monkeypatch.setattr(a, "_v940_hydrate_selected_date_results", lambda owner, day: owner)
        def fail(*args, **kwargs):
            raise fault
        monkeypatch.setattr(a, "_calendar_apply_filters", fail)
        with pytest.raises(ValueError) as caught:
            a.calendar_page()
        assert caught.value is fault
        phases = a.g.v935_route_phase_metrics
        assert all(name in phases for name in CALENDAR[:4])
        assert all(name not in phases for name in CALENDAR[4:])
        assert "calendar_context" in phases
        assert not hasattr(a.g, "_calendar_context_phase_collector")
        assert "OWNED-business-marker" not in _header(a, "owned")

@pytest.mark.parametrize("stage", ["start", "record", "merge"])
def test_new_observer_failures_do_not_stop_actual_calendar_caller(app_module, monkeypatch, stage):
    a = app_module
    with a.app.test_request_context("/calendar?lane=week"):
        summary = _owned_summary(a, monkeypatch)
        monkeypatch.setattr(a, "v932_safe_dashboard_data", lambda *x, **kw: ({}, summary))
        monkeypatch.setattr(a, "_v940_hydrate_selected_date_results", lambda owner, day: owner)
        monkeypatch.setattr(a, "_v940_calendar_provider_context", lambda owner: {})
        monkeypatch.setattr(a, "render_template", lambda *x, **kw: "owned-calendar")
        names = {"start": "_context_subphase_started", "record": "_context_subphase_record",
                 "merge": "_calendar_route_phase_values"}
        def fail(*args, **kwargs):
            raise OSError("OWNED-observer-marker")
        monkeypatch.setattr(a, names[stage], fail)
        assert a.calendar_page() == "owned-calendar"
        assert all(name in a.g.v935_route_phase_metrics for name in PARENTS)
        assert not hasattr(a.g, "_calendar_context_phase_collector")
        assert "OWNED-observer-marker" not in _header(a, "owned")

def test_real_shark_collector_preserves_selection_identity_order_and_headers(app_module, monkeypatch):
    a = app_module
    _freeze_app_evaluation_clock(a, monkeypatch)
    with a.app.test_request_context("/shark"):
        summary = _owned_summary(a, monkeypatch)
        trace = _trace_real_calls(a, monkeypatch)
        with monkeypatch.context() as disabled:
            disabled.setattr(a, "_context_subphase_started", lambda *x: None)
            unobserved = a._v998_shark_collections(summary, {})
            unobserved_calls = list(trace)
        trace.clear()
        a.g.v937_shark_phase_metrics = {}
        a.g.shark_context_subphase_metrics = {}
        result = a._v998_shark_collections(summary, {})
        assert result == unobserved
        assert trace == unobserved_calls
        assert tuple(a.g.shark_context_subphase_metrics) == SHARK
        assert a.g.v937_shark_phase_metrics == {}
        assert result["agenda"]["state"] in {"AVAILABLE", "EMPTY"}
        assert a._V999_SHARK_PHASES == SHARK_PARENTS
        assert len(SHARK_PARENTS) == 19
        assert set(SHARK).isdisjoint(SHARK_PARENTS)
        assert not any(name.startswith("nested_") for name in SHARK)
        header = _header(a, "owned-shark")
        for name in SHARK:
            assert len(re.findall(r"(?:^|,\s*)sharkctx_" + name + r";dur=", header)) == 1
            assert "shark_" + name + ";dur=" not in header

def test_shark_unreached_agenda_is_not_fabricated(app_module, monkeypatch):
    a = app_module
    with a.app.test_request_context("/shark"):
        a.g.v937_shark_phase_metrics = {}
        a.g.shark_context_subphase_metrics = {}
        fault = ValueError("OWNED-projection-fault")
        def fail(*args, **kwargs):
            raise fault
        monkeypatch.setattr(a, "_v991_realtime_projection", fail)
        result = a._v998_shark_collections({"storage_status": "ok"}, {})
        assert result["agenda"]["state"] == "UNAVAILABLE"
        assert tuple(a.g.shark_context_subphase_metrics) == ("collection_projection",)
        assert a.g.v937_shark_phase_metrics == {}
        header = _header(a, "owned-shark")
        assert "sharkctx_collection_projection;dur=" in header
        assert "sharkctx_collection_agenda;dur=" not in header
        assert "sharkctx_collection_favorites;dur=" not in header

@pytest.mark.parametrize("stage", ["start", "record"])
def test_observer_fault_does_not_mask_same_business_exception(app_module, monkeypatch, stage):
    a = app_module
    fault = ValueError("OWNED-same-instance")
    calls = []
    def observer_fault(*args, **kwargs):
        raise OSError("OWNED-observer-failure")
    monkeypatch.setattr(a, "_context_subphase_" + ("started" if stage == "start" else "record"), observer_fault)
    with a.app.test_request_context("/shark"):
        with pytest.raises(ValueError) as caught:
            with a._context_subphase("shark", SHARK[0]):
                calls.append("body")
                raise fault
        assert caught.value is fault
    assert calls == ["body"]

def test_no_request_keeps_return_identity_and_exception(app_module):
    a = app_module
    value = object()
    def call():
        with a._context_subphase("shark", SHARK[0]):
            return value
    assert call() is value
    fault = ValueError("owned")
    with pytest.raises(ValueError) as caught:
        with a._context_subphase("calendar", CALENDAR[0]):
            raise fault
    assert caught.value is fault

def test_reentrancy_masks_none_and_restores_parent_without_leaking_requests(app_module):
    a = app_module
    parent, child = {}, {}
    with a.app.test_request_context("/calendar"):
        with a._calendar_context_phase_collection(parent):
            with a._calendar_context_phase_collection(None):
                with a._context_subphase("calendar", CALENDAR[0]):
                    pass
            assert parent == {}
            assert a.g._calendar_context_phase_collector is parent
            with a._calendar_context_phase_collection(child):
                with a._context_subphase("calendar", CALENDAR[0]):
                    pass
            assert tuple(child) == (CALENDAR[0],)
            assert a.g._calendar_context_phase_collector is parent
            with a._context_subphase("calendar", CALENDAR[1]):
                pass
        assert tuple(parent) == (CALENDAR[1],)
        assert not hasattr(a.g, "_calendar_context_phase_collector")
    with a.app.test_request_context("/calendar"):
        assert not hasattr(a.g, "_calendar_context_phase_collector")

def test_fixed_labels_and_finite_values_only(app_module, monkeypatch):
    a = app_module
    parents = {name: 1.0 for name in PARENTS}
    children = {CALENDAR[0]: 2.0, "OWNED-secret-label": 9.0,
                CALENDAR[1]: float("nan"), CALENDAR[2]: float("inf")}
    assert a._calendar_route_phase_values(parents, children) == {**parents, CALENDAR[0]: 2.0}
    with a.app.test_request_context("/shark"):
        a.g.v937_shark_phase_metrics = {}
        a.g.shark_context_subphase_metrics = {}
        with a._context_subphase("shark", "OWNED-secret-label"):
            pass
        a._context_subphase_record("shark", "OWNED-secret-label", 0)
        assert a.g.v937_shark_phase_metrics == {}
        assert a.g.shark_context_subphase_metrics == {}
        native_time = a.time
        class AppClockProxy:
            def __getattr__(self, name):
                return getattr(native_time, name)
            def perf_counter(self):
                return float("nan")
        monkeypatch.setattr(a, "time", AppClockProxy())
        with a._context_subphase("shark", SHARK[0]):
            pass
        assert a.g.v937_shark_phase_metrics == {}
        assert a.g.shark_context_subphase_metrics == {}


def _freeze_app_evaluation_clock(a, monkeypatch):
    """Fix only App's evaluation instant, never provider evidence or stdlib time."""
    native_datetime = a.datetime
    anchor = native_datetime.now(a.MADRID_TZ)
    class DateTimeMeta(type):
        def __instancecheck__(cls, value):
            return isinstance(value, native_datetime)
        def __subclasscheck__(cls, value):
            return issubclass(value, native_datetime)
    class AppEvaluationDateTime(native_datetime, metaclass=DateTimeMeta):
        @classmethod
        def now(cls, tz=None):
            return anchor.astimezone(tz) if tz is not None else anchor.replace(tzinfo=None)
    monkeypatch.setattr(a, "datetime", AppEvaluationDateTime)

def test_shark_early_unavailable_has_no_synthetic_children(app_module, monkeypatch):
    a = app_module
    with a.app.test_request_context("/shark"):
        a.g.v937_shark_phase_metrics = {}
        a.g.shark_context_subphase_metrics = {}
        def forbidden(*args, **kwargs):
            pytest.fail("Projection reached despite early storage-unavailable branch")
        monkeypatch.setattr(a, "_v991_realtime_projection", forbidden)
        result = a._v998_shark_collections({"storage_status": "database_locked"}, {})
        assert result["live"]["state"] == result["agenda"]["state"] == "UNAVAILABLE"
        assert a.g.v937_shark_phase_metrics == {}
        assert a.g.shark_context_subphase_metrics == {}
        assert not a._shark_context_timing_header(a.g.shark_context_subphase_metrics)

def test_shark_unknown_owner_skips_agenda_but_records_actual_other_phases(app_module):
    a = app_module
    with a.app.test_request_context("/shark"):
        rows = [_unique_primary(a, 7300 + i) for i in range(2)]
        summary = _summary(rows)
        summary.update(storage_status="ok", raw_matches_count=2)
        assert a._v991_operation_for(summary) is None, "OWNED unprepared fixture precondition"
        a.g.v937_shark_phase_metrics = {}
        a.g.shark_context_subphase_metrics = {}
        result = a._v998_shark_collections(summary, {})
        assert result["live"]["state"] == result["agenda"]["state"] == "UNAVAILABLE"
        assert result["favorites"]["state"] == "EMPTY"
        assert tuple(a.g.shark_context_subphase_metrics) == (
            "collection_projection", "collection_live_context", "collection_favorites")
        assert a.g.v937_shark_phase_metrics == {}
        assert "sharkctx_collection_agenda;dur=" not in _header(a, "owned-shark")

@pytest.mark.parametrize("user, expected_reads", [({}, 0), ({"id": "owned-no-favorites"}, 1)])
def test_shark_no_favorites_does_not_normalize_or_select_saved_rows(app_module, monkeypatch, user, expected_reads):
    a = app_module
    with a.app.test_request_context("/shark"):
        summary = _owned_summary(a, monkeypatch)
        saved_reads = []
        def no_saved(*args, **kwargs):
            saved_reads.append((args, kwargs))
            return []
        def forbidden(*args, **kwargs):
            pytest.fail("Favorites normalization reached for empty saved data")
        monkeypatch.setattr(a, "get_favorites", no_saved)
        monkeypatch.setattr(a, "favorite_sets", forbidden)
        a.g.v937_shark_phase_metrics = {}
        a.g.shark_context_subphase_metrics = {}
        result = a._v998_shark_collections(summary, user)
        assert result["favorites"] == {"state": "EMPTY", "matches": [], "total": 0, "saved_count": 0}
        assert len(saved_reads) == expected_reads
        assert tuple(a.g.shark_context_subphase_metrics) == SHARK
        assert a.g.v937_shark_phase_metrics == {}

def test_actual_shark_page_caller_has_closed_bounded_header_without_duplicate_metrics(app_module, monkeypatch):
    """Direct anonymous caller plus real header writer; no full-HTTP/auth claim."""
    a = app_module
    with a.app.test_request_context("/shark"):
        assert a.current_session_user() is None, "OWNED anonymous request precondition"
        stale_parents = {"OWNED-stale-parent": 11.0}
        stale_children = {"OWNED-stale-child": 13.0, SHARK[2]: 17.0}
        a.g.v937_shark_phase_metrics = stale_parents
        a.g.shark_context_subphase_metrics = stale_children
        summary = _owned_summary(a, monkeypatch)
        trace = _trace_real_calls(a, monkeypatch)
        captured = {}
        def source(*args, **kwargs):
            assert args == ("/shark",)
            assert kwargs == {"compact": True, "_shark_view": True}
            return {}, summary
        def render(template, **kwargs):
            assert template == "shark.html"
            captured.update(kwargs)
            return "owned-shark"
        # Supply only owned data/render frontiers. Selection, authority,
        # collections, metrics, session/admission and assistant callers stay real.
        monkeypatch.setattr(a, "v932_safe_dashboard_data", source)
        monkeypatch.setattr(a, "render_template", render)
        result = a.shark_page()
        assert result == "owned-shark"
        assert a.g.v937_shark_phase_metrics is not stale_parents
        assert a.g.shark_context_subphase_metrics is not stale_children
        assert stale_parents == {"OWNED-stale-parent": 11.0}
        assert stale_children == {"OWNED-stale-child": 13.0, SHARK[2]: 17.0}
        collections = captured["data"]["shark_assistant"]["context"]["collections"]
        assert collections["agenda"]["state"] in {"AVAILABLE", "EMPTY"}, (
            "OWNED prepared source did not reach the established agenda branch")
        assert any(event[0] == "c3" for event in trace)
        assert any(event[0] == "selection" for event in trace)
        header = _header(a, result)
        pairs = re.findall(r"(?:^|,\s*)([a-z0-9_]+);dur=([0-9.]+)", header)
        names = [name for name, _value in pairs]
        assert len(names) == len(set(names))
        shark_names = {name.removeprefix("shark_") for name in names if name.startswith("shark_")}
        assert shark_names == a._V999_SHARK_PHASES == SHARK_PARENTS
        assert len(shark_names) == 19
        assert set(a.g.v937_shark_phase_metrics) == SHARK_PARENTS
        child_names = {name.removeprefix("sharkctx_") for name in names if name.startswith("sharkctx_")}
        assert child_names == set(SHARK)
        assert tuple(a.g.shark_context_subphase_metrics) == SHARK
        assert not any("OWNED-stale" in name for name in names)
        assert len(header.encode("latin1")) <= 2000
        values = {name: float(value) for name, value in pairs}
        assert all(math.isfinite(value) and value >= 0 for value in values.values())
        assert values["shark_nested_collections"] + 1 >= sum(values["sharkctx_" + name] for name in SHARK)
        # Nested siblings already include nested_collections. Do not add its
        # collection_* grandchildren a second time.
        nested_siblings = [value for name, value in values.items() if name.startswith("shark_nested_")]
        assert values["shark_assistant_context"] + 1 >= sum(nested_siblings)

def test_reentrant_child_error_restores_exact_parent_collector(app_module):
    a = app_module
    parent, child = {}, {}
    fault = ValueError("OWNED reentrant failure")
    with a.app.test_request_context("/calendar"):
        with a._calendar_context_phase_collection(parent):
            with pytest.raises(ValueError) as caught:
                with a._calendar_context_phase_collection(child):
                    with a._context_subphase("calendar", CALENDAR[0]):
                        raise fault
            assert caught.value is fault
            assert a.g._calendar_context_phase_collector is parent
            assert tuple(child) == (CALENDAR[0],)
            assert parent == {}
        assert not hasattr(a.g, "_calendar_context_phase_collector")


@pytest.mark.parametrize("invalid", [
    float("nan"), float("inf"), -float("inf"), -1, True, False,
    "1.0", None, [], {},
], ids=["nan", "positive-inf", "negative-inf", "negative", "true", "false",
        "string", "none", "list", "dict"])
def test_shark_child_header_filters_invalid_values_without_touching_input(app_module, invalid):
    a = app_module
    metrics = {SHARK[0]: 0, SHARK[1]: invalid, SHARK[2]: 1.25,
               "OWNED-not-a-label": 9.0}
    original_items = tuple(metrics.items())
    assert a._shark_context_timing_header(metrics) == (
        "sharkctx_collection_projection;dur=0.0, sharkctx_collection_agenda;dur=1.2")
    assert tuple(metrics) == tuple(name for name, _value in original_items)
    assert all(metrics[name] is value for name, value in original_items)


@pytest.mark.parametrize("metrics", [None, [], (), "owned", 1],
                         ids=["none", "list", "tuple", "string", "integer"])
def test_shark_child_header_rejects_non_mapping_collectors(app_module, metrics):
    assert app_module._shark_context_timing_header(metrics) == ""


@pytest.mark.parametrize("failure", ["writer", "mapping-read", "unrepresentable-int"])
def test_shark_child_header_observer_failure_preserves_legacy_header_and_body(app_module, monkeypatch, failure):
    a = app_module
    with a.app.test_request_context("/shark"):
        parents = {"input": 12.5, "nested_collections": 3.0}
        a.g.v937_shark_phase_metrics = parents
        a.g.shark_context_subphase_metrics = {SHARK[0]: 1.0}
        if failure == "writer":
            def fail(*args, **kwargs):
                raise OSError("OWNED-child-writer-error")
            monkeypatch.setattr(a, "_shark_context_timing_header", fail)
        elif failure == "mapping-read":
            class FaultyMetrics(dict):
                def get(self, key, default=None):
                    raise OSError("OWNED-child-read-error")
            a.g.shark_context_subphase_metrics = FaultyMetrics({SHARK[0]: 1.0})
        else:
            a.g.shark_context_subphase_metrics = {SHARK[0]: 10 ** 1000}
        response = a.app.make_response("owned-response")
        response.headers["Server-Timing"] = "app;dur=9.0"
        response = a.apply_security_headers_and_csrf(response)
        assert response.status_code == 200
        assert response.get_data(as_text=True) == "owned-response"
        assert response.headers["Server-Timing"] == (
            "app;dur=9.0, shark_input;dur=12.5, shark_nested_collections;dur=3.0")
        assert response.headers["X-Nemesis-Shark-Data"] == "db-cache-only"
        assert a.g.v937_shark_phase_metrics is parents
        assert parents == {"input": 12.5, "nested_collections": 3.0}
        assert "OWNED-child" not in str(response.headers)


def test_calendar_route_header_does_not_publish_stale_shark_children(app_module):
    a = app_module
    with a.app.test_request_context("/calendar"):
        a.g.v935_route_phase_namespace = "calendar"
        a.g.v935_route_phase_metrics = {"calendar_context": 5.0}
        a.g.v937_shark_phase_metrics = {"input": 7.0}
        a.g.shark_context_subphase_metrics = {SHARK[0]: 2.0}
        header = _header(a, "owned-calendar")
        assert header == "calendar_calendar_context;dur=5.0"
        assert "shark_" not in header
        assert "sharkctx_" not in header
        assert a.g.shark_context_subphase_metrics == {SHARK[0]: 2.0}


def test_nested_shark_children_do_not_replace_parent_metric_collector(app_module):
    a = app_module
    with a.app.test_request_context("/shark"):
        parents = {"input": 7.0}
        children = {}
        a.g.v937_shark_phase_metrics = parents
        a.g.shark_context_subphase_metrics = children
        with a._context_subphase("shark", SHARK[0]):
            with a._context_subphase("shark", SHARK[1]):
                pass
        assert a.g.v937_shark_phase_metrics is parents
        assert parents == {"input": 7.0}
        assert a.g.shark_context_subphase_metrics is children
        assert tuple(children) == (SHARK[1], SHARK[0])
        assert all(math.isfinite(value) and value >= 0 for value in children.values())
        assert children[SHARK[0]] + 1 >= children[SHARK[1]]


def test_shark_children_do_not_leak_into_next_request(app_module):
    a = app_module
    with a.app.test_request_context("/shark"):
        a.g.v937_shark_phase_metrics = {"input": 7.0}
        with a._context_subphase("shark", SHARK[0]):
            pass
        assert "sharkctx_collection_projection;dur=" in _header(a, "owned-first")
    with a.app.test_request_context("/shark"):
        assert not hasattr(a.g, "shark_context_subphase_metrics")
        assert not hasattr(a.g, "v937_shark_phase_metrics")
        a.g.v937_shark_phase_metrics = {"input": 2.0}
        assert _header(a, "owned-next") == "shark_input;dur=2.0"
