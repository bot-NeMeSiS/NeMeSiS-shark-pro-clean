"""Client routes + responsive components. SIMULATED_QA, no external traffic."""
from pathlib import Path
import json
import secrets
import os
import sqlite3

import pytest
from flask import Flask
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader, Environment, select_autoescape
from playwright.sync_api import sync_playwright

from test_combi_advisor_contract import db, NOW, preview_values, ready_save, fixture
from engines import client_combi_store as store
from engines.security_engine import generate_csrf_token
from blueprints.client_combis import create_client_combi_blueprint

ROOT=Path(__file__).resolve().parents[1]
BASE="<!doctype html><html lang='es'><meta name='viewport' content='width=device-width'><body>{% block content %}{% endblock %}</body></html>"
UI="{% macro page_header(a,b,c) %}<h1>{{ a }}</h1><p>{{ b }}</p>{% endmacro %}{% macro empty_state(a,b) %}<p>{{ a }} {{ b }}</p>{% endmacro %}"


@pytest.fixture
def webapp(db, monkeypatch):
    for name in ('read_center','make_preview','save_draft','read_advice'):
        original=getattr(store,name)
        monkeypatch.setattr(store,name,lambda *a,_f=original,**kw:_f(*a,now=NOW,**kw))
    app=Flask(__name__);app.secret_key=secrets.token_urlsafe(40);app.testing=True
    app.jinja_loader=ChoiceLoader([DictLoader({'base.html':BASE,'components/v933_ui.html':UI}),FileSystemLoader(ROOT/'templates')])
    app.jinja_env.filters['madrid_datetime_label']=lambda value:store.clock(value).astimezone(__import__('zoneinfo').ZoneInfo('Europe/Madrid')).strftime('%d/%m/%Y %H:%M') if store.clock(value) else 'Hora pendiente'
    @app.context_processor
    def token():
        from flask import session
        value=generate_csrf_token(session)
        return {'csrf_token':lambda:value}
    app.add_url_rule('/combis','combis_page',lambda:'OLD_GLOBAL_DATA')
    app.add_url_rule('/api/combis','api_combis',lambda:'OLD_GLOBAL_DATA')
    app.add_url_rule('/api/combis/build','api_combis_build',lambda:'OLD_UNSAFE_SAVE',methods=['POST'])
    app.add_url_rule('/api/shark/ask','api_shark_ask',lambda:'UNCHANGED_OTHER_INTENT',methods=['GET','POST'])
    app.register_blueprint(create_client_combi_blueprint(db))
    return app


def login(client,owner='a'):
    with client.session_transaction() as sess:
        sess['user_id']=owner
        return generate_csrf_token(sess)


@pytest.mark.parametrize('url',['/combis','/combinadas'])
def test_legacy_and_new_page_share_one_handler(webapp,url):
    c=webapp.test_client();token=login(c)
    response=c.get(url)
    assert response.status_code==200
    assert 'OLD_GLOBAL_DATA' not in response.get_data(as_text=True)
    assert b'NEMESIS-COMBI-ADVICE-V1' in response.data
    assert response.headers['Cache-Control']=='private, no-store'
    assert 'Cookie' in response.headers['Vary']
    assert len([r for r in webapp.url_map.iter_rules() if r.rule==url])==1


@pytest.mark.parametrize('url',['/api/combis','/api/client/combinadas'])
def test_api_list_requires_auth(webapp,url):
    assert webapp.test_client().get(url).status_code==401


@pytest.mark.parametrize('url',['/api/combis/build','/api/client/combinadas/preview','/api/client/combinadas/save'])
def test_auth_csrf_and_post_required(webapp,url):
    c=webapp.test_client()
    assert c.post(url,json=preview_values()).status_code==401
    assert c.get(url).status_code==405
    login(c)
    assert c.post(url,json=preview_values()).status_code==403


def test_cross_session_token_denied(webapp):
    a,b=webapp.test_client(),webapp.test_client();token=login(a);login(b,'b')
    assert b.post('/api/client/combinadas/preview',json={**preview_values(),'csrf_token':token}).status_code==403


def test_legacy_build_now_previews_without_writing(webapp,db):
    c=webapp.test_client();t=login(c)
    r=c.post('/api/combis/build',json={**preview_values(),'csrf_token':t,'odds':999,'total_odds':999})
    assert r.status_code==200 and r.json['combi']['total_odds']=='2.25'
    with sqlite3.connect(db) as con:assert not con.execute("SELECT 1 FROM sqlite_master WHERE name='client_combi_drafts'").fetchone()


def test_preview_save_and_private_list_complete_flow(webapp):
    a,b=webapp.test_client(),webapp.test_client();token=login(a);login(b,'b')
    body={**preview_values(),'csrf_token':token}
    p=a.post('/api/client/combinadas/preview',json=body).json['combi']
    body.update(revision=p['revision'],request_id=secrets.token_hex(16))
    saved=a.post('/api/client/combinadas/save',json=body)
    assert saved.status_code==201
    assert a.post('/api/client/combinadas/save',json=body).status_code==200
    assert len(a.get('/api/client/combinadas').json['saved'])==1
    assert b.get('/api/client/combinadas').json['saved']==[]


def test_preview_form_works_without_javascript(webapp):
    c=webapp.test_client();token=login(c)
    p=c.post('/combinadas',data={**preview_values(),'csrf_token':token})
    assert p.status_code==200
    html=p.get_data(as_text=True)
    assert 'Revisión SHARK' in html and 'Guardar borrador privado' in html
    assert 'name="revision"' in html and 'name="request_id"' in html


@pytest.mark.parametrize('body',[[],None,'text',1])
def test_malformed_json_rejected(webapp,body):
    c=webapp.test_client();login(c)
    assert c.post('/api/client/combinadas/preview',data=json.dumps(body),content_type='application/json').status_code==400


def test_oversize_payload_bounded(webapp):
    c=webapp.test_client();login(c)
    assert c.post('/api/client/combinadas/preview',json={'big':'a'*66000}).status_code==413


def test_advice_target_resolves_without_published_pick(webapp):
    r=webapp.test_client().get('/api/shark/combi-advice?match_id=m1')
    assert r.status_code==200 and r.json['advice']['pick'] is None
    assert r.json['advice']['team_form']['home']['sample_size']==0


def test_shared_helpers_present_and_no_binding_drift(webapp):
    assert webapp.extensions['nemesis_combi_routes']['legacy_build_is_preview_only']
    other=Flask('test-drift')
    other.add_url_rule('/wrong','combis_page',lambda:'')
    with pytest.raises(RuntimeError,match='Unexpected'):other.register_blueprint(create_client_combi_blueprint('unused'))


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as pw:
        options={'headless':True,'args':['--no-sandbox']}
        path=os.environ.get('NEMESIS_QA_CHROMIUM') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else '')
        if path: options['executable_path']=path
        b=pw.chromium.launch(**options)
        yield b;b.close()


@pytest.mark.parametrize('width',[320,390,430,1366])
def test_mobile_builder_component_interaction(browser,webapp,width,tmp_path):
    c=webapp.test_client();token=login(c)
    html=c.post('/combinadas',data={**preview_values(),'csrf_token':token}).get_data(as_text=True)
    page=browser.new_page(viewport={'width':width,'height':844})
    page.route('**/*',lambda route:route.abort())
    page.set_content(html)
    page.add_style_tag(content='body{margin:12px;background:#08101c;color:#edf4fc;font-family:Arial}*{box-sizing:border-box}'+(ROOT/'static/combinadas.css').read_text())
    page.add_script_tag(path=str(ROOT/'static/combinadas.js'))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert page.locator('input[type=checkbox]').count()==17
    assert page.locator('button[type=submit]').first.bounding_box()['height']>=44
    details=page.locator('summary').filter(has_text='Copiar borrador')
    details.focus();page.keyboard.press('Enter')
    page.locator('[data-copy-combi]').click()
    assert 'Copia el texto' in page.locator('[data-copy-status]').inner_text()
    # Captures carry a visible label rather than pretending these are live matches.
    page.evaluate("document.body.insertAdjacentHTML('afterbegin','<p>SIMULATED_QA · datos de prueba, no producción</p>')")
    dest=Path(os.environ['NEMESIS_COMBI_QA_OUTPUT']) if os.environ.get('NEMESIS_COMBI_QA_OUTPUT') else tmp_path
    dest.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(dest/f'combinadas-{width}.png'),full_page=True)
    page.close()


def test_no_javascript_keeps_preview_and_save_forms(browser,webapp):
    c=webapp.test_client();token=login(c)
    html=c.post('/combinadas',data={**preview_values(),'csrf_token':token}).get_data(as_text=True)
    context=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
    page=context.new_page();page.route('**/*',lambda route:route.abort());page.set_content(html)
    assert page.get_by_role('button',name='Guardar borrador privado').is_visible()
    assert not page.locator('[data-copy-combi]').is_visible()
    assert page.locator('form[action="/combinadas"]').count()>=2
    context.close()


def test_widget_uses_same_rules_and_never_saves(webapp,db):
    c=webapp.test_client();token=login(c)
    result=c.post('/api/shark/ask',json={'question':'Prepara una combi de 3 partidos','csrf_token':token})
    assert result.status_code==200
    assert result.json['shark']['context']['preview']['probability'] is None
    assert len(result.json['shark']['context']['preview']['legs'])==3
    assert result.json['shark']['next_url']=='/combinadas'
    with sqlite3.connect(db) as conn:assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='client_combi_drafts'").fetchone()
    assert c.get('/api/shark/ask?q=partidos').get_data(as_text=True)=='UNCHANGED_OTHER_INTENT'


def test_widget_insufficient_or_free_never_creates_fake_picks(webapp):
    c=webapp.test_client();login(c,'f')
    result=c.get('/api/shark/ask?q=combinada%2015').json
    assert result['shark']['context']['preview'] is None
    assert '/combisí' not in str(result)


def test_widget_post_requires_csrf(webapp):
    c=webapp.test_client();login(c)
    assert c.post('/api/shark/ask',json={'q':'combi 3'}).status_code==403


def test_widget_privacy_limits_and_dispatch_guard(webapp):
    c=webapp.test_client()
    response=c.get('/api/shark/ask?q=combinada')
    assert response.headers['Cache-Control']=='private, no-store'
    assert 'Cookie' in response.headers['Vary']
    assert c.post('/api/shark/ask',json={'question':'x'*66000}).status_code==413
    other=Flask('widget-drift')
    other.add_url_rule('/not-shark','api_shark_ask',lambda:'')
    with pytest.raises(RuntimeError,match='Unexpected legacy SHARK'):
        other.register_blueprint(create_client_combi_blueprint('unused'))


def test_widget_respects_date_and_leg_count_instead_of_guessing_year(webapp, monkeypatch):
    seen=[]
    def capture(path,user,options):
        seen.append(options)
        return {'copy_text':'SIMULATED_QA','warnings':[]}
    monkeypatch.setattr(store,'make_preview',capture)
    c=webapp.test_client();login(c)
    assert c.get('/api/shark/ask',query_string={'q':'Dame una combinada de 4 partidos equilibrada para 2026-09-23'}).status_code==200
    assert seen[0]['date']=='2026-09-23' and seen[0]['count']=='4' and seen[0]['risk']=='equilibrado'
