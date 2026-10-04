from __future__ import annotations

import importlib.util
import io
import json
import socket
import urllib.error
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "render_cron_master_tick.py"
SPEC = importlib.util.spec_from_file_location("render_cron_master_tick", MODULE_PATH)
master = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(master)


class MockResponse:
    def __init__(self, payload: dict, status: int = 200):
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def read(self, _limit: int = -1) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def run_master(monkeypatch, capsys, outcomes, secret: str = "pytest-master-secret", backup_is_due: bool = False, postmatch_outcome=None, highlights_outcome=None):
    calls = []

    def fake_urlopen(request, timeout):
        if request.full_url.endswith(master.READINESS_ENDPOINT):
            return MockResponse({"ok": True, "version": "SIMULATED_QA"})
        if master.HIGHLIGHTS_ENDPOINT in request.full_url:
            if isinstance(highlights_outcome, BaseException):
                raise highlights_outcome
            return highlights_outcome or MockResponse({
                "ok": True,
                "highlights_sync": {
                    "ok": True,
                    "skipped": True,
                    "reason": "fresh_sync_window",
                    "external_calls": 0,
                },
            })
        calls.append({"request": request, "timeout": timeout})
        if request.full_url.endswith('/api/automation/postmatch/tick'):
            if isinstance(postmatch_outcome, BaseException):
                raise postmatch_outcome
            return postmatch_outcome or MockResponse({'ok': True, 'result': 'SKIPPED_DISABLED', 'processed': 0})
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("AUTOMATION_SECRET", secret)
    monkeypatch.setattr(master, "backup_due", lambda _utc_now: backup_is_due)
    monkeypatch.setattr(master.urllib.request, "urlopen", fake_urlopen)
    return_code = master.main()
    output = capsys.readouterr().out.strip()
    return return_code, json.loads(output), calls, output


def telegram_ok(status: str = "QUEUE_EMPTY") -> MockResponse:
    return MockResponse({"ok": True, "status": status, "sent": 0})


def evolution_ok(result: str = "PASS") -> MockResponse:
    return MockResponse({"ok": True, "result": result, "safe_mode": "PASS", "storage": "PASS"})


def backup_ok(status: str = "PASS", created: bool = True) -> MockResponse:
    return MockResponse({"ok": True, "status": status, "backup_created": created})


def test_backup_window_is_utc_and_bounded():
    assert master.backup_due("2026-09-26T02:30:00+00:00") is True
    assert master.backup_due("2026-09-26T04:29:59+00:00") is True
    assert master.backup_due("2026-09-26T02:29:59+00:00") is False
    assert master.backup_due("2026-09-26T04:30:00+00:00") is False


def test_master_calls_backup_only_when_due(monkeypatch, capsys):
    return_code, payload, calls, _output = run_master(
        monkeypatch,
        capsys,
        [telegram_ok(), evolution_ok(), backup_ok()],
        backup_is_due=True,
    )
    assert return_code == 0
    assert payload["overall"] == "PASS"
    assert payload["backup_status"] == "PASS"
    assert payload["backup"]["backup_created"] is True
    assert len(calls) == 4
    assert calls[2]["request"].get_method() == "POST"
    assert calls[2]["request"].full_url.endswith(master.BACKUP_ENDPOINT)
    assert calls[2]["request"].headers["X-automation-secret"] == "pytest-master-secret"


@pytest.mark.parametrize("evolution_result", ["PASS", "SKIPPED_NOT_DUE", "SKIPPED_ALREADY_RUNNING"])
def test_master_passes_for_telegram_and_valid_evolution_results(monkeypatch, capsys, evolution_result):
    return_code, payload, calls, _output = run_master(
        monkeypatch,
        capsys,
        [telegram_ok(), evolution_ok(evolution_result)],
    )
    assert return_code == 0
    assert payload["overall"] == "PASS"
    assert payload["telegram_status"] == "PASS"
    assert payload["continuous_evolution_status"] == "PASS"
    assert payload["duration_ms"] >= 0
    assert payload["telegram"]["telegram_status"] == "PASS"
    assert payload["continuous_evolution"]["continuous_status"] == "PASS"
    assert payload["continuous_evolution"]["continuous_result"] == ("RUN" if evolution_result == "PASS" else evolution_result)
    assert len(calls) == 3
    assert len(_output.splitlines()) == 1


def test_master_partial_when_telegram_fails_and_evolution_still_runs(monkeypatch, capsys):
    return_code, payload, calls, _output = run_master(
        monkeypatch,
        capsys,
        [urllib.error.URLError("telegram unavailable"), evolution_ok()],
    )
    assert return_code == 2
    assert payload["overall"] == "FAIL"
    assert payload["telegram"]["telegram_status"] == "FAIL"
    assert payload["continuous_evolution"]["continuous_result"] == "RUN"
    assert len(calls) == 3


def test_master_partial_when_evolution_fails_and_telegram_is_preserved(monkeypatch, capsys):
    return_code, payload, calls, _output = run_master(
        monkeypatch,
        capsys,
        [telegram_ok("NO_DUE_JOBS"), urllib.error.URLError("evolution unavailable")],
    )
    assert return_code == 2
    assert payload["overall"] == "FAIL"
    assert payload["telegram"]["telegram_result"] == "NO_DUE_JOBS"
    assert payload["continuous_evolution"]["continuous_status"] == "FAIL"
    assert len(calls) == 3


def test_master_fails_when_both_calls_fail(monkeypatch, capsys):
    return_code, payload, calls, _output = run_master(
        monkeypatch,
        capsys,
        [urllib.error.URLError("telegram unavailable"), urllib.error.URLError("evolution unavailable")],
    )
    assert return_code == 2
    assert payload["overall"] == "FAIL"
    assert len(calls) == 3


@pytest.mark.parametrize(
    ("missing", "expected"),
    [("AUTOMATION_SECRET", "MISSING_AUTOMATION_SECRET"), ("PUBLIC_BASE_URL", "MISSING_PUBLIC_BASE_URL")],
)
def test_master_missing_configuration_fails_without_http(monkeypatch, capsys, missing, expected):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("AUTOMATION_SECRET", "pytest-master-secret")
    monkeypatch.delenv(missing, raising=False)
    monkeypatch.setattr(master.urllib.request, "urlopen", lambda *_args, **_kwargs: pytest.fail("HTTP must not run"))
    return_code = master.main()
    payload = json.loads(capsys.readouterr().out)
    assert return_code == 2
    assert payload["overall"] == "FAIL"
    assert payload["telegram_status"] == "NOT_EXECUTED"
    assert payload["continuous_evolution_status"] == "NOT_EXECUTED"
    assert payload["duration_ms"] >= 0
    assert payload["telegram"]["telegram_result"] == expected
    assert payload["continuous_evolution"]["continuous_result"] == expected


def test_telegram_timeout_does_not_block_evolution(monkeypatch, capsys):
    return_code, payload, calls, _output = run_master(
        monkeypatch,
        capsys,
        [socket.timeout("telegram timeout"), evolution_ok()],
    )
    assert return_code == 2
    assert payload["telegram"]["telegram_result"] == "TIMEOUT"
    assert payload["continuous_evolution"]["continuous_result"] == "RUN"
    assert len(calls) == 3


def test_evolution_timeout_preserves_telegram(monkeypatch, capsys):
    return_code, payload, calls, _output = run_master(
        monkeypatch,
        capsys,
        [telegram_ok("QUEUE_EMPTY"), socket.timeout("evolution timeout")],
    )
    assert return_code == 2
    assert payload["telegram"]["telegram_result"] == "QUEUE_EMPTY"
    assert payload["continuous_evolution"]["continuous_result"] == "TIMEOUT"
    assert len(calls) == 3


def test_unexpected_telegram_exception_still_allows_evolution(monkeypatch, capsys):
    monkeypatch.setattr(
        master,
        "wait_for_web_ready",
        lambda _base_url: {
            "readiness_status": "PASS",
            "readiness_http": 200,
            "readiness_result": "WEB_READY",
            "readiness_attempts": 1,
            "readiness_duration_ms": 1,
        },
    )
    monkeypatch.setattr(master, "telegram_tick", lambda *_args: (_ for _ in ()).throw(RuntimeError("sensitive detail")))
    monkeypatch.setattr(
        master,
        "continuous_evolution_tick",
        lambda *_args: {
            "continuous_http": 200,
            "continuous_status": "PASS",
            "continuous_result": "RUN",
            "continuous_duration_ms": 1,
        },
    )
    monkeypatch.setattr(
        master,
        "highlights_tick",
        lambda *_args: {
            "highlights_http": 200,
            "highlights_status": "PASS",
            "highlights_result": "fresh_sync_window",
            "highlights_duration_ms": 1,
        },
    )
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("AUTOMATION_SECRET", "pytest-master-secret")
    return_code = master.main()
    payload = json.loads(capsys.readouterr().out)
    assert return_code == 2
    assert payload["overall"] == "FAIL"
    assert payload["telegram"]["telegram_result"] == "RuntimeError"
    assert payload["continuous_evolution"]["continuous_result"] == "RUN"
    assert "sensitive detail" not in json.dumps(payload)


def test_secret_is_header_only_and_never_appears_in_output(monkeypatch, capsys):
    secret = "pytest-super-sensitive-master-secret"
    return_code, payload, calls, output = run_master(
        monkeypatch,
        capsys,
        [
            MockResponse({"ok": True, "status": secret}),
            MockResponse({"ok": True, "result": secret}),
        ],
        secret=secret,
    )
    assert return_code == 2
    assert payload["overall"] == "FAIL"
    assert secret not in output
    assert secret not in json.dumps(payload)
    assert len(calls) == 3
    assert all(call["request"].headers["X-automation-secret"] == secret for call in calls)
    assert all(secret not in call["request"].full_url for call in calls)
    assert calls[0]["request"].get_method() == "POST"
    assert calls[0]["request"].full_url.endswith("/api/automation/telegram/tick")
    assert calls[0]["request"].data == b"{}"
    assert calls[0]["request"].headers["Content-type"] == "application/json"
    assert calls[1]["request"].get_method() == "POST"
    assert calls[1]["request"].full_url.endswith("/api/automation/continuous-evolution/tick")
    assert calls[0]["timeout"] == master.TELEGRAM_TIMEOUT_SECONDS
    assert calls[1]["timeout"] == master.CONTINUOUS_EVOLUTION_TIMEOUT_SECONDS


def test_master_logs_only_sanitized_sports_pipeline_evidence(monkeypatch, capsys):
    secret = "pytest-super-sensitive-master-secret"
    telegram = MockResponse(
        {
            "ok": True,
            "status": "PASS",
            "sports_pipeline": {
                "status": "OK",
                "deep_status": "SKIPPED_NOT_DUE",
                "deep_external_calls": 0,
                "provider_authenticated": True,
                "provider_plan": "Free",
                "quota": {"daily_limit": 100, "daily_used": 7, "daily_remaining": 93},
                "capabilities": {
                    "lineups": {"requested": True, "received": 2, "persisted": 2},
                    secret: {"requested": True, "received": 1, "persisted": 1},
                },
                "last_sample": {
                    "status": "OK",
                    "finished_at": "2026-09-01T15:20:00+00:00",
                    "external_calls": 7,
                    "fixture_ids": ["9001", secret],
                    "source": "LAST_PERSISTED_DEEP_SAMPLE",
                    "scope": "DEEP_ENRICHMENT",
                    "is_current_job": False,
                    "freshness_state": "HISTORICAL_SAMPLE_AGE_UNASSESSED",
                },
                "job_execution": {
                    "state": "OK",
                    "ok": True,
                    "external_calls": 0,
                    "processed": 1,
                    "scope": "CURRENT_SPORTS_SYNC",
                },
                "provider_access": {
                    "provider": "API-Football",
                    "state": "AUTHENTICATED",
                    "configured": True,
                    "authenticated": True,
                    "checked_at": "2026-09-01T15:20:00+00:00",
                    "source": "LAST_PERSISTED_DEEP_SAMPLE",
                },
                "quota_observation": {
                    "state": "OBSERVED",
                    "values": {"daily_remaining": 93},
                    "observed_at": "2026-09-01T15:20:00+00:00",
                    "source": "LAST_PERSISTED_DEEP_SAMPLE",
                    "freshness": "LAST_OBSERVED_NOT_CURRENT",
                },
                "coverage": {
                    "provider": "API-Football",
                    "source": "LAST_PERSISTED_DEEP_SAMPLE",
                    "observed_at": "2026-09-01T15:20:00+00:00",
                    "capabilities": {
                        "lineups": {
                            "state": "LAST_OBSERVED",
                            "requested": True,
                            "received": 2,
                            "persisted": 9,
                            "received_scope": "LAST_PERSISTED_DEEP_SAMPLE_RESPONSE",
                            "persisted_scope": "STORE_TOTAL",
                            "reason": secret,
                        }
                    },
                },
                "data_freshness": {
                    "state": "PARTIAL",
                    "entity_timestamps_evaluated": True,
                    "reason": "Existe evidencia stale.",
                    "stale_samples": [{
                        "fixture_id": "stale-9001",
                        "home_team": secret,
                        "away_team": "Visitante",
                        "competition": "Liga QA",
                        "provider": "SportsDB",
                        "provider_observed_at": "2026-09-20T09:00:00+00:00",
                        "freshness_seconds": 7200,
                        "stale_reason": "LIVE_OBSERVATION_TOO_OLD",
                        "status_canonical": "LIVE",
                    }],
                },
                "unexpected": secret,
            },
        }
    )

    return_code, payload, _calls, output = run_master(
        monkeypatch,
        capsys,
        [telegram, evolution_ok()],
        secret=secret,
    )
    pipeline = payload["telegram"]["sports_pipeline"]

    assert return_code == 0
    assert pipeline["provider_authenticated"] is True
    assert pipeline["quota"]["daily_remaining"] == 93
    assert pipeline["capabilities"]["lineups"]["persisted"] == 2
    assert pipeline["last_sample"]["fixture_ids"] == ["9001"]
    assert pipeline["last_sample"]["source"] == "LAST_PERSISTED_DEEP_SAMPLE"
    assert pipeline["job_execution"]["scope"] == "CURRENT_SPORTS_SYNC"
    assert pipeline["provider_access"]["state"] == "AUTHENTICATED"
    assert pipeline["quota_observation"]["freshness"] == "LAST_OBSERVED_NOT_CURRENT"
    assert pipeline["coverage"]["capabilities"]["lineups"]["persisted_scope"] == "STORE_TOTAL"
    assert pipeline["coverage"]["capabilities"]["lineups"]["reason"] == "REDACTED"
    assert pipeline["data_freshness"]["state"] == "PARTIAL"
    assert pipeline["data_freshness"]["stale_samples"][0]["fixture_id"] == "stale-9001"
    assert pipeline["data_freshness"]["stale_samples"][0]["home_team"] == "REDACTED"
    assert pipeline["data_freshness"]["stale_samples"][0]["freshness_seconds"] == 7200
    assert "unexpected" not in pipeline
    assert secret not in output


def test_invalid_base_url_is_rejected_before_http(monkeypatch, capsys):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.invalid?secret=must-not-travel")
    monkeypatch.setenv("AUTOMATION_SECRET", "pytest-master-secret")
    monkeypatch.setattr(master.urllib.request, "urlopen", lambda *_args, **_kwargs: pytest.fail("HTTP must not run"))
    return_code = master.main()
    payload = json.loads(capsys.readouterr().out)
    assert return_code == 2
    assert payload["overall"] == "FAIL"
    assert payload["telegram"]["telegram_result"] == "INVALID_PUBLIC_BASE_URL"


def test_master_runner_is_stateless_and_uses_only_approved_configuration():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert source.count("os.environ.get(") == 2
    assert 'os.environ.get("PUBLIC_BASE_URL")' in source
    assert 'os.environ.get("AUTOMATION_SECRET")' in source
    for forbidden in (
        "sqlite3",
        "DB_PATH",
        "TELEGRAM_BOT_TOKEN",
        "STRIPE",
        "subprocess",
        "pathlib",
        "requests.",
        "RENDER_API",
    ):
        assert forbidden not in source


def test_readiness_probe_retries_transient_502_then_recovers(monkeypatch):
    outcomes = [
        urllib.error.HTTPError("https://example.invalid/api/runtime-version", 502, "bad gateway", {}, None),
        urllib.error.HTTPError("https://example.invalid/api/runtime-version", 503, "unavailable", {}, None),
        MockResponse({"ok": True}, 200),
    ]
    calls = []
    sleeps = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        if request.full_url.endswith('/api/automation/postmatch/tick'):
            return MockResponse({'ok': True, 'result': 'SKIPPED_DISABLED', 'processed': 0})
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(master.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(master.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = master.wait_for_web_ready("https://example.invalid")

    assert result["readiness_status"] == "PASS"
    assert result["readiness_http"] == 200
    assert result["readiness_result"] == "WEB_READY"
    assert result["readiness_attempts"] == 3
    assert sleeps == [master.READINESS_BACKOFF_SECONDS, master.READINESS_BACKOFF_SECONDS]
    assert all(url.endswith(master.READINESS_ENDPOINT) for url, _ in calls)
    assert all(timeout == master.READINESS_TIMEOUT_SECONDS for _, timeout in calls)


def test_readiness_failure_does_not_run_side_effecting_ticks(monkeypatch, capsys):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("AUTOMATION_SECRET", "pytest-master-secret")
    monkeypatch.setattr(
        master,
        "wait_for_web_ready",
        lambda _base_url: {
            "readiness_status": "FAIL",
            "readiness_http": 502,
            "readiness_result": "HTTP_502",
            "readiness_attempts": master.READINESS_ATTEMPTS,
            "readiness_duration_ms": 25000,
        },
    )
    monkeypatch.setattr(master, "telegram_tick", lambda *_args: pytest.fail("telegram must not run"))
    monkeypatch.setattr(master, "continuous_evolution_tick", lambda *_args: pytest.fail("evolution must not run"))

    return_code = master.main()
    payload = json.loads(capsys.readouterr().out)

    assert return_code == 2
    assert payload["overall"] == "FAIL"
    assert payload["web_readiness"]["readiness_result"] == "HTTP_502"
    assert payload["telegram_status"] == "NOT_EXECUTED"
    assert payload["continuous_evolution_status"] == "NOT_EXECUTED"


def test_readiness_probe_never_sends_automation_secret(monkeypatch):
    seen = []
    secret = "pytest-readiness-secret-must-not-travel"
    monkeypatch.setenv("AUTOMATION_SECRET", secret)

    def fake_urlopen(request, timeout):
        seen.append(request)
        return MockResponse({"ok": True}, 200)

    monkeypatch.setattr(master.urllib.request, "urlopen", fake_urlopen)
    result = master.wait_for_web_ready("https://example.invalid")

    assert result["readiness_status"] == "PASS"
    assert len(seen) == 1
    assert seen[0].get_method() == "GET"
    assert seen[0].full_url == "https://example.invalid/api/runtime-version?compact=1"
    assert seen[0].data is None
    headers = {name.lower(): value for name, value in seen[0].header_items()}
    assert "x-automation-secret" not in headers
    assert "authorization" not in headers
    assert secret not in seen[0].full_url
    assert secret not in json.dumps(headers)


@pytest.mark.parametrize("reason", ["DAILY_BUDGET", "TICK_BUDGET", "SOURCE_COOLDOWN"])
def test_controlled_postmatch_partial_succeeds(monkeypatch, capsys, reason):
    code, payload, _, _ = run_master(
        monkeypatch, capsys, [telegram_ok(), evolution_ok(), backup_ok()],
        backup_is_due=True,
        postmatch_outcome=MockResponse({"ok": True, "result": "PARTIAL", "jobs": [
            {"state": "COMPLETE", "reason": "COMPLETE"},
            {"state": "RETRY", "reason": reason},
        ]}),
    )
    assert code == 1
    assert payload["overall"] == "PARTIAL"
    assert payload["postmatch"]["postmatch_status"] == "PARTIAL"
    assert payload["postmatch"]["postmatch_result"] == "PARTIAL"


@pytest.mark.parametrize("job", [
    {"state": "RETRY", "reason": "INTERNAL_ERROR"},
    {"state": "RETRY", "reason": "STORAGE_UNAVAILABLE"},
    {"state": "RETRY", "reason": "NETWORK"},
    {"state": "FAILED", "reason": "DAILY_BUDGET"},
    {"state": "RETRY", "reason": "UNKNOWN"},
    None,
])
def test_uncontrolled_postmatch_partial_fails(monkeypatch, capsys, job):
    code, payload, _, _ = run_master(
        monkeypatch, capsys, [telegram_ok(), evolution_ok()],
        postmatch_outcome=MockResponse({"ok": True, "result": "PARTIAL", "jobs": [job]}),
    )
    assert code != 0
    assert payload["postmatch"]["postmatch_status"] == "FAIL"


@pytest.mark.parametrize("failed", [0, 1, 2])
def test_controlled_partial_does_not_hide_other_failures(monkeypatch, capsys, failed):
    outcomes = [telegram_ok(), evolution_ok(), backup_ok()]
    outcomes[failed] = urllib.error.URLError("unavailable")
    code, payload, _, _ = run_master(
        monkeypatch, capsys, outcomes, backup_is_due=True,
        postmatch_outcome=MockResponse({"ok": True, "result": "PARTIAL", "jobs": [
            {"state": "RETRY", "reason": "DAILY_BUDGET"},
        ]}),
    )
    assert code != 0
    assert payload["postmatch"]["postmatch_status"] == "PARTIAL"


@pytest.mark.parametrize("outcome", [
    MockResponse({"ok": False, "result": "PARTIAL", "jobs": [{"state": "RETRY", "reason": "DAILY_BUDGET"}]}),
    MockResponse({"ok": True, "result": "PARTIAL"}),
    MockResponse({"ok": True, "result": "PARTIAL", "jobs": []}),
    MockResponse({"ok": True, "result": "PARTIAL", "jobs": "invalid"}),
    MockResponse({"ok": True, "result": "STORAGE_UNAVAILABLE"}),
    MockResponse({"ok": True, "result": "IDLE"}, status=201),
    urllib.error.URLError("postmatch unavailable"),
    socket.timeout("postmatch timeout"),
])
def test_invalid_or_failed_postmatch_response_still_fails(monkeypatch, capsys, outcome):
    code, payload, _, _ = run_master(
        monkeypatch, capsys, [telegram_ok(), evolution_ok()], postmatch_outcome=outcome,
    )
    assert code != 0
    assert payload["postmatch"]["postmatch_status"] == "FAIL"


def test_postmatch_timeout_uses_extended_budget_and_is_diagnostic(monkeypatch, capsys):
    code, payload, calls, output = run_master(
        monkeypatch,
        capsys,
        [telegram_ok(), evolution_ok()],
        postmatch_outcome=socket.timeout("late but healthy response"),
    )

    assert code != 0
    assert payload["postmatch"]["postmatch_status"] == "FAIL"
    assert payload["postmatch"]["postmatch_result"] == "TIMEOUT"
    assert payload["postmatch"]["postmatch_http"] is None
    postmatch_call = next(
        call for call in calls
        if call["request"].full_url.endswith("/api/automation/postmatch/tick")
    )
    assert postmatch_call["timeout"] == master.POSTMATCH_TIMEOUT_SECONDS
    assert master.POSTMATCH_TIMEOUT_SECONDS == 45
    assert "late but healthy response" not in output


def test_highlights_tick_is_separate_bounded_and_header_authenticated(monkeypatch):
    seen = {}
    secret = "pytest-highlights-secret"

    def fake_urlopen(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return MockResponse({
            "ok": True,
            "highlights_sync": {
                "ok": True,
                "status": "OK",
                "external_calls": 2,
                "persistent_cache_hits": 1,
                "profile_links_reused": 1,
                "v2_event_lookups": 1,
                "v2_cache_hits": 0,
                "v2_highlights_found": 1,
                "highlights_found": 3,
                "linked_matches": 2,
                "errors": [],
            },
        })

    monkeypatch.setattr(master.urllib.request, "urlopen", fake_urlopen)
    result = master.highlights_tick("https://example.invalid", secret)

    assert result["highlights_status"] == "PASS"
    assert result["external_calls"] == 2
    assert result["v2_event_lookups"] == 1
    assert result["v2_highlights_found"] == 1
    assert seen["timeout"] == master.HIGHLIGHTS_TIMEOUT_SECONDS == 24
    request = seen["request"]
    assert request.get_method() == "POST"
    assert request.full_url.startswith("https://example.invalid" + master.HIGHLIGHTS_ENDPOINT + "?")
    assert "days_back=7" in request.full_url
    assert "limit=250" in request.full_url
    assert secret not in request.full_url
    headers = {name.lower(): value for name, value in request.header_items()}
    assert headers["x-automation-secret"] == secret


def test_highlights_failure_is_reported_without_stopping_other_lanes(monkeypatch, capsys):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("AUTOMATION_SECRET", "pytest-master-secret")
    monkeypatch.setattr(master, "wait_for_web_ready", lambda _url: {
        "readiness_status": "PASS",
        "readiness_http": 200,
        "readiness_result": "WEB_READY",
        "readiness_attempts": 1,
        "readiness_duration_ms": 1,
    })
    monkeypatch.setattr(master, "telegram_tick", lambda *_a: {
        "telegram_status": "PASS", "telegram_result": "QUEUE_EMPTY", "telegram_duration_ms": 1,
    })
    monkeypatch.setattr(master, "highlights_tick", lambda *_a: {
        "highlights_status": "FAIL", "highlights_result": "TIMEOUT", "highlights_duration_ms": 24000,
    })
    monkeypatch.setattr(master, "continuous_evolution_tick", lambda *_a: {
        "continuous_status": "PASS", "continuous_result": "RUN", "continuous_duration_ms": 1,
    })
    monkeypatch.setattr(master, "backup_due", lambda _utc: False)
    monkeypatch.setattr(master, "postmatch_tick", lambda *_a: {
        "postmatch_status": "PASS", "postmatch_result": "IDLE", "duration_ms": 1,
    })

    code = master.main()
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["overall"] == "FAIL"
    assert payload["telegram_status"] == "PASS"
    assert payload["highlights_status"] == "FAIL"
    assert payload["highlights"]["highlights_result"] == "TIMEOUT"
    assert payload["continuous_evolution_status"] == "PASS"
