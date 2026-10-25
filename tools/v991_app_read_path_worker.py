"""Fresh-process real-App WSGI evidence worker. No App/RAM/getter replacements."""
from __future__ import annotations
import argparse
from contextlib import closing
from datetime import datetime, timedelta
import hashlib
from html import unescape
import importlib
import inspect
import json
import os
from pathlib import Path
import platform
import re
import sqlite3
import secrets
import sys
import tempfile
import traceback
from urllib.parse import urlparse
from urllib.request import url2pathname
from zoneinfo import ZoneInfo

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    repo, out = args.repo_root.resolve(), args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if out.is_relative_to(repo): raise RuntimeError('Worker output must be outside the product checkout')
    database = out/'application.sqlite'
    if database.exists(): raise RuntimeError('Each worker requires a new output/database')
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo))
    platform.uname(); platform.platform()  # Windows runtime metadata before strict process guard.
    for key in tuple(os.environ):
        if any(part in key.upper() for part in ('TOKEN','SECRET','PASSWORD','API_KEY')): os.environ[key] = ''
    for key in ('API_FOOTBALL_KEY','API_SPORTS_KEY','THE_ODDS_API_KEY','THESPORTSDB_API_KEY','THESPORTSDB_KEY',
                'TELEGRAM_BOT_TOKEN','TELEGRAM_CHAT_ID','STRIPE_SECRET_KEY','STRIPE_PUBLISHABLE_KEY','OPENAI_API_KEY',
                'SMTP_PASSWORD','SMTP_HOST','SMTP_USERNAME','RENDER_API_KEY','RENDER_DEPLOY_HOOK_URL'):
        os.environ[key] = ''
    os.environ.update(DB_PATH=str(database), NEMESIS_LOCAL_SAFE_MODE='0', NEMESIS_LOCAL_MODE='OFFLINE_SAFE', NEMESIS_OFFLINE_MODE='1',
        NEMESIS_LOCAL_EXTERNAL_AUTHORIZED='0', BACKGROUND_JOBS_ENABLED='false', AUTO_GENERATE_PICKS='false', AUTO_SEND_TELEGRAM_PICKS='false',
        RUN_STARTUP_SCHEDULER_NOW='0', SCHEDULER_ENABLED='0', ENABLE_AUTO_SYNC='0', DAILY_AUTOMATION_DRY_RUN='1',
        ENABLE_LIVE_API='0', ENABLE_ODDS_API='0', ENABLE_API_FOOTBALL_PROVIDER='0', ENABLE_API_FOOTBALL_LIVE_TRACKER='0',
        ENABLE_TELEGRAM_AUTO='0', ENABLE_TELEGRAM_AUTOMATION='0', TELEGRAM_AUTO_SEND_ENABLED='0',
        ADMIN_EMAIL='v991-ci-owner@example.invalid', ADMIN_PASSWORD=secrets.token_urlsafe(32), SECRET_KEY=secrets.token_urlsafe(32),
        AUTOMATION_SECRET='', PUBLIC_BASE_URL='http://127.0.0.1', APP_PUBLIC_URL='http://127.0.0.1', SESSION_COOKIE_SECURE='0',
        CONTINUOUS_EVOLUTION_SAFE_MODE='1', CONTINUOUS_EVOLUTION_STORAGE_ROOT=str(out/'continuous'),
        TEMP=str(out), TMP=str(out), TMPDIR=str(out), MPLCONFIGDIR=str(out/'mpl'), NUMBA_CACHE_DIR=str(out/'numba'))
    tempfile.tempdir = str(out)
    boundary = []
    def path_of(raw):
        value = os.fsdecode(raw)
        if value.startswith('file:'):
            parsed = urlparse(value)
            if parsed.netloc not in ('','localhost'): return None
            value = url2pathname(parsed.path)
        return Path(value).resolve()
    def inside(raw):
        value = path_of(raw)
        return value is not None and value.is_relative_to(out)
    def reject(event):
        boundary.append(event); raise PermissionError('V991_APP_WORKER_'+event)
    def audit(event, data):
        if event in {'socket.connect','socket.getaddrinfo','socket.bind'}: reject('NETWORK')
        if event in {'subprocess.Popen','os.system','os.exec','os.spawn','os.posix_spawn'}: reject('PROCESS')
        if event == 'sqlite3.connect' and data[0] != ':memory:' and path_of(data[0]) != database: reject('SQLITE')
        if event == 'open' and isinstance(data[0], (str,bytes)):
            if any(c in (data[1] or '') for c in 'wax+') or (data[2] or 0)&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC):
                if not inside(data[0]): reject('WRITE')
        if event in {'os.mkdir','os.remove','os.rmdir','os.rename'}:
            if event == 'os.mkdir' and Path(os.fsdecode(data[0])).is_dir(): return
            if not inside(data[0]) or (event == 'os.rename' and not inside(data[1])): reject('FS')
    sys.addaudithook(audit)
    source_paths = ('app.py','engines/home_matchday.py','engines/fixture_realtime_projection.py','engines/data_vault_engine.py',
             'engines/canonical_competition_context.py','engines/fixture_identity_read_model.py','engines/fixture_snapshot_read_model.py',
             'templates/home.html','templates/calendar.html','templates/live.html','templates/components/v933_ui.html',
             'static/v934-realtime.js','localization/ui.json','APP_VERSION','VERSION.txt')
    def hashes(): return {name:hashlib.sha256((repo/name).read_bytes()).hexdigest() for name in source_paths}
    before = hashes()
    facts = {'errors':[], 'boundary_events':boundary, 'reference_reads_per_request':[], 'source_hashes_before':before,
             'database_is_external':not database.is_relative_to(repo), 'browser_claimed':False}
    refs = []
    original_connect = sqlite3.connect
    def connect(*a, **kw):
        conn = original_connect(*a, **kw)
        conn.set_trace_callback(lambda sql:refs.append(1) if re.search(r'FROM\s+competitions\s+WHERE\s+key\s+IN',sql,re.I) else None)
        return conn
    sqlite3.connect = connect
    try:
        app = importlib.import_module('app')
        facts['actual_app_file'] = Path(app.__file__).resolve() == repo/'app.py'
        if Path(app.DB_PATH).resolve() != database: raise RuntimeError('App did not bind the exact synthetic database')
        app.app.config.update(TESTING=True)
        app.seed_core()
        facts['version'] = app.APP_VERSION
        facts['blueprints'] = sorted(app.app.blueprints)
        fixture = json.loads((repo/'tests/v991_fixture_identity.json').read_text(encoding='utf-8'))['input']
        def insert(conn, table, row):
            columns = {r[1] for r in conn.execute('PRAGMA table_info("'+table+'")')}
            values = {key:value for key,value in row.items() if key in columns}
            conn.execute('INSERT INTO "'+table+'" ('+','.join('"'+key+'"' for key in values)+') VALUES ('+','.join('?' for _ in values)+')',tuple(values.values()))
        now = datetime.now(ZoneInfo('Europe/Madrid'))
        with closing(sqlite3.connect(database)) as conn, conn:
            conn.execute('DELETE FROM matches'); conn.execute('DELETE FROM picks')
            for role, tier in (('free','FREE'),('pro','PRO'),('elite','ELITE'),('admin','ELITE')):
                insert(conn,'users',{'id':'v991-ci-'+role,'username':'v991-session-'+role,'email':'v991-session-'+role+'@example.invalid',
                    'name':'CI '+role,'password_hash':app.generate_password_hash('synthetic-user-password'),'auth_version':0,
                    'role':role.upper(),'membership':tier,'membership_expires_at':(now+timedelta(days=2)).isoformat(),'created_at':now.isoformat()})
            for row in fixture['catalogue']:
                conn.execute('DELETE FROM competitions WHERE key=?',(row['key'],)); insert(conn,'competitions',row)
        clients = {}
        from flask import session, g, template_rendered, request_finished
        for role in ('anonymous','free','pro','elite','admin'):
            client = app.app.test_client()
            if role != 'anonymous':
                with app.app.test_request_context('/'):
                    app.set_login_session(app.get_user_by_id('v991-ci-'+role)); state = dict(session)
                with client.session_transaction() as target: target.update(state)
            clients[role] = client
        capture, source = [], []
        def rendered(sender, template, context, **kw): capture.append(context.get('data') or {})
        def finished(sender, response, **kw):
            summary = getattr(g,'v935_public_sports_summary',{}) or {}
            source.append({'storage_status':summary.get('storage_status'),'raw_count':summary.get('raw_matches_count')})
        template_rendered.connect(rendered,app.app,weak=False); request_finished.connect(finished,app.app,weak=False)
        facts['fixture_projection_requests'] = []
        def get(role, path, query=None, headers=None):
            capture.clear(); source.clear(); start = len(refs)
            projected = []
            def observe_calls(frame,event,arg):
                if event == 'call' and frame.f_code is app._v991_realtime_projection.__code__:
                    projected.append(1)
            previous_profile = sys.getprofile()
            if previous_profile is not None: raise RuntimeError('Fresh worker unexpectedly has a profiler')
            sys.setprofile(observe_calls)
            try:
                response = clients[role].get(path,query_string=query or {},headers=headers or {},environ_overrides={'REMOTE_ADDR':'127.0.0.1'})
            finally:
                sys.setprofile(previous_profile)
            facts['fixture_projection_requests'].append({'role':role,'path':path,'calls':len(projected)})
            facts['reference_reads_per_request'].append(len(refs)-start)
            return response, capture[-1] if capture else {}, source[-1] if source else {}
        facts['bindings'] = []
        for path in ('/','/app','/calendar','/api/calendar','/directo','/api/realtime/sports'):
            rules = [r for r in app.app.url_map.iter_rules() if r.rule == path and 'GET' in r.methods]
            handler = app.app.view_functions[rules[0].endpoint] if len(rules)==1 else None
            facts['bindings'].append({'path':path,'unique':len(rules)==1,'module':handler.__module__ if handler else None})
        # Cold missing store, same permitted DB_PATH, no deletion or journal-mode change.
        with closing(sqlite3.connect(database)) as conn:
            if conn.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0]: raise RuntimeError('Synthetic WAL is busy')
        original_sha = hashlib.sha256(database.read_bytes()).hexdigest()
        def move_files(prefix, *, ledger=None):
            files = [database,Path(str(database)+'-wal'),Path(str(database)+'-shm'),Path(str(database)+'-journal')]
            moves = [(path,out/(prefix+'-'+path.name)) for path in files if path.exists()]
            if not all(path.resolve().is_relative_to(out) and target.resolve().is_relative_to(out) and not target.exists() for path,target in moves): raise RuntimeError('Unsafe QA file move')
            for path,target in moves:
                path.rename(target)
                if ledger is not None: ledger.append((path,target))
            return moves
        def restore_files(moves):
            failures = []
            for path,backup in reversed(moves):
                try:
                    if not backup.exists(): raise RuntimeError('Missing preserved synthetic file')
                    if path.exists(): raise RuntimeError('Refusing to overwrite a synthetic file')
                    backup.rename(path)
                except (OSError,RuntimeError) as exc:
                    failures.append(path.name+':'+type(exc).__name__)
            if failures: raise RuntimeError('Synthetic restore incomplete: '+','.join(failures))
        def metadata_fact(response, source, consumer):
            body = response.get_json() or {}
            meta = body.get('fixture_identity' if consumer=='directo-v2' else 'fixture_metrics') or {}
            return {'storage_status':source.get('storage_status'),'state':meta.get('state'),
                'snapshot_state':body.get('source_snapshot_state'),'counts':meta.get('counts',(meta.get('general') or {}).get('counts')),
                'etag':response.headers.get('ETag')}
        from engines.ui_localization_engine import translate
        def html_fact(response, read, language):
            html = response.get_data(as_text=True)
            without_scripts = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', html, flags=re.S|re.I)
            visible_text = unescape(re.sub(r'<[^>]+>', ' ', without_scripts))
            notices = re.findall(r'<p\b([^>]*\bdata-directo-notice[^>]*)>(.*?)</p>',html,re.S|re.I)
            title = translate('Datos no disponibles temporalmente',language)
            notice = translate('No se ha podido leer la información de partidos. Vuelve a intentarlo más tarde.',language)
            empty = translate('No hay partidos para este estado',language)
            return {'http':response.status_code,'storage_status':read.get('storage_status'),
                'notice_visible':bool(notices) and not bool(re.search(r'\bhidden(?:\s|=|$)',notices[0][0])),
                'expected_title_present':title in visible_text,'expected_notice_present':notice in visible_text,
                'confirmed_empty_title_present':empty in visible_text}
        moves = []; originals_moved = False; facts['missing'] = {}; facts['missing_html'] = {}
        try:
            move_files('original',ledger=moves)
            originals_moved = True
            for index,consumer in enumerate(('directo-v2','fixture-metrics-v1')):
                response,_,read = get('anonymous','/api/realtime/sports',{'scope':'matches','consumer':consumer})
                facts['missing'][consumer] = metadata_fact(response,read,consumer)
                move_files('auto-created-'+str(index))  # Preserve unexpected auto-init files, never erase them.
            for language in ('es','en','fr'):
                response,_,read = get('anonymous','/live',headers={'Accept-Language':language})
                facts['missing_html'][language] = html_fact(response,read,language)
                move_files('auto-created-html-'+language)
        finally:
            try:
                if originals_moved and database.exists(): move_files('auto-created-final')
            finally:
                restore_files(moves)
        facts['original_database_restored'] = hashlib.sha256(database.read_bytes()).hexdigest()==original_sha
        from engines.v934_realtime_sports_engine import invalidate_realtime_cache
        invalidate_realtime_cache(); facts['empty'] = {}; facts['empty_html'] = {}
        for consumer in ('directo-v2','fixture-metrics-v1'):
            query = {'scope':'matches','consumer':consumer}
            response,_,read = get('anonymous','/api/realtime/sports',query)
            facts['empty'][consumer] = metadata_fact(response,read,consumer)
            conditional,_,_ = get('anonymous','/api/realtime/sports',query,{'If-None-Match':facts['missing'][consumer]['etag']})
            facts['empty'][consumer]['conditional_old_missing_http'] = conditional.status_code
        for language in ('es','en','fr'):
            response,_,read = get('anonymous','/live',headers={'Accept-Language':language})
            facts['empty_html'][language] = html_fact(response,read,language)
        # LIVE at the current minute is date-stable even around local midnight.
        now = datetime.now(ZoneInfo('Europe/Madrid')); kickoff = now.replace(second=0,microsecond=0)
        rows = fixture['rows']
        for row in rows:
            row.update(match_date=kickoff.date().isoformat(),kickoff_iso=kickoff.isoformat(),kickoff_time=kickoff.strftime('%H:%M'),
                match_time=kickoff.strftime('%H:%M'),status='LIVE',minute=1,home_score=1,away_score=0,updated_at=now.isoformat(),last_synced_at=now.isoformat())
            raw = json.loads(row['raw_json'])
            if row['source']=='api_football_live':
                raw['fixture'].update(date=kickoff.isoformat(),status={'short':'1H','elapsed':1}); raw['goals']={'home':1,'away':0}
            else: raw.update(strTimestamp=kickoff.isoformat(),strStatus='1H',intMinute='1',intHomeScore='1',intAwayScore='0')
            row['raw_json'] = json.dumps(raw)
        with closing(sqlite3.connect(database)) as conn, conn:
            for row in rows: insert(conn,'matches',row)
            for index,tier,odds in ((1,'PRO',1.83),(2,'ELITE',2.14)):
                row = rows[index-1]
                insert(conn,'picks',{'id':'v991-ci-pick-'+str(index),'match_id':row['id'],'home_team':row['home_team'],'away_team':row['away_team'],
                    'competition_name':row['competition_name'],'match_date':row['match_date'],'kickoff_iso':row['kickoff_iso'],'match_time':row['match_time'],
                    'market':'1x2','pick_type':'1x2','selection':'1','odds':odds,'bookmaker':'Casa de pruebas','status':'published',
                    'membership_required':tier,'match_status':'LIVE','source':'The Odds API','created_at':now.isoformat(),'updated_at':now.isoformat(),
                    'raw_json':json.dumps({'odds_updated_at':now.isoformat(),'synthetic_fixture':True})})
        invalidate_realtime_cache(); facts['roles'] = {}
        for role in clients:
            home,data,read = get(role,'/')
            live = data.get('home_matchday',{}).get('live',{})
            ids = [str(row['id']) for group in live.get('groups',[]) for row in group['matches']]
            app_response,_,_ = get(role,'/app')
            facts['roles'][role] = {'home_http':home.status_code,'app_http':app_response.status_code,'raw_count':read.get('raw_count'),
                'today_count':(data.get('sports_metrics') or {}).get('matches_today'),'home_live_ids':ids}
            if role == 'elite': facts['publishable_pick_ids'] = sorted(row['id'] for row in data.get('picks',[]))
        response,_,read = get('anonymous','/api/calendar',{'lane':'today','date':now.date().isoformat()})
        body = response.get_json(); calendar = body.get('calendar') or {}
        facts['calendar'] = {'http':response.status_code,'ids':[row['id'] for row in body.get('matches',[])],
            'today_count':calendar.get('sports_metrics',{}).get('matches_today'),'raw_count':read.get('raw_count')}
        html_calendar,calendar_data,_ = get('anonymous','/calendario',{'lane':'today','date':now.date().isoformat()})
        facts['calendar_html'] = {'http':html_calendar.status_code,
            'ids':[row['id'] for row in (calendar_data.get('calendar') or {}).get('matches',[])],
            'count':(calendar_data.get('calendar') or {}).get('sports_metrics',{}).get('matches_today')}
        facts['live'] = {}
        for route in ('/live','/directo','/en-directo'):
            response,_,_ = get('anonymous',route,{'f':'live'})
            html = response.get_data(as_text=True)
            blocks = re.findall(r'<script\b(?=[^>]*\bdata-directo-fixture-identity\b)[^>]*>(.*?)</script>',html,re.S)
            bootstrap = json.loads(blocks[0]) if len(blocks)==1 else {}
            identity = bootstrap.get('fixture_identity') or {}; general = identity.get('general') or {}; view = identity.get('view') or {}
            facts['live'][route] = {'http':response.status_code,'bootstrap_count':len(blocks),
                'member_ids':sorted(row['id'] for row in general.get('members',[])),'emitted_ids':sorted(row['id'] for row in bootstrap.get('matches',[])),
                'groups':{row['id']:row['group'] for row in general.get('members',[])},'live_count':general.get('counts',{}).get('live'),
                'view_count':view.get('groups_before_limit'),'rendered_ids':re.findall(r'<article\b[^>]*\bdata-v934-match-id="([^"]+)"',html)}
        def clocks(body):
            return {row['id']:{key:row.get('realtime_state',{}).get(key) for key in ('provider_observed_at','live_valid_until_madrid','score_home','score_away','minute')}
                    for row in body.get('matches',[])}
        query = {'scope':'matches','consumer':'directo-v2','lane':'live'}
        first,_,_ = get('anonymous','/api/realtime/sports',query)
        conditional,_,_ = get('anonymous','/api/realtime/sports',query,{'If-None-Match':first.headers.get('ETag')})
        last,_,_ = get('anonymous','/api/realtime/sports',query)
        facts['live_poll'] = {'http':[first.status_code,conditional.status_code,last.status_code],'conditional_bytes':len(conditional.get_data()),
            'first_etag':first.headers.get('ETag'),'last_etag':last.headers.get('ETag'),
            'first_clocks':clocks(first.get_json()),'last_clocks':clocks(last.get_json()),'first_ids':sorted(row['id'] for row in first.get_json().get('matches',[]))}
        facts['retention'] = []
        keys = ('id','match_id','market','selection','odds','source','bookmaker','membership_required')
        for role in clients:
            for scope in ('all','picks','odds'):
                old,_,_ = get(role,'/api/realtime/sports',{'scope':scope})
                new,_,_ = get(role,'/api/realtime/sports',{'scope':scope,'consumer':'fixture-metrics-v1'})
                def financial(response): return sorted([{key:row.get(key) for key in keys} for row in response.get_json().get('picks',[])],key=lambda row:str(row['id']))
                facts['retention'].append({'role':role,'scope':scope,'http':[old.status_code,new.status_code],'legacy':financial(old),'modern':financial(new)})
    except BaseException as exc:
        facts['errors'].append({'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()})
    finally:
        after = hashes(); facts.update(source_hashes_after=after,sources_unchanged=before==after)
        (out/'receipt.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 1 if facts['errors'] or boundary or not facts['sources_unchanged'] else 0

if __name__ == '__main__': raise SystemExit(main())
