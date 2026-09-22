"""Private review HTTP and component flows; synthetic accounts, offline browser."""
from html.parser import HTMLParser
import sqlite3

import pytest

from test_combi_routes_and_browser import webapp, db, browser, login
from test_combi_advisor_contract import NOW, ready_save, preview_values
from engines import client_combi_store as store
from engines.combi_draft_review import review_draft


@pytest.fixture(autouse=True)
def fixed_review_time(monkeypatch):
    import blueprints.client_combis as bp
    monkeypatch.setattr(bp, 'review_draft', lambda *args: review_draft(*args, now=NOW))


@pytest.fixture
def saved(webapp, db):
    # webapp fixture already pins the store's time for all route calls.
    result = store.make_preview(db, 'a', preview_values())
    import secrets
    values = {**preview_values(), 'revision':result['revision'], 'request_id':secrets.token_hex(16)}
    return store.save_draft(db, 'a', values)['id']


class Inputs(HTMLParser):
    def __init__(self, content):
        super().__init__(); self.inputs = []; self.feed(content)
    def handle_starttag(self, tag, attrs):
        if tag == 'input': self.inputs.append(dict(attrs))


def test_error_does_not_reset_amount_or_selections(webapp):
    client = webapp.test_client(); token = login(client, 'b')
    response = client.post('/combinadas', data={'csrf_token':token,'pick_ids':['p1','p2','p3','p4'],'stake':'19,37'})
    assert response.status_code == 400  # PRO permits 3, but retain the user's edits.
    inputs = Inputs(response.get_data(as_text=True)).inputs
    assert next(i for i in inputs if i.get('name')=='stake')['value'] == '19,37'
    selected = [i['value'] for i in inputs if i.get('type')=='checkbox' and 'checked' in i]
    assert selected == ['p1','p2','p3','p4']


def test_ineligible_selection_is_preserved_until_user_removes_it(webapp, db):
    with sqlite3.connect(db) as conn: conn.execute("UPDATE picks SET status='draft' WHERE id='p1'")
    c = webapp.test_client(); t = login(c)
    response = c.post('/combinadas', data={'csrf_token':t,'pick_ids':['p1','p2'],'stake':'0,12'})
    assert response.status_code == 409
    html = response.get_data(as_text=True)
    assert 'Se conservan marcadas' in html
    inputs = Inputs(html).inputs
    assert {i['value'] for i in inputs if i.get('type')=='checkbox' and 'checked' in i} == {'p1','p2'}


@pytest.mark.parametrize('page', [False, True])
def test_review_private_and_read_only(webapp, db, saved, page):
    a, b = webapp.test_client(), webapp.test_client(); login(a); login(b,'b')
    url = '/combinadas?borrador='+saved if page else '/api/client/combinadas/'+saved+'/review'
    before = open(db,'rb').read()
    response = a.get(url)
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'private, no-store' and 'Cookie' in response.headers['Vary']
    assert b.get(url).status_code == 404
    assert webapp.test_client().get(url).status_code == 401
    assert open(db,'rb').read() == before


def test_review_page_links_and_preview_without_automatic_save(webapp, saved):
    c = webapp.test_client(); login(c)
    html = c.get('/combinadas').get_data(as_text=True)
    assert '/combinadas?borrador='+saved in html
    response = c.get('/combinadas?borrador='+saved)
    html = response.get_data(as_text=True)
    assert 'data-combi-review=' in html and 'Guardar borrador privado' in html
    assert len(c.get('/api/client/combinadas').json['saved']) == 1


def test_quote_changed_after_review_is_rejected_before_save(webapp, db, saved):
    import secrets
    c = webapp.test_client(); token = login(c)
    reviewed = c.get('/api/client/combinadas/'+saved+'/review').json['review']
    with sqlite3.connect(db) as conn: conn.execute("UPDATE picks SET odds='2.4' WHERE id='p1'")
    response = c.post('/api/client/combinadas/save', json={**preview_values(),'csrf_token':token,
                      'revision':reviewed['preview']['revision'],'request_id':secrets.token_hex(16)})
    assert response.status_code == 409
    assert len(c.get('/api/client/combinadas').json['saved']) == 1


def test_reflected_form_text_is_escaped(webapp):
    c = webapp.test_client(); token = login(c)
    response = c.post('/combinadas',data={'csrf_token':token,'pick_ids':['p1','p2'], 'stake':'"><script>alert(1)</script>'})
    assert response.status_code == 400
    assert '<script>alert(1)</script>' not in response.get_data(as_text=True)


@pytest.mark.parametrize('width', [320,390,430,1366])
def test_review_mobile_components(browser,webapp,db,saved,width,tmp_path):
    from pathlib import Path
    c = webapp.test_client(); login(c)
    with sqlite3.connect(db) as conn: conn.execute("UPDATE picks SET odds='1.8' WHERE id='p1'")
    html = c.get('/combinadas?borrador='+saved).get_data(as_text=True)
    page = browser.new_page(viewport={'width':width,'height':844})
    page.route('**/*',lambda route:route.abort())
    page.set_content(html)
    root = Path(__file__).resolve().parents[1]
    page.add_style_tag(content='body{margin:12px;background:#08101c;color:#edf4fc;font-family:Arial}*{box-sizing:border-box}'+(root/'static/combinadas.css').read_text())
    assert page.locator('[data-combi-review]').is_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert page.get_by_role('button',name='Guardar borrador privado').bounding_box()['height']>=44
    page.evaluate("document.body.insertAdjacentHTML('afterbegin','<p>SIMULATED_QA · no es producción</p>')")
    page.screenshot(path=str(tmp_path/f'combi-review-{width}.png'),full_page=True)
    page.close()


def test_no_javascript_review_does_not_require_background_requests(browser,webapp,saved):
    c=webapp.test_client();login(c)
    context=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
    page=context.new_page();page.route('**/*',lambda route:route.abort())
    page.set_content(c.get('/combinadas?borrador='+saved).get_data(as_text=True))
    assert page.locator('[data-combi-review]').is_visible()
    assert page.get_by_role('button',name='Guardar borrador privado').is_visible()
    context.close()


def test_over_limit_form_keeps_all_visible_choices(webapp):
    c = webapp.test_client(); t = login(c)
    ids = ['p'+str(i) for i in range(1,17)]
    response = c.post('/combinadas', data={'csrf_token':t,'pick_ids':ids,'stake':'0,10'})
    assert response.status_code == 400
    selected = [i['value'] for i in Inputs(response.get_data(as_text=True)).inputs
                if i.get('type') == 'checkbox' and 'checked' in i]
    assert set(selected) == set(ids)
