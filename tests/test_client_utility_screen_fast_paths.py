"""Regression coverage for lightweight client utility screens."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _between(start_marker, end_marker):
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def test_client_success_does_not_build_dashboard_or_unused_onboarding():
    route = _between("def client_success_page():", '@app.route("/api/client/success")')
    assert "dashboard_data(" not in route
    assert "home_light_data(" not in route
    assert "onboarding_status(" not in route
    assert "client_success_runtime_context(user_ctx)" in route
    template = (ROOT / "templates" / "client_success.html").read_text(encoding="utf-8")
    assert "data.client_success" in template
    assert "data.onboarding" not in template


def test_adaptive_screen_uses_compact_snapshot_only():
    route = _between(
        "def v758_adaptive_experience_page():",
        '@app.route("/api/client/device-experience")',
    )
    assert 'v932_safe_dashboard_data(request.path, scope="client", compact=True)' in route
    assert "= dashboard_data(" not in route
    assert "v742_track_record_context" not in route
    assert "build_client_app_premium_context" not in route
    assert "build_v757_app_center" not in route
    assert 'data["v758_adaptive"] = v758_adaptive_context(data, user, "adaptive")' in route


def test_navigation_map_does_not_build_dashboard():
    route = _between(
        "def v809_client_navigation_map_page():",
        "# V808 route aliases for buttons found in legacy/client/admin templates.",
    )
    assert "dashboard_data(" not in route
    assert "v566_membership_ui" not in route
    assert "v809_client_navigation_items()" in route


def test_client_success_runtime_contract(app_module, monkeypatch):
    user = {"id": "qa-help", "membership": "FREE", "role": "FREE"}
    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(
        app_module,
        "dashboard_data",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("dashboard_data forbidden")),
    )
    monkeypatch.setattr(
        app_module,
        "home_light_data",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("home_light_data forbidden")),
    )
    monkeypatch.setattr(
        app_module,
        "onboarding_status",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("unused onboarding forbidden")),
    )
    monkeypatch.setattr(app_module, "client_success_runtime_context", lambda actual: {"membership": actual["membership"], "score": 100})
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))
    with app_module.app.test_request_context("/ayuda"):
        name, ctx = app_module.client_success_page()
    assert name == "client_success.html"
    assert ctx["data"]["client_success"]["score"] == 100
    assert ctx["data"]["session_user"]["id"] == "qa-help"


def test_adaptive_runtime_contract(app_module, monkeypatch):
    user = {"id": "qa-adaptive", "membership": "PRO", "role": "PRO"}
    calls = {"safe": 0, "adaptive": 0}
    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(
        app_module,
        "dashboard_data",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("full dashboard forbidden")),
    )
    def fake_safe(route, lane="today", date_value=None, scope="client", compact=False, sports_summary=None):
        calls["safe"] += 1
        assert route == "/experiencia"
        assert scope == "client"
        assert compact is True
        return ({"match_hub": {"counts": {"today": 2, "live": 1}}, "picks": [{"id": "p1"}]}, {})
    def fake_adaptive(data, actual_user, page_key):
        calls["adaptive"] += 1
        assert actual_user is user
        assert page_key == "adaptive"
        return {"headline": "QA", "counts": data["match_hub"]["counts"]}
    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", fake_safe)
    monkeypatch.setattr(app_module, "v758_adaptive_context", fake_adaptive)
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))
    with app_module.app.test_request_context("/experiencia"):
        name, ctx = app_module.v758_adaptive_experience_page()
    assert name == "adaptive_experience.html"
    assert ctx["data"]["v758_adaptive"]["counts"]["today"] == 2
    assert calls == {"safe": 1, "adaptive": 1}


def test_navigation_map_runtime_contract(app_module, monkeypatch):
    user = {"id": "qa-map", "membership": "ELITE", "role": "ELITE"}
    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(
        app_module,
        "dashboard_data",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("dashboard_data forbidden")),
    )
    monkeypatch.setattr(app_module, "v809_client_navigation_items", lambda: [{"group": "QA", "title": "Inicio", "href": "/app", "body": "QA", "icon": "I"}])
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))
    with app_module.app.test_request_context("/app/mapa"):
        name, ctx = app_module.v809_client_navigation_map_page()
    assert name == "client_navigation_map.html"
    assert ctx["items"][0]["href"] == "/app"
    assert ctx["data"]["session_user"]["id"] == "qa-map"
