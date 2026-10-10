"""Offline regressions for the real browser gate; no production or provider calls."""
from html import escape
import os
import shutil
from urllib.parse import urlsplit

import pytest

from tools.run_production_quality_browser_gate import (
    ACTIVE_VERSION, MOBILE_NAV, PUBLIC_NAV, _active_css_contract,
    _click_journey, _navigation_destination_matches, _page_evidence,
)

BASE = 'https://gate.invalid'
HREF = '/static/product-system.css?v=' + ACTIVE_VERSION + '-canonical-core-4-home-leagues'
MARKUP = '<link rel="stylesheet" href="' + HREF + '">'


def evidence():
    return {'stylesheets': [{'href': HREF, 'url': BASE+HREF, 'active': True}], 'resources': [BASE+HREF]}


def test_current_canonical_css_requires_rendered_link_and_loaded_rules():
    assert _active_css_contract(MARKUP, evidence(), BASE, ACTIVE_VERSION) == (True, HREF)


@pytest.mark.parametrize('change', ['absent', 'unloaded', 'inactive', 'wrong-origin', 'duplicate-dom', 'wrong-dom-href'])
def test_css_rejects_missing_or_unproven_dom_evidence(change):
    metrics = evidence()
    if change == 'absent': metrics['stylesheets'] = []
    elif change == 'unloaded': metrics['resources'] = []
    elif change == 'inactive': metrics['stylesheets'][0]['active'] = False
    elif change == 'wrong-origin': metrics['stylesheets'][0]['url'] = 'https://other.invalid'+HREF
    elif change == 'duplicate-dom': metrics['stylesheets'] *= 2
    elif change == 'wrong-dom-href': metrics['stylesheets'][0]['href'] = '/static/other.css'
    assert _active_css_contract(MARKUP, metrics, BASE, ACTIVE_VERSION)[0] is False


@pytest.mark.parametrize('markup', [
    '', '<!--'+MARKUP+'-->', MARKUP+MARKUP,
    MARKUP.replace('product-system.css', 'app.css'),
    MARKUP+'<link rel="stylesheet" href="/static/app.css?v=legacy">',
    MARKUP.replace(ACTIVE_VERSION, 'V000_OUTDATED'),
    MARKUP.replace('rel="stylesheet"', 'rel="preload"'),
    MARKUP.replace('<link ', '<link disabled '),
    MARKUP.replace('<link ', '<link media="print" '),
    MARKUP.replace('href="/', 'href="https://other.invalid/'),
])
def test_css_does_not_accept_legacy_disabled_commented_or_stale_links(markup):
    assert _active_css_contract(markup, evidence(), BASE, ACTIVE_VERSION)[0] is False


@pytest.mark.parametrize('actual,passed', [
    (BASE+'/calendario?lane=finished', True),
    (BASE+'/calendario?lane=today', False),
    (BASE+'/calendario?lane=week', False),
    (BASE+'/calendario', False),
    (BASE+'/calendario?lane=finished&lane=today', False),
    (BASE+'/calendario?lane=finished&extra=', False),
    (BASE+'/calendario?lane=finished#other', False),
    (BASE+'/cliente-login', False),
    ('https://other.invalid/calendario?lane=finished', False),
    ('http://gate.invalid/calendario?lane=finished', False),
    ('https://[invalid', False),
])
def test_navigation_keeps_origin_and_calendar_filter(actual, passed):
    assert _navigation_destination_matches(BASE, '/calendario?lane=finished', actual) is passed


def test_query_order_is_not_a_false_navigation_failure():
    assert _navigation_destination_matches(BASE, '/calendario?lane=finished&q=Team+A', BASE+'/calendario?q=Team%20A&lane=finished')


@pytest.fixture(scope='module')
def contract_browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        executable = os.getenv('NEMESIS_QA_CHROMIUM') or shutil.which('chromium') or pw.chromium.executable_path
        browser = pw.chromium.launch(headless=True, executable_path=executable)
        yield browser
        browser.close()


def routed_page(browser, width, *, css_status=200, links=MARKUP, nav_links=None):
    context = browser.new_context(viewport={'width': width, 'height': 844}, service_workers='block')
    page = context.new_page()
    seen = []
    def route_handler(route):
        request = route.request
        seen.append((request.method, request.url))
        assert request.method == 'GET' and request.url.startswith(BASE+'/')
        path = urlsplit(request.url).path
        if path == '/static/product-system.css':
            route.fulfill(status=css_status, content_type='text/css', body='body{font-family:sans-serif;}a{display:inline-block;padding:12px;}')
        else:
            destinations = nav_links if nav_links is not None else (PUBLIC_NAV if width > 760 else MOBILE_NAV)
            zone = 'public-desktop' if width > 760 else 'client-bottom'
            nav = ''.join('<a href="'+escape(href, quote=True)+'">'+escape(href)+'</a>' for href in destinations)
            route.fulfill(status=200, content_type='text/html', body='<!doctype html><html><head>'+links+'</head><body><nav data-nav-zone="'+zone+'">'+nav+'</nav><main data-v933-surface="public">SIMULATED_QA</main></body></html>')
    page.route('**/*', route_handler)
    return context, page, seen


@pytest.mark.parametrize('width', [390, 1440])
def test_real_browser_clicks_filtered_calendar_and_observes_css(contract_browser, width):
    context, page, seen = routed_page(contract_browser, width)
    try:
        paths = PUBLIC_NAV if width > 760 else MOBILE_NAV
        zone = 'public-desktop' if width > 760 else 'client-bottom'
        journey = _click_journey(page, BASE, zone, paths)
        assert len(journey) == len(paths) and all(row['pass'] for row in journey)
        calendar = next(row for row in journey if row['href'].startswith('/calendario'))
        assert calendar['final_url'] == BASE+'/calendario?lane=finished'
        metrics = _page_evidence(page, BASE, '/')
        assert metrics['cssVersioned'] is True
        assert metrics['canonical_css_href'] == HREF
        assert seen and all(method == 'GET' and url.startswith(BASE+'/') for method, url in seen)
    finally:
        context.close()


@pytest.mark.parametrize('status,links', [
    (404, MARKUP), (200, MARKUP.replace('<link ', '<link disabled ')),
    (200, MARKUP.replace('<link ', '<link media="print" ')), (200, MARKUP+MARKUP),
])
def test_real_browser_rejects_unloaded_disabled_and_duplicate_css(contract_browser, status, links):
    context, page, _ = routed_page(contract_browser, 1440, css_status=status, links=links)
    try:
        assert _page_evidence(page, BASE, '/')['cssVersioned'] is False
    finally:
        context.close()


@pytest.mark.parametrize('destinations', [('/calendario?lane=today',), ('/calendario?lane=finished',)*2])
def test_real_browser_does_not_pass_wrong_or_duplicate_navigation(contract_browser, destinations):
    context, page, _ = routed_page(contract_browser, 1440, nav_links=destinations)
    try:
        result = _click_journey(page, BASE, 'public-desktop', ('/calendario?lane=finished',))
        assert result[0]['found'] is False and result[0]['pass'] is False
    finally:
        context.close()
