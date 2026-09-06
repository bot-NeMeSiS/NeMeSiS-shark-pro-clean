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


def run_master(monkeypatch, capsys, outcomes, secret: str = "pytest-master-secret"):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append({"request": request, "timeout": timeout})
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("AUTOMATION_SECRET", secret)
    monkeypatch.setattr(master.urllib.request, "urlopen", fake_urlopen)
    return_code = master.main()
    output = capsys.readouterr().out.strip()
    return return_code, json.loads(output), calls, output


def telegram_ok(status: str = "QUEUE_EMPTY") -> MockResponse:
    return MockResponse({"ok": True, "status": status, "sent": 0})


def evolution_ok(result: str = "PASS") -> MockResponse:
    return MockResponse({"ok": True, "result": result, "safe_mode": "PASS", "storage": "PASS"})


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
    assert len(calls) == 2
    assert len(_output.splitlines()) == 1


def test_master_partial_when_telegram_fails_and_evolution_still_runs(monkeypatch, capsys):
    return_code, payload, calls, _output = run_master(
        monkeypatch,
        capsys,
        [urllib.error.URLError("telegram unavailable"), evolution_ok()],
    )
    assert return_code == 1
    assert payload["overall"] == "PARTIAL"
    assert payload["telegram"]["telegram_status"] == "FAIL"
    assert payload["continuous_evolution"]["continuous_result"] == "RUN"
    assert len(calls) == 2


def test_master_partial_when_evolution_fails_and_telegram_is_preserved(monkeypatch, capsys):
    return_code, payload, calls, _output = run_master(
        monkeypatch,
        capsys,
        [telegram_ok("NO_DUE_JOBS"), urllib.error.URLError("evolution unavailable")],
    )
    assert return_code == 1
    assert payload["overall"] == "PARTIAL"
    assert payload["telegram"]["telegram_result"] == "NO_DUE_JOBS"
    assert payload["continuous_evolution"]["continuous_status"] == "FAIL"
    assert len(calls) == 2


def test_master_fails_when_both_calls_fail(monkeypatch, capsys):
    return_code, payload, calls, _output = run_master(
        monkeypatch,
        capsys,
        [urllib.error.URLError("telegram unavailable"), urllib.error.URLError("evolution unavailable")],
    )
    assert return_code == 2
    assert payload["overall"] == "FAIL"
    assert len(calls) == 2


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
    assert return_code == 1
    assert payload["telegram"]["telegram_result"] == "TIMEOUT"
    assert payload["continuous_evolution"]["continuous_result"] == "RUN"
    assert len(calls) == 2


def test_evolution_timeout_preserves_telegram(monkeypatch, capsys):
    return_code, payload, calls, _output = run_master(
        monkeypatch,
        capsys,
        [telegram_ok("QUEUE_EMPTY"), socket.timeout("evolution timeout")],
    )
    assert return_code == 1
    assert payload["telegram"]["telegram_result"] == "QUEUE_EMPTY"
    assert payload["continuous_evolution"]["continuous_result"] == "TIMEOUT"
    assert len(calls) == 2


def test_unexpected_telegram_exception_still_allows_evolution(monkeypatch, capsys):
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
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("AUTOMATION_SECRET", "pytest-master-secret")
    return_code = master.main()
    payload = json.loads(capsys.readouterr().out)
    assert return_code == 1
    assert payload["overall"] == "PARTIAL"
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
    assert return_code == 1
    assert payload["overall"] == "PARTIAL"
    assert secret not in output
    assert secret not in json.dumps(payload)
    assert len(calls) == 2
    assert all(call["request"].headers["X-automation-secret"] == secret for call in calls)
    assert all(secret not in call["request"].full_url for call in calls)
    assert calls[0]["request"].get_method() == "GET"
    assert calls[0]["request"].full_url.endswith("/api/automation/telegram/tick?runner=render_cron")
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
                    "state": "NOT_ESTABLISHED",
                    "entity_timestamps_evaluated": False,
                    "reason": "Los contadores no prueban frescura.",
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
    assert pipeline["data_freshness"]["state"] == "NOT_ESTABLISHED"
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
