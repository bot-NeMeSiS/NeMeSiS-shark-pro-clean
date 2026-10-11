"""Home league hierarchy: real templates/CSS, synthetic data, zero external requests.

No production DB, provider calls or fabricated official fixture/logo coverage.
"""
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote, urlsplit
import os
import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from engines.home_matchday import build_matchday

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime.fromisoformat('2026-10-11T12:00:00+02:00')
MAJORS = [('laliga','LaLiga','España'),('premier','Premier League','Inglaterra'),
          ('champions','Champions League','Europa'),('serie-a','Serie A','Italia'),
          ('bundesliga','Bundesliga','Alemania'),('ligue1','Ligue 1','Francia')]


def fixture_rows(major_count=6, other_count=30):
    result=[]
    for i,(key,label,country) in enumerate(MAJORS[:major_count]):
        for j in range(2):
            result.append(row(f'qa-main-{i}-{j}', key, label, country, 10))
    for i in range(other_count):
        result.append(row(f'qa-other-{i}',f'other-{i}',f'Competición de prueba {i:02}',
                          'España' if i%2 else 'Portugal',70))
    return result


def row(identifier,key,label,country,rank,**extra):
    return dict(id=identifier,competition_key=key,competition_name=label,country=country,
        home_team='Equipo local QA',away_team='Equipo visitante QA',source='SIMULATED_QA',
        kickoff_iso=(NOW+timedelta(hours=2)).isoformat(),kickoff_time='14:00',
        client_status_label='Programado',competition_logo='/static/qa-badge.svg',
        status='NS',qa_rank=rank,**extra)


def build(rows):
    return build_matchday(rows, now=NOW,
        status_for=lambda m: {'key':'UPCOMING','is_upcoming':True,'is_live':False,
                             'is_stale':m.get('is_stale',False),'status_conflict':m.get('status_conflict',False)},
        kickoff_for=lambda m:datetime.fromisoformat(m['kickoff_iso']),
        priority_for=lambda m: {'rank':m['qa_rank']})


def environment():
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=select_autoescape(['html']))
    env.globals.update(ui=lambda value,**values:str(value or '').format(**values),
        ui_owned=lambda value:str(value or ''),current_user=None,
        request=SimpleNamespace(path='/',endpoint='home'),
        ui_calendar_date=lambda value,**kw:str(value),
        ui_match_clock=lambda match:match.get('kickoff_time','Hora'),
        ui_match_datetime=lambda match:match.get('kickoff_time',''),
        nemesis_data_confidence=lambda *args:{'score':0,'label':'SIMULATED_QA','tone':'neutral','disclaimer':'Datos de prueba'},
        nemesis_attention_priority=lambda *args:{'level':1,'label':'QA','disclaimer':'Datos simulados'},
        sports_entity_href=lambda kind,key,name:'/'+('competicion' if kind=='competition' else 'equipo')+'/'+quote(str(key),safe=''),
        url_for=lambda endpoint,**kw:'/static/'+kw.get('filename','qa-badge.svg'))
    env.filters['sync_madrid_label']=lambda value:value
    env.filters['match_madrid_context']=lambda value:value
    return env


def markup(rows=None,section='public-today'):
    day=build(fixture_rows() if rows is None else rows)
    component=environment().get_template('components/home_competition_groups.html').module
    body=str(component.competition_groups(day['today']['groups'],False,section))
    styles=(ROOT/'static/product-system.css').read_text()+'\n'+(ROOT/'static/home-league-disclosure.css').read_text()
    script=(ROOT/'static/home-league-disclosure.js').read_text()
    return '<!doctype html><html lang="es"><head><meta name="viewport" content="width=device-width, initial-scale=1">'+\
        '<style>'+styles+'</style></head><body class="ns-app">'+\
        '<main class="v933-page" style="max-width:1100px;margin:0 auto;padding:20px"><p>SIMULATED_QA · Vista del componente, no producción</p>'+\
        '<h1>Partidos de hoy</h1><p>Principales primero · Hora Madrid</p>'+body+'</main><script>'+script+'</script></body></html>'



def test_major_leagues_only_in_primary_without_losing_any_match():
    rows=fixture_rows();original=deepcopy(rows);lane=build(rows)['today']
    primary=[g for g in lane['groups'] if g['home_primary']]
    secondary=[g for g in lane['groups'] if not g['home_primary']]
    assert len(primary)==6 and len(secondary)==30
    assert lane['shown']==lane['total']==42
    assert {m['id'] for g in primary+secondary for m in g['matches']}=={r['id'] for r in rows}
    assert rows==original
    assert all(g['home_priority_rank']==10 for g in primary)


def test_unknown_and_minor_leagues_are_not_promoted_to_fill_empty_home():
    lane=build(fixture_rows(0,35))['today']
    assert len(lane['groups'])==35 and not any(g['home_primary'] for g in lane['groups'])
    assert lane['shown']==35


def test_same_name_in_other_country_is_not_promoted_by_a_substring():
    rows=[row('official','premier','Premier League','Inglaterra',10),
          row('other','ghana-premier','Premier League','Ghana',95)]
    groups=build(rows)['today']['groups']
    assert {g['country']:g['home_primary'] for g in groups}=={'Inglaterra':True,'Ghana':False}


def test_favorite_in_another_competition_can_be_visible_without_mutation():
    rows=fixture_rows(0,5);rows[3]['is_favorite']=True;old=deepcopy(rows)
    groups=build(rows)['today']['groups']
    assert [g['key'] for g in groups if g['home_primary']]==['other-3']
    assert rows==old


def test_more_than_six_major_groups_are_still_bounded_and_accessible():
    rows=[row(str(i),str(i),'Major QA '+str(i),'España',10) for i in range(15)]
    groups=build(rows)['today']['groups']
    assert sum(g['home_primary'] for g in groups)==6
    assert sum(g['shown'] for g in groups)==15


@pytest.mark.parametrize('attribute',['is_stale','status_conflict'])
def test_disclosure_never_resurrects_rejected_rows(attribute):
    rows=fixture_rows(1,1);rows[0][attribute]=True
    lane=build(rows)['today']
    assert lane['total']==2 and all(m['id']!=rows[0]['id'] for g in lane['groups'] for m in g['matches'])


def test_native_disclosure_and_provider_text_are_safe_without_javascript():
    rows=[row('x','x','<script>do_not_execute</script>','España',95)]
    html=markup(rows)
    assert '&lt;script&gt;do_not_execute&lt;/script&gt;' in html
    assert '<script>do_not_execute' not in html
    assert 'data-home-more-leagues' in html and 'name="home-other-leagues-public-today"' in html
    assert '<details open' not in html


def test_home_assets_are_conditional_and_canonical_bundle_is_not_replaced():
    text=(ROOT/'templates/base.html').read_text()
    start=text.index("{% if request.endpoint in ['home', 'v757_client_app_center_page'] %}")
    block=text[start:text.index('{% endif %}',start)]
    assert 'home-league-disclosure.css' in block and 'home-league-disclosure.js' in block
    assert text.count("filename='home-league-disclosure.css'")==1
    assert "filename='product-system.css'" in text


@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        instance=p.chromium.launch(headless=True,executable_path=os.getenv('NEMESIS_QA_CHROMIUM') or p.chromium.executable_path)
        yield instance
        instance.close()


def prepare_page(browser,html,width=390,javascript=True):
    # In-memory component QA. Browser policy can forbid even a synthetic .invalid
    # navigation in this environment. No network navigation is attempted here.
    context=browser.new_context(viewport={'width':width,'height':900},java_script_enabled=javascript,service_workers='block')
    page=context.new_page(); calls=[];errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    context.route('**/*',lambda route:(calls.append(route.request.url),route.abort()))
    from urllib.parse import quote
    badge='data:image/svg+xml,'+quote('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" rx="10" fill="white"/><text x="8" y="40" font-size="22">QA</text></svg>')
    page.set_content(html.replace('/static/qa-badge.svg',badge),wait_until='load')
    # Record the actual anchor requested by native keyboard activation without
    # visiting any server. Full HTTP navigation belongs to the existing CI suite.
    page.evaluate("document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(a){window.__qaDestination=a.getAttribute('href');e.preventDefault();}})")
    return context,page,calls,errors


@pytest.mark.parametrize('width',[320,390,1440])
@pytest.mark.parametrize('javascript',[False,True])
@pytest.mark.parametrize('section',['today','public-today'])
def test_browser_compact_index_native_fold_and_links(browser,width,javascript,section):
    context,page,calls,errors=prepare_page(browser,markup(section=section),width,javascript)
    try:
        assert page.locator('.home-league-index a').count()==6
        assert page.locator('[data-home-importance="primary"]:visible').count()==6
        assert page.locator('[data-home-importance="secondary"]:visible').count()==0
        assert page.locator('[data-v934-match-id]').count()==42
        assert page.locator('[data-v934-match-id]:visible').count()==12
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        more=page.locator('[data-home-more-leagues]')
        more.locator(':scope > summary').focus();page.keyboard.press('Enter')
        assert more.get_attribute('open') is not None
        assert page.locator('[data-home-importance="secondary"]:visible').count()==30
        # Expanding More lists compact league headers, not every match at once.
        assert page.locator('[data-v934-match-id]:visible').count()==12
        league=page.locator('[data-home-importance="secondary"]').first
        league.locator(':scope > summary').focus();page.keyboard.press('Space')
        assert league.locator('[data-v934-match-id]').is_visible()
        another=page.locator('[data-home-importance="secondary"]').nth(1)
        another.locator(':scope > summary').focus();page.keyboard.press('Enter')
        assert not league.locator('[data-v934-match-id]').is_visible()
        assert another.locator('[data-v934-match-id]').is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        link=another.locator('a[href^="/match/"]').last
        dest=link.get_attribute('href');link.focus()
        assert dest.startswith('/match/') and link.evaluate('(el)=>document.activeElement===el')
        if javascript:
            page.keyboard.press('Enter')
            assert page.evaluate('window.__qaDestination')==dest
        assert not errors
        assert calls==[]
    finally:context.close()


@pytest.mark.parametrize('width',[320,390,1440])
def test_search_clear_hash_and_input_composition(browser,width):
    context,page,calls,errors=prepare_page(browser,markup(),width)
    try:
        page.locator('[data-home-more-leagues] > summary').click()
        query=page.locator('[data-home-league-search]');query.fill('espana')
        assert page.locator('[data-home-importance="secondary"]:visible').count()==15
        query.fill('no hay liga con este texto')
        assert page.locator('[data-home-no-league-results]').is_visible()
        page.locator('[data-home-league-clear]').click()
        assert query.input_value()=='' and page.locator('[data-home-importance="secondary"]:visible').count()==30
        target=page.locator('[data-home-importance="secondary"]').nth(12)
        target_id=target.get_attribute('id')
        query.fill('oculta todas')
        page.evaluate('(id)=>{location.hash=id}',target_id)
        page.wait_for_function('(id)=>document.getElementById(id).open',arg=target_id)
        assert target.is_visible() and target.locator('[data-v934-match-id]').is_visible()
        assert query.input_value()==''
        page.add_script_tag(content=(ROOT/'static/home-league-disclosure.js').read_text())
        assert page.locator('[data-home-league-filter]').count()==1
        assert not errors
    finally:context.close()


@pytest.mark.parametrize('width',[320,1440])
def test_minor_only_day_is_compact_instead_of_becoming_a_catalogue(browser,width):
    context,page,calls,errors=prepare_page(browser,markup(fixture_rows(0,35)),width,False)
    try:
        assert page.locator('.home-league-index a').count()==0
        assert page.locator('[data-home-more-leagues] > summary').is_visible()
        assert page.locator('[data-v934-match-id]:visible').count()==0
        assert page.locator('[data-home-league-agenda]').bounding_box()['height'] < 200
        page.locator('[data-home-more-leagues] > summary').click()
        assert page.locator('[data-home-importance="secondary"]:visible').count()==35
        assert not errors
    finally:context.close()


@pytest.mark.parametrize('path,template',[
    ('/','home.html'),('/app','client_app_center.html'),('/inicio','client_app_center.html'),
    ('/mi-app','client_app_center.html'),('/panel-cliente','client_app_center.html')])
def test_real_flask_home_loads_disclosure_once_on_every_home_alias(app_module,path,template):
    """Full application Jinja and route matching. Runs in CI with Flask installed."""
    from flask import render_template
    from test_design02_calendar_presentation import Structure
    day=build(fixture_rows())
    user=None if path=='/' else {'id':'qa-home-focus','name':'Prueba','membership':'FREE'}
    with app_module.app.test_request_context(path):
        html=render_template(template,data={'home_matchday':day,'sports_metrics':{'matches_today':42,'live_confirmed':0,'picks_ready':0}},
            current_user=user,greeting={'label':'Vista de prueba','name':'QA'},evidence_origin='SIMULATED_QA')
    dom=Structure(html)
    primary=[n for n in dom.nodes if n['attrs'].get('data-home-importance')=='primary']
    secondary=[n for n in dom.nodes if n['attrs'].get('data-home-importance')=='secondary']
    assert len(primary)==6 and len(secondary)==30
    assert html.count('home-league-disclosure.css')==1
    assert html.count('home-league-disclosure.js')==1
    assert all(any('data-home-more-leagues' in p['attrs'] for p in n['parents']) for n in secondary)
    assert not any(any(p['tag']=='details' for p in n['parents']) for n in primary)


@pytest.mark.parametrize('empty_value',[False,True])
def test_hierarchy_detector_accepts_boolean_attributes_without_losing_structure(empty_value):
    from test_design02_calendar_presentation import Structure
    html=markup()
    if empty_value:
        html=html.replace('data-home-more-leagues>', 'data-home-more-leagues="">')
    dom=Structure(html)
    secondary=[n for n in dom.nodes if n['attrs'].get('data-home-importance')=='secondary']
    primary=[n for n in dom.nodes if n['attrs'].get('data-home-importance')=='primary']
    assert len(secondary)==30 and len(primary)==6
    assert all(any('data-home-more-leagues' in p['attrs'] for p in n['parents']) for n in secondary)
    assert all(not any(p['tag']=='details' for p in n['parents']) for n in primary)
    # A secondary row detached from the disclosure must still fail this detector.
    detached=Structure('<details data-home-importance="secondary"><summary>QA</summary></details>').nodes[0]
    assert not any('data-home-more-leagues' in p['attrs'] for p in detached['parents'])
