"""Founder OS must not tax every route or rebuild the sports dashboard."""


def _boom(*_args, **_kwargs):
    raise AssertionError("dashboard_data must not run on Founder OS")


def test_founder_os_page_skips_dashboard_data(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "is_admin_session", lambda: True)
    monkeypatch.setattr(app_module, "dashboard_data", _boom)
    monkeypatch.setattr(app_module, "current_session_user", lambda: {"id": "admin", "role": "ADMIN"})
    monkeypatch.setattr(app_module, "founder_os_snapshot", lambda *_a, **_kw: {"available": True})
    captured = {}
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: captured.update(name=name, **ctx) or "ok")
    with app_module.app.test_request_context("/admin/founder-os"):
        assert app_module.admin_founder_os_page() == "ok"
    assert captured["name"] == "admin_founder_os.html"
    assert captured["data"]["session_user"]["id"] == "admin"


def test_founder_stylesheet_is_route_scoped(app_module, monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "is_admin_session", lambda: False)
    public_html = client.get("/cliente-login").get_data(as_text=True)
    assert "founder-os.css" not in public_html

    monkeypatch.setattr(app_module, "is_admin_session", lambda: True)
    monkeypatch.setattr(app_module, "founder_os_snapshot", lambda *_a, **_kw: {"available": False, "safe_error": "QA"})
    monkeypatch.setattr(app_module, "current_session_user", lambda: {"id": "admin", "role": "ADMIN"})
    founder_html = client.get("/admin/founder-os").get_data(as_text=True)
    assert "founder-os.css" in founder_html
