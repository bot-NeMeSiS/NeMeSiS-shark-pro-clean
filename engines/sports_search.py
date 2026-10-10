"""Bounded, read-only discovery of public sports entities already stored locally."""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
import sqlite3
import time
import unicodedata
from urllib.parse import quote, urlencode

KINDS = ('team', 'league', 'match')
TEAM_REFERENCE_PREFIX = '@team:'


@lru_cache(maxsize=4096)
def fold(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', str(value or ''))
                           if unicodedata.category(c) != 'Mn').casefold().split())


def clean_query(value):
    return ' '.join(str(value or '').split())[:90]


def _like(value):
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _terms_clause(expression, terms):
    return ' AND '.join(f"sports_fold({expression}) LIKE ? ESCAPE '\\'" for _ in terms), tuple('%'+_like(t)+'%' for t in terms)


def _text(value, limit=180):
    return str(value or '').strip()[:limit]


def _item(kind, row):
    if kind == 'match':
        label = f"{row['home_team']} · {row['away_team']}"
        context = ' · '.join(filter(None, (row['competition_name'] or row['league_name'], row['country'], row['match_date'], row['kickoff_time'])))
        value = str(row['id'])
        href = '/match/'+quote(value, safe='')
        legacy = [value]
    else:
        label = _text(row['name'])
        context = ' · '.join(filter(None, (row['country'], row['league'] if kind == 'team' else row['region'])))
        value = TEAM_REFERENCE_PREFIX + str(row['key']) if kind == 'team' else str(row['key'])
        href = ('/team/' if kind == 'team' else '/competition/') + quote(str(row['key']), safe='')
        legacy = [label] if kind == 'team' else [label, str(row['key'])]
    return {'kind':kind, 'value':value, 'label':label, 'context':_text(context, 260),
            'href':href, 'legacy_values':legacy, 'saved':False}


def search_sports(db_path, query='', kind='', *, today=None, limit=8, excluded_names=(), budget_seconds=.6):
    """Never initialize schemas, fetch providers, or persist a user's query.

    Every SQL projection omits raw payloads; the SQLite progress deadline bounds
    broad searches. An interrupted/missing catalogue is explicit, not 'no hits'.
    """
    query = clean_query(query)
    kind = kind if kind in KINDS else ''
    result = {'query':query, 'kind':kind, 'items':[], 'has_more':False, 'complete':True, 'status':'READY'}
    terms = fold(query).split()
    if len(fold(query)) < 2 or not any(c.isalnum() for c in query):
        result['status'] = 'TYPE_MORE'
        return result
    if len(terms) > 8:
        result.update(status='REFINE_QUERY', complete=False)
        return result
    limit = max(1, min(int(limit), 12))
    today = str(today or date.today().isoformat())[:10]
    excluded = {fold(str(name)) for name in excluded_names}
    conn = None
    try:
        conn = sqlite3.connect(Path(db_path).resolve().as_uri()+'?mode=ro', uri=True, timeout=.15)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        conn.create_function('sports_fold', 1, fold, deterministic=True)
        conn.create_function('sports_real_name', 1, lambda v: int(bool(str(v or '').strip()) and fold(v) not in excluded), deterministic=True)
        deadline = time.monotonic() + budget_seconds
        conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        for current in (kind,) if kind else KINDS:
            if time.monotonic() > deadline:
                raise sqlite3.OperationalError('search deadline')
            if current in {'team','league'}:
                table = 'teams' if current == 'team' else 'competitions'
                extra = 'league' if current == 'team' else 'region'
                clause, args = _terms_clause(f"coalesce(name,'') || ' ' || coalesce(country,'') || ' ' || coalesce({extra},'')", terms)
                data = conn.execute(f"""SELECT key,name,country,{extra} FROM {table}
                    WHERE sports_real_name(name) AND {clause}
                    ORDER BY CASE WHEN sports_fold(name)=? THEN 0
                                  WHEN sports_fold(name) LIKE ? ESCAPE '\\' THEN 1 ELSE 2 END,
                             name COLLATE NOCASE, country, key LIMIT ?""",
                    args+(fold(query), _like(fold(query))+'%', limit+1)).fetchall()
                data = [r for r in data if fold(r['name']) not in excluded]
            else:
                clause, args = _terms_clause("coalesce(home_team,'') || ' ' || coalesce(away_team,'') || ' ' || coalesce(competition_name,league_name,'') || ' ' || coalesce(country,'')", terms)
                data = []
                for comparison, order in (('>=','ASC'), ('<','DESC')):
                    try:
                        if time.monotonic() > deadline:
                            raise sqlite3.OperationalError('search deadline')
                        rows = conn.execute(f"""SELECT id,home_team,away_team,competition_name,league_name,country,match_date,kickoff_time
                            FROM matches WHERE match_date {comparison} ? AND {clause}
                            AND sports_real_name(home_team) AND sports_real_name(away_team)
                            AND lower(coalesce(source,''))<>'seed estructural'
                            ORDER BY match_date {order}, kickoff_time {order}, id LIMIT ?""",
                            (today,)+args+(limit+1-len(data),)).fetchall()
                    except sqlite3.Error:
                        # Keep available upcoming matches if historical search times out.
                        result['items'].extend(_item(current, row) for row in data[:limit])
                        raise
                    data.extend(r for r in rows if fold(r['home_team']) not in excluded and fold(r['away_team']) not in excluded)
                    if len(data) > limit:
                        break
            result['has_more'] |= len(data) > limit
            result['items'].extend(_item(current, row) for row in data[:limit])
    except (sqlite3.Error, OSError, ValueError):
        result.update(complete=False, status='PARTIAL' if result['items'] else 'UNAVAILABLE')
    finally:
        if conn is not None:
            conn.close()
    return result


def mark_saved(result, favorites):
    saved = {(str(f.get('kind')), str(f.get('value')).casefold()) for f in favorites}
    for item in result['items']:
        item['saved'] = any((item['kind'], str(v).casefold()) in saved for v in [item['value'], *item.pop('legacy_values', [])])
    return result


def search_saved(favorites, query='', kind=''):
    from engines.account_collection_views import favorite_collection
    collection = favorite_collection(favorites, query, kind)
    items = [{'kind':f['kind'], 'value':f['value'], 'label':f.get('label') or f['value'],
              'context':'', 'saved':True,
              'href':'/favoritos?'+urlencode({'q':f.get('label') or f['value'], 'kind':f['kind']})+'#saved-favorites'}
             for f in collection['items'][:24]]
    return {'query':collection['query'], 'kind':collection['kind'], 'items':items,
            'complete':True, 'has_more':len(collection['items']) > 24, 'status':'READY'}
