"""Integration of existing combinadas into the client navigation, not a new app.

Fixtures use SQLite and synthetic accounts/quotes. Browser cases render the real
shell/templates but abort external requests: they check UI, not production speed.
"""
from pathlib import Path
import json
import sqlite3
import secrets
from datetime import datetime, timedelta, timezone

import pytest
from html.parser import HTMLParser
from dataclasses import dataclass
import re

from test_combi_advisor_contract import db, NOW, preview_values
from test_combi_routes_and_browser import webapp, login, browser

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Element:
    tag: str
    attrs: dict
    parents: list


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.items, self.stack = [], []
        self.feed(html.decode() if isinstance(html, bytes) else str(html))

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        self.items.append(Element(tag, attrs, list(self.stack)))
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append((tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack)-1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def find(self, tag, **attributes):
        return [e for e in self.items if e.tag == tag and
                all(k in e.attrs and (v is None or e.attrs[k] == v) for k,v in attributes.items())]


def checked(response):
    return [el.attrs['value'] for el in Elements(response.data).find('input',type='checkbox',name='pick_ids',checked=None)]


def test_match_entry_requires_one_explicit_outcome(webapp, db):
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE picks SET match_id='m1',home_team='Local 1',away_team='Visitante 1',selection='X' WHERE id='p2'")
    before = Path(db).read_bytes()
    c = webapp.test_client(); login(c)
    response = c.get('/combinadas?match_id=m1')
    assert response.status_code == 200
    assert checked(response) == []
    assert 'Elige solo una' in response.get_data(as_text=True)
    assert Path(db).read_bytes() == before


def test_pick_entry_takes_priority_over_match_query(webapp):
    c = webapp.test_client(); login(c)
    assert checked(c.get('/combinadas?pick=p1&match_id=m2')) == ['p1']


def test_invalid_pick_never_falls_back_to_another_match(webapp):
    c = webapp.test_client(); login(c)
    response = c.get('/combinadas?pick=missing&match_id=m1')
    assert checked(response) == []
    assert 'no está disponible' in response.get_data(as_text=True)


def test_single_match_entry_selects_one_but_saves_nothing(webapp, db):
    before = Path(db).read_bytes()
    c = webapp.test_client(); login(c)
    assert checked(c.get('/combinadas?match_id=m1')) == ['p1']
    assert Path(db).read_bytes() == before


def test_linked_pick_is_in_first_visible_group(webapp):
    c = webapp.test_client(); login(c)
    response = c.get('/combinadas?pick=p1')
    chosen = Elements(response.data).find('input',type='checkbox',value='p1')[0]
    assert 'checked' in chosen.attrs
    assert not any(tag == 'details' for tag,attrs in chosen.parents)


def test_preserved_large_selection_opens_its_remaining_options(webapp):
    c = webapp.test_client(); token = login(c)
    response = c.post('/combinadas', data={'pick_ids':['p'+str(i) for i in range(1,17)], 'stake':'19,37', 'csrf_token':token})
    assert response.status_code == 400
    elements = Elements(response.data)
    selected = elements.find('input',type='checkbox',checked=None)
    assert len(selected) == 16
    for item in selected:
        assert all('open' in attrs for tag,attrs in item.parents if tag == 'details')
    assert elements.find('input',name='stake')[0].attrs['value'] == '19,37'


def test_subnavigation_is_present_without_any_eligible_picks(webapp, db):
    with sqlite3.connect(db) as conn: conn.execute('DELETE FROM picks')
    c = webapp.test_client(); login(c)
    response = c.get('/combinadas')
    elements = Elements(response.data)
    assert len(elements.find('nav',**{'data-picks-workspace-nav':None})) == 1
    assert elements.find('a',**{'aria-current':'page'})[0].attrs['href'] == '/combinadas'
    assert elements.find('a',href='/combinadas#combinadas-guardadas')


def test_denied_pick_entry_does_not_leak_premium_label(webapp, db):
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE picks SET membership_required='ELITE',selection='private-selection' WHERE id='p1'")
    c = webapp.test_client(); login(c,'b')
    response = c.get('/combinadas?pick=p1')
    assert checked(response) == []
    assert 'private-selection' not in response.get_data(as_text=True)


@pytest.mark.parametrize('path',['/combis','/combinadas','/combinadas?borrador=abc'])
@pytest.mark.parametrize('authenticated',[False,True])
def test_mobile_keeps_five_items_and_marks_picks_section(app_module,path,authenticated):
    with app_module.app.test_request_context(path):
        macro = app_module.app.jinja_env.get_template('components/v933_navigation.html').module
        elements = Elements(macro.v933_mobile_bottom_nav(authenticated))
        assert len(elements.find('a')) == 5
        current = elements.find('a',**{'aria-current':None})
        assert len(current) == 1 and current[0].attrs['href'] == '/picks'
        assert current[0].attrs['aria-current'] == 'true'  # current section, not the Picks page


@pytest.mark.parametrize('path',['/combis','/combinadas'])
@pytest.mark.parametrize('kind',['public','client'])
def test_desktop_marks_same_section_without_extra_primary_items(app_module,path,kind):
    with app_module.app.test_request_context(path):
        macro = app_module.app.jinja_env.get_template('components/v933_navigation.html').module
        html = macro.v933_client_navigation('PRO') if kind == 'client' else macro.v933_public_navigation()
        current = Elements(html).find('a',**{'aria-current':None})
        assert len(current) == 1 and current[0].attrs['href'] == '/picks'


@pytest.mark.parametrize('path,href',[('/picks','/picks'),('/calendar','/calendar'),('/profile','/profile'),('/app','/app')])
def test_other_primary_destinations_keep_their_current_page(app_module,path,href):
    with app_module.app.test_request_context(path):
        macro = app_module.app.jinja_env.get_template('components/v933_navigation.html').module
        elements = Elements(macro.v933_mobile_bottom_nav(True))
        assert elements.find('a',**{'aria-current':'page'})[0].attrs['href'] == href


@pytest.fixture
def client_pages(app_module):
    """Render actual app routes against the isolated pytest DB, never a live user."""
    app = app_module.app
    c = app.test_client(); c.get('/combinadas')
    ident = 'combi-navigation-qa-' + secrets.token_hex(8)
    now = datetime.now(timezone.utc)
    with sqlite3.connect(app_module.DB_PATH) as conn:
        conn.execute('INSERT INTO users(id,email,password_hash,role,membership,created_at) VALUES (?,?,?,?,?,?)',
                     (ident,ident+'@example.invalid','unusable-test-hash','PRO','PRO',now.isoformat()))
    try:
        with c.session_transaction() as sess:
            sess['user_id'] = ident; sess['user_role'] = 'PRO'; sess['membership'] = 'PRO'
        output = {}
        for path in ['/app','/profile','/picks','/combinadas','/combis']:
            res = c.get(path)
            assert res.status_code == 200, (path,res.status_code)
            output[path] = res.get_data(as_text=True)
        yield output
    finally:
        with sqlite3.connect(app_module.DB_PATH) as conn:
            conn.execute('DELETE FROM users WHERE id=?',(ident,))
        app_module.invalidate_v934_realtime_cache('v934:sports:')


def test_actual_home_account_and_picks_reach_one_combi_screen(client_pages,app_module):
    home = Elements(client_pages['/app'])
    account = Elements(client_pages['/profile'])
    shortcuts = [e for e in home.find('a') if any('ns16-home-actions' in a.get('class','').split() for t,a in e.parents)]
    assert any(e.attrs['href'] == '/combinadas' for e in shortcuts)
    assert len(shortcuts) == 3
    assert account.find('a',href='/combinadas#combinadas-guardadas')
    assert account.find('a',href='/memberships')  # plan access is retained
    for route in ('/combis','/combinadas','/picks'):
        assert len(Elements(client_pages[route]).find('nav',**{'data-picks-workspace-nav':None})) == 1
    app = app_module.app
    assert app.view_functions['combis_page'] is app.view_functions['architecture.client_combis.page']
    assert len([r for r in app.url_map.iter_rules() if r.rule == '/combinadas']) == 1


@pytest.mark.parametrize('width',[320,390,430,1366])
def test_real_client_shell_workspace_is_visible_and_usable(browser,client_pages,width,tmp_path):
    from urllib.parse import urlsplit
    page = browser.new_page(viewport={'width':width,'height':844})
    page.route('**/*',lambda route:route.abort())
    html = client_pages['/combinadas']
    css = []
    for link in Elements(html).find('link',rel='stylesheet'):
        path = urlsplit(link.attrs.get('href','')).path
        if path.startswith('/static/') and (ROOT/path.lstrip('/')).is_file():
            css.append((ROOT/path.lstrip('/')).read_text())
    # Test-only extraction of static markup. Actual dependencies remain unchanged.
    html = re.sub(r'<script\b[^>]*>[\s\S]*?</script>', '', html)
    html = re.sub(r'<link\b[^>]*>', '', html)
    page.set_content(html)
    page.add_style_tag(content='\n'.join(css))
    nav = page.locator('[data-picks-workspace-nav]')
    assert nav.is_visible()
    for item in nav.locator('a').all():
        assert item.bounding_box()['height'] >= 44
    assert nav.locator('[aria-current=page]').get_attribute('href') == '/combinadas'
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    nav.locator('a').first.focus()
    page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement.textContent.trim()') == 'Combinadas'
    if width < 768:
        assert page.locator('[data-nav-zone=client-bottom]').is_visible()
        assert page.locator('[data-nav-zone=client-bottom] [aria-current=true]').get_attribute('href') == '/picks'
    page.locator('.ns-combis').evaluate("el=>el.insertAdjacentHTML('afterbegin','<p style=\"color:white;position:relative;z-index:9999\">SIMULATED_QA · cuenta y datos temporales; no producción</p>')")
    import os
    out = Path(os.environ.get('NEMESIS_COMBI_INTEGRATION_EVIDENCE',str(tmp_path)));out.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(out/f'combinadas-integracion-{width}.png'),full_page=True)
    page.close()


def test_oversized_pick_link_does_not_silently_truncate_or_fall_back(webapp):
    c = webapp.test_client(); login(c)
    response = c.get('/combinadas',query_string={'pick':'p1'+'x'*180,'match_id':'m1'})
    assert checked(response) == []
    assert 'no está disponible' in response.get_data(as_text=True)
