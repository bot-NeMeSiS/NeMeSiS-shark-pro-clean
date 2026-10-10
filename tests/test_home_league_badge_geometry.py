"""Offline Home badge regression: actual template, CSS and Chromium; synthetic logos."""
from pathlib import Path
import os
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape
import pytest

ROOT = Path(__file__).resolve().parents[1]
SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" fill="white"/><text x="8" y="40" fill="black">QA</text></svg>'


def render_badge(name='Liga QA', logo='/static/qa-logo.svg'):
    env = Environment(loader=FileSystemLoader(ROOT/'templates'), autoescape=select_autoescape(['html']))
    return str(env.get_template('components/home_league_badge.html').module.home_league_badge(name, logo, 'SIMULATED_QA'))


def test_home_badge_escapes_provider_text_and_preserves_loader_contract():
    markup = render_badge('<script>not executed</script>', '/static/qa.svg" onerror="bad')
    assert '<script>' not in markup
    assert '&lt;script&gt;' in markup and '&#34;' in markup
    assert 'referrerpolicy="no-referrer"' in markup
    assert 'style="--sports-crest-size:50px"' in markup
    assert 'data-fallback=' in markup and 'aria-hidden="true"' in markup
    assert '<img' not in render_badge(logo='')


@pytest.mark.parametrize('width', [320, 390, 1440])
@pytest.mark.parametrize('javascript', [True, False])
def test_home_badge_geometry_with_canonical_css(width, javascript):
    from playwright.sync_api import sync_playwright
    calls = []
    blocks = []
    for n, logo in enumerate(['data:image/svg+xml,'+quote(SVG), '']):
        blocks.append('<section class="home-competition-group home-league-tone-'+str(n)+'"><header class="home-competition-header"><div class="home-league-identity">'+render_badge('Liga de prueba '+str(n), logo)+'<div class="home-league-title"><h3>Liga de prueba '+str(n)+'</h3><p>DATOS SIMULADOS · QA</p></div></div></header></section>')
    markup = '<!doctype html><html lang="es"><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>'+ (ROOT/'static/product-system.css').read_text() +'</style></head><body class="ns-app"><main class="v933-page ns16-home home-agenda-focus"><section class="ns16-section ns16-home-sports"><h1>Prueba de logos · SIMULATED_QA</h1><div class="home-competition-list">'+''.join(blocks)+'</div></section></main></body></html>'
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path=os.getenv('NEMESIS_QA_CHROMIUM') or pw.chromium.executable_path)
        context = browser.new_context(viewport={'width':width, 'height':850}, java_script_enabled=javascript, service_workers='block')
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('**/*', lambda route: (calls.append(route.request.url), route.abort()))
        try:
            page.set_content(markup, wait_until='load')
            assert page.locator('.home-competition-group').count() == 2
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
            for badge in page.locator('.home-competition-header .v933-competition-logo').all():
                box = badge.bounding_box()
                crest = badge.locator('.crest').bounding_box()
                assert box and crest
                assert box['width'] >= 49 and box['height'] >= 49
                assert crest['width'] >= 49 and crest['height'] >= 49
            good = page.locator('img').first
            good.scroll_into_view_if_needed()
            page.wait_for_function('Array.from(document.images).some(i=>i.naturalWidth>0)')
            box = good.bounding_box()
            assert box and box['width'] >= 36 and box['height'] >= 36
            empty = page.locator('.home-competition-group').last.locator('.crest')
            assert empty.locator('em').is_visible()
            assert not errors
            assert not calls
            out = os.getenv('HOME_BADGE_QA_OUTPUT')
            if out:
                folder = Path(out); folder.mkdir(parents=True, exist_ok=True)
                page.evaluate('window.scrollTo(0,0)')
                page.screenshot(path=str(folder/f'badge-{width}-js-{javascript}.png'),full_page=True)
        finally:
            context.close(); browser.close()
