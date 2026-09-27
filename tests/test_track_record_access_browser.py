"""SIMULATED_QA: actual Flask pages/styles in Chromium; no external transport."""
import os
import sqlite3
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright

from engines.pick_grading_engine import ensure_pick_grading_schema
from test_get_business_readonly_v941 import isolated, snapshot


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        options={"headless":True}
        if os.getenv("NEMESIS_QA_CHROMIUM"):
            options["executable_path"]=os.environ["NEMESIS_QA_CHROMIUM"]
        engine=pw.chromium.launch(**options)
        yield engine
        engine.close()


@pytest.mark.parametrize("plan", ["FREE","PRO","ELITE"])
@pytest.mark.parametrize("width", [390,1440])
def test_history_filters_preserve_plan_boundary_and_mobile_layout(app_module,monkeypatch,tmp_path,browser,plan,width):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    ensure_pick_grading_schema(db)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET role=?,membership=?,membership_expires_at='2030-01-01' WHERE id='qa-read-client'",(plan,plan))
        for index,(tier,result) in enumerate((("FREE","won"),("FREE","lost"),("PRO","won"),("ELITE","void"))):
            identifier="qa-history-"+str(index)
            conn.execute("INSERT INTO picks(id,home_team,away_team,selection,status,membership_required) VALUES(?,?,?,?,?,?)",
                (identifier,"QA Home","QA Away","QA_SELECTION_"+tier+"_"+result,result,tier))
            conn.execute("""INSERT INTO pick_grading_results
                (id,pick_id,result_status,odds,stake,profit,graded_at) VALUES(?,?,?,?,?,?,?)""",
                (identifier,identifier,result,2,1,1 if result=="won" else -1 if result=="lost" else 0,"2026-09-01"))
    client=a.app.test_client()
    with client.session_transaction() as state:
        state.update(user_id="qa-read-client",user_role=plan,membership=plan)
    before=snapshot(db)
    page=browser.new_page(viewport={"width":width,"height":844},service_workers="block")
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    def serve(route):
        url=urlsplit(route.request.url)
        if url.netloc!="localhost":
            route.abort()
            return
        response=client.get(url.path+("?"+url.query if url.query else ""))
        route.fulfill(status=response.status_code,body=response.data,
                      headers={k:v for k,v in response.headers.items() if k.lower() not in {"content-length","set-cookie"}})
    page.route("**/*",serve)
    try:
        page.goto("http://localhost/track-record",wait_until="load")
        panel=page.locator(".ns16-track-recent")
        assert "QA_SELECTION_FREE_won" in panel.inner_text()
        assert ("QA_SELECTION_PRO_won" in panel.inner_text())==(plan in {"PRO","ELITE"})
        assert ("QA_SELECTION_ELITE_void" in panel.inner_text())==(plan=="ELITE")
        page.get_by_role("link",name="Perdidos",exact=True).click()
        page.wait_for_url("**/track-record?result=lost")
        assert "QA_SELECTION_FREE_lost" in panel.inner_text()
        assert "QA_SELECTION_FREE_won" not in panel.inner_text()
        assert "QA_SELECTION_PRO_won" not in page.content()
        page.get_by_role("link",name="Void",exact=True).click()
        page.wait_for_url("**/track-record?result=void")
        if plan=="ELITE":
            assert "QA_SELECTION_ELITE_void" in panel.inner_text()
        else:
            assert "Sin resultados para este filtro" in panel.inner_text()
            assert page.get_by_role("link",name="Ver todos los resultados",exact=True).is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
        assert not errors
        assert snapshot(db)==before
        page.screenshot(path=str(tmp_path/f"history-{plan}-{width}.png"))
    finally:
        page.close()
