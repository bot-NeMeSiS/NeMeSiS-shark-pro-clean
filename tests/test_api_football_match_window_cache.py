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
