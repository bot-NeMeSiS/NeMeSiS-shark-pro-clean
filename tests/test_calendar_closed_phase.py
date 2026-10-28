"""Closed Calendar timing records preserve business outcomes and privacy.

These engine-only cases cover fixed records, fresh request-local traces,
ordinary sink/serialization exceptions and nested/concurrent context cleanup.
No App import is required. Real clocks, tokens and context primitives remain.
Sink injection changes only the engine module binding, never shared stdlib.
Blocking stdout or arbitrary clock/token/context failures are not certified."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock, get_ident
from types import SimpleNamespace

import pytest

from engines import closed_operation_timing as timing


DOMAIN = "calendar_read"
CALLBACK_PHASES = (
    "sports_context",
    "historical_results",
    "calendar_context",
    "provider_context",
    "template_render",
)
SCHEMA_KEYS = {
    "event", "domain", "trace", "parent", "phase", "point", "duration_ms",
    "offset_ms", "in_transaction", "error", "dropped_records",
}
PRIVATE_MARKERS = (
    "SYNTHETIC_SECRET_20261028",
    "/calendario?team=SYNTHETIC_QUERY_20261028",
    "SELECT private_value FROM SYNTHETIC_SQL_20261028",
    "SYNTHETIC_USER_ID_20261028",
    "SYNTHETIC_FIXTURE_ID_20261028",
    "https://provider.invalid/SYNTHETIC_PROVIDER_KEY_20261028",
)


@pytest.fixture
def calendar_output(monkeypatch):
    """Capture only the engine's output; serialize concurrent writes as records."""
    output = []
    lock = Lock()

    def sink(value, *args, **kwargs):
        with lock:
            output.append((value, args, kwargs))

    monkeypatch.setattr(timing, "print", sink, raising=False)
    return output


def _records(output):
    rows = []
    for value, args, kwargs in output:
        assert type(value) is str
        assert args == ()
        assert kwargs == {"flush": True}
        rows.append(json.loads(value))
    for row in rows:
        assert set(row) == SCHEMA_KEYS
        assert row["event"] == "operational_phase"
        assert row["domain"] in timing.PHASES
        assert row["phase"] in timing.PHASES[row["domain"]]
        assert re.fullmatch(r"[0-9a-f]{16}", row["trace"])
        assert row["parent"] is None or re.fullmatch(r"[0-9a-f]{16}", row["parent"])
        assert row["point"] in {"begin", "end"}
        assert type(row["offset_ms"]) is int and row["offset_ms"] >= 0
        if row["point"] == "begin":
            assert row["duration_ms"] is None
        else:
            assert type(row["duration_ms"]) is int and row["duration_ms"] >= 0
        assert row["in_transaction"] is None
        assert row["error"] in {None, "ERROR"}
        assert type(row["dropped_records"]) is int
        assert row["dropped_records"] == 0
    text = "\n".join(value for value, _args, _kwargs in output)
    for marker in PRIVATE_MARKERS:
        assert marker not in text
    return rows


def _points(rows):
    return [(row["phase"], row["point"]) for row in rows]


def _expected_points(phases):
    return (
        [("operation", "begin")]
        + [(label, point) for label in phases for point in ("begin", "end")]
        + [("operation", "end")]
    )


def test_calendar_success_has_twelve_closed_records_and_preserves_result(calendar_output):
    assert timing.PHASES[DOMAIN] == frozenset(("operation", *CALLBACK_PHASES))
    assert timing.trace_id(DOMAIN) is None
    marker = object()
    payload = {"private_values": PRIVATE_MARKERS}
    invocations = []

    @timing.operation(DOMAIN)
    def call(argument, *, query):
        invocations.append((argument, query))
        for label in CALLBACK_PHASES:
            with timing.phase(DOMAIN, label):
                assert timing.trace_id(DOMAIN) is not None
        return marker

    assert call(payload, query=PRIVATE_MARKERS[1]) is marker
    assert len(invocations) == 1
    assert invocations[0][0] is payload
    assert invocations[0][1] == PRIVATE_MARKERS[1]
    assert timing.trace_id(DOMAIN) is None
    rows = _records(calendar_output)
    assert len(rows) == 12
    assert _points(rows) == _expected_points(CALLBACK_PHASES)
    assert {row["domain"] for row in rows} == {DOMAIN}
    assert len({row["trace"] for row in rows}) == 1
    assert all(row["parent"] is None and row["error"] is None for row in rows)


@pytest.mark.parametrize("failed_phase", CALLBACK_PHASES)
def test_each_calendar_phase_preserves_original_exception_and_excludes_private_text(
    calendar_output, failed_phase,
):
    problem = RuntimeError(" | ".join(PRIVATE_MARKERS))
    invocations, entered = [], []
    payload = {"private_values": PRIVATE_MARKERS}

    @timing.operation(DOMAIN)
    def call(argument):
        invocations.append(argument)
        for label in CALLBACK_PHASES:
            with timing.phase(DOMAIN, label):
                entered.append(label)
                if label == failed_phase:
                    raise problem

    assert timing.trace_id(DOMAIN) is None
    with pytest.raises(RuntimeError) as caught:
        call(payload)
    assert caught.value is problem
    assert len(invocations) == 1 and invocations[0] is payload
    prefix = CALLBACK_PHASES[:CALLBACK_PHASES.index(failed_phase) + 1]
    assert entered == list(prefix)
    assert timing.trace_id(DOMAIN) is None
    rows = _records(calendar_output)
    assert _points(rows) == _expected_points(prefix)
    assert len({row["trace"] for row in rows}) == 1
    assert all(row["domain"] == DOMAIN and row["parent"] is None for row in rows)
    for row in rows:
        expected = "ERROR" if (
            row["point"] == "end" and row["phase"] in {failed_phase, "operation"}
        ) else None
        assert row["error"] == expected


@pytest.mark.parametrize("failed_binding", ("print", "json"))
@pytest.mark.parametrize("business_fails", (False, True))
def test_ordinary_emission_failure_preserves_outcome_and_later_context(
    monkeypatch, calendar_output, capsys, failed_binding, business_fails,
):
    marker = object()
    problem = ValueError(" | ".join(PRIVATE_MARKERS))
    invocations, emission_attempts = [], []

    def broken(*_args, **_kwargs):
        emission_attempts.append(True)
        if failed_binding == "print":
            raise OSError("SYNTHETIC_SECRET_20261028")
        raise ValueError("SYNTHETIC_SECRET_20261028")

    @timing.operation(DOMAIN)
    def call():
        invocations.append(True)
        with timing.phase(DOMAIN, "provider_context"):
            if business_fails:
                raise problem
            return marker

    assert timing.trace_id(DOMAIN) is None
    with monkeypatch.context() as injected:
        if failed_binding == "print":
            injected.setattr(timing, "print", broken, raising=False)
        else:
            # Replace this module's json binding, not json.dumps on shared stdlib.
            injected.setattr(timing, "json", SimpleNamespace(dumps=broken))
        if business_fails:
            with pytest.raises(ValueError) as caught:
                call()
            assert caught.value is problem
        else:
            assert call() is marker
        assert timing.trace_id(DOMAIN) is None
    assert invocations == [True]
    assert emission_attempts
    assert calendar_output == []
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""

    @timing.operation(DOMAIN)
    def healthy():
        with timing.phase(DOMAIN, "provider_context"):
            return marker

    assert healthy() is marker
    assert timing.trace_id(DOMAIN) is None
    rows = _records(calendar_output)
    assert _points(rows) == _expected_points(("provider_context",))
    assert len({row["trace"] for row in rows}) == 1
    assert all(row["parent"] is None and row["error"] is None for row in rows)


@pytest.mark.parametrize("child_fails", (False, True))
def test_nested_calendar_context_restores_parent_after_success_or_failure(
    calendar_output, child_fails,
):
    traces = {}
    marker = object()
    problem = RuntimeError(" | ".join(PRIVATE_MARKERS))

    @timing.operation(DOMAIN)
    def child():
        traces["child"] = timing.trace_id(DOMAIN)
        with timing.phase(DOMAIN, "provider_context"):
            assert traces["child"] != traces["parent"]
            if child_fails:
                raise problem
            return marker

    @timing.operation(DOMAIN)
    def parent():
        traces["parent"] = timing.trace_id(DOMAIN)
        assert timing.trace_id("media_request") == traces["outer"]
        with timing.phase(DOMAIN, "sports_context"):
            if child_fails:
                with pytest.raises(RuntimeError) as caught:
                    child()
                assert caught.value is problem
            else:
                assert child() is marker
            assert timing.trace_id(DOMAIN) == traces["parent"]
            assert timing.trace_id("media_request") == traces["outer"]
        return marker

    @timing.operation("media_request")
    def outer():
        traces["outer"] = timing.trace_id("media_request")
        assert timing.trace_id(DOMAIN) is None
        assert parent() is marker
        assert timing.trace_id(DOMAIN) is None
        assert timing.trace_id("media_request") == traces["outer"]
        return marker

    assert timing.trace_id(DOMAIN) is timing.trace_id("media_request") is None
    assert outer() is marker
    assert timing.trace_id(DOMAIN) is timing.trace_id("media_request") is None
    assert len(set(traces.values())) == 3
    rows = _records(calendar_output)
    assert len(rows) == 10
    for name, expected_parent, phases in (
        ("outer", None, ()),
        ("parent", traces["outer"], ("sports_context",)),
        ("child", traces["parent"], ("provider_context",)),
    ):
        scoped = [row for row in rows if row["trace"] == traces[name]]
        assert _points(scoped) == _expected_points(phases)
        assert all(row["parent"] == expected_parent for row in scoped)
        for row in scoped:
            expected = "ERROR" if (
                name == "child" and child_fails and row["point"] == "end"
            ) else None
            assert row["error"] == expected


def test_calendar_concurrent_calls_and_reused_threads_leave_no_context(calendar_output):
    def worker(barrier, business_fails):
        assert timing.trace_id(DOMAIN) is timing.trace_id("media_request") is None
        marker = object()
        problem = RuntimeError(" | ".join(PRIVATE_MARKERS))
        active_trace = []

        @timing.operation(DOMAIN)
        def call():
            active_trace.append(timing.trace_id(DOMAIN))
            with timing.phase(DOMAIN, "calendar_context"):
                barrier.wait(timeout=15)
                assert timing.trace_id(DOMAIN) == active_trace[0]
                if business_fails:
                    raise problem
                return marker

        if business_fails:
            with pytest.raises(RuntimeError) as caught:
                call()
            assert caught.value is problem
        else:
            assert call() is marker
        assert timing.trace_id(DOMAIN) is timing.trace_id("media_request") is None
        assert len(active_trace) == 1
        return get_ident(), active_trace[0], business_fails

    rounds = []
    # Barriers force both workers to participate in every round; subsequent
    # rounds therefore verify reuse of the same two worker threads.
    with ThreadPoolExecutor(max_workers=2) as pool:
        for business_fails in (False, True, False):
            barrier = Barrier(2)
            futures = [pool.submit(worker, barrier, business_fails) for _ in range(2)]
            rounds.append([future.result(timeout=30) for future in futures])
    assert timing.trace_id(DOMAIN) is timing.trace_id("media_request") is None
    first_workers = {thread_id for thread_id, _trace, _failed in rounds[0]}
    assert len(first_workers) == 2
    assert all(
        {thread_id for thread_id, _trace, _failed in results} == first_workers
        for results in rounds
    )
    outcomes = {trace: failed for results in rounds for _thread, trace, failed in results}
    assert len(outcomes) == 6
    rows = _records(calendar_output)
    assert len(rows) == 24
    assert {row["trace"] for row in rows} == set(outcomes)
    assert all(row["domain"] == DOMAIN and row["parent"] is None for row in rows)
    for trace, failed in outcomes.items():
        scoped = [row for row in rows if row["trace"] == trace]
        assert _points(scoped) == _expected_points(("calendar_context",))
        for row in scoped:
            assert row["error"] == ("ERROR" if failed and row["point"] == "end" else None)


def test_inactive_and_unknown_calendar_labels_never_expose_supplied_text(calendar_output):
    assert timing.trace_id(DOMAIN) is None
    for label in CALLBACK_PHASES:
        with timing.phase(DOMAIN, label):
            pass
    assert calendar_output == []
    marker = object()

    @timing.operation(DOMAIN)
    def call():
        with timing.phase(DOMAIN, " | ".join(PRIVATE_MARKERS)):
            return marker

    assert call() is marker
    assert timing.trace_id(DOMAIN) is None
    rows = _records(calendar_output)
    assert _points(rows) == _expected_points(())
    assert all(row["domain"] == DOMAIN and row["parent"] is None for row in rows)

