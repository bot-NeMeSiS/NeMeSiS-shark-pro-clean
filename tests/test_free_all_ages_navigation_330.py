"""Release guard: anonymous and FREE navigation must be informative (#330).

These tests do NOT claim to verify the server age gate, checkout lawfulness,
or compliance for every route. Those are separately required before merge.
"""
from pathlib import Path

import pytest
from jinja2 import Environment
from test_app_navigation import render_directory
from test_design02_calendar_presentation import Structure


ROOT = Path(__file__).resolve().parents[1]
ADULT_TARGETS = {"/picks", "/combinadas", "/historico", "/membresias", "/precios"}


def test_public_and_default_free_nav_do_not_promote_betting():
    text = (ROOT / "templates/components/navigation_contracts.html").read_text(encoding="utf-8")
    nav = Environment().from_string(text).make_module()
    for name in ("PUBLIC_LINKS", "PUBLIC_MOBILE_LINKS", "CLIENT_LINKS", "CLIENT_MOBILE_LINKS"):
        entries = getattr(nav, name)
        assert entries, name
        paths = {href.split("?")[0] for _label, href, _icon in entries}
        assert ADULT_TARGETS.isdisjoint(paths), (name, paths)
    assert ("Pronósticos", "/picks", "target") in nav.CLIENT_ADULT_LINKS


@pytest.mark.parametrize("scope", ["public", "client"])
def test_explore_is_informational_for_anonymous_and_free(app_module, scope):
    html = render_directory(app_module, scope)
    tree = Structure(html)
    targets = {
        node["attrs"].get("href", "").split("?")[0]
        for node in tree.nodes
        if "data-explore-item" in node["attrs"]
    }
    assert ADULT_TARGETS.isdisjoint(targets), (scope, targets)
    assert "/competiciones" in targets
    if scope == "client":
        assert "/shark" in targets, "FREE retains sports-only SHARK discovery"


def test_free_plan_description_has_no_betting_upsell():
    text = (ROOT / "templates/membership.html").read_text(encoding="utf-8")
    free = text.split('class="v933-plan-card is-blue', 1)[1].split('{% for key, tone', 1)[0]
    assert "Pronósticos" not in free
    assert "apuestas" not in free.lower()
    assert "Resultados" in free


def test_anonymous_sports_home_has_no_betting_promotion():
    from test_home_canonical_consistency import data_for, render

    markup = render("home.html", data_for([]))
    assert 'data-free-informational="true"' in markup
    assert "SHARK deportivo" in markup
    assert 'href="/competiciones"' in markup
    for restricted in ("/picks", "/combinadas", "/historico", "/membresias", "/precios"):
        assert f'href="{restricted}"' not in markup, restricted
    assert "pronósticos SHARK" not in markup.lower()


def test_sports_hub_template_does_not_advertise_betting():
    source = (ROOT / "templates/sports_hub.html").read_text(encoding="utf-8")
    assert 'href="/picks"' not in source
    assert "Combinadas" not in source
    assert "Pronósticos" not in source
    assert 'href="/competiciones"' in source


def test_free_client_dashboard_is_sport_only_when_picks_are_in_context():
    from test_home_canonical_consistency import render

    data = {
        "v925_picks": {"picks": [{"id": "private-qa-pick"}]},
        "sports_metrics": {"matches_today": 1, "picks_ready": 1},
        "v925_calendar": {},
    }
    html = render("client_app_center.html", data)
    assert "Explora tus competiciones" in html
    assert 'href="/picks"' not in html
    assert 'data-free-informational="true"' in html
    assert "Pronósticos activos" not in html
    assert "Pronóstico destacado" not in html
