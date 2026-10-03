"""Isolated full-app browser check. Default uses real local HTTP and complete app JS.

--snapshot is a constrained-environment diagnostic: it is NOT an HTTP/E2E pass.
The runner uses a temporary database, synthetic source fixtures and blocked
third-party requests. It cannot certify provider access or video playback.
"""
import os,json,sys,sqlite3,base64,argparse,tempfile,threading,logging,secrets
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--output',default='reports/postmatch_browser')
parser.add_argument('--snapshot',action='store_true')
parser.add_argument('--automation-center',action='store_true')
args=parser.parse_args()
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
temporary=tempfile.TemporaryDirectory(prefix='nemesis-postmatch-qa-')
os.chdir(ROOT)
os.environ.update(DB_PATH=str(Path(temporary.name)/'app.sqlite'),SECRET_KEY=secrets.token_hex(32),AUTOMATION_SECRET=secrets.token_hex(32),
  BACKGROUND_JOBS_ENABLED='false',AUTO_SEND_TELEGRAM_PICKS='false',AUTO_GENERATE_PICKS='false',SCHEDULER_ENABLED='0')
for key in ('THE_ODDS_API_KEY','ODDS_API_KEY','THESPORTSDB_KEY','THESPORTSDB_API_KEY','API_FOOTBALL_KEY','API_FOOTBALL_API_KEY','OPENAI_API_KEY','TELEGRAM_BOT_TOKEN','STRIPE_SECRET_KEY'):os.environ.pop(key,None)
import app
app.app.config.update(TESTING=True)
app.init_db()
from test_postmatch_recovery import MATCH,EVENT,STATS,NOW,factory
from engines.postmatch_store import Store
from engines.postmatch_recovery import tick
with sqlite3.connect(app.DB_PATH) as c:
 cols={r[1] for r in c.execute('PRAGMA table_info(matches)')}
 seed={k:v for k,v in MATCH.items() if k in cols}
 fields=','.join(seed);marks=','.join('?' for _ in seed)
 c.execute(f'INSERT OR REPLACE INTO matches({fields}) VALUES({marks})',tuple(seed.values()))
store=Store(app.DB_PATH);store.configure(enabled=True,sources=['thesportsdb'],daily_limit=60,actor='offline-qa',confirmed=True)
os.environ['THESPORTSDB_KEY']='offline-test-only'
print('RECOVERY',tick(app.DB_PATH,clock=lambda:NOW,source_factory=factory))
os.environ.pop('THESPORTSDB_KEY',None)
with store.connection(True) as c:
 c.execute("UPDATE sportsdb_match_highlights SET rights_status='LICENSED',commercial_use_status='ALLOWED',"
           "rights_verified_at='2026-09-30T22:00:00Z',attribution='Fuente simulada para QA',official_source_verified=0")
from engines.sportsdb_highlights_engine import classify_stored_highlight
with store.connection() as c: print('VIDEO_CLASS',classify_stored_highlight(dict(c.execute('SELECT * FROM sportsdb_match_highlights').fetchone()))['can_embed'])
from tools.run_v929_click_navigation_qa import _signed_sessions
sessions=_signed_sessions(app.app)
from playwright.sync_api import sync_playwright
out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
checks=[]
server=None
if not args.snapshot:
 from werkzeug.serving import make_server
 logging.getLogger('werkzeug').setLevel(logging.ERROR)
 server=make_server('127.0.0.1',0,app.app,threaded=True)
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 base='http://127.0.0.1:'+str(server.server_port)
else:
 base='http://nemesis.test'
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=os.getenv('NEMESIS_QA_CHROMIUM') or pw.chromium.executable_path,headless=True,args=['--no-sandbox'])
 for role in (['admin'] if args.automation_center else ['client_free','client_pro','client_elite','admin']):
  for width in [320,390,1440]:
   client=app.app.test_client();client.set_cookie(sessions['cookie_name'],sessions[role])
   ctx=browser.new_context(viewport={'width':width,'height':900},service_workers='block',locale='es-ES')
   ctx.add_cookies([{'name':sessions['cookie_name'],'value':sessions[role],'url':base}])
   page=ctx.new_page();errors=[];external=[]
   page.on('pageerror',lambda error:errors.append(str(error)[:250]))
   def route_request(route):
    url=urlsplit(route.request.url)
    if url.netloc!=urlsplit(base).netloc:
     external.append(route.request.url);route.abort();return
    if route.request.method!='GET':route.abort();return
    if not args.snapshot: route.continue_();return
    path=url.path+('?' + url.query if url.query else '')
    response=client.get(path)
    headers={k:v for k,v in response.headers.items() if k.lower() not in {'content-length','content-encoding','transfer-encoding','set-cookie'}}
    route.fulfill(status=response.status_code,headers=headers,body=response.get_data())
   ctx.route('**/*',route_request)
   path='/admin/automation-center' if args.automation_center else '/admin/highlights-review' if role=='admin' else '/match/'+MATCH['id']
   if args.snapshot:
    # The fallback deliberately uses an isolated CSS + native-video-controller
    # snapshot. The full application JS/navigation must still pass in CI.
    import re
    response=client.get(path);status=response.status_code
    raw=response.get_data(as_text=True)
    def style_tag(match):
     tag=match.group(0)
     if 'stylesheet' not in tag:return ''
     href=re.search(r'href=[\"\']([^\"\']+)',tag)
     return '<style>'+client.get(urlsplit(href.group(1)).path).get_data(as_text=True)+'</style>' if href else ''
    raw=re.sub(r'<script\b[^>]*>.*?</script>','',raw,flags=re.S|re.I)
    raw=re.sub(r'<link\b[^>]*>',style_tag,raw,flags=re.I)
    raw=raw.replace('</body>','<script>'+(ROOT/'static/postmatch-media.js').read_text()+'</script></body>')
    page.set_content(raw,wait_until='load',timeout=15000)
   else:
    response=page.goto(base+path,wait_until='load',timeout=15000)
    status=response.status
   page.wait_for_timeout(750)
   content=page.locator('body').inner_text()
   if role!='admin':
    assert page.locator('#match-section-video').count()==1
    assert page.get_by_text('Estadísticas recuperadas después del partido · fuentes').count()==1, content[-1800:]
    assert page.locator('#match-section-video iframe').count()==0
    assert not page.locator('[data-video-mount]').is_visible()
    button=page.locator('[data-video-activate]');assert button.count()==1, content[-1800:]
    # Before third-party media action, not one external player request may exist.
    assert not any('youtube' in url or 'vimeo' in url for url in external)
    page.screenshot(path=str(out/f'{role}-{width}-before-play.png'),full_page=True)
    button.click();page.wait_for_timeout(350)
    assert page.locator('#match-section-video iframe').count()==1
    assert page.get_by_role('link',name='Ver en la plataforma original').count()==1
    assert page.locator('[data-video-notice]').inner_text().startswith('La plataforma')
   else:
    if args.automation_center:
     assert page.get_by_text('NeMeSiS Master Automation',exact=True).count()>=1
     for label in ('Sports','Highlights','Postmatch','Delivery / Telegram','Maintenance / Backups'):
      assert page.get_by_text(label,exact=True).count()>=1
     for link in page.locator('.v933-admin-automation a').all():
      href=link.get_attribute('href') or ''
      if href.startswith('/admin/'):
       assert client.get(href.split('#')[0]).status_code==200, href
    else:
     assert page.locator('[data-postmatch-workers]').count()==1
    if not args.automation_center: assert page.get_by_text('Trabajadores pospartido',exact=True).count()==1
   overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth+2')
   print(role,width,status, 'overflow',overflow, 'errors',errors)
   page.screenshot(path=str(out/f'{role}-{width}.png'),full_page=True)
   checks.append({'role':role,'width':width,'status':status,'overflow':overflow,'page_errors':errors,
                  'data':'synthetic_isolated','network':'CSS/controller snapshot only' if args.snapshot else 'local HTTP with complete app JS; external requests blocked','media_verified':False})
   ctx.close()
 browser.close()
(out/'checks.json').write_text(json.dumps({'mode':'snapshot' if args.snapshot else 'full_http','production_playback_verified':False,'checks':checks},indent=2,ensure_ascii=False),encoding='utf-8')
if server: server.shutdown();server.server_close()
temporary.cleanup()
assert all(c['status']==200 and not c['overflow'] and not c['page_errors'] for c in checks)
print('SNAPSHOT_QA_OK' if args.snapshot else 'BROWSER_QA_OK',len(checks))
