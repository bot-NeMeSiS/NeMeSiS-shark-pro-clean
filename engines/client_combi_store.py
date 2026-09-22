"""Private draft persistence on the existing DB, separate from global editorial combis.

Reads never initialize schema. Writes use one short owned transaction and no network.
Only explicit saves create the additive private table; legacy global rows are not
assigned to users or broadcast. A draft is not evidence that a bet was placed.
"""
from __future__ import annotations
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import uuid

from engines.combi_advisor_engine import (CONTRACT, CombiError, assess_pick, capabilities,
    clock, decimal, key, outcome, preview, suggest, text, visible_pick)
from engines.v935_launch_trust_engine import match_status_truth, match_kickoff_madrid
from engines.team_result_evidence_engine import build_team_result_evidence


def _table(conn, name):
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


def _json(value):
    try:
        data = json.loads(value or '{}')
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


@contextmanager
def connection(path, *, write=False):
    path = Path(path).resolve()
    if not path.is_file():
        raise CombiError('STORAGE_UNAVAILABLE', 'No se pudo leer la información guardada.', 503)
    try:
        with closing(sqlite3.connect(path.as_uri()+('?mode=rw' if write else '?mode=ro'), uri=True, timeout=.5)) as conn:
            conn.row_factory = sqlite3.Row
            if not write:
                conn.execute('PRAGMA query_only=ON')
            conn.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            try:
                yield conn
                if write:
                    conn.commit()
            except Exception:
                if write:
                    conn.rollback()
                raise
    except sqlite3.Error:
        raise CombiError('STORAGE_UNAVAILABLE', 'No se ha podido confirmar la operación. No se reintenta automáticamente.', 503) from None


def actor(conn, user_id, now):
    if not user_id:
        return {'id': '', 'membership': 'FREE'}
    if not _table(conn, 'users'):
        raise CombiError('AUTH_REQUIRED', 'Inicia sesión para consultar tus combinadas.', 401)
    record = conn.execute('SELECT * FROM users WHERE id=?', (str(user_id),)).fetchone()
    if not record:
        raise CombiError('AUTH_REQUIRED', 'La cuenta ya no está disponible. Inicia sesión.', 401)
    record = dict(record)
    plan = text(record.get('membership') or 'FREE').upper()
    expires = record.get('membership_expires_at')
    if expires and (clock(expires) is None or clock(expires) <= now):
        plan = 'FREE'
    if record.get('role') == 'ADMIN':
        plan = 'ADMIN'
    if record.get('disabled') or record.get('is_blocked') or text(record.get('status')).lower() in {'blocked','disabled','deleted'}:
        raise CombiError('AUTH_REQUIRED', 'La cuenta no está activa.', 403)
    return {'id': str(record['id']), 'membership': plan}


def _records(conn, ids=None):
    if not _table(conn, 'picks') or not _table(conn, 'matches'):
        return [], {}, []
    if ids is not None:
        placeholders = ','.join('?' for _ in ids)
        picks = [dict(row) for row in conn.execute('SELECT * FROM picks WHERE id IN ('+placeholders+')', ids)] if ids else []
    else:
        picks = [dict(row) for row in conn.execute("SELECT * FROM picks WHERE lower(status) IN ('published','publicado') ORDER BY updated_at DESC,id LIMIT 200")]
    mids = sorted({str(p.get('match_id') or '') for p in picks if p.get('match_id')})
    if not mids:
        return picks, {}, []
    placeholders = ','.join('?' for _ in mids)
    matches = {str(row['id']): dict(row) for row in conn.execute('SELECT * FROM matches WHERE id IN ('+placeholders+')', mids)}
    odds = []
    if _table(conn, 'odds_snapshots'):
        odds = [dict(row) for row in conn.execute('SELECT * FROM odds_snapshots WHERE match_id IN ('+placeholders+') ORDER BY created_at DESC,id DESC LIMIT 4000', mids)]
    return picks, matches, odds


def _quote_stamp(row, bookmaker):
    """A newly saved cache row does not make an old provider quote fresh."""
    payload_text = row.get('payload_json')
    if not payload_text:
        return row.get('created_at'), 'RECEIPT_ONLY'
    raw = _json(payload_text)
    if not raw:
        return None, 'INVALID_PROVIDER_PAYLOAD'
    if 'bookmakers' in raw:
        if not isinstance(raw.get('bookmakers'),list):
            return None, 'INVALID_PROVIDER_PAYLOAD'
        books = [b for b in raw.get('bookmakers') or [] if isinstance(b,dict)
                 and bookmaker in {key(b.get('title')),key(b.get('key'))}]
        if len(books) != 1:
            return None, 'QUOTE_CLOCK_UNAVAILABLE'
        if not isinstance(books[0].get('markets'),list):
            return None, 'INVALID_PROVIDER_PAYLOAD'
        markets = [m for m in books[0].get('markets') or [] if isinstance(m,dict) and m.get('key')=='h2h']
        if len(markets) != 1:
            return None, 'QUOTE_CLOCK_UNAVAILABLE'
        return markets[0].get('last_update') or books[0].get('last_update'), 'PROVIDER_QUOTE_TIME'
    for field in ('odds_updated_at','last_update','price_updated_at'):
        if field in raw:
            return raw[field], 'PROVIDER_QUOTE_TIME'
    # A manual authorized snapshot can have receipt evidence only. It is explicitly
    # labelled, never presented as a provider publication timestamp.
    return row.get('created_at'), 'RECEIPT_ONLY'


def _quote(pick, match, observations):
    selection = outcome(pick, match)
    book = key(pick.get('bookmaker'))
    if not selection or not book:
        return {}
    raw = _json(pick.get('raw_json'))
    closed = pick.get('market_closed') or raw.get('market_closed')
    matching = []
    for row in observations:
        if str(row.get('match_id')) != str(match.get('id')) or key(row.get('bookmaker')) != book:
            continue
        if key(row.get('market')) not in {'h2h','1x2'}:
            continue
        if any(key(row.get(side+'_team')) != key(match.get(side+'_team')) for side in ('home','away')):
            continue
        dt = clock(row.get('created_at'))
        if dt:
            matching.append((dt, str(row.get('id')), row))
    if matching:
        latest = max(item[0] for item in matching)
        field = {'1':'home_price','X':'draw_price','2':'away_price'}[selection]
        latest_rows = [item[2] for item in matching if item[0] == latest]
        try:
            prices = {decimal(row.get(field)) for row in latest_rows}
        except CombiError:
            return {}
        if len(prices) != 1:
            return {}  # Conflicting prices at the same receipt time are not a quote.
        row = max(matching, key=lambda item:(item[0],item[1]))[2]
        stamp, clock_scope = _quote_stamp(row,book)
        return {'id': row['id'], 'odds': row.get({'1':'home_price','X':'draw_price','2':'away_price'}[selection]),
                'observed_at': stamp, 'clock_scope':clock_scope, 'received_at':row.get('created_at'), 'source': row.get('source'), 'bookmaker': row.get('bookmaker'), 'closed':closed}
    # No fabrication of a quote clock from a pick's editorial updated_at.
    return {'id': 'pick:'+str(pick.get('id')), 'odds': pick.get('odds'),
            'observed_at': pick.get('odds_updated_at') or raw.get('odds_updated_at'), 'clock_scope':'RECORDED_QUOTE_TIME',
            'source': pick.get('odds_source') or raw.get('odds_source') or pick.get('source'),
            'bookmaker': pick.get('bookmaker'), 'closed': closed}


def candidates(conn, user, now, ids=None):
    from engines.combi_match_catalogue import is_market_id, resolve_choices
    direct_ids = [i for i in (ids or []) if is_market_id(i)]
    editorial_ids = [i for i in ids if not is_market_id(i)] if ids is not None else None
    picks, matches, odds = _records(conn, editorial_ids)
    result = []
    by_event_book = {}
    for observation in odds:
        by_event_book.setdefault((str(observation.get('match_id')), key(observation.get('bookmaker'))), []).append(observation)
    for pick in picks:
        if not visible_pick(pick, capabilities(user)['plan']):
            continue  # Never expose a premium selection through block explanations.
        match = matches.get(str(pick.get('match_id')), {})
        observations = by_event_book.get((str(pick.get('match_id')), key(pick.get('bookmaker'))), [])
        result.append(assess_pick(pick, match, _quote(pick, match, observations), user, now=now))
    result.extend(resolve_choices(conn,user,now,direct_ids))
    return result


def _ids(values):
    if isinstance(values, str):
        values = [part.strip() for part in values.split(',') if part.strip()]
    if not isinstance(values, list) or len(values) > 15 or any(not isinstance(p,str) or not 1 <= len(p) <= 180 for p in values):
        raise CombiError('INVALID_SELECTION', 'Revisa los identificadores de las selecciones.')
    if len(set(values)) != len(values):
        raise CombiError('DUPLICATE_PICK', 'Una selección no puede aparecer dos veces.')
    return values


def _build(conn, user, values, now):
    if not user['id']:
        raise CombiError('AUTH_REQUIRED', 'Inicia sesión para crear un borrador privado.', 401)
    ids = _ids(values.get('pick_ids') or values.get('picks') or [])
    if values.get('mode') == 'suggest':
        raw_count = str(values.get('count', values.get('limit','3')))
        if not re.fullmatch(r'\d{1,2}', raw_count):
            raise CombiError('INVALID_OPTIONS', 'Número de selecciones no válido.')
        legs = suggest(candidates(conn,user,now), int(raw_count), user=user,
                       risk=text(values.get('risk') or 'conservador'),
                       date=text(values.get('date'),10), bookmaker=text(values.get('bookmaker'),120))
    else:
        pool = {p['id']:p for p in candidates(conn,user,now,ids)}
        if any(pid not in pool for pid in ids):
            raise CombiError('SELECTION_UNAVAILABLE', 'Alguna selección no está disponible para tu cuenta.', 409)
        legs = [pool[pid] for pid in ids]
    return preview(legs, values.get('stake', '0.10'), user=user, now=now)


def _saved(conn, user, limit=20):
    if not user['id'] or not _table(conn, 'client_combi_drafts'):
        return []
    output = []
    for row in conn.execute('SELECT id,payload_json,created_at FROM client_combi_drafts WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT ?', (user['id'],limit)):
        payload = _json(row['payload_json'])
        allowed = all(visible_pick(p,capabilities(user)['plan']) for p in payload.get('legs') or [])
        output.append({'id':row['id'], 'created_at':row['created_at'], 'payload':payload if allowed else {},
                       'locked':not allowed, 'requires_revalidation':True})
    return output


def read_center(path, user_id='', *, now=None, catalogue_filters=None, selected=None):
    now = clock(now) or datetime.now(timezone.utc)
    with connection(path) as conn:
        user = actor(conn,user_id,now)
        pool = candidates(conn,user,now)
        extra = {}
        if catalogue_filters is not None:
            from engines.combi_match_catalogue import read_catalogue
            extra['catalogue'] = read_catalogue(conn,user,filters=catalogue_filters,now=now)
            if selected:
                current = {p['id'] for p in pool}
                pool.extend(p for p in candidates(conn,user,now,selected) if p['id'] not in current)
        return {**extra, 'contract':CONTRACT, 'capabilities':capabilities(user), 'signed_in':bool(user['id']),
                'candidates':[p for p in pool if p['eligible']], 'blocked':[p for p in pool if not p['eligible']],
                'saved':_saved(conn,user), 'sample_limit':200, 'as_of':now.isoformat(), 'external_calls':0}


def make_preview(path, user_id, values, *, now=None):
    now = clock(now) or datetime.now(timezone.utc)
    with connection(path) as conn:
        return _build(conn,actor(conn,user_id,now),values,now)


def save_draft(path, user_id, values, *, now=None):
    now = clock(now) or datetime.now(timezone.utc)
    request_id = str(values.get('request_id') or '')
    revision = str(values.get('revision') or '')
    if not re.fullmatch('[a-f0-9]{32}', request_id) or not re.fullmatch('[a-f0-9]{64}', revision):
        raise CombiError('PREVIEW_REQUIRED', 'Revisa una vista previa antes de guardar.', 409)
    with connection(path,write=True) as conn:
        user = actor(conn,user_id,now)
        if not user['id']:
            raise CombiError('AUTH_REQUIRED','Inicia sesión.',401)
        if _table(conn,'client_combi_drafts'):
            old = conn.execute('SELECT id,revision,payload_json FROM client_combi_drafts WHERE user_id=? AND request_id=?', (user['id'],request_id)).fetchone()
            if old:
                saved = _json(old['payload_json'])
                requested_ids = _ids(values.get('pick_ids') or values.get('picks') or [])
                same_request = requested_ids == [p['id'] for p in saved.get('legs',[])] and decimal(values.get('stake','0.10'),money=True) == decimal(saved.get('stake'),money=True)
                if old['revision'] != revision or not same_request:
                    raise CombiError('REQUEST_CONFLICT','La operación ya se utilizó para otro borrador.',409)
                return {'id':old['id'],'replayed':True,'not_a_bet':True}
        result = _build(conn,user,values,now)
        if result['revision'] != revision:
            raise CombiError('QUOTE_CHANGED','Las cuotas o el contexto han cambiado. Genera y revisa otra vista previa.',409)
        conn.execute('''CREATE TABLE IF NOT EXISTS client_combi_drafts(
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, request_id TEXT NOT NULL,
            revision TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(user_id,request_id))''')
        count = conn.execute('SELECT COUNT(*) FROM client_combi_drafts WHERE user_id=?',(user['id'],)).fetchone()[0]
        if count >= 100:
            raise CombiError('DRAFT_LIMIT','Has alcanzado 100 borradores. No se eliminan los anteriores automáticamente.',409)
        draft_id = uuid.uuid4().hex
        conn.execute('INSERT INTO client_combi_drafts VALUES (?,?,?,?,?,?)',
            (draft_id,user['id'],request_id,revision,json.dumps(result,ensure_ascii=False),now.isoformat()))
        return {'id':draft_id,'replayed':False,'not_a_bet':True}


def _recent_form(conn, match, now):
    result = {}
    cutoff = min(now, match_kickoff_madrid(match) or now)
    for side in ('home','away'):
        name = text(match.get(side+'_team'))
        related = [dict(row) for row in conn.execute(
            'SELECT * FROM matches WHERE home_team=? OR away_team=? ORDER BY match_date DESC,id LIMIT 300',
            (name,name))] if 'match_date' in match else [dict(row) for row in conn.execute(
            'SELECT * FROM matches WHERE home_team=? OR away_team=? LIMIT 300', (name,name))]
        related = [row for row in related if str(row.get('id')) != str(match.get('id'))
                   and key(row.get('source')) == key(match.get('source'))
                   and (not match.get('season') or row.get('season') == match.get('season'))
                   and (match_kickoff_madrid(row) is not None and match_kickoff_madrid(row) < cutoff)]
        evidence = build_team_result_evidence(related, name)
        recent = evidence['items'][:5]
        result[side] = {'team':name,'sample_size':len(recent),
                       'wins':sum(item['outcome']=='Victoria' for item in recent),
                       'draws':sum(item['outcome']=='Empate' for item in recent),
                       'losses':sum(item['outcome']=='Derrota' for item in recent),
                       'goals_for':sum(item['goals_for'] for item in recent),
                       'goals_against':sum(item['goals_against'] for item in recent),
                       'items':[{'label':text(item['match'].get('home_team'))+' vs '+text(item['match'].get('away_team')),
                                 'score':str(item['home_score'])+'–'+str(item['away_score']),
                                 'outcome':item['outcome'],'href':item['href']} for item in recent],
                       'season_complete':False,'source':text(match.get('source')),
                       'scope':'Lectura actual de resultados anteriores al inicio; no reconstrucción de lo sabido entonces.'}
    return result


def read_advice(path, user_id='', *, pick_id='', match_id='', now=None):
    now = clock(now) or datetime.now(timezone.utc)
    with connection(path) as conn:
        user = actor(conn,user_id,now)
        if pick_id:
            pool = candidates(conn,user,now,[text(pick_id,180)])
            if not pool:
                raise CombiError('SELECTION_UNAVAILABLE','Selección no disponible para tu cuenta.',404)
            pick = pool[0]
            match_id = pick['match_id']
        else:
            pick = None
        if not _table(conn,'matches'):
            raise CombiError('MATCH_UNAVAILABLE','Partido no disponible.',404)
        row = conn.execute('SELECT * FROM matches WHERE id=?', (text(match_id,180),)).fetchone()
        if not row:
            raise CombiError('MATCH_UNAVAILABLE','Partido no disponible.',404)
        match = dict(row)
        truth = match_status_truth(match,now=now)
        return {'contract':CONTRACT, 'mode':'EVIDENCE_RULES_NO_GENERATIVE_MODEL',
                'match_id':str(match['id']), 'match':text(match.get('home_team'))+' vs '+text(match.get('away_team')),
                'source':text(match.get('source')), 'status':truth.get('lifecycle'),
                'observed_at':text(match.get('last_synced_at')), 'pick':pick,
                'advice':('Puede revisarse como selección 1X2 con cuota reciente; eso no demuestra ventaja ni garantiza el resultado.'
                          if pick and pick['eligible'] else 'Esperar o no apostar también es una decisión: faltan condiciones para construir una combinada con esta evidencia.'),
                'checklist':['Revisar bajas y alineaciones confirmadas en la ficha; no se dan por conocidas.',
                             'Distinguir resultados registrados de una temporada completa.',
                             'Comparar cuota, contexto y condiciones de liquidación; no perseguir pérdidas.'],
                'team_form':_recent_form(conn,match,now), 'probability':None, 'external_calls':0}
