"""Synthetic calendar components with real template, CSS and served calendar script."""
import pytest
from test_calendar_discovery_release_browser import browser, mount, history_simulation, VALID


@pytest.mark.parametrize('width',[320,390,768,1440])
@pytest.mark.parametrize('javascript',[True,False])
def test_leagues_are_compact_native_keyboard_operable_and_multi_open(browser,app_module,width,javascript,tmp_path):
    leagues=[dict(key=str(i),anchor_id='league-'+str(i),label='Liga QA '+str(i),matches=[
        dict(id='fixture-'+str(i),home_team='Club local QA',away_team='Club visitante QA')]) for i in range(3)]
    days=[dict(date='2026-10-26',anchor_id='qa-day',matches_count=3,
               league_sections=[dict(key='es',kind='country',label='España',count=3,leagues=leagues)])]
    page,calls,errors=mount(browser,app_module,width=width,run_script=javascript,day_groups=days)
    try:
        groups=page.locator('details.v940-calendar-league')
        assert groups.count()==3
        assert page.locator('details.v940-calendar-league[open]').count()==0
        assert page.locator('.v940-calendar-league .v933-match-card:visible').count()==0
        assert page.locator('[data-v940-calendar-search]').is_visible()
        first=groups.nth(0).locator(':scope > summary')
        first.focus();page.keyboard.press('Enter')
        assert groups.nth(0).get_attribute('open') is not None
        groups.nth(1).locator(':scope > summary').click()
        assert page.locator('details.v940-calendar-league[open]').count()==2
        first.click()
        assert groups.nth(0).get_attribute('open') is None
        assert groups.nth(1).get_attribute('open') is not None
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
        page.screenshot(path=str(tmp_path/('organization-'+str(width)+'-'+str(javascript)+'.png')),full_page=True)
        assert not errors
        assert not any('api/' in url for url in calls)
    finally:
        page.close()


def test_back_restore_reopens_only_current_response_groups_and_no_private_content(browser,app_module):
    leagues=[dict(key=str(i),anchor_id='league-'+str(i),label='Liga QA '+str(i),matches=[]) for i in range(3)]
    days=[dict(date='2026-10-26',anchor_id='qa-day',league_sections=[
        dict(key='es',kind='country',label='España',count=3,leagues=leagues)])]
    state=dict(VALID,openLeagues=['league-1','unknown-old-group',None,{'private':'discarded'}])
    page,_,errors=mount(browser,app_module,day_groups=days,before=history_simulation(state))
    try:
        page.evaluate('window.qaFlush()')
        assert page.locator('details.v940-calendar-league[open]').count()==1
        assert page.locator('#league-1').get_attribute('open') is not None
        assert page.locator('#league-0').get_attribute('open') is None
        assert not errors
    finally:
        page.close()


def test_live_group_label_follows_existing_card_observation_without_network(browser,app_module):
    league=dict(key='live',anchor_id='live-qa',label='Liga QA',matches=[
        dict(id='live-fixture',home_team='QA Local',away_team='QA Visitante',
             status_info={'is_live':True,'key':'LIVE'})])
    days=[dict(date='2026-10-26',anchor_id='qa-day',league_sections=[
        dict(key='es',kind='country',label='España',count=1,leagues=[league])])]
    page,calls,errors=mount(browser,app_module,day_groups=days)
    try:
        label=page.locator('[data-league-live-count]')
        assert label.is_visible() and label.inner_text()=='1 en directo'
        page.locator('[data-v934-match-card]').evaluate('(card)=>card.setAttribute("data-canonical-live","false")')
        page.wait_for_function('document.querySelector("[data-league-live-count]").hidden')
        assert label.get_attribute('data-league-live-count')=='0'
        assert not errors
        assert not any('/api/' in url for url in calls)
    finally:
        page.close()


@pytest.mark.parametrize('width',[390,1440])
def test_native_back_preserves_query_and_deliberate_group_state(browser,app_module,width):
    # Actual browser navigation/history with synthetic GET responses, not production.
    import mimetypes
    from pathlib import Path
    from urllib.parse import urlsplit
    from test_calendar_discovery_release import render_calendar
    root=Path(__file__).resolve().parents[1]
    leagues=[dict(key=str(i),anchor_id='league-'+str(i),label='Liga QA '+str(i),matches=[
        dict(id='fixture-'+str(i),home_team='QA Local',away_team='QA Visitante',
             competition_name='Liga QA',source='SIMULATED_QA',kickoff_time='18:00')]) for i in range(2)]
    days=[dict(date='2026-10-26',anchor_id='qa-day',league_sections=[
        dict(key='es',kind='country',label='España',count=2,leagues=leagues)])]
    context=browser.new_context(viewport={'width':width,'height':900},service_workers='block')
    page=context.new_page();calls=[];errors=[]
    page.on('pageerror',lambda exc:errors.append(str(exc)))
    def serve(route):
        url=urlsplit(route.request.url);calls.append((route.request.method,url.path))
        if url.netloc!='continuity.invalid':route.abort();return
        if url.path=='/calendario':
            html,_=render_calendar(app_module,'?'+url.query,day_groups=days)
            route.fulfill(status=200,content_type='text/html',body='<!doctype html><html lang="es">'+html+'</html>');return
        if url.path.startswith('/match/'):
            route.fulfill(status=200,content_type='text/html',body='<h1>SIMULATED_QA fixture</h1>');return
        path=(root/url.path.lstrip('/')).resolve()
        if url.path.startswith('/static/') and path.is_relative_to(root/'static') and path.is_file():
            route.fulfill(status=200,content_type=mimetypes.guess_type(str(path))[0] or 'application/octet-stream',body=path.read_bytes());return
        route.abort()
    context.route('**/*',serve)
    try:
        url='https://continuity.invalid/calendario?lane=week&date=2026-10-26&sort=time'
        page.goto(url,wait_until='networkidle')
        page.locator('#league-1 > summary').click()
        page.locator('#league-1 a[href="/match/fixture-1"]').click()
        page.wait_for_url('**/match/fixture-1')
        page.go_back(wait_until='networkidle')
        assert page.url==url
        assert page.locator('#league-1').get_attribute('open') is not None
        assert page.locator('#league-0').get_attribute('open') is None
        assert not errors
        assert all(method=='GET' and not path.startswith('/api/') for method,path in calls)
    finally:
        context.close()
