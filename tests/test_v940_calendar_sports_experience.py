from __future__ import annotations

import shutil
import urllib.parse
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from engines.company_intelligence_engine import build_company_intelligence_snapshot
from engines.sentinel_autopilot_engine import (
    build_v940_calendar_experience_contract_snapshot,
    create_autopilot_task,
    detect_product_quality_contract_issues,
    run_autopilot_scan,
)


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL"


def _match(app_module, index: int) -> dict:
    offset = index % 7
    return {
        "id": f"v940-match-{index}",
        "match_id": f"v940-match-{index}",
        "match_date": app_module.today_iso(offset),
        "home_team": f"Local {index}",
        "away_team": f"Visitante {index}",
        "competition_name": f"Liga {index % 8}",
        "country": "Espana" if index % 2 == 0 else "Global",
        "kickoff_time": f"{12 + index % 10:02d}:{(index * 5) % 60:02d}",
        "source": "fixture-test",
        "v935_lifecycle": "UPCOMING",
    }


def _summary(app_module, total: int) -> dict:
    matches = [_match(app_module, index) for index in range(total)]
    today = [item for item in matches if item["match_date"] == app_module.today_iso()]
    picks = [
        {
            "id": f"v940-pick-{index}",
            "match_id": item["id"],
            "market": "1X2",
            "selection": "Local",
            "odds": 1.80,
        }
        for index, item in enumerate(matches)
        if index % 3 == 0
    ]
    return {
        "all_valid_matches": matches,
        "valid_upcoming_matches": matches,
        "valid_matches_available": matches,
        "valid_matches_today": today,
        "valid_live_events": [],
        "valid_active_picks": picks,
        "finished_matches": [],
        "incident_matches": [],
        "incomplete_matches": [],
        "raw_matches_count": total,
        "stale_live_excluded": 0,
        "safe_message": "Agenda de prueba local.",
    }


def _fixture_root(tmp_path: Path, *, break_context: bool = False) -> Path:
    paths = (
        "app.py",
        "static/v933-product.css",
        "static/v934-realtime.js",
        "static/v940-calendar.js",
        "templates/components/v933_ui.html",
        "templates/home.html",
        "templates/client_app_center.html",
        "templates/calendar.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/shark.html",
        "templates/match_detail.html",
        "templates/admin_dashboard.html",
        "templates/admin_data_center.html",
        "templates/admin_data_trust_center.html",
        "templates/admin_realtime_center.html",
        "engines/madrid_time_engine.py",
        "engines/v934_realtime_sports_engine.py",
    )
    for relative in paths:
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    if break_context:
        template_path = tmp_path / "templates" / "calendar.html"
        template = template_path.read_text(encoding="utf-8")
        template_path.write_text(
            template.replace("data-v940-calendar-context", "data-v940-context-removed"),
            encoding="utf-8",
        )
    return tmp_path


def test_v940_version_cache_and_runtime_markers_are_aligned():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == VERSION
    assert (ROOT / "APP_VERSION").read_text(encoding="utf-8").strip() == VERSION
    assert f"APP_VERSION = '{VERSION}'" in app_source
    assert "NEMESIS_CACHE_V940" in app_source
    assert "has_v940_nemesis_sports_experience_phase_1_foundation" in app_source
    assert "has_v939_autonomous_company_intelligence_growth_quality_platform" in app_source


def test_v940_calendar_uses_one_contract_for_five_and_five_hundred_matches(app_module):
    for total in (5, 500):
        summary = _summary(app_module, total)
        with app_module.app.test_request_context("/calendar?lane=week"):
            calendar = app_module.v940_calendar_context(
                summary,
                "week",
                app_module.today_iso(),
            )
        assert calendar["contract"] == "v940-calendar-history-layers-v1"
        assert calendar["sports_metrics"]["contract"] == "sports-metrics-v1"
        assert calendar["counts"]["visible"] == total
        assert len(calendar["matches"]) == total
        assert calendar["database_written"] is False
        assert calendar["external_calls"] == 0


def test_v940_direct_search_locates_one_match_in_large_collection(app_module):
    summary = _summary(app_module, 500)
    with app_module.app.test_request_context("/calendar?lane=week&q=Local+437"):
        calendar = app_module.v940_calendar_context(
            summary,
            "week",
            app_module.today_iso(),
        )
    assert calendar["counts"]["visible"] == 1
    assert calendar["matches"][0]["id"] == "v940-match-437"
    assert calendar["active_filters"][0]["key"] == "q"


def test_v940_filter_layers_are_visible_reversible_and_shareable(app_module):
    summary = _summary(app_module, 24)
    query = (
        "/calendar?lane=week&date="
        + app_module.today_iso()
        + "&q=Local&league=Liga+2&country=Espana&sort=league&with_pick=1"
    )
    with app_module.app.test_request_context(query):
        calendar = app_module.v940_calendar_context(
            summary,
            "week",
            app_module.today_iso(),
        )
    active = {item["key"]: item for item in calendar["active_filters"]}
    assert {"q", "league", "country", "sort", "with_pick"} <= set(active)
    query_values = urllib.parse.parse_qs(
        urllib.parse.urlsplit(active["q"]["remove_href"]).query
    )
    assert "q" not in query_values
    assert query_values["league"] == ["Liga 2"]
    assert query_values["country"] == ["Espana"]
    assert query_values["date"] == [app_module.today_iso()]
    assert calendar["reset_href"].startswith("/calendar?")


def test_v940_page_and_api_consume_the_same_snapshot(client, app_module, monkeypatch):
    summary = _summary(app_module, 32)
    metrics = app_module.build_sports_metrics_contract(summary)
    summary["sports_metrics"] = metrics

    def safe_dashboard(*_args, **_kwargs):
        return {"sports_metrics": metrics}, summary

    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", safe_dashboard)
    page = client.get("/calendar", query_string={"lane": "week", "q": "Local 19"})
    api = client.get("/api/calendar", query_string={"lane": "week", "q": "Local 19"})
    payload = api.get_json()

    assert page.status_code == 200
    assert api.status_code == 200
    assert payload["calendar"]["sports_metrics"]["snapshot_id"] == metrics["snapshot_id"]
    assert payload["calendar"]["counts"]["visible"] == 1
    html = page.get_data(as_text=True)
    assert f'data-sports-snapshot="{metrics["snapshot_id"]}"' in html
    assert 'data-v940-calendar-experience="history-layers-v1"' in html
    assert html.count('data-v939-match-card-spec="canonical-v1"') == 1


def test_v940_calendar_aliases_share_the_same_discovery_contract(client, app_module, monkeypatch):
    summary = _summary(app_module, 8)
    metrics = app_module.build_sports_metrics_contract(summary)
    summary["sports_metrics"] = metrics

    def safe_dashboard(*_args, **_kwargs):
        return {"sports_metrics": metrics}, summary

    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", safe_dashboard)
    for route in (
        "/calendar",
        "/calendario",
        "/calendario-global",
        "/partidos",
        "/partidos/calendario",
    ):
        response = client.get(route, query_string={"lane": "week"})
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'data-v940-calendar-experience="history-layers-v1"' in html
        assert f'data-sports-snapshot="{metrics["snapshot_id"]}"' in html

def test_v940_template_is_valid_and_uses_only_the_canonical_match_card():
    template = (ROOT / "templates" / "calendar.html").read_text(encoding="utf-8")
    environment = Environment(loader=FileSystemLoader(str(ROOT / "templates")))
    environment.parse(template)

    assert template.count("{{ match_card(match, false, true) }}") == 1
    assert template.count("v933-match-grid") == 1
    assert "data-v940-calendar-command" in template
    assert "data-v940-calendar-context" in template
    assert "data-v940-calendar-index" in template
    assert "data-v940-calendar-collection" in template


def test_v940_progressive_enhancement_is_local_and_restores_only_history_context():
    javascript = (ROOT / "static" / "v940-calendar.js").read_text(encoding="utf-8")
    assert "window.sessionStorage" in javascript
    assert 'navigationType() !== "back_forward"' in javascript
    assert "IntersectionObserver" in javascript
    assert 'event.key !== "/"' in javascript
    assert "fetch(" not in javascript
    assert "XMLHttpRequest" not in javascript
    assert "sendBeacon(" not in javascript


def test_v940_sentinel_contract_is_green_and_mutation_opens_approval_task(tmp_path):
    healthy = build_v940_calendar_experience_contract_snapshot(ROOT, VERSION)
    assert healthy["validation_result"] == "PASS"
    assert healthy["evidence"]["violations"] == []

    broken_root = _fixture_root(tmp_path, break_context=True)
    broken = build_v940_calendar_experience_contract_snapshot(broken_root, VERSION)
    assert broken["validation_result"] == "REGRESSION"
    assert "template_contract" in broken["evidence"]["violations"]

    issues = detect_product_quality_contract_issues(broken_root, VERSION)
    issue = next(item for item in issues if item["id"] == "V940-CALENDAR-EXPERIENCE-CONTRACT")
    task = create_autopilot_task(issue)
    assert issue["priority"] == "P1"
    assert issue["safe_to_auto_fix"] is False
    assert task["status"] == "pending_approval"
    assert task["safe_fix_plan"]["requires_approval"] is True

    autopilot = run_autopilot_scan(app_version=VERSION, project_root=broken_root)
    assert autopilot["score"] < 10
    assert autopilot["dangerous_actions_executed"] is False


def test_v940_company_intelligence_preserves_calendar_learning(app_module, tmp_path):
    snapshot = build_company_intelligence_snapshot(
        ROOT,
        tmp_path / "read-only-company-intelligence.sqlite",
        app_module.APP_VERSION,
        environment="test",
        sports_metrics=app_module.build_sports_metrics_contract(_summary(app_module, 5)),
    )
    learning = {
        item["issue_id"]: item
        for item in snapshot["product_quality_learning"]
    }["V940-CALENDAR-EXPERIENCE-CONTRACT"]
    assert learning["validation_result"] == "PASS"
    assert learning["production_certified"] is False
    assert learning["autofix_allowed"] is False
    assert snapshot["database_written"] is False
    assert snapshot["external_calls"] == 0

