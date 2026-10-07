"""Cron SQLite contention and provider failures remain bounded and truthful."""
import sqlite3
import time

import pytest

from database_manager import connect
from engines.cron_request_budget import CronRequestBudget, CronTimeBudget, sqlite_busy_timeout


def test_sqlite_lock_does_not_consume_thirty_second_transport(tmp_path):
    path = str(tmp_path / "locked.sqlite")
    writer = connect(path)
    writer.execute("CREATE TABLE evidence(value TEXT)")
    writer.commit()
    writer.execute("BEGIN IMMEDIATE")
    writer.execute("INSERT INTO evidence VALUES ('preserved')")
    try:
        with CronRequestBudget():
            contender = connect(path)
            try:
                assert contender.execute("PRAGMA busy_timeout").fetchone()[0] == 500
                started = time.monotonic()
                with pytest.raises(sqlite3.OperationalError, match="locked"):
                    contender.execute("INSERT INTO evidence VALUES ('blocked')")
                assert time.monotonic() - started < 2
            finally:
                contender.close()
        writer.commit()
        assert writer.execute("SELECT value FROM evidence").fetchall()[0][0] == "preserved"
    finally:
        writer.close()


def test_sqlite_wait_honors_parent_and_restores_default():
    now = [0.0]
    with CronRequestBudget(seconds=1, clock=lambda: now[0]):
        now[0] = .7
        assert 299 <= sqlite_busy_timeout(30000) <= 300
        now[0] = 1
        with pytest.raises(CronTimeBudget):
            sqlite_busy_timeout(30000)
    assert sqlite_busy_timeout(30000) == 30000


@pytest.mark.parametrize("error,reason", [
    ("HTTP 403 forbidden", "AUTH_OR_ACCESS"),
    ("connection timeout", "NETWORK_OR_TIMEOUT"),
    ("sqlite OperationalError database locked", "LOCAL_DB_OR_SCHEMA"),
])
def test_live_failure_keeps_technical_truth(app_module, monkeypatch, error, reason):
    monkeypatch.setattr(app_module, "run_sports_sync_cycle", lambda **kwargs: {
        "ok": True, "status": "PARTIAL", "live": {
            "ok": False, "status": "partial_AUTH_OR_ACCESS_ERROR_KEY_ACCESS",
            "configured": True, "enabled": True, "external_calls": 0, "error": error,
        },
    })
    monkeypatch.setattr(app_module, "api_exploitation_summary", lambda *args: {})
    monkeypatch.setattr(app_module, "_build_sports_pipeline_diagnostics", lambda *args: {})
    result = app_module.bounded_sports_sync()
    assert result["technical_errors"] == ["live_" + reason]
    assert result["ok"] is False
    assert not result["controlled_deferrals"]


def test_monitor_retains_safe_live_reason_and_fail(monkeypatch):
    import json
    from tools import render_cron_master_tick as master

    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, *args):
            return json.dumps({"ok": False, "status": "PARTIAL", "technical_errors": [
                "live_AUTH_OR_ACCESS", "live_https://secret.invalid/token"
            ]}).encode()

    monkeypatch.setattr(master.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    result = master.sports_tick("https://example.invalid", "test")
    assert result["sports_status"] == "FAIL"
    assert result["sports_technical_errors"] == [
        {"stage": "live", "reason": "AUTH_OR_ACCESS"},
        {"stage": "live", "reason": "UNCLASSIFIED"},
    ]
    assert "secret.invalid" not in json.dumps(result)


def test_expired_provider_skips_post_fetch_scans(app_module, monkeypatch):
    now = [0.0]
    calls = []
    monkeypatch.setattr(app_module, "sports_sync_window_state", lambda: calls.append("window") or {"live_refresh_required": True})
    def fixtures(*args, **kwargs):
        now[0] = 16
        return {"ok": True, "status": "OK", "external_calls": 1}
    monkeypatch.setattr(app_module, "sync_api_football_match_window", fixtures)
    monkeypatch.setattr(app_module, "_api_football_deep_enrichment_candidates", lambda **kwargs: pytest.fail("expired scan"))
    monkeypatch.setattr(app_module, "automation_safe_set", lambda *args: {})
    monkeypatch.setattr(app_module, "invalidate_v934_realtime_cache", lambda *args: None)
    with CronRequestBudget(clock=lambda: now[0]):
        result = app_module.run_sports_sync_cycle(include_odds=False)
    assert calls == ["window"]
    assert result["live"]["status"] == "TIME_BUDGET"
    assert result["deep_enrichment"]["status"] == "TIME_BUDGET"


@pytest.mark.parametrize("category,error,partial", [
    ("FREE_PLAN_RESTRICTED", "Free plan does not provide live coverage", True),
    ("SUBSCRIPTION_RESTRICTED", "Endpoint unavailable for this subscription", True),
    ("AUTH_OR_ACCESS", "HTTP 403 forbidden", False),
    ("ACCESS_RESTRICTED", "Access rejected", False),
    ("SUBSCRIPTION_RESTRICTED", "HTTP 403 forbidden", False),
])
def test_fresh_plan_limit_is_partial_but_access_rejection_is_fail(app_module, monkeypatch, category, error, partial):
    monkeypatch.setattr(app_module, "run_sports_sync_cycle", lambda **kwargs: {
        "ok": True, "status": "PARTIAL", "live": {
            "ok": True, "status": "partial_" + category,
            "failure_category": category, "errors": [error], "external_calls": 1,
        },
    })
    monkeypatch.setattr(app_module, "api_exploitation_summary", lambda *args: {})
    monkeypatch.setattr(app_module, "_build_sports_pipeline_diagnostics", lambda *args: {})
    result = app_module.bounded_sports_sync()
    assert result["ok"] is partial
    assert bool(result["technical_errors"]) is not partial
    assert result["controlled_deferrals"] == (["PROVIDER_PLAN_LIMIT"] if partial else [])
