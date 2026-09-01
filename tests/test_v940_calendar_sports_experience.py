from __future__ import annotations

import shutil
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from engines.company_intelligence_engine import build_company_intelligence_snapshot
from engines.live_engine import normalize_live_state
from engines.live_experience_engine import enrich_live_match
from engines.live_match_experience_engine import build_live_card_payload
from engines.match_context_engine import build_match_context
from engines.sentinel_autopilot_engine import (
    build_v940_calendar_experience_contract_snapshot,
    create_autopilot_task,
    detect_product_quality_contract_issues,
    run_autopilot_scan,
)
from engines.v934_realtime_sports_engine import build_realtime_snapshot
from engines.v935_launch_trust_engine import enrich_match_lifecycle, match_status_truth


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



def _sports_relevance_match(app_module, match_id, competition, *, date_offset=1, kickoff="20:00", status="NS", home="Equipo Local", away="Equipo Visitante", **extra):
    item = {
        "id": match_id,
        "match_id": match_id,
        "match_date": app_module.today_iso(date_offset),
        "kickoff_time": kickoff,
        "home_team": home,
        "away_team": away,
        "competition_name": competition,
        "country": extra.pop("country", "Global"),
        "source": extra.pop("source", "provider-test"),
        "status": status,
        "updated_at": extra.pop("updated_at", app_module.now_iso()),
        "v935_lifecycle": extra.pop("v935_lifecycle", "UPCOMING"),
        "v935_surface": extra.pop("v935_surface", {"home": True, "calendar": True, "live": False}),
    }
    item.update(extra)
    return item


def _sports_relevance_summary(matches, picks=None, live=None, finished=None):
    return {
        "all_valid_matches": matches,
        "valid_upcoming_matches": matches,
        "valid_matches_available": matches,
        "valid_matches_today": [item for item in matches if item.get("v935_surface", {}).get("home")],
        "valid_live_events": live or [],
        "valid_active_picks": picks or [],
        "finished_matches": finished or [],
        "incident_matches": [],
        "incomplete_matches": [],
        "raw_matches_count": len(matches),
        "stale_live_excluded": 0,
        "safe_message": "Agenda de prueba local.",
    }


def test_sports_relevance_tier_s_beats_tier_c_even_when_minor_has_pick(app_module):
    elite = _sports_relevance_match(
        app_module,
        "elite-match",
        "UEFA Champions League",
        home="Real Madrid",
        away="Manchester City",
    )
    minor = _sports_relevance_match(
        app_module,
        "minor-pick-match",
        "Liga Local QA",
        home="Local Barrio",
        away="Visitante Barrio",
    )
    summary = _sports_relevance_summary(
        [minor, elite],
        picks=[{"id": "pick-minor", "match_id": "minor-pick-match", "market": "1X2", "selection": "Local", "odds": 2.1}],
    )
    with app_module.app.test_request_context("/calendar?lane=week"):
        calendar = app_module.v940_calendar_context(summary, "week", app_module.today_iso())
    assert calendar["matches"][0]["id"] == "elite-match"
    minor_ranked = next(item for item in calendar["matches"] if item["id"] == "minor-pick-match")
    assert minor_ranked["has_pick"] is True
    assert "PICK_SECONDARY" in minor_ranked["sports_relevance"]["reasons"]


def test_sports_relevance_live_tier_a_beats_upcoming_tier_s(app_module):
    live = _sports_relevance_match(
        app_module,
        "live-a",
        "Primeira Liga",
        date_offset=0,
        kickoff="19:00",
        status="1H",
        home="Benfica",
        away="Porto",
        minute="37",
        kickoff_iso=app_module.now_iso(),
        home_score=1,
        away_score=0,
        v935_lifecycle="LIVE",
        v935_surface={"home": True, "calendar": True, "live": True},
    )
    upcoming = _sports_relevance_match(
        app_module,
        "upcoming-s",
        "UEFA Champions League",
        date_offset=1,
        home="Bayern Munich",
        away="PSG",
    )
    summary = _sports_relevance_summary([upcoming, live], live=[live])
    with app_module.app.test_request_context("/calendar?lane=week"):
        calendar = app_module.v940_calendar_context(summary, "week", app_module.today_iso())
    assert calendar["matches"][0]["id"] == "live-a"
    assert calendar["matches"][0]["sports_relevance"]["is_live"] is True


def test_sports_relevance_favorite_boost_is_explainable(app_module):
    plain = _sports_relevance_match(app_module, "plain-local", "Liga Local QA", home="Club Normal")
    favorite = _sports_relevance_match(app_module, "favorite-local", "Liga Local QA", home="Mi Club")
    plain_ranked = app_module.apply_sports_relevance(plain, favorites={"team": set(), "league": set(), "match": set()})
    favorite_ranked = app_module.apply_sports_relevance(favorite, favorites={"team": {"mi club"}, "league": set(), "match": set()})
    assert favorite_ranked["sports_relevance_score"] > plain_ranked["sports_relevance_score"]
    assert "USER_FAVORITE" in favorite_ranked["sports_relevance"]["reasons"]


def test_sports_relevance_unknown_competitions_are_degraded_not_deleted(app_module):
    unknown = _sports_relevance_match(app_module, "unknown-match", "Torneo Sin Mapeo")
    ranked = app_module.apply_sports_relevance(unknown)
    assert ranked["sports_relevance_bucket"] == "UNKNOWN"
    assert ranked["sports_relevance"]["data_quality"] == "UNKNOWN_COMPETITION"


def test_sports_relevance_finished_match_is_removed_from_live_lane(app_module):
    finished = _sports_relevance_match(
        app_module,
        "finished-live-source",
        "LaLiga",
        date_offset=0,
        status="FT",
        home_score=2,
        away_score=1,
        v935_lifecycle="FINISHED",
        v935_surface={"home": True, "calendar": True, "live": True},
    )
    summary = _sports_relevance_summary([finished], live=[finished], finished=[finished])
    with app_module.app.test_request_context("/live?f=live"):
        live_context = app_module.v931_live_context(summary, "live", "")
    assert live_context["matches"] == []


def test_sports_relevance_upcoming_uses_madrid_kickoff_proximity(app_module):
    now_value = app_module.datetime.now(app_module.TZ).replace(second=0, microsecond=0)
    soon_dt = now_value + app_module.timedelta(hours=2)
    later_dt = now_value + app_module.timedelta(days=2)
    soon = {
        "id": "soon",
        "match_date": soon_dt.date().isoformat(),
        "kickoff_time": soon_dt.strftime("%H:%M"),
        "home_team": "Real Madrid",
        "away_team": "Barcelona",
        "competition_name": "LaLiga",
        "source": "provider-test",
        "status": "NS",
    }
    later = {
        "id": "later",
        "match_date": later_dt.date().isoformat(),
        "kickoff_time": later_dt.strftime("%H:%M"),
        "home_team": "Real Madrid",
        "away_team": "Barcelona",
        "competition_name": "LaLiga",
        "source": "provider-test",
        "status": "NS",
    }
    ranked = app_module.sort_matches_by_sports_relevance([later, soon], now_value=now_value)
    assert ranked[0]["id"] == "soon"
    assert "KICKOFF_PROXIMITY_3H" in ranked[0]["sports_relevance"]["reasons"]


def test_sports_relevance_deduplicates_before_ranking(app_module):
    first = _sports_relevance_match(app_module, "dup-match", "Premier League", kickoff="18:00")
    duplicate = {**first, "kickoff_time": "19:00"}
    ranked = app_module.sort_matches_by_sports_relevance([first, duplicate])
    assert len(ranked) == 1
    assert ranked[0]["id"] == "dup-match"


def test_sports_relevance_home_links_to_match_center(client, app_module, monkeypatch):
    elite = _sports_relevance_match(
        app_module,
        "home-elite-match",
        "UEFA Champions League",
        date_offset=1,
        home="Real Madrid",
        away="Manchester City",
    )
    summary = _sports_relevance_summary([elite])

    monkeypatch.setattr(app_module, "get_public_home_sports_summary", lambda: summary)
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '/match/home-elite-match' in html
    assert 'data-sports-relevance="PRIORITY"' in html


def test_sports_relevance_empty_live_state_is_honest(client, app_module, monkeypatch):
    summary = _sports_relevance_summary([])
    monkeypatch.setattr(app_module, "get_public_home_sports_summary", lambda: summary)
    response = client.get("/live")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "No hay partidos para este estado" in html or "Sin directo destacado" in html


@pytest.mark.parametrize(
    ("terminal_status", "expected_lifecycle"),
    [
        ("FT", "FINISHED"),
        ("FINISHED", "FINISHED"),
        ("CANCELLED", "CANCELLED"),
        ("POSTPONED", "POSTPONED"),
        ("ABANDONED", "ABANDONED"),
    ],
)
def test_p0_terminal_status_never_renders_live(app_module, terminal_status, expected_lifecycle):
    match = _sports_relevance_match(
        app_module,
        f"terminal-{terminal_status.lower()}",
        "CONCACAF Central American Cup",
        date_offset=0,
        kickoff="02:30",
        status="LIVE",
        match_status=terminal_status,
        minute="88",
        home_score=2,
        away_score=0,
        score="2-0",
    )
    truth = match_status_truth(match)
    canonical = app_module.canonical_match_status(match)
    client_view = app_module.client_match_display_context(match)
    live_card = build_live_card_payload(match)
    live_state = normalize_live_state(match)

    assert truth["lifecycle"] == expected_lifecycle
    assert truth["status_conflict"] is True
    assert truth["is_live"] is False
    assert canonical["is_live"] is False
    assert canonical["status_conflict"] is True
    assert "directo" not in client_view["client_status_label"].lower()
    assert live_card["is_live"] is False
    assert live_state["key"] not in {"LIVE", "HT"}


@pytest.mark.parametrize(
    ("match_id", "home", "away", "score", "home_score", "away_score"),
    [
        ("day1-mixco-alianza", "Mixco", "Alianza", "2-0", 2, 0),
        ("day1-olimpia-saprissa", "CD Olimpia", "Deportivo Saprissa", "2-1", 2, 1),
    ],
)
def test_p0_day1_live_ft_contradictions_degrade_to_finished(
    app_module, match_id, home, away, score, home_score, away_score
):
    match = _sports_relevance_match(
        app_module,
        match_id,
        "CONCACAF Central American Cup",
        date_offset=0,
        kickoff="02:30",
        status="LIVE",
        home=home,
        away=away,
        score=score,
        home_score=home_score,
        away_score=away_score,
        status_info={"key": "FT", "label": "Finalizado", "is_finished": True, "is_live": False},
        v935_lifecycle="FINISHED",
        v935_surface={"home": True, "calendar": False, "live": True},
    )
    canonical = app_module.canonical_match_status(match)
    enriched = enrich_match_lifecycle(match)
    live_context = app_module.v931_live_context(_sports_relevance_summary([match], live=[match], finished=[match]))

    assert canonical["key"] == "FT"
    assert canonical["is_live"] is False
    assert canonical["status_conflict"] is True
    assert enriched["v935_lifecycle"] == "FINISHED"
    assert enriched["v935_surface"]["live"] is False
    assert live_context["matches"] == []


def test_p0_live_without_real_minute_uses_honest_label_and_no_fake_score(app_module):
    live = _sports_relevance_match(
        app_module,
        "live-no-minute",
        "Primeira Liga",
        date_offset=0,
        kickoff="20:00",
        status="LIVE",
        home="Benfica",
        away="Porto",
        minute="",
        score="",
        home_score=None,
        away_score=None,
    )
    scheduled_with_minute = {**live, "id": "scheduled-minute-only", "status": "NS", "minute": "37"}

    assert app_module.canonical_match_status(live)["is_live"] is True
    assert app_module.canonical_live_minute(live) == ""
    assert app_module.client_match_display_context(live)["client_status_label"] == "En directo"
    assert build_live_card_payload(live)["minute_label"] == "En directo"
    assert build_live_card_payload(live)["score_label"] == "Resultado pendiente"
    assert enrich_live_match(live)["live_score_label"] == "Marcador no disponible"
    assert app_module.canonical_match_status(scheduled_with_minute)["is_live"] is False


@pytest.mark.parametrize("active_status", ["1H", "2H", "HT", "BT", "ET", "P"])
def test_p0_explicit_active_phase_is_live_without_inventing_minute(app_module, active_status):
    match = _sports_relevance_match(
        app_module,
        f"active-{active_status.lower()}",
        "UEFA Champions League",
        status=active_status,
        minute="",
        score="",
        home_score=None,
        away_score=None,
    )
    canonical = app_module.canonical_match_status(match)
    assert canonical["is_live"] is True
    assert app_module.canonical_live_minute(match) == ""


def test_p0_cached_live_reader_rejects_minute_only_and_terminal_conflicts(app_module, monkeypatch):
    rows = [
        _sports_relevance_match(
            app_module,
            "cached-explicit-live",
            "Primeira Liga",
            status="LIVE",
            minute="",
            home="Benfica",
            away="Porto",
        ),
        _sports_relevance_match(
            app_module,
            "cached-minute-only",
            "Primeira Liga",
            status="NS",
            minute="37",
            home="Braga",
            away="Estoril",
        ),
        _sports_relevance_match(
            app_module,
            "cached-live-ft",
            "Primeira Liga",
            status="LIVE",
            match_status="FT",
            minute="88",
            score="2-0",
            home_score=2,
            away_score=0,
            home="Sporting CP",
            away="Casa Pia",
        ),
    ]
    monkeypatch.setattr(app_module, "rows", lambda *_args, **_kwargs: [dict(item) for item in rows])

    result = app_module.get_matches(app_module.today_iso(), "live")

    assert [item["id"] for item in result] == ["cached-explicit-live"]
    assert result[0]["client_live_minute"] == ""


def test_p0_live_table_membership_and_minute_do_not_infer_live(app_module, monkeypatch):
    cached_rows = [
        {
            "lm_match_id": "live-table-no-status",
            "lm_status": "",
            "lm_minute": "41",
            "lm_home_score": 0,
            "lm_away_score": 0,
            "lm_payload_json": "",
            "lm_source": "persisted-provider-cache",
            "lm_updated_at": app_module.now_iso(),
            "id": "live-table-no-status",
            "competition_name": "Primeira Liga",
            "country": "Portugal",
            "home_team": "Braga",
            "away_team": "Estoril",
            "status": "",
            "minute": "41",
        },
        {
            "lm_match_id": "live-table-explicit",
            "lm_status": "1H",
            "lm_minute": "",
            "lm_home_score": 1,
            "lm_away_score": 0,
            "lm_payload_json": "",
            "lm_source": "persisted-provider-cache",
            "lm_updated_at": app_module.now_iso(),
            "id": "live-table-explicit",
            "competition_name": "Primeira Liga",
            "country": "Portugal",
            "home_team": "Benfica",
            "away_team": "Porto",
            "status": "1H",
            "minute": "",
        },
    ]
    monkeypatch.setattr(app_module, "rows", lambda *_args, **_kwargs: [dict(item) for item in cached_rows])
    monkeypatch.setattr(app_module, "seed_core", lambda: None)

    result = app_module.live_matches_from_live_table()

    assert [item["id"] for item in result] == ["live-table-explicit"]
    assert result[0]["status_info"]["is_live"] is True
    assert result[0]["client_live_minute"] == ""


@pytest.mark.parametrize(
    ("competition", "country", "expected_tier"),
    [
        ("Premier League", "Ukraine", "UNKNOWN"),
        ("Premier League", "Russia", "UNKNOWN"),
        ("Premier League", "Malta", "UNKNOWN"),
        ("Premier League", "Faroe Islands", "UNKNOWN"),
        ("Premier League", "Wales", "UNKNOWN"),
        ("Premier League", "Canada", "UNKNOWN"),
        ("Ukrainian Premier League", "Ukraine", "UNKNOWN"),
        ("Russian Premier League", "Russia", "UNKNOWN"),
        ("Maltese Premier League", "Malta", "UNKNOWN"),
        ("Faroe Islands Premier League", "Faroe Islands", "UNKNOWN"),
        ("Welsh Premier League", "Wales", "UNKNOWN"),
        ("Canadian Premier League", "Canada", "UNKNOWN"),
        ("Austrian Bundesliga", "Austria", "B"),
        ("Bundesliga austríaca", "Austria", "B"),
        ("Serie A", "Ecuador", "UNKNOWN"),
        ("LigaPro Serie A", "Ecuador", "UNKNOWN"),
    ],
)
def test_p0_day1_sixteen_generic_name_false_positives_are_not_tier_s(
    app_module, competition, country, expected_tier
):
    result = app_module.sports_competition_priority({
        "competition_name": competition,
        "country": country,
        "source": "persisted-provider-cache",
    })
    assert result["tier"] == expected_tier
    assert result["tier"] != "S"


def test_p0_canonical_id_then_scoped_exact_alias_classification(app_module):
    assert app_module.sports_competition_priority({"competition_id": "4328", "competition_name": "Premier League", "country": "Ukraine"})["tier"] == "S"
    assert app_module.sports_competition_priority({"competition_id": "premier-league", "competition_name": "Premier League", "country": "Ukraine"})["tier"] == "UNKNOWN"
    assert app_module.sports_competition_priority({"competition_key": "premier-league", "competition_name": "Premier League", "country": "Ukraine"})["tier"] == "UNKNOWN"
    assert app_module.sports_competition_priority({"competition_key": "premier-league", "competition_name": "Premier League", "country": "England"})["tier"] == "S"
    assert app_module.sports_competition_priority({"competition_name": "Premier League", "country": "England"})["tier"] == "S"
    assert app_module.sports_competition_priority({"competition_name": "Bundesliga", "country": "Germany"})["tier"] == "S"
    assert app_module.sports_competition_priority({"competition_name": "Ligue 1", "country": "France"})["tier"] == "S"
    assert app_module.sports_competition_priority({"competition_name": "Serie A", "country": "Italy"})["tier"] == "S"
    assert app_module.sports_competition_priority({"competition_name": "Serie A", "country": "Ecuador"})["tier"] == "UNKNOWN"


def test_p0_home_sports_first_orders_day1_elite_matches_above_low_priority_leagues(app_module):
    now_value = app_module.datetime.now(app_module.TZ).replace(second=0, microsecond=0)
    kickoff_value = now_value + app_module.timedelta(hours=1)
    date_offset = (kickoff_value.date() - now_value.date()).days
    kickoff = kickoff_value.strftime("%H:%M")
    matches = [
        _sports_relevance_match(app_module, "k-league-2", "South Korean K League 2", date_offset=date_offset, kickoff=kickoff, country="South Korea"),
        _sports_relevance_match(app_module, "chinese-super-league", "Chinese Super League", date_offset=date_offset, kickoff=kickoff, country="China"),
        _sports_relevance_match(app_module, "bayern-stuttgart", "Bundesliga", date_offset=date_offset, kickoff=kickoff, country="Germany", home="Bayern Munich", away="Stuttgart"),
        _sports_relevance_match(app_module, "lille-psg", "Ligue 1", date_offset=date_offset, kickoff=kickoff, country="France", home="Lille", away="Paris Saint-Germain"),
        _sports_relevance_match(app_module, "milan-venezia", "Serie A", date_offset=date_offset, kickoff=kickoff, country="Italy", home="AC Milan", away="Venezia"),
    ]
    ranked = app_module.sort_matches_by_sports_relevance(
        matches,
        "home",
        pick_ids={"k-league-2", "chinese-super-league"},
        now_value=now_value,
    )
    order = [item["id"] for item in ranked]

    for important in ("bayern-stuttgart", "lille-psg", "milan-venezia"):
        assert order.index(important) < order.index("k-league-2")
        assert order.index(important) < order.index("chinese-super-league")
    expected_reason = "TIER_SA_TODAY" if date_offset == 0 else "IMPORTANT_UPCOMING"
    assert ranked[0]["sports_relevance"]["home_priority_reason"] == expected_reason
    assert next(item for item in ranked if item["id"] == "k-league-2")["sports_relevance_bucket"] == "UNKNOWN"
    assert next(item for item in ranked if item["id"] == "chinese-super-league")["sports_relevance_bucket"] == "UNKNOWN"


def test_p0_unknown_baseline_is_classified_without_blind_mapping_or_api_calls(app_module, monkeypatch):
    external_calls = {"count": 0}

    def fail_external(*_args, **_kwargs):
        external_calls["count"] += 1
        raise AssertionError("No external provider call is allowed in relevance classification")

    monkeypatch.setattr(app_module, "fetch_json_url", fail_external)
    matches = [
        _sports_relevance_match(
            app_module,
            f"unknown-{index}",
            f"Competición sin mapear {index % 5}",
            country="País A" if index % 2 == 0 else "País B",
            source="persisted-provider-a" if index % 3 else "persisted-provider-b",
        )
        for index in range(130)
    ]
    quality = app_module.build_unknown_competition_quality(matches, matches[:3])

    assert quality["total"] == 130
    assert quality["mapped_automatically"] == 0
    assert quality["UNKNOWN_VISIBLE_ON_HOME"]["count"] == 3
    assert sum(item["count"] for item in quality["UNKNOWN_BY_FREQUENCY"]) == 130
    assert sum(item["count"] for item in quality["UNKNOWN_BY_COUNTRY"]) == 130
    assert sum(item["count"] for item in quality["UNKNOWN_BY_PROVIDER"]) == 130
    assert quality["external_calls"] == 0
    assert external_calls["count"] == 0


def test_p0_match_surface_contract_keeps_status_score_teams_kickoff_and_competition_consistent(app_module):
    match = _sports_relevance_match(
        app_module,
        "consistent-ft",
        "Bundesliga",
        date_offset=0,
        kickoff="18:30",
        country="Germany",
        status="LIVE",
        match_status="FT",
        home="Bayern Munich",
        away="Stuttgart",
        score="2-0",
        home_score=2,
        away_score=0,
        minute="",
    )
    base_contract = app_module.canonical_match_surface_contract(match)
    client_view = app_module.client_match_display_context(match)
    client_contract = client_view["surface_contract"]
    enriched = enrich_match_lifecycle(match)
    live_card = build_live_card_payload(client_view)
    domain_match = app_module.canonical_match_for_domain_context(match)
    match_context = build_match_context(
        {"match": domain_match, "timeline": [], "related_picks": []},
        madrid_context=client_view,
        live_context={"available": True, "status": "LIVE", "minute": "88"},
    )

    for contract in (base_contract, client_contract):
        assert contract["id"] == "consistent-ft"
        assert contract["home"] == "Bayern de Múnich"
        assert contract["away"] == "Stuttgart"
        assert contract["competition"] == "Bundesliga"
        assert contract["status_key"] == "FT"
        assert contract["score"] == "2-0"
        assert contract["kickoff_time"] == "18:30"
    assert enriched["v935_lifecycle"] == "FINISHED"
    assert live_card["status_label"] == "Finalizado"
    assert live_card["score_label"] == "2-0"
    assert live_card["home"] == base_contract["home"]
    assert live_card["away"] == "Stuttgart"
    assert live_card["competition"] == "Bundesliga"
    assert live_card["is_live"] is False
    assert domain_match["status"] == "FT"
    assert domain_match["minute"] is None
    assert match_context["lifecycle"]["is_finished"] is True
    assert match_context["lifecycle"]["is_live"] is False


DAY2_RETAINED_STALE_CARDINALITY = 19
DAY2_CONFIRMED_STALE_MATCH_ID = "sportsdb-9c185a90a281810876"


def test_p0_day2_stale_live_cardinality_is_not_live_on_any_surface(app_module):
    """Replay the retained Day 2 shape: 19 stale LIVE readings, one exact traced entity."""
    observed_at = datetime(2026, 8, 30, 22, 40, tzinfo=ZoneInfo("Europe/Madrid"))
    candidates = []
    for index in range(DAY2_RETAINED_STALE_CARDINALITY):
        match_id = DAY2_CONFIRMED_STALE_MATCH_ID if index == 0 else f"day2-stale-cardinality-{index + 1:02d}"
        candidate = _sports_relevance_match(
            app_module,
            match_id,
            "MLS",
            date_offset=0,
            kickoff="20:00",
            status="LIVE",
            home="Portland Timbers II" if index == 0 else f"Candidato Day 2 local {index + 1}",
            away="Austin FC II" if index == 0 else f"Candidato Day 2 visitante {index + 1}",
            score="0-0",
            home_score=0,
            away_score=0,
            minute="",
            source="TheSportsDB API",
            updated_at="2026-08-30T22:30:00+02:00",
            evidence_origin="REAL_PRODUCTION_OBSERVATION" if index == 0 else "DAY2_CARDINALITY_REPLAY",
        )
        candidate["match_date"] = "2026-08-30"
        candidates.append(candidate)

    summary = _sports_relevance_summary(candidates, live=candidates)
    snapshot = build_realtime_snapshot(summary, now=observed_at)
    canonical = [match_status_truth(item, now=observed_at) for item in candidates]
    enriched = [enrich_match_lifecycle(item, now=observed_at) for item in candidates]
    home_live = [
        item for item in enriched
        if (item.get("v935_surface") or {}).get("home")
        and (item.get("v935_surface") or {}).get("live")
    ]

    first = candidates[0]
    first_view = app_module.client_match_display_context(first)
    first_domain = app_module.canonical_match_for_domain_context(first)
    first_match_center = build_match_context(
        {"match": first_domain, "timeline": [], "related_picks": []},
        madrid_context=first_view,
        live_context={
            "available": True,
            "status": "LIVE",
            "updated_at": "2026-08-30T22:30:00+02:00",
            "minute": None,
            "events": [],
        },
    )

    assert len(snapshot["stale_live"]) == DAY2_RETAINED_STALE_CARDINALITY
    assert snapshot["live"] == []
    assert snapshot["counts"]["live"] == 0
    assert all(item["lifecycle"] == "STALE" for item in canonical)
    assert all(item["is_live"] is False for item in canonical)
    assert all(item["stale_reason"] == "LIVE_EVIDENCE_TOO_OLD" for item in canonical)
    assert all((item.get("v935_surface") or {}).get("live") is False for item in enriched)
    assert home_live == []
    assert app_module.canonical_match_status(first)["is_live"] is False
    assert app_module.canonical_live_minute(first) == ""
    assert first_view["status_info"]["is_live"] is False
    assert first_view["status_info"]["is_stale"] is True
    assert first_match_center["lifecycle"]["is_live"] is False
    assert first_match_center["lifecycle"]["is_stale"] is True
    assert first_match_center["story"]["phase"] == "Actualizacion pendiente"


def test_p0_cached_public_summary_reconciles_live_cards_and_counter(app_module, monkeypatch):
    cached_live = _sports_relevance_match(
        app_module,
        "cached-live-now-stale",
        "Bundesliga",
        date_offset=0,
        kickoff="20:00",
        status="LIVE",
        updated_at="2026-08-30T22:30:00+02:00",
    )
    cached_summary = _sports_relevance_summary([cached_live], live=[cached_live])
    cached_summary["sports_home"] = {"live_now": [cached_live], "quality": {"live_real": 1}}
    cached_summary["sports_metrics"] = app_module.build_sports_metrics_contract(cached_summary)

    def fake_cached_snapshot(_key, _builder, **_kwargs):
        return cached_summary, "HIT"

    monkeypatch.setattr(app_module, "cached_v934_realtime_snapshot", fake_cached_snapshot)
    monkeypatch.setattr(
        app_module,
        "build_v934_realtime_snapshot",
        lambda _summary: {
            "live": [],
            "stale_live": [{"id": cached_live["id"]}],
        },
    )

    current = app_module.get_public_home_sports_summary()

    assert current["valid_live_events"] == []
    assert current["sports_home"]["live_now"] == []
    assert current["sports_metrics"]["live_confirmed"] == 0
    assert current["summary_cache_status"] == "HIT"


def test_p0_operations_quality_contract_is_compact_and_cache_only(app_module):
    elite = _sports_relevance_match(
        app_module,
        "quality-elite",
        "Bundesliga",
        date_offset=1,
        country="Germany",
        home="Bayern Munich",
        away="Stuttgart",
    )
    unknown = _sports_relevance_match(app_module, "quality-unknown", "Torneo sin mapear", date_offset=1)
    summary = _sports_relevance_summary([elite, unknown])
    summary["last_sync"] = app_module.now_iso()
    summary["sports_home"] = app_module.build_sports_home_sections(summary)
    metrics = app_module.build_sports_metrics_contract(summary)
    quality = metrics["sports_quality"]

    assert quality["live_real"] == 0
    assert quality["live_conflicts"] == 0
    assert quality["unknown"] == 1
    assert quality["tier_sa_available"] == 1
    assert quality["tier_sa_surfaced"] == 1
    assert quality["external_calls"] == 0


def test_p0_relevance_registry_work_stays_linear_with_large_catalog(app_module, monkeypatch):
    calls = {"count": 0}
    original = app_module.normalized_label

    def counted(value):
        calls["count"] += 1
        return original(value)

    monkeypatch.setattr(app_module, "normalized_label", counted)
    competitions = [
        ("Bundesliga", "Germany"),
        ("Ligue 1", "France"),
        ("Serie A", "Italy"),
        ("K League 2", "South Korea"),
        ("Chinese Super League", "China"),
        ("Premier League", "England"),
        ("Torneo sin mapear", "Unknown"),
        ("UEFA Champions League", "Europe"),
    ]
    matches = [
        _sports_relevance_match(
            app_module,
            f"performance-{index}",
            competitions[index % len(competitions)][0],
            country=competitions[index % len(competitions)][1],
            home=f"Local {index}",
            away=f"Visitante {index}",
        )
        for index in range(200)
    ]

    ranked = app_module.sort_matches_by_sports_relevance(matches)

    assert len(ranked) == 200
    assert calls["count"] < 6000


def test_p0_home_sections_reuse_preclassified_catalog(app_module, monkeypatch):
    matches = [
        _sports_relevance_match(
            app_module,
            f"prepared-{index}",
            "Bundesliga",
            country="Germany",
            home=f"Local {index}",
            away=f"Visitante {index}",
        )
        for index in range(20)
    ]
    ranked = app_module.sort_matches_by_sports_relevance(matches)
    summary = _sports_relevance_summary(ranked)

    def fail_reclassification(*_args, **_kwargs):
        raise AssertionError("Preclassified catalog must not be classified again")

    monkeypatch.setattr(app_module, "apply_sports_relevance", fail_reclassification)
    sections = app_module.build_sports_home_sections(summary, reuse_ranked=True)

    assert sections["ranked"]
    assert sections["quality"]["external_calls"] == 0


def test_p0_public_sports_cache_ignores_unrelated_database_writes(app_module, monkeypatch, tmp_path):
    db_path = tmp_path / "performance-cache.db"
    db_path.write_bytes(b"baseline")
    monkeypatch.setattr(app_module, "DB_PATH", str(db_path))
    cache_key = app_module._public_sports_cache_key()
    app_module.invalidate_v934_realtime_cache(cache_key)
    builds = {"count": 0}

    def builder():
        builds["count"] += 1
        return {"ok": True, "source": "LOCAL_QA"}

    try:
        first, first_status = app_module.cached_v934_realtime_snapshot(
            cache_key,
            builder,
            ttl_seconds=60,
        )
        db_path.write_bytes(b"unrelated-business-write")
        second, second_status = app_module.cached_v934_realtime_snapshot(
            app_module._public_sports_cache_key(),
            builder,
            ttl_seconds=60,
        )

        assert first == second == {"ok": True, "source": "LOCAL_QA"}
        assert first_status == "refreshed"
        assert second_status == "hit"
        assert builds["count"] == 1
    finally:
        app_module.invalidate_v934_realtime_cache(cache_key)


def test_p0_team_page_reuses_favorites_and_skips_match_timeline_n_plus_one(app_module, monkeypatch):
    match = _sports_relevance_match(
        app_module,
        "team-performance",
        "Bundesliga",
        country="Germany",
        home="Bochum",
        away="Stuttgart",
    )
    favorite_calls = {"count": 0}

    def favorites():
        favorite_calls["count"] += 1
        return {"team": set(), "league": set(), "match": set(), "all": []}

    monkeypatch.setattr(app_module, "team_lookup", lambda _team_id: {"name": "Bochum", "key": "bochum"})
    monkeypatch.setattr(
        app_module,
        "resolve_team",
        lambda name: {"key": app_module.canonical_team_key(name), "name": name, "logo_url": "", "source": "LOCAL_QA"},
    )
    monkeypatch.setattr(
        app_module,
        "rows",
        lambda query, _params=(): [dict(match)] if "match_date>=?" in query else [],
    )
    monkeypatch.setattr(app_module, "get_picks", lambda limit=120: [])
    monkeypatch.setattr(app_module, "favorite_sets", favorites)
    monkeypatch.setattr(
        app_module,
        "match_timeline",
        lambda _match: (_ for _ in ()).throw(AssertionError("Team cards must not query per-match timelines")),
    )

    detail = app_module.team_page_data("Bochum")

    assert detail["upcoming"]
    assert detail["upcoming"][0]["timeline"] == []
    assert favorite_calls["count"] == 1


def test_p0_shark_briefing_reuses_cached_live_snapshot_without_rebuild(app_module, monkeypatch):
    live = _sports_relevance_match(
        app_module,
        "shark-live-cache",
        "Bundesliga",
        date_offset=0,
        status="1H",
        country="Germany",
        minute="32",
        v935_lifecycle="LIVE",
        v935_surface={"home": True, "calendar": True, "live": True},
    )
    summary = _sports_relevance_summary([live], live=[live])
    summary["last_sync"] = app_module.now_iso()
    monkeypatch.setattr(app_module, "default_profile", lambda: {"membership_plan": "FREE"})
    monkeypatch.setattr(app_module, "get_favorites", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        app_module,
        "real_time_global_state",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("SHARK render must not rebuild live state")),
    )

    briefing = app_module.shark_briefing(summary)

    assert briefing["context"]["live_state"]["live"][0]["id"] == "shark-live-cache"
    assert briefing["context"]["live_state"]["no_render_api_call"] is True
    assert briefing["context"]["live_state"]["state"]["sync_status"] == "cache_only"
