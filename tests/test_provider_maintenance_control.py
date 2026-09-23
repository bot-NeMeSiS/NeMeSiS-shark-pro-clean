"""Provider maintenance/admin contract. Synthetic callbacks only; no real network."""
from datetime import datetime


def admin_client(app_module, role="ADMIN"):
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        if role:
            sess.update(user_id="provider-maintenance-qa", user_role=role, membership=role)
        token = app_module.generate_csrf_token(sess)
    return client, {"X-CSRF-Token": token}


def stub_local_state(app_module, monkeypatch, state=None):
    state = state if state is not None else {}
    monkeypatch.setattr(app_module, "automation_get", lambda key, default=None: state.get(key, default))
    monkeypatch.setattr(app_module, "automation_set", lambda key, value: state.__setitem__(key, dict(value)))
    monkeypatch.setattr(app_module, "get_api_sports_status", lambda *_: {
        "api_sports_configured": True, "api_sports_provider_available": True,
        "last_sync": "2026-09-23T17:00:00+02:00", "last_error": "",
        "fixtures_cached": 3, "events_cached": 2, "stats_cached": 4,
    })
    monkeypatch.setattr(app_module, "sportsdb_feed_status", lambda: {
        "key_present": True, "cached_matches": 180,
        "last_cached_update": "2026-09-23T17:00:00+02:00", "last_sync": {},
    })
    monkeypatch.setattr(app_module, "odds_last_sync", lambda: {
        "status": "CACHE_REUSED", "last_sync": "2026-09-23T17:00:00+02:00",
        "processed": 12,
    })
    monkeypatch.setattr(app_module, "dashboard_data", lambda: {"telegram": {"configured": False}, "sportsdb": {}})
    monkeypatch.setattr(app_module, "one", lambda *a, **k: {"total": 0})
    monkeypatch.setattr(app_module, "admin_exists", lambda: True)
    return state


def test_maintenance_page_never_calls_providers_on_render(app_module, monkeypatch):
    stub_local_state(app_module, monkeypatch)
    monkeypatch.setenv("API_FOOTBALL_KEY", "qa-not-real")
    monkeypatch.setenv("ENABLE_API_FOOTBALL_PROVIDER", "true")
    monkeypatch.setenv("THE_ODDS_API_KEY", "qa-not-real")
    monkeypatch.setenv("ENABLE_ODDS_API", "true")
    monkeypatch.setenv("THESPORTSDB_KEY", "qa-not-real")
    monkeypatch.setattr(app_module, "probe_api_football_account", lambda: (_ for _ in ()).throw(AssertionError("network")))
    monkeypatch.setattr(app_module, "odds_api_request", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    monkeypatch.setattr(app_module, "sportsdb_v1", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    client, _ = admin_client(app_module)
    response = client.get("/admin/platform-maintenance")
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "API-Football / API-Sports" in text
    assert "The Odds API" in text
    assert "TheSportsDB" in text
    assert "Llamadas al abrir" in text
    assert "0" in text


def test_status_api_is_admin_only_and_read_only(app_module, monkeypatch):
    stub_local_state(app_module, monkeypatch)
    assert app_module.app.test_client().get("/api/admin/provider-maintenance/status").status_code == 403
    client, _ = admin_client(app_module)
    result = client.get("/api/admin/provider-maintenance/status")
    payload = result.get_json()
    assert result.status_code == 200
    assert payload["maintenance"]["external_calls_on_page_load"] == 0
    assert payload["maintenance"]["secrets_visible"] is False


def test_api_football_direct_check_verifies_paid_plan_and_saves_safe_evidence(app_module, monkeypatch):
    state = stub_local_state(app_module, monkeypatch)
    monkeypatch.setenv("API_FOOTBALL_KEY", "PRIVATE_QA_KEY")
    monkeypatch.setattr(app_module, "probe_api_football_account", lambda: {
        "ok": True, "http_status": 200, "configured": True, "plan": "Pro",
        "active": True, "end": "2026-12-31",
        "quota": {"daily_limit": 1000, "daily_used": 20, "daily_remaining": 980},
        "error": "PRIVATE_PROVIDER_TEXT",
    })
    client, headers = admin_client(app_module)
    response = client.post("/api/admin/provider-maintenance/check", json={"provider": "api_football"}, headers=headers)
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["plan_state"]["code"] == "PAID_PLAN_VERIFIED"
    assert payload["quota"]["daily_remaining"] == 980
    assert payload["external_calls"] == 1
    assert "PRIVATE_QA_KEY" not in response.get_data(as_text=True)
    assert "PRIVATE_PROVIDER_TEXT" not in response.get_data(as_text=True)
    assert state


def test_direct_check_cooldown_prevents_second_paid_call(app_module, monkeypatch):
    state = stub_local_state(app_module, monkeypatch)
    monkeypatch.setenv("THE_ODDS_API_KEY", "PRIVATE_ODDS_KEY")
    calls = []
    def odds(*args, **kwargs):
        calls.append(1)
        return {"ok": True, "http_status": 200, "payload": [{"key": "soccer"}],
                "quota": {"requests_remaining": 500, "requests_used": 10}}
    monkeypatch.setattr(app_module, "odds_api_request", odds)
    client, headers = admin_client(app_module)
    first = client.post("/api/admin/provider-maintenance/check", json={"provider": "the_odds_api"}, headers=headers).get_json()
    second = client.post("/api/admin/provider-maintenance/check", json={"provider": "the_odds_api"}, headers=headers).get_json()
    assert first["external_calls"] == 1
    assert second["external_calls"] == 0 and second["reused"] is True
    assert len(calls) == 1
    assert "payload" not in str(state)


def test_odds_direct_check_exposes_quota_not_provider_payload(app_module, monkeypatch):
    stub_local_state(app_module, monkeypatch)
    monkeypatch.setenv("THE_ODDS_API_KEY", "PRIVATE_ODDS_KEY")
    monkeypatch.setattr(app_module, "odds_api_request", lambda *a, **k: {
        "ok": True, "http_status": 200,
        "payload": [{"secret_canary": "MUST_NOT_ESCAPE"}],
        "quota": {"requests_remaining": 321, "requests_used": 9, "requests_last": 1},
    })
    client, headers = admin_client(app_module)
    response = client.post("/api/admin/provider-maintenance/check", json={"provider": "the_odds_api"}, headers=headers)
    text = response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["ok"] and payload["items_observed"] == 1
    assert payload["quota"]["requests_remaining"] == 321
    assert "MUST_NOT_ESCAPE" not in text


def test_sportsdb_direct_check_counts_only_and_invalid_provider_fails_closed(app_module, monkeypatch):
    stub_local_state(app_module, monkeypatch)
    monkeypatch.setenv("THESPORTSDB_KEY", "PRIVATE_SPORTSDB_KEY")
    monkeypatch.setattr(app_module, "sportsdb_v1", lambda *a, **k: {
        "leagues": [{"idLeague": "1", "private": "MUST_NOT_ESCAPE"}]
    })
    client, headers = admin_client(app_module)
    good = client.post("/api/admin/provider-maintenance/check", json={"provider": "thesportsdb"}, headers=headers)
    bad = client.post("/api/admin/provider-maintenance/check", json={"provider": "unknown"}, headers=headers)
    assert good.status_code == 200 and good.get_json()["items_observed"] == 1
    assert "MUST_NOT_ESCAPE" not in good.get_data(as_text=True)
    assert bad.status_code == 400 and bad.get_json()["status"] == "INVALID_PROVIDER"


def test_direct_check_requires_admin_and_csrf(app_module, monkeypatch):
    stub_local_state(app_module, monkeypatch)
    client, headers = admin_client(app_module, role=None)
    assert client.post("/api/admin/provider-maintenance/check", json={"provider": "api_football"}, headers=headers).status_code == 403
    admin, _ = admin_client(app_module)
    assert admin.post("/api/admin/provider-maintenance/check", json={"provider": "api_football"}, headers={"X-CSRF-Token": "invalid"}).status_code == 403


def test_sportsdb_error_json_is_not_false_green(app_module, monkeypatch):
    stub_local_state(app_module, monkeypatch)
    monkeypatch.setenv("THESPORTSDB_KEY", "PRIVATE_SPORTSDB_KEY")
    monkeypatch.setattr(app_module, "sportsdb_v1", lambda *a, **k: {"error": "invalid key"})
    client, headers = admin_client(app_module)
    response = client.post("/api/admin/provider-maintenance/check", json={"provider": "thesportsdb"}, headers=headers)
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is False
    assert payload["status"] == "PROVIDER_REJECTED"
    assert payload["items_observed"] == 0


def test_admin_navigation_names_existing_system_route_as_maintenance(app_module):
    directory = app_module.v807_admin_directory()
    item = next(row for row in directory if row.get("href") == "/admin/system")
    assert item["title"] == "Mantenimiento"
    partial = (app_module.BASE_DIR / "templates" / "partials" / "admin_visual_system.html").read_text(encoding="utf-8")
    assert "('Mantenimiento','/admin/system','⚙')" in partial
