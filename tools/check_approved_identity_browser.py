"""Real isolated client/Admin HTTP and approved visual assets. Never production."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import os
import re
import secrets
import sys
import tempfile
import threading
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.is_relative_to(ROOT):parser.error('Use an external disposable directory')
    out.mkdir(parents=True,exist_ok=False)
    temp=out/'app';temp.mkdir();database=temp/'identity.sqlite'
    sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True;tempfile.tempdir=str(temp)
    for key in tuple(os.environ):
        if re.search(r'TOKEN|SECRET|PASSWORD|_KEY(?:_|$)',key.upper()) or key=='DATABASE_URL':
            os.environ[key]=''
    from tools.local_desktop import run_local_desktop as local
    local.LOCAL_DIR=temp;local.configure_local_environment('OFFLINE_SAFE',54910,database.name)
    password=secrets.token_urlsafe(32)
    os.environ.update(NEMESIS_LOCAL_SAFE_MODE='0',ADMIN_EMAIL='qa@example.invalid',
        ADMIN_PASSWORD=password,SECRET_KEY=secrets.token_urlsafe(32),
        AUTOMATION_SECRET=secrets.token_urlsafe(32),TEMP=str(temp),TMP=str(temp),
        CONTINUOUS_EVOLUTION_STORAGE_ROOT=str(temp/'evolution'))
    for key in ('BACKGROUND_JOBS_ENABLED','AUTO_GENERATE_PICKS','AUTO_SEND_TELEGRAM_PICKS'):
        os.environ[key]='false'
    from playwright._impl._driver import compute_driver_executable
    from tools.run_v944_match_center_browser_qa import install_boundary,source_fingerprint
    command=[*map(str,compute_driver_executable()),'run-driver']
    before=source_fingerprint()
    asset_files=list((ROOT/'static/img/approved-identity').glob('*'))
    asset_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in asset_files if p.is_file()}
    boundary=install_boundary(temp,out,database,command)
    from tools import run_autonomous_product_qa as qa
    qa.seed_database(database);qa._seed_extra(database,password,datetime.now(ZoneInfo('Europe/Madrid')))
    import app
    app.DB_PATH=str(database);app._SEEDED_DB_PATH=str(database);app.APP_INITIALIZED=True
    app.app.config.update(TESTING=True)
    http=[];errors=[];external=[];views=[]
    @app.app.after_request
    def record(response):
        from flask import request
        http.append(dict(method=request.method,path=request.path,status=response.status_code))
        return response
    from werkzeug.serving import make_server
    server=make_server('127.0.0.1',0,app.app,threaded=True)
    base='http://127.0.0.1:'+str(server.server_port)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    from playwright.sync_api import sync_playwright
    def login(page,admin):
        path='/admin-login' if admin else '/cliente-login'
        page.goto(base+path,wait_until='domcontentloaded')
        page.locator('input[name="login"]').fill('admin_qa' if admin else 'client-qa@example.invalid')
        page.locator('input[name="password"]').fill(password)
        page.locator('form[action="'+path+'"] button[type="submit"]').click()
        page.wait_for_url('**/admin/**' if admin else '**/app')
    def check(page,width,role,path):
        response=page.goto(base+path,wait_until='domcontentloaded')
        assert response and response.status==200,(role,path,response.status if response else None)
        page.wait_for_load_state('networkidle')
        scene=page.locator('[data-brand-scene]')
        assert scene.count()==1 and scene.get_attribute('aria-hidden')=='true'
        assert scene.evaluate('(el)=>getComputedStyle(el).position')=='fixed'
        assert scene.evaluate('(el)=>getComputedStyle(el).pointerEvents')=='none'
        assert scene.evaluate('(el)=>getComputedStyle(el).animationName')=='none'
        expected_ocean='ocean-768' if width<768 else 'ocean-1600'
        expected_shark='wireframe-480' if width<768 else 'wireframe-960'
        assert expected_ocean in scene.evaluate('(el)=>getComputedStyle(el,"::before").backgroundImage')
        assert expected_shark in scene.evaluate('(el)=>getComputedStyle(el,"::after").backgroundImage')
        decoded=scene.evaluate('''async (el) => {
          const sources=["::before","::after"].flatMap(pseudo=>
            Array.from(getComputedStyle(el,pseudo).backgroundImage.matchAll(/url\\(["']?([^"')]+)["']?\\)/g),m=>m[1]));
          return Promise.all(sources.map(async src=>{
            const image=new Image();image.src=src;await image.decode();
            return {src,width:image.naturalWidth,height:image.naturalHeight};
          }));
        }''')
        assert len(decoded)==2 and all(item['width']>0 and item['height']>0 for item in decoded)
        assert page.evaluate('getComputedStyle(document.body,"::before").content')=='none'
        assert page.evaluate('getComputedStyle(document.body,"::after").content')=='none'
        logos=page.locator('img[data-brand-source="owner-approved-family-20261023"]:visible')
        assert logos.count()>=1,(role,path)
        for logo in logos.all():
            assert logo.evaluate('(el)=>el.complete&&el.naturalWidth>0')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(role,path,width)
        assert page.locator('[data-ns-assistant]').count()==(0 if role=='admin' else 1)
        file=out/(str(width)+'-'+role+'-'+path.strip('/').replace('/','-')+'.png')
        page.screenshot(path=str(file),animations='disabled')
        views.append(dict(width=width,role=role,path=path,screenshot=file.name,
                          sha256=hashlib.sha256(file.read_bytes()).hexdigest(),decoded_scene=decoded))
    try:
        with sync_playwright() as pw:
            options={'headless':True}
            if os.getenv('NEMESIS_QA_CHROMIUM'):options['executable_path']=os.environ['NEMESIS_QA_CHROMIUM']
            browser=pw.chromium.launch(**options)
            for width,height in ((320,740),(390,844),(768,900),(1440,900)):
                for admin in (False,True):
                    context=browser.new_context(viewport=dict(width=width,height=height),
                        service_workers='block',locale='es-ES',reduced_motion='reduce')
                    def routes(route):
                        if urlsplit(route.request.url).netloc==urlsplit(base).netloc:route.continue_()
                        else:external.append(urlsplit(route.request.url).hostname);route.abort()
                    context.route('**/*',routes)
                    page=context.new_page();page.set_default_timeout(12000)
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    if not admin:check(page,width,'public','/cliente-login')
                    login(page,admin)
                    for path in (('/admin/control-center','/admin/users','/admin/data-center') if admin else
                                 ('/app','/calendario','/directo','/mi-cuenta')):
                        check(page,width,'admin' if admin else 'client',path)
                    page.emulate_media(forced_colors='active')
                    assert not page.locator('[data-brand-scene]').is_visible()
                    context.close()
            browser.close()
    finally:
        server.shutdown();thread.join(timeout=10);server.server_close()
        after_assets={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in asset_files if p.is_file()}
        receipt=dict(views=views,http=http,errors=errors,external_requests=external,
            boundary_events=boundary,source_unchanged=before==source_fingerprint(),
            assets_unchanged=asset_hashes==after_assets,asset_hashes=asset_hashes,
            origin='SIMULATED_QA',real_application=str(app.__file__)==str(ROOT/'app.py'),
            limits='Owned synthetic SQLite/accounts and actual local HTTP login/assets; no production, real provider, physical device, purchase or global performance certification.')
        receipt['unexpected_http']=[r for r in http if r['status']>=400]
        receipt['no_shark_question']=not any(r['path']=='/api/shark/ask' for r in http)
        receipt['ok']=(len(views)==32 and receipt['source_unchanged'] and receipt['assets_unchanged']
            and receipt['no_shark_question'] and not errors and not external and not boundary and not receipt['unexpected_http'])
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    assert receipt['ok'],out
    print(json.dumps(dict(ok=True,identity_views=len(views),output=str(out))))


if __name__=='__main__':main()
