"""Performance contract for /mi-cuenta."""

from pathlib import Path

import pytest

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
        "client_account_activity_snapshot(user_id=user_id, limit=7)",
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


def test_account_center_preserves_personal_list_counts_and_snapshot_total():
    route = _route_source()
    assert '"favorites": len(favorites)' in route
    assert '"alerts": len(client_alerts)' in route
    assert '"activity": activity_snapshot["total"]' in route
    assert '"activity": len(activity)' not in route


def test_account_template_contract_matches_light_payload():
    template = (ROOT / "templates" / "account_center.html").read_text(encoding="utf-8")
    for marker in (
        "account = data.account_center",
        "data.get('membership')",
        "data.payments_client",
        "data.get('session_user')",
        "data.get('client_activity')",
        "data.get('activity_snapshot')",
        "account_activity_list(",
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

@pytest.mark.parametrize(
    "state,total,item_count",
    [("available", 23, 7), ("empty", 0, 0), ("unavailable", None, 0)],
)
def test_account_center_uses_exact_activity_total_without_legacy_fallback(
    app_module, monkeypatch, state, total, item_count,
):
    user = {"id": "qa-counts", "role": "CLIENT", "membership": "FREE"}
    items = [{"id": f"qa-{index}"} for index in range(item_count)]
    snapshot = {
        "state": state, "items": items, "total": total,
        "returned_count": item_count, "next_cursor": None,
    }
    calls = []
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Account preview must not read legacy or sports dashboards")
    def read_snapshot(*, user_id, limit=7, cursor=None):
        calls.append((user_id, limit, cursor))
        return snapshot
    for name in (
        "dashboard_data", "v932_safe_dashboard_data",
        "get_public_home_sports_summary", "client_activity_feed",
    ):
        monkeypatch.setattr(app_module, name, forbidden)
    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(app_module, "get_favorites", lambda **_kw: [{"id": "f1"}, {"id": "f2"}])
    monkeypatch.setattr(app_module, "client_account_activity_snapshot", read_snapshot)
    monkeypatch.setattr(app_module, "build_client_alerts", lambda **_kw: [{"id": "alert"}])
    monkeypatch.setattr(app_module, "v566_membership_ui", lambda _user: {})
    monkeypatch.setattr(app_module, "client_payments_context", lambda *_args: {})
    monkeypatch.setattr(app_module, "telegram_user_state", lambda _user: {"linked": False})
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))
    with app_module.app.test_request_context("/mi-cuenta"):
        name, context = app_module.account_center_page()
    assert name == "account_center.html"
    assert context["data"]["activity_snapshot"] is snapshot
    assert context["data"]["client_activity"] is items
    assert context["data"]["account_center"]["favorites"] == 2
    assert context["data"]["account_center"]["alerts"] == 1
    assert context["data"]["account_center"]["activity"] == total
    assert calls == [("qa-counts", 7, None)]
