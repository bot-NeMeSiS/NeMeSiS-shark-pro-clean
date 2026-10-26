"""Real isolated Flask/HTTP/served JS. Never connects to production/providers."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse,hashlib,json,os,secrets,sqlite3,sys,tempfile,threading
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.is_relative_to(ROOT):parser.error('Use an external disposable output directory')
    out.mkdir(parents=True,exist_ok=False)
    temp=out/'app';temp.mkdir();database=temp/'shark.sqlite'
    sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True;tempfile.tempdir=str(temp)
    for key in tuple(os.environ):
        if any(part in key.upper() for part in ('TOKEN','SECRET','PASSWORD','API_KEY')):os.environ[key]=''
    from tools.local_desktop import run_local_desktop as local
    local.LOCAL_DIR=temp;local.configure_local_environment('OFFLINE_SAFE',54910,database.name)
    password=secrets.token_urlsafe(32)
    os.environ.update(NEMESIS_LOCAL_SAFE_MODE='0',ADMIN_EMAIL='qa@example.invalid',
        ADMIN_PASSWORD=password,SECRET_KEY=secrets.token_urlsafe(32),AUTOMATION_SECRET=secrets.token_urlsafe(32),
        TEMP=str(temp),TMP=str(temp),CONTINUOUS_EVOLUTION_STORAGE_ROOT=str(temp/'evolution'))
    for key in ('BACKGROUND_JOBS_ENABLED','AUTO_GENERATE_PICKS','AUTO_SEND_TELEGRAM_PICKS'):os.environ[key]='false'
    from playwright._impl._driver import compute_driver_executable
    from tools.run_v944_match_center_browser_qa import install_boundary,source_fingerprint
    before=source_fingerprint();catalogue_before=hashlib.sha256((ROOT/'localization/ui.json').read_bytes()).hexdigest()
    command=[*map(str,compute_driver_executable()),'run-driver']
    boundary=install_boundary(temp,out,database,command)
    from tools import run_autonomous_product_qa as qa
    qa.seed_database(database);qa._seed_extra(database,password,datetime.now(ZoneInfo('Europe/Madrid')))
    import app
    app.DB_PATH=str(database);app._SEEDED_DB_PATH=str(database);app.APP_INITIALIZED=True
    app.app.config.update(TESTING=True)
    app.ensure_shark_memory_table()
    with sqlite3.connect(database) as c:
        c.row_factory=sqlite3.Row
        other_user=dict(c.execute("SELECT * FROM users WHERE id='qa-client-autonomous-product'").fetchone())
        other_user.update(id='qa-workspace-other',name='Other QA',username='workspace_other',email='workspace-other@example.invalid')
        c.execute('INSERT INTO users('+','.join(other_user)+') VALUES('+','.join('?' for _ in other_user)+')',tuple(other_user.values()))
    http=[]
    @app.app.after_request
    def record(response):
        from flask import request
        http.append(dict(path=request.path,method=request.method,status=response.status_code))
        return response
    from werkzeug.serving import make_server
    server=make_server('127.0.0.1',0,app.app,threaded=True);base='http://127.0.0.1:'+str(server.server_port)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    results=[];errors=[];external=[];screens=[]
    extra_checks=dict(other_account_isolated=False,late_reply_ignored=False,
        anonymous_no_request=False,no_broadcast_privacy=False,admin_separated=False,no_js_full_page=False)
    def used():
        with sqlite3.connect(database) as c:
            return c.execute("SELECT count(*) FROM shark_memory WHERE user_id='qa-client-autonomous-product' AND event_type='client_question'").fetchone()[0]
    def reset_allowance():
        # Only this run's disposable synthetic account, before each profile.
        with sqlite3.connect(database) as c:c.execute("DELETE FROM shark_memory WHERE user_id='qa-client-autonomous-product'")
    def login(page,admin=False,identifier=None):
        page.goto(base+('/admin-login' if admin else '/cliente-login'),wait_until='domcontentloaded')
        page.locator('input[name="login"]').fill(identifier or ('admin_qa' if admin else 'client-qa@example.invalid'))
        page.locator('input[name="password"]').fill(password)
        page.locator('form[action="'+('/admin-login' if admin else '/cliente-login')+'"] button[type="submit"]').click()
        page.wait_for_url('**/admin/**' if admin else '**/app')
    def capture(page,name):
        file=out/(name+'.png');page.screenshot(path=str(file),animations='disabled')
        screens.append(dict(file=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            options={'headless':True}
            if os.getenv('NEMESIS_QA_CHROMIUM'):options['executable_path']=os.environ['NEMESIS_QA_CHROMIUM']
            browser=pw.chromium.launch(**options)
            for width in (320,390,768,1440):
                height={320:640,390:844,768:900,1440:900}[width]
                reset_allowance();context=browser.new_context(viewport=dict(width=width,height=height),service_workers='block',locale='es-ES',reduced_motion='reduce')
                def routes(route):
                    if urlsplit(route.request.url).netloc==urlsplit(base).netloc:route.continue_()
                    else:external.append(urlsplit(route.request.url).hostname);route.abort()
                context.route('**/*',routes);page=context.new_page();page.set_default_timeout(12000)
                page.on('pageerror',lambda e:errors.append(str(e)))
                def console_error(message):
                    if message.type!='error':return
                    location=message.location.get('url','')
                    if urlsplit(location).path=='/api/shark/ask' and any(str(code) in message.text for code in (401,403,429,500)):return
                    errors.append(message.text)
                page.on('console',console_error)
                login(page);page.goto(base+'/mi-cuenta',wait_until='domcontentloaded')
                root=page.locator('[data-ns-assistant]');dialog=page.locator('#ns-assistant-dialog');launcher=root.locator('[data-ns-assistant-open]')
                assert root.count()==1 and launcher.is_visible() and not dialog.is_visible()
                initial=used();start=len([x for x in http if x['path'].startswith('/api/shark/')])
                launcher.click();assert dialog.is_visible()
                assert page.locator('#ns-assistant-title').evaluate('e=>e===document.activeElement')
                assert used()==initial and len([x for x in http if x['path'].startswith('/api/shark/')])==start
                assert dialog.evaluate('e=>e.scrollWidth<=e.clientWidth+1')
                assert dialog.bounding_box()['height']<480, 'Empty compact chat must not waste a tall blank panel'
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                capture(page,str(width)+'-compact')
                # Hold the first actual request, submit twice, then let the real
                # Flask CSRF/quota/answer handler complete exactly once.
                held=[]
                def hold(route):held.append(route)
                context.route('**/api/shark/ask',hold)
                page.locator('#ns-assistant-question').fill('Resume la información deportiva disponible.')
                page.locator('#ns-assistant-form').evaluate('e=>{e.requestSubmit();e.requestSubmit();}')
                page.wait_for_function('document.querySelector("#ns-assistant-form").getAttribute("aria-busy")==="true"')
                page.wait_for_timeout(100)
                assert len(held)==1 and used()==initial
                held[0].continue_();context.unroute('**/api/shark/ask',hold)
                page.locator('.ns-assistant-message.is-bot').wait_for()
                assert used()==initial+1
                transcript=page.locator('[data-assistant-messages]').inner_text()
                assert transcript and page.locator('.ns-assistant-message.is-user').count()==1
                marker=page.locator('[data-assistant-messages]').evaluate('e=>{e.dataset.qaSameNode="preserved";return true}')
                page.locator('[data-assistant-expand]').click();assert dialog.evaluate('e=>e.classList.contains("is-expanded")')
                capture(page,str(width)+'-expanded')
                page.locator('[data-assistant-expand]').click();page.locator('[data-assistant-minimize]').click()
                assert not dialog.is_visible();launcher.click()
                assert page.locator('[data-assistant-messages]').inner_text()==transcript
                assert page.locator('[data-assistant-messages]').get_attribute('data-qa-same-node')=='preserved'
                page.locator('[data-assistant-hide]').click();assert not launcher.is_visible()
                page.locator('[data-open-explore]:visible').first.click()
                page.locator('#app-navigation-dialog [data-ns-assistant-restore]').click()
                assert dialog.is_visible() and not launcher.is_visible()
                assert page.locator('[data-assistant-messages]').inner_text()==transcript
                page.keyboard.press('Escape');assert not dialog.is_visible()
                assert launcher.evaluate('e=>e===document.activeElement')
                capture(page,str(width)+'-launcher')
                assert used()==initial+1
                if width<768:
                    nav=page.locator('[data-nav-zone="client-bottom"]')
                    assert nav.locator('a').count()==4
                    assert len(nav.evaluate('e=>getComputedStyle(e).gridTemplateColumns.split(" ")'))==4
                # UI-only error fixtures do not stand in for backend gates.
                launcher.click()
                page.keyboard.press('Shift+Tab')
                assert dialog.locator('footer a').evaluate('e=>e===document.activeElement')
                for _ in range(14):
                    page.keyboard.press('Tab')
                    focused=dialog.evaluate('e=>({inside:e.contains(document.activeElement),open:e.open,tag:document.activeElement.tagName,id:document.activeElement.id,html:document.activeElement.outerHTML.slice(0,180)})')
                    if not focused['inside']:
                        (out/'focus-failure.json').write_text(json.dumps(dict(step=_,state=focused),indent=2))
                        capture(page,str(width)+'-focus-failure')
                    assert focused['inside'],focused
                def malicious(route):route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'shark':{'answer':'<img src=x onerror=alert(1)>'}}))
                context.route('**/api/shark/ask',malicious)
                page.locator('#ns-assistant-question').fill('UI fixture escaping')
                page.locator('#ns-assistant-form button[type="submit"]').click()
                page.locator('.ns-assistant-message.is-bot').last.wait_for()
                page.wait_for_function('document.querySelectorAll(".ns-assistant-message.is-bot").length===2')
                assert root.locator('.ns-assistant-message img').count()==0
                assert '<img' in root.locator('.ns-assistant-message.is-bot').last.inner_text()
                context.unroute('**/api/shark/ask',malicious)
                def limited(route):route.fulfill(status=429,content_type='application/json',body=json.dumps({'ok':False,'usage':{'remaining':0}}))
                context.route('**/api/shark/ask',limited)
                page.locator('#ns-assistant-question').fill('UI fixture quota')
                page.locator('#ns-assistant-form button[type="submit"]').click()
                page.wait_for_function('document.querySelector("[data-assistant-upgrade]").hidden===false')
                assert page.locator('#ns-assistant-form button[type="submit"]').is_disabled()
                assert used()==initial+1
                context.unroute('**/api/shark/ask',limited)
                # Another real document in this context clears old private DOM.
                other=context.new_page();other.goto(base+'/mi-cuenta',wait_until='domcontentloaded')
                page.wait_for_function('document.querySelector("[data-assistant-messages]").childElementCount===0')
                assert page.locator('#ns-assistant-question').input_value()=='' and not dialog.is_visible()
                assert not page.locator('#ns-assistant-form').is_visible()
                if width==1440:
                    # Change the actual synthetic account using real logout and
                    # login handlers, not a fabricated identity label.
                    other.goto(base+'/logout',wait_until='domcontentloaded')
                    other.locator('form[action="/logout"] button[type="submit"]').click()
                    login(other,identifier='workspace-other@example.invalid')
                    other.locator('[data-ns-assistant-open]').click()
                    other.locator('#ns-assistant-question').fill('Resume el calendario disponible.')
                    other.locator('#ns-assistant-form button[type="submit"]').click()
                    other.locator('.ns-assistant-message.is-bot').wait_for()
                    with sqlite3.connect(database) as c:
                        assert c.execute("SELECT count(*) FROM shark_memory WHERE user_id='qa-workspace-other' AND event_type='client_question'").fetchone()[0]==1
                    assert used()==initial+1
                    assert page.locator('[data-assistant-messages]').inner_text()==''
                    extra_checks['other_account_isolated']=True
                other.close()
                if width==1440:
                    # A deliberately late UI fixture ignores AbortSignal. The
                    # generation check must still discard it after transition.
                    page.reload(wait_until='domcontentloaded');launcher.click()
                    page.evaluate('''() => {
                      const original=window.fetch.bind(window);
                      window.fetch=(url,options)=>url==='/api/shark/ask'
                        ?new Promise(resolve=>{window.qaLateReply=()=>resolve(new Response(JSON.stringify({ok:true,shark:{answer:'LATE_QA_PRIVATE'}}),{status:200,headers:{'Content-Type':'application/json'}}));})
                        :original(url,options);
                    }''')
                    page.locator('#ns-assistant-question').fill('Late UI fixture')
                    page.locator('#ns-assistant-form button[type="submit"]').click()
                    page.wait_for_function('Boolean(window.qaLateReply)')
                    transition=context.new_page();transition.goto(base+'/mi-cuenta',wait_until='domcontentloaded')
                    page.wait_for_function('document.querySelector("#ns-assistant-form").hidden===true')
                    page.evaluate('window.qaLateReply()');page.wait_for_timeout(100)
                    assert 'LATE_QA_PRIVATE' not in page.locator('[data-assistant-messages]').inner_text()
                    extra_checks['late_reply_ignored']=True
                    transition.close()
                # Reset document state, not quota, for a transport fault fixture.
                page.reload(wait_until='domcontentloaded');launcher.click()
                faults=[]
                def unavailable(route):
                    faults.append(1);route.fulfill(status=500,content_type='application/json',body='{"ok":false}')
                context.route('**/api/shark/ask',unavailable)
                page.locator('#ns-assistant-question').fill('UI fixture recoverable failure')
                page.locator('#ns-assistant-form button[type="submit"]').click()
                page.wait_for_function('document.querySelector("#ns-assistant-form").getAttribute("aria-busy")==="false"')
                assert page.locator('#ns-assistant-question').input_value()=='UI fixture recoverable failure'
                assert page.locator('#ns-assistant-form button[type="submit"]').is_enabled()
                page.wait_for_timeout(100);assert len(faults)==1
                context.unroute('**/api/shark/ask',unavailable)
                def signed_out(route):route.fulfill(status=401,content_type='application/json',body='{"login_required":true}')
                context.route('**/api/shark/ask',signed_out)
                page.locator('#ns-assistant-form button[type="submit"]').click()
                dialog.wait_for(state='hidden');launcher.click()
                assert page.locator('[data-assistant-messages]').inner_text()=='' and page.locator('#ns-assistant-question').input_value()==''
                assert not page.locator('#ns-assistant-form').is_visible() and page.locator('[data-assistant-login]').is_visible()
                context.unroute('**/api/shark/ask',signed_out)
                # Real server CSRF rejection must happen before quota consumption.
                page.reload(wait_until='domcontentloaded');launcher.click()
                with sqlite3.connect(database) as c:before_csrf=c.execute("SELECT count(*) FROM shark_memory WHERE event_type='client_question'").fetchone()[0]
                page.locator('meta[name="csrf-token"]').evaluate('e=>e.content="invalid-workspace-qa"')
                page.locator('#ns-assistant-question').fill('Rejected CSRF QA')
                page.locator('#ns-assistant-form button[type="submit"]').click();dialog.wait_for(state='hidden')
                with sqlite3.connect(database) as c:assert c.execute("SELECT count(*) FROM shark_memory WHERE event_type='client_question'").fetchone()[0]==before_csrf
                from tools.run_v929_click_navigation_qa import _click_one
                navigation=_click_one(page,base,'/mi-cuenta',dict(tag='a',target='/shark',text='Abrir SHARK'),12000,'client_workspace')
                assert navigation['result']=='OK' and navigation['final_path']=='/shark'
                assert navigation.get('interaction')=='shark_workspace_and_full_page'
                context.close()
                results.append(dict(width=width,height=height,real_quota_delta=1,double_submit_one_request=True,same_dom_preserved=True,hide_restore=True,session_transition_clears=True,keyboard_trap=True,real_csrf_before_quota=True,full_page_navigation=True,second_account_checked=width==1440,ui_fault_fixtures=['200_markup','429','500','401']))
            # Anonymous JavaScript opening has no question form or API call.
            context=browser.new_context(service_workers='block');context.route('**/*',routes)
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'/faq',wait_until='domcontentloaded')
            before_asks=sum(x['path'].startswith('/api/shark/') for x in http)
            page.locator('[data-ns-assistant-open]').click()
            assert page.locator('#ns-assistant-dialog').is_visible() and page.locator('#ns-assistant-form').count()==0
            assert sum(x['path'].startswith('/api/shark/') for x in http)==before_asks
            extra_checks['anonymous_no_request']=True
            context.close()
            # Restricted-browser fallback is a UI fault fixture, not a new
            # backend answer or a physical browser/device certification.
            context=browser.new_context(service_workers='block');context.route('**/*',routes)
            context.add_init_script('''window.BroadcastChannel=undefined;
              const original=window.fetch.bind(window);
              window.fetch=(url,options)=>url==='/api/shark/ask'
                ?Promise.resolve(new Response(JSON.stringify({ok:true,shark:{answer:'FALLBACK_QA_PRIVATE'}}),{status:200,headers:{'Content-Type':'application/json'}}))
                :original(url,options);''')
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));login(page)
            page.locator('[data-ns-assistant-open]').click();page.locator('#ns-assistant-question').fill('Fallback UI fixture')
            page.locator('#ns-assistant-form button[type="submit"]').click();page.locator('.ns-assistant-message.is-bot').wait_for()
            page.evaluate('window.dispatchEvent(new Event("blur"))')
            assert page.locator('[data-assistant-messages]').inner_text()=='' and not page.locator('#ns-assistant-dialog').is_visible()
            extra_checks['no_broadcast_privacy']=True
            context.close()
            # Verify server-rendered separation on the real Admin handler.
            context=browser.new_context(service_workers='block');context.route('**/*',routes)
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            login(page,admin=True);page.goto(base+'/admin/control-center',wait_until='domcontentloaded')
            assert page.locator('[data-ns-assistant]').count()==0
            extra_checks['admin_separated']=True
            context.close()
            # Progressive GET is still usable with scripts disabled.
            context=browser.new_context(java_script_enabled=False,service_workers='block');context.route('**/*',routes)
            page=context.new_page();page.goto(base+'/faq',wait_until='domcontentloaded')
            page.locator('[data-ns-assistant-open]').click();page.wait_for_url('**/shark')
            assert page.locator('[data-ns-assistant]').count()==0
            extra_checks['no_js_full_page']=True
            context.close();browser.close()
    finally:
        server.shutdown();thread.join(timeout=10);server.server_close()
        receipt={'results':results,'extra_checks':extra_checks,'errors':errors,'boundary_events':boundary,'external_requests':external,'http':http,'screenshots':screens,'source_unchanged':before==source_fingerprint() and catalogue_before==hashlib.sha256((ROOT/'localization/ui.json').read_bytes()).hexdigest(),'source_fingerprint':before,'origin':'SIMULATED_QA','real_application':str(app.__file__)==str(ROOT/'app.py'),'limits':'Ephemeral synthetic accounts/store; actual local Flask HTTP/served assets, baseline SHARK and CSRF rejection. UI 200-markup/429/500/401, late-response and missing-BroadcastChannel fixtures injected; backend auth/quota gates checked separately. Real two-account transition checked on desktop. Chromium only, not physical iOS/Android or production certification.'}
        unexpected_http=[x for x in http if x['status']>=400 and not (x['path']=='/api/shark/ask' and x['status']==403)]
        receipt['unexpected_http']=unexpected_http
        receipt['ok']=len(results)==4 and all(extra_checks.values()) and not errors and not boundary and not external and not unexpected_http and receipt['source_unchanged']
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    assert receipt['ok'],out
    print(json.dumps(dict(ok=True,profiles=len(results),output=str(out),screenshots=len(screens))))


if __name__=='__main__':main()
