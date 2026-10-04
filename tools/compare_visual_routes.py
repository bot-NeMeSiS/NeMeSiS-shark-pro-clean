"""Compare actual route rendering and SQL on one immutable real cache snapshot.
Historical templates versus canonical templates; unchanged current business code.
No production actions, network, SQL text or user records are recorded.
"""
import argparse, io, tarfile, json, subprocess, statistics, time, sqlite3, socket, os
from pathlib import Path
from jinja2 import ChoiceLoader, DictLoader
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from tools.run_visual_preview import prepare
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--snapshot',type=Path,default=root/'work/public-cache-snapshot.json')
    parser.add_argument('--baseline',default='b7e8aea1')
    parser.add_argument('--output',type=Path,default=root/'work/route-performance.json')
    parser.add_argument('--surfaces',nargs='+',choices=['client','admin'],default=['client','admin'])
    args=parser.parse_args()
    module=prepare(snapshot=args.snapshot)
    original_loader=module.app.jinja_env.loader
    archive=subprocess.check_output(['git','archive',args.baseline,'templates'])
    with tarfile.open(fileobj=io.BytesIO(archive)) as files:
     old={member.name.removeprefix('templates/'):files.extractfile(member).read().decode('utf-8') for member in files.getmembers() if member.isfile() and member.name.endswith('.html')}
    loaders={'before':ChoiceLoader([DictLoader(old),original_loader]),'after':original_loader}
    counters={};original_connect=sqlite3.connect

    def connect(*a,**kw):
     c=original_connect(*a,**kw)
     def trace(statement):
      kind=(statement.lstrip().split(None,1) or [''])[0].upper()
      counters[kind]=counters.get(kind,0)+1
     c.set_trace_callback(trace)
     return c
    sqlite3.connect=connect
    external=[]
    def forbidden(*a,**kw):
     external.append('network attempt');raise RuntimeError('Outbound network prohibited in visual benchmark')
    socket.socket.connect=forbidden
    routes=['/app','/calendario','/directo','/picks','/combinadas','/shark','/telegram','/mi-cuenta','/membresias','/onboarding']+['/match/'+i for i in module.app.config['VISUAL_REVIEW_MATCH_IDS'][:3]]
    surfaces={'client':routes,'admin':['/admin/dashboard','/admin/matches','/admin/picks','/admin/telegram/command-center','/admin/users','/admin/memberships','/admin/data-center','/admin/founder-os','/admin/founder-control']}
    route_surfaces={route:surface for surface,items in surfaces.items() if surface in args.surfaces for route in items}
    routes=list(route_surfaces)
    rows=[]
    for route in routes:
     # Warm each route immediately before its alternating samples so unrelated
     # application cache expiry does not bias one template set.
     for version in loaders:
      module.app.jinja_env.loader=loaders[version]
      with module.app.test_client() as client:
       client.get('/local-safe/login/'+route_surfaces[route]+'?token='+os.environ['NEMESIS_LOCAL_ACCESS_TOKEN'])
       client.get(route)
     for repeat in range(5):
      for version in (['before','after'] if repeat%2==0 else ['after','before']):
       module.app.jinja_env.loader=loaders[version]
       with module.app.test_client() as client:
        client.get('/local-safe/login/'+route_surfaces[route]+'?token='+os.environ['NEMESIS_LOCAL_ACCESS_TOKEN'])
        counters.clear();external.clear();start=time.perf_counter();response=client.get(route)
        rows.append({'version':version,'route':route,'repeat':repeat,'status':response.status_code,'renderMs':round((time.perf_counter()-start)*1000,2),'htmlBytes':len(response.data),'sqlStatements':dict(counters),'externalAttempts':len(external)})
    summary=[]
    for route in routes:
     item={'route':route}
     for version in loaders:
      subset=[r for r in rows if r['route']==route and r['version']==version]
      item[version]={'medianRenderMs':statistics.median(r['renderMs'] for r in subset),'medianHtmlBytes':statistics.median(r['htmlBytes'] for r in subset),'selectCounts':[r['sqlStatements'].get('SELECT',0) for r in subset],'writeCounts':[sum(r['sqlStatements'].get(k,0) for k in ['INSERT','UPDATE','DELETE','REPLACE']) for r in subset],'externalAttempts':sum(r['externalAttempts'] for r in subset),'statuses':[r['status'] for r in subset]}
     summary.append(item)
    output={'method':'Historical ' + args.baseline + ' templates vs canonical templates, identical current backend and 387-record public cache snapshot. Five alternating warm samples after warming each route with both template sets. Flask request rendering + actual SQLite statement counts; no production latency claim. Outbound sockets prohibited.','summary':summary,'samples':rows}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,indent=2),encoding='utf-8');print(json.dumps(summary))


if __name__ == "__main__":
    main()
