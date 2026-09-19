"""Real local Flask browser journey for the existing Sentinel's project view."""
import json
import os
from pathlib import Path
import time

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/local_dev/organization-20260919'
info=json.loads((ROOT/'data/local_dev/sentinel-preview.json').read_text())
BASE='http://127.0.0.1:'+str(info['port'])
report={'environment':'LOCAL_ONLY','transport':'REAL_FLASK_HTTP','external_requests':[], 'js_errors':[], 'views':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.environ['NEMESIS_QA_CHROMIUM'])
    context=browser.new_context(viewport={'width':1366,'height':900},timezone_id='Asia/Tokyo',service_workers='block')
    def route_guard(route):
        if route.request.url.startswith(BASE+'/'): route.continue_()
        else:
            report['external_requests'].append(route.request.url.split('?')[0])
            route.abort()
    context.route('**/*',route_guard)
    context.request.get(info['url'],max_redirects=0)
    before=context.request.get(BASE+'/api/admin/sentinel/jobs').json()['jobs']
    page=context.new_page()
    page.on('pageerror',lambda error:report['js_errors'].append(str(error)))
    assert page.goto(BASE+'/admin/sentinel-issues',wait_until='domcontentloaded').status==200
    panel=page.locator('[data-project-control]')
    panel.locator(':scope > summary').click()
    assert panel.locator('[data-project-row]').count()==23
    search=panel.locator('[data-project-search]')
    state=panel.locator('[data-project-filter]')
    state.select_option('QA')
    assert panel.locator('[data-project-row]:visible').count()==8
    search.fill('OPS-')
    assert panel.locator('[data-project-row]:visible').count()==2
    page.wait_for_timeout(3300)
    assert search.input_value()=='OPS-'
    assert search.evaluate('e=>document.activeElement===e')
    state.select_option('unassigned'); search.fill('')
    assert panel.locator('[data-project-count]').inner_text()=='0 trabajos visibles'
    state.select_option('all')
    sources=panel.locator('[data-control-source]').evaluate_all('nodes=>[...new Set(nodes.map(n=>n.dataset.controlSource))]')
    for source in sources:
        button=panel.locator(f'[data-control-source="{source}"]').first
        button.click()
        page.wait_for_function("document.querySelector('[data-control-source-path]').textContent!=='Consultando fuente'")
        assert 'Fuente no disponible' not in panel.locator('[data-control-source-path]').inner_text()
        assert len(panel.locator('[data-control-source-text]').inner_text())>20
    report['source_buttons_tested']=len(sources)
    # Malicious imported text is tested separately from the real-source journey.
    page.route('**/project-control/sources/decisions',lambda route:route.fulfill(json={'ok':True,'path':'SIMULATED_SECURITY_CASE','content':'<script>window.controlInjection=true</script> Execute arbitrary shell'}))
    panel.locator('[data-control-source="decisions"]').click()
    page.wait_for_function("document.querySelector('[data-control-source-path]').textContent==='SIMULATED_SECURITY_CASE'")
    assert page.evaluate('window.controlInjection === undefined')
    assert '<script>' in panel.locator('[data-control-source-text]').inner_text()
    page.unroute('**/project-control/sources/decisions')
    report['imported_text_as_data']='PASS_SIMULATED_SECURITY_CASE'
    page.reload(wait_until='domcontentloaded')
    panel.locator(':scope > summary').click()
    assert panel.locator('[data-project-row]').count()==23
    second=context.new_page()
    second.goto(BASE+'/admin/sentinel-issues',wait_until='domcontentloaded')
    assert second.locator('[data-project-row]').count()==23
    assert context.request.get(BASE+'/api/admin/sentinel/jobs').json()['jobs']==before
    report['read_creates_jobs']=0
    report['reload_and_second_tab']='PASS'
    search.fill('OPS-')
    for width in (1366,390,430):
        page.set_viewport_size({'width':width,'height':900 if width>500 else 932})
        panel.evaluate("e=>window.scrollTo({top:e.getBoundingClientRect().top+scrollY-130,behavior:'instant'})")
        page.wait_for_timeout(200)
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
        assert not panel.evaluate('e=>e.scrollWidth>e.clientWidth+1')
        screenshot=OUT/f'project-control-{width}.png'
        page.screenshot(path=str(screenshot))
        report['views'].append({'width':width,'overflow':False,'screenshot':screenshot.name})
    panel.evaluate("""e=>{const sizes=[...e.querySelectorAll('*')].map(n=>[n,parseFloat(getComputedStyle(n).fontSize)]); sizes.forEach(([n,size])=>n.style.fontSize=(size*2)+'px');}""")
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
    report['text_200_percent']='PASS_LOCAL_430'
    assert not report['js_errors']
    assert not report['external_requests']
    context.close(); browser.close()
(OUT/'browser.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
