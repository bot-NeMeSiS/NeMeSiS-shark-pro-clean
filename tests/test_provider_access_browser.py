"""Rendered provider evidence on desktop/mobile, with no outbound traffic."""
import mimetypes
from pathlib import Path
import re
from urllib.parse import urlsplit

import pytest
from test_app_navigation_browser import browser
from test_provider_access_clarity import admin_evidence


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('width', [320, 1440])
@pytest.mark.parametrize('javascript', [True, False])
@pytest.mark.parametrize('language,expected', [('es','Suspensión comunicada'), ('en','Suspension reported'), ('fr','Suspension signalée')])
def test_provider_observations_readable_without_calls(browser, app_module, monkeypatch, tmp_path, width, javascript, language, expected):
    health = admin_evidence(monkeypatch, app_module)
    monkeypatch.setattr(app_module, 'is_admin_session', lambda: True)
    monkeypatch.setattr(app_module, 'current_session_user', lambda: {'id':'qa-provider','role':'ADMIN'})
    with app_module.app.test_request_context('/admin/data-center', headers={'Accept-Language':language}):
        markup = app_module.render_template('admin_data_center.html', data={'provider_health':health}, message='', result=None)
    # Test this read-only presentation; unrelated realtime/PWA scripts are
    # covered separately by the repository's full HTTP navigation gate.
    markup = re.sub(r'<script\b([^>]*)>.*?</script>', lambda m: m.group(0) if any(
        name in m[1] for name in ('application/json','app-navigation.js','ui-localization.js','v930-icons.js')) else '', markup, flags=re.S|re.I)
    context = browser.new_context(viewport={'width':width,'height':950}, java_script_enabled=javascript, locale=language, service_workers='block')
    page = context.new_page()
    calls, errors = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    def serve(route):
        url = urlsplit(route.request.url)
        calls.append((route.request.method, url.path))
        if url.netloc != 'provider-evidence.invalid':
            route.abort(); return
        if url.path == '/admin/data-center':
            route.fulfill(status=200, content_type='text/html; charset=utf-8', body=markup); return
        if url.path.startswith('/static/'):
            asset = (ROOT/url.path.lstrip('/')).resolve()
            if asset.is_relative_to(ROOT/'static') and asset.is_file():
                route.fulfill(status=200, content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream', body=asset.read_bytes()); return
        route.fulfill(status=200, content_type='text/html', body='<p>SIMULATED_QA</p>')
    page.route('**/*', serve)
    try:
        page.goto('https://provider-evidence.invalid/admin/data-center')
        assert page.locator('html').get_attribute('lang') == language
        assert expected in page.locator('#provider-health').inner_text()
        assert page.locator('[data-provider-observation="REUSED"]').count() == 2
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        assert page.locator('#provider-health form input[name="csrf_token"]').first.get_attribute('value')
        card = page.locator('.provider-health-card').first
        assert not card.locator('button[type="submit"]').is_visible()
        card.locator('summary').focus()
        card.locator('summary').press('Enter')
        assert card.locator('button[type="submit"]').is_visible()
        assert card.locator('button[type="submit"]').bounding_box()['height'] >= 43.9
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        assert not errors
        assert all(method == 'GET' and not path.endswith('/check') for method, path in calls)
        # Element screenshots wait for animation frames that disabled-JS pages
        # cannot emit in some Chromium versions. Page capture needs no script.
        page.screenshot(path=str(tmp_path/f'provider-{width}-{language}-{javascript}.png'), full_page=True)
    finally:
        context.close()
