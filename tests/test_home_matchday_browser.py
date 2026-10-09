"""Synthetic Home in Chromium: visible agenda, real styles and GET navigation."""
from datetime import datetime
import mimetypes
from pathlib import Path
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import pytest
from test_app_navigation_browser import browser
from test_home_matchday import LEAGUES, match

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('width',[320,1440])
@pytest.mark.parametrize('language',['es','en','fr'])
@pytest.mark.parametrize('javascript',[True,False])
def test_matchday_is_visible_diverse_and_navigable(browser,app_module,width,language,javascript,tmp_path):
    from flask import render_template
    from engines.madrid_time_engine import madrid_greeting
    now=datetime.now(ZoneInfo('Europe/Madrid'))
    # Future matches work across midnight without freezing any application clock.
    rows=[match('live-qa',LEAGUES[1],now=now,hours=-.5,state='live',home_score=1,away_score=0,minute=30)]
    rows += [match('qa-'+league[0],league,now=now,hours=24) for league in LEAGUES]
    rows += [match('final-qa',LEAGUES[2],now=now,hours=-4,state='finished',home_score=0,away_score=0)]
    day=app_module.home_matchday_context({'all_valid_matches':rows},favorites={'match':{'qa-laliga'}})
    assert day['upcoming']['shown']==6
    with app_module.app.test_request_context('/app',headers={'Accept-Language':language}):
        markup=render_template('client_app_center.html',data={'home_matchday':day,'sports_metrics':{'matches_today':1,'live_confirmed':1,'picks_ready':0}},
            current_user={'id':'qa-home','name':'María','membership':'FREE'},
            greeting=madrid_greeting('María',username='qa-home',locale=language))
    markup=re.sub(r'<script\b([^>]*)>.*?</script>',lambda m:m.group(0) if any(
        name in m[1] for name in ('application/json','ui-localization.js','v930-icons.js')) else '',markup,flags=re.S|re.I)
    context=browser.new_context(viewport={'width':width,'height':1000},java_script_enabled=javascript,locale=language,service_workers='block')
    page=context.new_page(); calls=[];errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    def serve(route):
        url=urlsplit(route.request.url);calls.append((route.request.method,url.path))
        if url.netloc!='home.invalid':route.abort();return
        if url.path=='/app':route.fulfill(status=200,content_type='text/html; charset=utf-8',body=markup);return
        asset=(ROOT/url.path.lstrip('/')).resolve()
        if url.path.startswith('/static/') and asset.is_relative_to(ROOT/'static') and asset.is_file():
            route.fulfill(status=200,content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream',body=asset.read_bytes());return
        route.fulfill(status=200,content_type='text/html',body='<p>SIMULATED_QA destination</p>')
    page.route('**/*',serve)
    try:
        page.goto('https://home.invalid/app')
        assert page.locator('[data-madrid-greeting]').inner_text().endswith('María')
        assert page.locator('[data-personal-home]').count()==0
        assert page.locator('.home-agenda-focus details').count()==0
        assert page.locator('.home-agenda-focus').evaluate('(el)=>getComputedStyle(el).display')==('grid' if width>1100 else 'block')
        assert page.locator('.home-agenda-focus .ns16-home-command').evaluate('(el)=>getComputedStyle(el).display')=='flex'
        assert page.locator('.home-competition-group header').first.evaluate('(el)=>getComputedStyle(el).display')=='flex'
        for league in LEAGUES:
            card=page.locator('[data-v934-match-id="qa-'+league[0]+'"]')
            assert card.count()==1 and card.is_visible()
        assert page.locator('[data-v934-match-id="qa-laliga"] .fav-star').get_attribute('aria-pressed')=='true'
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        assert not page.locator('.home-agenda-matches').evaluate_all('(nodes)=>nodes.some(el=>el.scrollWidth>el.clientWidth+1)')
        if language=='es' and javascript:
            page.screenshot(path=str(tmp_path/f'home-{width}.png'),full_page=True)
            page.screenshot(path=str(tmp_path/f'home-{width}-viewport.png'))
        link=page.locator('[data-v934-match-id="qa-laliga"] a[href="/match/qa-laliga"]').last
        # Native focus scrolls the link into view and works with scripts disabled;
        # avoid Playwright's animation/stability scroll polling in no-JS contexts.
        link.focus();page.keyboard.press('Enter')
        page.wait_for_url('**/match/qa-laliga')
        assert not errors
        assert all(method=='GET' and not path.startswith('/api/') for method,path in calls)
    finally:context.close()
