from __future__ import annotations

import json
from datetime import datetime

import pytest

import engines.product_review_system_engine as ce


ENDPOINT = "/api/automation/continuous-evolution/tick"
SECRET = "pytest-native-workforce-header"


def _configure(monkeypatch, tmp_path):
    storage = tmp_path / "continuous-evolution"
    monkeypatch.setenv("AUTOMATION_SECRET", SECRET)
    monkeypatch.setenv("CONTINUOUS_EVOLUTION_SAFE_MODE", "1")
    monkeypatch.setenv("CONTINUOUS_EVOLUTION_STORAGE_ROOT", str(storage))
    return storage, {"X-Automation-Secret": SECRET, "X-NeMeSiS-Cron-Runner": "render-cron"}


def _freeze(monkeypatch, value):
    real_now = ce._ce_now
    frozen = datetime.fromisoformat(value)
    monkeypatch.setattr(ce, "_ce_now", lambda now=None: frozen if now is None else real_now(now))


def test_native_hourly_review_runs_before_daily_without_mutating_product_memory(client, monkeypatch, tmp_path):
    storage, headers = _configure(monkeypatch, tmp_path)
    # This checks endpoint/cadence integration. Deadline exhaustion is tested
    # separately with a controlled clock, independent of shared CI CPU load.
    monkeypatch.setattr(ce, "NATIVE_WORKFORCE_BUDGET_SECONDS", 10.0)
    storage.mkdir()
    memory_bytes = json.dumps({"recommendations": {"unrelated": {"state": "DEFERRED"}}}).encode()
    (storage / "product_memory.json").write_bytes(memory_bytes)
    _freeze(monkeypatch, "2026-10-29T01:00:00+01:00")

    first = client.post(ENDPOINT, headers=headers)
    assert first.status_code == 200
    payload = first.get_json()
    assert payload["result"] == "PASS"
    assert payload["daily_result"] == "SKIPPED_NOT_DUE"
    native = payload["native_workforce"]
    assert native["result"] == "PASS"
    assert native["receipt_id"]
    assert native["expected_count"] == native["executed_count"] == 22
    assert native["review_kind"] == "STATIC_PARTIAL"
    assert native["business_execution_certified"] is False
    assert native["production_certified"] is False
    assert SECRET not in first.get_data(as_text=True)

    # Caller-controlled task/force values must not bypass the server cadence.
    repeat = client.post(
        ENDPOINT + "?force=1&task_name=monthly_strategy_review",
        headers=headers,
        json={"force": True, "task_name": "monthly_strategy_review"},
    ).get_json()
    assert repeat["result"] == "SKIPPED_NOT_DUE"
    assert repeat["native_workforce"]["result"] == "SKIPPED_NOT_DUE"
    assert repeat["native_workforce"]["executed_count"] == 0

    _freeze(monkeypatch, "2026-10-29T02:00:00+01:00")
    following = client.post(ENDPOINT, headers=headers).get_json()
    assert following["native_workforce"]["result"] == "PASS"
    assert following["native_workforce"]["receipt_id"] != native["receipt_id"]
    assert following["daily_result"] == "SKIPPED_NOT_DUE"
    assert not (storage / "latest_snapshot.json").exists()
    assert (storage / "product_memory.json").read_bytes() == memory_bytes


def test_native_review_respects_existing_administrator_pause(client, monkeypatch, tmp_path):
    storage, headers = _configure(monkeypatch, tmp_path)
    _freeze(monkeypatch, "2026-10-29T05:00:00+01:00")
    ce.set_continuous_evolution_pause(paused=True, storage_root=storage, reason="QA pause")

    response = client.post(ENDPOINT, headers=headers)
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["result"] == "SKIPPED_PAUSED"
    assert payload["native_workforce"]["result"] == "SKIPPED_PAUSED"
    assert payload["native_workforce"]["receipt_id"] is None
    assert payload["native_workforce"]["executed_count"] == 0
    assert not (storage / "native_workforce").exists()


@pytest.mark.parametrize(
    ("native_status", "native_ok", "dangerous", "http_status", "aggregate"),
    [
        ("PARTIAL", False, False, 200, "PARTIAL"),
        ("SKIPPED_STALE_LOCK", False, False, 200, "PARTIAL"),
        ("UNRECOGNIZED_RESULT", True, False, 200, "PARTIAL"),
        ("PASS", True, True, 500, "EXTERNAL_ACTION_ATTEMPT"),
    ],
)
def test_native_failure_is_not_hidden_by_daily_not_due(
    client, app_module, monkeypatch, tmp_path,
    native_status, native_ok, dangerous, http_status, aggregate,
):
    _storage, headers = _configure(monkeypatch, tmp_path)

    def scheduled(_root, _version, *, task_name, **_kwargs):
        if task_name == "platform_workforce_review":
            return {
                "ok": native_ok,
                "task_name": task_name,
                "result": native_status,
                "job": {},
                "receipt": {"evidence": "DO_NOT_EXPOSE_NATIVE_EVIDENCE"},
                "dangerous_actions_executed": dangerous,
            }
        return {"ok": True, "task_name": task_name, "result": "SKIPPED_NOT_DUE", "job": {}}

    monkeypatch.setattr(app_module, "run_continuous_evolution_scheduler_task", scheduled)
    response = client.post(ENDPOINT, headers=headers)
    payload = response.get_json()
    assert response.status_code == http_status
    assert payload["ok"] is False
    assert payload["result"] == aggregate
    assert payload["daily_result"] == "SKIPPED_NOT_DUE"
    assert payload["native_workforce"]["result"] == native_status
    assert "DO_NOT_EXPOSE_NATIVE_EVIDENCE" not in response.get_data(as_text=True)
