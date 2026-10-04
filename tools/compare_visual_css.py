import argparse, json, subprocess, statistics, time
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--baseline',default='b7e8aea1')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
meta=json.loads((root/'data/local_dev/visual-preview.json').read_text())
base='http://127.0.0.1:'+str(meta['port'])
old=subprocess.check_output(['git','show',args.baseline+':static/product-system.css'])
rows=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch()
    for repeat in range(3):
        for version in (['before','after'] if repeat%2==0 else ['after','before']):
            for route in ['/app','/calendario','/directo','/shark','/mi-cuenta']:
                ctx=browser.new_context(viewport={'width':390,'height':844},service_workers='block')
                ctx.route('**/*',lambda r:r.continue_() if urlparse(r.request.url).hostname in ('127.0.0.1','localhost',None) else r.abort())
                if version=='before':
                    ctx.route('**/product-system.css*',lambda r:r.fulfill(status=200,content_type='text/css',body=old))
                page=ctx.new_page()
                page.goto(base+'/local-safe/login/client?token='+meta['token'])
                started=time.perf_counter()
                page.goto(base+route,wait_until='load')
                load=round((time.perf_counter()-started)*1000,1)
                resources=page.evaluate('performance.getEntriesByType("resource").map(e=>({url:new URL(e.name).pathname,bytes:e.transferSize}))')
                rows.append({'version':version,'route':route,'loadMs':load,'resources':resources})
                ctx.close()
    browser.close()
summary=[]
for route in ['/app','/calendario','/directo','/shark','/mi-cuenta']:
    item={'route':route}
    for version in ['before','after']:
        values=[r for r in rows if r['route']==route and r['version']==version]
        item[version]={'medianLoadMs':statistics.median(r['loadMs'] for r in values),'medianResources':statistics.median(len(r['resources']) for r in values)}
    summary.append(item)
(root/'reports/redesign-20261004/css-comparison.json').write_text(json.dumps({'method':'CSS-only A/B on identical current templates and empty offline database; 3 samples per route/version, 390x844. Not a full historical backend benchmark.','summary':summary,'samples':rows},indent=2),encoding='utf-8')
print(json.dumps(summary))
