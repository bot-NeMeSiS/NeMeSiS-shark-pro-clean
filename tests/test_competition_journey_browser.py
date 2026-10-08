"""Rendered competition UI at mobile breakpoints; no providers or real accounts."""
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from test_app_navigation_browser import browser
from test_competition_journey import competition, match
from engines.competition_center_engine import build_competition_center_context

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('width',[320,390,768,1440])
@pytest.mark.parametrize('surface',['directory','detail'])
def test_competition_get_journey_layout(browser,app_module,monkeypatch,width,surface):
    from flask import render_template
    monkeypatch.setattr(app_module,'competitions',lambda:[{**competition(),'country':'España'}])
    monkeypatch.setattr(app_module,'rows',lambda *a,**kw:[])
    path='/competiciones' if surface=='directory' else '/competition/laliga'
    with app_module.app.test_request_context(path):
        if surface=='directory':
            markup=app_module.global_football()
        else:
            detail={'competition':competition(),'matches':[match('next'),match('old',date='2026-06-14')],
                    'seasons':['2026-2027','2025-2026'],'selected_season':'2026-2027'}
            detail['competition_center']=build_competition_center_context(detail,observed_at_madrid='2026-10-08T16:00:00+02:00')
            markup=render_template('competition_detail.html',detail=detail)
    # Keep styles and semantic GET controls; isolate unrelated realtime jobs.
    markup=re.sub(r'<script\b[^>]*>.*?</script>','',markup,flags=re.S|re.I)
    context=browser.new_context(viewport={'width':width,'height':850})
    page=context.new_page()
    calls=[]
    def serve(route):
        url=urlsplit(route.request.url)
        calls.append((route.request.method,url.path))
        if url.netloc!='competition.invalid':
            route.abort(); return
        if url.path==path:
            route.fulfill(status=200,content_type='text/html; charset=utf-8',body=markup); return
        asset=(ROOT/url.path.lstrip('/')).resolve()
        if url.path.startswith('/static/') and asset.is_relative_to(ROOT/'static') and asset.is_file():
            route.fulfill(status=200,content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream',body=asset.read_bytes()); return
        route.fulfill(status=200,content_type='text/html',body='<p>Isolated test destination</p>')
    page.route('**/*',serve)
    try:
        page.goto('https://competition.invalid'+path)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        if surface=='directory':
            form=page.get_by_role('search')
            assert form.get_attribute('method')=='get'
            page.get_by_role('searchbox').fill('liga')
            page.get_by_role('button',name='Buscar',exact=True).click()
            page.wait_for_url('**/competiciones?q=liga&country=')
            page.get_by_role('link',name='Explorar competición LaLiga EA Sports',exact=True).click()
            page.wait_for_url('**/competition/laliga')
        else:
            assert page.locator('.competition-season-form').get_attribute('method')=='get'
            page.get_by_text('Pendientes de actualización',exact=False).click()
            assert page.locator('.competition-pending').get_attribute('open') is not None
            assert page.locator('.competition-pending a[href="/match/old"]').is_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
            page.get_by_role('combobox',name='Temporada',exact=True).select_option('2025-2026')
            page.get_by_role('button',name='Ver temporada',exact=True).click()
            page.wait_for_url('**/competition/laliga?season=2025-2026')
        assert all(method=='GET' for method,_ in calls)
    finally:
        context.close()
