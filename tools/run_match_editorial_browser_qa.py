"""Synthetic editorial/browser evidence. Default: full app HTTP. --snapshot: CSS diagnostic only.

No real provider, article, account or production storage is used. Snapshot mode
must NOT be reported as a full browser-navigation or production certification.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from itertools import product
import json
import logging
import os
from pathlib import Path
import re
import secrets
import socket
import sqlite3
import sys
import tempfile
import threading
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--snapshot',action='store_true')
    parser.add_argument('--languages',nargs='+',choices=['es','en','fr'],default=['es'])
    parser.add_argument('--roles',nargs='+',choices=['client_free','client_pro','client_elite','admin'],default=['client_free','client_pro','client_elite','admin'])
    args=parser.parse_args()
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    temp=tempfile.TemporaryDirectory(prefix='nemesis-editorial-qa-')
    sys.path[:0]=[str(ROOT),str(ROOT/'tests')];os.chdir(ROOT)
    for name in list(os.environ):
        if any(x in name for x in ('API_KEY','BOT_TOKEN','STRIPE_SECRET','PUBLIC_BASE_URL','THESPORTSDB_KEY')):
            os.environ.pop(name,None)
    os.environ.update(DB_PATH=str(Path(temp.name)/'app.sqlite'),SECRET_KEY=secrets.token_hex(32),AUTOMATION_SECRET=secrets.token_hex(32),
        BACKGROUND_JOBS_ENABLED='false',AUTO_SEND_TELEGRAM_PICKS='false',AUTO_GENERATE_PICKS='false',
        SCHEDULER_ENABLED='0',ENABLE_AUTO_SYNC='0',AUTO_SYNC_ON_STARTUP='0')
    connect=socket.socket.connect
    def offline(self,address):
        if isinstance(address,tuple) and address[0] not in {'127.0.0.1','localhost','::1'}:
            raise AssertionError('External transport forbidden in editorial QA')
        return connect(self,address)
    socket.socket.connect=offline
    import app
    app.app.config.update(TESTING=True);app.init_db()
    from test_postmatch_recovery import MATCH,NOW,factory
    from engines.postmatch_store import Store
    from engines.postmatch_recovery import tick
    from engines.match_news_store import save_draft,decide,snapshot
    with closing(sqlite3.connect(app.DB_PATH)) as c, c:
        cols={r[1] for r in c.execute('PRAGMA table_info(matches)')}
        row={k:v for k,v in MATCH.items() if k in cols}
        c.execute('INSERT OR REPLACE INTO matches('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')',tuple(row.values()))
    Store(app.DB_PATH).configure(enabled=True,sources=['thesportsdb'],daily_limit=60,actor='offline-qa',confirmed=True)
    os.environ['THESPORTSDB_KEY']='offline-fixture-only';tick(app.DB_PATH,clock=lambda:NOW,source_factory=factory)
    os.environ.pop('THESPORTSDB_KEY',None)
    with closing(sqlite3.connect(app.DB_PATH)) as c, c:
        c.execute("UPDATE sportsdb_match_highlights SET rights_status='LICENSED',commercial_use_status='ALLOWED',rights_verified_at='2026-09-30T22:00:00Z',attribution='Fuente de vídeo simulada para QA',official_source_verified=0")
    initial=snapshot(app.DB_PATH,MATCH['id'],admin=True)
    for index,title in enumerate(['Claves y datos del encuentro: referencia de prueba','La jornada, explicada desde los hechos registrados','Reacciones y contexto: ejemplo editorial sin artículo real']):
        fields=dict(identity=initial['identity'],url=f'https://sports.example.com/qa-{index}',title=title,publisher='Medio simulado · QA',
          published_at='2026-09-30T21:00:00+02:00',evidence_url='https://sports.example.com/qa-terms',
          basis='Registro enteramente sintético, no atribuye licencia a ninguna noticia real.',confirmed='1')
        nid=save_draft(app.DB_PATH,MATCH['id'],fields,actor='qa',now=NOW)
        item=next(x for x in snapshot(app.DB_PATH,MATCH['id'],admin=True)['items'] if x['id']==nid)
        decide(app.DB_PATH,MATCH['id'],nid,{'action':'PUBLISH','confirmed':'1','revision':item['revision']},actor='qa',now=NOW+1)
    from tools.run_v929_click_navigation_qa import _signed_sessions
    sessions=_signed_sessions(app.app)
    from playwright.sync_api import sync_playwright
    server=None
    if not args.snapshot:
        from werkzeug.serving import make_server
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        server=make_server('127.0.0.1',0,app.app,threaded=True)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{server.server_port}'
    else:base='http://nemesis.test'
    results=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=os.getenv('NEMESIS_QA_CHROMIUM') or pw.chromium.executable_path,headless=True,args=['--no-sandbox'])
            from engines.ui_localization_engine import translate
            for role,language in product(args.roles,args.languages):
                for width in (320,390,1440):
                    client=app.app.test_client();client.set_cookie(sessions['cookie_name'],sessions[role])
                    ctx=browser.new_context(viewport={'width':width,'height':900},service_workers='block',locale=language,
                                            timezone_id='Asia/Tokyo')
                    ctx.add_cookies([{'name':sessions['cookie_name'],'value':sessions[role],'url':base},
                                     {'name':'nemesis_locale','value':language,'url':base}])
                    client.set_cookie('nemesis_locale',language)
                    page=ctx.new_page();errors=[];external=[]
                    page.on('pageerror',lambda error:errors.append(str(error)[:300]))
                    def route(route):
                        if urlsplit(route.request.url).netloc!=urlsplit(base).netloc:
                            external.append(route.request.url);route.abort();return
                        route.continue_()
                    ctx.route('**/*',route)
                    path='/admin/highlights-review/news?match_id='+MATCH['id'] if role=='admin' else '/match/'+MATCH['id']
                    if args.snapshot:
                        response=client.get(path);status=response.status_code
                        html=response.get_data(as_text=True)
                        def style(m):
                            tag=m.group(0);href=re.search(r'href=["\']([^"\']+)',tag)
                            return '<style>'+client.get(urlsplit(href[1]).path).get_data(as_text=True)+'</style>' if href and 'stylesheet' in tag else ''
                        html=re.sub(r'<script\b[^>]*>.*?</script>','',html,flags=re.S|re.I)
                        html=re.sub(r'<link\b[^>]*>',style,html,flags=re.I)
                        html=html.replace('</body>','<script>'+(ROOT/'static/postmatch-media.js').read_text()+'</script></body>')
                        page.set_content(html,wait_until='load')
                    else:
                        status=page.goto(base+path,wait_until='load',timeout=15000).status
                    assert status==200,(path,status)
                    page.wait_for_timeout(650)
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'),(role,width,'overflow')
                    if role!='admin':
                        assert page.locator('#match-editorial-summary').count()==1
                        assert page.locator('html').get_attribute('lang')==language
                        assert page.locator('#match-editorial-summary').get_by_role('heading',name=translate('Así fue el partido',language)).count()==1
                        assert page.locator('#match-section-news').get_by_role('heading',name=translate('Noticias y crónicas del partido',language)).count()==1
                        assert page.locator('#match-section-video').count()==1
                        assert page.locator('#match-section-news [data-match-news]').count()==3
                        assert page.locator('#match-section-video iframe').count()==0
                        assert not any('youtube' in x or 'vimeo' in x for x in external)
                        assert page.locator('#match-editorial-summary').bounding_box()['y'] < page.locator('[data-match-component="SharkPanel"]').bounding_box()['y']
                        page.screenshot(path=str(out/f'{role}-{language}-{width}.png'),full_page=True)
                        page.locator('[data-video-activate]').click()
                        assert page.locator('#match-section-video iframe').count()==1
                        assert page.get_by_role('link',name=translate('Ver en la plataforma original',language)).count()==1
                        if not args.snapshot:
                            page.reload(wait_until='load')
                            assert page.locator('#match-section-video iframe').count()==0
                            assert page.locator('#match-section-news [data-match-news]').count()==3
                    else:
                        assert page.locator('[data-news-review]').count()==3
                        page.screenshot(path=str(out/f'{role}-{language}-{width}.png'),full_page=True)
                    assert not errors,errors
                    results.append(dict(role=role,language=language,width=width,status=status,mode='snapshot_css_diagnostic' if args.snapshot else 'full_http',errors=errors,overflow=False))
                    (out/'results.json').write_text(json.dumps(results,indent=2))
                    print(role,language,width,'OK',flush=True)
                    ctx.close()
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
        socket.socket.connect=connect
    (out/'results.json').write_text(json.dumps(results,indent=2))
    print('EDITORIAL_QA',len(results),'SNAPSHOT ONLY' if args.snapshot else 'FULL HTTP')
    temp.cleanup()


if __name__=='__main__':main()
