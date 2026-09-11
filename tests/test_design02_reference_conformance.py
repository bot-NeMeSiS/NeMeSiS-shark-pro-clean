"""Structural design regressions. Synthetic data is confined to these tests."""
from pathlib import Path

import pytest
from jinja2 import ChoiceLoader, DictLoader

from test_design02_calendar_presentation import Structure


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('key,field,component', [
    ('lineups', 'confirmed', 'LineupsPanel'),
    ('event_summary', 'available', 'Timeline'),
    ('statistics', 'available', 'StatsPanel'),
    ('head_to_head', 'available', 'HeadToHeadPanel'),
    ('standings', 'available', 'StandingsPanel'),
    ('media', 'visible_count', 'VideoPanel'),
])
@pytest.mark.parametrize('available', [False, True])
def test_available_match_sections_stay_open_and_missing_sections_remain_accessible(
    app_module, key, field, component, available
):
    from engines.match_context_engine import build_match_context
    from test_v944_match_center_foundation import _detail

    detail = _detail()
    context = build_match_context(detail, evaluation_time='2026-07-23T19:50:00+02:00')
    context[key][field] = available
    env = app_module.app.jinja_env.overlay(loader=ChoiceLoader([
        DictLoader({'base.html': '{% block content %}{% endblock %}'}),
        app_module.app.jinja_env.loader,
    ]))
    with app_module.app.test_request_context('/match/SIMULATED_QA'):
        html = env.get_template('match_detail.html').render(
            detail=detail, match_context=context, current_user=None
        )
    dom = Structure(html)
    if key == 'media':
        panels = [n for n in dom.nodes if n['attrs'].get('data-match-region') == 'authorized-video']
        if not available:
            assert not panels
            assert 'Resumen en vídeo no disponible' not in html
            return
    else:
        panels = [n for n in dom.nodes if n['attrs'].get('data-match-component') == component]
    panel, = panels
    in_disclosure = any('v944-coverage-details' in n['attrs'].get('class', '') for n in panel['parents'])
    assert in_disclosure is not available
    assert len(panels) == 1


@pytest.mark.parametrize('with_results', [False, True])
def test_team_without_confirmed_form_does_not_display_zero_statistics(app_module, with_results):
    from engines.team_center_engine import build_team_center_context
    from test_team_center_premium_experience import _detail

    detail = _detail()
    if not with_results:
        detail['recent'] = []
    detail['team_center'] = build_team_center_context(detail, observed_at_madrid='2026-07-28T10:00:00+02:00')
    env = app_module.app.jinja_env.overlay(loader=ChoiceLoader([
        DictLoader({'base.html': '{% block content %}{% endblock %}'}),
        app_module.app.jinja_env.loader,
    ]))
    with app_module.app.test_request_context('/team/SIMULATED_QA'):
        html = env.get_template('team_detail.html').render(detail=detail, current_user=None)
    dom = Structure(html)
    assert bool(dom.with_class('team-center-form-metrics')) is with_results
    if not with_results:
        assert 'No disponible. Ninguna fuente confirma una muestra suficiente.' in html


def test_compact_brand_reuses_certified_app_icon_without_second_geometry(app_module):
    with app_module.app.test_request_context('/app'):
        macro = app_module.app.jinja_env.get_template('partials/brand_logo.html').make_module()
        dom = Structure(str(macro.nemesis_brand()))
    img, = [n for n in dom.nodes if n['tag'] == 'img']
    assert img['attrs']['src'] == '/static/img/app-icons/app-icon-96.png?v=8d0ed4207e73'
    assert img['attrs']['data-brand-source'] == 'official-app-icon'
    assert (ROOT / img['attrs']['src'].split('?')[0].lstrip('/')).is_file()


def test_admin_table_contract_keeps_actions_and_headers_unbroken():
    css = (ROOT / 'static/v933-product.css').read_text(encoding='utf-8')
    assert '.v933-admin-picks .v933-data-table { min-width: 780px; table-layout: auto !important; }' in css
    assert '.v933-admin-picks .v933-data-table :is(th,.v928-table-action,.v933-status-chip) { white-space: nowrap !important; }' in css
    assert '.v930-admin-launch .v928-data-table { min-width: 620px; table-layout: auto !important; }' in css


def test_local_admin_banner_keeps_desktop_heading_clearance():
    css = (ROOT / 'static/v933-product.css').read_text(encoding='utf-8')
    rule = next(line for line in css.splitlines() if ':has(> .nemesis-local-safe-banner) main.v933-admin-shell' in line)
    assert 'padding-top: 90px !important' in rule
    assert 'ns-admin' in rule
