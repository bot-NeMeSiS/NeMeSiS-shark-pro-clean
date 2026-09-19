"""Real browser smoke/captures of the running LOCAL SAFE candidate, no providers."""
import json
import os
from pathlib import Path
import sys
import uuid

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.local_review.preview import read_metadata, is_running

meta=read_metadata()
assert is_running(meta), 'Start the managed preview first'
base=f"http://127.0.0.1:{meta['port']}"
output=ROOT/'data/local_dev'/('preview-review-'+uuid.uuid4().hex)
output.mkdir()
report={'environment':'LOCAL_SAFE_SIMULATED_QA','views':[],'errors':[],'external':[],'failures':[]}
paths=['/app','/calendar','/partidos','/live','/directo','/picks','/recommendations',
       '/match/local-match-2','/historico','/shark','/membership','/profile','/telegram','/support']
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=os.environ['NEMESIS_QA_CHROMIUM'])
    context=browser.new_context(timezone_id='Asia/Tokyo')
    def network(route):
        if route.request.url.startswith(base+'/'): route.continue_()
        else: report['external'].append(route.request.url.split('?')[0]); route.abort()
    context.route('**/*',network)
    context.request.get(meta['url'].replace('/login/admin','/login/client'),max_redirects=0)
    page=context.new_page()
    page.on('pageerror',lambda error:report['errors'].append(str(error)))
    page.goto(base+'/profile',wait_until='domcontentloaded')
    selector=page.locator('[data-language-selector]')
    selector.locator('select').select_option('es')
    with page.expect_navigation(): selector.locator('button[type=submit]').click()
    assert page.locator('html').get_attribute('lang')=='es'
    report['language_selection']='ES saved through real form/CSRF'
    for path in paths+['/admin/sentinel-issues']:
        if path.startswith('/admin'):
            context.request.get(meta['url'],max_redirects=0)
        for width in (1366,390,430):
            page.set_viewport_size({'width':width,'height':900 if width==1366 else 932})
            response=page.goto(base+path,wait_until='domcontentloaded')
            page.wait_for_timeout(150)
            main=page.locator('main')
            banner=page.locator('[data-local-safe-banner]')
            overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth+2')
            valid=response.status==200 and main.count()==1 and main.is_visible() and banner.count()==1
            if path=='/recommendations': valid=valid and page.locator('[data-v933-template=betting-review]').count()==1
            filename=path.strip('/').replace('/','-')+f'-{width}.png'
            page.screenshot(path=str(output/filename))
            report['views'].append({'path':path,'width':width,'status':response.status,'shell':bool(valid),
                                    'main_count':main.count(),'banner_count':banner.count(),
                                    'overflow':overflow,'image':filename,'title':page.title()})
            if not valid or overflow: report['failures'].append(filename)
    context.request.get(meta['url'].replace('/login/admin','/login/client'),max_redirects=0)
    page.goto(base+'/app',wait_until='domcontentloaded')
    link=page.locator('a[href^="/match/"]:visible').first
    with page.expect_navigation(): link.click()
    assert '/match/' in page.url and page.locator('main').is_visible()
    page.go_back(wait_until='domcontentloaded')
    assert page.url==base+'/app'
    with page.expect_navigation(): page.locator('a[href="/calendar"]:visible').first.click()
    assert '/calendar' in page.url
    report['navigation']='Home -> Match -> Back -> Calendar: PASS'
    context.close()
    browser.close()
(output/'result.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'output':str(output),'views':len(report['views']),
                  'failures':report['failures'],'errors':report['errors'],'external':report['external']}))
raise SystemExit(bool(report['failures'] or report['errors'] or report['external']))
