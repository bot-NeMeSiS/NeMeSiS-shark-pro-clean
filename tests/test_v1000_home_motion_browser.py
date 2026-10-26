"""Actual App, SQLite, password login and browser; original LOCAL SAFE required."""
from datetime import datetime, timedelta, timezone
import json
import os
import secrets
import sqlite3

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.security import generate_password_hash

from test_v1000_match_header_browser import fixture_server


def _question_rows(database):
    with sqlite3.connect(database) as conn:
        result = []
        for table in ('shark_memory', 'shark_context_snapshots'):
            if conn.execute("SELECT 1 FROM sqlite_master WHERE name=? AND type='table'", (table,)).fetchone():
                result.append(conn.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0])
            else:
                result.append(0)
        return result


def _wait_light(page, running):
    page.wait_for_function("expected => document.querySelector('[data-marine-light]').classList.contains('is-running') === expected",arg=running,timeout=3000)


def _preferences(context, page, *, reduced=False, transparent=False):
    context.new_cdp_session(page).send('Emulation.setEmulatedMedia', {'features':[
        {'name':'prefers-reduced-motion','value':'reduce' if reduced else 'no-preference'},
        {'name':'prefers-reduced-transparency','value':'reduce' if transparent else 'no-preference'}]})


def _browser(pw, origin, width, *, reduced=False, blocked_storage=False):
    browser = pw.chromium.launch(executable_path=os.environ['NEMESIS_QA_CHROMIUM'])
    context = browser.new_context(viewport={'width':width,'height':960},
                                  reduced_motion='reduce' if reduced else 'no-preference',
                                  service_workers='block')
    calls, external = [], []
    def boundary(route):
        request = route.request
        calls.append((request.method, request.url.split('?')[0]))
        if request.url.startswith(origin + '/'):
            route.continue_()
        else:
            external.append(request.url.split('?')[0]); route.abort()
    context.route('**/*', boundary)
    if blocked_storage:
        context.add_init_script("Storage.prototype.setItem=function(){throw new DOMException('Owned test: storage disabled','SecurityError')}")
    context.add_init_script("window.__motionEvents=[]; ['animationstart','animationiteration','animationend'].forEach(type=>document.addEventListener(type,e=>{if(e.animationName==='ns-discovery-pulse')window.__motionEvents.push(type)},true));")
    return browser, context, calls, external


@pytest.mark.parametrize('width,plan', [(390,'FREE'), (1440,'PRO'), (1440,'ELITE')])
def test_actual_client_home_is_compact_personal_and_links_account_without_paid_upsell(fixture_server, tmp_path, width, plan):
    a, database, origin, _ = fixture_server
    ident = 'v1000-home-' + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    with sqlite3.connect(database) as conn:
        conn.execute('''INSERT INTO users(id,name,username,email,password_hash,role,membership,
                        membership_source,membership_expires_at,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?)''',
                     (ident,'María','v1000-'+ident,ident+'@example.invalid',generate_password_hash(password),
                      plan,plan,'admin_manual',(now+timedelta(days=365)).isoformat(),now.isoformat()))
    with sync_playwright() as pw:
        browser, context, calls, external = _browser(pw, origin, width, reduced=True)
        page = context.new_page()
        _preferences(context,page,reduced=True)
        errors=[]; page.on('pageerror', lambda error:errors.append(str(error)))
        try:
            assert page.goto(origin+'/cliente-login?next=/app').status==200
            form=page.locator('form[action^="/cliente-login"]')
            form.locator('[name="login"]').fill(ident+'@example.invalid')
            form.locator('[name="password"]').fill(password)
            form.locator('[type="submit"]').click()
            page.wait_for_url(origin+'/app')
            page.wait_for_function('document.readyState === \"complete\"')
            assert page.locator('[data-v1000-home]').count()==1
            assert page.locator('[data-home-greeting]').inner_text().endswith('María')
            assert page.locator('[data-home-greeting]').evaluate('e=>e.tagName')=='P'
            assert '@example.invalid' not in page.locator('[data-home-greeting]').inner_text()
            assert page.locator('.ns16-home-hero h1').inner_text()=='Partidos y resultados'
            assert page.locator('.ns16-home-hero').evaluate('e=>e.getBoundingClientRect().height')<=160
            assert page.locator('.ns16-home-actions a[href="/mi-cuenta"]').count()==1
            assert page.locator('.ns16-home-actions a[href="/membresias"]').count()==0
            assert page.locator('.ns16-home-actions a[href="/favoritos"]').count()==1
            assert page.locator('[data-sports-priority="important-today"]').count()==1
            assert page.locator('[data-sports-priority="recent-results"] .home-more-count').inner_text()=='1 partido'
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(tmp_path/f'home-{width}-{plan}.png'))
            cookie=next(c['value'] for c in context.cookies(origin) if c['name']==a.app.config.get('SESSION_COOKIE_NAME','session'))
            state=a.app.session_interface.get_signing_serializer(a.app).loads(cookie)
            assert state.get('user_id')==ident and state.get('auth_session_id')
            assert not external and not errors, (external,errors)
        finally:
            context.close(); browser.close()


@pytest.mark.parametrize('width', [390,1440])
def test_optional_motion_pauses_and_discovery_never_replays_or_spends_a_question(fixture_server, tmp_path, width):
    _a, database, origin, _ = fixture_server
    before = _question_rows(database)
    with sync_playwright() as pw:
        browser, context, calls, external = _browser(pw, origin, width)
        page=context.new_page(); errors=[]
        _preferences(context,page)
        page.on('pageerror', lambda error:errors.append(str(error)))
        try:
            assert page.goto(origin+'/').status==200
            assert page.locator('[data-motion-preferences]').is_visible()
            # Two finite pulses of the image; the actual native launcher stays put.
            launcher=page.locator('[data-ns-assistant-open]')
            launcher.wait_for(state='visible')
            print('DISCOVERY_VISIBILITY', launcher.evaluate("e=>({rect:e.getBoundingClientRect().toJSON(),visibility:getComputedStyle(e).visibility,display:getComputedStyle(e).display,ready:document.readyState})"))
            page.wait_for_function("localStorage.getItem('nemesis.shark.discovery.v1') === 'seen'",timeout=5000)
            count=launcher.locator('img').evaluate('e=>getComputedStyle(e).animationIterationCount')
            assert count in ('2','1')  # completed pulses have no active animation
            page.wait_for_function("!document.querySelector('[data-ns-assistant-open]').classList.contains('ns-discovery-pulse')")
            assert page.evaluate('window.__motionEvents')==['animationstart','animationiteration','animationend']
            _wait_light(page, False)
            page.locator('[data-motion-preferences] summary').click()
            checkbox=page.locator('[data-marine-toggle]')
            checkbox.check()
            _wait_light(page, True)
            page.locator('[data-motion-toggle]').click()
            assert page.locator('[data-motion-toggle]').get_attribute('aria-pressed')=='true'
            _wait_light(page, False)
            page.reload(wait_until='networkidle')
            assert launcher.get_attribute('class').find('ns-discovery-pulse')==-1
            _wait_light(page, False)
            page.locator('[data-motion-preferences] summary').click()
            page.locator('[data-motion-toggle]').click()
            _wait_light(page, True)
            launcher.click()
            assert page.locator('#ns-assistant-dialog').is_visible()
            _wait_light(page, False)
            assert _question_rows(database)==before
            assert all(path==origin+'/api/growth/funnel-event' for method,path in calls if method=='POST')
            page.locator('[data-assistant-minimize]').click()
            _preferences(context,page,reduced=True)
            _wait_light(page, False)
            assert not page.locator('[data-motion-toggle]').is_enabled()
            _preferences(context,page)
            _wait_light(page, True)
            page.locator('[data-motion-toggle]').click()
            _preferences(context,page,reduced=True)
            _preferences(context,page)
            _wait_light(page, False)
            page.screenshot(path=str(tmp_path/f'motion-{width}.png'))
            assert not external and not errors,(external,errors)
        finally:
            context.close(); browser.close()


@pytest.mark.parametrize('blocked,reduced,transparent', [(True,False,False),(False,True,False),(False,False,True)])
def test_restricted_storage_and_reduced_motion_are_quiet(fixture_server, blocked, reduced, transparent):
    _a,database,origin,_=fixture_server
    before=_question_rows(database)
    with sync_playwright() as pw:
        browser,context,calls,external=_browser(pw,origin,390,reduced=reduced,blocked_storage=blocked)
        page=context.new_page(); errors=[]
        _preferences(context,page,reduced=reduced,transparent=transparent)
        page.on('pageerror',lambda error:errors.append(error.stack))
        try:
            assert page.goto(origin+'/').status==200
            assert page.locator('[data-motion-toggle]').is_enabled()==(transparent and not blocked and not reduced)
            assert not page.locator('[data-marine-toggle]').is_enabled()
            _wait_light(page, False)
            if blocked or reduced:
                assert page.locator('.ns-discovery-pulse').count()==0
            assert page.locator('[data-ns-assistant-open]').get_attribute('href')=='/shark'
            assert _question_rows(database)==before
            assert all(path==origin+'/api/growth/funnel-event' for method,path in calls if method=='POST')
            assert not external and not errors,(external,errors)
        finally:
            context.close(); browser.close()


def test_history_return_keeps_manual_pause_without_replaying_discovery(fixture_server):
    _a,database,origin,_=fixture_server
    before=_question_rows(database)
    with sync_playwright() as pw:
        browser,context,calls,external=_browser(pw,origin,390)
        context.add_init_script("window.__motionPageShows=[];addEventListener('pageshow',e=>window.__motionPageShows.push(e.persisted))")
        page=context.new_page();_preferences(context,page)
        try:
            assert page.goto(origin+'/').status==200
            page.locator('[data-ns-assistant-open]').focus() # Interaction ends discovery.
            page.locator('[data-motion-preferences] summary').click()
            page.locator('[data-marine-toggle]').check()
            _wait_light(page,True)
            assert page.goto(origin+'/faq').status==200
            page.locator('[data-motion-preferences] summary').click()
            page.locator('[data-motion-toggle]').click()
            assert page.locator('[data-motion-toggle]').get_attribute('aria-pressed')=='true'
            page.go_back(wait_until='domcontentloaded')
            page.locator('[data-motion-preferences]').wait_for()
            _wait_light(page,False)
            assert page.locator('[data-motion-toggle]').get_attribute('aria-pressed')=='true'
            assert page.locator('.ns-discovery-pulse').count()==0
            print('MOTION_HISTORY_RETURN',page.evaluate('({pageShows:window.__motionPageShows,navigation:performance.getEntriesByType("navigation")[0]?.type})'))
            assert _question_rows(database)==before
            assert not external
            assert all(path==origin+'/api/growth/funnel-event' for method,path in calls if method=='POST')
        finally:
            context.close();browser.close()
