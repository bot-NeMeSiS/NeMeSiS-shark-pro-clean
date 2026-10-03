"""Admin activation and isolated HTTP boundaries; no real users or provider calls."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_media_review_is_mounted_by_existing_admin_composition():
    source = (ROOT / "blueprints" / "architecture.py").read_text(encoding="utf-8")
    assert "create_media_review_blueprint" in source
    assert "bp.register_blueprint(create_media_review_blueprint(db_path, _admin_required))" in source


def test_highlights_review_routes_are_registered_and_protected(app_module, client):
    routes = {rule.rule for rule in app_module.app.url_map.iter_rules()}
    assert "/admin/highlights-review" in routes
    assert "/api/admin/highlights/readiness" in routes
    assert "/admin/highlights-review/<highlight_id>/decision" in routes
    assert "/admin/highlights-review/sync" in routes
    page = client.get("/admin/highlights-review")
    api = client.get("/api/admin/highlights/readiness")
    assert page.status_code == 403
    assert api.status_code == 403
    assert page.get_json()["error"] == "admin_required"
    assert api.get_json()["error"] == "admin_required"


def test_existing_admin_highlights_center_links_to_rights_review():
    template = (ROOT / "templates" / "admin_highlights_center.html").read_text(encoding="utf-8")
    assert 'href="/admin/highlights-review"' in template
    assert "Revisar derechos" in template


def test_activation_does_not_mount_client_player_or_telegram_delivery():
    source = (ROOT / "blueprints" / "architecture.py").read_text(encoding="utf-8")
    assert "highlight_player" not in source
    assert "telegram" not in (ROOT / "blueprints" / "media_review.py").read_text(encoding="utf-8").lower().replace(
        "never changes rights or sends telegram", ""
    )


@pytest.fixture()
def isolated_review(tmp_path, monkeypatch):
    """Real blueprint and readers with isolated sessions and a minimal base layout.

    These cases do not certify full-app authentication, dates or visual layout.
    Provider synchronization and rights writes must not run accidentally.
    """
    from flask import Flask, session
    from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader
    from blueprints import media_review
    from engines import sportsdb_highlights_engine

    app = Flask("isolated_highlights_review")
    app.config.update(TESTING=True, SECRET_KEY="synthetic-review-http-test-secret")
    app.jinja_loader = ChoiceLoader([
        DictLoader({"base.html": "{% block content %}{% endblock %}"}),
        FileSystemLoader(str(ROOT / "templates")),
    ])
    csrf = "synthetic-csrf-for-review"
    app.jinja_env.globals["csrf_token"] = lambda: csrf
    app.jinja_env.filters["madrid_datetime_label"] = str
    database = tmp_path / "not-created.sqlite"
    app.register_blueprint(media_review.create_media_review_blueprint(
        str(database), lambda: session.get("admin_id") == "qa-admin"
    ))

    def forbidden(*args, **kwargs):
        raise AssertionError("No provider call or rights write is authorized by this test")

    monkeypatch.setattr(media_review, "decide_highlight", forbidden)
    monkeypatch.setattr(sportsdb_highlights_engine, "sync_sportsdb_highlights", forbidden)
    client = app.test_client()
    with client.session_transaction() as state:
        state["admin_id"] = "qa-admin"
        state["csrf_token"] = csrf
    return client, database, csrf


def _assert_private(response):
    assert response.headers["Cache-Control"] == "private, no-store"
    assert "Cookie" in response.vary


@pytest.mark.parametrize("url", [
    "/admin/highlights-review/qa-id/decision",
    "/admin/highlights-review/sync",
    "/admin/highlights-review/policies/1/revoke",
])
@pytest.mark.parametrize("token", [None, "", "wrong-token", "ñ-token", "🔒"])
def test_admin_post_rejects_malformed_csrf_without_server_error(isolated_review, url, token):
    client, database, _csrf = isolated_review
    data = {} if token is None else {"csrf_token": token}
    response = client.post(url, data=data)
    assert response.status_code == 403
    assert response.get_json() == {"ok": False, "error": "csrf_failed"}
    _assert_private(response)
    assert not database.exists()


@pytest.mark.parametrize("method,url", [
    ("GET", "/admin/highlights-review"),
    ("GET", "/api/admin/highlights/readiness"),
    ("POST", "/admin/highlights-review/qa-id/decision"),
    ("POST", "/admin/highlights-review/sync"),
    ("POST", "/admin/highlights-review/policies/1/revoke"),
])
def test_all_review_surfaces_reject_non_admin_even_with_valid_csrf(isolated_review, method, url):
    client, database, csrf = isolated_review
    with client.session_transaction() as state:
        state.pop("admin_id")
    response = client.open(url, method=method, data={"csrf_token": csrf})
    assert response.status_code == 403
    assert response.get_json() == {"ok": False, "error": "admin_required"}
    _assert_private(response)
    assert not database.exists()


@pytest.mark.parametrize("url,status", [
    ("/admin/highlights-review", 200),
    ("/api/admin/highlights/readiness", 503),
])
def test_admin_read_does_not_create_absent_catalogue(isolated_review, url, status):
    client, database, _csrf = isolated_review
    response = client.get(url)
    assert response.status_code == status
    _assert_private(response)
    body = response.get_data(as_text=True)
    assert str(database) not in body
    assert not database.exists()
    if response.is_json:
        assert response.get_json()["ok"] is False
    else:
        assert "Revisión de vídeo-resúmenes" in body
        assert "Recuento no verificable" in body


def test_valid_csrf_preserves_explicit_review_action(isolated_review, monkeypatch):
    from blueprints import media_review

    client, database, csrf = isolated_review
    calls = []

    def record(db_path, highlight_id, values, *, actor):
        calls.append((db_path, highlight_id, dict(values), actor))
        return {"ok": True}

    monkeypatch.setattr(media_review, "decide_highlight", record)
    response = client.post("/admin/highlights-review/qa-id/decision", data={
        "csrf_token": csrf, "decision": "REVIEW_REQUIRED", "review_token": "synthetic-review-token",
    })
    assert response.status_code == 303
    assert response.headers["Location"] == "/admin/highlights-review"
    _assert_private(response)
    assert len(calls) == 1
    assert calls[0][0] == str(database)
    assert calls[0][1] == "qa-id"
    assert calls[0][2]["decision"] == "REVIEW_REQUIRED"
    assert calls[0][3] == "qa-admin"
    assert not database.exists()
