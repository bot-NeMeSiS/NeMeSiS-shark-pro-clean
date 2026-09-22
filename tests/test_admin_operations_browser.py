"""Offline component DOM/interaction tests, not production or Safari certification."""
from pathlib import Path
import os
import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright
from test_admin_operations_workbench import sample
from engines.admin_operations_workbench import build_admin_workbench

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        path=os.getenv('NEMESIS_QA_CHROMIUM') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else '')
        args={'headless':True,'args':['--no-sandbox']}
        if path:args['executable_path']=path
        b=p.chromium.launch(**args);yield b;b.close()


def html(data=None):
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=select_autoescape())
    env.filters['madrid_datetime_label']=lambda v:__import__('datetime').datetime.fromisoformat(v).strftime('%d/%m/%Y %H:%M Madrid')
    component=env.get_template('components/admin_operations_workbench.html').render(workbench=build_admin_workbench(data or sample()))
    return '''<!doctype html><html lang="es"><meta name="viewport" content="width=device-width"><body><p>SIMULATED_QA · administración con datos sintéticos</p><main class="operations-center-v1" data-operations-next-issue="pending">'''+component+'''<details id="diagnostics"><summary>Diagnóstico</summary><section id="v938-safe-actions"><button data-v938-action="scan" data-action="admin-operation">Diagnóstico local</button><button data-v938-action="prompt" data-action="admin-operation">Generar prompt</button><output data-v938-output></output><a data-admin-refresh hidden href="/admin/operations-center#operations-incidents">Actualizar bandeja</a></section></details></main></body></html>'''


def load(browser,width=390,js=True,data=None):
    context=browser.new_context(java_script_enabled=js,viewport={'width':width,'height':900})
    page=context.new_page();page.route('**/*',lambda r:r.abort())
    css='body{background:#091221;color:#eef6ff;margin:12px;font:16px Arial}*{box-sizing:border-box}'+(ROOT/'static/admin-operations.css').read_text()
    page.set_content(html(data).replace('<body>','<style>'+css+'</style><body>'))
    if js:page.add_script_tag(path=str(ROOT/'static/admin-operations.js'))
    return context,page


@pytest.mark.parametrize('width',[320,390,430,1366])
def test_task_filter_tools_no_overflow_and_copy_fallback(browser,width,tmp_path):
    c,p=load(browser,width)
    try:
        assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
        p.locator('[data-task-category]').select_option('verify')
        assert p.locator('[data-admin-task]:visible').count()==1
        p.locator('[data-action="admin-reset-filters"]').click()
        assert p.locator('[data-admin-task]:visible').count()==3
        p.locator('[data-task-search]').fill('LECTURA')
        assert p.locator('[data-admin-task]:visible').count()==1
        p.locator('[data-admin-task]:visible summary').click()
        p.locator('[data-admin-task]:visible [data-action="admin-copy-brief"]').click()
        assert 'Copia el texto' in p.locator('[data-admin-task]:visible [data-copy-result]').inner_text()
        p.locator('[data-tool-search]').fill('usuarios')
        assert p.locator('[data-admin-tool]:visible').count()==1
        p.locator('[data-action="admin-reset-filters"]').click()
        directory=Path(os.environ.get('NEMESIS_ADMIN_QA_OUTPUT',str(tmp_path)));directory.mkdir(parents=True,exist_ok=True)
        p.locator('[data-tool-search]').fill('')
        p.locator('[data-admin-task] details').evaluate_all('(nodes)=>nodes.forEach(n=>n.open=false)')
        p.evaluate('window.scrollTo(0,0)')
        p.screenshot(path=str(directory/f'admin-workbench-{width}.png'))
    finally:c.close()


def test_no_js_keeps_tasks_briefs_and_links(browser):
    c,p=load(browser,js=False)
    try:
        assert p.locator('[data-admin-task]').count()==3
        assert p.locator('[data-admin-tool]').count()==12
        assert not p.locator('[data-task-search]').is_visible()
        summary=p.locator('[data-admin-task] summary').first;summary.focus();p.keyboard.press('Enter')
        assert p.locator('textarea').first.is_visible()
    finally:c.close()


def setup_response(page, payload, status=200, content_type='application/json'):
    page.evaluate('''({payload,status,contentType})=>{window.calls=[];window.nemesisJsonHeaders=()=>({'Content-Type':'application/json','X-CSRF-Token':'synthetic-csrf'});window.fetch=async (url,opts)=>{window.calls.push({url,opts});return {ok:status===200,status,redirected:false,headers:{get:()=>contentType},json:async()=>payload};}}''',{'payload':payload,'status':status,'contentType':content_type})
    page.locator('#diagnostics').evaluate('(d)=>d.open=true')


@pytest.mark.parametrize('payload',[{'ok':False,'snapshot':{'incidents':[]}}, {'ok':True}, {'ok':True,'snapshot':{'incidents':None}}])
def test_ok_false_and_bad_payload_are_not_reported_as_success(browser,payload):
    c,p=load(browser)
    try:
        setup_response(p,payload);p.locator('[data-v938-action="scan"]').click()
        p.wait_for_function("document.querySelector('[data-v938-output]').textContent.includes('No se pudo confirmar')")
        assert p.locator('[data-v938-action="prompt"]').is_disabled()
        assert p.evaluate('calls.length')==1
    finally:c.close()


def test_successful_scan_invalidates_old_prompt_and_needs_fresh_reading(browser):
    c,p=load(browser)
    try:
        setup_response(p,{'ok':True,'snapshot':{'incidents':[{'issue_id':'new'}]}})
        p.locator('[data-v938-action="scan"]').click()
        p.wait_for_function("document.querySelector('[data-v938-output]').textContent.includes('Diagnóstico guardado')")
        assert 'lectura anterior' in p.locator('[data-v938-output]').inner_text()
        assert p.locator('[data-v938-action="prompt"]').is_disabled() and p.locator('[data-admin-refresh]').is_visible()
    finally:c.close()


def test_wrong_issue_prompt_not_displayed(browser):
    c,p=load(browser)
    try:
        setup_response(p,{'ok':True,'issue':{'issue_id':'different'},'prompt':'SHOULD_NOT_BE_PRESENTED'})
        p.locator('[data-v938-action="prompt"]').click()
        p.wait_for_function("document.querySelector('[data-v938-output]').textContent.includes('No se pudo confirmar')")
        assert 'SHOULD_NOT_BE_PRESENTED' not in p.locator('[data-v938-output]').inner_text()
    finally:c.close()


def test_matching_prompt_is_displayed_and_not_executed(browser):
    c,p=load(browser)
    try:
        setup_response(p,{'ok':True,'issue':{'issue_id':'pending'},'prompt':'Revisar cobertura sintética.'})
        p.locator('[data-v938-action="prompt"]').click()
        p.wait_for_function("document.querySelector('[data-v938-output]').textContent==='Revisar cobertura sintética.'")
        assert p.evaluate('calls.length')==1
        assert 'pending' in p.evaluate('calls[0].opts.body')
    finally:c.close()


def test_in_flight_blocks_other_actions_and_never_retries(browser):
    c,p=load(browser)
    try:
        setup_response(p,{})
        p.evaluate("() => {window.fetch=(url,opts)=>{calls.push({url,opts});return new Promise((_resolve,reject)=>{window.rejectRequest=reject;});};}")
        p.locator('[data-v938-action="scan"]').click()
        assert p.locator('[data-v938-action="prompt"]').is_disabled()
        p.evaluate("document.querySelector('[data-v938-action=prompt]').dispatchEvent(new Event('click'))")
        assert p.evaluate('calls.length')==1
        p.evaluate("rejectRequest(new Error('network unavailable'))")
        p.wait_for_function("document.querySelector('[data-v938-output]').textContent.includes('No se pudo confirmar')")
        assert p.evaluate('calls.length')==1
    finally:c.close()


def test_xss_is_text_not_executable(browser):
    data=sample();data['incidents'][0]['title']='<img src=x onerror="window.xss=1">'
    c,p=load(browser,data=data)
    try:assert p.locator('[data-admin-task] img').count()==0 and not p.evaluate('window.xss||false')
    finally:c.close()


def test_confirmed_and_urgent_filters_can_be_selected(browser):
    c,p=load(browser)
    try:
        p.locator('[data-task-category]').select_option('confirmed')
        p.locator('[data-task-priority]').select_option('urgent')
        assert p.locator('[data-admin-task]:visible').count()==1
        assert p.locator('[data-admin-task]:visible').get_attribute('data-category')=='confirmed'
    finally:c.close()
