"""Regression of recorded UI issues; synthetic clients, offline component browser."""
from pathlib import Path
import os
import sqlite3
import secrets
import pytest
from flask import render_template
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from test_combi_advisor_contract import db, NOW
from test_combi_routes_and_browser import webapp, login, browser
from test_combi_match_catalogue import quotes
from engines.combi_match_catalogue import choice_id

ROOT=Path(__file__).resolve().parents[1]


def ids_for_two(db):
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        rows=conn.execute('SELECT * FROM odds_snapshots ORDER BY id LIMIT 2').fetchall()
        return [choice_id(dict(row),'1') for row in rows]


def test_builder_displays_fixtures_and_three_options_without_picks(webapp, db):
    quotes(db)
    with sqlite3.connect(db) as conn:conn.execute('DELETE FROM picks')
    c=webapp.test_client();login(c)
    page=c.get('/combinadas')
    assert page.status_code==200
    assert b'Elige pr' in page.data and b'data-market-choice' in page.data
    assert page.data.count(b'data-market-match=')==17
    assert page.data.count(b'data-market-choice')==6


def test_filter_post_retains_chosen_other_match_and_amount(webapp, db):
    quotes(db);selection=ids_for_two(db)[0]
    c=webapp.test_client();token=login(c)
    result=c.post('/combinadas',data={'csrf_token':token,'action':'browse','q':'Local 2','pick_ids':selection,'stake':'19,37'})
    assert result.status_code==200
    html=result.get_data(as_text=True)
    assert 'value="19,37"' in html and f'value="{selection}" checked' in html
    assert 'Tu selección en otros resultados' in html
    assert 'data-market-match="m1"' not in html and 'data-market-match="m2"' in html
    with sqlite3.connect(db) as conn:assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='client_combi_drafts'").fetchone()


def test_browse_requires_same_session_csrf(webapp):
    a,b=webapp.test_client(),webapp.test_client()
    t=login(a);login(b,'b')
    assert b.post('/combinadas',data={'action':'browse','csrf_token':t}).status_code==403


def test_displayed_market_price_is_never_trusted_from_client(webapp,db):
    quotes(db);ids=ids_for_two(db)
    c=webapp.test_client();t=login(c)
    response=c.post('/api/client/combinadas/preview',json={'csrf_token':t,'pick_ids':ids,'stake':'0.10','odds':'999','total_odds':'888'})
    assert response.status_code==200 and response.json['combi']['total_odds']=='3.2400'


def test_shared_faq_is_complete_and_actionable():
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=select_autoescape())
    env.globals['ui']=lambda x:x
    macro=env.get_template('components/platform_faq.html').module.platform_faq
    all_html=str(macro());compact=str(macro(True))
    assert all_html.count('class="ns-faq-item"')==12
    assert compact.count('class="ns-faq-item"')==6
    assert 'href="/faq"' in compact
    assert 'un dato pendiente' in all_html and 'borrador privado' in all_html
    assert 'data.support_tips' not in (ROOT/'templates/support.html').read_text()


def test_support_and_faq_use_same_questions(app_module):
    for path,template,extra in [('/support','support.html',{}),('/faq','company_platform.html',{'page_key':'faq','page':{'title':'Ayuda','summary':'QA'},'company_nav':[],'company_pricing':{},'company_updated_at':'','company_contract':'QA'})]:
        with app_module.app.test_request_context(path):
            html=render_template(template,data={'support_available':False},**extra)
        assert 'data-platform-faq="client-help-v1"' in html
        assert '¿Por qué no veo una cuota' in html


def test_shark_question_and_answer_exist_without_picks(app_module):
    with app_module.app.test_request_context('/shark?q=Donde%20esta%20mi%20cuenta'):
        html=render_template('shark.html',data={'shark_assistant':{'answer':{'answer':'Respuesta de prueba sobre tu cuenta.'}},'v925_picks':{'picks':[]}})
    assert 'name="q"' in html and 'Respuesta de prueba sobre tu cuenta.' in html
    assert 'Combinadas y decisiones con evidencia' not in html
    assert '<form method="get" action="/shark">' in html


def test_shark_escapes_question_and_answer(app_module):
    with app_module.app.test_request_context('/shark?q=%3Cscript%3Ealert(1)%3C/script%3E'):
        html=render_template('shark.html',data={'shark_assistant':{'answer':{'answer':'<img src=x onerror=alert(1)>'}}})
    assert '<img src=x onerror=alert(1)>' not in html
    assert '&lt;script&gt;' in html and '&lt;img' in html


@pytest.mark.parametrize('width',[320,390,430,1366])
def test_catalogue_visual_and_single_event_choice(browser,webapp,db,width,tmp_path):
    quotes(db)
    with sqlite3.connect(db) as conn:
        conn.execute('DELETE FROM picks')
        conn.execute("UPDATE matches SET competition_name='UEFA Champions League' WHERE id='m1'")
    client=webapp.test_client();login(client)
    html=client.get('/combinadas').get_data(as_text=True)
    page=browser.new_page(viewport={'width':width,'height':844})
    page.route('**/*',lambda r:r.abort())
    page.set_content(html)
    page.add_style_tag(content='body{margin:12px;background:#07121e;color:#edf4fc;font:16px Arial}*{box-sizing:border-box}'+(ROOT/'static/combinadas.css').read_text())
    page.add_script_tag(path=str(ROOT/'static/combinadas.js'))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert page.get_by_role('searchbox').is_visible()
    options=page.locator('[data-market-choice]')
    options.nth(0).check();options.nth(1).check()
    assert not options.nth(0).is_checked() and options.nth(1).is_checked()
    assert '1 selección' in page.locator('[data-selection-count]').inner_text()
    summary=page.locator('.ns-market-info summary').first
    summary.focus();page.keyboard.press('Enter')
    assert page.locator('.ns-market-info[open]').count()==1
    for button in page.locator('button').all():
        if button.is_visible():assert button.bounding_box()['height']>=44
    page.evaluate("document.body.insertAdjacentHTML('afterbegin','<div style=\"position:fixed;top:0;left:0;right:0;z-index:10000;background:#07121e;color:white;padding:5px;font-size:11px;text-align:center\">SIMULATED_QA · datos sintéticos, no producción</div>')")
    dest=Path(os.getenv('NEMESIS_PLATFORM_QA_OUTPUT',str(tmp_path)));dest.mkdir(parents=True,exist_ok=True)
    # First viewport, with optional full page kept only in isolated QA artifacts.
    page.screenshot(path=str(dest/f'combinadas-fixtures-{width}.png'))
    page.close()


@pytest.mark.parametrize('width',[320,390,1366])
def test_faq_keyboard_readable_without_javascript(browser,width,tmp_path):
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=select_autoescape());env.globals['ui']=lambda x:x
    html=str(env.get_template('components/platform_faq.html').module.platform_faq(True))
    context=browser.new_context(java_script_enabled=False,viewport={'width':width,'height':844})
    page=context.new_page();page.set_content('<meta name="viewport" content="width=device-width"><style>body{margin:12px;background:#07121e;color:#eef4fc;font:16px Arial}*{box-sizing:border-box}'+(ROOT/'static/platform-help.css').read_text()+'</style><p>SIMULATED_QA · ayuda al cliente</p>'+html)
    first=page.locator('summary').first;first.focus();page.keyboard.press('Enter')
    assert page.locator('.ns-faq-item[open]').count()==1
    assert 'Un partido y su cuota' in page.locator('.ns-faq-item[open]').inner_text()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    dest=Path(os.getenv('NEMESIS_PLATFORM_QA_OUTPUT',str(tmp_path)));dest.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(dest/f'faq-{width}.png'))
    context.close()
