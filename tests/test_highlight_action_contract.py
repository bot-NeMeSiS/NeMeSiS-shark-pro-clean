"""The declared navigation action is the real player binding, not an audit-only label."""
from pathlib import Path
import os

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright
from engines.navigation_integrity_engine import _NavigationHTMLParser

ROOT = Path(__file__).resolve().parents[1]


def rendered_player():
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=select_autoescape())
    return str(env.get_template('components/highlight_player.html').module.highlight_player({
        'can_embed': True, 'can_link': True, 'decision': 'APPROVED',
        'title': 'SIMULATED_QA', 'embed_url': 'https://www.youtube-nocookie.com/embed/officialQA1',
        'original_url': 'https://www.youtube.com/watch?v=officialQA1',
    }))


def test_player_action_is_declared_for_existing_navigation_auditor():
    source = rendered_player()
    parser = _NavigationHTMLParser('highlight_player.html')
    parser.feed(source)
    assert not [entry for entry in parser.entries if entry['kind'] == 'button']
    parser = _NavigationHTMLParser('highlight_player.html')
    parser.feed(source.replace('data-action="highlight-player-toggle"', ''))
    assert len([entry for entry in parser.entries if entry['kind'] == 'button']) == 1


@pytest.mark.parametrize('declared', [True, False])
def test_player_only_enables_when_real_action_is_bound(declared):
    with sync_playwright() as pw:
        path = os.getenv('NEMESIS_QA_CHROMIUM')
        options = {'headless': True, 'args': ['--no-sandbox']}
        if path:
            options['executable_path'] = path
        elif Path('/usr/bin/chromium').exists():
            options['executable_path'] = '/usr/bin/chromium'
        browser = pw.chromium.launch(**options)
        try:
            page = browser.new_page()
            page.route('**/*', lambda route: route.abort())
            source = rendered_player()
            if not declared:
                source = source.replace('data-action="highlight-player-toggle"', '')
            page.set_content(source)
            page.add_script_tag(path=str(ROOT / 'static/highlights-player.js'))
            button = page.locator('[data-highlight-load]')
            assert button.is_visible() is declared
            if declared:
                button.click()
                assert page.locator('iframe').count() == 1
                button.click()
            assert page.locator('iframe').count() == 0
        finally:
            browser.close()
