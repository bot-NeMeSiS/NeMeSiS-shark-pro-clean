"""Exact artwork delivery repair; no provider traffic, no database writes."""
from copy import deepcopy
from html.parser import HTMLParser
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
import pytest

ROOT = Path(__file__).resolve().parents[1]
UNAVAILABLE = 'https://www.thesportsdb.com/images/media/team/badge/xdfie41784675774.png'
REPLACEMENT = 'https://r2.thesportsdb.com/images/media/team/badge/wq9sir1639406443.png'


class Images(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.images = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.images.append(dict(attrs))


def render(identity, name='Barcelona', fallback='/team-crest.svg?name=Barcelona'):
    env = Environment(loader=FileSystemLoader(ROOT/'templates'), autoescape=select_autoescape(['html']))
    env.filters['team_crest_url'] = lambda value: fallback
    env.filters['team_identity'] = lambda value, side: {}
    return str(env.get_template('partials/team_identity.html').module.crest(identity, name, 'mega'))


def test_exact_unavailable_asset_uses_verified_provider_artwork_without_mutation():
    identity = {'crest_url': UNAVAILABLE, 'provider': 'thesportsdb', 'has_real_logo': True, 'initials': 'FCB'}
    before = deepcopy(identity)
    image = Images(render(identity)).images[0]
    assert image['src'] == REPLACEMENT
    assert image['loading'] == 'lazy'
    assert "crest-image-error" in image['onerror']
    assert identity == before


@pytest.mark.parametrize('url', [
    REPLACEMENT, '/team-crest.svg?name=Barcelona',
    'https://www.thesportsdb.com/images/media/team/badge/another.png',
    'https://r2.thesportsdb.com/images/media/team/badge/xdfie41784675774.png',
    'https://other.invalid/images/media/team/badge/xdfie41784675774.png',
    UNAVAILABLE+'?variant=unverified', UNAVAILABLE+'/tiny',
])
def test_other_artwork_is_not_rewritten(url):
    assert Images(render({'crest_url': url})).images[0]['src'] == url


def test_missing_logo_and_escaped_text_keep_existing_fallback_contract():
    name = '<script>test</script>"'
    markup = render({}, name)
    assert '<script>' not in markup
    assert '&lt;script&gt;' in markup
    assert '<em aria-hidden="true">' in markup
    assert Images(markup).images[0]['alt'] == name


def test_repair_also_applies_to_the_existing_fallback_resolver_output():
    assert Images(render({}, fallback=UNAVAILABLE)).images[0]['src'] == REPLACEMENT


@pytest.mark.parametrize('width', [390, 1366])
@pytest.mark.parametrize('javascript', [True, False])
def test_browser_loads_repaired_image_without_requesting_the_missing_asset(width, javascript):
    from playwright.sync_api import sync_playwright
    # In-memory markup, intercepted image response: no network/provider credentials.
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64"/></svg>'
    requests = []
    with sync_playwright() as pw:
        executable = os.environ.get('NEMESIS_QA_CHROMIUM')
        browser = pw.chromium.launch(headless=True, **({'executable_path': executable} if executable else {}))
        context = browser.new_context(viewport={'width':width,'height':844}, java_script_enabled=javascript, service_workers='block')
        def intercept(route):
            requests.append((route.request.method, route.request.url))
            assert route.request.method == 'GET'
            assert route.request.url == REPLACEMENT
            route.fulfill(status=200, content_type='image/svg+xml', body=svg)
        context.route('**/*', intercept)
        page = context.new_page()
        try:
            page.set_content('<!doctype html><html><head><meta name="viewport" content="width=device-width"></head><body>'+render({'crest_url':UNAVAILABLE})+'</body></html>', wait_until='load')
            image = page.locator('img')
            image.scroll_into_view_if_needed()
            page.wait_for_function('document.images[0].complete && document.images[0].naturalWidth > 0')
            assert image.get_attribute('src') == REPLACEMENT
            assert requests == [('GET',REPLACEMENT)]
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        finally:
            context.close();browser.close()
