"""Organization regressions over synthetic rendered snapshots, no provider calls."""
import pytest
from test_calendar_discovery_release import render_calendar
from test_design02_calendar_presentation import Structure, assert_calendar_structure
from test_home_matchday import build, match
from test_design02_r7_home_composition import render_home


@pytest.mark.parametrize('query', ['', '?q=SIMULATED_QA', '?league=SIMULATED_QA'])
def test_league_disclosure_keeps_search_headers_and_every_fixture(query, app_module):
    leagues = [dict(key=str(i), anchor_id='league-'+str(i), label='SIMULATED_QA '+str(i),
                    matches=[dict(id='fixture-'+str(i), home_team='QA Home', away_team='QA Away',
                                  is_favorite=i < 3)]) for i in range(5)]
    days = [dict(date='2026-10-26', anchor_id='qa-day', matches_count=5,
                 league_sections=[dict(key='qa', kind='country', label='España', count=5, leagues=leagues)])]
    html, _ = render_calendar(app_module, query, day_groups=days)
    assert_calendar_structure(html)
    dom = Structure(html)
    groups = [n for n in dom.nodes if n['attrs'].get('data-v940-calendar-section') == 'league']
    assert len(groups) == 5
    assert all(n['tag'] == 'details' for n in groups)
    assert sum('open' in n['attrs'] for n in groups) == (5 if query else 2)
    assert len([n for n in dom.nodes if 'data-v934-match-id' in n['attrs']]) == 5
    for group in groups:
        assert any(n['tag'] == 'summary' and group in n['parents'] for n in dom.nodes)


@pytest.mark.parametrize('route,active', [('/directo','/directo'),('/live','/directo'),
    ('/calendario','/calendario?lane=today'),('/partidos','/calendario?lane=today'),
    ('/combinadas','/picks'),('/mi-cuenta','/mi-cuenta'),('/app',None)])
def test_client_has_one_canonical_active_destination_without_losing_home(app_module,route,active):
    with app_module.app.test_request_context(route):
        model=app_module.app.jinja_env.get_template('components/navigation_contracts.html').make_module()
        destinations=[href for _,href,_ in model.CLIENT_LINKS if str(model.is_active(href,route)).strip()]
    assert destinations == ([active] if active else [])
    from test_app_navigation import render_directory
    dom=Structure(render_directory(app_module,scope='client'))
    home_links=[n for n in dom.nodes if 'data-explore-item' in n['attrs'] and n['attrs'].get('href')=='/app']
    assert len(home_links)==2  # complete page plus its independent Explore dialog


@pytest.mark.parametrize('language',['es','en','fr'])
def test_client_home_has_five_unique_fixtures_total_and_links_for_undisplayed_lanes(app_module,language):
    rows=[match('live-'+str(i), hours=-.5, state='live') for i in range(8)]
    rows += [match('tomorrow',hours=24),match('done',hours=-4,state='finished')]
    day=build(rows)
    dom=Structure(render_home(app_module,{'home_matchday':day},language))
    ids=[n['attrs']['data-v934-match-id'] for n in dom.nodes if 'data-v934-match-id' in n['attrs']]
    assert len(ids) == len(set(ids)) == 5
    assert day['live']['total'] == 8
    links=[n['attrs'].get('href') for n in dom.nodes if n['tag']=='a']
    assert '/directo' in links and '/calendario?lane=week' in links and '/calendario?lane=finished' in links
    assert 'Sin resultados recientes verificados' not in render_home(app_module,{'home_matchday':day},language)


def test_public_home_hero_consumes_one_slot_without_duplicate_or_false_empty(app_module):
    from jinja2 import ChoiceLoader,DictLoader
    env=app_module.app.jinja_env.overlay(loader=ChoiceLoader([
        DictLoader({'base.html':'{% block content %}{% endblock %}'}),app_module.app.jinja_env.loader]))
    day=build([match('live-'+str(i),hours=-.5,state='live') for i in range(8)])
    with app_module.app.test_request_context('/'):
        html=env.get_template('home.html').render(data={'home_matchday':day},current_user=None)
    dom=Structure(html)
    ids=[n['attrs']['data-v934-match-id'] for n in dom.nodes if 'data-v934-match-id' in n['attrs']]
    assert len(ids)==len(set(ids))==5
    assert 'No hay partidos destacados en directo' not in html
    assert day['live']['total']==8


def test_explicit_favorite_enriched_after_grouping_is_not_hidden_as_secondary(app_module):
    day=build([match('saved',('regional-qa','Liga regional QA','España'))])
    group=day['today']['groups'][0]
    assert group['home_primary'] is False
    # Account favorites are applied after canonical grouping by the actual adapter.
    group['matches'][0]['is_favorite']=True
    dom=Structure(render_home(app_module,{'home_matchday':day}))
    card,=[n for n in dom.nodes if n['attrs'].get('data-v934-match-id')=='saved']
    assert not any(n['tag']=='details' for n in card['parents'])
    assert group['home_primary'] is False
