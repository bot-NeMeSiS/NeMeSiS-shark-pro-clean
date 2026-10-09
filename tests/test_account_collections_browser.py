"""GET collection journeys on real Chromium, with synthetic account data."""
import mimetypes
from pathlib import Path
import re
from urllib.parse import urlsplit

import pytest
from test_app_navigation_browser import browser
from test_account_collections import FAVORITES, forbidden

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('width', [320, 1440])
@pytest.mark.parametrize('language', ['es', 'en', 'fr'])
@pytest.mark.parametrize('javascript', [True, False])
@pytest.mark.parametrize('role', ['client', 'admin'])
def test_collection_get_journey(browser, app_module, monkeypatch, tmp_path, width, language, javascript, role):
    monkeypatch.setattr(app_module,'current_session_user',lambda:{'id':'qa-collections','role':'ADMIN' if role=='admin' else 'CLIENT','membership':'FREE'})
    monkeypatch.setattr(app_module,'is_admin_session',lambda:role=='admin')
    monkeypatch.setattr(app_module,'get_favorites',lambda **kw:FAVORITES)
    monkeypatch.setattr(app_module,'favorite_feed_full',lambda **kw:{'matches':[],'live':[],'picks':[]})
    monkeypatch.setattr(app_module,'favorite_insights',lambda **kw:{'by_kind':{kind:[] for kind in ('team','league','match')}})
    monkeypatch.setattr(app_module,'list_backups',lambda:[{
        'name':'database_synthetic_20261009.db','created_at':'2026-10-09T04:30:00+02:00','size_mb':1,'valid':True}])
    monkeypatch.setattr(app_module,'backup_dir',lambda:'/synthetic/backups')
    monkeypatch.setattr(app_module,'automation_get_bounded',lambda *a:{'time':'2026-10-09T04:30:00+02:00','result':{'ok':False,'failure_stage':'INTEGRITY'}})
    for name in ('dashboard_data','add_favorite','remove_favorite','create_database_backup','restore_database_backup'):
        monkeypatch.setattr(app_module,name,forbidden)
    path='/favoritos' if role=='client' else '/admin/backups'
    context=browser.new_context(viewport={'width':width,'height':950},java_script_enabled=javascript,locale=language,service_workers='block')
    page=context.new_page()
    calls,errors=[],[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    def serve(route):
        url=urlsplit(route.request.url)
        calls.append((route.request.method,url.path))
        if url.netloc!='collections.invalid':
            route.abort();return
        if url.path==path:
            with app_module.app.test_request_context(url.path+'?'+url.query,headers={'Accept-Language':language}):
                html=app_module.favorites_page() if role=='client' else app_module.admin_backups_page()
            # Full HTTP QA separately covers all application JavaScript. This
            # fixture isolates the collection from unrelated PWA/realtime work.
            html=re.sub(r'<script\b([^>]*)>.*?</script>',lambda m:m.group(0) if any(
                name in m[1] for name in ('application/json','app-navigation.js','ui-localization.js','v930-icons.js')) else '',html,flags=re.S|re.I)
            route.fulfill(status=200,content_type='text/html; charset=utf-8',body=html);return
        if url.path.startswith('/static/'):
            asset=(ROOT/url.path.lstrip('/')).resolve()
            if asset.is_relative_to(ROOT/'static') and asset.is_file():
                route.fulfill(status=200,content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream',body=asset.read_bytes());return
        route.fulfill(status=200,content_type='text/html',body='<p>SIMULATED_QA</p>')
    page.route('**/*',serve)
    try:
        page.goto('https://collections.invalid'+path)
        assert page.locator('html').get_attribute('lang')==language
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        if role=='client':
            assert page.locator('.favorite-item').count()==3
            page.locator('#favorite-query').fill('atletico')
            page.locator('#favorite-kind').select_option('team')
            with page.expect_navigation():
                page.locator('.collection-toolbar button').press('Enter')
            assert page.locator('.favorite-item').count()==1
            assert 'Atlético Madrid' in page.locator('.favorite-item').inner_text()
            page.locator('#favorite-query').fill('zzmissing')
            with page.expect_navigation():
                page.locator('.collection-toolbar button').press('Enter')
            assert page.locator('.favorite-item').count()==0
            with page.expect_navigation():
                page.locator('.collection-toolbar a').press('Enter')
            assert page.locator('.favorite-item').count()==3
        else:
            assert page.locator('[data-tone="warning"]').is_visible()
            assert not page.locator('button[type="submit"]').first.is_visible()
            if javascript:
                page.locator('.backup-row summary').click()
            else:
                page.locator('.backup-row summary').press('Enter')
            assert page.locator('input[name="action"][value="restore"]').count()==1
            assert page.locator('form input[name="csrf_token"]').first.get_attribute('value')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        page.screenshot(path=str(tmp_path/f'{role}-{width}-{language}-{javascript}.png'),full_page=True)
        assert not errors
        assert all(method=='GET' for method,_ in calls)
    finally:
        context.close()
