"""Complete rendered calendar, synthetic rows and intercepted GET navigation."""
from datetime import date, timedelta
from pathlib import Path
import mimetypes
import re
from urllib.parse import parse_qs, urlsplit, urlencode

import pytest
from test_app_navigation_browser import browser

ROOT=Path(__file__).resolve().parents[1]


def wait_for_calendar_paint(page, javascript):
    if javascript:
        page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    else:
        # Page.evaluate is unavailable when the no-JavaScript variant is under test.
        page.wait_for_timeout(50)


def render_calendar_card(page, card, javascript):
    """Wait for content-visibility:auto cards to render after entering the viewport."""
    viewport_height=page.viewport_size['height']
    for _ in range(12):
        box=card.bounding_box()
        assert box is not None
        if box['y']>=0 and box['y']+box['height']<=viewport_height:
            break
        delta=box['y']+box['height']/2-viewport_height/2
        page.mouse.wheel(0,max(-viewport_height*.8,min(viewport_height*.8,delta)))
        page.wait_for_timeout(50)
    else:
        raise AssertionError(f'Calendar card did not enter viewport: {card.bounding_box()}')
    wait_for_calendar_paint(page,javascript)


def sample(app_module):
    day=app_module.today_iso(1)
    rows=[]
    for league in ('Liga Azul QA','Liga Verde QA'):
        for index, hour in enumerate(('18:30','21:00','14:00','16:15')):
            rows.append({'id':f'{league[5:9]}-{index}','match_id':f'{league[5:9]}-{index}',
                'match_date':day,'kickoff_time':hour,'home_team':f'Club {index}',
                'away_team':'Visitante QA','competition_name':league,'country':'España',
                'source':'fixture-test','v935_lifecycle':'UPCOMING',
                'home_score':'','away_score':''})
    return day,{'all_valid_matches':rows,'valid_upcoming_matches':rows,'valid_matches_available':rows,
        'valid_matches_today':[],'valid_live_events':[],'finished_matches':[],
        'valid_active_picks':[],'incident_matches':[],'incomplete_matches':[]}


@pytest.mark.parametrize('width',[320,390,1440])
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
        assert page.locator('.v940-calendar-layer-state').count()==1
        density=page.locator('.v940-calendar-layer-state').evaluate("el=>({display:getComputedStyle(el).display,wrap:getComputedStyle(el.querySelector('.v940-calendar-active-filters')).flexWrap,helper:getComputedStyle(document.querySelector('.v940-calendar-sort small')).display,overflow:el.querySelector('.v940-calendar-active-filters').scrollWidth>el.querySelector('.v940-calendar-active-filters').clientWidth})")
        if width<=480:
            assert density['display']=='flex'
            assert density['wrap']=='nowrap'
            assert density['helper']=='none'
            if width==320:
                assert density['overflow']
        assert page.locator('[data-results-calendar-tabs] a[href="/directo"]').count()==1
        assert '-calendar-context-2' in page.locator('script[src*="v940-calendar.js"]').get_attribute('src')
        sort=page.locator('select[name=sort]'); assert sort.count()==1 and sort.is_visible()
        assert sort.bounding_box()['height']>=44-0.001
        sort.select_option('time')
        if javascript:assert page.locator('[data-v940-pending-filters]').is_visible()
        submit=page.locator('[data-v940-discovery-form] button[type=submit]')
        submit.focus();page.keyboard.press('Enter');page.wait_for_url('**/*sort=time*',wait_until='domcontentloaded')
        assert parse_qs(urlsplit(page.url).query)['q']==['Club']
        groups=page.locator('[data-v940-calendar-section="league"]')
        assert groups.count()==2
        for group in groups.all():
            assert [n.get_attribute('data-v934-match-id')[-1] for n in group.locator('[data-v934-match-id]').all()]==['2','3','0','1']
        cards=page.locator('.v933-calendar-day .v933-match-card:not(.is-incomplete)')
        assert cards.count()==8
        compact_card=cards.first
        render_calendar_card(page,compact_card,javascript)
        assert page.locator('link[href*="sports-match-density.css"]').count()==1
        assert compact_card.locator('.v933-match-card-header').evaluate('(el)=>getComputedStyle(el).display')=='none'
        assert compact_card.locator('[data-match-kickoff-clock]').is_visible()
        if width<=760:
            max_height=110
            geometry=compact_card.evaluate("el=>({height:el.getBoundingClientRect().height,rows:getComputedStyle(el).gridTemplateRows,teams:el.querySelector('.v933-match-teams').getBoundingClientRect().height})")
            assert geometry['height']<=max_height, geometry
            assert len(compact_card.locator('.v933-match-teams').evaluate('(el)=>getComputedStyle(el).gridTemplateColumns.split(" ")'))==3
            allocations=[]
            for card in cards.all():
                render_calendar_card(page,card,javascript)
                rendered_text=card.inner_text()
                assert 'Club ' in rendered_text and 'Visitante QA' in rendered_text, rendered_text
                assert card.locator('a[href^="/match/"]').count()==1
                allocation=card.evaluate("el=>{const rows=getComputedStyle(el).gridTemplateRows.split(' ').map(parseFloat);return {rows,teams:el.querySelector('.v933-match-teams').getBoundingClientRect().height,footer:el.querySelector('.v933-match-card-footer').getBoundingClientRect().height}}")
                allocations.append(allocation)
            assert all(len(item['rows'])==2 and item['rows'][0]+1>=item['teams'] and item['rows'][1]+1>=item['footer'] for item in allocations), allocations
            render_calendar_card(page,compact_card,javascript)
            before=geometry['height']
            compact_card.evaluate("el=>{el.querySelector('[data-match-kickoff-clock]')?.remove();el.querySelector('[data-match-kickoff-zone]')?.remove()}")
            wait_for_calendar_paint(page,javascript)
            without_optional_clock=compact_card.evaluate("el=>({height:el.getBoundingClientRect().height,teams:el.querySelector('.v933-match-teams').getBoundingClientRect().height})")
            if width>=390:
                assert before-without_optional_clock['height']>=10
                assert without_optional_clock['teams']<42
            else:
                assert without_optional_clock['height']<=before
        else:
            assert compact_card.bounding_box()['height']<=84
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
