"""Real-template/Chromium QA. All matches and badge responses are SIMULATED_QA."""
from datetime import datetime
from pathlib import Path
import mimetypes
import os
import re
from urllib.parse import urlsplit

import pytest
from test_app_navigation_browser import browser
from test_home_matchday import LEAGUES, build, match

ROOT = Path(__file__).resolve().parents[1]
BADGE = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect x="1" y="1" width="62" height="62" rx="14" fill="#f1f5f9"/><text x="32" y="39" text-anchor="middle" fill="#172b4d" font-size="20">QA</text></svg>'


def day_fixture():
    rows = [match('preview-' + str(i), LEAGUES[i % 6], hours=1 + (i % 5)) for i in range(30)]
    for item in rows:
        item['competition_logo'] = '/static/qa-broken.svg' if item['competition_key'] == 'ligue-1' else '/static/qa-badge.svg'
    return build(rows)


def markup_for(app_module, public=False):
    from flask import render_template
    day = day_fixture()
    data = {'home_matchday':day,'sports_metrics':{'matches_today':30,'live_confirmed':0,'picks_ready':0}}
    with app_module.app.test_request_context('/' if public else '/app'):
        markup = render_template('home.html' if public else 'client_app_center.html', data=data,
            current_user=None if public else {'id':'home-qa','name':'Vista de prueba','membership':'FREE'},
            greeting={'label':'Agenda de prueba','name':'DATOS SIMULADOS'}, evidence_origin='SIMULATED_QA')
    # Retain real icons, localization and image-failure handling. All traffic is intercepted.
    markup = re.sub(r'<script\b([^>]*)>.*?</script>', lambda m: m.group(0) if any(
        name in m[1] for name in ('application/json','v930-icons.js','ui-localization.js','v937-product-client.js')) else '', markup, flags=re.S|re.I)
    return markup


def calendar_markup_for(app_module, query):
    """Use the same accepted synthetic rows through the real calendar adapter."""
    from flask import render_template
    day=day_fixture()
    rows=[item for group in day['today']['groups'] for item in group['matches']]
    summary=dict(all_valid_matches=rows,valid_matches_available=rows,
                 valid_matches_today=rows,valid_upcoming_matches=rows,
                 valid_live_events=[],finished_matches=[],valid_active_picks=[],
                 incident_matches=[],incomplete_matches=[])
    with app_module.app.test_request_context('/calendario?'+query):
        calendar=app_module.v940_calendar_context(summary,date_value=day['date'])
        assert calendar['counts']['visible']==30
        html=render_template('calendar.html',data={'calendar':calendar,'v925_calendar':{'has_real_data':True}},
                             current_user=None)
    return re.sub(r'<script\b([^>]*)>.*?</script>',lambda m:m.group(0) if any(
        name in m[1] for name in ('v940-calendar.js','v930-icons.js','ui-localization.js')) else '',html,flags=re.S|re.I)


def test_public_home_get_receives_the_same_snapshot_matchday(app_module, monkeypatch):
    data = {'all_valid_matches':[]}
    monkeypatch.setattr(app_module,'capture_growth_attribution_from_request',lambda:None)
    monkeypatch.setattr(app_module,'get_public_home_sports_summary',lambda:data)
    monkeypatch.setattr(app_module,'home_light_data',lambda *a,**kw:{'picks':[]})
    monkeypatch.setattr(app_module,'get_v934_realtime_context',lambda *a:{})
    monkeypatch.setattr(app_module,'render_template',lambda name,**kw:kw)
    with app_module.app.test_request_context('/'):
        result = app_module.home()
    assert result['data']['home_matchday']['today']['total'] == 0


def test_runtime_asset_flag_uses_the_generated_bundle(app_module,monkeypatch):
    # This unit covers asset diagnostics, not authentication. Do not impersonate
    # an absent account using a cookie; role/session privacy has its own tests.
    monkeypatch.setattr(app_module,'is_admin_session',lambda:True)
    with app_module.app.test_request_context('/api/runtime-version'):
        payload=app_module.api_runtime_version().get_json()
    assert payload['static_css_cache_busting'] is True
    from engines.canonical_assets import css_digest
    assert payload['canonical_css_sha256'] == css_digest(ROOT)
    assert payload['canonical_css_asset'] == '/static/product-system.css'


def test_badge_request_never_creates_missing_database(app_module, monkeypatch, tmp_path):
    missing = tmp_path/'absent.db'
    monkeypatch.setattr(app_module,'DB_PATH',str(missing))
    # Call the view directly, excluding unrelated global request hooks.
    with app_module.app.test_request_context('/asset/league-logo/qa?name=QA&country=Spain'):
        response = app_module.asset_league_logo('qa')
    assert response.status_code == 302
    assert response.headers['Location'].startswith('/team-crest.svg?')
    assert not missing.exists()


@pytest.mark.parametrize('width',[320,390,1440])
@pytest.mark.parametrize('javascript',[True,False])
@pytest.mark.parametrize('public',[False,True])
def test_more_today_grouped_with_logos_and_native_league_navigation(browser, app_module, width, javascript, public, tmp_path):
    context = browser.new_context(viewport={'width':width,'height':1000}, java_script_enabled=javascript, service_workers='block', locale='es-ES')
    page = context.new_page(); errors=[]; calls=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    markup = markup_for(app_module, public=public)
    page_path = '/' if public else '/app'
    def serve(route):
        url = urlsplit(route.request.url); calls.append((route.request.method,url.path))
        if url.netloc != 'league-home.invalid': route.abort(); return
        if url.path == page_path: route.fulfill(status=200,content_type='text/html; charset=utf-8',body=markup); return
        if url.path == '/calendario':
            route.fulfill(status=200,content_type='text/html; charset=utf-8',body=calendar_markup_for(app_module,url.query));return
        if url.path == '/static/qa-badge.svg': route.fulfill(status=200,content_type='image/svg+xml',body=BADGE); return
        if url.path == '/static/qa-broken.svg': route.fulfill(status=404,body='QA missing badge'); return
        path = (ROOT/url.path.lstrip('/')).resolve()
        if url.path.startswith('/static/') and path.is_relative_to(ROOT/'static') and path.is_file():
            route.fulfill(status=200,content_type=mimetypes.guess_type(str(path))[0] or 'application/octet-stream',body=path.read_bytes()); return
        route.fulfill(status=200,content_type='text/html',body='<p>SIMULATED_QA destination</p>')
    page.route('**/*',serve)
    try:
        page.goto('https://league-home.invalid'+page_path)
        agenda=page.locator('[data-home-league-agenda="'+('public-today' if public else 'today')+'"]')
        preview_count=4 if public else 5
        assert agenda.locator('[data-v934-match-id]').count() == preview_count
        assert page.locator('[data-v934-match-id]').count() == 5
        assert agenda.locator('.home-competition-group').count() == preview_count
        assert agenda.locator('.home-competition-header img').count() == preview_count
        assert agenda.locator('details').count() == 0
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        boxes = agenda.locator('.home-competition-group').evaluate_all('(els)=>els.map(e=>{const r=e.getBoundingClientRect();return {top:r.top,bottom:r.bottom,left:r.left,right:r.right}})')
        # Wide screens intentionally place domestic competition groups in a
        # responsive grid; verify the cards never collide instead of requiring
        # a single vertical column.
        assert all(
            boxes[i]['right'] <= boxes[j]['left']
            or boxes[j]['right'] <= boxes[i]['left']
            or boxes[i]['bottom'] <= boxes[j]['top']
            or boxes[j]['bottom'] <= boxes[i]['top']
            for i in range(len(boxes)) for j in range(i + 1, len(boxes))
        )
        assert len(set(agenda.locator('.home-competition-group').evaluate_all('(els)=>els.map(e=>getComputedStyle(e).borderLeftColor)'))) > 1
        ids=agenda.locator('[data-v934-match-id]').evaluate_all('(els)=>els.map(e=>e.dataset.v934MatchId)')
        assert len(set(ids)) == preview_count
        for group in agenda.locator('.home-competition-group').all():
            assert group.locator('[data-v934-match-id]').count() == 1
        link=page.locator('.home-league-index a').first
        target=link.get_attribute('href')
        link.focus(); page.keyboard.press('Enter')
        assert page.locator(target).count()==1 and page.locator(target).is_visible()
        if javascript:
            good=agenda.locator('img[src="/static/qa-badge.svg"]').first
            good.scroll_into_view_if_needed()
            good.evaluate('(el)=>el.loading="eager"')
            page.wait_for_function("(src) => Array.from(document.images).some(el => el.getAttribute('src') === src && el.naturalWidth > 0)", arg='/static/qa-badge.svg')
            broken=agenda.locator('img[src="/static/qa-broken.svg"]')
            if broken.count():
                broken.first.locator('..').scroll_into_view_if_needed();broken.first.evaluate('(el)=>el.loading="eager"')
                page.wait_for_function("(src) => Array.from(document.images).some(el => el.getAttribute('src') === src && el.closest('.crest').dataset.crestState === 'fallback')", arg='/static/qa-broken.svg')
            out=tmp_path/'home-league-review';out.mkdir(parents=True,exist_ok=True)
            page.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(out/f'home-{"public" if public else "client"}-{width}.png'),full_page=True)
            page.screenshot(path=str(out/f'home-{"public" if public else "client"}-{width}-viewport.png'))
        # The preview must not lose the 25 omitted fixtures: follow its actual
        # dated "all" link into the complete calendar and inspect every identity.
        complete=page.locator('[data-sports-priority="important-today"] .home-agenda-more a')
        assert complete.count()==1
        assert 'date='+day_fixture()['date'] in complete.get_attribute('href')
        complete.focus();page.keyboard.press('Enter')
        page.wait_for_url('**/calendario?date=*')
        all_ids=page.locator('[data-v940-calendar-collection] [data-v934-match-id]').evaluate_all(
            '(nodes)=>nodes.map(node=>node.dataset.v934MatchId)')
        assert len(all_ids)==len(set(all_ids))==30
        assert set(all_ids)=={'preview-'+str(i) for i in range(30)}
        leagues=page.locator('details.v940-calendar-league')
        assert leagues.count()==6
        for league in leagues.all():
            league.locator('summary').click()
            assert league.locator('summary').evaluate('''el => {
                const r=el.getBoundingClientRect();
                const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                return el===hit||el.contains(hit);
            }'''), 'A fixed header or bottom bar obscures the native fold target'
            league.locator('summary').press('Enter')
            assert league.get_attribute('open') is None
            league.locator('summary').press('Enter')
            assert league.get_attribute('open') is not None
        assert page.locator('details.v940-calendar-league[open]').count()==6
        assert not errors
        assert all(method=='GET' and not path.startswith('/api/') for method,path in calls)
    finally:
        context.close()


def test_public_hero_and_grouped_preview_share_global_budget_with_complete_agenda_link(app_module):
    from test_design02_calendar_presentation import Structure
    dom=Structure(markup_for(app_module,public=True))
    agenda=next(n for n in dom.nodes if n['attrs'].get('data-home-league-agenda')=='public-today')
    cards=[n for n in dom.nodes if 'data-v934-match-id' in n['attrs'] and agenda in n['parents']]
    assert len(cards)==4
    assert len([n for n in dom.nodes if 'home-competition-group' in n['attrs'].get('class','') and agenda in n['parents']])==4
    ids=[n['attrs']['data-v934-match-id'] for n in dom.nodes if 'data-v934-match-id' in n['attrs']]
    assert len(ids)==len(set(ids))==5
    assert day_fixture()['today']['total']==30
