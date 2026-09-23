"""Native catalogue controls are explicitly owned by the existing manual form.

Offline browser DOM and real Flask handler; no HTTP provider or production data.
"""
from pathlib import Path
import sqlite3

import pytest
from werkzeug.datastructures import MultiDict
from engines.navigation_integrity_engine import _NavigationHTMLParser
from test_combi_advisor_contract import db
from test_combi_routes_and_browser import webapp, login, browser
from test_combi_match_catalogue import quotes

ROOT = Path(__file__).resolve().parents[1]
FORM = 'combi-manual-builder'


def test_partial_declares_a_real_form_owner_to_navigation_auditor():
    source = (ROOT / 'templates/components/combi_match_catalogue.html').read_text()
    parser = _NavigationHTMLParser('combi_match_catalogue.html')
    parser.feed(source)
    assert not [item for item in parser.entries if item['kind'] == 'button']
    # Removing the declared owner must still be caught by the unmodified auditor.
    broken = _NavigationHTMLParser('combi_match_catalogue.html')
    broken.feed(source.replace(' form="'+FORM+'"', ''))
    assert [item for item in broken.entries if item['kind'] == 'button']


@pytest.mark.parametrize('control', ['search', 'previous', 'next'])
def test_browser_control_submits_selection_and_amount_to_same_handler(browser, webapp, db, monkeypatch, control):
    from engines import combi_match_catalogue
    monkeypatch.setattr(combi_match_catalogue, 'PAGE_SIZE', 1)
    quotes(db)
    with sqlite3.connect(db) as conn:
        conn.execute('DELETE FROM picks')
    client = webapp.test_client()
    login(client)
    html = client.get('/combinadas?page=2').get_data(as_text=True)
    context = browser.new_context(java_script_enabled=False)
    try:
        page = context.new_page()
        page.route('**/*', lambda route: route.abort())
        page.set_content(html)
        assert page.locator('#'+FORM).count() == 1
        page.locator('[name=stake]').first.fill('19,37')
        chosen = page.locator('[data-market-choice]').first
        chosen.check()
        chosen_id = chosen.get_attribute('value')
        selector = {'search':'button[name=action][value=browse]',
                    'previous':'button[name=page][value="1"]',
                    'next':'button[name=page][value="3"]'}[control]
        button = page.locator(selector)
        assert button.evaluate('(b)=>b.form && b.form.id') == FORM
        if control == 'search':
            page.locator('input[name=q]').fill('Local 17')
        # FormData with the submitter reproduces the native successful controls,
        # including csrf, all selected IDs and the specific paging/search action.
        pairs = button.evaluate('(b)=>Array.from(new FormData(b.form,b).entries())')
        response = client.post('/combinadas', data=MultiDict(pairs))
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert 'value="19,37"' in body
        assert 'value="'+chosen_id+'" checked' in body
        assert 'Tu selección en otros resultados' in body
        with sqlite3.connect(db) as conn:
            assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='client_combi_drafts'").fetchone()
    finally:
        context.close()
