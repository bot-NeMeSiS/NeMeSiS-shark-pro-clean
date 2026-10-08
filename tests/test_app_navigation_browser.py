"""Real Chromium interactions on rendered shells, with all external traffic blocked."""
import mimetypes
import os
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from test_app_navigation import render_directory

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        instance = pw.chromium.launch(headless=True, executable_path=os.getenv('NEMESIS_QA_CHROMIUM') or pw.chromium.executable_path)
        yield instance
        instance.close()


def mount(browser, app_module, scope='client', width=390, *, javascript=True):
    markup = render_directory(app_module, scope)
    # Isolate navigation from unrelated realtime/PWA jobs while retaining the
    # complete rendered shell and actual styles, translations and icon renderer.
    markup = re.sub(r'<script\b([^>]*)>.*?</script>', lambda m: m.group(0) if any(
        name in m[1] for name in ('application/json','app-navigation.js','ui-localization.js','v930-icons.js')) else '', markup, flags=re.S|re.I)
    context = browser.new_context(viewport={'width':width,'height':850}, java_script_enabled=javascript, locale='es-ES', timezone_id='Europe/Madrid')
    page = context.new_page()
    errors, calls = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    path = '/admin/explorar' if scope == 'admin' else '/explorar'
    def serve(route):
        url = urlsplit(route.request.url)
        calls.append((route.request.method, url.path))
        if url.netloc != 'navigation.invalid':
            route.abort(); return
        if url.path == path:
            route.fulfill(status=200,content_type='text/html; charset=utf-8',body=markup); return
        if url.path.startswith('/static/'):
            asset = (ROOT / url.path.lstrip('/')).resolve()
            if asset.is_relative_to(ROOT / 'static') and asset.is_file():
                route.fulfill(status=200,content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream',body=asset.read_bytes()); return
        route.fulfill(status=200,content_type='text/html',body='<p>SIMULATED_QA destination</p>')
    page.route('**/*', serve)
    page.goto('https://navigation.invalid'+path)
    return context, page, errors, calls


@pytest.mark.parametrize('scope',['public','client','admin'])
@pytest.mark.parametrize('width',[320,390,768,1440])
def test_explorer_filter_focus_and_mobile_layout(browser, app_module, scope, width):
    context,page,errors,calls = mount(browser,app_module,scope,width)
    try:
        trigger = page.locator('#v933-admin-search') if scope == 'admin' and width == 1440 else page.locator('[data-open-explore]:visible').first
        if scope == 'admin' and width == 1440:
            trigger.press('Enter')
        else:
            trigger.click()
        dialog = page.locator('#app-navigation-dialog')
        assert dialog.is_visible()
        search = dialog.locator('[data-explore-query]')
        assert search.evaluate('(el)=>el===document.activeElement')
        search.fill('COPIAS SEGURÍDAD' if scope == 'admin' else '  competicíones  ')
        choices = dialog.locator('[data-explore-item]:visible')
        assert choices.count() == 1
        expected = '/admin/backups' if scope == 'admin' else '/competiciones'
        assert choices.first.get_attribute('href') == expected
        page.keyboard.press('ArrowDown')
        assert choices.first.evaluate('(el)=>el===document.activeElement')
        page.keyboard.press('ArrowUp')
        assert search.evaluate('(el)=>el===document.activeElement')
        search.fill('zzsincoincidencia')
        assert dialog.locator('[data-explore-empty]').is_visible()
        search.fill('')
        assert dialog.locator('[data-explore-item]:visible').count() >= 15
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert dialog.evaluate('(el)=>el.scrollWidth <= el.clientWidth+1')
        evidence = ROOT/'reports/app-navigation-20261008'
        evidence.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(evidence/f'{scope}-{width}.png'))
        page.keyboard.press('Escape')
        assert not dialog.is_visible()
        assert trigger.evaluate('(el)=>el===document.activeElement')
        assert not errors
        assert all(method == 'GET' and not path.startswith('/api/') for method,path in calls)
    finally:
        context.close()


def test_match_search_encodes_query_and_navigates_only_on_selection(browser,app_module):
    context,page,errors,calls = mount(browser,app_module)
    try:
        page.keyboard.press('Control+k')
        search = page.locator('#explore-dialog-query')
        query = 'Madrid & Athletic <equipo>'
        search.fill(query)
        link = page.locator('#app-navigation-dialog [data-explore-match]')
        assert parse_qs(urlsplit(link.get_attribute('href')).query) == {'lane':['week'],'q':[query]}
        assert not page.locator('#app-navigation-dialog script:not([src])').count()
        assert all(path != '/calendario' for _,path in calls)
        search.press('Enter')
        page.wait_for_url('**/calendario?**')
        assert parse_qs(urlsplit(page.url).query)['q'] == [query]
        assert not errors
    finally:
        context.close()


def test_admin_search_stays_on_current_page_and_respects_existing_modal(browser,app_module):
    context,page,errors,calls = mount(browser,app_module,'admin',1440)
    try:
        start = page.url
        page.locator('#v933-admin-search').fill('usuarios')
        page.locator('#v933-admin-search').press('Enter')
        dialog = page.locator('#app-navigation-dialog')
        assert dialog.is_visible() and page.url == start
        assert dialog.locator('[data-explore-item]:visible').first.get_attribute('href') == '/admin/users'
        page.keyboard.press('Escape')
        page.evaluate("() => {const d=document.createElement('dialog'); d.id='qa-confirm'; d.textContent='SIMULATED_QA confirmación'; document.body.append(d); d.showModal();}")
        page.keyboard.press('Control+k')
        assert not dialog.is_visible() and page.locator('#qa-confirm').is_visible()
        assert not errors and all(method=='GET' for method,_ in calls)
    finally:
        context.close()


def test_no_javascript_fallback_exposes_links_and_a_get_form(browser,app_module):
    context,page,errors,calls = mount(browser,app_module,'public',320,javascript=False)
    try:
        assert not page.locator('#app-navigation-dialog').is_visible()
        assert page.locator('.app-explore-page a[href="/competiciones"]').is_visible()
        form = page.locator('.app-explore-page [data-explore-form]')
        assert form.get_attribute('method')=='get' and form.get_attribute('action')=='/explorar'
        assert page.locator('[data-open-explore]:visible').first.get_attribute('href')=='/explorar'
    finally:
        context.close()


def test_queued_close_does_not_clear_a_reopened_search(browser,app_module):
    context,page,errors,calls = mount(browser,app_module)
    try:
        page.keyboard.press('Control+k')
        state = page.evaluate("""() => new Promise(resolve => {
          const dialog = document.getElementById('app-navigation-dialog');
          const input = dialog.querySelector('[data-explore-query]');
          dialog.addEventListener('close', () => resolve({
            open: dialog.open, query: input.value, focused: input === document.activeElement,
            links: [...dialog.querySelectorAll('[data-explore-item]:not([hidden])')].map(a => a.getAttribute('href'))
          }), {once: true});
          dialog.close();
          window.NemesisNavigation.open(document.querySelector('[data-open-explore]'), 'competicion');
        })""")
        assert state == {'open':True,'query':'competicion','focused':True,'links':['/competiciones']}
        assert not errors and all(method=='GET' for method,_ in calls)
    finally:
        context.close()


@pytest.mark.parametrize('scope',['public','client','admin'])
def test_canonical_click_audit_follows_a_destination_inside_finder(browser,app_module,scope):
    from tools.run_v929_click_navigation_qa import _click_one
    context,page,errors,calls = mount(browser,app_module,scope)
    try:
        origin = '/admin/explorar' if scope == 'admin' else '/explorar'
        result = _click_one(page,'https://navigation.invalid',origin,
                            {'tag':'a','target':origin,'text':'Explorar'},5000,scope)
        assert result['result'] == 'OK', result
        assert result['interaction'] == 'navigation_dialog'
        assert result['selected_navigation_target']
        assert result['final_path'] == urlsplit(result['selected_navigation_target']).path
        assert result['final_path'] != origin
        assert not errors and all(method=='GET' for method,_ in calls)
    finally:
        context.close()


def test_canonical_click_audit_still_rejects_broken_finder_destinations(browser,app_module):
    from tools.run_v929_click_navigation_qa import _click_one
    context,page,errors,calls = mount(browser,app_module)
    try:
        page.route('https://navigation.invalid/app', lambda route: route.fulfill(
            status=404,content_type='text/html',body='<p>Ruta no encontrada</p>'))
        result = _click_one(page,'https://navigation.invalid','/explorar',
                            {'tag':'a','target':'/explorar','text':'Explorar'},5000,'client')
        assert result['result'] == 'ROTA_404'
        assert result['selected_navigation_target'] == '/app'
    finally:
        context.close()
