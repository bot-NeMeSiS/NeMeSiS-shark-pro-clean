"""Read-only geometry checks on rendered real routes; no external traffic."""
import json
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from tools.run_autonomous_product_qa import inspect_text_geometry
from tools.run_visual_browser_qa import ROUTES,PROFILES
root=Path(__file__).resolve().parents[1]
def main():
    meta=json.loads((root/'data/local_dev/visual-preview.json').read_text())
    base='http://127.0.0.1:'+str(meta['port']);rows=[]
    with sync_playwright() as pw:
     browser=pw.chromium.launch()
     for profile,size in PROFILES.items():
      for surface in ['client','admin']:
       context=browser.new_context(viewport=dict(zip(('width','height'),size)),service_workers='block')
       context.route('**/*',lambda r:r.continue_() if urlparse(r.request.url).hostname in ('127.0.0.1','localhost',None) else r.abort())
       page=context.new_page();page.goto(base+'/local-safe/login/'+surface+'?token='+meta['token'])
       routes=list(ROUTES[surface])+(['/match/'+i for i in meta.get('match_ids',[])[:3]] if surface=='client' else [])
       for route in routes:
        page.goto(base+route,wait_until='load');geometry=inspect_text_geometry(page)
        rows.append({'profile':profile,'surface':surface,'route':route,'geometry':geometry})
       context.close()
     browser.close()
    (root/'work/text-geometry.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    failures=[r for r in rows if any(v=='FAIL' for v in r['geometry'].values() if isinstance(v,str))]
    print(json.dumps({'routesChecked':len(rows),'failures':failures}))
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
