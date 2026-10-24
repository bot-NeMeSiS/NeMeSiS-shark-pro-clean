"""Fast-path contract for the private client activity screen."""
from pathlib import Path

import pytest


@pytest.mark.parametrize("cursor", [None, "qa-next-cursor"])
def test_activity_route_never_builds_full_dashboard(app_module, monkeypatch, cursor):
    user = {"id": "qa-user", "membership": "PRO", "role": "PRO"}
    calls = {"dashboard": 0, "activity": 0}

    monkeypatch.setattr(app_module, "current_session_user", lambda: user)

    def forbidden_dashboard(*_args, **_kwargs):
        calls["dashboard"] += 1
        raise AssertionError("/actividad must not build dashboard_data")

    items = [{"id": "a1", "label": "Favorito actualizado.", "created_at": "2026-09-29T13:00:00+02:00"}]
    snapshot = {"state": "available", "items": items, "total": 23, "returned_count": 1, "next_cursor": "older"}
    def fake_snapshot(*, user_id, limit=7, cursor=None):
        calls["activity"] += 1
        assert limit == 20
        assert user_id == "qa-user"
        assert cursor == expected_cursor
        return snapshot

    expected_cursor = cursor
    monkeypatch.setattr(app_module, "dashboard_data", forbidden_dashboard)
    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", forbidden_dashboard)
    monkeypatch.setattr(app_module, "get_public_home_sports_summary", forbidden_dashboard)
    monkeypatch.setattr(app_module, "client_activity_feed", forbidden_dashboard)
    monkeypatch.setattr(app_module, "client_account_activity_snapshot", fake_snapshot)
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))

    path = "/actividad" + ("?cursor=" + cursor if cursor else "")
    with app_module.app.test_request_context(path):
        name, ctx = app_module.activity_page()

    assert name == "activity.html"
    assert ctx["data"]["session_user"]["id"] == "qa-user"
    assert ctx["data"]["client_activity"][0]["id"] == "a1"
    assert ctx["data"]["client_activity"] is items
    assert ctx["data"]["activity_snapshot"] is snapshot
    assert calls == {"dashboard": 0, "activity": 1}


def test_activity_route_redirects_without_session(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "current_session_user", lambda: None)
    def forbidden_snapshot(**_kwargs):
        raise AssertionError("Unauthenticated activity must not read account rows")
    monkeypatch.setattr(app_module, "client_account_activity_snapshot", forbidden_snapshot)
    with app_module.app.test_request_context("/actividad"):
        response = app_module.activity_page()
    assert response.status_code == 302
    assert response.location.endswith("/cliente-login")


def test_activity_template_only_consumes_activity_payload():
    root = Path(__file__).resolve().parents[1]
    source = (root / "templates" / "activity.html").read_text(encoding="utf-8")
    assert "data.get('activity_snapshot')" in source
    assert "account_activity_list(activity_snapshot" in source
    assert "activity_snapshot.get('next_cursor')" in source
    assert "url_for('activity_page', cursor=" in source
    source += (root / "templates" / "components" / "account_activity.html").read_text(encoding="utf-8")
    for forbidden in (
        "data.matches",
        "data.upcoming_matches",
        "data.picks",
        "data.combis",
        "data.favorite_feed",
        "data.match_hub",
        "data.daily_briefing",
        "data.client_alerts",
        "data.data_center",
    ):
        assert forbidden not in source


def test_activity_source_uses_dedicated_reader_not_dashboard():
    root = Path(__file__).resolve().parents[1]
    source = (root / "app.py").read_text(encoding="utf-8")
    start = source.index("def activity_page():")
    end = source.index('\n\n\n@app.route("/mi-dia")', start)
    route = source[start:end]
    assert "client_account_activity_snapshot(" in route
    assert "limit=20" in route
    assert 'cursor=request.args.get("cursor")' in route
    assert "client_activity_feed(" not in route
    assert '"activity_snapshot": snapshot' in route
    assert '"client_activity": snapshot["items"]' in route
    assert "dashboard_data(" not in route
    assert '"client_activity"' in route
