"""Browser checks over actual guarded-App HTML, not mocked handlers."""
import argparse,json,hashlib,mimetypes
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

def check_javascript(browser,root,source,out):
    import re
    from datetime import datetime,timezone
    from email.utils import format_datetime
    html=(source/'directo-live.html').read_text(encoding='utf-8')
    bootstrap=json.loads(re.search(r'<script[^>]*data-directo-fixture-identity[^>]*>(.*?)</script>',html,re.S).group(1))
    now=datetime.fromisoformat(bootstrap['generated_at_madrid'])
    results=[]
    for width in (390,1440):
        for mode in (503,304,200):
            context=browser.new_context(viewport={'width':width,'height':960},service_workers='block')
            page=context.new_page();writes=[];polls=[]
            page.clock.install(time=now)
            def route(r):
                url=urlsplit(r.request.url)
                if r.request.method!='GET':
                    writes.append(r.request.method);r.abort();return
                if url.netloc!='nemesis-isolated.invalid':r.abort();return
                if url.path=='/screen':
                    r.fulfill(status=200,content_type='text/html; charset=utf-8',body=html);return
                if url.path=='/api/realtime/sports':
                    polls.append(r.request.url)
                    headers={'Date':format_datetime(now.astimezone(timezone.utc),usegmt=True),'ETag':'"isolated-unchanged"'}
                    r.fulfill(status=mode,headers=headers,content_type='application/json',
                        body=json.dumps(bootstrap) if mode==200 else '');return
                asset=(root/url.path.lstrip('/')).resolve()
                if url.path.startswith('/static/') and asset.is_relative_to(root/'static') and asset.is_file():
                    r.fulfill(status=200,body=asset.read_bytes(),content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream');return
                r.fulfill(status=404,body='')
            page.route('**/*',route)
            try:
                page.goto('http://nemesis-isolated.invalid/screen',wait_until='networkidle')
                board=page.locator('[data-v934-directo]')
                cards=board.locator('[data-v934-match-card]')
                assert cards.count()==2
                assert board.locator('[data-canonical-live="true"]').count()==2
                links=board.locator('a[href^="/match/"]')
                before=links.evaluate_all('(es)=>es.map(e=>e.getAttribute("href"))')
                page.clock.run_for(135000)
                page.wait_for_timeout(50)
                assert cards.count()==2
                assert board.locator('[data-canonical-live="true"]').count()==0
                assert board.get_attribute('data-sports-live-confirmed')=='0'
                assert all(cards.nth(i).is_visible() for i in range(2))
                assert all(board.locator('[data-v934-minute]').nth(i).is_hidden() for i in range(2))
                assert links.evaluate_all('(es)=>es.map(e=>e.getAttribute("href"))')==before
                links.first.focus()
                assert links.first.evaluate('(e)=>e===document.activeElement')
                assert polls and not writes
                results.append({'width':width,'poll_http':mode,'polls':len(polls),
                    'expired_live_count':0,'cards_retained':2,'links_preserved':True,'outbound_writes':writes})
                if width==390 and mode==503:
                    board.screenshot(path=str(out/'directo-expired-javascript-390.png'))
            finally:context.close()
    return results

def check_recovery(browser,root,source,out):
    import re
    from datetime import datetime,timedelta,timezone
    from email.utils import format_datetime
    html=(source/'directo-before-recovery.html').read_text(encoding='utf-8')
    initial=json.loads(re.search(r'<script[^>]*data-directo-fixture-identity[^>]*>(.*?)</script>',html,re.S).group(1))
    fresh=json.loads((source/'directo-recovery-payload.json').read_text(encoding='utf-8'))
    now=datetime.fromisoformat(initial['generated_at_madrid'])
    # Only transport scheduling metadata is shortened in this isolated browser;
    # source clocks, scores, identity proofs, deadlines and frames remain exact.
    initial['poll_after_seconds']=45
    results=[]
    for width in (390,1440):
        context=browser.new_context(viewport={'width':width,'height':960},service_workers='block')
        page=context.new_page();page.clock.install(time=now)
        phase={'fresh':False};polls=[];writes=[]
        def route(r):
            url=urlsplit(r.request.url)
            if r.request.method!='GET':writes.append(r.request.method);r.abort();return
            if url.netloc!='nemesis-isolated.invalid':r.abort();return
            if url.path=='/screen':r.fulfill(status=200,content_type='text/html; charset=utf-8',body=html);return
            if url.path=='/api/realtime/sports':
                payload=fresh if phase['fresh'] else initial
                polls.append(phase['fresh'])
                server=now+timedelta(seconds=45 if phase['fresh'] else 0)
                r.fulfill(status=200,content_type='application/json',
                    headers={'Date':format_datetime(server.astimezone(timezone.utc),usegmt=True)},
                    body=json.dumps(payload));return
            asset=(root/url.path.lstrip('/')).resolve()
            if url.path.startswith('/static/') and asset.is_relative_to(root/'static') and asset.is_file():
                r.fulfill(status=200,body=asset.read_bytes(),content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream');return
            r.fulfill(status=404,body='')
        page.route('**/*',route)
        try:
            page.goto('http://nemesis-isolated.invalid/screen',wait_until='networkidle')
            board=page.locator('[data-v934-directo]')
            assert board.locator('[data-canonical-live="true"]').count()==2
            ids=board.locator('[data-v934-match-card]').evaluate_all('(es)=>es.map(e=>e.dataset.v934MatchId)')
            page.clock.run_for(15000);page.wait_for_timeout(30)
            assert board.locator('[data-canonical-live="true"]').count()==0
            phase['fresh']=True
            page.clock.run_for(31000);page.wait_for_timeout(50)
            assert True in polls,('No fresh transport poll',polls)
            assert board.locator('[data-canonical-live="true"]').count()==2
            assert board.get_attribute('data-sports-live-confirmed')=='2'
            assert board.locator('[data-v934-match-card]').evaluate_all('(es)=>es.map(e=>e.dataset.v934MatchId)')==ids
            assert board.locator('[data-v934-match-card]').count()==2
            assert all(board.locator('[data-v934-minute]').nth(i).is_visible() for i in range(2))
            assert not writes
            results.append({'width':width,'expired_live':0,'recovered_live':2,'same_card_ids':ids,'writes':writes})
        finally:context.close()
    return results

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repo-root',type=Path,required=True)
    p.add_argument('--receipt-dir',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--browser')
    p.add_argument('--javascript-only',action='store_true')
    p.add_argument('--recovery-only',action='store_true')
    a=p.parse_args()
    root=a.repo_root.resolve();source=a.receipt_dir.resolve();out=a.output_dir.resolve()
    out.mkdir(parents=True,exist_ok=True)
    receipt=json.loads((source/'receipt.json').read_text(encoding='utf-8'))
    assert receipt['boundary_events']==[] and receipt['sources_unchanged']
    assert receipt['live_minimal_contracts']['success']
    results=[];blocked=[];writes=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(**({'executable_path':a.browser} if a.browser else {}))
        try:
            for width in (() if (a.javascript_only or a.recovery_only) else (320,360,390,768,1440)):
                for filename,selector in (('directo-retained.html','[data-directo-retained-observations]'),
                                           ('match-fields.html','[data-match-field-availability]')):
                    data=(source/filename).read_bytes()
                    context=browser.new_context(viewport={'width':width,'height':960},
                        java_script_enabled=False,reduced_motion='reduce',service_workers='block')
                    page=context.new_page()
                    def route(r):
                        url=urlsplit(r.request.url)
                        if r.request.method!='GET':
                            writes.append(r.request.method);r.abort();return
                        if url.netloc!='nemesis-isolated.invalid':
                            blocked.append(url.netloc);r.abort();return
                        if url.path=='/screen':
                            r.fulfill(status=200,content_type='text/html; charset=utf-8',body=data);return
                        asset=(root/url.path.lstrip('/')).resolve()
                        if url.path.startswith('/static/') and asset.is_relative_to(root/'static') and asset.is_file():
                            r.fulfill(status=200,body=asset.read_bytes(),content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream');return
                        r.fulfill(status=404,body='')
                    page.route('**/*',route)
                    try:
                        page.goto('http://nemesis-isolated.invalid/screen',wait_until='networkidle')
                        panel=page.locator(selector)
                        assert panel.count()==1 and panel.is_visible()
                        box=panel.bounding_box()
                        assert box and box['x']>=-1 and box['x']+box['width']<=width+1,(filename,width,box)
                        assert panel.evaluate('(e)=>e.scrollWidth<=e.clientWidth+2'),(filename,width,'panel overflow')
                        if filename.startswith('directo'):
                            cards=panel.locator('[data-directo-observation-id]')
                            assert cards.count()==2
                            assert len(set(cards.evaluate_all('(es)=>es.map(e=>e.dataset.directoObservationId)')))==2
                            assert panel.locator('time[datetime]').count()==2
                            assert panel.locator('a[href^="/match/"]').count()==2
                            assert panel.locator('[data-canonical-live="true"]').count()==0
                            link=panel.locator('a').first
                            link.focus()
                            assert link.evaluate('(e)=>e===document.activeElement')
                        else:
                            assert panel.locator('[data-match-field]').count()==7
                            assert all(panel.locator('[data-match-field]').nth(i).is_visible() for i in range(7))
                        if width in (390,1440):
                            panel.scroll_into_view_if_needed()
                            panel.screenshot(path=str(out/(filename.replace('.html','')+'-'+str(width)+'.png')))
                        results.append({'html':filename,'width':width,'pass':True,
                            'sha256':hashlib.sha256(data).hexdigest()})
                    finally:context.close()
            js_results=[] if a.recovery_only else check_javascript(browser,root,source,out)
            recovery_results=check_recovery(browser,root,source,out) if a.recovery_only else []
        finally:browser.close()
    assert not writes
    record={'actual_app_receipt':str(source/'receipt.json'),'checks':results,
        'outbound_writes':writes,'external_requests_blocked':sorted(set(blocked)),
        'javascript_exercised':True,'javascript_checks':js_results,'recovery_checks':recovery_results,'scope':'New panels only; not full page/role/provider or speed certification'}
    (out/'browser-receipt.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({'checks':len(results),'javascript_checks':len(js_results),'recovery_checks':len(recovery_results),'passed':all(v['pass'] for v in results),'writes':writes}))
if __name__=='__main__':main()
