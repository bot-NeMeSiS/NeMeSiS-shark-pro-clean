"""Performance contract for the FIRST 10 onboarding read path."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _route_source():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index("def onboarding_page():")
    end = source.index('\n@app.route("/mi-cuenta")', start)
    return source[start:end]


def test_onboarding_does_not_build_dashboard_context():
    route = _route_source()
    assert "dashboard_data(" not in route
    assert "v932_safe_dashboard_data(" not in route
    assert 'data = {"onboarding": onboarding_status(user)}' in route


def test_onboarding_preserves_login_gate():
    route = _route_source()
    assert "current_session_user()" in route
    assert 'redirect("/cliente-login")' in route


def test_onboarding_template_only_uses_onboarding_payload():
    template = (ROOT / "templates" / "onboarding.html").read_text(encoding="utf-8")
    assert "data.onboarding" in template
    assert "data.get(" not in template
    for marker in ("sports_metrics", "match_hub", "picks", "odds", "favorites"):
        assert marker not in template


def test_base_template_does_not_require_page_data_object():
    template = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    # "data" exists only as a local JavaScript response variable in the base.
    assert "{{ data" not in template
    assert "{% if data" not in template
