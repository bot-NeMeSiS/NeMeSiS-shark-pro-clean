"""Read-only forthcoming fixtures and 1X2 choices, independent of editorial picks.

Uses the existing quote, lifecycle, entitlement and draft evaluator. No provider
calls, migrations, synthetic pick rows, price claims or changes to stored matches.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from urllib.parse import quote

from engines.combi_advisor_engine import (
    CombiError, assess_market_choice, capabilities, clock, key, text,
)
from engines.picks_quality_engine import competition_priority
from engines.v935_launch_trust_engine import match_kickoff_madrid, match_status_truth

PREFIX = 'market:'
SCAN_LIMIT = 2000
PAGE_SIZE = 24


def is_market_id(value):
    return isinstance(value, str) and value.startswith(PREFIX)


def _anchor(row):
    fields = ['id','match_id','bookmaker','market','home_team','away_team','source']
    return hashlib.sha256(json.dumps([str(row.get(f) or '') for f in fields],
                                    ensure_ascii=False).encode()).hexdigest()[:20]


def choice_id(row, selection):
    sid = str(row.get('id') or '')
    if not sid or len(sid) > 140 or selection not in {'1','X','2'}:
        return ''
    return PREFIX + sid + ':' + selection + ':' + _anchor(row)


def _odds(conn, mids):
    from engines import client_combi_store as store
    if not mids or not store._table(conn, 'odds_snapshots'):
        return [], False
    # Per page, never one lookup per fixture; overflow is explicit, not no-odds.
    args = ','.join('?' for _ in mids)
    rows = [dict(r) for r in conn.execute(
        'SELECT * FROM odds_snapshots WHERE match_id IN ('+args+') ORDER BY created_at DESC,id DESC LIMIT 4001', mids)]
    return rows[:4000], len(rows) > 4000


def _market_quote(choice, match, observations):
    from engines import client_combi_store as store
    price = store._quote(choice, match, observations)
    row = next((r for r in observations if str(r.get('id')) == str(price.get('id'))), {})
    raw = store._json(row.get('payload_json'))
    for info in (row, raw):
        for flag in ('market_closed', 'suspended', 'is_suspended'):
            if flag in info and info[flag] is not None and key(info[flag]) not in {'', '0', 'false', 'no'}:
                price['closed'] = True
        if key(info.get('status')) in {'closed','suspended','removed','cancelled'}:
            price['closed'] = True
    return price


def resolve_choices(conn, user, now, ids):
    """Re-read the immutable association before resolving the newest stored price."""
    from engines import client_combi_store as store
    if not ids or not store._table(conn, 'odds_snapshots') or not store._table(conn, 'matches'):
        return []
    parsed = {}
    for ident in ids:
        try:
            sid, selection, fingerprint = ident[len(PREFIX):].rsplit(':', 2)
        except ValueError:
            continue
        if selection in {'1','X','2'} and sid and len(ident) <= 180:
            parsed[ident] = (sid,selection,fingerprint)
    if not parsed:
        return []
    sids = sorted({p[0] for p in parsed.values()})
    rows = list(conn.execute('SELECT * FROM odds_snapshots WHERE id IN ('+','.join('?' for _ in sids)+')', sids))
    anchors = {}
    for row in rows:
        anchors.setdefault(str(row['id']), []).append(dict(row))
    mids = sorted({str(row['match_id']) for row in rows if row['match_id']})
    if not mids:
        return []
    matches = {str(r['id']):dict(r) for r in conn.execute(
        'SELECT * FROM matches WHERE id IN ('+','.join('?' for _ in mids)+')', mids)}
    observations, truncated = _odds(conn,mids)
    if truncated:
        raise CombiError('QUOTE_WINDOW_LIMIT', 'Hay demasiadas revisiones de cuotas para verificarlas en esta lectura.', 503)
    output = []
    for ident,(sid,selection,fingerprint) in parsed.items():
        group = anchors.get(sid,[])
        if len(group) != 1 or _anchor(group[0]) != fingerprint:
            continue
        anchor = group[0]
        match = matches.get(str(anchor.get('match_id')))
        if not match or key(anchor.get('market')) not in {'1x2','h2h'}:
            continue
        if any(key(anchor.get(side+'_team')) != key(match.get(side+'_team')) for side in ('home','away')):
            continue
        choice = {'id':ident,'match_id':str(match['id']), 'market':'1x2', 'selection':selection,
                  'bookmaker':anchor.get('bookmaker'), 'membership_required':'PRO'}
        # Existing resolver refuses stale provider clocks and conflicting prices.
        market = _market_quote(choice, match, observations)
        output.append(assess_market_choice(choice, match, market, user, now=now))
    return output


def read_catalogue(conn, user, *, filters=None, selected=None, now=None):
    from engines import client_combi_store as store
    now = clock(now) or datetime.now(timezone.utc)
    filters = filters if isinstance(filters,dict) else {}
    q, day = text(filters.get('q'),100), text(filters.get('day'),10)
    league = text(filters.get('league'),160)
    try:
        page = max(1,min(int(filters.get('page') or 1),100))
    except (ValueError,TypeError):
        page = 1
    if day:
        try:
            datetime.strptime(day,'%Y-%m-%d')
        except ValueError:
            raise CombiError('INVALID_DATE','Selecciona una fecha válida.') from None
    result = {'state':'EMPTY','matches':[], 'total':0,'page':page,'pages':1,
              'q':q,'day':day,'league':league,'leagues':[], 'truncated':False,
              'external_calls':0, 'scan_limit':SCAN_LIMIT, 'quote_truncated':False}
    if not store._table(conn,'matches'):
        return result
    cols = {r[1] for r in conn.execute('PRAGMA table_info(matches)')}
    if not {'id','home_team','away_team'} <= cols:
        result['state']='SCHEMA_UNAVAILABLE'
        return result
    conn.create_function('ns_catalogue_fold',1,lambda v:key(v),deterministic=True)
    sql = 'SELECT * FROM matches WHERE 1=1'
    params = []
    if q:
        parts = ["COALESCE(\""+c+"\",'')" for c in ('home_team','away_team','competition_name','league_name') if c in cols]
        sql += " AND instr(ns_catalogue_fold("+"||' '||".join(parts)+'),?)>0'
        params.append(key(q))
    # Search precedes the safety bound; it is not just filtering the visible page.
    order = '"match_date" DESC,' if 'match_date' in cols else ''
    sql += ' ORDER BY '+order+'id LIMIT ?'
    params.append(SCAN_LIMIT+1)
    records = [dict(r) for r in conn.execute(sql,params)]
    result['truncated'] = len(records)>SCAN_LIMIT
    items = []
    for m in records[:SCAN_LIMIT]:
        sport = key(m.get('sport_key'))
        if not (sport.startswith('soccer') or sport in {'football','futbol'}) or not text(m.get('source')):
            continue
        if any(key(m.get(f)) in {'1','true','yes'} for f in ('is_fake','is_demo','simulated')):
            continue
        kickoff = match_kickoff_madrid(m)
        truth = match_status_truth(m,now=now)
        if not kickoff or kickoff<=now or truth['lifecycle']!='UPCOMING' or truth.get('status_conflict'):
            continue
        competition=text(m.get('competition_name') or m.get('league_name'))
        if day and kickoff.date().isoformat()!=day:
            continue
        if league and key(competition)!=key(league):
            continue
        rank=competition_priority(competition)
        items.append((m,kickoff,competition,rank))
    target=text(filters.get('target'),180) if not q else ''
    items.sort(key=lambda item:(bool(target) and str(item[0]['id'])!=target,-item[3],item[1],str(item[0]['id'])))
    result.update(total=len(items),pages=max(1,(len(items)+PAGE_SIZE-1)//PAGE_SIZE),
                  leagues=sorted({item[2] for item in items if item[2]}))
    result['page']=min(page,result['pages'])
    page_items=items[(result['page']-1)*PAGE_SIZE:result['page']*PAGE_SIZE]
    mids=[str(item[0]['id']) for item in page_items]
    observations, truncated=_odds(conn,mids)
    result['quote_truncated']=truncated
    for m,kickoff,competition,rank in page_items:
        quotes={}
        for r in observations:
            if str(r.get('match_id')) != str(m['id']) or key(r.get('market')) not in {'h2h','1x2'}:
                continue
            if any(key(r.get(side+'_team'))!=key(m.get(side+'_team')) for side in ('home','away')):
                continue
            book=key(r.get('bookmaker'))
            if book and book not in quotes:
                quotes[book]=r
        groups=[]
        for book,anchor in sorted(quotes.items()):
            choices=[]
            for selection in ('1','X','2'):
                ident=choice_id(anchor,selection)
                if not ident:
                    continue
                choice={'id':ident,'match_id':str(m['id']),'market':'1x2','selection':selection,
                        'bookmaker':anchor.get('bookmaker'),'membership_required':'PRO'}
                price=_market_quote(choice,m,observations) if not truncated else {}
                leg=assess_market_choice(choice,m,price,user,now=now)
                choices.append(leg)
            groups.append({'bookmaker':text(anchor.get('bookmaker')), 'choices':choices})
        info={'id':str(m['id']), 'home':text(m.get('home_team')),'away':text(m.get('away_team')),
              'competition':competition,'kickoff':kickoff.isoformat(), 'featured':rank>=14,
              'source':text(m.get('source')), 'groups':groups,
              'match_url':'/match/'+quote(str(m['id']),safe=''),
              'venue':text(m.get('venue_name') or m.get('stadium')),
              'referee':text(m.get('referee')), 'season':text(m.get('season')),
              'round':text(m.get('round') or m.get('round_name'))}
        result['matches'].append(info)
    result['state']='RECORDED' if items else 'EMPTY'
    return result
