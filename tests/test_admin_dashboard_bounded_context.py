"""Regression coverage for the bounded Admin Dashboard fast-path."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _between(start_marker, end_marker):
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def test_admin_dashboard_uses_bounded_context_only():
    route = _between(
        "def v566_admin_dashboard_page():",
        '@app.route("/api/admin/control-center")',
    )
    assert 'v932_safe_dashboard_data(request.path, scope="admin", compact=True)' in route
    assert "data = dashboard_data(" not in route
    assert 'data["v934_realtime"] = get_v934_realtime_context(summary)' in route
    assert 'data["admin_master"] = master_snapshot(__import__(__name__))' in route
    for marker in (
        "v928_admin_overview",
        "quality_center_summary",
        "v566_admin_items",
        "fallback_overview",
        "q=quality",
        "items=items",
    ):
        assert marker not in route


def test_admin_template_does_not_need_removed_payloads():
    template = (ROOT / "templates" / "admin_dashboard.html").read_text(encoding="utf-8")
    assert "v928_admin" not in template
    assert "quality_center" not in template
    assert "q." not in template
    assert "q[" not in template


def test_admin_dashboard_runtime_skips_legacy_fanout(app_module, monkeypatch):
    import blueprints.admin_master_control as admin_master_control

    calls = {"safe": 0, "realtime": 0, "master": 0}
    summary = {"provider_status": "ok", "valid_live_events": []}

    monkeypatch.setattr(app_module, "is_admin_session", lambda: True)

    def fake_safe(route, lane="today", date_value=None, scope="client", compact=False, sports_summary=None):
        calls["safe"] += 1
        assert route == "/admin/dashboard"
        assert scope == "admin"
        assert compact is True
        return ({"session_user": {"role": "ADMIN"}}, summary)

    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", fake_safe)
    monkeypatch.setattr(
        app_module,
        "dashboard_data",
        lambda *_a, **_kw: (_ for _ in ()).throw(
            AssertionError("admin dashboard must not build legacy dashboard_data")
        ),
    )

    for name in ("v928_admin_overview", "quality_center_summary", "v566_admin_items"):
        monkeypatch.setattr(
            app_module,
            name,
            lambda *_a, _name=name, **_kw: (_ for _ in ()).throw(
                AssertionError(f"unused admin builder called: {_name}")
            ),
            raising=False,
        )

    def fake_realtime(actual):
        calls["realtime"] += 1
        assert actual is summary
        return {"state": "qa"}

    def fake_master(actual_app):
        calls["master"] += 1
        assert actual_app is app_module
        return {"version": "QA", "facts": [], "areas": []}

    monkeypatch.setattr(app_module, "get_v934_realtime_context", fake_realtime)
    monkeypatch.setattr(admin_master_control, "master_snapshot", fake_master)
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))

    with app_module.app.test_request_context("/admin/dashboard"):
        name, ctx = app_module.v566_admin_dashboard_page()

    assert name == "admin_dashboard.html"
    assert ctx["data"]["v934_realtime"]["state"] == "qa"
    assert ctx["data"]["admin_master"]["version"] == "QA"
    assert "q" not in ctx
    assert "items" not in ctx
    assert calls == {"safe": 1, "realtime": 1, "master": 1}
