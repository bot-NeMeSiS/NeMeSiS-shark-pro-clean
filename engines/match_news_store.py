"""Reviewed news references per exact persisted fixture. No scraping or article copy.

Reads do not initialize the database. Mutations require an authenticated actor,
explicit source/fixture review and optimistic version checks. Retracted content
and old identities stay in the audit trail but are never selected for clients.
"""
from __future__ import annotations
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sqlite3
import time
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from engines.postmatch_store import identity

SCHEMA = '''
CREATE TABLE IF NOT EXISTS match_news_references (
 id INTEGER PRIMARY KEY, match_id TEXT NOT NULL, match_identity TEXT NOT NULL,
 url TEXT NOT NULL, title TEXT NOT NULL, publisher TEXT NOT NULL,
 published_at TEXT NOT NULL, evidence_url TEXT NOT NULL, basis TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('DRAFT','PUBLISHED','RETRACTED')),
 revision TEXT NOT NULL, reviewed_by TEXT NOT NULL, updated_at REAL NOT NULL,
 UNIQUE(match_id,match_identity,url));
CREATE INDEX IF NOT EXISTS match_news_lookup ON match_news_references(match_id,match_identity,state,published_at);
CREATE TABLE IF NOT EXISTS match_news_audit (
 id INTEGER PRIMARY KEY, news_id INTEGER NOT NULL, action TEXT NOT NULL,
 actor TEXT NOT NULL, snapshot TEXT NOT NULL, created_at REAL NOT NULL);
'''


class NewsError(ValueError):
    pass


def safe_url(value):
    raw = str(value or '').strip()
    if len(raw) > 2048 or not raw or re.search(r'[\s\\\x00-\x1f\x7f]', raw):
        raise NewsError('La dirección debe ser un enlace HTTPS público válido.')
    try:
        p = urlsplit(raw)
        host = (p.hostname or '').encode('idna').decode('ascii').lower()
        if p.scheme != 'https' or p.username or p.password or p.port or not host or host.endswith('.'):
            raise ValueError()
        if '.' not in host or host.endswith(('.localhost','.local','.internal','.test','.invalid')):
            raise ValueError()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError()
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', host):
            raise ValueError()
        if not re.fullmatch(r'(?:[a-z]{2,63}|xn--[a-z0-9-]{2,59})', host.rsplit('.',1)[-1]):
            raise ValueError()  # Reject legacy numeric/hexadecimal IPv4 spellings too.
        parts = parse_qsl(p.query, keep_blank_values=True)
        if any(k.lower() in {'token','secret','password','api_key','apikey','access_token','auth','key'} for k,_ in parts):
            raise ValueError()
        query = urlencode([(k,v) for k,v in parts if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid'}])
        return urlunsplit(('https',host,p.path or '/',query,''))
    except (ValueError, UnicodeError):
        raise NewsError('No se admiten credenciales, direcciones internas o enlaces no seguros.') from None


def clean(value, limit, label):
    value = str(value or '').strip()
    if not value or len(value) > limit or any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise NewsError(f'Revisa el campo {label}.')
    return value


@contextmanager
def connection(path, write=False):
    uri = Path(path).expanduser().resolve().as_uri() + ('?mode=rw' if write else '?mode=ro')
    with closing(sqlite3.connect(uri, uri=True, timeout=.6)) as conn:
        conn.row_factory = sqlite3.Row
        if not write:
            conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        try:
            yield conn
            if write: conn.commit()
        except BaseException:
            conn.rollback()
            raise


def snapshot(path, match_id='', *, admin=False):
    result = {'state':'NOT_INITIALIZED','match':{},'identity':'','items':[],'matches':[],'external_calls':0}
    try:
        with connection(path) as conn:
            if not match_id:
                if admin:
                    result['matches'] = [dict(r) for r in conn.execute('SELECT id,home_team,away_team,match_date,competition_name FROM matches ORDER BY match_date DESC,id LIMIT 30')]
                result['state'] = 'VERIFIED'
                return result
            row = conn.execute('SELECT * FROM matches WHERE id=?',(str(match_id),)).fetchone()
            if not row:
                return {**result,'state':'MATCH_NOT_FOUND'}
            match = dict(row)
            ident = identity(match)
            result.update(match=match, identity=ident)
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='match_news_references'").fetchone():
                return result
            query = 'SELECT * FROM match_news_references WHERE match_id=? AND match_identity=?'
            if not admin: query += " AND state='PUBLISHED'"
            rows = conn.execute(query+' ORDER BY published_at DESC,id DESC LIMIT 30',(str(match_id),ident)).fetchall()
            for raw in rows:
                item = dict(raw)
                try: item['url'] = safe_url(item['url'])
                except NewsError: continue
                if not admin:
                    item = {k:item[k] for k in ('id','url','title','publisher','published_at','revision')}
                result['items'].append(item)
            result['state'] = 'VERIFIED'
    except (sqlite3.Error, OSError, ValueError):
        result['state'] = 'READ_UNAVAILABLE'
        result['items'] = []
    return result


def save_draft(path, match_id, data, *, actor, now=None):
    if not actor: raise NewsError('Falta la identidad del revisor.')
    now = time.time() if now is None else now
    if data.get('confirmed') != '1':
        raise NewsError('Confirma la asociación al encuentro y los permisos de la referencia.')
    url, evidence = safe_url(data.get('url')), safe_url(data.get('evidence_url'))
    title = clean(data.get('title'),180,'título descriptivo')
    publisher = clean(data.get('publisher'),100,'medio')
    basis = clean(data.get('basis'),1200,'fundamento del uso')
    try:
        published = datetime.fromisoformat(str(data.get('published_at','')).replace('Z','+00:00'))
        if published.tzinfo is None or published.timestamp() > now + 300: raise ValueError()
    except (TypeError,ValueError):
        raise NewsError('Indica la publicación con zona horaria; no puede estar en el futuro.') from None
    # Initialize only after validation and inside an explicit authenticated mutation.
    with connection(path, True) as conn:
        row = conn.execute('SELECT * FROM matches WHERE id=?',(str(match_id),)).fetchone()
        if not row: raise NewsError('El partido ya no existe.')
        match = dict(row); ident = identity(match)
        if ident != data.get('identity'): raise NewsError('El partido ha cambiado. Recarga antes de guardar.')
        # Not heuristic matching: an admin must verify a tight chronological window.
        try:
            kickoff_day = datetime.fromisoformat(str(match['match_date'])[:10]).replace(tzinfo=timezone.utc)
        except (ValueError, KeyError):
            raise NewsError('La fecha del encuentro no está confirmada.') from None
        if not -2*86400 <= published.timestamp()-kickoff_day.timestamp() <= 7*86400:
            raise NewsError('La fecha del artículo no corresponde al intervalo de este encuentro.')
        for statement in SCHEMA.split(';'):
            if statement.strip(): conn.execute(statement)
        rev = hashlib.sha256(json.dumps([ident,url,title,publisher,published.isoformat(),evidence,basis,now],ensure_ascii=False).encode()).hexdigest()
        try:
            cur = conn.execute('INSERT INTO match_news_references(match_id,match_identity,url,title,publisher,published_at,evidence_url,basis,state,revision,reviewed_by,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                (str(match_id),ident,url,title,publisher,published.astimezone(timezone.utc).isoformat(),evidence,basis,'DRAFT',rev,str(actor)[:120],now))
        except sqlite3.IntegrityError:
            raise NewsError('Ese enlace ya está registrado para el partido. Revisa la referencia existente.') from None
        item = dict(conn.execute('SELECT * FROM match_news_references WHERE id=?',(cur.lastrowid,)).fetchone())
        conn.execute('INSERT INTO match_news_audit(news_id,action,actor,snapshot,created_at) VALUES(?,?,?,?,?)',
                     (cur.lastrowid,'DRAFT',str(actor)[:120],json.dumps(item,ensure_ascii=False),now))
    return cur.lastrowid


def decide(path, match_id, news_id, data, *, actor, now=None):
    if not actor or data.get('action') not in {'PUBLISH','RETRACT'}: raise NewsError('Acción no válida.')
    if data.get('confirmed') != '1': raise NewsError('Confirma la decisión antes de continuar.')
    now = time.time() if now is None else now
    with connection(path, True) as conn:
        row = conn.execute('SELECT * FROM match_news_references WHERE id=? AND match_id=?',(int(news_id),str(match_id))).fetchone()
        match = conn.execute('SELECT * FROM matches WHERE id=?',(str(match_id),)).fetchone()
        if not row or not match or row['match_identity'] != identity(dict(match)):
            raise NewsError('La referencia o el partido han cambiado.')
        if data.get('revision') != row['revision']: raise NewsError('Otra revisión cambió esta referencia. Recarga la página.')
        if data['action'] == 'PUBLISH': safe_url(row['url']); safe_url(row['evidence_url'])
        state = 'PUBLISHED' if data['action']=='PUBLISH' else 'RETRACTED'
        rev = hashlib.sha256((row['revision']+state+str(now)).encode()).hexdigest()
        conn.execute('UPDATE match_news_references SET state=?,revision=?,reviewed_by=?,updated_at=? WHERE id=?',
                     (state,rev,str(actor)[:120],now,int(news_id)))
        conn.execute('INSERT INTO match_news_audit(news_id,action,actor,snapshot,created_at) VALUES(?,?,?,?,?)',
                     (int(news_id),state,str(actor)[:120],json.dumps(dict(row),ensure_ascii=False),now))
    return state
