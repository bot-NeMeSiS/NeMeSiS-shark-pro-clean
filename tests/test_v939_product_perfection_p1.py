from __future__ import annotations

import re
from pathlib import Path

from engines.company_intelligence_engine import collect_sports_signals
from engines.sentinel_autopilot_engine import (
    _independent_sports_query_issues,
    _rendered_sports_contract_issues,
    create_autopilot_task,
    _scan_routes,
)


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DEFINITION_FIELDS = {
    "functional_definition",
    "origin",
    "filters",
    "time_window",
    "authorized_consumers",
    "refresh_seconds",
    "limitations",
    "edge_cases",
}
CANONICAL_KEYS = {
    "picks_ready",
    "matches_today",
    "matches_available",
    "live_confirmed",
    "matches_with_picks",
    "incomplete_excluded",
    "stale_live_excluded",
    "finished_verified",
    "matches_synchronized",
}


def _match(app_module, match_id: str, *, lifecycle: str = "UPCOMING", score: bool = False):
    item = {
        "id": match_id,
        "match_id": match_id,
        "match_date": app_module.today_iso(),
        "home_team": f"Local {match_id}",
        "away_team": f"Visitante {match_id}",
        "competition_name": "Competicion real",
        "kickoff_time": "20:00",
        "source": "fixture-test",
        "updated_at": app_module.now_iso(),
        "last_synced_at": app_module.now_iso(),
        "v935_lifecycle": lifecycle,
    }
    if score:
        item.update({"home_score": 2, "away_score": 1})
    return item


def _summary(app_module):
    today = _match(app_module, "m-today")
    live = _match(app_module, "m-live", lifecycle="LIVE")
    upcoming = _match(app_module, "m-next")
    finished = _match(app_module, "m-finished", lifecycle="FINISHED", score=True)
    return {
        "valid_matches_today": [today, live, finished],
        "valid_upcoming_matches": [today, upcoming],
        "valid_matches_available": [today, live, finished, upcoming],
        "valid_live_events": [live],
        "valid_active_picks": [
            {"id": "p-1", "match_id": "m-today"},
            {"id": "p-2", "match_id": "m-today"},
            {"id": "p-3", "match_id": "m-next"},
        ],
        "finished_matches": [finished, _match(app_module, "m-no-score", lifecycle="FINISHED")],
        "incomplete_matches": [{"id": "incomplete"}],
        "raw_matches_count": 7,
        "stale_live_excluded": 2,
        "last_sync": "2026-07-22T12:00:00+02:00",
        "metrics_generated_at_madrid": "2026-07-22T12:00:15+02:00",
    }


def test_sports_data_contract_has_one_definition_and_deterministic_snapshot(app_module):
    summary = _summary(app_module)
    first = app_module.build_sports_metrics_contract(summary)
    summary["sports_metrics"] = first
    second = app_module.get_sports_metrics_contract(summary)

    assert first is second
    assert first["contract"] == "sports-metrics-v1"
    assert first["matches_today"] == 3
    assert first["matches_available"] == 4
    assert first["live_confirmed"] == 1
    assert first["picks_ready"] == 3
    assert first["matches_with_picks"] == 2
    assert first["finished_verified"] == 1
    assert first["matches_synchronized"] == 7
    assert first["incomplete_excluded"] == 1
    assert first["stale_live_excluded"] == 2
    assert first["snapshot_id"] == app_module.build_sports_metrics_contract(summary)["snapshot_id"]

    assert CANONICAL_KEYS <= set(first["definitions"])
    for key in CANONICAL_KEYS:
        assert REQUIRED_DEFINITION_FIELDS <= set(first["definitions"][key])


def test_all_runtime_contexts_keep_the_same_snapshot(app_module):
    summary = _summary(app_module)
    summary["sports_metrics"] = app_module.build_sports_metrics_contract(summary)
    expected = summary["sports_metrics"]["snapshot_id"]

    with app_module.app.test_request_context("/calendar"):
        calendar = app_module.v931_calendar_context(summary)
        live = app_module.v931_live_context(summary)
        provider = app_module._v931_provider_context(summary)
        dashboard, _ = app_module.v931_safe_dashboard_data(
            "/calendar", compact=True, sports_summary=summary
        )

    contexts = [
        app_module._v931_legacy_home_summary(summary),
        calendar,
        live,
        provider,
        dashboard,
    ]
    assert all(context["sports_metrics"]["snapshot_id"] == expected for context in contexts)
    assert calendar["counts"]["today"] == summary["sports_metrics"]["matches_today"]
    assert live["counts"]["live"] == summary["sports_metrics"]["live_confirmed"]
    assert provider["counts"]["picks"] == summary["sports_metrics"]["matches_with_picks"]


def test_company_intelligence_never_recalculates_without_contract(app_module):
    metrics = app_module.build_sports_metrics_contract(_summary(app_module))
    canonical = collect_sports_signals("ignored.sqlite", app_module.APP_VERSION, sports_metrics=metrics)[0]
    missing = collect_sports_signals("ignored.sqlite", app_module.APP_VERSION)[0]

    assert canonical["source"] == "sports-metrics-v1"
    assert canonical["evidence"]["sports_metrics"]["snapshot_id"] == metrics["snapshot_id"]
    assert missing["certification_state"] == "NOT_CERTIFIED"
    assert missing["evidence"]["contract_received"] is False
    assert "records_total" not in missing["evidence"]


def test_public_sports_surfaces_render_the_same_contract(client):
    observed = {}
    for route in ["/", "/calendar", "/live", "/picks", "/shark"]:
        response = client.get(route)
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        match = re.search(r'data-sports-snapshot="([^"]+)"', html)
        assert match, f"Falta snapshot en {route}"
        assert 'data-sports-contract="sports-metrics-v1"' in html
        assert html.count('data-v934-match-card="true"') == html.count(
            'data-v939-match-card-spec="canonical-v1"'
        )
        observed[route] = match.group(1)
    assert len(set(observed.values())) == 1, observed


def test_autopilot_opens_p1_for_contract_or_card_divergence(app_module):
    expected = app_module.build_sports_metrics_contract(_summary(app_module))
    bad_html = (
        '<div data-sports-contract="sports-metrics-v1" data-sports-snapshot="wrong" '
        'data-sports-matches-today="99" data-sports-matches-available="99" '
        'data-sports-live-confirmed="0" data-sports-picks-ready="0" '
        'data-sports-matches-with-picks="0" data-sports-finished-verified="0" '
        'data-sports-matches-synchronized="0">'
        '<article data-v934-match-card="true"></article></div>'
    )
    issues = _rendered_sports_contract_issues("/", 200, bad_html, expected, app_module.APP_VERSION)

    assert issues
    assert all(issue["category"] == "sports_data_contract" for issue in issues)
    assert all(issue["severity"] == "high" for issue in issues)
    tasks = [create_autopilot_task(issue) for issue in issues]
    assert all(task["safe_fix_plan"]["requires_approval"] is True for task in tasks)


def test_autopilot_route_scan_executes_contract_guard(app_module):
    expected = app_module.build_sports_metrics_contract(_summary(app_module))
    bad_html = (
        '<main data-sports-contract="sports-metrics-v1" data-sports-snapshot="wrong" '
        'data-sports-matches-today="99" data-sports-matches-available="99" '
        'data-sports-live-confirmed="0" data-sports-picks-ready="0" '
        'data-sports-matches-with-picks="0" data-sports-finished-verified="0" '
        'data-sports-matches-synchronized="0">Sin datos reales disponibles</main>'
    )

    class Response:
        status_code = 200

        @staticmethod
        def get_data(as_text=False):
            return bad_html

    class Client:
        @staticmethod
        def get(route):
            return Response()

    assert _scan_routes(None, app_module.APP_VERSION, expected) == []
    issues = _scan_routes(Client(), app_module.APP_VERSION, expected)
    assert any(issue["category"] == "sports_data_contract" for issue in issues)


def test_autopilot_source_guard_finds_no_private_metric_queries(app_module):
    assert _independent_sports_query_issues(ROOT, app_module.APP_VERSION) == []


def test_match_card_component_and_css_are_canonical():
    component = (ROOT / "templates" / "components" / "v933_ui.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "v933-product.css").read_text(encoding="utf-8")

    assert component.count("{% macro match_card(") == 1
    assert 'data-v939-match-card-spec="canonical-v1"' in component
    assert 'class="v933-match-card-header"' in component
    assert 'class="v933-match-card-footer"' in component
    assert 'class="v933-match-card-actions"' in component
    assert ".v933-two-col .v933-match-grid" in css
    assert ".v933-match-card-footer" in css
    assert "overflow-wrap: anywhere" not in re.search(
        r"\.v933-match-teams strong\s*\{[^}]+\}", css
    ).group(0)

