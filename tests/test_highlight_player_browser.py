"""Browser components use synthetic HTML. External player requests are intercepted, not fetched."""
from pathlib import Path
import os
import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as pw:
        path=os.environ.get('NEMESIS_QA_CHROMIUM')
        options={'headless':True,'args':['--no-sandbox']}
        if path:options['executable_path']=path
        elif Path('/usr/bin/chromium').exists():options['executable_path']='/usr/bin/chromium'
        b=pw.chromium.launch(**options);yield b;b.close()


def html(embed=True):
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=select_autoescape())
    player=env.get_template('components/highlight_player.html').module.highlight_player({
        'decision':'APPROVED','title':'SIMULATED_QA — Norte / Sur', 'can_embed':embed,'can_link':True,
        'original_url':'https://www.youtube.com/watch?v=officialQA1','embed_url':'https://www.youtube-nocookie.com/embed/officialQA1',
        'attribution':'Canal de prueba — autorización sintética, no real'})
    return '<!doctype html><html lang="es"><meta name="viewport" content="width=device-width"><style>body{margin:12px;background:#08101c;color:white}*{box-sizing:border-box}'+(ROOT/'static/highlights-experience.css').read_text()+'</style><h1>SIMULATED_QA</h1>'+str(player)+'</html>'

@pytest.mark.parametrize('width',[320,390,430,1366])
def test_player_is_opt_in_closeable_and_not_autoplay(browser,width,tmp_path):
    page=browser.new_page(viewport={'width':width,'height':844})
    requests=[]
    page.route('https://www.youtube-nocookie.com/**',lambda route:(requests.append(route.request.url),route.fulfill(status=200,content_type='text/html',body='<p>SIMULATED_QA iframe, not a video.</p>')))
    page.set_content(html());page.add_script_tag(path=str(ROOT/'static/highlights-player.js'))
    assert page.locator('iframe').count()==0 and requests==[]
    button=page.locator('[data-highlight-load]');assert button.is_visible()
    button.focus();page.keyboard.press('Enter')
    iframe=page.locator('iframe');iframe.wait_for()
    assert iframe.get_attribute('src')=='https://www.youtube-nocookie.com/embed/officialQA1'
    assert 'autoplay' not in iframe.get_attribute('allow')
    assert iframe.bounding_box()['height']>=200
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    assert 'solicitado' in page.locator('[data-highlight-status]').inner_text()
    assert page.locator('a').get_attribute('rel')=='noopener noreferrer'
    page.screenshot(path=str(tmp_path/f'highlight-player-{width}.png'),full_page=True)
    button.click();assert page.locator('iframe').count()==0
    assert button.get_attribute('aria-expanded')=='false'
    page.close()


def test_no_javascript_keeps_authorized_source_link(browser):
    context=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
    page=context.new_page();page.set_content(html())
    assert page.locator('iframe').count()==0
    assert not page.locator('[data-highlight-load]').is_visible()
    assert page.locator('a').is_visible()
    context.close()


def test_link_only_never_creates_player(browser):
    page=browser.new_page();page.set_content(html(False));page.add_script_tag(path=str(ROOT/'static/highlights-player.js'))
    assert page.locator('[data-highlight-load]').count()==0
    assert page.locator('iframe').count()==0
    page.close()

@pytest.mark.parametrize('url',['https://youtube.com.evil.org/embed/a','javascript:alert(1)','https://www.youtube-nocookie.com/embed/a?autoplay=1'])
def test_dom_mutation_cannot_inject_unapproved_player(browser,url):
    page=browser.new_page();page.set_content(html());page.locator('[data-highlight-load]').evaluate('(el,url)=>el.dataset.embedUrl=url',url)
    page.add_script_tag(path=str(ROOT/'static/highlights-player.js'))
    assert not page.locator('[data-highlight-load]').is_visible()
    assert page.locator('iframe').count()==0
    page.close()

@pytest.mark.parametrize('width',[320,390,430,1366])
def test_admin_review_is_readable_and_keyboard_accessible(browser,width,tmp_path):
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=select_autoescape())
    source=(ROOT/'templates/admin_highlights_review.html').read_text().replace('{% extends "base.html" %}','')
    env.globals.update(url_for=lambda *a,**kw:'/static/'+kw['filename'],csrf_token=lambda:'test-csrf')
    env.filters['madrid_datetime_label']=str
    rendered=env.from_string(source).render(review_error='',review={'state':'RECORDED','counts':{'stored':1},'sample_limit':40,'runs':[],
      'items':[{'id':'qa','title':'SIMULATED_QA — Club Norte / Club Sur','source':'Datos simulados','event_date':'2026-09-20',
      'can_display':False,'reason':'Derechos pendientes: no publicado.','match_id':'m1','video_url':'https://www.youtube.com/watch?v=officialQA1','review_token':'test-token','attribution':''}]})
    page=browser.new_page(viewport={'width':width,'height':844});page.route('**/static/**',lambda route:route.abort())
    page.set_content('<!doctype html><html lang="es"><style>body{margin:12px;background:#08101c;color:#edf4fc;font-family:Arial}*{box-sizing:border-box}'+(ROOT/'static/highlights-experience.css').read_text()+'</style>'+rendered+'</html>')
    summary=page.locator('summary');summary.focus();page.keyboard.press('Enter')
    assert page.locator('select[name=decision]').is_visible()
    assert page.locator('input[name=confirmed]').count()==1
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert page.locator('button').last.bounding_box()['height']>=44
    page.screenshot(path=str(tmp_path/f'highlights-review-{width}.png'),full_page=True)
    page.close()
