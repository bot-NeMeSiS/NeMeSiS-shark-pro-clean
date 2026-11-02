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
    # This check deliberately removes scripts: exercise the real no-JS fallback,
    # rather than a JS-enabled document whose controller was removed by the test.
    context=browser.new_context(viewport={'width':width,'height':850},java_script_enabled=False)
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
        cards=panel.locator('[data-v934-match-id]')
        expected_ids={f'personal-qa-{i}' for i in range(3)}
        ids=cards.evaluate_all('(nodes)=>nodes.map(node=>node.dataset.v934MatchId)')
        assert len(ids)==len(set(ids))==3 and set(ids)==expected_ids
        featured=panel.locator('[data-home-featured]')
        assert featured.count()==1
        assert featured.locator('[data-v934-match-id]').count()==2
        visible_feature=featured.locator('[data-home-featured-slide]:not([hidden]) [data-v934-match-id]')
        hidden_feature=featured.locator('[data-home-featured-slide][hidden] [data-v934-match-id]')
        assert visible_feature.count()==hidden_feature.count()==1
        assert visible_feature.is_visible() and not hidden_feature.is_visible()
        hidden_id=hidden_feature.get_attribute('data-v934-match-id')
        fallback=featured.locator('noscript a[href="/match/'+hidden_id+'"]')
        assert fallback.count()==1 and fallback.is_visible()
        assert featured.locator('[data-home-featured-controls]:visible').count()==0
        # The owner now asks for secondary leagues to start folded. This fixture
        # is deliberately unknown, not a major league or an explicit favorite.
        # Featured slots are outside that disclosure; the remaining league is
        # still folded, and every original fixture retains a native route.
        assert panel.locator('[data-home-importance="primary"]').count()==0
        agenda=panel.locator('[data-home-league-agenda="upcoming"]')
        assert agenda.count()==1 and agenda.locator('[data-v934-match-id]').count()==1
        more=agenda.locator('[data-home-more-leagues]')
        assert more.count()==1 and more.get_attribute('open') is None
        assert agenda.locator('[data-v934-match-id]:visible').count()==0
        assert panel.locator('[data-v934-match-id]:visible').count()==1
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        more.locator(':scope > summary').focus();page.keyboard.press('Enter')
        assert more.get_attribute('open') is not None
        league=more.locator('[data-home-importance="secondary"]')
        assert league.count()==1 and league.get_attribute('open') is None
        assert agenda.locator('[data-v934-match-id]:visible').count()==0
        assert panel.locator('[data-v934-match-id]:visible').count()==1
        league.locator(':scope > summary').focus();page.keyboard.press('Space')
        assert league.get_attribute('open') is not None
        assert agenda.locator('[data-v934-match-id]:visible').count()==1
        assert panel.locator('[data-v934-match-id]:visible').count()==2
        for identity in expected_ids:
            link=panel.locator('[data-v934-match-id="'+identity+'"] a[href="/match/'+identity+'"]').last
            if not link.is_visible():
                link=featured.locator('noscript a[href="/match/'+identity+'"]')
            assert link.count()==1 and link.is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        if width in (390,1440):
            output=ROOT/'data/local_dev/personal-home-qa'
            output.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(output/f'home-{width}.png'))
        link=panel.locator('[data-v934-match-id="personal-qa-0"] a[href="/match/personal-qa-0"]').last
        if not link.is_visible():
            link=featured.locator('noscript a[href="/match/personal-qa-0"]')
        link.click()
        page.wait_for_url('https://personal.invalid/match/personal-qa-0')
        assert all(method=='GET' for method in calls)
    finally: context.close()
