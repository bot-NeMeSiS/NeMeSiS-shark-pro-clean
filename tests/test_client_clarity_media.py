"""Client navigation/media regression. Synthetic catalogue and isolated templates only."""
from copy import deepcopy
from contextlib import closing
from pathlib import Path
import os
import sqlite3
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, ChoiceLoader, DictLoader, select_autoescape
import pytest
from engines.app_navigation import navigation_matches
from engines.ui_localization_engine import translate
from engines.sportsdb_highlights_engine import ensure_sportsdb_highlights_schema
from engines.highlight_read_model import read_highlights_for_match, read_highlights_map, read_highlights_summary

ROOT = Path(__file__).resolve().parents[1]


def env():
    e=Environment(loader=ChoiceLoader([DictLoader({'base.html':'{% block content %}{% endblock %}',
        'partials/brand_logo.html':'{% macro nemesis_brand(href, zone, compact=false) %}<a href="{{ href }}">NeMeSiS QA</a>{% endmacro %}'}), FileSystemLoader(ROOT/'templates')]),autoescape=select_autoescape(['html']))
    e.globals.update(ui=lambda s,**kw:translate(s,'es',**kw), ui_owned=lambda s:s,
        navigation_matches=navigation_matches,
        url_for=lambda endpoint,**kw:'/static/'+kw.get('filename',''),
        request=SimpleNamespace(path='/live'), ui_locale='es')
    e.filters['match_madrid_context']=lambda row:row
    e.filters['sync_madrid_label']=lambda value:value
    return e


@pytest.fixture
def catalogue(tmp_path,monkeypatch):
    def deny(*a,**kw):raise AssertionError('EXTERNAL_NETWORK_FORBIDDEN')
    monkeypatch.setattr('urllib.request.urlopen',deny)
    path=tmp_path/'synthetic.sqlite'
    ensure_sportsdb_highlights_schema(path)
    return path


def add(path,index,rights='UNKNOWN_RIGHTS',match='m1'):
    with closing(sqlite3.connect(path)) as conn:
        conn.execute('''INSERT INTO sportsdb_match_highlights
            (id,match_id,video_url,rights_status,commercial_use_status,source,updated_at)
            VALUES(?,?,?,?,?,?,?)''',(f'h{index:04}',match,'https://www.youtube.com/watch?v=SIMULATED_QA',
                rights,'ALLOWED' if rights=='LICENSED' else 'UNKNOWN','Synthetic QA',f'{index:04}'))
        conn.commit()


def test_older_authorized_video_survives_recent_unreviewed_rows(catalogue):
    add(catalogue,0,'LICENSED')
    for i in range(1,12):add(catalogue,i)
    before=catalogue.read_bytes()
    detail=read_highlights_for_match(catalogue,'m1')
    badge=read_highlights_map(catalogue,['m1'])
    assert detail['read_state']=='VERIFIED'
    assert [h['id'] for h in detail['highlights']]==['h0000']
    assert detail['highlights'][0]['id']==badge['map']['m1'][0]['id']
    assert catalogue.read_bytes()==before
    assert detail['candidate_sampled']==12
    assert detail['playback_verified'] is False


@pytest.mark.parametrize('rights',['UNKNOWN_RIGHTS','BLOCKED','REVIEW_REQUIRED'])
def test_scanning_more_rows_does_not_authorize_them(catalogue,rights):
    for i in range(14):add(catalogue,i,rights)
    assert read_highlights_for_match(catalogue,'m1')['highlights']==[]


def test_limit_is_for_authorized_display_not_raw_candidates(catalogue):
    for i in range(35):add(catalogue,i,'LICENSED' if i%2==0 else 'UNKNOWN_RIGHTS')
    r=read_highlights_for_match(catalogue,'m1')
    assert len(r['highlights'])==8
    assert all(h['rights_status']=='LICENSED' for h in r['highlights'])
    assert r['sample_limit']==8


def test_scan_limit_does_not_misreport_catalogue_as_empty(catalogue):
    add(catalogue,0,'LICENSED')
    for i in range(1,252):add(catalogue,i)
    r=read_highlights_for_match(catalogue,'m1')
    assert r['ok'] is False and r['read_state']=='READ_LIMIT_REACHED'
    assert r['candidate_sample_truncated'] is True
    assert r['rights_warnings'] is None
    assert r['candidate_sampled']==250


def test_summary_keeps_bounded_sample_without_other_match_leak(catalogue):
    for i in range(32):add(catalogue,i,'LICENSED',match='other')
    assert len(read_highlights_summary(catalogue)['latest_highlights'])==8
    assert read_highlights_for_match(catalogue,'m1')['highlights']==[]


@pytest.mark.parametrize('scope,path,expected',[
    ('public','/live','/directo'),('public','/directo','/directo'),
    ('public','/historico','/historico'),('public','/track-record','/historico'),
    ('public','/resumenes','/calendario?lane=finished'),
    ('public','/resumen/h1','/calendario?lane=finished'),
    ('client','/live','/calendario?lane=today'),
    ('client','/track-record','/picks'),('client','/combinadas','/picks'),
    ('client','/notificaciones','/mi-cuenta'),('client','/actividad','/mi-cuenta'),
])
def test_only_the_correct_main_section_is_active(scope,path,expected):
    m=env().get_template('components/navigation_contracts.html').module
    entries=m.PUBLIC_LINKS if scope=='public' else m.CLIENT_LINKS
    active=[href for _,href,_ in entries if str(m.is_active(href,path,scope)).strip()]
    assert active==[expected]


def test_client_visible_navigation_uses_same_pronostico_label():
    m=env().get_template('components/v933_navigation.html').module
    text=str(m.v933_client_navigation())
    assert '>Pronósticos</span>' in text and '>Picks</span>' not in text
    assert '/picks' in text and 'data-keep-internal-term' not in text


@pytest.mark.parametrize('query',['highlights','vídeos','resúmenes','goles'])
def test_directory_finds_videos_by_common_names_without_javascript(query):
    from html.parser import HTMLParser
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.visible=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='a' and 'data-explore-item' in a and 'hidden' not in a:self.visible.append(a['href'])
    m=env().get_template('components/app_navigation.html').module
    p=Links();p.feed(str(m.navigation_content('client',True,query)))
    assert p.visible==['/resumenes']


def test_directory_groups_sport_and_analysis_without_admin_leak():
    m=env().get_template('components/navigation_contracts.html').module
    assert '/resumenes' in [item[1] for item in m.DISCOVERY_SPORTS]
    assert '/picks' not in [item[1] for item in m.DISCOVERY_SPORTS]
    assert '/picks' in [item[1] for item in m.DISCOVERY_ANALYSIS]
    html=str(env().get_template('components/app_navigation.html').module.navigation_content('public',True,''))
    assert '>Deporte</h3>' in html and '>Análisis</h3>' in html
    assert 'href="/admin/' not in html and 'href="/mi-cuenta"' not in html


def page_data(status='VERIFIED',available=None):
    return {'v766_highlights':{'status':status},'v769_highlights_center':{
        'status':status,'read_state':status,'read_ok':status=='VERIFIED',
        'pending_read_state':'READ_UNAVAILABLE','available':available or [],'pending_matches':[]}}


@pytest.mark.parametrize('status,state',[('DISABLED_BY_ADMIN','paused'),('READ_UNAVAILABLE','unavailable'),
    ('NO_DATABASE','unavailable'),('CATALOGUE_NOT_INITIALIZED','unavailable'),('UNRECOGNIZED_ERROR','unavailable'),('VERIFIED','empty')])
def test_media_page_has_honest_distinct_states(status,state):
    html=env().get_template('highlights.html').render(data=page_data(status))
    assert f'data-highlights-state="{state}"' in html
    assert 'None' not in html and 'data-highlights-pending' not in html
    assert '<iframe' not in html
    if state=='unavailable':assert 'Todavía no hay vídeos listos' not in html


def videos():
    return [{'id':str(i),'match_label':f'QA Equipo {i} vs QA Rival','event_date_label':'10/10/2026',
        'source_label':'SIMULATED_QA','competition_label':league,'detail_url':f'/resumen/{i}',
        'match_url':f'/match/{i}','can_embed':i==0,'thumbnail_url':''}
        for i,league in enumerate(['Liga B','Liga A','Liga B'])]


def test_media_groups_and_labels_without_invented_players():
    data=page_data(available=videos());before=deepcopy(data)
    html=env().get_template('highlights.html').render(data=data)
    assert html.count('data-highlight-league=')==2
    assert html.index('data-highlight-id="0"') < html.index('data-highlight-id="2"')
    assert 'data-highlights-state="available"' in html
    assert '<iframe' not in html and 'plataforma original' in html
    assert data==before


@pytest.mark.parametrize('embed',[False,True])
def test_detail_external_fallback_and_back_link_are_available_without_js(embed):
    h={'match_label':'QA A vs QA B','title':'QA','safe_url':'https://www.youtube.com/watch?v=SIMULATED_QA',
       'can_embed':embed,'embed_url':'https://www.youtube-nocookie.com/embed/SIMULATED_QA'}
    html=env().get_template('highlight_detail.html').render(data={'highlight':h})
    assert 'Volver a resúmenes' in html and 'Abrir fuente' in html
    assert 'rel="noopener noreferrer"' in html and '<iframe' not in html
    assert ('data-video-activate=' in html) is embed
    assert ('<noscript>' in html) is embed


@pytest.mark.parametrize('width',[320,390,1440])
def test_browser_real_templates_and_css_are_readable_offline(width,tmp_path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=os.getenv('NEMESIS_QA_CHROMIUM') or pw.chromium.executable_path)
        context=browser.new_context(viewport={'width':width,'height':844},service_workers='block')
        page=context.new_page();calls=[]
        page.route('**/*',lambda route:(calls.append(route.request.url),route.abort()))
        try:
            for name,body in [('videos',env().get_template('highlights.html').render(data=page_data(available=videos()))),
                 ('menu',str(env().get_template('components/app_navigation.html').module.navigation_content('client',True,'')))]:
                css=(ROOT/'static/product-system.css').read_text()+'\n'+(ROOT/'static/app-navigation.css').read_text()
                page.set_content('<!doctype html><html><head><meta name="viewport" content="width=device-width"><style>'+css+'</style></head><body class="ns-app">'+body+'</body></html>')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+2')
                if name=='menu':
                    page.add_script_tag(content=(ROOT/'static/app-navigation.js').read_text())
                    page.locator('[data-explore-query]').fill('highlights')
                    assert page.locator('[data-explore-item]:visible').count()==1
                    assert page.locator('[data-explore-item]:visible').get_attribute('href')=='/resumenes'
                else:
                    assert page.locator('[data-highlight-league]').count()==2
                    assert page.locator('[data-highlight-id]').count()==3
                output=os.environ.get('CLIENT_CLARITY_QA_OUTPUT')
                if output:
                    folder=Path(output);folder.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(folder/f'{name}-{width}-SIMULATED_QA.png'),full_page=True)
            assert calls==[]
        finally:context.close();browser.close()
