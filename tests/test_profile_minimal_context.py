"""Performance contract for /perfil and /profile."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _route_source():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index("def profile_page():")
    end = source.index('\n@app.route("/alertas")', start)
    return source[start:end]


def test_profile_does_not_build_dashboard_or_sports_context():
    route = _route_source()
    assert "dashboard_data(" not in route
    assert "v932_safe_dashboard_data(" not in route
    assert "get_public_home_sports_summary(" not in route


def test_profile_loads_only_personal_lists_rendered_by_template():
    route = _route_source()
    assert 'data = {"session_user": user}' in route
    assert "get_favorites(user_id=user_id)" in route
    assert "client_activity_feed(limit=8, user_id=user_id)" in route
    assert "telegram_user_state(user)" in route


def test_profile_does_not_build_unused_heavy_contexts():
    route = _route_source()
    for marker in (
        "crest_sync_status",
        "shark_briefing",
        "_v931_provider_context",
        "get_safe_picks_context",
        "get_v935_customer_trust_context",
        "v566_membership_ui",
    ):
        assert marker not in route


def test_profile_template_contract_matches_minimal_route_payload():
    template = (ROOT / "templates" / "profile.html").read_text(encoding="utf-8")
    for marker in (
        "data.get('session_user')",
        "data.get('telegram_state')",
        "data.get('client_activity')",
        "data.get('favorites')",
    ):
        assert marker in template
    for marker in (
        "data.get('sportsdb')",
        "data.get('briefing')",
        "data.get('v925_calendar')",
        "data.get('v925_picks')",
        "data.get('v935_customer_trust')",
        "data.get('membership')",
    ):
        assert marker not in template
