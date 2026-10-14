"""Directo feedback regression: real updater, canonical payloads, offline DOM.

The DOM is a component fixture, not a Flask or production browser session.
No provider/API credentials, network traffic, filesystem DB or mocked test pass.
"""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import html
import json
import os
from pathlib import Path
import re
import shutil
from zoneinfo import ZoneInfo

import pytest
from jinja2 import DictLoader, Environment
from engines.v934_realtime_sports_engine import build_realtime_snapshot

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 10, 21, 0, tzinfo=ZoneInfo('Europe/Madrid'))
MESSAGE = 'Algunas lecturas ya no confirman un directo vigente. No se inventan minutos ni resultados.'


def row(now=NOW, ident='shown-qa', status='LIVE', **changes):
    item = dict(id=ident, match_id=ident, home_team='Local QA', away_team='Visitante QA',
                competition_name='Liga QA', source='observed-qa-cache', competition_id='qa-league',
                match_date=now.date().isoformat(), kickoff_time='20:00', status=status, minute=15,
                home_score=1, away_score=0, last_synced_at=now.isoformat())
    if status == 'NS':
        item.update(kickoff_time='23:55', minute=None, home_score=None, away_score=None)
    item.update(changes)
    return item


def snapshot(rows, now=NOW):
    payload = build_realtime_snapshot({'valid_matches_today': rows}, now=now)
    return dict(payload, ok=True, scope='matches')


def kpi_paths():
    # Read paths from the real production template, not the updater's mapping.
    source = (ROOT/'templates/live.html').read_text()
    calls = [line for line in source.splitlines() if '{{ kpi_card(' in line]
    paths = [re.search(r", '([^']+)'\) }}", line).group(1) for line in calls]
    assert len(paths) == 4
    return dict(zip(('live', 'break', 'finished', 'with_pick'), paths))


def markup(initial, lane='live', legacy=False):
    paths = kpi_paths()
    if legacy:
        paths = {key: '/live?f='+key for key in paths}
    kpis = ''.join(f'<a class="v933-kpi" data-test-kpi="{key}" href="{path}"><strong>1</strong><small>Ahora</small></a>' for key,path in paths.items())
    cards = ''
    for item in initial['matches']:
        state = item['realtime_state']
        cards += f'''<div data-realtime-consumer="directo-v1" data-realtime-state="{html.escape(json.dumps(state), quote=True)}">
<article data-v934-match-card data-v934-match-id="{item['id']}" data-canonical-live="true">
<span data-v934-status><span class="v933-status-chip">En directo</span></span><strong data-v934-score>1 - 0</strong>
<small data-v934-minute>Min 15</small><a href="/match/{item['id']}">Abrir partido</a></article>
<p data-realtime-freshness>Observación registrada · <time></time></p><p data-directo-card-notice hidden></p></div>'''
    return f'''<!doctype html><html lang="es"><head><meta name="viewport" content="width=device-width"></head><body>
<main data-v934-realtime="matches" data-v934-directo="inplace-v1" data-v934-poll="45" data-directo-lane="{lane}"
data-directo-evaluated-at="{initial['generated_at_madrid']}" data-sports-live-confirmed="{initial['counts']['live']}">
{kpis}<p data-directo-notice role="status" hidden></p><a data-directo-refresh-list href="/directo?f={lane}&amp;q=Local" hidden>Actualizar lista</a>{cards}</main></body></html>'''


@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        executable = os.environ.get('NEMESIS_QA_CHROMIUM') or shutil.which('chromium')
        instance = pw.chromium.launch(headless=True, **({'executable_path':executable} if executable else {}))
        yield instance
        instance.close()


@pytest.fixture
def screen(browser):
    contexts = []
    def create(lane='live', rows=None, legacy=False):
        context = browser.new_context(viewport={'width':390,'height':844}, service_workers='block')
        contexts.append(context)
        page = context.new_page()
        errors, requests = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        context.route('**/*', lambda route: (requests.append(route.request.url), route.abort()))
        page.clock.install(time=NOW)
        initial = snapshot([row()] if rows is None else rows)
        page.set_content(markup(initial,lane,legacy))
        page.evaluate('''() => {
          window.qa = {calls:[], transport:{}};
          window.fetch = async (url,options) => {
            qa.calls.push({url:String(url), method:options.method || 'GET',headers:options.headers});
            return new Response(JSON.stringify(qa.transport.payload), {status:200,headers:{Date:qa.transport.date}});
          };
        }''')
        page.add_script_tag(content=(ROOT/'static/v934-realtime.js').read_text())
        page._qa_errors, page._qa_requests = errors, requests
        return page
    yield create
    for context in contexts:
        for page in context.pages:
            assert page._qa_errors == []
            assert page._qa_requests == []
        context.close()


def deliver(page, rows, *, seconds=45, extra=None, advance=45000):
    now = NOW+timedelta(seconds=seconds)
    payload = snapshot(rows,now)
    if extra:
        payload.update(extra)
    page.evaluate('(t)=>qa.transport=t', {'payload':payload, 'date':format_datetime(now.astimezone(timezone.utc),usegmt=True)})
    page.clock.run_for(advance)
    page.wait_for_timeout(20)
    return payload


@pytest.mark.parametrize('legacy',[False,True])
def test_counts_follow_production_links_and_legacy_bookmarks(screen,legacy):
    page=screen(legacy=legacy)
    now=NOW+timedelta(seconds=45)
    page.locator('a[href="/match/shown-qa"]').focus()
    deliver(page,[row(now,status='FT'),row(now,'pause-qa','HT')],extra={'counts':{'live':1,'finished':1,'matches_with_picks':3}})
    for key,value in [('live','1'),('break','1'),('finished','1'),('with_pick','3')]:
        assert page.locator(f'[data-test-kpi="{key}"] strong').inner_text()==value
    assert page.locator('a[href="/match/shown-qa"]').evaluate('el=>el===document.activeElement')
    assert page.locator('[data-canonical-live]').get_attribute('data-canonical-live')=='false'
    assert page.locator('[data-v934-minute]').is_hidden()


@pytest.mark.parametrize('lane,status,expected', [
    ('live','NS',False),('live','FT',False),('live','PST',False),('live','SUSP',False),
    ('live','LIVE',True),('live','HT',True),('break','LIVE',False),('break','HT',True),
    ('finished','LIVE',False),('finished','FT',True),('with_pick','LIVE',False),
])
def test_refresh_notice_only_for_confirmed_candidates_in_lane(screen,lane,status,expected):
    page=screen(lane=lane)
    now=NOW+timedelta(seconds=45)
    deliver(page,[row(now),row(now,'other-qa',status)])
    refresh=page.locator('[data-directo-refresh-list]')
    assert refresh.is_visible() is expected
    assert refresh.get_attribute('href')==f'/directo?f={lane}&q=Local'
    assert page.locator('[data-realtime-consumer]').count()==1
    assert page.evaluate('qa.calls.length')==1
    assert page.evaluate('qa.calls[0].method')=='GET'


def test_browser_expired_candidate_does_not_trigger_false_refresh(screen):
    page=screen(rows=[])
    now=NOW+timedelta(seconds=45)
    # Valid at server projection, expired by the response's conservative HTTP clock.
    candidate=row(now,'old-qa',last_synced_at=(now-timedelta(seconds=120)).isoformat())
    deliver(page,[candidate])
    assert page.locator('main').get_attribute('data-directo-visible-live-count')=='0'
    assert 'Hay partidos fuera' not in page.locator('[data-directo-notice]').inner_text()


def test_delayed_empty_feed_is_not_silent_and_recovers_on_new_observation(screen):
    page=screen(rows=[])
    now=NOW+timedelta(seconds=45)
    deliver(page,[row(now,'old-qa',last_synced_at=(now-timedelta(seconds=121)).isoformat())])
    assert page.locator('[data-directo-notice]').inner_text()==MESSAGE
    assert page.locator('[data-directo-notice]').is_visible()
    assert page.locator('[data-directo-refresh-list]').is_hidden()
    assert page.locator('[data-canonical-live="true"]').count()==0
    later=NOW+timedelta(seconds=225)
    deliver(page,[row(later,'new-qa')],seconds=225,advance=180000)
    assert page.locator('main').get_attribute('data-directo-delayed')=='false'
    assert page.locator('[data-directo-refresh-list]').is_visible()
    assert page.locator('[data-realtime-consumer]').count()==0  # no invented DOM replacement
    assert page.evaluate('qa.calls.length')==2  # original 45/180-second schedule preserved


def test_empty_confirmed_feed_removes_previous_delay_notice(screen):
    page=screen(rows=[])
    deliver(page,[],extra={'realtime_live_status':'stale','counts':{'live':0,'stale_live':2}})
    assert page.locator('[data-directo-notice]').is_visible()
    deliver(page,[],seconds=225,advance=180000)
    assert page.locator('[data-directo-notice]').is_hidden()


@pytest.mark.parametrize('count',[0,-1,'2',True,None])
def test_unproven_delayed_counts_do_not_claim_a_delay(screen,count):
    page=screen(rows=[])
    deliver(page,[],extra={'realtime_live_status':'stale','counts':{'live':0,'stale_live':count}})
    assert page.locator('main').get_attribute('data-directo-delayed')=='false'


def test_invalid_candidate_does_not_announce_new_matches(screen):
    page=screen(rows=[])
    payload=snapshot([row(NOW+timedelta(seconds=45),'bad-qa')],NOW+timedelta(seconds=45))
    payload['matches'][0]['realtime_state']['contract']='INVALID'
    deliver(page,[],extra=payload)
    assert page.locator('[data-directo-refresh-list]').is_hidden()
    assert page.locator('[data-test-kpi="live"] strong').inner_text()=='—'


def test_expiry_updates_visible_canonical_counts_without_more_requests(screen):
    page=screen()
    page.evaluate('Object.defineProperty(document,"hidden",{value:true,configurable:true})')
    page.clock.run_for(122000)
    assert page.locator('[data-test-kpi="live"] strong').inner_text()=='0'
    assert page.locator('[data-canonical-live]').get_attribute('data-canonical-live')=='false'
    assert page.locator('[data-v934-minute]').is_hidden()
    assert page.evaluate('qa.calls.length')==0


@pytest.mark.parametrize('delayed,historical',[(False,False),(True,False),(True,True)])
def test_delayed_notice_is_server_rendered_even_without_javascript(delayed,historical):
    from types import SimpleNamespace
    macros='{% macro page_header(a,b,c,d) %}{% endmacro %}{% macro kpi_card(a,b,c,d,e,f) %}{% endmacro %}{% macro section_header(a,b,c,d,e) %}{% endmacro %}{% macro match_card(a) %}{% endmacro %}{% macro filter_tabs(a,b) %}{% endmacro %}{% macro empty_state(a,b,c,d,e) %}{{ a }}{% endmacro %}{% macro sports_contract_attributes(a) %}{% endmacro %}'
    env=Environment(loader=DictLoader({'base.html':'{% block content %}{% endblock %}',
        'live.html':(ROOT/'templates/live.html').read_text(), 'components/v933_ui.html':macros,
        'components/realtime_live_card.html':'{% macro live_card(a) %}{% endmacro %}'}),autoescape=True)
    surface=SimpleNamespace(lane='finished' if historical else 'live',matches=[],historical=historical,contract='QA')
    markup=env.get_template('live.html').render(data={'v934_realtime':{'realtime_live_status':'stale' if delayed else 'no_live_events'}},
        client_live_surface=lambda *_:surface, ui=lambda value:value,
        request=SimpleNamespace(args={},full_path='/directo'))
    assert (MESSAGE in markup) is (delayed and not historical)
    assert 'data-canonical-live="true"' not in markup


def test_updated_script_has_new_cache_identity_without_reverting_css():
    source=(ROOT/'templates/base.html').read_text()
    line=next(line for line in source.splitlines() if "filename='v934-realtime.js'" in line)
    assert 'directo-inplace-1-feedback-2' in line
    assert 'canonical-core-4-home-leagues' in source


def test_pick_filtered_card_leaves_filter_when_no_longer_live(screen):
    page=screen(lane='with_pick')
    deliver(page,[row(NOW+timedelta(seconds=45),status='FT')])
    assert page.locator('[data-realtime-consumer]').get_attribute('data-directo-filter-match')=='false'
    assert page.locator('[data-directo-card-notice]').is_visible()
    assert page.locator('[data-v934-minute]').is_hidden()


def test_duplicate_script_keeps_one_poll_and_one_card(screen):
    page=screen()
    page.add_script_tag(content=(ROOT/'static/v934-realtime.js').read_text())
    deliver(page,[row(NOW+timedelta(seconds=45))])
    assert page.evaluate('qa.calls.length')==1
    assert page.locator('[data-realtime-consumer]').count()==1
