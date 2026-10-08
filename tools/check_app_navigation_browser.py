"""Full local HTTP navigation journeys with synthetic accounts and no providers."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import sys
import threading
from urllib.parse import quote, urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True


def main():
    from tools.local_desktop.run_sentinel_local import prepare
    from werkzeug.serving import make_server
    from playwright.sync_api import sync_playwright
    output = ROOT / 'data/local_dev' / ('navigation-http-' + uuid.uuid4().hex)
    output.mkdir(parents=True)
    os.environ['TEMP'] = os.environ['TMP'] = str(output)
    module, _, blocked = prepare(db_name=output.name + '.sqlite', allow_browser=True)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    server = make_server('127.0.0.1', 0, module.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    checks = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=os.getenv('NEMESIS_QA_CHROMIUM') or pw.chromium.executable_path)
            for width in (390,1440):
                for role, paths in (
                    ('public', ['/explorar','/calendario?lane=today','/directo']),
                    ('client', ['/mi-cuenta','/favoritos']),
                    ('admin', ['/admin/dashboard','/admin/users','/admin/backups']),
                ):
                    context = browser.new_context(viewport={'width':width,'height':900}, service_workers='block', locale='es-ES',timezone_id='Europe/Madrid')
                    errors, posts = [], []
                    page = context.new_page()
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('request', lambda request: posts.append(request.url) if request.method != 'GET' else None)
                    context.route('**/*', lambda route: route.continue_() if urlsplit(route.request.url).netloc==urlsplit(origin).netloc else route.abort())
                    if role != 'public':
                        response = context.request.get(origin+'/local-safe/login/'+role+'?token='+quote(os.environ['NEMESIS_LOCAL_ACCESS_TOKEN']),max_redirects=0)
                        assert response.status == 302
                    for index, path in enumerate(paths):
                        response = page.goto(origin+path,wait_until='domcontentloaded')
                        page.wait_for_function('Boolean(window.NemesisNavigation)')
                        assert response.status == 200, (role,path,response.status)
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'), (role,path,width)
                        # Let pre-existing page instrumentation finish before the
                        # navigation interaction whose no-mutation property we test.
                        posts.clear()
                        page.keyboard.press('Control+k')
                        dialog = page.locator('#app-navigation-dialog')
                        dialog.wait_for(state='visible')
                        search = dialog.locator('[data-explore-query]')
                        assert search.evaluate('(el)=>el===document.activeElement')
                        search.fill('copias' if role=='admin' else 'competicion')
                        result = dialog.locator('[data-explore-item]:visible')
                        assert result.count()==1
                        assert result.get_attribute('href')==('/admin/backups' if role=='admin' else '/competiciones')
                        assert not dialog.locator('a[href^="/admin/"]').count() if role!='admin' else True
                        page.screenshot(path=str(output/f'{role}-{width}-{index}.png'))
                        page.keyboard.press('Escape')
                        dialog.wait_for(state='hidden')
                        assert not posts, (role,path,'navigation issued POST',posts)
                        assert not errors, (role,path,errors)
                        if role=='admin' and path=='/admin/dashboard':
                            page.locator('[data-open-command]').click()
                            page.locator('#master-command-dialog').wait_for(state='visible')
                            page.keyboard.press('Control+k')
                            assert not dialog.is_visible(), 'Explorer replaced admin action dialog'
                            page.keyboard.press('Escape')
                        checks.append({'role':role,'path':path,'width':width,'status':'PASS','navigation_posts':len(posts),'js_errors':list(errors)})
                    # Actual GET navigation keeps session, without a dashboard detour.
                    page.keyboard.press('Control+k')
                    page.locator('#explore-dialog-query').fill('copias' if role=='admin' else 'competicion')
                    with page.expect_navigation():
                        page.locator('#app-navigation-dialog [data-explore-item]:visible').click()
                    assert page.url == origin+('/admin/backups' if role=='admin' else '/competiciones')
                    context.close()
            browser.close()
        report={'mode':'full_local_http','source':'SIMULATED_QA','production_touched':False,'checks':checks,'blocked_boundary_events':blocked}
        (output/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'ok':True,'checks':len(checks),'output':str(output)}))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
