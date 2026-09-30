"""Performance contract for /favoritos and /favorites."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _route_source():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index("def favorites_page():")
    end = source.index("# ===================== V785 MEMBERSHIP / STRIPE FLOW POLISH", start)
    return source[start:end]


def test_favorites_does_not_build_full_dashboard_context():
    route = _route_source()
    assert "dashboard_data(" not in route
    assert "v932_safe_dashboard_data(" not in route
    assert "get_public_home_sports_summary(" not in route


def test_favorites_loads_only_template_contract():
    route = _route_source()
    assert "get_favorites(user_id=user_id)" in route
    assert "favorite_feed_full(user_id=user_id)" in route
    assert "favorite_insights(" in route
    assert '"status": "favorites_fast_path"' in route


def test_favorites_fast_path_has_no_provider_or_commercial_side_effects():
    route = _route_source()
    for marker in (
        "sync_",
        "fetch_odds_events",
        "sportsdb_v1",
        "client_payments_context",
        "telegram_send",
        "stripe",
        "data_center_summary",
        "odds_diagnostics",
    ):
        assert marker not in route


def test_favorites_template_contract_matches_fast_path_payload():
    template = (ROOT / "templates" / "favorites.html").read_text(encoding="utf-8")
    for marker in (
        "data.favorite_insights",
        "data.favorite_feed",
        "data.favorite_bundle",
        "data.favorites",
    ):
        assert marker in template
