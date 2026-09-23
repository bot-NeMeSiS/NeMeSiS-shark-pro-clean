"""Direct provider health checks: explicit, bounded and never implicit on render."""
import app as app_module


def _state_store(monkeypatch):
    state = {}

    def get_bounded(key, default=None, max_bytes=64 * 1024):
        return state.get(key, default)

    monkeypatch.setattr(app_module, "automation_get_bounded", get_bounded)
    monkeypatch.setattr(app_module, "automation_set", lambda key, value: state.__setitem__(key, dict(value)))
    return state


def test_api_football_direct_check_marks_paid_only_from_provider_evidence(monkeypatch):
    state = _state_store(monkeypatch)
    monkeypatch.setattr(app_module, "env_present", lambda key: key == "API_FOOTBALL_KEY")
    monkeypatch.setattr(app_module, "probe_api_football_account", lambda: {
        "ok": True, "http_status": 200, "plan": "Pro", "active": True,
        "end": "2026-12-31",
        "quota": {"daily_limit": 1000, "daily_used": 20, "daily_remaining": 980},
        "error": "MUST_NOT_ESCAPE",
    })
    result, status = app_module.v945_provider_direct_check("api_football")
    assert status == 200 and result["ok"] is True
    assert result["plan_state"] == "PAID_PLAN_VERIFIED"
    assert result["quota"]["daily_remaining"] == 980
    assert result["external_calls"] == 1
    assert "MUST_NOT_ESCAPE" not in str(result)
    assert state


def test_direct_check_cooldown_reuses_safe_odds_evidence(monkeypatch):
    _state_store(monkeypatch)
    monkeypatch.setattr(app_module, "env_present", lambda key: key == "THE_ODDS_API_KEY")
    calls = []

    def odds(*_a, **_kw):
        calls.append(1)
        return {
            "ok": True, "http_status": 200,
            "payload": [{"secret_canary": "MUST_NOT_ESCAPE"}],
            "quota": {"requests_remaining": 321, "requests_used": 9, "requests_last": 1},
        }

    monkeypatch.setattr(app_module, "odds_api_request", odds)
    first, _ = app_module.v945_provider_direct_check("the_odds")
    second, _ = app_module.v945_provider_direct_check("the_odds")
    assert first["external_calls"] == 1
    assert first["quota"]["requests_remaining"] == 321
    assert second["external_calls"] == 0 and second["reused"] is True
    assert len(calls) == 1
    assert "MUST_NOT_ESCAPE" not in str(first)


def test_sportsdb_direct_check_requires_real_catalog_shape(monkeypatch):
    _state_store(monkeypatch)
    monkeypatch.setattr(app_module, "thesportsdb_key", lambda: "qa-not-real")
    monkeypatch.setattr(app_module, "sportsdb_v1", lambda *_a, **_kw: {"error": "invalid key"})
    result, status = app_module.v945_provider_direct_check("sportsdb")
    assert status == 200
    assert result["ok"] is False
    assert result["status"] == "PROVIDER_REJECTED"
    assert result.get("items_observed", 0) == 0


def test_missing_configuration_never_calls_provider(monkeypatch):
    _state_store(monkeypatch)
    monkeypatch.setattr(app_module, "env_present", lambda *_a, **_kw: False)
    called = []
    monkeypatch.setattr(app_module, "odds_api_request", lambda *_a, **_kw: called.append(1))
    result, status = app_module.v945_provider_direct_check("the_odds")
    assert status == 200
    assert result["status"] == "NOT_CONFIGURED"
    assert result["external_calls"] == 0
    assert not called


def test_invalid_provider_fails_closed(monkeypatch):
    _state_store(monkeypatch)
    result, status = app_module.v945_provider_direct_check("unknown")
    assert status == 400
    assert result["status"] == "INVALID_PROVIDER"
    assert result["external_calls"] == 0


def test_health_snapshot_only_reads_persisted_direct_evidence(monkeypatch):
    monkeypatch.setattr(app_module, "automation_get_bounded", lambda key, default=None, max_bytes=0: (
        {"ok": True, "status": "CONNECTED", "checked_at": "2026-09-23T19:00:00+02:00",
         "plan": "Pro", "plan_state": "PAID_PLAN_VERIFIED", "external_calls": 1}
        if key == "v945_provider_direct_check:api_football" else {}
    ))
    monkeypatch.setattr(app_module, "env_present", lambda key: key == "API_FOOTBALL_KEY")
    snapshot = app_module.v945_provider_health_snapshot()
    provider = next(item for item in snapshot["providers"] if item["key"] == "api_football")
    assert snapshot["provider_calls_during_render"] == 0
    assert provider["direct_check"]["status"] == "CONNECTED"
    assert "Plan verificado directamente" in provider["billing_status"]


def test_direct_check_http_requires_admin_and_valid_csrf(monkeypatch):
    _state_store(monkeypatch)
    monkeypatch.setattr(app_module, "env_present", lambda *_a, **_kw: False)
    anonymous = app_module.app.test_client()
    blocked = anonymous.post("/api/admin/provider-health/check", json={"provider": "the_odds"})
    assert blocked.status_code == 403

    admin = app_module.app.test_client()
    with admin.session_transaction() as sess:
        sess["user_role"] = "ADMIN"
        valid = app_module.generate_csrf_token(sess)

    bad = admin.post(
        "/api/admin/provider-health/check",
        json={"provider": "the_odds"},
        headers={"X-CSRF-Token": "invalid"},
    )
    assert bad.status_code == 403

    good = admin.post(
        "/api/admin/provider-health/check",
        json={"provider": "the_odds"},
        headers={"X-CSRF-Token": valid},
    )
    assert good.status_code == 200
    payload = good.get_json()
    assert payload["status"] == "NOT_CONFIGURED"
    assert payload["external_calls"] == 0
