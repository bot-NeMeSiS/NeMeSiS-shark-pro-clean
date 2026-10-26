"""Request-local Home coherence; synthetic data, no provider calls or DB writes.

Offline component tests use the real Home and shared card templates, with an
in-memory base and deterministic display helpers. Separate Flask tests below
exercise the actual application's Jinja environment in CI.
"""
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import os
from urllib.parse import quote

from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, select_autoescape
import pytest

from engines.home_matchday import build_matchday
from engines.ui_localization_engine import translate

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 11, 12, tzinfo=ZoneInfo('Europe/Madrid'))
BADGE = 'data:image/svg+xml,'+quote('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><text x="4" y="32">QA</text></svg>')


def row(identity, state='UPCOMING', *, stale=False):
    dt = NOW + timedelta(hours=2 if state=='UPCOMING' else -1)
    return {'id':identity, 'home_team':'QA Local '+identity, 'away_team':'QA Visitante',
            'competition_key':'qa-league', 'competition_name':'Liga SIMULATED_QA',
            'country':'Spain', 'source':'SIMULATED_QA', 'client_schedule_label':'11/10/2026 14:00',
            'kickoff_iso':dt.isoformat(), 'kickoff_time':dt.strftime('%H:%M'),
            'status_info':{'key':state, 'is_live':state=='LIVE', 'is_finished':state=='FINISHED',
                           'is_upcoming':state=='UPCOMING', 'is_stale':stale},
            'home_score':1 if state!='UPCOMING' else None,
            'away_score':0 if state!='UPCOMING' else None, 'is_favorite':False,
            'competition_logo':BADGE}


def make_day(rows, limit=None):
    return build_matchday(rows, now=NOW, status_for=lambda m:m['status_info'],
        kickoff_for=lambda m:datetime.fromisoformat(m['kickoff_iso']),
        priority_for=lambda m:{'rank':10}, limit=limit)


def data_for(rows, *, old_count=91, limit=None):
    stale = row('cached-expired', 'LIVE', stale=True)
    return {'home_matchday':make_day(rows,limit), 'sports_metrics':{'live_confirmed':old_count},
            'home_summary':{'has_real_data':True, 'sports_home':{
                'live_now':[stale], 'important_today':[stale], 'upcoming':[stale],
                'recent_results':[stale], 'favorites':[stale]}}}


def component_env(path='/'):
    env=Environment(loader=ChoiceLoader([DictLoader({'base.html':'{% block content %}{% endblock %}'}),
                    FileSystemLoader(ROOT/'templates')]),autoescape=select_autoescape(['html']))
    env.globals.update(ui=lambda value,**kw:translate(value,'es',**kw),
        ui_country=lambda value:str(value or ''),
        ui_owned=lambda value:translate(value,'es'),
        request=SimpleNamespace(path=path),
        sports_match_team_href=lambda match,side:f"/team/{quote(str(match.get(side+'_team') or ''))}",
        ui_calendar_date=lambda value,**kw:str(value),
        ui_match_clock=lambda m:m.get('kickoff_time') or 'Hora',
        ui_match_datetime=lambda m:m.get('client_schedule_label') or 'Hora pendiente',
        sports_entity_href=lambda kind,identity,label:f'/{kind}/{quote(str(identity))}',
        url_for=lambda endpoint,**kw:BADGE if endpoint=='asset_league_logo' else '/static/'+kw.get('filename',''),
        nemesis_data_confidence=lambda *a:{'tone':'neutral','score':0,'label':'SIMULATED_QA','disclaimer':'SIMULATED_QA'},
        nemesis_attention_priority=lambda *a:{'level':0,'label':'SIMULATED_QA','disclaimer':'SIMULATED_QA'})
    env.filters['sync_madrid_label'] = lambda value: value
    from engines.home_preview import home_preview
    env.filters['home_preview'] = home_preview
    return env


def render(template,data,env=None):
    env=env or component_env('/' if template=='home.html' else '/app')
    return env.get_template(template).render(data=data,current_user=None,
           greeting={'label':'Prueba','name':'SIMULATED_QA'},evidence_origin='SIMULATED_QA')


@pytest.mark.parametrize('template',['home.html','client_app_center.html'])
@pytest.mark.parametrize('state',['LIVE','UPCOMING','FINISHED','EMPTY'])
def test_snapshot_owns_cards_and_counter_even_when_cached_summary_disagrees(template,state):
    data=data_for([] if state=='EMPTY' else [row('current',state)],old_count=0 if state=='LIVE' else 91)
    before=deepcopy(data)
    html=render(template,data)
    expected=1 if state=='LIVE' else 0
    assert f'data-sports-live-confirmed="{expected}"' in html
    assert 'cached-expired' not in html
    if template=='home.html':
        assert ('Partido en directo' in html) is (state=='LIVE')
        assert ('No hay partidos destacados en directo' in html) is (state!='LIVE')
        assert f'{expected} en directo' in html
    if state!='EMPTY':assert 'data-v934-match-id="current"' in html
    assert data==before


@pytest.mark.parametrize('template',['home.html','client_app_center.html'])
def test_live_count_is_total_not_the_bounded_number_of_cards(template):
    data=data_for([row(str(i),'LIVE') for i in range(17)],limit=3)
    assert data['home_matchday']['live']['shown']==3
    assert data['home_matchday']['live']['total']==17
    html=render(template,data)
    assert 'data-sports-live-confirmed="17"' in html
    assert 'data-v934-match-id="16"' not in html


def test_legacy_preview_without_matchday_is_preserved():
    data={'home_summary':{'sports_home':{'live_now':[row('legacy','LIVE')]}},
          'sports_metrics':{'live_confirmed':1}}
    html=render('home.html',data)
    assert 'data-v934-match-id="legacy"' in html and 'Partido en directo' in html


def test_locked_client_home_shows_unknown_counts_instead_of_false_zeroes():
    data = {
        'match_hub': {},
        'home_summary': {'storage_status': 'database_locked', 'sports_home': {}},
        'sports_metrics': {'matches_today': 0, 'matches_available': 0,
                           'live_confirmed': 0, 'picks_ready': 0},
        'v925_calendar': {'storage_status': 'database_locked',
                          'provider_status': 'temporarily_unavailable'},
        'v925_picks': {'picks': []},
    }
    html = render('client_app_center.html', data)

    assert html.count('<strong>—</strong>') == 3


def test_visible_factual_method_and_history_navigation_are_preserved():
    data={'highlight':{'match_label':'QA A vs QA B','safe_url':'https://example.invalid/qa',
                      'can_embed':False},
          'match_context':{'summaries':{'items':[{'text':'Marcador de prueba confirmado.'}]}}}
    html=render('highlight_detail.html',data)
    assert 'href="/historico">Historial</a>' in html
    assert 'Volver a resúmenes' in html
    assert 'data-postmatch-recap-method' in html
    assert '0 llamadas de IA generativa' in html
    assert '0 llamadas externas durante la lectura' in html
    assert 'La reproducción del vídeo es independiente' in html
    assert '<iframe' not in html


@pytest.mark.parametrize('template',['home.html','client_app_center.html'])
@pytest.mark.parametrize('state',['LIVE','UPCOMING','EMPTY'])
def test_flask_templates_keep_home_consistent(app_module,template,state):
    # Actual Jinja globals, filters, shared components and route context.
    from jinja2 import ChoiceLoader, DictLoader
    env=app_module.app.jinja_env.overlay(loader=ChoiceLoader([
        DictLoader({'base.html':'{% block content %}{% endblock %}'}),app_module.app.jinja_env.loader]))
    data=data_for([] if state=='EMPTY' else [row('current',state)])
    with app_module.app.test_request_context('/' if template=='home.html' else '/app'):
        html=render(template,data,env)
    assert 'cached-expired' not in html
    assert f'data-sports-live-confirmed="{1 if state=="LIVE" else 0}"' in html
    if template=='home.html':assert ('Partido en directo' in html) is (state=='LIVE')
    if template=='client_app_center.html' and state=='EMPTY':
        assert 'Todavía no hay pronósticos publicados' in html
        assert 'href="/picks"' in html


@pytest.mark.parametrize('case,expected', [
    ('current', 'PRIORITY'), ('wrong_match', None), ('wrong_state', None),
    ('stale', None), ('conflict', None), ('unrecognized', None),
    ('canonical_has_bucket', 'STANDARD'),
])
def test_featured_priority_preserves_only_same_fixture_current_metadata(case,expected):
    fixture=row('current','UPCOMING')
    if case=='canonical_has_bucket':fixture['sports_relevance_bucket']='STANDARD'
    data=data_for([fixture],old_count=0)
    candidate={**fixture,'home_team':'OLD TEAM LABEL MUST NOT LEAK',
        'home_score':99,'away_score':99,'kickoff_time':'00:00',
        'sports_relevance_bucket':'PRIORITY',
        'sports_relevance':{'bucket':'PRIORITY','is_live':False,'is_upcoming':True,
                           'is_finished':False,'is_stale':False,'status_conflict':False}}
    if case=='wrong_match':candidate['id']='other-match'
    elif case=='wrong_state':candidate['sports_relevance'].update(is_live=True,is_upcoming=False)
    elif case=='stale':candidate['sports_relevance']['is_stale']=True
    elif case=='conflict':candidate['sports_relevance']['status_conflict']=True
    elif case=='unrecognized':candidate['sports_relevance_bucket']='<script>unsafe</script>'
    data['home_summary']['sports_home']['upcoming']=[candidate]
    before=deepcopy(data)
    html=render('home.html',data)
    board=html.split('<aside class="v933-today-board',1)[1].split('</aside>',1)[0]
    assert 'data-v934-match-id="current"' in board
    if expected:assert f'data-sports-relevance="{expected}"' in board
    else:assert 'data-sports-relevance=' not in board
    assert 'OLD TEAM LABEL MUST NOT LEAK' not in html
    assert 'other-match' not in html and 'Partido en directo' not in html
    assert 'unsafe' not in html
    assert data==before


@pytest.fixture(scope='module')
def consistency_browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        executable=os.getenv('NEMESIS_QA_CHROMIUM')
        browser=pw.chromium.launch(headless=True,**({'executable_path':executable} if executable else {}))
        yield browser
        browser.close()


@pytest.mark.parametrize('width',[320,390,1440])
@pytest.mark.parametrize('javascript',[False,True])
@pytest.mark.parametrize('state',['LIVE','UPCOMING','EMPTY'])
def test_browser_coherent_home_with_real_templates_and_css(consistency_browser,width,javascript,state):
    html=render('home.html',data_for([] if state=='EMPTY' else [row('current',state)]))
    css=(ROOT/'static/product-system.css').read_text(encoding='utf-8')
    browser=consistency_browser
    context=browser.new_context(viewport={'width':width,'height':900},java_script_enabled=javascript,service_workers='block')
    page=context.new_page(); calls=[]; errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    context.route('**/*',lambda route:(calls.append(route.request.url),route.abort()))
    try:
        page.set_content('<!doctype html><html lang="es"><head><meta name="viewport" content="width=device-width"><style>'+css+'</style></head><body class="ns-app">'+html+'</body></html>')
        assert page.locator('[data-v934-match-id="cached-expired"]').count()==0
        assert page.locator('[data-sports-live-confirmed]').get_attribute('data-sports-live-confirmed')==('1' if state=='LIVE' else '0')
        title=page.locator('[data-home-featured-title]')
        assert title.is_visible()
        assert (title.inner_text()=='Partido en directo') is (state=='LIVE')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+2')
        assert not errors and not calls
        out=os.getenv('HOME_CONSISTENCY_QA_OUTPUT')
        if out and javascript:
            folder=Path(out);folder.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(folder/f'home-{width}-{state}-SIMULATED_QA.png'),full_page=True)
    finally:
        context.close()
