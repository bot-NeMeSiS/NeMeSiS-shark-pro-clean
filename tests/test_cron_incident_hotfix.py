"""Regression coverage for the October 4 incident; every transport is mocked."""
import io
import json
import urllib.error

import pytest

from tools import render_cron_master_tick as master


class Response:
    status = 200

    def __init__(self, payload):
        self.body = json.dumps(payload).encode()

    def read(self, *args):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_text_transport_returns_confirmed_dict(app_module, monkeypatch):
    calls = []
    def transport(*args, **kwargs):
        calls.append(1)
        return Response({"ok": True, "result": {"message_id": 17}})
    monkeypatch.setattr(app_module.urllib.request, "urlopen", transport)
    result = app_module.telegram_send_text_with_fallback("https://example.invalid/send", {"text": "test"})
    assert result["sent"] is True
    assert result["status"] == "SENT"
    assert len(calls) == 1


@pytest.mark.parametrize("payload", [None, [], {"ok": True, "result": None}, {"ok": True, "result": []}])
def test_invalid_transport_is_uncertain_without_resend(app_module, monkeypatch, payload):
    calls = []
    monkeypatch.setattr(app_module.urllib.request, "urlopen", lambda *a, **k: calls.append(1) or Response(payload))
    result = app_module.telegram_send_text_with_fallback("https://example.invalid/send", {"text": "test"})
    assert result["delivery_uncertain"] is True
    assert len(calls) == 1


def test_none_callback_fails_closed(app_module):
    result = app_module._safe_sports_sync_call("test", lambda: None)
    assert result["ok"] is False
    assert result["status"] == "INVALID_RESPONSE"


def test_none_scheduler_module_does_not_stop_queue(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "get_telegram_settings", lambda: {"enabled": True, "auto_live_alerts": True})
    monkeypatch.setattr(app_module, "telegram_env_auto_enabled", lambda: False)
    monkeypatch.setattr(app_module, "env_bool", lambda *a: False)
    monkeypatch.setattr(app_module, "enqueue_live_alerts", lambda **k: None)
    calls = []
    monkeypatch.setattr(app_module, "process_premium_telegram_queue", lambda **k: calls.append(1) or {"ok": True, "sent": 0})
    result = app_module.telegram_scheduler_delivery()
    assert result["ok"] is False
    assert result["modules"]["live_alerts"]["status"] == "INVALID_RESPONSE"
    assert calls == [1]


def test_diagnostics_failure_does_not_erase_delivery(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "run_sports_sync_cycle", lambda **k: None)
    monkeypatch.setattr(app_module, "telegram_scheduler_tick", lambda **k: {"ok": True, "status": "QUEUE_EMPTY"})
    monkeypatch.setattr(app_module, "api_exploitation_summary", lambda *a: {})
    monkeypatch.setattr(app_module, "_sports_entity_freshness_snapshot", lambda: (_ for _ in ()).throw(ValueError()))
    monkeypatch.setattr(app_module, "founder_alert_tick", lambda *a: {})
    result = app_module.telegram_cron_with_sports_sync()
    assert result["ok"] is True
    assert "sports_pipeline" not in result


def test_execution_error_cannot_be_labeled_queue_empty(app_module):
    result = app_module._cron_compact_payload("telegram_tick", {"ok": False, "error": "cron_execution_error"}, "2026-10-04T09:35:00+02:00", "2026-10-04T09:35:01+02:00")
    assert result["status"] == "CONTROLLED_ERROR"
    assert result["ok"] is False


@pytest.mark.parametrize("payload,expected", [
    ({"ok": True, "status": "QUEUE_EMPTY"}, "PASS"),
    ({"ok": False, "status": "QUEUE_EMPTY", "error": "execution_error"}, "FAIL"),
    ({"ok": True, "status": "QUEUE_EMPTY", "failed": 1}, "FAIL"),
    (None, "FAIL"),
])
def test_queue_empty_classification(monkeypatch, payload, expected):
    monkeypatch.setattr(master.urllib.request, "urlopen", lambda *a, **k: Response(payload))
    assert master.telegram_tick("https://example.invalid", "test")["telegram_status"] == expected


def test_gateway_recovery_retries_only_readiness(monkeypatch):
    methods = []
    def transport(request, **kwargs):
        methods.append(request.method)
        if request.method == "POST" or len(methods) == 2:
            raise urllib.error.HTTPError(request.full_url, 502, "gateway", {}, io.BytesIO())
        return Response({"ok": True})
    monkeypatch.setattr(master.urllib.request, "urlopen", transport)
    monkeypatch.setattr(master.time, "sleep", lambda *a: None)
    result = master.isolated_tick(master.telegram_tick, "telegram", "https://example.invalid", "test")
    assert result["telegram_status"] == "FAIL"
    assert result["web_recovery"]["readiness_status"] == "PASS"
    assert methods == ["POST", "GET", "GET"]
    assert master.isolated_tick(lambda *a: None, "highlights", "", "")["highlights_status"] == "FAIL"


@pytest.mark.parametrize("delivery,evolution,backup,expected", [
    ("PASS", "PASS", "PASS", "PASS"),
    ("FAIL", "PASS", "PASS", "PARTIAL"),
    ("FAIL", "FAIL", "PASS", "FAIL"),
    ("PASS", "PASS", "FAIL", "PARTIAL"),
])
def test_overall_classification(delivery, evolution, backup, expected):
    assert master.overall_status({"telegram_status": delivery}, {"continuous_status": evolution}, {"backup_status": backup}) == expected
