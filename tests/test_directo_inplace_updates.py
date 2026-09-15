"""SIMULATED_QA: canonical server lease + actual Directo macro and updater.

No Flask imitation and no provider. This covers the existing DOM component and
script in Chromium with an in-memory fetch transport. The separate HTTP tests
cover the full application route. No external hostname/navigation is required.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import html
import json
from pathlib import Path
import shutil
from zoneinfo import ZoneInfo

import pytest
from jinja2 import Environment, FileSystemLoader

from engines.realtime_state_engine import build_realtime_match_state
from engines.v934_realtime_sports_engine import build_realtime_snapshot, normalize_match
from engines.v935_launch_trust_engine import LIVE_STALE_SECONDS, match_status_truth

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 15, 20, 0, tzinfo=ZoneInfo('Europe/Madrid'))


def row(now=NOW, **changes):
    result = dict(id='inplace-qa', match_id='inplace-qa', home_team='Local QA', away_team='Visitante QA',
        competition_name='Liga QA', competition_id='league-qa', source='observed-qa-cache',
        match_date=now.date().isoformat(), kickoff_time='19:00', status='LIVE', minute=67,
        home_score=1, away_score=0, last_synced_at=(now-timedelta(seconds=30)).isoformat())
    result.update(changes)
    return result


def snapshot(now=NOW, rows=None):
    result = build_realtime_snapshot(dict(valid_matches_today=[row(now)] if rows is None else rows), now=now)
    return dict(result, ok=True, scope='matches')


@pytest.mark.parametrize('status,age', [('LIVE', 30), ('HT', 0), ('LIVE', 120), ('LIVE', -20),
    ('FT', 30), ('SUSP',30), ('LIVE',121), ('LIVE', 900), ('LIVE',-900)])
def test_server_deadline_is_derived_from_canonical_live_policy(status, age):
    record = row(status=status, last_synced_at=(NOW-timedelta(seconds=age)).isoformat())
    before = deepcopy(record)
    state = build_realtime_match_state(record, now=NOW)
    truth = match_status_truth(record, now=NOW)
    assert state['is_live'] is truth['is_live']
    if truth['is_live']:
        deadline = datetime.fromisoformat(state['live_valid_until_madrid'])
        observed = datetime.fromisoformat(record['last_synced_at'])
        assert (deadline.astimezone(timezone.utc)-observed.astimezone(timezone.utc)).total_seconds() == LIVE_STALE_SECONDS+1
        assert match_status_truth(record, now=deadline-timedelta(microseconds=1))['is_live'] is True
        assert match_status_truth(record, now=deadline)['is_live'] is False
    else:
        assert state['live_valid_until_madrid'] == ''
    assert before == record


def test_unknown_provider_clock_never_gets_a_browser_live_lease():
    for changes in ({'last_synced_at':None}, {'live_updated_at':'broken'}, {'strProgress':'FT'}):
        state = build_realtime_match_state(row(**changes), now=NOW)
        assert state['live_valid_until_madrid'] == ''
        assert state['is_live'] is False


@pytest.fixture(scope='module')
def chromium():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        # CI uses its installed Playwright browser; sandbox uses system Chromium.
        executable = shutil.which('chromium')
        browser = pw.chromium.launch(**({'executable_path':executable} if executable else {}))
        yield browser
        browser.close()


def document(width=390, initial=None):
    initial = normalize_match(row(), now=NOW) if initial is None else initial
    env = Environment(loader=FileSystemLoader(ROOT/'templates'), autoescape=True)
    env.filters['sync_madrid_label'] = lambda s: s
    env.globals.update(current_user=None, nemesis_source_label=lambda s:s,
        nemesis_data_confidence=lambda *a:dict(level='HIGH', label='Confirmada', score=90, tone='blue'),
        nemesis_attention_priority=lambda *a:dict(level=1, label='Informativo', disclaimer='QA'))
    card = str(env.get_template('components/realtime_live_card.html').module.live_card(initial))
    return f'''<!doctype html><html lang="es"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body><main data-v934-directo="inplace-v1" data-v934-realtime="matches" data-v934-poll="45"
data-directo-lane="live" data-sports-live-confirmed="1" data-directo-evaluated-at="{NOW.isoformat()}">
<nav><a href="/live?f=live&q=Local" aria-current="page">En directo</a></nav>
<a class="v933-kpi" href="/live?f=live"><strong>1</strong><small>Ahora</small></a>
<a class="v933-kpi" href="/live?f=break"><strong>0</strong><small>Pausa</small></a>
<a class="v933-kpi" href="/live?f=finished"><strong>0</strong><small>Hoy</small></a>
<p data-directo-notice role="status" hidden></p><a data-directo-refresh-list href="/live?f=live&q=Local" hidden>Actualizar lista</a>
{card}</main><script src="/static/v934-realtime.js"></script></body></html>'''


@pytest.fixture
def screen(chromium):
    from urllib.parse import urlsplit
    page = chromium.new_page(viewport={'width':390,'height':844})
    page.clock.install(time=NOW)
    transport = {'payload':snapshot(), 'status':200, 'date':NOW, 'calls':[], 'external':[], 'errors':[]}
    page.on('pageerror',lambda e:transport['errors'].append(str(e)))
    page.route('**/*', lambda route: (transport['external'].append(route.request.url), route.abort()))
    page.set_content(document().replace('<script src="/static/v934-realtime.js"></script>', ''))
    page.evaluate("""() => {
      window.qa = {transport: {}, calls: []};
      window.fetch = async function(url, options) {
        qa.calls.push({url:String(url), method:options.method || 'GET', headers:options.headers});
        const t = qa.transport;
        const headers = {'Date':t.date, 'ETag':'"qa-etag"'};
        return new Response(t.status === 304 ? null : JSON.stringify(t.payload),
          {status:t.status, headers:headers});
      };
    }""")
    page._qa_transport = transport
    page.add_script_tag(content=(ROOT/'static/v934-realtime.js').read_text())
    yield page,transport
    assert transport['external']==[]
    assert transport['errors']==[]
    page.close()


def advance(page, ms):
    t=page._qa_transport
    page.evaluate('(v)=>qa.transport=v', {'payload':t['payload'], 'status':t['status'],
        'date':format_datetime(t['date'].astimezone(timezone.utc),usegmt=True)})
    page.clock.run_for(ms)
    page.wait_for_timeout(20)
    t['calls']=page.evaluate('qa.calls.map(c=>({...c,headers:Object.fromEntries(new Headers(c.headers))}))')


def deliver(page, transport, elapsed=45, changes=None, rows=None):
    instant=NOW+timedelta(seconds=elapsed)
    transport.update(payload=snapshot(instant, rows if rows is not None else [row(instant, **(changes or {}))]),
        date=instant,status=200)
    advance(page,45000)


def status(page):
    article=page.locator('[data-canonical-live]')
    return article.get_attribute('data-canonical-status'),article.get_attribute('data-canonical-live')


def test_open_card_updates_in_place_and_preserves_navigation_and_focus(screen):
    page,t=screen
    link=page.locator('a[href="/match/inplace-qa"]');link.focus()
    page.evaluate('window.savedArticle=document.querySelector("[data-canonical-live]")')
    deliver(page,t,changes={'home_score':2,'minute':70})
    assert page.locator('[data-v934-score]').inner_text()=='2 - 0'
    assert page.locator('[data-v934-minute]').inner_text()=='Min 70'
    assert page.evaluate('savedArticle===document.querySelector("[data-canonical-live]")')
    assert link.evaluate('(node)=>node===document.activeElement')
    assert page.url == 'about:blank'
    assert page.locator('[aria-current="page"]').inner_text()=='En directo'
    assert len(t['calls'])==1 and t['calls'][0]['method']=='GET'
    assert status(page)==('LIVE','true')


@pytest.mark.parametrize('changes,expected_score,expected_minute', [
    ({'home_score':0,'away_score':0,'minute':0},'0 - 0','Min 0'),
    ({'home_score':None,'away_score':0,'minute':70},'Resultado pendiente','Min 70'),
    ({'home_score':1,'away_score':1,'minute':'90+4'},'1 - 1','Min 90+4'),
])
def test_zero_partial_and_added_time_are_never_inferred(screen, changes, expected_score, expected_minute):
    page,t=screen;deliver(page,t,changes=changes)
    assert page.locator('[data-v934-score]').inner_text()==expected_score
    assert page.locator('[data-v934-minute]').inner_text()==expected_minute


def test_live_expires_during_network_failure_without_fake_final_or_minute(screen):
    page,t=screen;t['status']=503
    advance(page,93000)
    assert status(page)==('STALE','false')
    assert page.locator('[data-v934-score]').inner_text()=='1 - 0'
    assert page.locator('[data-v934-minute]').is_hidden()
    assert page.locator('.v933-kpi[href="/live?f=live"] strong').inner_text()=='0'
    assert page.locator('[data-v937-confidence-score]').count()==0
    assert 'Datos retrasados' in page.locator('[data-v934-status]').inner_text()
    assert 'Finalizado' not in page.locator('[data-v934-status]').inner_text()


def test_304_response_does_not_renew_the_sports_lease(screen):
    page,t=screen
    advance(page,45000)
    t.update(status=304,date=NOW+timedelta(seconds=90))
    advance(page,48000)
    assert len(t['calls'])==2
    assert t['calls'][1]['headers'].get('if-none-match')=='"qa-etag"'
    assert status(page)==('STALE','false')
    assert page.locator('[data-v934-minute]').is_hidden()


def test_fresh_observation_restores_live_but_duplicate_old_observation_does_not(screen):
    page,t=screen;t['status']=503;advance(page,94000)
    assert status(page)[1]=='false'
    t.update(status=200,date=NOW+timedelta(seconds=140))
    page.locator('main').dispatch_event('v934:refresh');advance(page,45000)
    assert status(page)[1]=='false'
    deliver(page,t,elapsed=185,changes={'home_score':2,'minute':72})
    assert status(page)==('LIVE','true')
    assert page.locator('[data-v934-score]').inner_text()=='2 - 0'


def test_terminal_update_withdraws_live_and_retains_focusable_match_link(screen):
    page,t=screen;page.locator('a[href="/match/inplace-qa"]').focus()
    deliver(page,t,changes={'status':'FT','home_score':2,'minute':90})
    assert status(page)==('FINISHED','false')
    assert page.locator('[data-v934-minute]').is_hidden()
    assert page.locator('[data-directo-filter-match="false"]').count()==1
    assert page.locator('[data-directo-card-notice]').is_visible()
    assert page.locator('.v933-kpi[href="/live?f=live"] strong').inner_text()=='0'
    assert page.locator('.v933-kpi[href="/live?f=finished"] strong').inner_text()=='1'
    assert page.locator('a[href="/match/inplace-qa"]').evaluate('(n)=>n===document.activeElement')
    deliver(page,t,elapsed=90)
    assert status(page)==('FINISHED','false')


def test_missing_record_is_unknown_not_finished_or_zero_score(screen):
    page,t=screen;deliver(page,t,rows=[])
    assert status(page)==('INCOMPLETE','false')
    assert page.locator('[data-v934-score]').inner_text()=='1 - 0'
    assert page.locator('[data-v934-minute]').is_hidden()
    assert 'última lectura' in page.locator('[data-v934-status]').inner_text()


def test_old_response_does_not_regress_a_newer_score(screen):
    page,t=screen;deliver(page,t,elapsed=45,changes={'home_score':2,'minute':70})
    t.update(payload=snapshot(),date=NOW+timedelta(seconds=90))
    advance(page,45000)
    assert page.locator('[data-v934-score]').inner_text()=='2 - 0'
    assert page.locator('[data-v934-minute]').inner_text()=='Min 70'


def test_same_observation_with_changed_score_is_withheld(screen):
    page,t=screen
    deliver(page,t,changes={'home_score':2,'last_synced_at':row()['last_synced_at']})
    assert status(page)==('INCOMPLETE','false')
    assert page.locator('[data-v934-score]').inner_text()=='1 - 0'
    assert 'observación nueva' in page.locator('[data-v934-status]').inner_text()


def test_new_fixture_does_not_replace_identity_or_invent_a_card(screen):
    page,t=screen;instant=NOW+timedelta(seconds=45)
    deliver(page,t,rows=[row(instant),row(instant,id='second-qa',match_id='second-qa',home_team='Other QA')])
    assert page.locator('[data-realtime-consumer]').count()==1
    assert page.locator('[data-directo-refresh-list]').is_visible()
    assert page.locator('[data-directo-refresh-list]').get_attribute('href')=='/live?f=live&q=Local'
    assert page.locator('.v933-kpi[href="/live?f=live"] strong').inner_text()=='2'
    assert page.locator('main').get_attribute('data-directo-visible-live-count')=='1'


@pytest.mark.parametrize('field,value', [('contract','OTHER'),('competition_id','other-league'),('provider','other-source')])
def test_invalid_or_conflicting_identity_cannot_silently_update_the_match(screen,field,value):
    page,t=screen;new=snapshot(NOW+timedelta(seconds=45));new['matches'][0]['realtime_state'][field]=value
    t.update(payload=new,date=NOW+timedelta(seconds=45));advance(page,45000)
    assert status(page)[1]=='false'
    assert page.locator('[data-v934-score]').inner_text()=='1 - 0'


def test_hidden_resume_and_bfcache_cannot_extend_a_lease(screen):
    page,t=screen
    page.evaluate('Object.defineProperty(document,"hidden",{configurable:true,value:true});document.dispatchEvent(new Event("visibilitychange"))')
    advance(page,95000)
    assert len(t['calls'])==0
    assert status(page)==('STALE','false')
    page.evaluate('window.dispatchEvent(new PageTransitionEvent("pagehide",{persisted:true}))')
    advance(page,180000)
    page.evaluate('Object.defineProperty(document,"hidden",{configurable:true,value:false});window.dispatchEvent(new PageTransitionEvent("pageshow",{persisted:true}))')
    assert status(page)==('STALE','false')
    assert len(t['calls'])==0


def test_duplicate_script_does_not_create_duplicate_pollers(screen):
    page,t=screen;page.add_script_tag(content=(ROOT/'static/v934-realtime.js').read_text())
    advance(page,45000)
    assert len(t['calls'])==1


def test_time_does_not_increment_a_sporting_minute(screen):
    page,t=screen;advance(page,30000)
    assert page.locator('[data-v934-minute]').inner_text()=='Min 67'
    assert t['calls']==[]


def test_no_response_does_not_create_overlapping_requests_and_expiry_still_runs(screen):
    page,t=screen
    page.evaluate('''() => {window.fetch=(url, options)=>new Promise((resolve,reject)=>{
      qa.calls.push({url:String(url),method:'GET',headers:options.headers});
      options.signal.addEventListener('abort',()=>reject(new Error('aborted')));
    });}''')
    advance(page,95000)
    assert len(t['calls'])==1  # 45 s request, 12 s timeout, 60 s backoff
    assert status(page)==('STALE','false')


def test_clock_rollback_cannot_add_time_to_live_evidence(screen):
    page,t=screen;t['status']=503
    page.clock.set_system_time(NOW-timedelta(days=1))
    advance(page,94000)
    assert status(page)==('STALE','false')


def test_polling_older_generic_bar_still_uses_the_shared_loader(chromium):
    page=chromium.new_page();page.clock.install(time=NOW)
    page.set_content('''<aside data-v934-realtime="all" data-v934-poll="45">
      <strong data-v934-realtime-title></strong><dd data-v934-count="live"></dd>
      <p data-v934-realtime-message></p></aside>''')
    page.evaluate('''() => {window.calls=0;window.fetch=async()=>{
      calls++;return new Response(JSON.stringify({ok:true,counts:{live:1,matches:1,picks:0},
        matches:[],live:[],picks:[],poll_after_seconds:45}),{status:200});};}''')
    page.add_script_tag(content=(ROOT/'static/v934-realtime.js').read_text())
    page.clock.run_for(55000)
    assert page.locator('[data-v934-count="live"]').inner_text()=='1'
    assert page.locator('[data-v934-realtime-title]').inner_text()=='Actualización en directo'
    assert page.evaluate('calls')==1
    page.close()
