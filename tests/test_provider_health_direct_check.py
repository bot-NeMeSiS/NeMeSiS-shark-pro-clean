"""Direct provider health checks: explicit, bounded and never implicit on render."""
from contextlib import closing

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
    assert provider["direct_check"]["freshness"] == "LAST_OBSERVED_NOT_CURRENT"
    assert provider["billing_status"] == "Comprobación directa anterior; no confirma el estado actual"


def test_direct_check_http_requires_admin_and_valid_csrf(monkeypatch,tmp_path):
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "provider-admin.sqlite3"))
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(app_module, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(app_module, "APP_INITIALIZED", False)
    app_module.seed_core()
    with closing(app_module.db()) as conn, conn:
        admin_id = app_module.create_admin_record(
            conn, "Provider QA", "provider-qa", "provider-qa@example.invalid", "local-qa-password")
    user = app_module.get_user_by_id(admin_id)
    _state_store(monkeypatch)
    monkeypatch.setattr(app_module, "env_present", lambda *_a, **_kw: False)
    anonymous = app_module.app.test_client()
    blocked = anonymous.post("/api/admin/provider-health/check", json={"provider": "the_odds"})
    assert blocked.status_code == 403

    admin = app_module.app.test_client()
    with app_module.app.test_request_context():
        app_module.set_login_session(user)
        signed_in = dict(app_module.session)
    with admin.session_transaction() as sess:
        sess.clear()
        sess.update(signed_in)
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


def test_single_fixture_renewal_http_keeps_admin_csrf_and_server_proof(monkeypatch, tmp_path):
    real_render = app_module.render_template
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "renewal-admin.sqlite3"))
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(app_module, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(app_module, "APP_INITIALIZED", False)
    app_module.seed_core()
    with closing(app_module.db()) as conn, conn:
        admin_id = app_module.create_admin_record(
            conn, "Renewal QA", "renewal-qa", "renewal-qa@example.invalid", "local-qa-password")
    user = app_module.get_user_by_id(admin_id)
    state = _state_store(monkeypatch)
    trusted = {"provider": "api_football", "status": "CONNECTED", "ok": True,
               "active": True, "http_status": 200, "plan": "Pro",
               "plan_state": "PAID_PLAN_VERIFIED", "external_calls": 1,
               "checked_at": "2026-11-27T21:26:15+00:00"}
    state["v945_provider_direct_check:api_football"] = trusted
    calls = []
    def collect(path, **kwargs):
        calls.append((path, kwargs))
        return {"ok": True, "status": "OK", "external_calls": 1, "stats_inserted": 3}
    monkeypatch.setattr(app_module, "refresh_api_football_statistics_if_due", collect)
    monkeypatch.setattr(app_module, "probe_api_football_account",
                        lambda: (_ for _ in ()).throw(AssertionError("no repeated status probe")))
    endpoint = "/api/admin/provider-health/api-football/recover-statistics"
    anonymous = app_module.app.test_client()
    with anonymous.session_transaction() as sess:
        anonymous_csrf = app_module.generate_csrf_token(sess)
    assert anonymous.post(endpoint, json={"match_id": "af-101"},
                          headers={"X-CSRF-Token": anonymous_csrf}).status_code == 403
    admin = app_module.app.test_client()
    with app_module.app.test_request_context():
        app_module.set_login_session(user)
        signed_in = dict(app_module.session)
    with admin.session_transaction() as sess:
        sess.clear(); sess.update(signed_in)
        csrf = app_module.generate_csrf_token(sess)
    assert admin.post(endpoint, json={"match_id": "af-101"},
                      headers={"X-CSRF-Token": "invalid"}).status_code == 403
    for payload in ([], {"match_id": ["101"]}, {"match_id": "101", "force": True},
                    {"match_id": "101", "check": trusted}, {"match_id": "101/../102"},
                    {"match_id": "101", "env": {"API_FOOTBALL_DAILY_CALL_BUDGET": "999999"}}):
        assert admin.post(endpoint, json=payload, headers={"X-CSRF-Token": csrf}).status_code == 400
    assert calls == []
    response = admin.post(endpoint, json={"match_id": "af-101"}, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200 and response.get_json()["stats_inserted"] == 3
    assert calls == [(app_module.DB_PATH, {"limit": 1,
                      "renewal_request": {"fixture_id": "af-101", "check": trusted}})]
    assert admin.get(endpoint).status_code == 405
    assert len(calls) == 1

    # The redirect after an explicit check must read its saved receipt, not an
    # older v932 projection; neither path may perform a second provider probe.
    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", lambda *a, **k: ({}, {}))
    monkeypatch.setattr(app_module, "get_v934_realtime_context", lambda *a, **k: {})
    monkeypatch.setattr(app_module, "v932_admin_data_center_fallback", lambda *a: {})
    monkeypatch.setattr(app_module, "v932_admin_sports_diagnostics", lambda *a: {})
    monkeypatch.setattr(app_module, "v932_safe_context",
                        lambda path, scope, key, loader, fallback: {"source": "OLD_CACHE"} if key == "provider_health" else {})
    fresh_reads = []
    def saved_receipt():
        fresh_reads.append(True)
        return {"source": "CURRENT_SAVED_RECEIPT", "provider_calls_during_render": 0,
                "providers": [{"key": "api_football", "direct_check": trusted}]}
    monkeypatch.setattr(app_module, "v945_provider_health_snapshot", saved_receipt)
    monkeypatch.setattr(app_module, "render_template",
                        lambda name, **kw: app_module.jsonify(kw["data"]["provider_health"]))
    normal = admin.get("/admin/data-center")
    assert normal.get_json()["source"] == "OLD_CACHE" and fresh_reads == []
    checked = admin.get("/admin/data-center?provider_check=CONNECTED")
    assert checked.status_code == 200 and checked.get_json()["source"] == "CURRENT_SAVED_RECEIPT"
    assert checked.get_json()["provider_calls_during_render"] == 0 and fresh_reads == [True]
    def unavailable():
        import sqlite3
        raise sqlite3.OperationalError("synthetic unreadable receipt")
    monkeypatch.setattr(app_module, "v945_provider_health_snapshot", unavailable)
    unknown = admin.get("/admin/data-center?provider_check=CONNECTED")
    assert unknown.get_json()["source"] == "UNAVAILABLE"
    assert len(calls) == 1

    monkeypatch.setattr(app_module, "render_template", real_render)
    monkeypatch.setattr(app_module, "v945_provider_health_snapshot", saved_receipt)
    rendered = admin.get("/admin/data-center?provider_check=CONNECTED")
    assert rendered.status_code == 200
    html = rendered.get_data(as_text=True)
    assert 'action="/admin/provider-health/api-football/recover-statistics"' in html
    assert 'for="renewal-statistics-match"' in html
    assert 'name="match_id"' in html and 'name="csrf_token"' in html
    assert "Recuperar estadísticas de este partido" in html
    assert len(calls) == 1
