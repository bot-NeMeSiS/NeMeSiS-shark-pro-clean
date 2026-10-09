"""Synthetic provider receipts: suspension is evidence, never a billing diagnosis."""
import json
import sqlite3

import pytest

from engines import api_football_live_tracker_engine as tracker
from engines.provider_access_evidence import provider_stage_evidence


SUSPENDED = {"ok": False, "response": [], "errors": {"access": "Your account is suspended, check on https://dashboard.api-football.com. PRIVATE_CANARY"}}
PLAN = {"ok": False, "response": [], "errors": {"plan": "Free plans do not have access to this date. PRIVATE_CANARY"}}


def enable(monkeypatch):
    monkeypatch.setenv("API_FOOTBALL_KEY", "synthetic-test-key")
    monkeypatch.setenv("ENABLE_API_FOOTBALL_PROVIDER", "true")
    monkeypatch.setenv("ENABLE_API_FOOTBALL_LIVE_TRACKER", "true")


@pytest.mark.parametrize("text,expected", [
    ("Your account is suspended", "ACCOUNT_SUSPENDED"),
    ("Your account has been suspended", "ACCOUNT_SUSPENDED"),
    ("Account is suspended; daily quota reached", "ACCOUNT_SUSPENDED"),
    ("Account payment status unknown", "PROVIDER_RESPONSE"),
    ("This fixture is suspended", "PROVIDER_RESPONSE"),
    ("Daily quota reached", "RATE_OR_QUOTA"),
    ("Free plans do not have access to this date", "FREE_PLAN_RESTRICTED"),
])
def test_suspension_never_infers_billing_or_confuses_fixture_status(text, expected):
    assert tracker._safe_provider_state_label({"ok": False, "errors": {"access": text}}) == expected


def test_simultaneous_account_and_plan_errors_are_both_kept():
    assert tracker._provider_failure_labels({"ok": False, "errors": {
        **SUSPENDED["errors"], **PLAN["errors"],
    }}) == ["ACCOUNT_SUSPENDED", "FREE_PLAN_RESTRICTED"]


def test_last_response_suspension_survives_truncated_legacy_summary_and_cache(tmp_path, monkeypatch):
    enable(monkeypatch)
    path = str(tmp_path / "provider.db")
    calls = []
    def get(*args, **kwargs):
        calls.append(args)
        return SUSPENDED if len(calls) == 5 else PLAN
    monkeypatch.setattr(tracker, "_api_get", get)
    fresh = tracker.sync_api_football_match_window(path, deep_limit=0)
    assert len(calls) == fresh["external_calls"] == 5
    assert fresh["status"] == "PARTIAL_ACCOUNT_SUSPENDED"
    assert fresh["failure_categories"] == ["ACCOUNT_SUSPENDED", "FREE_PLAN_RESTRICTED"]
    assert fresh["provider_observation_current"] is True
    with sqlite3.connect(path) as conn:
        error = conn.execute("SELECT error FROM api_football_live_sync_state WHERE key='match_window'").fetchone()[0]
        assert "suspended" not in error
    monkeypatch.setattr(tracker, "_api_get", lambda *a, **kw: pytest.fail("cached result must not call provider"))
    cached = tracker.sync_api_football_match_window(path, deep_limit=0)
    assert cached["status"] == "CACHE_PROVIDER_FAILURE_ACCOUNT_SUSPENDED"
    assert cached["failure_categories"] == fresh["failure_categories"]
    assert cached["external_calls"] == 0
    assert cached["provider_observation_current"] is False
    assert cached["provider_observed_at"] == fresh["provider_observed_at"]
    assert "PRIVATE_CANARY" not in json.dumps(cached)


def test_live_suspension_preserves_backoff_and_recovers_only_after_real_observation(tmp_path, monkeypatch):
    enable(monkeypatch)
    path = str(tmp_path / "live.db")
    monkeypatch.setattr(tracker, "_api_get", lambda *a, **kw: SUSPENDED)
    fresh = tracker.sync_api_football_live_tracker(path, deep_limit=0)
    assert fresh["status"] == "partial_ACCOUNT_SUSPENDED_ERROR_KEY_ACCESS"
    assert fresh["provider_observation_current"] is True
    monkeypatch.setattr(tracker, "_api_get", lambda *a, **kw: pytest.fail("backoff must not call provider"))
    cached = tracker.sync_api_football_live_tracker(path, deep_limit=0)
    assert cached["status"] == "PROVIDER_FAILURE_BACKOFF_ACCOUNT_SUSPENDED"
    assert cached["external_calls"] == 0
    assert not cached["provider_observation_current"]
    assert cached["backoff_seconds"] == 21600
    assert "PRIVATE_CANARY" not in json.dumps(cached)
    # Advance only the synthetic record's age, never the production clock.
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE api_football_live_sync_state SET last_sync_at='2000-01-01T00:00:00Z'")
    monkeypatch.setattr(tracker, "_api_get", lambda *a, **kw: {"ok": True, "response": []})
    recovered = tracker.sync_api_football_live_tracker(path, deep_limit=0)
    assert recovered["status"] == "ok"
    assert recovered["external_calls"] == 1
    assert recovered["failure_categories"] == []
    assert recovered["provider_observation_current"] is True


@pytest.mark.parametrize("state,calls,current,scope", [
    ("PARTIAL_ACCOUNT_SUSPENDED", 1, True, "CURRENT_CYCLE"),
    ("CACHE_PROVIDER_FAILURE_ACCOUNT_SUSPENDED", 0, True, "REUSED"),
    ("PROVIDER_FAILURE_BACKOFF_ACCOUNT_SUSPENDED", 1, True, "REUSED"),
    ("OK", 0, True, "NOT_ESTABLISHED"),
    ("OK", 1, False, "NOT_ESTABLISHED"),
])
def test_current_observation_requires_new_calls_and_an_explicit_receipt(state, calls, current, scope):
    evidence = provider_stage_evidence({"state": state, "external_calls": calls,
        "provider_observation_current": current, "provider_observed_at": "PRIVATE_CANARY",
        "failure_categories": ["PRIVATE_CANARY", "ACCOUNT_SUSPENDED"]})
    assert evidence["observation_scope"] == scope
    assert evidence["provider_observed_at"] == ""
    assert "PRIVATE_CANARY" not in json.dumps(evidence)


def admin_evidence(monkeypatch, app_module):
    current = {
        "api_football_primary": {"state": "CACHE_PROVIDER_FAILURE_FREE_PLAN_RESTRICTED", "external_calls": 0, "ok": False},
        "live_refresh": {"state": "PROVIDER_FAILURE_BACKOFF_ACCOUNT_SUSPENDED", "external_calls": 0,
                         "ok": True, "provider_observed_at": "2026-10-09T10:00:00Z"},
    }
    detail = {"compact": {"sports_pipeline": {"current_sync": current}}}
    monkeypatch.setattr(app_module, "automation_get_bounded", lambda key, *a, **kw: detail if key == "telegram_tick_last_detail" else {})
    monkeypatch.setattr(app_module, "env_present", lambda key: key == "API_FOOTBALL_KEY")
    for name in ("probe_api_football_account", "sportsdb_v1", "odds_api_request", "automation_set"):
        monkeypatch.setattr(app_module, name, lambda *a, **kw: pytest.fail("admin GET must not probe or write"))
    return app_module.v945_provider_health_snapshot()


def test_admin_includes_live_rejection_without_implying_subscription_or_recovery(app_module, monkeypatch):
    result = admin_evidence(monkeypatch, app_module)
    primary = result["providers"][0]
    assert primary["status"] == "REVISAR_ACCOUNT_SUSPENDED"
    assert primary["status_label"] == "Suspensión comunicada"
    assert primary["failure_categories"] == ["ACCOUNT_SUSPENDED", "FREE_PLAN_RESTRICTED"]
    assert primary["billing_status"] == "No verificable automáticamente"
    assert "Motivo sin confirmar" in primary["next_action"]
    assert all(item["observation_scope"] == "REUSED" for item in primary["observations"])
    assert [item["lane_label"] for item in primary["observations"]] == ["Calendario y resultados", "Directo"]
    assert result["has_alerts"] and result["provider_calls_during_render"] == 0


@pytest.mark.parametrize("cached", [False, True])
def test_fresh_suspension_is_fail_but_unchanged_backoff_is_partial(app_module, monkeypatch, cached):
    stage = {"ok": True, "external_calls": 0 if cached else 1,
        "status": ("PROVIDER_FAILURE_BACKOFF_" if cached else "partial_") + "ACCOUNT_SUSPENDED",
        "failure_category": "ACCOUNT_SUSPENDED", "errors": ["provider_failure_backoff" if cached else "Your account is suspended"]}
    monkeypatch.setattr(app_module, "run_sports_sync_cycle", lambda **kw: {"ok": True, "live": stage})
    monkeypatch.setattr(app_module, "api_exploitation_summary", lambda *a: {})
    monkeypatch.setattr(app_module, "_build_sports_pipeline_diagnostics", lambda *a: {})
    result = app_module.bounded_sports_sync()
    assert result["ok"] is cached
    assert result["technical_errors"] == ([] if cached else ["live_AUTH_OR_ACCESS"])


def test_provider_health_api_remains_admin_only(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "is_admin_session", lambda: False)
    monkeypatch.setattr(app_module, "v945_provider_health_snapshot", lambda: pytest.fail("unauthorized evidence read"))
    with app_module.app.test_request_context('/api/admin/provider-health'):
        assert app_module.api_admin_provider_health()[1] == 403


def test_receipt_survives_pipeline_compaction_without_raw_error(app_module):
    from tools.render_cron_master_tick import sanitized_sports_pipeline
    stage = {"ok": False, "status": "PARTIAL_ACCOUNT_SUSPENDED", "external_calls": 5,
        "failure_categories": ["ACCOUNT_SUSPENDED", "FREE_PLAN_RESTRICTED", "PRIVATE_CANARY"],
        "provider_observation_current": True, "provider_observed_at": "2026-10-09T10:00:00Z",
        "errors": ["PRIVATE_CANARY"]}
    pipeline = app_module._build_sports_pipeline_diagnostics({"fixtures": stage, "live": stage}, {})
    compact = app_module._cron_compact_payload("sports_sync", {"sports_pipeline": pipeline}, "", "")
    for lane in ("api_football_primary", "live_refresh"):
        evidence = compact["sports_pipeline"]["current_sync"][lane]
        assert evidence["failure_categories"] == ["ACCOUNT_SUSPENDED", "FREE_PLAN_RESTRICTED"]
        assert evidence["provider_observation_current"] is True
        assert evidence["provider_observed_at"] == "2026-10-09T10:00:00+00:00"
    assert "PRIVATE_CANARY" not in json.dumps(compact)
    logged = sanitized_sports_pipeline(compact, "PRIVATE_CANARY")
    for lane in ("api_football_primary", "live_refresh"):
        assert logged["current_sync"][lane]["failure_categories"] == ["ACCOUNT_SUSPENDED", "FREE_PLAN_RESTRICTED"]
        assert logged["current_sync"][lane]["provider_observation_current"] is True
    assert "PRIVATE_CANARY" not in json.dumps(logged)


@pytest.mark.parametrize('calls', [True, "1", float('inf'), float('nan'), 1.5, -1, None])
def test_invalid_call_counts_cannot_claim_a_new_observation(calls):
    evidence = provider_stage_evidence({"state":"OK", "external_calls":calls, "provider_observation_current":True})
    assert evidence["provider_observation_current"] is False


def test_new_calendar_success_cannot_hide_or_refresh_an_older_live_restriction(app_module, monkeypatch):
    detail = {"sports_pipeline": {"current_sync": {
        "api_football_primary": {"ok": True, "state": "OK", "external_calls": 1, "provider_observation_current": True},
        "live_refresh": {"ok": True, "state": "PROVIDER_FAILURE_BACKOFF_FREE_PLAN_RESTRICTED", "external_calls": 0},
    }}}
    monkeypatch.setattr(app_module, "automation_get_bounded", lambda key, *a, **kw: detail if key == "last_automation_result" else {})
    monkeypatch.setattr(app_module, "env_present", lambda key: True)
    primary = app_module.v945_provider_health_snapshot()["providers"][0]
    assert primary["status"] == "REVISAR_PLAN_ACCESO"
    assert primary["provider_observation_current"] is False


@pytest.mark.parametrize('language,expected', [('es','Suspensión comunicada'), ('en','Suspension reported'), ('fr','Suspension signalée')])
def test_admin_render_explains_both_lanes_without_probing(app_module, monkeypatch, language, expected):
    health = admin_evidence(monkeypatch, app_module)
    monkeypatch.setattr(app_module, 'is_admin_session', lambda: True)
    monkeypatch.setattr(app_module, 'v932_safe_dashboard_data', lambda *a, **kw: ({}, {}))
    monkeypatch.setattr(app_module, 'data_center_summary', lambda: {})
    monkeypatch.setattr(app_module, 'match_calendar_diagnostics', lambda: {})
    monkeypatch.setattr(app_module, 'get_v934_realtime_context', lambda *a: {})
    with app_module.app.test_request_context('/admin/data-center', headers={'Accept-Language': language}):
        html = app_module.admin_data_center_page()
    assert expected in html
    assert html.count('data-provider-observation="REUSED"') == 2
    assert 'PRIVATE_CANARY' not in html
