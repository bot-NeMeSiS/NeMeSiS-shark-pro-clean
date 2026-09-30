"""Regression coverage for the bounded Home fast-path."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _between(start_marker, end_marker):
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def test_home_route_does_not_build_dead_presentation_contexts():
    route = _between(
        "def v757_client_app_center_page():",
        '@app.route("/api/client/app-center")',
    )
    assert "v932_safe_dashboard_data(request.path, compact=True)" in route
    for marker in (
        "v742_track_record_context",
        "build_client_app_premium_context",
        "build_v757_app_center",
        "build_v757_trust_snapshot",
        "v758_adaptive_context",
        "v777_client_product_context",
        "v778_client_product_organization_context",
        "get_v934_realtime_context",
        "get_v935_customer_trust_context",
    ):
        assert marker not in route
    for marker in (
        "v566_membership_ui",
        "_v931_provider_context",
        "get_safe_picks_context",
        "get_safe_odds_context",
    ):
        assert marker in route


def test_home_template_does_not_reference_removed_contexts():
    template = (ROOT / "templates" / "client_app_center.html").read_text(encoding="utf-8")
    for marker in (
        "track_record",
        "client_premium",
        "v757_app",
        "v757_trust",
        "v758_adaptive",
        "v777_product",
        "v778_organization",
        "v934_realtime",
        "v935_customer_trust",
    ):
        assert marker not in template


def test_home_runtime_skips_dead_builders(app_module, monkeypatch):
    user = {"id": "qa-fast-home", "membership": "FREE", "role": "FREE"}

    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(
        app_module,
        "v932_safe_dashboard_data",
        lambda *_a, **_kw: (
            {"picks": [], "matches": [], "upcoming_matches": [], "match_hub": {}},
            {"provider_status": "ok", "valid_active_picks": []},
        ),
    )
    monkeypatch.setattr(app_module, "v566_membership_ui", lambda _user: {"name": "FREE"})
    monkeypatch.setattr(app_module, "_v931_provider_context", lambda _summary: {"provider_status": "ok"})
    monkeypatch.setattr(app_module, "get_safe_picks_context", lambda picks: {"picks": list(picks)})
    monkeypatch.setattr(app_module, "get_safe_odds_context", lambda picks: {"picks": list(picks)})
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))

    for name in (
        "v742_track_record_context",
        "build_client_app_premium_context",
        "build_v757_app_center",
        "build_v757_trust_snapshot",
        "v758_adaptive_context",
        "v777_client_product_context",
        "v778_client_product_organization_context",
        "get_v934_realtime_context",
        "get_v935_customer_trust_context",
    ):
        monkeypatch.setattr(
            app_module,
            name,
            lambda *_a, _name=name, **_kw: (_ for _ in ()).throw(
                AssertionError(f"dead builder called: {_name}")
            ),
            raising=False,
        )

    with app_module.app.test_request_context("/app"):
        name, ctx = app_module.v757_client_app_center_page()

    assert name == "client_app_center.html"
    data = ctx["data"]
    assert data["membership"]["name"] == "FREE"
    assert data["v925_calendar"]["provider_status"] == "ok"
    assert "v925_picks" in data
    for key in (
        "track_record",
        "client_premium",
        "v757_app",
        "v757_trust",
        "v758_adaptive",
        "v777_product",
        "v778_organization",
        "v934_realtime",
        "v935_customer_trust",
    ):
        assert key not in data
