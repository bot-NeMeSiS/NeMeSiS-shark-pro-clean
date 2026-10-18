"""Focused regressions for public input and credential-reset boundaries."""
import urllib.parse
import xml.etree.ElementTree as ET

import pytest
from werkzeug.exceptions import NotFound


def test_team_crest_svg_escapes_and_bounds_request_label(client):
    hostile = 'Equipo"><script>alert(1)</script><img src=x onerror=alert(2)>'
    response = client.get("/team-crest.svg?" + urllib.parse.urlencode({"name": hostile}))

    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert "<script>" not in response.get_data(as_text=True)
    assert "<img" not in response.get_data(as_text=True)
    root = ET.fromstring(response.get_data(as_text=True))
    assert root.attrib["aria-label"] == hostile

    markup_like_initials = client.get("/team-crest.svg?name=%3C%20script%20%3E")
    initials_root = ET.fromstring(markup_like_initials.get_data(as_text=True))
    svg_ns = {"svg": "http://www.w3.org/2000/svg"}
    assert initials_root.find(".//svg:text", svg_ns).text == "<S>"

    long_name = client.get("/team-crest.svg?name=" + ("A" * 1000))
    assert len(ET.fromstring(long_name.get_data(as_text=True)).attrib["aria-label"]) == 120


def test_password_reset_without_smtp_never_returns_or_creates_public_token(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "get_user_by_login", lambda _identifier: {"id": 41, "email": "member@example.invalid", "role": "FREE"})
    monkeypatch.setattr(app_module, "smtp_configured", lambda: False)
    monkeypatch.setattr(app_module, "local_safe_mode_enabled", lambda: False)
    monkeypatch.setattr(app_module, "create_password_reset_token", lambda *_args: (_ for _ in ()).throw(AssertionError("must not create a token")))
    monkeypatch.setattr(app_module, "telegram_log", lambda *_args, **_kwargs: None)

    result = app_module.password_reset_request("member@example.invalid")

    assert result["ok"] is True
    assert result["diagnostic_reset_url"] == ""
    assert result["delivery"]["mode"] == "smtp_not_configured"


def test_password_reset_diagnostic_is_relative_and_local_safe_only(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "get_user_by_login", lambda _identifier: {"id": 42, "email": "member@example.invalid", "role": "FREE"})
    monkeypatch.setattr(app_module, "smtp_configured", lambda: False)
    monkeypatch.setattr(app_module, "local_safe_mode_enabled", lambda: True)
    monkeypatch.setattr(app_module, "create_password_reset_token", lambda *_args: "synthetic-reset-token")
    monkeypatch.setattr(app_module, "telegram_log", lambda *_args, **_kwargs: None)

    with app_module.app.test_request_context("/forgot-password", headers={"Host": "attacker.invalid"}):
        result = app_module.password_reset_request("member@example.invalid")

    assert result["delivery"]["mode"] == "local_safe_diagnostic"
    assert result["diagnostic_reset_url"].startswith("/reset-password/")
    assert "attacker.invalid" not in result["diagnostic_reset_url"]


def test_password_reset_email_uses_trusted_https_origin_not_host_header(app_module, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://trusted.example/app/")
    monkeypatch.setattr(app_module, "get_user_by_login", lambda _identifier: {"id": 43, "email": "member@example.invalid", "role": "FREE"})
    monkeypatch.setattr(app_module, "smtp_configured", lambda: True)
    monkeypatch.setattr(app_module, "create_password_reset_token", lambda *_args: "synthetic-reset-token")
    sent = {}

    def fake_send(_recipient, _subject, body):
        sent["body"] = body
        return {"ok": True, "sent": True, "mode": "smtp"}

    monkeypatch.setattr(app_module, "send_email_message", fake_send)
    monkeypatch.setattr(app_module, "telegram_log", lambda *_args, **_kwargs: None)

    with app_module.app.test_request_context("/forgot-password", headers={"Host": "attacker.invalid"}):
        result = app_module.password_reset_request("member@example.invalid")

    assert "https://trusted.example/app/reset-password/synthetic-reset-token" in sent["body"]
    assert "attacker.invalid" not in sent["body"]
    assert result["diagnostic_reset_url"] == ""


def test_password_reset_requires_trusted_base_and_invalidates_token_after_send_failure(app_module, monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("APP_PUBLIC_URL", raising=False)
    monkeypatch.delenv("BASE_URL", raising=False)
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    monkeypatch.delenv("CANONICAL_URL", raising=False)
    monkeypatch.setattr(app_module, "get_user_by_login", lambda _identifier: {"id": 44, "email": "member@example.invalid", "role": "FREE"})
    monkeypatch.setattr(app_module, "smtp_configured", lambda: True)
    monkeypatch.setattr(app_module, "local_safe_mode_enabled", lambda: False)
    monkeypatch.setattr(app_module, "create_password_reset_token", lambda *_args: (_ for _ in ()).throw(AssertionError("must not create a token without a trusted origin")))
    monkeypatch.setattr(app_module, "telegram_log", lambda *_args, **_kwargs: None)

    with app_module.app.test_request_context("/forgot-password", headers={"Host": "attacker.invalid"}):
        result = app_module.password_reset_request("member@example.invalid")

    assert result["delivery"]["mode"] == "trusted_public_url_missing"
    assert result["diagnostic_reset_url"] == ""

    monkeypatch.setenv("PUBLIC_BASE_URL", "https://trusted.example")
    monkeypatch.setattr(app_module, "create_password_reset_token", lambda *_args: "synthetic-reset-token")
    revoked = []
    monkeypatch.setattr(app_module, "send_email_message", lambda *_args: {"ok": False, "mode": "smtp"})
    monkeypatch.setattr(app_module, "mark_password_reset_used", revoked.append)
    with app_module.app.test_request_context("/forgot-password", headers={"Host": "attacker.invalid"}):
        failed_delivery = app_module.password_reset_request("member@example.invalid")

    assert failed_delivery["diagnostic_reset_url"] == ""
    assert revoked == ["synthetic-reset-token"]


def test_legacy_telegram_automation_rejects_secret_in_query_and_json(client, app_module, monkeypatch):
    monkeypatch.setenv("AUTOMATION_SECRET", "header-only-test-secret")
    monkeypatch.setattr(app_module, "telegram_config", lambda: {"enabled": True})
    monkeypatch.setattr(app_module, "telegram_scheduler_delivery", lambda **_kwargs: {"ok": True, "status": "QA_SENT"})
    route = "/api/telegram/auto-run"

    query = client.post(route + "?secret=header-only-test-secret", json={})
    body = client.post(route, json={"secret": "header-only-test-secret"})
    header = client.post(route, json={}, headers={"X-Automation-Secret": "header-only-test-secret"})

    assert query.status_code == 403
    assert body.status_code == 403
    assert header.status_code == 200
    assert header.get_json()["status"] == "QA_SENT"


def test_admin_bootstrap_is_unavailable_outside_local_safe_or_test_setup(client, app_module, monkeypatch):
    monkeypatch.setitem(app_module.app.config, "TESTING", False)
    monkeypatch.setattr(app_module, "NEMESIS_LOCAL_SAFE_MODE", False)
    monkeypatch.setattr(app_module, "admin_exists", lambda: (_ for _ in ()).throw(AssertionError("route must stop before checking admin state")))

    with app_module.app.test_request_context("/admin-bootstrap"):
        with pytest.raises(NotFound):
            app_module.admin_bootstrap_page()


def test_growth_funnel_rejects_oversized_json_before_processing(client):
    client.get("/landing")
    with client.session_transaction() as session:
        csrf = session["csrf_token"]
    response = client.post(
        "/api/growth/funnel-event",
        data='{"stage":"LANDING","padding":"' + ("x" * (16 * 1024)) + '"}',
        content_type="application/json",
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 413
    assert response.get_json()["error"] == "request_body_too_large"
