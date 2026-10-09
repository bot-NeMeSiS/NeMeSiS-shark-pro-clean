"""Complete rendered calendar, synthetic rows and intercepted GET navigation."""
from datetime import date, timedelta
from pathlib import Path
import mimetypes
import re
from urllib.parse import parse_qs, urlsplit, urlencode

import pytest
from test_app_navigation_browser import browser

ROOT=Path(__file__).resolve().parents[1]


def sample(app_module):
    day=app_module.today_iso(1)
    rows=[]
    for league in ('Liga Azul QA','Liga Verde QA'):
        for index, hour in enumerate(('18:30','21:00','14:00','16:15')):
            rows.append({'id':f'{league[5:9]}-{index}','match_id':f'{league[5:9]}-{index}',
                'match_date':day,'kickoff_time':hour,'home_team':f'Club {index}',
                'away_team':'Visitante QA','competition_name':league,'country':'España',
                'source':'fixture-test','v935_lifecycle':'UPCOMING'})
    return day,{'all_valid_matches':rows,'valid_upcoming_matches':rows,'valid_matches_available':rows,
        'valid_matches_today':[],'valid_live_events':[],'finished_matches':[],
        'valid_active_picks':[],'incident_matches':[],'incomplete_matches':[]}


@pytest.mark.parametrize('width',[320,1440])
@pytest.mark.parametrize('language',['es','en','fr'])
@pytest.mark.parametrize('javascript',[True,False])
def test_calendar_order_context_and_get_continuity(browser,app_module,width,language,javascript,tmp_path):
    from flask import render_template
    day,summary=sample(app_module)
    context=browser.new_context(viewport={'width':width,'height':900},java_script_enabled=javascript,
                                locale=language,reduced_motion='reduce',service_workers='block')
    page=context.new_page();calls=[];errors=[]
    page.set_default_timeout(10000)
    page.on('pageerror',lambda exc:errors.append(str(exc)))
    def serve(route):
        url=urlsplit(route.request.url); calls.append((route.request.method,url.path))
        if url.netloc!='calendar.invalid':route.abort();return
        if url.path in ('/calendar','/calendario'):
            with app_module.app.test_request_context(url.path+'?'+url.query,headers={'Accept-Language':language}):
                cal=app_module.v940_calendar_context(summary,app_module.request.args.get('lane','today'))
                html=render_template('calendar.html',data={'calendar':cal,'v925_calendar':{'has_real_data':True}},current_user=None)
            html=re.sub(r'<script\b([^>]*)>.*?</script>',lambda m:m.group(0) if any(
                name in m[1] for name in ('application/json','v940-calendar.js','ui-localization.js','v930-icons.js')) else '',html,flags=re.S|re.I)
            route.fulfill(status=200,content_type='text/html; charset=utf-8',body=html);return
        asset=(ROOT/url.path.lstrip('/')).resolve()
        if url.path.startswith('/static/') and asset.is_relative_to(ROOT/'static') and asset.is_file():
            route.fulfill(status=200,content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream',body=asset.read_bytes());return
        route.fulfill(status=200,content_type='text/html',body='<p>SIMULATED_QA destination</p>')
    page.route('**/*',serve)
    try:
        page.goto('https://calendar.invalid/calendario?'+urlencode({'date':day,'q':'Club'}))
        global_context=page.locator('[data-v940-current-context]')
        before=global_context.inner_text()
        assert 'Liga Azul' not in before and 'Liga Verde' not in before
        assert page.locator('.v940-calendar-totals').inner_text().startswith('8')
        assert '2' in page.locator('.v940-calendar-totals').inner_text()
        assert page.locator('.v940-calendar-advanced').get_attribute('open') is None
        assert page.locator('[data-results-calendar-tabs] a[href="/directo"]').count()==1
        assert '-calendar-context-2' in page.locator('script[src*="v940-calendar.js"]').get_attribute('src')
        sort=page.locator('select[name=sort]'); assert sort.count()==1 and sort.is_visible()
        assert sort.bounding_box()['height']>=44-0.001
        sort.select_option('time')
        if javascript:assert page.locator('[data-v940-pending-filters]').is_visible()
        submit=page.locator('[data-v940-discovery-form] button[type=submit]')
        submit.focus();page.keyboard.press('Enter');page.wait_for_url('**/*sort=time*')
        assert parse_qs(urlsplit(page.url).query)['q']==['Club']
        groups=page.locator('[data-v940-calendar-section="league"]')
        assert groups.count()==2
        for group in groups.all():
            assert [n.get_attribute('data-v934-match-id')[-1] for n in group.locator('[data-v934-match-id]').all()]==['2','3','0','1']
        # Scroll position must never rewrite the selected collection title.
        before=page.locator('[data-v940-current-context]').inner_text()
        groups.last.locator('a[href^="/match/"]').last.focus()
        assert page.locator('[data-v940-current-context]').inner_text()==before
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        if language=='es' and javascript:
            page.evaluate('scrollTo(0,0)')
            page.screenshot(path=str(tmp_path/f'calendar-clarity-{width}.png'),full_page=True)
            page.screenshot(path=str(tmp_path/f'calendar-clarity-{width}-viewport.png'))
        results=page.locator('[data-results-calendar-tabs] a[href*="lane=finished"]')
        results.focus();page.keyboard.press('Enter');page.wait_for_url('**/*lane=finished*')
        args=parse_qs(urlsplit(page.url).query)
        assert args['date']==[day] and args['q']==['Club'] and args['sort']==['time']
        next_day=page.locator('.v933-calendar-date-navigation > a').last
        if not next_day.is_visible():
            picker=page.locator('.v933-calendar-date-picker > summary')
            picker.focus();page.keyboard.press('Enter')
            next_day=page.locator('.v933-calendar-date-form > a').last
        assert next_day.is_visible()
        next_day.focus();page.keyboard.press('Enter')
        expected=(date.fromisoformat(day)+timedelta(days=1)).isoformat()
        page.wait_for_url('**/*date='+expected+'*')
        args=parse_qs(urlsplit(page.url).query)
        assert args['lane']==['finished'] and args['q']==['Club'] and args['sort']==['time']
        assert all(method=='GET' and not path.startswith('/api/') for method,path in calls)
        assert not errors
    finally:context.close()
