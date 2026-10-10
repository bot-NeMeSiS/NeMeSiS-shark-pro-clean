"""Bounded, read-only discovery of public sports entities already stored locally."""
from __future__ import annotations

from bisect import insort
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
    value = str(value or '')
    if value.isascii():
        return ' '.join(value.casefold().split())
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', value)
                           if unicodedata.category(c) != 'Mn').casefold().split())


def clean_query(value):
    return ' '.join(str(value or '').split())[:90]


def _like(value):
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _terms_clause(expression, terms):
    # A cheap candidate pass only. Unicode matching below remains authoritative.
    return ' AND '.join(f"{expression} LIKE ? ESCAPE '\\'" for _ in terms), tuple('%'+_like(t)+'%' for t in terms)


_ASCII_LOWER = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')


def _sqlite_text(value, nocase=False):
    text = str(value or '')
    return value is not None, text.translate(_ASCII_LOWER) if nocase else text


class _Descending:
    """Reverse a SQLite text sort key, including its NULL placement."""
    __slots__ = ('value',)

    def __init__(self, value):
        self.value = value

    def __lt__(self, other):
        return self.value > other.value

    def __eq__(self, other):
        return self.value == other.value


class _Candidates:
    """Keep only the best limit+1 public rows; no response or account cache."""
    def __init__(self, kind, query, today, capacity):
        self.kind, self.query, self.today, self.capacity = kind, query, today, capacity
        self.entries = []
        self.identities = set()

    def add(self, row):
        identity = row['id' if self.kind == 'match' else 'key']
        if identity in self.identities:
            return
        if self.kind == 'match':
            historical = row['match_date'] < self.today
            stamp, clock = _sqlite_text(row['match_date']), _sqlite_text(row['kickoff_time'])
            rank = (historical, _Descending(stamp) if historical else stamp,
                    _Descending(clock) if historical else clock, _sqlite_text(identity))
        else:
            name = fold(row['name'])
            rank = (0 if name == self.query else 1 if name.startswith(self.query) else 2,
                    _sqlite_text(row['name'], True), _sqlite_text(row['country']), _sqlite_text(identity))
        insort(self.entries, (rank, str(identity), row))
        self.identities.add(identity)
        if len(self.entries) > self.capacity:
            removed = self.entries.pop()[2]
            self.identities.remove(removed['id' if self.kind == 'match' else 'key'])


def _matches(kind, row, terms, excluded):
    if kind == 'match':
        names = (row['home_team'], row['away_team'])
        competition = row['competition_name'] if row['competition_name'] is not None else row['league_name']
        fields = (*names, competition, row['country'])
    else:
        names = (row['name'],)
        fields = (row['name'], row['country'], row['league' if kind == 'team' else 'region'])
    # Folding fields separately is equivalent to folding their space-joined
    # text, and reuses common countries, leagues and team names in match history.
    text = ' '.join(filter(None, (fold(value) for value in fields)))
    return (all(term in text for term in terms)
            and all(str(name or '').strip() and fold(name) not in excluded for name in names))


def _search_sql(kind, today, *, terms=(), history=False, native=False, capacity=9):
    if kind == 'match':
        expression = "coalesce(home_team,'') || ' ' || coalesce(away_team,'') || ' ' || coalesce(competition_name,league_name,'') || ' ' || coalesce(country,'')"
        comparison, order = ('<', 'DESC') if history else ('>=', 'ASC')
        sql = f"""SELECT id,home_team,away_team,competition_name,league_name,country,match_date,kickoff_time
            FROM matches WHERE match_date {comparison} ?
            AND lower(coalesce(source,''))<>'seed estructural'"""
        args = (today,)
        ordering = f' ORDER BY match_date {order}, kickoff_time {order}, id'
    else:
        table, extra = ('teams', 'league') if kind == 'team' else ('competitions', 'region')
        expression = f"coalesce(name,'') || ' ' || coalesce(country,'') || ' ' || coalesce({extra},'')"
        sql, args, ordering = f'SELECT key,name,country,{extra} FROM {table} WHERE 1', (), ''
    if native:
        clause, values = _terms_clause(expression, terms)
        sql += ' AND ' + clause
        args += values
    sql += ordering
    if native:
        sql += ' LIMIT ?'
        args += (capacity,)
    return sql, args


def _scan(conn, sql, args, *, deadline, kind, terms, excluded, candidates, stop_after=None):
    """Yield after each examined row so Unicode scans can share the deadline."""
    if time.monotonic() >= deadline:
        raise sqlite3.OperationalError('search deadline')
    conn.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
    remaining = max(0, deadline - time.monotonic())
    conn.execute(f'PRAGMA busy_timeout={int(min(.15, remaining) * 1000)}')
    cursor = conn.execute(sql, args)
    accepted = 0
    try:
        while time.monotonic() < deadline:
            row = cursor.fetchone()
            if row is None:
                return accepted
            if _matches(kind, row, terms, excluded):
                candidates.add(row)
                accepted += 1
                if stop_after is not None and accepted >= stop_after:
                    return accepted
            yield
        raise sqlite3.OperationalError('search deadline')
    finally:
        cursor.close()


def _scan_category(conn, kind, today, *, deadline, terms, excluded, candidates, capacity):
    sql, args = _search_sql(kind, today)
    found = yield from _scan(conn, sql, args, deadline=deadline, kind=kind, terms=terms,
                             excluded=excluded, candidates=candidates,
                             stop_after=capacity if kind == 'match' else None)
    if kind == 'match' and found < capacity:
        sql, args = _search_sql(kind, today, history=True)
        yield from _scan(conn, sql, args, deadline=deadline, kind=kind, terms=terms,
                         excluded=excluded, candidates=candidates, stop_after=capacity-found)


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

    Native candidates improve a cold first response; only the Unicode pass can
    certify completeness. All phases share one deadline, including connection
    waits, and an interrupted category retains its verified partial candidates.
    """
    query = clean_query(query)
    kind = kind if kind in KINDS else ''
    result = {'query':query, 'kind':kind, 'items':[], 'has_more':False, 'complete':True, 'status':'READY'}
    folded_query = fold(query)
    terms = folded_query.split()
    if len(folded_query) < 2 or not any(c.isalnum() for c in query):
        result['status'] = 'TYPE_MORE'
        return result
    if len(terms) > 8:
        result.update(status='REFINE_QUERY', complete=False)
        return result
    limit = max(1, min(int(limit), 12))
    today = str(today or date.today().isoformat())[:10]
    budget_seconds = min(.6, max(0, float(budget_seconds)))
    deadline = time.monotonic() + budget_seconds
    excluded = {fold(str(name)) for name in excluded_names}
    kinds = (kind,) if kind else KINDS
    candidates = {current: _Candidates(current, folded_query, today, limit+1) for current in kinds}
    completed = set()
    scans = {}
    conn = None
    try:
        if time.monotonic() >= deadline:
            raise sqlite3.OperationalError('search deadline')
        conn = sqlite3.connect(Path(db_path).resolve().as_uri()+'?mode=ro', uri=True,
                               timeout=min(.15, max(0, deadline - time.monotonic())))
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        # Both passes must observe the same catalogue, even if a writer commits.
        conn.execute('BEGIN')
        for current in kinds:
            try:
                sql, args = _search_sql(current, today, terms=terms, native=True, capacity=limit+1)
                for _ in _scan(conn, sql, args, deadline=min(deadline, time.monotonic()+budget_seconds*.2/len(kinds)),
                               kind=current, terms=terms, excluded=excluded, candidates=candidates[current]):
                    pass
            except sqlite3.Error:
                pass  # The authoritative pass can still complete this category.
        scans = {current: _scan_category(conn, current, today, deadline=deadline, terms=terms,
                                        excluded=excluded, candidates=candidates[current], capacity=limit+1)
                 for current in kinds}
        while scans and time.monotonic() < deadline:
            for current, scan in list(scans.items()):
                try:
                    for _ in range(64):
                        next(scan)
                except StopIteration:
                    completed.add(current)
                    del scans[current]
                except sqlite3.Error:
                    del scans[current]
    except (sqlite3.Error, OSError, ValueError):
        pass
    finally:
        for scan in scans.values():
            scan.close()
        if conn is not None:
            conn.close()
    for current in kinds:
        data = candidates[current].entries
        result['has_more'] |= len(data) > limit
        result['items'].extend(_item(current, entry[2]) for entry in data[:limit])
    if len(completed) != len(kinds):
        result.update(complete=False, status='PARTIAL' if result['items'] else 'UNAVAILABLE')
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
