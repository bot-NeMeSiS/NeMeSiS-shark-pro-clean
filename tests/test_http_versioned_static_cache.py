"""Regression coverage for safe HTTP caching of versioned public static assets."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_service_worker_keeps_private_navigation_out_of_cache_storage():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index("def service_worker():")
    end = source.index("def pwa_install_guide_page():", start)
    route = source[start:end]
    assert "req.mode==='navigate'" in route
    assert "cache:'no-store'" in route
    assert "caches.open" not in route
    assert "cache.put" not in route
    assert "cache.match" not in route
    assert "url.pathname.startsWith('/static/')" in route
    assert "url.searchParams.has('v')" in route
    assert "cache:'force-cache'" in route


def test_versioned_css_gets_long_lived_immutable_http_cache(app_module):
    client = app_module.app.test_client()
    response = client.get("/static/app.css?v=qa-performance")
    assert response.status_code == 200
    cache_control = response.headers.get("Cache-Control", "")
    assert "public" in cache_control
    assert "max-age=31536000" in cache_control
    assert "immutable" in cache_control


def test_unversioned_css_is_not_promoted_to_immutable(app_module):
    client = app_module.app.test_client()
    response = client.get("/static/app.css")
    assert response.status_code == 200
    assert "immutable" not in response.headers.get("Cache-Control", "")


def test_private_html_and_api_cache_contract_remains_no_store(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "current_session_user", lambda: {"id": "qa", "role": "CLIENT", "membership": "FREE"})
    with app_module.app.test_request_context("/api/client/success"):
        app_module.session["user_id"] = "qa"
        response = app_module.app.make_response(("{}", 200, {"Content-Type": "application/json"}))
        response = app_module.apply_security_headers_and_csrf(response)
        assert "no-store" in response.headers.get("Cache-Control", "")
