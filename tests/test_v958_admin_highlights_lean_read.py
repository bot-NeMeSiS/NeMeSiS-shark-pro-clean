import pytest


@pytest.mark.parametrize(
    "path,expected_kind",
    [
        ("/admin/highlights-center", "html"),
        ("/api/admin/highlights/status", "json"),
    ],
)
def test_admin_highlights_center_uses_only_its_catalogue_read(
    app_module, monkeypatch, path, expected_kind
):
    """Admin highlights must not build an unrelated full sports dashboard."""
    user = {"id": "admin-v958-test", "role": "ADMIN", "membership": "ADMIN"}
    catalogue = {
        "ok": True,
        "read_state": "VERIFIED",
        "status": "NO_LINKS_RECORDED",
        "latest": [],
        "recent_runs": [],
        "stored_media_total": 0,
        "stored_linked_matches": 0,
        "rights_warnings": 0,
        "sampled_media": 0,
        "sample_truncated": False,
    }
    pending_calls = []
    rendered = {}

    def forbidden_dashboard(*_args, **_kwargs):
        pytest.fail("Admin highlights should not load the full sports dashboard")

    def read_catalogue(*, limit):
        assert limit == 30
        return catalogue

    def read_pending(*, days_back, limit):
        pending_calls.append((days_back, limit))
        return {"ok": True, "read_state": "VERIFIED", "matches": []}

    def render(template, **context):
        rendered["template"] = template
        rendered.update(context)
        return "rendered admin highlights"

    monkeypatch.setattr(app_module, "is_admin_session", lambda: True)
    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(app_module, "dashboard_data", forbidden_dashboard)
    monkeypatch.setattr(app_module, "v766_highlights_context", read_catalogue)
    monkeypatch.setattr(app_module, "v769_pending_highlight_snapshot", read_pending)
    monkeypatch.setattr(app_module, "render_template", render)

    response = app_module.app.test_client().get(path)

    assert response.status_code == 200
    assert pending_calls == [(10, 36)]
    if expected_kind == "html":
        assert response.get_data(as_text=True) == "rendered admin highlights"
        assert rendered["template"] == "admin_highlights_center.html"
        data = rendered["data"]
        assert data["session_user"] is user
        assert data["v766_highlights"] is catalogue
        assert data["v769_highlights_center"]["read_ok"] is True
        assert data["v769_highlights_center"]["counts"]["pending"] == 0
    else:
        payload = response.get_json()
        assert payload["ok"] is True
        assert payload["version"] == app_module.APP_VERSION
        assert payload["content_center"]["read_ok"] is True
        assert payload["content_center"]["counts"]["stored"] == 0


def test_admin_highlights_lean_read_keeps_admin_access_guard(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "is_admin_session", lambda: False)
    monkeypatch.setattr(
        app_module,
        "v766_highlights_context",
        lambda **_kwargs: pytest.fail("Unauthenticated request must not read catalogue"),
    )

    client = app_module.app.test_client()
    page = client.get("/admin/highlights-center")
    status = client.get("/api/admin/highlights/status")

    assert page.status_code == 302
    assert "/admin-login" in page.headers["Location"]
    assert status.status_code == 403


def test_admin_highlights_template_renders_from_its_bounded_context(app_module, monkeypatch):
    user = {"id": "admin-v958-render", "role": "ADMIN", "membership": "ADMIN"}
    catalogue = {
        "ok": True,
        "read_state": "VERIFIED",
        "status": "NO_LINKS_RECORDED",
        "latest": [],
        "recent_runs": [],
        "stored_media_total": 0,
        "stored_linked_matches": 0,
        "rights_warnings": 0,
        "sampled_media": 0,
        "sample_truncated": False,
    }

    monkeypatch.setattr(app_module, "is_admin_session", lambda: True)
    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(
        app_module,
        "dashboard_data",
        lambda *_args, **_kwargs: pytest.fail("Full dashboard must stay out of this page"),
    )
    monkeypatch.setattr(app_module, "v766_highlights_context", lambda **_kwargs: catalogue)
    monkeypatch.setattr(
        app_module,
        "v769_pending_highlight_snapshot",
        lambda **_kwargs: {"ok": True, "read_state": "VERIFIED", "matches": []},
    )

    response = app_module.app.test_client().get("/admin/highlights-center")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Centro de resúmenes" in html
    assert "Registros guardados:" in html
    assert "Lectura verificada" in html
    assert "Sin pendientes detectados en la muestra." in html
