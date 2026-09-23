"""Real Chromium QA of full Admin templates/styles with explicitly synthetic evidence.

HTTP is intercepted: local static files only, synthetic API replies and inert
preview frame. This verifies browser controls/layout, not providers or production.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime
import json
import mimetypes
import os
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit
import pytest

ROOT = Path(__file__).resolve().parents[1]


def snapshot():
    from engines.admin_control_engine import registry
    return {
        "version": "V941_ADMIN_PC_MASTER_CONTROL_CENTER_SHARK_AI_OPERATING_SYSTEM",
        "generated_at": "2026-09-23T20:00:00+02:00",
        "facts": [{"label": label, "value": value} for label, value in [
            ("Usuarios QA", 12), ("PRO QA", 4), ("ELITE QA", 2),
            ("Partidos guardados QA", 38), ("Partidos hoy QA", 0), ("Directos confirmados", None)]],
        "areas": [
            {"key":"sports","label":"Datos deportivos","state":"ATENCIÓN",
             "detail":"SIMULATED_QA: 38 eventos guardados; falta verificar el filtro de hoy.","href":"/admin/data-center"},
            {"key":"telegram","label":"Telegram","state":"SIN DATOS",
             "detail":"Configuración sintética; no se realizó ningún envío.","href":"/admin/telegram/command-center"},
        ],
        "recommendations": [{"title":"Revisar cobertura QA","evidence":"Evidencia sintética de prueba.","href":"/admin/data-center"}],
        "settings":{"highlights_enabled":True,"banner_enabled":False,"banner_text":""},
        "runtime":{"environment":"SIMULATED_QA","deployment":"Producción no consultada"},
        "ai":{"configured":False}, "audit":[], "actions":registry(),
    }


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        executable = os.getenv("NEMESIS_QA_CHROMIUM") or playwright.chromium.executable_path
        launched = playwright.chromium.launch(headless=True, executable_path=executable)
        yield launched
        launched.close()


def mount(browser, app_module, *, width=1440, height=900, data=None, responses=None):
    from flask import render_template, session
    data = deepcopy(data or snapshot())
    with app_module.app.test_request_context("/admin/dashboard"):
        session.update(user_id="admin-browser-qa", user_role="ADMIN", membership="ADMIN", user_membership="ADMIN")
        markup = render_template("admin_dashboard.html", data={"admin_master":data}, q={}, items=[],
            current_user={"id":"admin-browser-qa","role":"ADMIN","membership":"ADMIN","name":"Admin QA"})
    # Preserve the full canonical HTML/CSS shell; isolate this change's JS contract
    # from unrelated polling workers and PWA registration.
    markup = re.sub(r"<script\b([^>]*)>.*?</script>", lambda match:
        match.group(0) if ("application/json" in match.group(1) or
            "admin-master-control.js" in match.group(1) or "v930-icons.js" in match.group(1)) else "",
        markup, flags=re.S|re.I)
    markup = markup.replace("<body ", "<body data-qa-origin=\"SIMULATED_QA\" ", 1)
    markup = markup.replace("<h1>Centro de mando</h1>", "<h1>Centro de mando</h1><p>SIMULATED_QA · evidencia sintética · sin producción</p>")
    context = browser.new_context(viewport={"width":width,"height":height},locale="es-ES",timezone_id="Europe/Madrid", reduced_motion="reduce")
    page = context.new_page()
    page.set_default_timeout(7000)
    calls, errors, blocked = [], [], []
    replies = responses if responses is not None else {}
    def serve(route):
        request = route.request
        parsed = urlsplit(request.url)
        if parsed.netloc != "nemesis-qa.invalid":
            blocked.append(request.url); route.abort(); return
        if parsed.path == "/admin/dashboard":
            route.fulfill(status=200,content_type="text/html; charset=utf-8",body=markup); return
        if parsed.path.startswith("/static/"):
            path = (ROOT / parsed.path.lstrip("/")).resolve()
            if path.is_relative_to(ROOT / "static") and path.is_file():
                route.fulfill(status=200,content_type=mimetypes.guess_type(str(path))[0] or "application/octet-stream",body=path.read_bytes()); return
            route.fulfill(status=404,body=""); return
        if parsed.path == "/admin/client-preview/frame":
            plan = parse_qs(parsed.query).get("plan",["FREE"])[0]
            route.fulfill(status=200,content_type="text/html; charset=utf-8",body="<html><body style='background:#061526;color:white;font:20px Arial;padding:20px'><h1>Admin Preview QA</h1><p>"+plan+"</p><p>Marco inerte de prueba. No representa una cuenta real.</p></body></html>"); return
        if parsed.path.startswith("/api/admin/master-control"):
            payload = request.post_data_json if request.method == "POST" else None
            calls.append({"path":parsed.path,"method":request.method,"payload":payload})
            endpoint = parsed.path.removeprefix("/api/admin/master-control")
            result = replies.get(endpoint, {"ok":True,"snapshot":data} if not endpoint else {"ok":False})
            if callable(result):
                result = result(payload)
            status, result = result if isinstance(result, tuple) else (200,result)
            route.fulfill(status=status,content_type="application/json",body=json.dumps(result)); return
        route.fulfill(status=404,body="")
    page.route("**/*", serve)
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.goto("http://nemesis-qa.invalid/admin/dashboard",wait_until="networkidle")
    page.wait_for_function("Boolean(document.querySelector('[data-setting-current]')?.textContent)")
    return context, page, calls, errors, blocked


@pytest.mark.parametrize("width,height",[(320,844),(390,844),(768,1024),(1024,768),(1366,768),(1440,900),(1920,1080)])
def test_layout_no_automatic_admin_api_calls_and_captures(browser,app_module,width,height):
    context,page,calls,errors,blocked=mount(browser,app_module,width=width,height=height)
    try:
        assert not calls, "Opening Admin must not call or execute Admin APIs"
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
        assert page.locator("[data-admin-master-control]").is_visible()
        assert page.locator("#master-chat-form").is_visible()
        assert "Sin datos" in page.locator("[data-master-facts]").inner_text()
        assert not errors and not blocked
        output=ROOT/"data/local_dev/admin-master-v941-qa"
        output.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(output/f"admin-{width}x{height}.png"),full_page=True)
    finally:
        context.close()


@pytest.mark.parametrize("width",[390,1440])
def test_chat_proposal_requires_separate_approval(browser,app_module,width):
    proposal={"proposal_id":"qa-proposal","action_id":"settings.update","label":"Desactivar highlights",
              "risk_level":"LOW","before":{"highlights_enabled":True},"after":{"highlights_enabled":False},
              "parameters":{"key":"highlights_enabled","value":False}}
    responses={"/chat":{"ok":True,"kind":"PROPOSAL","message":"Cambio sintético; requiere aprobación.","proposal":proposal},
               "/execute":{"ok":True,"verification":"VERIFIED","audit_id":123}}
    context,page,calls,errors,blocked=mount(browser,app_module,width=width,responses=responses)
    try:
        page.locator("#master-message").fill("Desactiva highlights")
        page.locator("#master-chat-form button[type=submit]").click()
        page.locator("#master-proposal-dialog").wait_for(state="visible")
        assert len(calls)==1 and calls[0]["path"].endswith("/chat")
        assert "true" in page.locator("[data-proposal-before]").inner_text()
        assert "false" in page.locator("[data-proposal-after]").inner_text()
        page.locator("[data-proposal-approve]").click()
        page.wait_for_function("document.querySelector('[data-proposal-result]').textContent.includes('Verificación correcta')")
        executions=[call for call in calls if call["path"].endswith("/execute")]
        assert len(executions)==1 and executions[0]["payload"]=={"proposal_id":"qa-proposal","confirmation":True}
        assert page.locator("[data-proposal-approve]").is_disabled()
        assert not errors and not blocked
    finally: context.close()


@pytest.mark.parametrize("width",[390,1440])
def test_settings_preview_and_keyboard_controls(browser,app_module,width):
    proposal={"id":"qa-settings","action_id":"settings.update","risk_level":"LOW","before":False,"after":True}
    context,page,calls,errors,blocked=mount(browser,app_module,width=width,responses={"/proposals":{"ok":True,"proposal":proposal},"/cancel":{"ok":True,"result":{"state":"CANCELLED"}}})
    try:
        page.keyboard.press("Control+k")
        page.locator("[data-command-search]").fill("usuarios")
        assert page.locator("[data-command-results] a").count()==1
        assert page.locator("[data-command-results] a").get_attribute("href")=="/admin/users"
        page.keyboard.press("Escape")
        page.locator("#master-command-dialog").wait_for(state="hidden")
        page.locator("#master-setting-key").select_option("banner_enabled")
        page.locator("[name=boolean_value]").select_option("true")
        page.locator("#master-settings-form button[type=submit]").click()
        page.locator("#master-proposal-dialog").wait_for(state="visible")
        assert calls[-1]["payload"]=={"action_id":"settings.update","parameters":{"key":"banner_enabled","value":True}}
        assert not any(call["path"].endswith("/execute") for call in calls)
        page.locator("[data-proposal-cancel]").click()
        page.locator("#master-proposal-dialog").wait_for(state="hidden")
        assert any(call["path"].endswith("/cancel") for call in calls)
        assert not any(call["path"].endswith("/execute") for call in calls)
        page.locator("[data-preview-plan]").select_option("ELITE")
        page.locator("[data-preview-viewport]").select_option("1440")
        frame=page.locator("[data-client-preview-frame]")
        assert "plan=ELITE" in frame.get_attribute("src")
        assert "viewport=1440" in frame.get_attribute("src")
        assert frame.get_attribute("sandbox")=="allow-same-origin"
        assert "plan=ELITE" in page.locator("[data-preview-full]").get_attribute("href")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
        assert not errors and not blocked
    finally: context.close()


def test_server_error_never_claims_success_or_retries(browser,app_module):
    proposal={"id":"qa-fail","action_id":"sports.sync","risk_level":"MEDIUM","before":{},"after":{}}
    context,page,calls,errors,blocked=mount(browser,app_module,responses={
        "/proposals":{"ok":True,"proposal":proposal},"/execute":(409,{"ok":False})})
    try:
        page.locator("[data-master-propose='sports.sync']").click()
        page.locator("#master-proposal-dialog").wait_for(state="visible")
        page.locator("[data-proposal-approve]").click()
        page.wait_for_function("document.querySelector('[data-proposal-result]').textContent.includes('propuesta queda bloqueada')")
        assert "Verificación correcta" not in page.locator("[data-proposal-result]").inner_text()
        assert len([call for call in calls if call["path"].endswith("/execute")])==1
        assert page.locator("[data-proposal-approve]").is_disabled()
        assert not errors and not blocked
    finally:context.close()




def test_chat_content_is_text_and_empty_facts_stay_unknown(browser,app_module):
    data=snapshot(); data['facts']=[{'label':'Cuota proveedor','value':None}]
    context,page,calls,errors,blocked=mount(browser,app_module,data=data,responses={
        '/chat':{'ok':True,'kind':'INFORMATION','message':'<img src=x onerror="window.injected=1">','facts':['Evidencia sintética']}})
    try:
        assert 'Sin datos' in page.locator('[data-master-facts]').inner_text()
        page.locator('#master-message').fill('Qué está mal')
        page.locator('#master-chat-form button[type=submit]').click()
        page.wait_for_function("document.querySelector('[data-master-conversation]').textContent.includes('<img')")
        assert page.locator('[data-master-conversation] img').count()==0
        assert not page.evaluate('window.injected || false')
        assert not any(call['path'].endswith('/execute') for call in calls)
        assert not errors and not blocked
    finally:context.close()


def test_failed_nested_result_cannot_become_verified_success(browser,app_module):
    proposal={'id':'qa-nested-fail','action_id':'sports.sync','risk_level':'MEDIUM'}
    context,page,calls,errors,blocked=mount(browser,app_module,responses={
        '/proposals':{'ok':True,'proposal':proposal},
        '/execute':{'ok':True,'result':{'ok':False,'verification':'VERIFIED','audit_id':321}}})
    try:
        page.locator("[data-master-propose='sports.sync']").click()
        page.locator('#master-proposal-dialog').wait_for(state='visible')
        page.locator('[data-proposal-approve]').click()
        page.wait_for_function("document.querySelector('[data-proposal-result]').textContent.includes('Audit ID')")
        assert 'Verificación correcta' not in page.locator('[data-proposal-result]').inner_text()
        assert len([call for call in calls if call['path'].endswith('/execute')])==1
        assert not errors and not blocked
    finally:context.close()


@pytest.mark.parametrize('width,height',[(390,844),(1440,900)])
@pytest.mark.parametrize('plan',['FREE','PRO','ELITE'])
@pytest.mark.parametrize('screen',['shark','telegram','profile','memberships'])
def test_real_client_preview_route_captures(browser,app_module,width,height,plan,screen):
    """Actual protected Flask preview response; local seeded DB and no API mocks."""
    client=app_module.app.test_client()
    with client.session_transaction() as state:
        state.update(user_id='preview-browser-qa',user_role='ADMIN',membership='ADMIN',user_membership='ADMIN')
    path=f'/admin/client-preview/frame?page={screen}&plan={plan}&viewport={width}'
    response=client.get(path)
    assert response.status_code==200
    assert "script-src 'none'" in response.headers['Content-Security-Policy']
    assert 'no-store' in response.headers['Cache-Control']
    with client.session_transaction() as state:
        assert state['user_role']=='ADMIN' and state['membership']=='ADMIN' and state['user_id']=='preview-browser-qa'
    markup=response.get_data(as_text=True)
    markup=markup.replace('<main class="preview-shell">','<main class="preview-shell"><p style="border:1px solid #796b36;padding:8px">SIMULATED_QA · ruta Flask real · base local aislada</p>',1)
    context=browser.new_context(viewport={'width':width,'height':height},locale='es-ES',timezone_id='Europe/Madrid')
    page=context.new_page(); page.set_default_timeout(7000)
    errors=[]; unexpected=[]
    def serve(route):
        url=urlsplit(route.request.url)
        if url.netloc!='nemesis-qa.invalid':
            unexpected.append(route.request.url);route.abort();return
        if url.path=='/admin/client-preview/frame':
            route.fulfill(status=200,headers={'Content-Security-Policy':response.headers['Content-Security-Policy']},content_type='text/html; charset=utf-8',body=markup);return
        file=(ROOT/url.path.lstrip('/')).resolve()
        if url.path.startswith('/static/') and file.is_relative_to(ROOT/'static') and file.is_file():
            route.fulfill(status=200,content_type=mimetypes.guess_type(str(file))[0] or 'application/octet-stream',body=file.read_bytes());return
        unexpected.append(route.request.url);route.fulfill(status=404,body='')
    page.route('**/*',serve);page.on('pageerror',lambda error:errors.append(str(error)))
    try:
        page.goto('http://nemesis-qa.invalid'+path,wait_until='networkidle')
        assert page.locator('body').get_attribute('data-preview-plan')==plan
        assert page.locator('[data-preview-component="'+screen+'"]').is_visible()
        assert page.locator('script,form,button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled])').count()==0
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        assert not errors and not unexpected
        output=ROOT/'data/local_dev/admin-master-v941-qa';output.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(output/f'preview-{screen}-{plan.lower()}-{width}.png'),full_page=True)
    finally:context.close()



@pytest.mark.parametrize('plan',['FREE','PRO','ELITE'])
@pytest.mark.parametrize('screen',['shark','telegram','profile','memberships'])
def test_preview_links_cannot_escape_simulated_plan(app_module,plan,screen):
    from html.parser import HTMLParser
    class Links(HTMLParser):
        def __init__(self):
            super().__init__();self.values=[]
        def handle_starttag(self,tag,attrs):
            if tag=='a' and dict(attrs).get('href'):
                self.values.append(dict(attrs)['href'])
    client=app_module.app.test_client()
    with client.session_transaction() as state:
        state.update(user_id='preview-link-qa',user_role='ADMIN',membership='ADMIN',user_membership='ADMIN')
    response=client.get(f'/admin/client-preview/frame?page={screen}&plan={plan}&viewport=390')
    assert response.status_code==200
    links=Links();links.feed(response.get_data(as_text=True))
    assert links.values
    for href in links.values:
        target=urlsplit(href)
        assert not target.netloc and target.path in {'/admin/client-preview','/admin/client-preview/frame'},href
        assert parse_qs(target.query).get('plan')==[plan],href
