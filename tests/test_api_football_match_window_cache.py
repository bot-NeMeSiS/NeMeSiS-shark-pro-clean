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
        ("match_window", tracker._now_iso(), "PARTIAL", 0, 0, 0, 5, "HTTP 429 rate limit secret-canary", "{}"),
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
    assert result["status"] == "CACHE_PROVIDER_FAILURE_RATE_OR_QUOTA"
    assert result["cached_provider_failure"] is True
    assert result["cached_from_status"] == "PARTIAL"
    assert result["external_calls"] == 0
    assert calls == []



def test_safe_provider_failure_category_never_returns_provider_text():
    assert tracker._safe_provider_failure_category({"ok": False, "errors": {"token": "secret-canary invalid API key"}}) == "AUTH_OR_ACCESS"
    assert tracker._safe_provider_failure_category({"ok": False, "error": "HTTP 429 rate limit"}) == "RATE_OR_QUOTA"
    assert tracker._safe_provider_failure_category({"ok": False, "error": "connection timed out"}) == "NETWORK_OR_TIMEOUT"
    assert tracker._safe_provider_failure_category({"ok": False, "errors": {"plan": "season not available"}}) == "PLAN_OR_COVERAGE"
    assert tracker._safe_provider_failure_category({"ok": False, "errors": {"weird": "opaque-sensitive-provider-text"}}) == "PROVIDER_RESPONSE"


def test_match_window_exposes_only_safe_category_in_status(tmp_path, monkeypatch):
    db_path = str(tmp_path / "match-window-provider-category.db")
    _enable_provider(monkeypatch)

    def fake_get(path, params=None, timeout=18):
        return {"ok": False, "response": [], "errors": {"plan": "season not available secret-canary"}}

    monkeypatch.setattr(tracker, "_api_get", fake_get)
    result = tracker.sync_api_football_match_window(
        db_path,
        days_back=0,
        days_ahead=0,
        force=True,
        deep_limit=0,
    )
    assert result["ok"] is False
    assert result["status"] == "PARTIAL_PLAN_OR_COVERAGE"
    assert "secret-canary" not in result["status"]


def test_safe_plan_coverage_subtype_is_closed_and_secret_safe():
    cases = [
        ({"ok": False, "errors": {"plan": "Free plan does not include this season secret-canary"}}, "FREE_PLAN_SEASON_RESTRICTED"),
        ({"ok": False, "errors": {"season": "Season not available secret-canary"}}, "SEASON_UNAVAILABLE"),
        ({"ok": False, "errors": {"plan": "Free plan access restricted secret-canary"}}, "FREE_PLAN_RESTRICTED"),
        ({"ok": False, "error": "Endpoint not allowed for this account secret-canary"}, "ENDPOINT_RESTRICTED"),
        ({"ok": False, "errors": {"coverage": "Data not available secret-canary"}}, "COVERAGE_UNAVAILABLE"),
        ({"ok": False, "errors": {"subscription": "Upgrade plan secret-canary"}}, "SUBSCRIPTION_RESTRICTED"),
        ({"ok": False, "errors": {"other": "plan-limited opaque secret-canary"}}, "SUBSCRIPTION_RESTRICTED"),
    ]
    for payload, expected in cases:
        assert tracker._safe_provider_failure_category(payload) == "PLAN_OR_COVERAGE"
        assert tracker._safe_provider_state_label(payload) == expected
        assert "secret-canary" not in tracker._safe_provider_state_label(payload)


def test_cached_plan_error_exposes_specific_safe_subtype_without_new_call(tmp_path, monkeypatch):
    db_path = str(tmp_path / "match-window-plan-subtype-cache.db")
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
        (
            "match_window",
            tracker._now_iso(),
            "PARTIAL",
            0,
            0,
            0,
            5,
            "Free plan does not include this season secret-canary",
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
    result = tracker.sync_api_football_match_window(
        db_path,
        days_back=1,
        days_ahead=1,
        force=False,
        deep_limit=0,
    )
    assert result["ok"] is False
    assert result["status"] == "CACHE_PROVIDER_FAILURE_FREE_PLAN_SEASON_RESTRICTED"
    assert "secret-canary" not in result["status"]
    assert result["external_calls"] == 0
    assert calls == []


def test_fresh_plan_error_exposes_specific_safe_subtype_only(tmp_path, monkeypatch):
    db_path = str(tmp_path / "match-window-plan-subtype-fresh.db")
    _enable_provider(monkeypatch)

    def fake_get(path, params=None, timeout=18):
        return {
            "ok": False,
            "response": [],
            "errors": {"plan": "Free plan does not include this season secret-canary"},
        }

    monkeypatch.setattr(tracker, "_api_get", fake_get)
    result = tracker.sync_api_football_match_window(
        db_path,
        days_back=0,
        days_ahead=0,
        force=True,
        deep_limit=0,
    )
    assert result["ok"] is False
    assert result["status"] == "PARTIAL_FREE_PLAN_SEASON_RESTRICTED"
    assert "secret-canary" not in result["status"]
