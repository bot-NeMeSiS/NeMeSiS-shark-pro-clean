"""Bounded receipts preserve failure-time pending work without secrets."""
import json
from tools.browser_network_diagnostics import BrowserNetworkDiagnostics


class Request:
    method = "GET"
    resource_type = "fetch"
    url = "http://username:password@example.invalid/api/state?token=private#secret"
    def is_navigation_request(self):
        return False
    @property
    def headers(self):
        raise AssertionError("headers must never be read")
    @property
    def post_data(self):
        raise AssertionError("payload must never be read")


def test_failure_freezes_pending_before_later_completion():
    trace = BrowserNetworkDiagnostics()
    trace.set_case(768, "client", "/app")
    request = Request()
    trace.request_started(request)
    trace.capture_failure("TimeoutError", phase="networkidle", timeout_ms=12000)
    trace.request_finished(request)
    result = trace.snapshot()
    assert result["pending"] == []
    assert len(result["failure"]["pending"]) == 1
    assert result["failure"]["case"] == {"width":768, "role":"client", "path":"/app"}
    assert result["failure"]["timeout_ms"] == 12000
    assert [row["event"] for row in result["events"]] == ["request", "requestfinished"]
    serialized = json.dumps(result)
    assert all(secret not in serialized for secret in ("username", "password", "private", "secret", "token="))
    assert result["events"][0]["path"] == "/api/state"


def test_later_case_does_not_relabel_old_request_or_snapshot():
    trace = BrowserNetworkDiagnostics()
    trace.set_case(768, "client", "/app")
    request = Request()
    trace.request_started(request)
    result = trace.snapshot()
    trace.set_case(1440, "admin", "/admin/users")
    trace.request_failed(request)
    assert trace.snapshot()["events"][-1]["case"]["path"] == "/app"
    result["pending"][0]["case"]["path"] = "changed"
    assert trace.snapshot()["events"][0]["case"]["path"] == "/app"


def test_history_overflow_is_bounded_and_explicit():
    trace = BrowserNetworkDiagnostics()
    for _ in range(300):
        request = Request()
        trace.request_started(request)
        trace.request_finished(request)
    result = trace.snapshot()
    assert len(result["events"]) == 512
    assert result["dropped_events"] == 88
    assert result["complete_history"] is False
    assert result["pending"] == []


def test_pending_overflow_and_unmatched_terminal_are_not_hidden():
    trace = BrowserNetworkDiagnostics()
    requests = [Request() for _ in range(129)]
    for request in requests:
        trace.request_started(request)
    trace.request_finished(requests[-1])
    result = trace.snapshot()
    assert len(result["pending"]) == 128
    assert result["untracked_requests"] == 1
    assert result["unmatched_terminal_events"] == 1
    assert result["complete_history"] is False
