"""A failed first sports observation must remain diagnosable and fail closed."""
from datetime import timedelta
from hashlib import sha256
import json
import urllib.error

import pytest

from tools import v937_post_deploy_certification as cert


@pytest.fixture
def probe(monkeypatch):
    """Exercise the complete probe with an offline HTTP transport."""
    css = ".qa { color: #fff; }"
    href = "/static/product-system.css?v=" + cert.ACTIVE_VERSION + "-home-leagues-1"
    monkeypatch.setattr(cert, "css_digest", lambda root: sha256(css.encode()).hexdigest())

    def run(first_response=None, sports_changes=None, missing_fields=()):
        sports = {
            "matches": [], "live": [], "counts": {"live": 0, "stale_live": 0},
            "no_external_calls": True, "poll_after_seconds": 180,
            "last_safe_sync": cert.datetime.now(cert.MADRID).isoformat(),
            "provider_status": "cached",
        }
        sports.update(sports_changes or {})
        for field in missing_fields:
            if field.startswith("counts."):
                sports["counts"].pop(field.split(".", 1)[1], None)
            else:
                sports.pop(field, None)
        runtime = {
            "version": cert.ACTIVE_VERSION, "git_commit_hint": "a" * 40,
            "version_files_match": True, "deployment_alignment_status": "aligned_local_files",
        }
        calls = []

        def request(base, path, timeout=30):
            calls.append(path)
            payload = {
                "/api/runtime-version?compact=1": runtime,
                "/api/realtime/sports": sports,
                "/manifest.json": {"name": "QA"},
            }.get(path)
            body = json.dumps(payload) if payload is not None else '<link rel="stylesheet" href="' + href + '">'
            if path == href:
                body = css
            elif path == "/service-worker.js":
                body = cert.EXPECTED_CACHE
            response = {
                "path": path, "status": 404 if path == "/ruta-inventada" else 200,
                "latency_ms": 1, "body": body, "final_url": base + path, "error": None,
            }
            if path == "/api/realtime/sports" and calls.count(path) == 1 and first_response:
                response.update(first_response)
            return response

        monkeypatch.setattr(cert, "_request", request)
        result = cert._probe("https://qa.invalid", "offline", cert.ACTIVE_VERSION, "a" * 40)
        return result, calls

    return run


@pytest.mark.parametrize("first_response,kind,error_type,error", [
    ({"status": 0, "body": "", "error": "TimeoutError"}, "transport", "TimeoutError", "sports_api_http_failure"),
    ({"status": 0, "body": "", "error": "URLError"}, "transport", "URLError", "sports_api_http_failure"),
    ({"status": 429, "body": '{"message":"private-response-marker"}'}, "http", "HTTPError", "sports_api_http_failure"),
    ({"status": 503, "body": "private-response-marker"}, "http", "HTTPError", "sports_api_http_failure"),
    ({"status": 200, "body": "<html>private-response-marker</html>"}, "json_decode", "JSONDecodeError", "sports_api_json_invalid"),
    ({"status": 200, "body": ""}, "json_decode", "JSONDecodeError", "sports_api_json_invalid"),
    ({"status": 200, "body": "[]"}, "json_shape", "JSONNotObject", "sports_api_payload_not_object"),
    ({"status": 200, "body": "null"}, "json_shape", "JSONNotObject", "sports_api_payload_not_object"),
    ({"status": 200, "body": '"private-response-marker"'}, "json_shape", "JSONNotObject", "sports_api_payload_not_object"),
])
def test_first_failure_survives_later_success_without_secondary_contract_errors(
    probe, first_response, kind, error_type, error,
):
    first_response = dict(first_response, latency_ms=30001,
                          final_url="https://qa.invalid/?token=private-redirect-marker")
    result, calls = probe(first_response)

    assert result["status"] == "FAIL"
    assert result["errors"] == [error]
    # The later route check succeeds. It must not replace the initial evidence.
    assert calls.count("/api/realtime/sports") == 2
    later = next(item for item in result["routes"] if item["path"] == "/api/realtime/sports")
    assert later["status"] == 200 and later["latency_ms"] == 1
    evidence = result["sports_probe"]
    assert evidence["status"] == first_response["status"]
    assert evidence["latency_ms"] == 30001
    assert evidence["failure_kind"] == kind
    assert evidence["error_type"] == error_type
    assert evidence["payload_evaluable"] is False
    assert evidence["contract_status"] == "NOT_EVALUATED"
    for field in ("matches", "live", "stale_live_diagnostic", "public_stale_live", "false_live",
                  "poll_after_seconds", "last_safe_sync", "sync_age_seconds", "provider_status"):
        assert result[field] is None, field
    serialized = json.dumps(result)
    assert "private-response-marker" not in serialized
    assert "private-redirect-marker" not in serialized
    assert "body" not in evidence and "final_url" not in evidence


def test_unexpected_transport_details_are_not_written_to_report(probe):
    result, _ = probe({"status": 0, "body": "private-response-marker",
                       "error": "TimeoutError: private-exception-marker"})
    assert result["status"] == "FAIL"
    assert result["sports_probe"]["error_type"] == "TransportError"
    assert "private-exception-marker" not in json.dumps(result)


@pytest.mark.parametrize("exception", [
    TimeoutError("private-exception-marker"),
    urllib.error.URLError("private-exception-marker"),
])
def test_actual_request_boundary_discards_transport_exception_messages(monkeypatch, exception):
    def unavailable(*args, **kwargs):
        raise exception

    monkeypatch.setattr(cert.urllib.request, "urlopen", unavailable)
    payload, response = cert._json_response("https://qa.invalid", "/api/realtime/sports")
    assert payload == {}
    assert response["status"] == 0
    assert response["error"] == type(exception).__name__
    assert response["body"] == ""
    assert "private-exception-marker" not in json.dumps(response)


@pytest.mark.parametrize("changes,error", [
    ({"no_external_calls": False}, "sports_render_external_call_guard_missing"),
    ({"poll_after_seconds": 45}, "polling_interval_mismatch"),
    ({"last_safe_sync": None}, "sports_last_sync_missing"),
    ({"counts": {"live": 1, "stale_live": 0}}, "live_counter_mismatch"),
    ({"matches": [{"is_stale": True}]}, "public_stale_live:1"),
    ({"live": [{"is_live": False}], "counts": {"live": 1, "stale_live": 0}, "poll_after_seconds": 45}, "false_live:1"),
])
def test_valid_json_with_real_contract_failure_remains_failed(probe, changes, error):
    result, _ = probe(sports_changes=changes)
    assert result["status"] == "FAIL"
    assert result["errors"] == [error]
    assert result["sports_probe"]["payload_evaluable"] is True
    assert result["sports_probe"]["contract_status"] == "FAIL"
    assert result["sports_probe"]["failure_kind"] is None


def test_empty_object_is_rejected_without_inventing_observed_metrics(probe):
    result, _ = probe({"body": "{}"})
    assert result["status"] == "FAIL"
    assert result["sports_probe"]["payload_evaluable"] is False
    assert result["sports_probe"]["contract_status"] == "FAIL"
    assert set(result["errors"]) == {
        "sports_api_schema_invalid:matches", "sports_api_schema_invalid:live", "sports_api_schema_invalid:counts",
    }
    assert result["matches"] is None and result["live"] is None


def test_stale_successful_payload_still_fails_freshness_gate(probe):
    stale = (cert.datetime.now(cert.MADRID) - timedelta(minutes=25)).isoformat()
    result, _ = probe(sports_changes={"last_safe_sync": stale})
    assert result["status"] == "FAIL"
    assert result["errors"] == ["sports_data_stale"]
    assert result["sports_probe"]["contract_status"] == "FAIL"


def test_successful_probe_keeps_normal_metrics_and_passes(probe):
    result, _ = probe()
    assert result["status"] == "PASS" and result["errors"] == []
    assert result["sports_probe"]["payload_evaluable"] is True
    assert result["sports_probe"]["contract_status"] == "PASS"
    assert result["sports_probe"]["failure_kind"] is None
    assert result["sports_probe"]["error_type"] is None
    assert result["matches"] == result["live"] == result["false_live"] == 0
    assert result["poll_after_seconds"] == 180
    assert result["last_safe_sync"]


@pytest.mark.parametrize("changes,field", [
    ({"matches": {"private-payload-marker": []}}, "matches"),
    ({"matches": "private-payload-marker"}, "matches"),
    ({"matches": 7}, "matches"),
    ({"matches": False}, "matches"),
    ({"matches": None}, "matches"),
    ({"matches": [None, {"is_stale": False}]}, "matches"),
    ({"live": {"private-payload-marker": []}}, "live"),
    ({"live": "private-payload-marker"}, "live"),
    ({"live": 7}, "live"),
    ({"live": False}, "live"),
    ({"live": None}, "live"),
    ({"live": ["private-payload-marker"]}, "live"),
    ({"counts": [1]}, "counts"),
    ({"counts": "private-payload-marker"}, "counts"),
    ({"counts": False}, "counts"),
    ({"counts": None}, "counts"),
    ({"counts": {"live": "private-payload-marker", "stale_live": 0}}, "counts.live"),
    ({"counts": {"live": "0", "stale_live": 0}}, "counts.live"),
    ({"counts": {"live": False, "stale_live": 0}}, "counts.live"),
    ({"counts": {"live": 0.5, "stale_live": 0}}, "counts.live"),
    ({"counts": {"live": -1, "stale_live": 0}}, "counts.live"),
    ({"counts": {"live": None, "stale_live": 0}}, "counts.live"),
    ({"counts": {"live": 0, "stale_live": "private-payload-marker"}}, "counts.stale_live"),
    ({"counts": {"live": 0, "stale_live": True}}, "counts.stale_live"),
    ({"counts": {"live": 0, "stale_live": -1}}, "counts.stale_live"),
    ({"counts": {"live": 0, "stale_live": None}}, "counts.stale_live"),
    ({"poll_after_seconds": "180"}, "poll_after_seconds"),
    ({"poll_after_seconds": {"private-payload-marker": 180}}, "poll_after_seconds"),
    ({"poll_after_seconds": True}, "poll_after_seconds"),
    ({"poll_after_seconds": 180.5}, "poll_after_seconds"),
    ({"poll_after_seconds": None}, "poll_after_seconds"),
    ({"last_safe_sync": {"private-payload-marker": "date"}}, "last_safe_sync"),
    ({"last_safe_sync": True}, "last_safe_sync"),
    ({"provider_status": ["private-payload-marker"]}, "provider_status"),
    ({"provider_status": False}, "provider_status"),
])
def test_malformed_nested_payload_is_reported_without_false_zero_or_exception(probe, changes, field):
    result, calls = probe(sports_changes=changes)

    assert result["status"] == "FAIL"
    assert result["errors"] == ["sports_api_schema_invalid:" + field]
    evidence = result["sports_probe"]
    assert evidence["status"] == 200 and evidence["json_state"] == "object"
    assert evidence["failure_kind"] == "json_schema"
    assert evidence["error_type"] == "JSONContractShape"
    assert evidence["payload_evaluable"] is False
    assert evidence["contract_status"] == "FAIL"
    for name in ("matches", "live", "stale_live_diagnostic", "public_stale_live", "false_live",
                 "poll_after_seconds", "last_safe_sync", "sync_age_seconds", "provider_status"):
        assert result[name] is None, name
    assert "private-payload-marker" not in json.dumps(result)
    assert calls.count("/api/realtime/sports") == 2
    assert len(result["routes"]) == len(cert.PUBLIC_ROUTES)


def test_schema_failure_remains_after_a_later_valid_sports_response(probe):
    malformed = {
        "matches": "private-payload-marker", "live": [], "counts": {"live": 0, "stale_live": 0},
        "no_external_calls": True, "poll_after_seconds": 180,
        "last_safe_sync": cert.datetime.now(cert.MADRID).isoformat(), "provider_status": "cached",
    }
    result, calls = probe({"body": json.dumps(malformed)})
    assert result["status"] == "FAIL"
    assert result["errors"] == ["sports_api_schema_invalid:matches"]
    assert result["matches"] is None and result["live"] is None
    assert calls.count("/api/realtime/sports") == 2
    assert next(item for item in result["routes"] if item["path"] == "/api/realtime/sports")["status"] == 200
    assert "private-payload-marker" not in json.dumps(result)


@pytest.mark.parametrize("missing_fields,invalid_fields", [
    (("matches",), ("matches",)),
    (("live",), ("live",)),
    (("counts",), ("counts",)),
    (("matches", "live", "counts"), ("matches", "live", "counts")),
    (("counts.live",), ("counts.live",)),
    (("counts.stale_live",), ("counts.stale_live",)),
    (("counts.live", "counts.stale_live"), ("counts.live", "counts.stale_live")),
])
def test_missing_required_sports_evidence_cannot_be_certified_as_empty(probe, missing_fields, invalid_fields):
    result, _calls = probe(missing_fields=missing_fields)
    assert result["status"] == "FAIL"
    assert result["errors"] == ["sports_api_schema_invalid:" + field for field in invalid_fields]
    assert result["sports_probe"]["payload_evaluable"] is False
    assert result["sports_probe"]["contract_status"] == "FAIL"
    assert result["matches"] is None and result["live"] is None
    assert result["stale_live_diagnostic"] is None
    assert len(result["routes"]) == len(cert.PUBLIC_ROUTES)


@pytest.mark.parametrize("timestamp", ["0001-01-01T00:00:00+14:00", "9999-12-31T23:59:59-14:00"])
def test_out_of_range_timezone_timestamp_preserves_the_diagnostic(probe, timestamp):
    assert cert._parse_timestamp(timestamp) is None
    result, _calls = probe(sports_changes={"last_safe_sync": timestamp})
    assert result["status"] == "FAIL"
    assert result["errors"] == ["sports_last_sync_missing"]
    assert result["sync_age_seconds"] is None
    assert len(result["routes"]) == len(cert.PUBLIC_ROUTES)
