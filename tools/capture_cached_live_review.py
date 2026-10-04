"""Capture current cached LIVE evidence without extending source validity."""
import json,urllib.request,threading,sys
from pathlib import Path
from urllib.parse import urlparse
from werkzeug.serving import make_server,WSGIRequestHandler
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from tools.run_visual_preview import prepare
from tools.run_visual_browser_qa import INSPECT
from tools.run_autonomous_product_qa import inspect_text_geometry
import os
def main():
    with urllib.request.urlopen('https://bot-apuestas-crgf.onrender.com/api/realtime/sports?scope=all',timeout=30) as response:payload=json.load(response)
    assert payload.get('ok') and payload.get('no_external_calls') is True
    snapshot=root/'work/live-evidence-snapshot.json';snapshot.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
    module=prepare(port=54922,snapshot=snapshot)
    class Quiet(WSGIRequestHandler):
     def log_request(self,*args,**kwargs):pass
    server=make_server('127.0.0.1',0,module.app,threaded=True,request_handler=Quiet);threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(server.server_port)
    output=root/'work/live-populated';output.mkdir(exist_ok=True);rows=[]
    try:
     with sync_playwright() as pw:
      browser=pw.chromium.launch()
      for profile,size in [('desktop',(1440,900)),('tablet',(768,1024)),('mobile',(390,844))]:
       ctx=browser.new_context(viewport=dict(zip(('width','height'),size)),service_workers='block')
       ctx.route('**/*',lambda r:r.continue_() if urlparse(r.request.url).hostname in ('127.0.0.1','localhost',None) else r.abort())
       page=ctx.new_page();page.goto(base+'/local-safe/login/client?token='+os.environ['NEMESIS_LOCAL_ACCESS_TOKEN'])
       for route in ['/directo','/app']:
        response=page.goto(base+route,wait_until='load');name=profile+route.replace('/','-')+'.jpg';page.screenshot(path=str(output/name),full_page=True,type='jpeg',quality=80)
        page.screenshot(path=str(output/name.replace('.jpg','-viewport.jpg')),full_page=False,type='jpeg',quality=85)
        live=page.locator('[data-sports-live-confirmed]').first.get_attribute('data-sports-live-confirmed')
        row={'profile':profile,'surface':'client','route':route,'status':response.status,'screenshot':name,'viewportScreenshot':name.replace('.jpg','-viewport.jpg'),'sourceGenerated':payload.get('generated_at_madrid'),'liveConfirmed':int(live or 0),'geometry':inspect_text_geometry(page),**page.evaluate(INSPECT)};rows.append(row);print(json.dumps({'profile':profile,'route':route,'confirmedLive':row['liveConfirmed'],'overflow':row['overflow']}),flush=True)
       ctx.close()
      browser.close()
    finally:server.shutdown()
    (output/'observations.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
    assert all(r['status']==200 and not r['overflow'] and not r['brokenImages'] and not r['clientTextViolations'] for r in rows)
    print('Real cached LIVE captures:',len(rows),'confirmed:',[r['liveConfirmed'] for r in rows])


if __name__ == "__main__":
    main()
