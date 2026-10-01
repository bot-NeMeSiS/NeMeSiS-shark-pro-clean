"""Complete HTTP app: automatic feed -> publication -> client, plus admin controls.

Only synthetic metadata/permissions. Loopback is allowed; all remote traffic is
blocked. No snapshot mode or simulated full-HTTP success exists in this runner.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import logging
import os
from pathlib import Path
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
    args=parser.parse_args()
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='nemesis-editor-worker-qa-') as temporary:
        sys.path[:0]=[str(ROOT),str(ROOT/'tests')];os.chdir(ROOT)
        for name in list(os.environ):
            if any(x in name for x in ('API_KEY','BOT_TOKEN','STRIPE_SECRET','PUBLIC_BASE_URL','THESPORTSDB_KEY')):os.environ.pop(name,None)
        os.environ.update(DB_PATH=str(Path(temporary)/'app.sqlite'),SECRET_KEY=secrets.token_hex(32),AUTOMATION_SECRET=secrets.token_hex(32),
            BACKGROUND_JOBS_ENABLED='false',AUTO_SEND_TELEGRAM_PICKS='false',AUTO_GENERATE_PICKS='false',SCHEDULER_ENABLED='0',ENABLE_AUTO_SYNC='0',AUTO_SYNC_ON_STARTUP='0')
        original=socket.socket.connect
        def offline(self,address):
            if isinstance(address,tuple) and address[0] not in {'127.0.0.1','localhost','::1'}:raise AssertionError('External network blocked')
            return original(self,address)
        socket.socket.connect=offline
        import app
        app.app.config.update(TESTING=True);app.init_db()
        from test_postmatch_recovery import MATCH,NOW,factory
        from engines.postmatch_store import Store
        from engines.postmatch_recovery import tick
        from engines import editorial_worker as worker
        from engines.match_news_store import snapshot
        with sqlite3.connect(app.DB_PATH) as c:
            columns={r[1] for r in c.execute('PRAGMA table_info(matches)')}
            row={k:v for k,v in MATCH.items() if k in columns}
            c.execute('INSERT OR REPLACE INTO matches('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')',tuple(row.values()))
        Store(app.DB_PATH).configure(enabled=True,sources=['thesportsdb'],daily_limit=60,actor='synthetic-qa',confirmed=True)
        os.environ['THESPORTSDB_KEY']='synthetic-qa-only';tick(app.DB_PATH,clock=lambda:NOW,source_factory=factory);os.environ.pop('THESPORTSDB_KEY',None)
        with sqlite3.connect(app.DB_PATH) as c:
            c.execute("UPDATE sportsdb_match_highlights SET rights_status='LICENSED',commercial_use_status='ALLOWED',rights_verified_at='2026-09-30T22:00:00Z',attribution='Fuente de vídeo simulada para QA',official_source_verified=0")
        policy=dict(publisher='Medio simulado · QA',feed_url='https://sports.example.com/feed',article_host='sports.example.com',competition=MATCH['competition_name'],
                    evidence_url='https://sports.example.com/qa-terms',basis='Política exclusivamente sintética; no autoriza ninguna fuente real.',confirmed='1',scope_confirmed='1',auto_publish='1',auto_confirmed='1',expires_at='2026-11-01T00:00:00Z')
        worker.add_source(app.DB_PATH,policy,actor='qa',now=NOW)
        worker.configure(app.DB_PATH,{'enabled':'1','daily_limit':'12','confirmed':'1','revision':worker.state(app.DB_PATH,now=NOW)['revision']},actor='qa',now=NOW)
        xml=('<rss><channel>'+''.join(f'<item><title>Equipo Uno y Equipo Dos: noticia de prueba {n}</title><link>https://sports.example.com/qa-{n}</link><pubDate>Wed, 30 Sep 2026 21:00:00 GMT</pubDate></item>' for n in range(3))+'</channel></rss>').encode()
        result=worker.tick(app.DB_PATH,clock=lambda:NOW,fetcher=lambda *a,**k:xml)
        assert result['published']==3 and result['external_calls']==1,result
        assert len(snapshot(app.DB_PATH,MATCH['id'])['items'])==3
        # Freeze only source time/transport for a repeated admin action in this test.
        actual_tick=worker.tick
        worker.tick=lambda path,**kw:actual_tick(path,clock=lambda:NOW+1,fetcher=lambda *a,**k:xml,**kw)
        from tools.run_v929_click_navigation_qa import _signed_sessions
        sessions=_signed_sessions(app.app)
        from werkzeug.serving import make_server
        from playwright.sync_api import sync_playwright
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        server=make_server('127.0.0.1',0,app.app,threaded=True)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{server.server_port}';results=[]
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(executable_path=os.getenv('NEMESIS_QA_CHROMIUM') or pw.chromium.executable_path,headless=True,args=['--no-sandbox'])
                for role in ('client_free','client_pro','client_elite','admin'):
                    for width in (320,390,1440):
                        ctx=browser.new_context(viewport={'width':width,'height':900},service_workers='block',locale='es-ES')
                        ctx.add_cookies([{'name':sessions['cookie_name'],'value':sessions[role],'url':base}])
                        page=ctx.new_page();errors=[];external=[]
                        page.on('pageerror',lambda e:errors.append(str(e)[:200]))
                        def route(r):
                            if urlsplit(r.request.url).netloc!=urlsplit(base).netloc:external.append(r.request.url);r.abort();return
                            r.continue_()
                        ctx.route('**/*',route)
                        path='/admin/highlights-review/news?match_id='+MATCH['id'] if role=='admin' else '/match/'+MATCH['id']
                        response=page.goto(base+path,wait_until='load',timeout=15000)
                        assert response.status==200,(role,width,response.status)
                        page.wait_for_timeout(650)
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(role,width,'overflow')
                        if role=='admin':
                            assert page.locator('[data-editorial-worker]').count()==1
                            assert page.locator('[data-news-review]').count()==3
                            page.get_by_role('button',name='Revisar fuentes pendientes').click()
                            page.wait_for_load_state('load')
                            assert 'No hay fuentes pendientes de revisión.' in page.locator('body').inner_text()
                            assert worker.state(app.DB_PATH,now=NOW)['used']==1  # double action makes no extra request
                            page.screenshot(path=str(out/f'{role}-{width}.png'),full_page=True)
                            panel=page.locator('[data-editorial-worker]')
                            panel.get_by_text('Fuentes y límites',exact=True).click()
                            assert page.get_by_role('button',name='Guardar configuración',exact=True).is_visible()
                            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        else:
                            assert page.locator('#match-section-news [data-match-news]').count()==3
                            assert page.locator('#match-editorial-summary').count()==1
                            assert page.locator('#match-section-video').count()==1
                            assert page.locator('#match-section-video iframe').count()==0
                            assert not any('youtube' in u for u in external)
                            page.screenshot(path=str(out/f'{role}-{width}.png'),full_page=True)
                            page.locator('[data-video-activate]').click()
                            assert page.locator('#match-section-video iframe').count()==1
                        assert not errors,errors
                        results.append({'role':role,'width':width,'mode':'full_http','status':200,'automatic_references':3,'errors':errors,'overflow':False})
                        (out/'results.json').write_text(json.dumps(results,indent=2));print(role,width,'OK',flush=True)
                        ctx.close()
                browser.close()
        finally:
            server.shutdown();socket.socket.connect=original;worker.tick=actual_tick
        (out/'worker-result.json').write_text(json.dumps(result,indent=2))
        assert len(results)==12


if __name__=='__main__':main()
