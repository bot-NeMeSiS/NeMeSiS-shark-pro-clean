"""Source-level editorial queue, consumed by the existing postmatch Cron.

Only admin-approved RSS/Atom policies. Default off. A feed is fetched once per
batch, not per fixture. All writes are fenced, budgeted, and audited. No AI calls.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import secrets
import sqlite3
import time
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from engines.match_news_store import connection, safe_url, clean, NewsError, SCHEMA as NEWS_SCHEMA
from engines.postmatch_store import identity
from engines.editorial_feed_reader import https_feed, parse_feed, match_article, FeedError, RULE

SCHEMA = '''
CREATE TABLE IF NOT EXISTS editorial_settings (
 id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL DEFAULT 0,
 daily_limit INTEGER NOT NULL DEFAULT 12, revision TEXT NOT NULL,
 lease_token TEXT, lease_until REAL NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS editorial_sources (
 id INTEGER PRIMARY KEY, publisher TEXT NOT NULL, feed_url TEXT NOT NULL UNIQUE,
 article_host TEXT NOT NULL, competition TEXT NOT NULL, evidence_url TEXT NOT NULL,
 basis TEXT NOT NULL, expires_at REAL NOT NULL, auto_publish INTEGER NOT NULL,
 enabled INTEGER NOT NULL DEFAULT 1, revoked INTEGER NOT NULL DEFAULT 0,
 revision TEXT NOT NULL, reviewed_by TEXT NOT NULL, due_at REAL NOT NULL,
 last_attempt REAL, last_success REAL, failures INTEGER NOT NULL DEFAULT 0,
 last_result TEXT NOT NULL DEFAULT 'NEVER_RUN');
CREATE TABLE IF NOT EXISTS editorial_budget (
 day TEXT PRIMARY KEY, used INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS editorial_inbox (
 id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL, url TEXT NOT NULL,
 source_title TEXT NOT NULL, published_at TEXT NOT NULL, digest TEXT NOT NULL,
 state TEXT NOT NULL, match_id TEXT, news_id INTEGER, updated_at REAL NOT NULL,
 UNIQUE(source_id,url));
CREATE TABLE IF NOT EXISTS editorial_reference_sources (
 news_id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL, rule TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS editorial_audit (
 id INTEGER PRIMARY KEY, action TEXT NOT NULL, actor TEXT NOT NULL,
 detail TEXT NOT NULL, created_at REAL NOT NULL);
'''


class LostLease(RuntimeError):
    pass


def audit(conn, action, actor, data, now):
    conn.execute('INSERT INTO editorial_audit(action,actor,detail,created_at) VALUES(?,?,?,?)',
                 (action, actor, json.dumps(data, ensure_ascii=False, sort_keys=True), now))


def _schema(conn):
    for statement in (NEWS_SCHEMA + SCHEMA).split(';'):
        if statement.strip(): conn.execute(statement)
    conn.execute('INSERT OR IGNORE INTO editorial_settings(id,revision) VALUES(1,?)', (secrets.token_hex(16),))


def state(path, *, now=None):
    now = time.time() if now is None else now
    result = {'state':'NOT_INITIALIZED','enabled':False,'daily_limit':12,'used':0,
              'sources':[],'inbox':[],'running':False,'revision':'','external_calls':0}
    try:
        with connection(path) as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='editorial_settings'").fetchone(): return result
            cfg = conn.execute('SELECT * FROM editorial_settings WHERE id=1').fetchone()
            if not cfg: return {**result,'state':'READ_UNAVAILABLE'}
            result.update(state='VERIFIED', enabled=bool(cfg['enabled']), daily_limit=cfg['daily_limit'],
                          revision=cfg['revision'], running=cfg['lease_until']>now)
            day = datetime.fromtimestamp(now, ZoneInfo('Europe/Madrid')).date().isoformat()
            budget = conn.execute('SELECT used FROM editorial_budget WHERE day=?',(day,)).fetchone()
            result['used'] = budget[0] if budget else 0
            result['sources'] = [dict(r) for r in conn.execute('SELECT id,publisher,feed_url,article_host,competition,evidence_url,basis,expires_at,auto_publish,enabled,revoked,revision,due_at,last_attempt,last_success,failures,last_result FROM editorial_sources ORDER BY revoked,id DESC LIMIT 10')]
            for source in result['sources']:
                source['policy_valid'] = not source['revoked'] and source['expires_at'] > now
            result['inbox'] = [dict(r) for r in conn.execute("SELECT i.id,i.source_id,s.publisher,i.url,i.source_title,i.published_at,i.state,i.match_id,i.news_id FROM editorial_inbox i JOIN editorial_sources s ON s.id=i.source_id WHERE i.state IN ('UNMATCHED','AMBIGUOUS','SOURCE_CHANGED','DRAFT') ORDER BY i.updated_at DESC LIMIT 20")]
    except (sqlite3.Error, OSError, ValueError):
        return {**result, 'state':'READ_UNAVAILABLE','enabled':False,'sources':[],'inbox':[],'used':None}
    return result


def add_source(path, data, *, actor, now=None):
    now = time.time() if now is None else now
    if not actor or data.get('confirmed') != '1' or data.get('scope_confirmed') != '1':
        raise NewsError('Confirma el uso permitido del feed y su ámbito de competición.')
    feed = safe_url(data.get('feed_url'))
    host = urlsplit(safe_url('https://' + str(data.get('article_host') or '').strip() + '/')).hostname
    if host != str(data.get('article_host') or '').strip().lower():
        raise NewsError('Indica solo el dominio exacto del medio, sin rutas ni parámetros.')
    publisher = clean(data.get('publisher'),100,'medio')
    comp = clean(data.get('competition'),100,'competición canónica')
    basis = clean(data.get('basis'),1200,'condiciones de reutilización')
    evidence = safe_url(data.get('evidence_url'))
    try:
        expiry = datetime.fromisoformat(str(data.get('expires_at','')).replace('Z','+00:00'))
        if not expiry.tzinfo or not now < expiry.timestamp() <= now + 180*86400: raise ValueError()
    except (ValueError, TypeError, OverflowError):
        raise NewsError('La revisión debe caducar dentro de 180 días e incluir zona horaria.') from None
    auto = data.get('auto_publish') == '1'
    if auto and data.get('auto_confirmed') != '1':
        raise NewsError('Confirma la publicación por la regla de equipos, competición y fecha.')
    with connection(path, True) as conn:
        # Never creates a new database or replaces the application's schema.
        conn.execute('SELECT id FROM matches LIMIT 1')
        _schema(conn)
        if conn.execute('SELECT COUNT(*) FROM editorial_sources WHERE revoked=0').fetchone()[0] >= 5:
            raise NewsError('El editor admite hasta cinco fuentes vigentes.')
        try:
            cur = conn.execute('INSERT INTO editorial_sources(publisher,feed_url,article_host,competition,evidence_url,basis,expires_at,auto_publish,revision,reviewed_by,due_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (publisher,feed,host,comp,evidence,basis,expiry.timestamp(),int(auto),secrets.token_hex(16),str(actor)[:120],now))
        except sqlite3.IntegrityError:
            raise NewsError('Este feed ya está registrado. Revisa la fuente existente.') from None
        audit(conn,'SOURCE_APPROVED',str(actor)[:120],{'source_id':cur.lastrowid,'scope':comp,'auto_publish':auto,'expires_at':expiry.timestamp(),'rule':RULE},now)
        return cur.lastrowid


def configure(path, data, *, actor, now=None):
    now = time.time() if now is None else now
    if not actor: raise NewsError('Falta la identidad administrativa.')
    enabled = data.get('enabled') == '1'
    try:
        limit = int(data.get('daily_limit',12))
        if not 1 <= limit <= 60: raise ValueError()
    except (ValueError,TypeError): raise NewsError('El límite debe estar entre 1 y 60 consultas diarias.') from None
    with connection(path,True) as conn:
        cfg = conn.execute('SELECT * FROM editorial_settings WHERE id=1').fetchone()
        if not cfg or data.get('revision') != cfg['revision']: raise NewsError('La configuración cambió. Recarga la página.')
        if enabled:
            if data.get('confirmed') != '1': raise NewsError('Confirma el alcance y el límite antes de activar.')
            if not conn.execute('SELECT 1 FROM editorial_sources WHERE enabled=1 AND revoked=0 AND expires_at>?',(now,)).fetchone():
                raise NewsError('No hay una fuente habilitada con revisión vigente.')
        conn.execute('UPDATE editorial_settings SET enabled=?,daily_limit=?,revision=?,lease_token=NULL,lease_until=0 WHERE id=1',
                     (int(enabled),limit,secrets.token_hex(16)))
        audit(conn,'CONFIGURED',str(actor)[:120],{'enabled':enabled,'daily_limit':limit},now)


def source_action(path, source_id, data, *, actor, now=None):
    now = time.time() if now is None else now
    action = data.get('action')
    if not actor or action not in {'PAUSE','RESUME','RECHECK','REVOKE','RENEW'} or data.get('confirmed') != '1':
        raise NewsError('Confirma una acción válida sobre la fuente.')
    with connection(path,True) as conn:
        source = conn.execute('SELECT * FROM editorial_sources WHERE id=?',(source_id,)).fetchone()
        if not source or source['revision'] != data.get('revision'): raise NewsError('La fuente ha cambiado. Recarga la página.')
        if action in {'RESUME','RECHECK'} and (source['revoked'] or source['expires_at'] <= now):
            raise NewsError('La autorización está retirada o caducada; requiere nueva revisión.')
        if action == 'RECHECK' and source['last_attempt'] is not None and now-source['last_attempt'] < 300:
            raise NewsError('Ya se revisó esta fuente recientemente. Se mantiene el límite de consultas.')
        if action == 'RECHECK' and not source['enabled']:
            raise NewsError('Reanuda la fuente antes de programar una revisión.')
        if action == 'RENEW':
            if source['revoked']: raise NewsError('Una autorización retirada no se renueva automáticamente.')
            try:
                expires = datetime.fromisoformat(str(data.get('expires_at','')).replace('Z','+00:00'))
                if not expires.tzinfo or not now < expires.timestamp() <= now + 180*86400: raise ValueError()
            except (ValueError,TypeError,OverflowError): raise NewsError('Indica una fecha de revisión válida con zona horaria.') from None
            conn.execute('UPDATE editorial_sources SET expires_at=?,reviewed_by=? WHERE id=?',(expires.timestamp(),str(actor)[:120],source_id))
        enabled = source['enabled'] if action == 'RENEW' else 0 if action in {'PAUSE','REVOKE'} else 1
        revoked = 1 if action == 'REVOKE' else source['revoked']
        conn.execute('UPDATE editorial_sources SET enabled=?,revoked=?,revision=?,due_at=? WHERE id=?',
                     (enabled,revoked,secrets.token_hex(16),now,source_id))
        # Invalidates any in-flight result, including one from another web process.
        conn.execute('UPDATE editorial_settings SET revision=?,lease_token=NULL,lease_until=0 WHERE id=1',(secrets.token_hex(16),))
        audit(conn,'SOURCE_'+action,str(actor)[:120],{'source_id':source_id},now)


def claim(path, now):
    with connection(path,True) as conn:
        cfg = conn.execute('SELECT * FROM editorial_settings WHERE id=1').fetchone()
        if not cfg or not cfg['enabled']: return None, 'PAUSED'
        if cfg['lease_until'] > now: return None, 'RUNNING'
        source = conn.execute('SELECT * FROM editorial_sources WHERE enabled=1 AND revoked=0 AND expires_at>? AND due_at<=? ORDER BY due_at,id LIMIT 1',(now,now)).fetchone()
        if not source: return None, 'IDLE'
        day = datetime.fromtimestamp(now,ZoneInfo('Europe/Madrid')).date().isoformat()
        budget = conn.execute('SELECT used FROM editorial_budget WHERE day=?',(day,)).fetchone()
        if budget and budget[0] >= cfg['daily_limit']: return None, 'DAILY_BUDGET'
        # Reservation is not refunded after a crash or uncertain network outcome.
        conn.execute('INSERT INTO editorial_budget VALUES(?,1) ON CONFLICT(day) DO UPDATE SET used=used+1',(day,))
        token = secrets.token_hex(16)
        conn.execute('UPDATE editorial_settings SET lease_token=?,lease_until=? WHERE id=1',(token,now+60))
        conn.execute("UPDATE editorial_sources SET last_attempt=?,last_result='RUNNING' WHERE id=?",(now,source['id']))
        audit(conn,'CLAIM','editorial-worker',{'source_id':source['id'],'budget_day':day},now)
        return {**dict(source),'token':token,'config_revision':cfg['revision']}, 'RUNNING'


def _fence(conn, job, now):
    cfg = conn.execute('SELECT * FROM editorial_settings WHERE id=1').fetchone()
    source = conn.execute('SELECT * FROM editorial_sources WHERE id=?',(job['id'],)).fetchone()
    if (not cfg or not source or not cfg['enabled'] or cfg['revision']!=job['config_revision'] or
        cfg['lease_token']!=job['token'] or cfg['lease_until']<=now or not source['enabled'] or
        source['revoked'] or source['expires_at']<=now or source['revision']!=job['revision']):
        raise LostLease()


def finish(path, job, items, *, now, error='', rejected=0):
    counts = {'found':len(items),'published':0,'drafts':0,'ambiguous':0,'unmatched':0,'unchanged':0,'changed':0,'rejected':rejected}
    with connection(path,True) as conn:
        _fence(conn,job,now)
        if not error:
            day = datetime.fromtimestamp(now-7*86400,ZoneInfo('Europe/Madrid')).date().isoformat()
            today = datetime.fromtimestamp(now,ZoneInfo('Europe/Madrid')).date().isoformat()
            matches = [dict(r) for r in conn.execute('SELECT * FROM matches WHERE substr(match_date,1,10) BETWEEN ? AND ? ORDER BY match_date DESC,id LIMIT 501',(day,today))]
            # Fail closed instead of claiming uniqueness from an incomplete candidate set.
            if len(matches)>500: error='MATCH_WINDOW_TOO_LARGE'
        if not error:
            for item in items:
                match, result = match_article(item,matches,job,now)
                old = conn.execute('SELECT * FROM editorial_inbox WHERE source_id=? AND url=?',(job['id'],item['url'])).fetchone()
                digest = hashlib.sha256(json.dumps(item,sort_keys=True).encode()).hexdigest()
                news_id = old['news_id'] if old else None
                existing = conn.execute('SELECT * FROM match_news_references WHERE id=?',(news_id,)).fetchone() if news_id else None
                origin = conn.execute('SELECT source_id FROM editorial_reference_sources WHERE news_id=?',(news_id,)).fetchone() if news_id else None
                if existing and (not origin or origin[0] != job['id']):
                    # Another feed cannot demote or assume ownership of this reference.
                    result='EXISTING';counts['unchanged']+=1
                elif existing:
                    changed = not match or existing['match_identity']!=identity(match) or (old and old['digest']!=digest)
                    if changed:
                        result='SOURCE_CHANGED'; counts['changed']+=1
                        # Do not overwrite an explicit human edit or resurrect a withdrawal.
                        if existing['reviewed_by']=='editorial-worker' and existing['state']=='PUBLISHED':
                            conn.execute("UPDATE match_news_references SET state='DRAFT',revision=?,updated_at=? WHERE id=?",(secrets.token_hex(16),now,news_id))
                            conn.execute('INSERT INTO match_news_audit(news_id,action,actor,snapshot,created_at) VALUES(?,?,?,?,?)',(news_id,'SOURCE_CHANGED','editorial-worker',json.dumps(dict(existing)),now))
                    else:
                        result=existing['state'];counts['unchanged']+=1
                elif match:
                    mid, ident = str(match['id']),identity(match)
                    duplicate=conn.execute('SELECT id FROM match_news_references WHERE match_id=? AND match_identity=? AND url=?',(mid,ident,item['url'])).fetchone()
                    if duplicate:
                        news_id=duplicate['id'];result='EXISTING';counts['unchanged']+=1
                    else:
                        result='PUBLISHED' if job['auto_publish'] else 'DRAFT'
                        title=f"{match['home_team']} — {match['away_team']}: información en {job['publisher']}"[:180]
                        basis=f"Política de fuente revisada por {job['reviewed_by']}. {job['basis']}"[:1200]
                        cur=conn.execute('INSERT INTO match_news_references(match_id,match_identity,url,title,publisher,published_at,evidence_url,basis,state,revision,reviewed_by,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                            (mid,ident,item['url'],title,job['publisher'],item['published_at'],job['evidence_url'],basis,result,secrets.token_hex(16),'editorial-worker',now))
                        news_id=cur.lastrowid
                        conn.execute('INSERT INTO editorial_reference_sources VALUES(?,?,?)',(news_id,job['id'],RULE))
                        conn.execute('INSERT INTO match_news_audit(news_id,action,actor,snapshot,created_at) VALUES(?,?,?,?,?)',(news_id,result,'editorial-worker',json.dumps({'source_id':job['id'],'policy_revision':job['revision'],'identity':ident,'rule':RULE,'digest':digest}),now))
                        counts['published' if result=='PUBLISHED' else 'drafts']+=1
                else: counts['ambiguous' if result=='AMBIGUOUS' else 'unmatched']+=1
                # Original titles remain admin-only metadata under the approved feed policy.
                conn.execute('INSERT INTO editorial_inbox(source_id,url,source_title,published_at,digest,state,match_id,news_id,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(source_id,url) DO UPDATE SET source_title=excluded.source_title,published_at=excluded.published_at,digest=excluded.digest,state=excluded.state,match_id=excluded.match_id,news_id=excluded.news_id,updated_at=excluded.updated_at',
                    (job['id'],item['url'],item['title'],item['published_at'],digest,result,str(match['id']) if match else None,news_id,now))
        failures=job['failures']+1 if error else 0
        delay=(1800,7200,43200)[min(failures-1,2)] if error else 7200
        reason=error or ('REFERENCES_UPDATED' if counts['published'] or counts['drafts'] else 'NO_NEW_REFERENCES')
        conn.execute('UPDATE editorial_sources SET due_at=?,last_success=CASE WHEN ? THEN last_success ELSE ? END,failures=?,last_result=? WHERE id=?',
                     (now+delay,bool(error),now,failures,reason,job['id']))
        conn.execute('UPDATE editorial_settings SET lease_token=NULL,lease_until=0 WHERE id=1')
        audit(conn,'FINISH','editorial-worker',{'source_id':job['id'],'result':reason,**counts},now)
    return {'ok':not bool(error),'result':reason,'source_id':job['id'],'external_calls':1,**counts}


def tick(path, *, dry_run=False, deadline=None, fetcher=https_feed, clock=time.time, monotonic=time.monotonic):
    began=monotonic(); deadline=min(deadline if deadline is not None else began+8,began+8)
    snap=state(path,now=clock())
    if snap['state']=='READ_UNAVAILABLE': return {'ok':False,'result':'STORAGE_UNAVAILABLE','external_calls':0}
    if dry_run: return {'ok':True,'result':'DRY_RUN','external_calls':0,'database_writes':0}
    if not snap['enabled']: return {'ok':True,'result':'PAUSED','external_calls':0,'database_writes':0}
    if deadline-monotonic()<1: return {'ok':True,'result':'TIME_BUDGET','external_calls':0}
    job=None
    try:
        job,reason=claim(path,clock())
        if not job: return {'ok':True,'result':reason,'external_calls':0}
        raw=fetcher(job['feed_url'],deadline=deadline,monotonic=monotonic)
        items,rejected=parse_feed(raw,feed_url=job['feed_url'],article_host=job['article_host'],now=clock())
        if monotonic()>deadline: raise FeedError('TIME_BUDGET')
        return finish(path,job,items,now=clock(),rejected=rejected)
    except LostLease:
        return {'ok':False,'result':'STALE_EXECUTION','external_calls':1 if job else 0}
    except FeedError as exc:
        reason=str(exc) if str(exc) in {'TIME_BUDGET','UNSAFE_DNS','REDIRECT_REVIEW','ACCESS_DENIED','RATE_LIMIT','SOURCE_UNAVAILABLE','ENCODING_UNSUPPORTED','RESPONSE_TOO_LARGE','NETWORK_OR_TLS','UNSAFE_XML','FEED_TOO_COMPLEX','UNSUPPORTED_FEED','MALFORMED_FEED'} else 'SOURCE_UNAVAILABLE'
        try: return finish(path,job,[],now=clock(),error=reason) if job else {'ok':False,'result':reason,'external_calls':0}
        except (LostLease,sqlite3.Error,OSError): return {'ok':False,'result':'STALE_EXECUTION','external_calls':1}
    except (sqlite3.Error,OSError,ValueError,TypeError):
        # Keep the lease after storage failure: another process may recover after expiry.
        return {'ok':False,'result':'STORAGE_OR_PROCESSING_ERROR','external_calls':1 if job else 0}
