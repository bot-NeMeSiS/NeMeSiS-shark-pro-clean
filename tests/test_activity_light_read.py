"""Fast-path contract for the private client activity screen."""
from pathlib import Path


def test_activity_route_never_builds_full_dashboard(app_module, monkeypatch):
    user = {"id": "qa-user", "membership": "PRO", "role": "PRO"}
    calls = {"dashboard": 0, "activity": 0}

    monkeypatch.setattr(app_module, "current_session_user", lambda: user)

    def forbidden_dashboard(*_args, **_kwargs):
        calls["dashboard"] += 1
        raise AssertionError("/actividad must not build dashboard_data")

    def fake_activity(limit=20, user_id=None, include_internal=False):
        calls["activity"] += 1
        assert limit == 20
        assert user_id == "qa-user"
        assert include_internal is False
        return [{"id": "a1", "label": "Favorito actualizado.", "created_at": "2026-09-29T13:00:00+02:00"}]

    monkeypatch.setattr(app_module, "dashboard_data", forbidden_dashboard)
    monkeypatch.setattr(app_module, "client_activity_feed", fake_activity)
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))

    with app_module.app.test_request_context("/actividad"):
        name, ctx = app_module.activity_page()

    assert name == "activity.html"
    assert ctx["data"]["session_user"]["id"] == "qa-user"
    assert ctx["data"]["client_activity"][0]["id"] == "a1"
    assert calls == {"dashboard": 0, "activity": 1}


def test_activity_route_redirects_without_session(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "current_session_user", lambda: None)
    with app_module.app.test_request_context("/actividad"):
        response = app_module.activity_page()
    assert response.status_code == 302
    assert response.location.endswith("/cliente-login")


def test_activity_template_only_consumes_activity_payload():
    root = Path(__file__).resolve().parents[1]
    source = (root / "templates" / "activity.html").read_text(encoding="utf-8")
    assert "data.client_activity" in source
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
    assert "client_activity_feed(limit=20" in route
    assert "dashboard_data(" not in route
    assert '"client_activity"' in route
