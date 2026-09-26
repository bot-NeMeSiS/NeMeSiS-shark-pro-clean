"""Provider observations must preserve unknown values and cache provenance."""
import pytest

import app as app_module


@pytest.mark.parametrize("value", [None, "", True, False, -1, 1.5, "1.5", float("inf"), float("nan"), [], {}])
def test_unknown_or_invalid_quota_is_not_reported_as_zero(value):
    assert app_module._v945_provider_safe_quota({"daily_remaining": value}) == {}


@pytest.mark.parametrize("value,expected", [(0, 0), ("0", 0), (12, 12), ("12", 12), (12.0, 12)])
def test_observed_whole_quota_including_zero_is_preserved(value, expected):
    assert app_module._v945_provider_safe_quota({"daily_remaining": value}) == {"daily_remaining": expected}


def test_health_supports_same_api_key_alias_as_direct_probe(monkeypatch):
    monkeypatch.setattr(app_module, "automation_get_bounded", lambda *a, **k: {})
    monkeypatch.setattr(app_module, "env_present", lambda name: name == "API_FOOTBALL_API_KEY")
    provider = app_module.v945_provider_health_snapshot()["providers"][0]
    assert provider["configured"] is True
    assert provider["status"] == "SIN_VERIFICACION_RECIENTE"


def test_persisted_non_object_direct_evidence_is_ignored(monkeypatch):
    monkeypatch.setattr(app_module, "automation_get_bounded", lambda *a, **k: ["invalid"])
    assert app_module._v945_provider_direct_snapshot("the_odds") == {}


@pytest.mark.parametrize("state,expected", [("CACHE_REUSED", "CACHE"), ("CACHE_FREE_PLAN_RESTRICTED", "REVISAR_PLAN_ACCESO")])
def test_fallback_contribution_does_not_override_cache_or_restriction(monkeypatch, state, expected):
    evidence = {"compact": {"sports_pipeline": {"current_sync": {
        "sportsdb_fallback": {"state": state, "ok": True, "processed": 180}
    }}}}
    monkeypatch.setattr(app_module, "automation_get_bounded", lambda key, *a, **k: evidence if key == "telegram_tick_last_detail" else {})
    monkeypatch.setattr(app_module, "env_present", lambda name: False)
    monkeypatch.setattr(app_module, "sportsdb_v1", lambda *a, **k: pytest.fail("render must not call provider"))
    snapshot = app_module.v945_provider_health_snapshot()
    fallback = next(p for p in snapshot["providers"] if p["key"] == "sportsdb")
    assert fallback["status"] == expected
    assert fallback["processed"] == 180
    assert snapshot["provider_calls_during_render"] == 0
