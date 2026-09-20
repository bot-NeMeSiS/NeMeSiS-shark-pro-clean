"""Regression coverage for API-Football match-window cache and pre-call path."""

import sqlite3

from engines import api_football_live_tracker_engine as tracker


def _enable_provider(monkeypatch):
    monkeypatch.setenv("API_FOOTBALL_KEY", "test-key")
    monkeypatch.setenv("ENABLE_API_FOOTBALL_PROVIDER", "true")
    monkeypatch.setenv("ENABLE_API_FOOTBALL_LIVE_TRACKER", "true")


def test_match_window_reuses_recent_cache_without_provider_call(tmp_path, monkeypatch):
    db_path = str(tmp_path / "match-window-cache.db")
    _enable_provider(monkeypatch)
    tracker.ensure_live_tracker_schema(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT OR REPLACE INTO api_football_live_sync_state(
            key,last_sync_at,status,fixtures_count,events_count,stats_count,
            external_calls,error,payload_json
        ) VALUES (?,?,?,?,?,?,?,?,?)
        """,
        ("match_window", tracker._now_iso(), "OK", 0, 0, 0, 0, "", "{}"),
    )
    conn.commit()
    conn.close()

    calls = []

    def fake_get(path, params=None, timeout=18):
        calls.append((path, dict(params or {})))
        return {"ok": True, "response": []}

    monkeypatch.setattr(tracker, "_api_get", fake_get)

    result = tracker.sync_api_football_match_window(
        db_path,
        days_back=1,
        days_ahead=1,
        force=False,
        deep_limit=0,
    )

    assert result["ok"] is True
    assert result["status"] == "cache"
    assert result["external_calls"] == 0
    assert calls == []


def test_match_window_force_refresh_reaches_provider_after_local_setup(tmp_path, monkeypatch):
    db_path = str(tmp_path / "match-window-force.db")
    _enable_provider(monkeypatch)

    calls = []

    def fake_get(path, params=None, timeout=18):
        calls.append((path, dict(params or {})))
        return {"ok": True, "response": []}

    monkeypatch.setattr(tracker, "_api_get", fake_get)

    result = tracker.sync_api_football_match_window(
        db_path,
        days_back=1,
        days_ahead=1,
        force=True,
        deep_limit=0,
    )

    assert result["ok"] is True
    assert result["status"] == "OK"
    assert result["external_calls"] == 3
    assert [path for path, _params in calls] == ["fixtures", "fixtures", "fixtures"]

def test_match_window_cached_provider_failure_stays_failure_without_new_call(tmp_path, monkeypatch):
    db_path = str(tmp_path / "match-window-failure-cache.db")
    _enable_provider(monkeypatch)
    tracker.ensure_live_tracker_schema(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT OR REPLACE INTO api_football_live_sync_state(
            key,last_sync_at,status,fixtures_count,events_count,stats_count,
            external_calls,error,payload_json
        ) VALUES (?,?,?,?,?,?,?,?,?)
        """,
        ("match_window", tracker._now_iso(), "PARTIAL", 0, 0, 0, 5, "provider failure", "{}"),
    )
    conn.commit()
    conn.close()

    calls = []

    def fake_get(path, params=None, timeout=18):
        calls.append((path, dict(params or {})))
        return {"ok": True, "response": []}

    monkeypatch.setattr(tracker, "_api_get", fake_get)

    result = tracker.sync_api_football_match_window(
        db_path,
        days_back=1,
        days_ahead=1,
        force=False,
        deep_limit=0,
    )

    assert result["ok"] is False
    assert result["status"] == "CACHE_PROVIDER_FAILURE"
    assert result["cached_provider_failure"] is True
    assert result["cached_from_status"] == "PARTIAL"
    assert result["external_calls"] == 0
    assert calls == []

def test_live_provider_failure_uses_backoff_without_new_call(tmp_path, monkeypatch):
    db_path = str(tmp_path / "live-provider-backoff.db")
    _enable_provider(monkeypatch)
    tracker.ensure_live_tracker_schema(db_path)
    monkeypatch.setenv("API_FOOTBALL_FAILURE_BACKOFF_SECONDS", "1800")

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
            tracker._now_iso(),
            "partial",
            0,
            0,
            0,
            1,
            "Free plan does not have access to this season",
            "{}",
        ),
    )
    conn.commit()
    conn.close()

    calls = []

    def fake_get(path, params=None, timeout=18):
        calls.append((path, dict(params or {})))
        return {"ok": True, "response": []}

    monkeypatch.setattr(tracker, "_api_get", fake_get)

    result = tracker.sync_api_football_live_tracker(db_path, force=False, deep_limit=0)

    assert result["ok"] is False
    assert result["status"] == "CACHE_PROVIDER_FAILURE"
    assert result["cached_provider_failure"] is True
    assert result["provider_reason_code"] == "PLAN_OR_SEASON_ACCESS"
    assert result["external_calls"] == 0
    assert calls == []


def test_live_partial_with_real_fixtures_is_not_failure_backed_off(tmp_path, monkeypatch):
    db_path = str(tmp_path / "live-partial-with-data.db")
    _enable_provider(monkeypatch)
    tracker.ensure_live_tracker_schema(db_path)
    monkeypatch.setenv("API_FOOTBALL_FAILURE_BACKOFF_SECONDS", "1800")
    monkeypatch.setenv("API_FOOTBALL_LIVE_CACHE_SECONDS", "0")

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT OR REPLACE INTO api_football_live_sync_state(
            key,last_sync_at,status,fixtures_count,events_count,stats_count,
            external_calls,error,payload_json
        ) VALUES (?,?,?,?,?,?,?,?,?)
        """,
        ("live", tracker._now_iso(), "partial", 1, 0, 0, 1, "secondary stats failure", "{}"),
    )
    conn.commit()
    conn.close()

    calls = []

    def fake_get(path, params=None, timeout=18):
        calls.append((path, dict(params or {})))
        return {"ok": True, "response": [], "provider_reason_code": ""}

    monkeypatch.setattr(tracker, "_api_get", fake_get)

    result = tracker.sync_api_football_live_tracker(db_path, force=False, deep_limit=0)

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["external_calls"] == 1
    assert [path for path, _params in calls] == ["fixtures"]


def test_provider_reason_categories_are_safe_and_non_raw():
    assert tracker._safe_provider_reason_code("Free plan does not have access to season 2026") == "PLAN_OR_SEASON_ACCESS"
    assert tracker._safe_provider_reason_code("429 request limit reached") == "RATE_OR_QUOTA"
    assert tracker._safe_provider_reason_code("403 access denied") == "AUTH_OR_ACCESS"
    assert tracker._safe_provider_reason_code("required parameter is missing") == "INVALID_REQUEST"
    assert tracker._safe_provider_reason_code("connection timed out") == "NETWORK_OR_TIMEOUT"
    assert tracker._safe_provider_reason_code("opaque provider failure") == "PROVIDER_ERROR"

