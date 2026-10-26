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
        home_rhythm=page.locator('.home-agenda-focus').evaluate('(el)=>({rowGap:getComputedStyle(el).rowGap,childMargin:getComputedStyle(el.children[0]).marginBlockEnd})')
        assert home_rhythm['rowGap']=='12px'
        assert home_rhythm['childMargin']==('0px' if width>1100 else '10px')
        assert page.locator('.home-agenda-focus .ns16-home-command').evaluate('(el)=>getComputedStyle(el).rowGap')==('14px' if width>1100 else '12px')
        assert page.locator('.home-competition-group header').first.evaluate('(el)=>getComputedStyle(el).display')=='flex'
        compact_card=page.locator('.ns16-home .home-agenda-matches .v933-match-card').first
        team_names=compact_card.locator('.v933-match-teams strong')
        assert team_names.count()==2
        team_metrics=team_names.evaluate_all('(nodes)=>nodes.map(el=>({text:el.textContent,display:getComputedStyle(el).display,visibility:getComputedStyle(el).visibility,rect:el.getBoundingClientRect().toJSON()}))')
        assert all(name['display']!='none' and name['visibility']!='hidden' and name['rect']['width']>0 and name['rect']['height']>0 and name['text'].strip() for name in team_metrics), team_metrics
        card_style=compact_card.evaluate('(el)=>{const style=getComputedStyle(el);return {minHeight:style.minHeight,padding:style.padding}}')
        assert card_style['minHeight']=='0px'
        assert card_style['padding']==('8px' if width<=600 else '9px')
        assert page.locator('.ns16-home .home-agenda-matches .v933-match-teams').first.evaluate(
            '(el)=>getComputedStyle(el).gridTemplateColumns.split(" ").length==3'
        )
        upcoming_list=page.locator('[data-sports-priority="upcoming"] .home-competition-list').first
        group_positions=upcoming_list.locator(':scope > .home-presentation-section').evaluate_all(
            "nodes=>nodes.slice(0,2).map(el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width}})"
        )
        assert len(group_positions)==2
        if width>1100:
            assert group_positions[1]['x']>group_positions[0]['x']
            assert abs(group_positions[1]['y']-group_positions[0]['y'])<=2
            assert group_positions[0]['width']>=360
        else:
            assert abs(group_positions[1]['x']-group_positions[0]['x'])<=2
            assert group_positions[1]['y']>group_positions[0]['y']
        from engines.home_preview import home_preview
        preview=home_preview(day,with_hero=False)
        expected_ids=[row['id'] for lane in ('live','today','upcoming','results')
                      for group in preview[lane]['groups'] for row in group['matches']]
        assert len(expected_ids)==len(set(expected_ids))==5
        assert page.locator('[data-v934-match-id]').count()==5
        for identity in expected_ids:
            card=page.locator('[data-v934-match-id="'+identity+'"]')
            assert card.count()==1 and card.is_visible()
        assert day['upcoming']['total']==6
        assert page.locator('[data-sports-priority="upcoming"] a[href^="/calendario?lane=week&date="]').count()>=1
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


def test_home_secondary_sections_stay_accessible_without_js_and_respect_first_run(browser):
    script=(ROOT/'static/v937-product-client.js').read_text(encoding='utf-8')
    html='''<!doctype html><html lang="es"><body class="ns-app ns-authenticated">
      <main><details data-home-extras><summary class="v933-home-more-summary">Más opciones</summary>
        <section data-launch-onboarding="first-run"><button data-launch-onboarding-dismiss>Omitir</button></section>
        <nav aria-label="Herramientas secundarias"><a href="/daily-briefing">Resumen diario</a></nav>
      </details></main></body></html>'''
    def serve(route):
        route.fulfill(status=200,content_type='text/html; charset=utf-8',body=html)

    context=browser.new_context(viewport={'width':390,'height':844},service_workers='block')
    page=context.new_page();context.route('**/*',serve)
    try:
        page.goto('https://home.invalid/')
        page.add_script_tag(content=script)
        details=page.locator('[data-home-extras]')
        assert details.evaluate('(el)=>el.open') is True
        page.locator('[data-launch-onboarding-dismiss]').click()
        assert details.evaluate('(el)=>el.open') is False
        assert page.locator('section[data-launch-onboarding]').get_attribute('class')=='is-hidden'
        assert page.evaluate("localStorage.getItem('nemesis.launch.onboarding.dismissed.v1')")=='1'
        page.reload();page.add_script_tag(content=script)
        assert details.evaluate('(el)=>el.open') is False
        assert page.locator('section[data-launch-onboarding]').get_attribute('class')=='is-hidden'
    finally:
        context.close()

    no_js=browser.new_context(viewport={'width':320,'height':720},java_script_enabled=False,service_workers='block')
    no_js_page=no_js.new_page();no_js.route('**/*',serve)
    try:
        no_js_page.goto('https://home.invalid/')
        no_js_page.locator('[data-home-extras] > summary').focus()
        no_js_page.keyboard.press('Enter')
        assert no_js_page.locator('[data-home-extras]').evaluate('(el)=>el.open') is True
        assert no_js_page.get_by_role('link',name='Resumen diario').is_visible()
    finally:
        no_js.close()


@pytest.mark.parametrize('width',[390,1440])
def test_home_secondary_competitions_do_not_create_a_dead_desktop_column(browser,width):
    css=(ROOT/'static/product-system.css').read_text(encoding='utf-8')+'\n'+(ROOT/'static/home-league-disclosure.css').read_text(encoding='utf-8')
    html='''<!doctype html><html lang="es"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
    <body><main class="home-agenda-focus"><div class="home-league-browser"><div class="home-competition-list" data-home-league-agenda="today">
      <details class="home-leagues-more"><summary class="home-more-summary">Más competiciones</summary><div>Más partidos reales</div></details>
      <section class="home-presentation-section"><h3 class="home-presentation-section-heading">España</h3><div class="home-presentation-section-items"><article class="home-competition-group">LaLiga</article></div></section>
      <section class="home-presentation-section"><h3 class="home-presentation-section-heading">Torneos internacionales</h3><div class="home-presentation-section-items"><article class="home-competition-group">Champions League</article></div></section>
    </div></div></main></body></html>'''
    context=browser.new_context(viewport={'width':width,'height':800},service_workers='block')
    page=context.new_page()
    try:
        page.set_content(html)
        page.add_style_tag(content=css)
        disclosure=page.locator('.home-competition-list > .home-leagues-more').bounding_box()
        container=page.locator('.home-competition-list').bounding_box()
        sections=page.locator('.home-competition-list > .home-presentation-section').evaluate_all(
            '(nodes)=>nodes.map(el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width}})')
        assert disclosure and container and sections
        if width > 1100:
            assert abs(disclosure['width']-container['width'])<=1
            assert sections[1]['x']>sections[0]['x']
            assert abs(sections[1]['y']-sections[0]['y'])<=2
        else:
            assert abs(disclosure['width']-container['width'])<=1
            assert abs(sections[1]['x']-sections[0]['x'])<=2
            assert sections[1]['y']>sections[0]['y']
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
    finally:
        context.close()
