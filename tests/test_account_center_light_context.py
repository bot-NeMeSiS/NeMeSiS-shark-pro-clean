"""Performance contract for /mi-cuenta."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _route_source():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index("def account_center_page():")
    end = source.index('\n\n@app.route("/admin/memberships")', start)
    return source[start:end]


def test_account_center_does_not_build_full_dashboard():
    route = _route_source()
    assert "dashboard_data(" not in route
    assert "v932_safe_dashboard_data(" not in route


def test_account_center_loads_only_visible_personal_context():
    route = _route_source()
    for marker in (
        "get_favorites(user_id=user_id)",
        "client_activity_feed(limit=8, user_id=user_id)",
        "build_client_alerts(limit=8, user_id=user_id)",
        "v566_membership_ui(user)",
        "client_payments_context(DB_PATH, user)",
        "telegram_user_state(user)",
    ):
        assert marker in route


def test_account_center_drops_unused_context_builders():
    route = _route_source()
    for marker in (
        "onboarding_status(",
        "v778_client_product_organization_context(",
        "get_results_matches(",
        "pick_candidate_matches(",
        "smart_pick_board(",
        "favorite_feed_full(",
        "match_calendar_diagnostics(",
        "data_center_summary(",
        "crest_sync_status(",
        "sportsdb_feed_status(",
        "odds_diagnostics(",
    ):
        assert marker not in route


def test_account_center_preserves_rendered_counts_from_loaded_lists():
    route = _route_source()
    assert '"favorites": len(favorites)' in route
    assert '"alerts": len(client_alerts)' in route
    assert '"activity": len(activity)' in route


def test_account_template_contract_matches_light_payload():
    template = (ROOT / "templates" / "account_center.html").read_text(encoding="utf-8")
    for marker in (
        "account = data.account_center",
        "data.get('membership')",
        "data.payments_client",
        "data.get('session_user')",
        "data.get('client_activity')",
        "data.get('telegram_state')",
    ):
        assert marker in template
    for marker in (
        "data.get('onboarding')",
        "data.get('v778_organization')",
        "data.get('match_hub')",
        "data.get('smart_picks')",
        "data.get('data_center')",
    ):
        assert marker not in template
