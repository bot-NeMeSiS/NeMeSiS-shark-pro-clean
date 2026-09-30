"""Performance contract for /sports-hub, /sports and /today."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _route_source():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index("def sports_hub_page():")
    end = source.index('\n@app.route("/live")', start)
    return source[start:end]


def test_sports_hub_uses_compact_dashboard_context():
    route = _route_source()
    assert "v932_safe_dashboard_data(request.path, compact=True)" in route
    assert "\n    data = dashboard_data(" not in route
    assert "\n    return dashboard_data(" not in route


def test_sports_hub_does_not_call_external_providers():
    route = _route_source()
    for marker in (
        "sync_",
        "fetch_odds_events",
        "sportsdb_v1",
        "fetch_json_url",
        "fetch_json_response",
        "urllib.request",
    ):
        assert marker not in route


def test_sports_hub_reuses_snapshot_for_time_lanes():
    route = _route_source()
    assert 'summary.get("all_valid_matches")' in route
    assert 'summary.get("valid_upcoming_matches")' in route
    assert 'str(item.get("match_date") or "") == tomorrow' in route
    assert '"status": "sports_hub_fast_path"' in route


def test_sports_hub_template_only_needs_focused_payload():
    template = (ROOT / "templates" / "sports_hub.html").read_text(encoding="utf-8")
    assert "data.get('sports_hub')" in template
    for marker in (
        "data.get('client_activity')",
        "data.get('daily_briefing')",
        "data.get('telegram')",
        "data.get('data_center')",
        "data.get('odds')",
    ):
        assert marker not in template
