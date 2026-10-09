"""Local rendered templates; no production accounts or provider calls."""
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlsplit
import pytest
from test_app_navigation_browser import browser
from test_admin_master_browser import mount, snapshot
from engines.admin_daily_priorities import build_daily_priorities

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("width",[320,390,768,1440])
def test_admin_priority_refresh_keeps_evidence_and_never_executes(browser,app_module,width):
    data=snapshot()
    data["recommendations"]=build_daily_priorities([{"key":"db","state":"SIN DATOS","detail":"SIMULATED_QA: lectura pendiente"}])
    context,page,calls,errors,blocked=mount(browser,app_module,width=width,data=data)
    try:
        panel=page.locator('[aria-labelledby="master-recommendations-title"]')
        assert "Por comprobar" in panel.inner_text()
        assert "Siguiente paso:" in panel.inner_text()
        assert "Fecha de evidencia no disponible" in panel.inner_text()
        assert not calls
        page.get_by_role("button",name="Actualizar lectura",exact=True).click()
        page.get_by_text("Lectura local actualizada. No se han consultado proveedores externos.",exact=True).wait_for()
        assert "Siguiente paso:" in panel.inner_text()
        assert all(c["method"]=="GET" for c in calls)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
        assert not errors and not blocked
        if width in (390,1440):
            output=ROOT/'data/local_dev/personal-home-qa'
            output.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(output/f'admin-{width}.png'))
    finally:
        context.close()


@pytest.mark.parametrize("width",[320,390,768,1440])
def test_personal_home_get_navigation_and_layout(browser,app_module,width):
    from flask import render_template
    from datetime import datetime,timedelta
    from zoneinfo import ZoneInfo
    kickoff=datetime.now(ZoneInfo('Europe/Madrid'))+timedelta(days=1)
    data={"personal_home":{"state":"READY","saved_count":1,"matches":[{
        "id":f"personal-qa-{i}", "home_team":"Equipo favorito QA", "away_team":f"Rival QA {i+1}",
        "status":"NS", "status_info":{"key":"UPCOMING","is_upcoming":True},
        "kickoff_iso":kickoff.isoformat(), "match_date":kickoff.date().isoformat(),
        "client_schedule_label":kickoff.strftime('%d/%m/%Y %H:%M'),
        "competition_name":"Competición de prueba", "personal_reason":"Sigues a un equipo",
        "source":"SIMULATED_QA"} for i in range(3)]}}
    data['home_matchday']=app_module.home_matchday_context({'all_valid_matches':data['personal_home']['matches']})
    with app_module.app.test_request_context('/app'):
        markup=render_template('client_app_center.html',data=data,current_user={'id':'qa','membership':'FREE'},greeting={'label':'Hola','name':'QA'})
    markup=re.sub(r'<script\b[^>]*>.*?</script>','',markup,flags=re.S|re.I)
    context=browser.new_context(viewport={'width':width,'height':850})
    page=context.new_page()
    calls=[]
    def serve(route):
        url=urlsplit(route.request.url); calls.append(route.request.method)
        if url.netloc!='personal.invalid': route.abort(); return
        if url.path=='/app': route.fulfill(status=200,content_type='text/html; charset=utf-8',body=markup); return
        asset=(ROOT/url.path.lstrip('/')).resolve()
        if url.path.startswith('/static/') and asset.is_relative_to(ROOT/'static') and asset.is_file():
            route.fulfill(status=200,content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream',body=asset.read_bytes()); return
        route.fulfill(status=200,content_type='text/html',body='<p>Destino local aislado</p>')
    page.route('**/*',serve)
    try:
        page.goto('https://personal.invalid/app')
        assert page.locator('[data-personal-home]').count()==0
        panel=page.locator('[data-sports-priority="upcoming"]')
        assert panel.locator('[data-v934-match-id]').count()==3
        assert not panel.locator('details').count()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        if width in (390,1440):
            output=ROOT/'data/local_dev/personal-home-qa'
            output.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(output/f'home-{width}.png'))
        panel.locator('a[href="/match/personal-qa-0"]').last.click()
        page.wait_for_url('**/match/personal-qa-0')
        assert all(method=='GET' for method in calls)
    finally: context.close()
