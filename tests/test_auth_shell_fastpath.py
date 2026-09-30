"""Auth shell must not depend on sports/payment dashboard builders."""


def _boom(*_args, **_kwargs):
    raise AssertionError("home_light_data/dashboard_data must not run on auth shell")


def _capture(monkeypatch, app_module):
    captured = {}
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: captured.update(name=name, **ctx) or "ok")
    return captured


def test_auth_shell_data_is_minimal(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "home_light_data", _boom)
    monkeypatch.setattr(app_module, "dashboard_data", _boom)
    data = app_module.auth_shell_data("pro", "/app")
    assert data["selected_plan"] == "PRO"
    assert data["next_url"] == "/app"
    assert set(data) == {"app_name", "version", "date", "selected_plan", "next_url"}


def test_register_get_does_not_build_home(app_module, monkeypatch):
    captured = _capture(monkeypatch, app_module)
    monkeypatch.setattr(app_module, "home_light_data", _boom)
    monkeypatch.setattr(app_module, "dashboard_data", _boom)
    monkeypatch.setattr(app_module, "capture_growth_attribution_from_request", lambda: None)
    monkeypatch.setattr(app_module, "_store_pending_checkout_plan", lambda value: (value or "").upper())
    monkeypatch.setattr(app_module, "current_session_user", lambda: None)
    monkeypatch.setattr(app_module, "growth_is_first10_attribution", lambda *_args, **_kwargs: False)
    with app_module.app.test_request_context("/registro?plan=PRO&next=/app"):
        assert app_module.register_page() == "ok"
    assert captured["name"] == "register.html"
    assert captured["data"]["selected_plan"] == "PRO"
    assert captured["data"]["next_url"] == "/app"


def test_client_login_get_does_not_build_home(app_module, monkeypatch):
    captured = _capture(monkeypatch, app_module)
    monkeypatch.setattr(app_module, "home_light_data", _boom)
    monkeypatch.setattr(app_module, "dashboard_data", _boom)
    monkeypatch.setattr(app_module, "_store_pending_checkout_plan", lambda value: (value or "").upper())
    monkeypatch.setattr(app_module, "current_session_user", lambda: None)
    with app_module.app.test_request_context("/cliente-login?plan=ELITE&next=/app"):
        assert app_module.client_login_page() == "ok"
    assert captured["name"] == "client_login.html"
    assert captured["data"]["selected_plan"] == "ELITE"
    assert captured["data"]["next_url"] == "/app"


def test_password_recovery_gets_are_dashboard_independent(app_module, monkeypatch):
    captured = _capture(monkeypatch, app_module)
    monkeypatch.setattr(app_module, "home_light_data", _boom)
    monkeypatch.setattr(app_module, "dashboard_data", _boom)
    monkeypatch.setattr(app_module, "load_password_reset_token", lambda *_args, **_kwargs: None)

    with app_module.app.test_request_context("/forgot-password"):
        assert app_module.forgot_password_page() == "ok"
        assert captured["name"] == "password_reset_request.html"
        assert captured["admin"] is False

    captured.clear()
    with app_module.app.test_request_context("/reset-password/invalid"):
        assert app_module.reset_password_page("invalid") == "ok"
        assert captured["name"] == "password_reset_form.html"
        assert captured["admin"] is False

    captured.clear()
    with app_module.app.test_request_context("/admin-forgot-password"):
        assert app_module.admin_forgot_password_page() == "ok"
        assert captured["name"] == "password_reset_request.html"
        assert captured["admin"] is True

    captured.clear()
    with app_module.app.test_request_context("/admin-reset-password/invalid"):
        assert app_module.admin_reset_password_page("invalid") == "ok"
        assert captured["name"] == "password_reset_form.html"
        assert captured["admin"] is True


def test_admin_login_get_does_not_build_home(app_module, monkeypatch):
    captured = _capture(monkeypatch, app_module)
    monkeypatch.setattr(app_module, "home_light_data", _boom)
    monkeypatch.setattr(app_module, "dashboard_data", _boom)
    monkeypatch.setattr(app_module, "is_admin_session", lambda: False)
    with app_module.app.test_request_context("/admin-login"):
        assert app_module.admin_login_page() == "ok"
    assert captured["name"] == "admin_login.html"
    assert "configured" in captured
