"""Real UI, read-only search and explicit favorite save on synthetic account data."""
import mimetypes
from pathlib import Path
import re
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect
from test_app_navigation_browser import browser
from test_sports_search import sports_catalogue

ROOT = Path(__file__).resolve().parents[1]


def mount(browser, app_module, monkeypatch, sports_catalogue, width=390, language='es', javascript=True):
    monkeypatch.setattr(app_module, 'DB_PATH', str(sports_catalogue))
    monkeypatch.setattr(app_module, 'initialize_once', lambda: None)
    monkeypatch.setattr(app_module, 'current_session_user', lambda: {'id':'search-owner','role':'CLIENT','membership':'FREE'})
    monkeypatch.setattr(app_module, 'is_admin_session', lambda: False)
    monkeypatch.setattr(app_module, 'favorite_feed_full', lambda **kw: {'matches':[],'live':[],'picks':[]})
    monkeypatch.setattr(app_module, '_growth_maybe_activate_user', lambda **kw: None)
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session['user_id'] = 'search-owner'
    context = browser.new_context(viewport={'width':width,'height':920}, java_script_enabled=javascript, locale=language, service_workers='block')
    page = context.new_page()
    errors, calls = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    def serve(route):
        request = route.request
        url = urlsplit(request.url)
        calls.append((request.method, url.path, url.query))
        if url.netloc != 'search.invalid':
            route.abort(); return
        if url.path.startswith('/static/'):
            asset = (ROOT / url.path.lstrip('/')).resolve()
            if asset.is_relative_to(ROOT/'static') and asset.is_file():
                route.fulfill(status=200, content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream', body=asset.read_bytes()); return
        if url.path in {'/favoritos', '/api/sports-search', '/explorar'}:
            response = client.open(url.path+'?'+url.query, method=request.method, data=request.post_data, follow_redirects=True,
                headers={'Accept-Language':language, 'Content-Type':request.headers.get('content-type',''), 'Origin':'http://localhost'})
            body = response.get_data(as_text=True)
            if 'text/html' in response.content_type:
                body = re.sub(r'<script\b([^>]*)>.*?</script>', lambda m:m.group(0) if any(
                    name in m[1] for name in ('application/json','app-navigation.js','sports-search.js','ui-localization.js','v930-icons.js')) else '', body, flags=re.S|re.I)
            headers = {'content-type':response.content_type}
            if response.location:
                headers['location'] = response.location
            route.fulfill(status=response.status_code, headers=headers, body=body); return
        route.fulfill(status=200, content_type='text/html', body='<p>SIMULATED_QA destination</p>')
    page.route('**/*', serve)
    page.goto('https://search.invalid/favoritos')
    return context, page, errors, calls


@pytest.mark.parametrize('width', [320,1440])
@pytest.mark.parametrize('language', ['es','en','fr'])
def test_progressive_selection_explicit_save_and_saved_search(browser, app_module, monkeypatch, sports_catalogue, tmp_path, width, language):
    context,page,errors,calls = mount(browser,app_module,monkeypatch,sports_catalogue,width,language)
    try:
        search = page.locator('#favorite-find')
        options = page.locator('#favorite-discovery [role=option]')
        search.fill('gra')
        expect(options).to_have_count(9)
        assert options.filter(has_text='Nicaragua').count() == 1
        assert page.locator('#favorite-discovery img').count() == 0  # Stored markup stays text.
        search.fill('granáda fem')
        expect(options).to_have_count(1)
        expect(options.first).to_contain_text('Granada Femenino')
        assert all(method == 'GET' for method,_,_ in calls)
        search.press('ArrowDown')
        expect(search).to_have_attribute('aria-activedescendant','favorite-discovery-list-0')
        search.press('Enter')
        selection = page.locator('[data-sports-selection="favorite-discovery"]')
        expect(selection).to_be_visible()
        assert selection.locator('[name=value]').input_value() == '@team:granada-fem'
        assert selection.locator('[name=csrf_token]').input_value()
        assert app_module.get_favorites(user_id='search-owner') == []
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        page.screenshot(path=str(tmp_path/f'search-{width}-{language}.png'), full_page=True)
        with page.expect_navigation():
            selection.locator('button[type=submit]').click()
        assert [f['value'] for f in app_module.get_favorites(user_id='search-owner')] == ['@team:granada-fem']
        saved = page.locator('#favorite-query')
        saved.fill('fem')
        expect(page.locator('#saved-favorite-search [role=option]')).to_have_count(1)
        page.locator('#favorite-find-kind').select_option('match')
        search.fill('granada malaga')
        expect(options).to_have_count(1)
        assert '2099-10-10' in options.inner_text()
        options.first.click()
        assert selection.locator('[name=value]').input_value() == 'gr-future'
        with page.expect_navigation():
            selection.locator('button[type=submit]').click()
        assert {f['kind'] for f in app_module.get_favorites(user_id='search-owner')} == {'team','match'}
        assert not errors
        assert all(method == 'GET' or path == '/favoritos' for method,path,_ in calls)
    finally:
        context.close()


@pytest.mark.parametrize('javascript', [True,False])
def test_get_fallback_search_and_save_competition(browser, app_module, monkeypatch, sports_catalogue, javascript):
    context,page,errors,calls = mount(browser,app_module,monkeypatch,sports_catalogue,javascript=javascript)
    try:
        page.locator('#favorite-find-kind').select_option('league')
        page.locator('#favorite-find').fill('division espana')
        with page.expect_navigation():
            page.locator('.sports-search-toolbar button').press('Enter')
        result = page.locator('[data-sports-server-results] .sports-search-result')
        expect(result).to_have_count(1)
        assert result.locator('[name=value]').input_value() == 'sp2'
        assert all(method == 'GET' for method,_,_ in calls)
        with page.expect_navigation():
            result.locator('button').press('Enter')
        assert [f['value'] for f in app_module.get_favorites(user_id='search-owner')] == ['sp2']
        assert not errors
    finally:
        context.close()


def test_keyboard_navigation_explorer_error_and_selection_invalidation(browser, app_module, monkeypatch, sports_catalogue):
    context,page,errors,calls = mount(browser,app_module,monkeypatch,sports_catalogue)
    try:
        search = page.locator('#favorite-find')
        search.fill('granada fem')
        options = page.locator('#favorite-discovery [role=option]')
        expect(options).to_have_count(1)
        search.press('ArrowUp'); search.press('Enter')
        selection = page.locator('[data-sports-selection="favorite-discovery"]')
        expect(selection).to_be_visible()
        search.fill('zzmissing')
        expect(selection).to_be_hidden()
        expect(options).to_have_count(0)
        expect(page.locator('#favorite-discovery')).to_contain_text('Sin coincidencias')
        page.route('**/api/sports-search?**', lambda route: route.fulfill(status=503, body='unavailable'))
        search.fill('granada')
        expect(page.locator('#favorite-discovery')).to_contain_text('No se ha podido buscar')
        search.press('Escape')
        expect(page.locator('#favorite-discovery')).to_be_hidden()
        page.unroute('**/api/sports-search?**')
        page.keyboard.press('Control+k')
        explore = page.locator('#explore-dialog-query')
        explore.fill('granada nicaragua')
        expect(page.locator('#explore-dialog-sports [role=option]')).to_have_count(1)
        explore.press('ArrowDown'); explore.press('Enter')
        page.wait_for_url('**/team/granada-ni')
        assert not errors and all(method == 'GET' for method,_,_ in calls)
    finally:
        context.close()


def test_stale_response_and_composition_do_not_replace_current_results(browser,app_module,monkeypatch,sports_catalogue):
    context,page,errors,calls = mount(browser,app_module,monkeypatch,sports_catalogue)
    try:
        page.evaluate('''() => {
          const fetchOriginal = window.fetch;
          window.fetch = async (...args) => {
            const response = await fetchOriginal(...args);
            if (String(args[0]).includes('q=gra&')) {
              const jsonOriginal = response.json.bind(response);
              response.json = async () => {const value = await jsonOriginal(); await new Promise(resolve => window.finishOldSearch = resolve); return value;};
            }
            return response;
          };
        }''')
        search = page.locator('#favorite-find')
        search.fill('gra')
        page.wait_for_function('typeof window.finishOldSearch === "function"')
        search.fill('granada fem')
        options = page.locator('#favorite-discovery [role=option]')
        expect(options).to_have_count(1)
        page.evaluate('window.finishOldSearch()')
        expect(options).to_have_count(1)
        expect(options).to_contain_text('Granada Femenino')
        search.dispatch_event('compositionstart')
        search.fill('granada nicaragua')
        expect(page.locator('#favorite-discovery')).to_be_hidden()
        search.dispatch_event('compositionend')
        expect(options).to_have_count(1)
        expect(options).to_contain_text('Nicaragua')
        search.fill('g')
        expect(page.locator('#favorite-discovery')).to_be_hidden()
        assert not errors and all(method == 'GET' for method,_,_ in calls)
    finally:
        context.close()


@pytest.mark.parametrize('surface',['calendar','competitions'])
def test_existing_search_bars_offer_canonical_destinations(browser,app_module,monkeypatch,sports_catalogue,surface):
    context,page,errors,calls=mount(browser,app_module,monkeypatch,sports_catalogue)
    try:
        if surface=='calendar':
            from test_calendar_discovery_release import render_calendar
            from test_v940_calendar_sports_experience import _summary
            html,_=render_calendar(app_module,summary=_summary(app_module,3))
            html += '<link rel="stylesheet" href="/static/sports-search.css"><script defer src="/static/v940-calendar.js"></script><script defer src="/static/sports-search.js"></script>'
            path='/calendario'
            selector='[data-v940-calendar-search]'
            query='granada malaga'
            destination='/match/gr-future'
        else:
            with monkeypatch.context() as scoped:
                scoped.setattr(app_module,'competitions',lambda:[])
                scoped.setattr(app_module,'rows',lambda *a,**kw:[])
                with app_module.app.test_request_context('/competiciones'):
                    html=app_module.global_football()
            html=re.sub(r'<script\b([^>]*)>.*?</script>',lambda m:m.group(0) if any(name in m[1] for name in ('application/json','sports-search.js','ui-localization.js')) else '',html,flags=re.S|re.I)
            path='/competiciones'
            selector='input[data-sports-search="competition-sports-search"]'
            query='division espana'
            destination='/competition/sp2'
        page.route('https://search.invalid'+path,lambda route:route.fulfill(status=200,content_type='text/html',body=html))
        page.goto('https://search.invalid'+path)
        search=page.locator(selector)
        search.fill(query)
        panel=page.locator('#'+search.get_attribute('data-sports-search'))
        expect(panel.locator('[role=option]')).to_have_count(1)
        search.press('ArrowDown');search.press('Enter')
        page.wait_for_url('**'+destination)
        assert not errors and all(method=='GET' for method,_,_ in calls)
    finally:
        context.close()
