"""Regression coverage for API-Football live provider failure backoff."""

import sqlite3
from datetime import datetime, timedelta, timezone

from engines import api_football_live_tracker_engine as tracker


def _enable_provider(monkeypatch):
    monkeypatch.setenv("API_FOOTBALL_KEY", "test-key")
    monkeypatch.setenv("ENABLE_API_FOOTBALL_PROVIDER", "true")
    monkeypatch.setenv("ENABLE_API_FOOTBALL_LIVE_TRACKER", "true")
    monkeypatch.setenv("API_FOOTBALL_LIVE_PLAN_BACKOFF_SECONDS", "21600")


def _insert_live_failure(db_path, *, error, last_sync_at=None):
    tracker.ensure_live_tracker_schema(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT OR REPLACE INTO api_football_live_sync_state(
            key,last_sync_at,status,fixtures_count,events_count,stats_count,
            external_calls,error,payload_json
        ) VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            "live",
            last_sync_at or tracker._now_iso(),
            "partial",
            0,
            0,
            0,
            1,
            error,
            "{}",
        ),
    )
    conn.commit()
    conn.close()


def test_live_plan_failure_backoff_uses_zero_provider_calls(tmp_path, monkeypatch):
    db_path = str(tmp_path / "live-plan-backoff.db")
    _enable_provider(monkeypatch)
    _insert_live_failure(
        db_path,
        error="Free plan access restricted secret-canary",
    )
    calls = []

    def fake_get(path, params=None, timeout=18):
        calls.append((path, dict(params or {})))
        return {"ok": True, "response": []}

    monkeypatch.setattr(tracker, "_api_get", fake_get)
    result = tracker.sync_api_football_live_tracker(db_path, force=False, deep_limit=0)

    assert result["ok"] is True
    assert result["status"] == "PROVIDER_FAILURE_BACKOFF_FREE_PLAN_RESTRICTED"
    assert result["failure_category"] == "FREE_PLAN_RESTRICTED"
    assert result["provider_failure_backoff"] is True
    assert result["skipped"] is True
    assert result["external_calls"] == 0
    assert result["retry_after_seconds"] > 0
    assert calls == []
    assert "secret-canary" not in str(result)


def test_force_refresh_bypasses_live_plan_backoff(tmp_path, monkeypatch):
    db_path = str(tmp_path / "live-plan-force.db")
    _enable_provider(monkeypatch)
    _insert_live_failure(
        db_path,
        error="Free plan access restricted secret-canary",
    )
    calls = []

    def fake_get(path, params=None, timeout=18):
        calls.append((path, dict(params or {})))
        return {"ok": True, "response": []}

    monkeypatch.setattr(tracker, "_api_get", fake_get)
    result = tracker.sync_api_football_live_tracker(db_path, force=True, deep_limit=0)

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["external_calls"] == 1
    assert [path for path, _params in calls] == ["fixtures"]


def test_live_plan_backoff_expires_and_retries_provider(tmp_path, monkeypatch):
    db_path = str(tmp_path / "live-plan-expired.db")
    _enable_provider(monkeypatch)
    old = (
        datetime.now(timezone.utc) - timedelta(hours=7)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    _insert_live_failure(
        db_path,
        error="Free plan access restricted secret-canary",
        last_sync_at=old,
    )
    calls = []

    def fake_get(path, params=None, timeout=18):
        calls.append((path, dict(params or {})))
        return {"ok": True, "response": []}

    monkeypatch.setattr(tracker, "_api_get", fake_get)
    result = tracker.sync_api_football_live_tracker(db_path, force=False, deep_limit=0)

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["external_calls"] == 1
    assert [path for path, _params in calls] == ["fixtures"]


def test_network_failure_does_not_use_plan_backoff(tmp_path, monkeypatch):
    db_path = str(tmp_path / "live-network.db")
    _enable_provider(monkeypatch)
    recent_but_past_normal_cache = (
        datetime.now(timezone.utc) - timedelta(minutes=2)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    _insert_live_failure(
        db_path,
        error="connection timed out",
        last_sync_at=recent_but_past_normal_cache,
    )
    calls = []

    def fake_get(path, params=None, timeout=18):
        calls.append((path, dict(params or {})))
        return {"ok": True, "response": []}

    monkeypatch.setattr(tracker, "_api_get", fake_get)
    result = tracker.sync_api_football_live_tracker(db_path, force=False, deep_limit=0)

    assert result["status"] == "ok"
    assert result["external_calls"] == 1
    assert len(calls) == 1
