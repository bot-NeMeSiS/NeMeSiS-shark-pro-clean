"""Fast-path contract for the authenticated client app home.

Template tests render the actual page with presentation-only macro stubs. They
exercise lane selection, not browser appearance or production authentication.
All match data in this file is synthetic and stays in test memory.
"""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]


def _summary():
    return {
        "valid_matches_today": [
            {
                "id": "m1",
                "home_team": "Local QA",
                "away_team": "Visitante QA",
                "competition_name": "Liga QA",
                "match_date": "2026-09-29",
                "kickoff_time": "10:00",
                "source": "TheSportsDB API",
                "status": "PROGRAMADO",
            }
        ],
        "valid_upcoming_matches": [],
        "valid_live_events": [],
        "valid_active_picks": [],
        "valid_matches_available": [],
        "finished_matches": [
            {
                "id": "finished-qa",
                "home_team": "Final QA",
                "away_team": "Visitante QA",
                "competition_name": "Liga QA",
                "match_date": "2026-09-29",
                "kickoff_time": "08:00",
                "source": "TheSportsDB API",
                "status": "FT",
                "home_score": 2,
                "away_score": 1,
                "score": "2-1",
            }
        ],
        "all_valid_matches": [],
        "incomplete_matches": [],
        "provider_status": "qa",
        "last_sync": "2026-09-29T07:00:00+02:00",
        "safe_message": "QA",
        "sports_home": {
            "important_today": [],
            "live_now": [],
            "favorites": [],
            "upcoming": [],
            "recent_results": [
                {
                    "id": "finished-qa",
                    "home_team": "Final QA",
                    "away_team": "Visitante QA",
                    "competition_name": "Liga QA",
                    "match_date": "2026-09-29",
                    "kickoff_time": "08:00",
                    "source": "TheSportsDB API",
                    "status": "FT",
                    "home_score": 2,
                    "away_score": 1,
                    "score": "2-1",
                }
            ],
            "counts": {},
        },
    }


def test_compact_client_home_never_calls_full_dashboard_builder(app_module, monkeypatch):
    calls = []

    def forbidden_dashboard(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("client /app fast path must not call dashboard_data")

    monkeypatch.setattr(app_module, "dashboard_data", forbidden_dashboard)
    monkeypatch.setattr(
        app_module,
        "get_v932_real_sports_value_context",
        lambda summary=None: {"real_matches_available": True},
    )
    with app_module.app.test_request_context("/app"):
        data, summary = app_module.v932_safe_dashboard_data(
            "/app", compact=True, sports_summary=_summary(),
        )

    # Assert the call count too: a catch-all must not hide a forbidden call.
    assert calls == []
    assert data["v931_route_guard"]["status"] == "compact_read_only_context"
    assert data["v931_route_guard"]["no_render_api_call"] is True
    assert "match_hub" in data
    assert "sports_home" in data["home_summary"]
    assert "v925_picks" in data
    assert "sports_metrics" in data
    assert summary["provider_status"] == "qa"
    assert data["home_summary"]["sports_home"]["recent_results"]
    # Preserve results at the actual consumer boundary, not just inside a dict.
    assert 'data-test-match="finished-qa"' in _render_home(data)


def _route_source(name):
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    node = next(
        node for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    return ast.get_source_segment(source, node) or ""


def test_client_app_route_selects_compact_context():
    route = _route_source("v757_client_app_center_page")
    assert "v932_safe_dashboard_data(request.path, compact=True)" in route
    assert "\n    data = dashboard_data(" not in route
    assert "\n    return dashboard_data(" not in route
    # Lane preservation is asserted by rendering below, not by requiring a
    # duplicate route-side projection of the already available sports_home.


def test_picks_route_has_no_accidental_home_projection():
    route = _route_source("picks_page")
    assert "sports_home.get(\"recent_results\")" not in route
    assert "legacy match_hub contract still consumed by the current Inicio template" not in route


def test_client_home_template_only_depends_on_compact_sports_contract():
    source = (ROOT / "templates" / "client_app_center.html").read_text(encoding="utf-8")
    for marker in (
        "data.get('match_hub')",
        "data.get('home_summary')",
        "data.get('available_matches')",
        "data.get('v925_picks')",
        "data.get('sports_metrics')",
        "data.get('v925_calendar')",
    ):
        assert marker in source


# Presentation stubs leave the real template control flow and HTML intact.
_MACROS = """
{% macro icon(name) %}{% endmacro %}
{% macro status_chip(label, color='') %}{{ label }}{% endmacro %}
{% macro section_header(title, body='', label='', href='', badge='') %}<h2>{{ title }}</h2>{% endmacro %}
{% macro kpi_card(label, value, body='', color='', icon='', href='') %}<b data-test-kpi="{{ label }}">{{ value }}</b>{% endmacro %}
{% macro quick_action(label, body, href, icon, color='') %}<a href="{{ href }}">{{ label }}</a>{% endmacro %}
{% macro empty_state(title, body='', label='', href='', icon='') %}<p>{{ title }}</p>{% endmacro %}
{% macro match_card(match, a=false, b=false) %}<article data-test-match="{{ match.id }}"></article>{% endmacro %}
{% macro live_card(match) %}<article data-test-match="{{ match.id }}"></article>{% endmacro %}
{% macro pick_card(pick, a=false, mode='') %}<article data-test-pick="{{ pick.id }}"></article>{% endmacro %}
{% macro sports_contract_attributes(metrics) %}{% endmacro %}
"""


def _home_environment(template_override=None):
    stubs = {"base.html": "{% block content %}{% endblock %}", "components/v933_ui.html": _MACROS}
    if template_override is not None:
        stubs["client_app_center.html"] = template_override
    return Environment(
        loader=ChoiceLoader([DictLoader(stubs), FileSystemLoader(ROOT / "templates")]),
        autoescape=select_autoescape(["html"]),
    )


def _render_home(data, env=None):
    return (env or _home_environment()).get_template("client_app_center.html").render(
        data=data,
        current_user=SimpleNamespace(membership="FREE"),
        greeting=SimpleNamespace(label="Hola", name="QA"),
        ui=lambda text, **values: text.format(**values),
    )


LANES = (
    ("live_now", "live"),
    ("important_today", "today"),
    ("favorites", "favorites"),
    ("upcoming", "upcoming"),
    ("recent_results", "finished"),
)


def _empty_snapshot():
    return {key: [] for key, _ in LANES}


def _compact_data(snapshot, hub=None):
    return {
        "home_summary": {"sports_home": snapshot},
        "match_hub": hub or {},
        "available_matches": [],
        "v925_picks": {"picks": []},
        "sports_metrics": {},
        "v925_calendar": {},
    }


@pytest.mark.parametrize("lane,legacy_lane", LANES)
def test_compact_home_renders_each_snapshot_lane(lane, legacy_lane):
    snapshot = _empty_snapshot()
    snapshot[lane] = [{"id": "chosen-" + lane}]
    data = _compact_data(snapshot, {legacy_lane: [{"id": "obsolete-" + lane}]})
    html = _render_home(data)
    assert 'data-test-match="chosen-' + lane + '"' in html
    assert 'data-test-match="obsolete-' + lane + '"' not in html


@pytest.mark.parametrize("lane,legacy_lane", LANES)
@pytest.mark.parametrize("empty_value", [[], None])
def test_explicit_empty_snapshot_lane_does_not_revive_legacy_cards(lane, legacy_lane, empty_value):
    snapshot = _empty_snapshot()
    snapshot[lane] = empty_value
    html = _render_home(_compact_data(snapshot, {legacy_lane: [{"id": "stale-card"}]}))
    assert 'data-test-match="stale-card"' not in html
    if lane == "live_now":
        assert 'data-sports-priority="live-now"' not in html


@pytest.mark.parametrize("lane,legacy_lane", LANES)
@pytest.mark.parametrize("nested", [False, True])
def test_legacy_context_still_renders_when_compact_snapshot_absent(lane, legacy_lane, nested):
    hub = {"sports_home": {lane: [{"id": "legacy-card"}]}} if nested else {legacy_lane: [{"id": "legacy-card"}]}
    data = _compact_data(None, hub)
    assert 'data-test-match="legacy-card"' in _render_home(data)


def test_finished_and_favorite_cards_survive_together():
    snapshot = _empty_snapshot()
    snapshot["favorites"] = [{"id": "favorite-card"}]
    snapshot["recent_results"] = [{"id": "finished-card"}]
    html = _render_home(_compact_data(snapshot))
    assert 'data-test-match="favorite-card"' in html
    assert 'data-test-match="finished-card"' in html
    assert 'data-test-kpi="Favoritos">1</b>' in html


def test_template_reuse_does_not_mutate_inputs_or_leak_favorites():
    shared_hub = {"live": [], "favorites": []}
    first = _compact_data({**_empty_snapshot(), "favorites": [{"id": "user-a-favorite"}]}, shared_hub)
    second = _compact_data(_empty_snapshot(), shared_hub)
    before = deepcopy((first, second))
    env = _home_environment()
    assert 'data-test-match="user-a-favorite"' in _render_home(first, env)
    assert "user-a-favorite" not in _render_home(second, env)
    assert (first, second) == before


def test_pick_card_and_unavailable_state_remain_visible():
    data = _compact_data(_empty_snapshot())
    data["v925_picks"]["picks"] = [{"id": "pick-card"}]
    data["v925_calendar"]["provider_status"] = "temporarily_unavailable"
    html = _render_home(data)
    assert 'data-test-pick="pick-card"' in html
    assert 'data-home-empty="ERROR"' in html


def test_live_card_is_not_duplicated_in_featured_matches():
    snapshot = _empty_snapshot()
    snapshot["live_now"] = [{"id": "same-match"}]
    snapshot["important_today"] = [{"id": "same-match"}, {"id": "next-match"}]
    html = _render_home(_compact_data(snapshot))
    assert html.count('data-test-match="same-match"') == 1
    assert 'data-test-match="next-match"' in html
