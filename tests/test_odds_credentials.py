import io
import json
import urllib.error
import urllib.parse
from datetime import datetime, timedelta

import pytest

from engines import odds_credentials as credentials


@pytest.fixture(autouse=True)
def isolated_keys(monkeypatch):
    for name in credentials.NAMES.values():
        monkeypatch.delenv(name, raising=False)
    for name in ("ODDS_LEGACY_PROFILE", "ODDS_FREE_MAX_COMPETITIONS", "ODDS_FREE_REFRESH_MINUTES",
                 "ODDS_FREE_MAX_REGIONS", "ODDS_FREE_MAX_MARKETS"):
        monkeypatch.delenv(name, raising=False)


def error(status, code):
    return urllib.error.HTTPError("https://provider.invalid/?apiKey=PRIVATE", status,
                                 "PRIVATE", {"x-requests-remaining": "44"},
                                 io.BytesIO(json.dumps({"error_code": code, "message": "PRIVATE"}).encode()))


def transport(responses, calls):
    def get(url, timeout):
        calls.append(urllib.parse.parse_qs(urllib.parse.urlparse(url).query))
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return {"payload": result, "http_status": 200, "headers": {"requests_remaining": "44"}}
    return get


def keys(monkeypatch):
    monkeypatch.setenv("THE_ODDS_API_KEY_PAID", "paid-placeholder")
    monkeypatch.setenv("THE_ODDS_API_KEY_FREE", "free-placeholder")
    monkeypatch.setenv("THE_ODDS_API_KEY", "legacy-placeholder")


def test_paid_valid_does_not_touch_free(monkeypatch):
    keys(monkeypatch)
    calls = []
    result = credentials.request("sports/soccer/odds", {}, transport([[]], calls))
    assert len(calls) == 1
    assert result["credential_tier_selected"] == "PAID"
    assert not result["fallback_used"]


@pytest.mark.parametrize("status,code", [(401, "DEACTIVATED_KEY"), (403, "INVALID_KEY"), (401, "UNAUTHORIZED")])
def test_auth_falls_back_once_and_paid_recovers_next_refresh(monkeypatch, status, code):
    keys(monkeypatch)
    calls = []
    result = credentials.request("sports/soccer/odds", {"regions": "eu,uk", "markets": "totals,h2h"},
                                 transport([error(status, code), []], calls))
    assert result["ok"] and result["fallback_used"] and result["external_calls"] == 2
    assert result["credential_tier_selected"] == "FREE"
    assert calls[1]["regions"] == ["eu"] and calls[1]["markets"] == ["h2h"]
    next_result = credentials.request("sports/soccer/odds", {}, transport([[]], calls))
    assert next_result["credential_tier_selected"] == "PAID"
    assert calls[-1]["apiKey"] == ["paid-placeholder"]


@pytest.mark.parametrize("failure", [
    (429, "EXCEEDED_FREQ_LIMIT"), (401, "OUT_OF_USAGE_CREDITS"), (403, "HISTORICAL_UNAVAILABLE_ON_FREE_USAGE_PLAN"),
    (401, "UNKNOWN"), (500, "DEACTIVATED_KEY"), (503, "INVALID_KEY"),
    TimeoutError("PRIVATE"), urllib.error.URLError("PRIVATE")])
def test_no_fallback_for_quota_timeout_server_or_ambiguous_errors(monkeypatch, failure, caplog):
    keys(monkeypatch)
    calls = []
    exc = error(*failure) if isinstance(failure, tuple) else failure
    result = credentials.request("sports/soccer/odds", {}, transport([exc], calls))
    assert len(calls) == 1 and not result["ok"] and not result["fallback_used"]
    rendered = json.dumps(result) + caplog.text
    assert all(secret not in rendered for secret in ("PRIVATE", "paid-placeholder", "free-placeholder", "legacy-placeholder"))


def test_auth_chain_stops_after_one_fallback(monkeypatch):
    keys(monkeypatch)
    calls = []
    result = credentials.request("sports/soccer/odds", {},
                                 transport([error(401, "INVALID_KEY"), error(401, "INVALID_KEY")], calls))
    assert not result["ok"] and len(calls) == 2
    assert result["credential_tier_selected"] == "FREE"


@pytest.mark.parametrize("tier", ["FREE", "LEGACY"])
def test_single_compatible_key(monkeypatch, tier):
    monkeypatch.setenv(credentials.NAMES[tier], "placeholder")
    calls = []
    result = credentials.request("sports/soccer/odds", {}, transport([[]], calls))
    assert result["ok"] and result["credential_tier_selected"] == tier and len(calls) == 1


def test_paid_auth_can_fall_back_to_legacy(monkeypatch):
    monkeypatch.setenv("THE_ODDS_API_KEY_PAID", "placeholder-paid")
    monkeypatch.setenv("THE_ODDS_API_KEY", "placeholder-legacy")
    calls = []
    result = credentials.request("sports/soccer/odds", {}, transport([error(401, "INVALID_KEY"), []], calls))
    assert result["ok"] and result["credential_tier_selected"] == "LEGACY" and len(calls) == 2


def test_missing_key_is_controlled(app_module, monkeypatch):
    result = credentials.request("sports/soccer/odds", {}, lambda *a, **kw: pytest.fail("provider called"))
    assert not result["ok"] and result["error"] == "missing_key" and result["external_calls"] == 0
    monkeypatch.setattr(app_module, "seed_core", lambda: None)
    assert app_module.sync_odds_events()["sin_key"]


def test_free_profile_limits_fanout_and_keeps_configuration(app_module, monkeypatch):
    monkeypatch.setenv("THE_ODDS_API_KEY_FREE", "placeholder")
    monkeypatch.setenv("ODDS_REGIONS", "eu,uk")
    monkeypatch.setenv("ODDS_MARKETS", "totals,h2h")
    monkeypatch.setattr(app_module, "odds_last_sync", lambda: {})
    monkeypatch.setattr(app_module, "odds_competitions", lambda: [
        {"odds_key": "soccer_a", "name": "A"}, {"odds_key": "soccer_b", "name": "B"}])
    calls = []
    monkeypatch.setattr(app_module, "fetch_json_response", transport([[{"id": "real-event", "bookmakers": []}]], calls))
    events, errors, quota = app_module.fetch_odds_events()
    assert len(calls) == 1 and len(events) == 1 and not errors
    assert quota["controlled_deferrals"] == ["FREE_FANOUT"]
    assert app_module.os.getenv("ODDS_REGIONS") == "eu,uk"
    assert app_module.os.getenv("ODDS_MARKETS") == "totals,h2h"
    assert app_module.odds_cache_minutes() >= 360


def test_free_cache_preserved_without_provider_call(app_module, monkeypatch):
    monkeypatch.setenv("THE_ODDS_API_KEY", "placeholder")
    monkeypatch.setenv("ENABLE_ODDS_API", "true")
    monkeypatch.setattr(app_module, "seed_core", lambda: None)
    monkeypatch.setattr(app_module, "odds_last_sync", lambda: {
        "last_sync": (datetime.now(app_module.TZ) - timedelta(hours=2)).isoformat(),
        "processed": 12, "quota": {"requests_remaining": 44}})
    monkeypatch.setattr(app_module, "fetch_odds_events", lambda **kw: pytest.fail("cache must be reused"))
    result = app_module.sync_odds_events()
    assert result["status"] == "CACHE_REUSED" and result["external_calls"] == 0
    assert result["cached_processed"] == 12 and result["quota"]["requests_remaining"] == 44


def test_free_budget_prevents_fallback_spend_but_not_paid_recovery(app_module, monkeypatch):
    keys(monkeypatch)
    stamp = datetime.now(app_module.TZ).isoformat()
    monkeypatch.setattr(app_module, "odds_last_sync", lambda: {"quota": {"last_free_refresh_at": stamp}})
    calls = []
    monkeypatch.setattr(app_module, "fetch_json_response", transport([error(401, "DEACTIVATED_KEY")], calls))
    result = app_module.odds_api_request("sports/soccer/odds")
    assert len(calls) == 1 and result["controlled_deferrals"] == ["FREE_BUDGET"]
    assert result["http_status"] == 401 and not result["fallback_used"]
    monkeypatch.setattr(app_module, "fetch_json_response", transport([[]], calls))
    assert app_module.odds_api_request("sports/soccer/odds")["credential_tier_selected"] == "PAID"


def test_refresh_scope_avoids_repeated_paid_auth_failures(monkeypatch):
    keys(monkeypatch)
    calls = []
    get = transport([error(401, "INVALID_KEY"), [], []], calls)
    with credentials.refresh_selection():
        credentials.request("sports/a/odds", {}, get)
        credentials.request("sports/b/odds", {}, get)
    assert [c["apiKey"][0] for c in calls] == ["paid-placeholder", "free-placeholder", "free-placeholder"]


def test_safe_diagnostics_never_mask_odds_secret(app_module, monkeypatch, caplog):
    monkeypatch.setenv("THE_ODDS_API_KEY", "SENSITIVE-KEY-CANARY")
    monkeypatch.setattr(app_module, "one", lambda *a, **kw: {})
    monkeypatch.setattr(app_module, "odds_last_sync", lambda: {})
    monkeypatch.setattr(app_module, "odds_client_visibility_diagnostics", lambda: {})
    result = app_module.odds_diagnostics()
    assert result["key_masked"] == "configured"
    assert "SENSITIVE" not in json.dumps(result) + caplog.text


def test_fallback_respects_cron_deadline(monkeypatch):
    from engines.cron_request_budget import CronRequestBudget
    keys(monkeypatch)
    calls = []
    now = [0.0]
    def get(url, timeout):
        calls.append(1)
        now[0] = 16.0
        raise error(401, "DEACTIVATED_KEY")
    with CronRequestBudget(16, clock=lambda: now[0]):
        result = credentials.request("sports/a/odds", {}, get)
    assert len(calls) == 1 and result["controlled_deferrals"] == ["TIME_BUDGET"]
    assert not result["fallback_used"]


def test_compact_metadata_is_safe_and_current(app_module):
    result = app_module._cron_compact_payload("odds_sync", {
        "ok": True, "external_calls": 2,
        "quota": {"credential_tier_selected": "FREE", "fallback_used": True,
                  "http_status": 200, "requests_remaining": 44}}, "start", "end")
    assert result["credential_tier_selected"] == "FREE" and result["fallback_used"]
    assert result["provider_http"] == 200 and result["provider_observation_current"]


def test_configurable_free_limits_and_invalid_defaults(monkeypatch):
    monkeypatch.setenv("ODDS_FREE_MAX_REGIONS", "2")
    monkeypatch.setenv("ODDS_FREE_MAX_MARKETS", "2")
    assert credentials.profile_params({"regions": "eu,uk,us", "markets": "totals,h2h,spreads"}, "FREE") == {
        "regions": "eu,uk", "markets": "h2h,totals"}
    monkeypatch.setenv("ODDS_FREE_MAX_REGIONS", "invalid")
    assert credentials.positive_setting("ODDS_FREE_MAX_REGIONS", 1) == 1
