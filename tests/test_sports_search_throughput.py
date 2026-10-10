"""Synthetic read-only search equivalence, interruptions and bounded work."""
import sqlite3

import pytest

from engines import sports_search as search_engine
from test_sports_search import sports_catalogue


TODAY = '2026-10-09'
EXCLUDED = {'equipo a'}


def search(path, query='granada', kind='', **kwargs):
    return search_engine.search_sports(path, query, kind, today=TODAY,
                                       excluded_names=EXCLUDED, **kwargs)


def reference(path, query, kind='', limit=8):
    """The previous exhaustive SQL contract, on small synthetic catalogues."""
    folded = search_engine.fold(query)
    terms = folded.split()
    items, has_more = [], False
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        conn.create_function('sports_fold', 1, search_engine.fold)
        conn.create_function('sports_real_name', 1, lambda value:
            int(bool(str(value or '').strip()) and search_engine.fold(value) not in EXCLUDED))
        for current in (kind,) if kind else search_engine.KINDS:
            if current == 'match':
                expression = "coalesce(home_team,'') || ' ' || coalesce(away_team,'') || ' ' || coalesce(competition_name,league_name,'') || ' ' || coalesce(country,'')"
                data = []
                for comparison, order in (('>=', 'ASC'), ('<', 'DESC')):
                    clause = ' AND '.join(f"sports_fold({expression}) LIKE ? ESCAPE '\\'" for term in terms)
                    args = tuple('%'+search_engine._like(term)+'%' for term in terms)
                    data.extend(conn.execute(f'''SELECT id,home_team,away_team,competition_name,league_name,country,match_date,kickoff_time
                        FROM matches WHERE match_date {comparison} ? AND {clause}
                        AND sports_real_name(home_team) AND sports_real_name(away_team)
                        AND lower(coalesce(source,''))<>'seed estructural'
                        ORDER BY match_date {order}, kickoff_time {order}, id LIMIT ?''',
                        (TODAY,)+args+(limit+1-len(data),)).fetchall())
                    if len(data) > limit:
                        break
            else:
                table, extra = ('teams', 'league') if current == 'team' else ('competitions', 'region')
                expression = f"coalesce(name,'') || ' ' || coalesce(country,'') || ' ' || coalesce({extra},'')"
                clause = ' AND '.join(f"sports_fold({expression}) LIKE ? ESCAPE '\\'" for term in terms)
                args = tuple('%'+search_engine._like(term)+'%' for term in terms)
                data = conn.execute(f'''SELECT key,name,country,{extra} FROM {table}
                    WHERE sports_real_name(name) AND {clause}
                    ORDER BY CASE WHEN sports_fold(name)=? THEN 0
                        WHEN sports_fold(name) LIKE ? ESCAPE '\\' THEN 1 ELSE 2 END,
                        name COLLATE NOCASE,country,key LIMIT ?''',
                        args+(folded,search_engine._like(folded)+'%',limit+1)).fetchall()
            has_more |= len(data) > limit
            items.extend(search_engine._item(current, row) for row in data[:limit])
    return items, has_more


@pytest.fixture()
def unicode_catalogue(sports_catalogue):
    with sqlite3.connect(sports_catalogue) as conn:
        names = [('exact-upper', 'GRANADA', None), ('exact-accent', 'Granáda', ''),
                 ('exact', 'Granada', 'España'), ('sharp', 'Straße Granada', 'Deutschland'),
                 ('turkish', 'İstanbul', 'Türkiye'), ('greek', 'Στρατός', 'Ελλάδα'),
                 ('combining', 'A\u0301guilas', 'España'), ('underscore', 'Club_A Granada', 'España'),
                 ('slash', 'A\\B Granada', 'España'), ('excluded', 'Equipo A', 'Granada'),
                 ('empty', '', 'Granada')]
        conn.executemany('INSERT INTO teams VALUES(?,?,?,?,?,?)',
                         [(key,name,country,'Liga local',key,'sportsdb') for key,name,country in names])
        conn.executemany('INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?)', [
            ('early/a', 'Granáda', 'Straße', '', 'Granada', None, '2099-10-10', None, 'sportsdb'),
            ('early/b', 'Granáda', 'Straße', '', 'Granada', None, '2099-10-10', None, 'sportsdb'),
            ('past/a', 'Granáda', 'İstanbul', None, 'Copa', 'España', '2020-10-09', '19:00', 'sportsdb'),
            ('past/b', 'Granáda', 'Στρατός', 'Copa', 'Copa', 'España', '2020-10-09', None, 'sportsdb'),
        ])
    return sports_catalogue


@pytest.mark.parametrize('query', ['gra', 'GRANÁDA fem', 'granada atletico', 'granada nicaragua',
    '100%', 'club_a', 'a\\b', 'division espana', 'strasse', 'istanbul', 'στρα', 'aguilas', 'inexistente'])
@pytest.mark.parametrize('kind', ['', 'team', 'league', 'match'])
def test_complete_answers_match_previous_unicode_and_order_contract(unicode_catalogue, query, kind):
    expected, more = reference(unicode_catalogue, query, kind, limit=3)
    actual = search(unicode_catalogue, query, kind, limit=3)
    assert actual['complete'] and actual['status'] == 'READY'
    assert actual['items'] == expected
    assert actual['has_more'] == more


class FailingCursor:
    def __init__(self, cursor, after):
        self.cursor, self.after = cursor, after

    def fetchone(self):
        if self.after == 0:
            raise sqlite3.OperationalError('interrupted')
        self.after -= 1
        return self.cursor.fetchone()

    def close(self):
        self.cursor.close()


@pytest.mark.parametrize('table,kind', [('teams','team'), ('competitions','league'), ('matches','match')])
def test_interrupted_stream_retains_candidates_and_other_categories(sports_catalogue, monkeypatch, table, kind):
    connect = sqlite3.connect

    class Connection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if f'FROM {table} ' in sql:
                if 'LIKE' in sql:
                    raise sqlite3.OperationalError('native pass unavailable')
                cursor = super().execute(sql, *args, **kwargs)
                return FailingCursor(cursor, 1 if kind != 'league' else 2)
            return super().execute(sql, *args, **kwargs)

    monkeypatch.setattr(sqlite3, 'connect', lambda *args, **kwargs: connect(*args, **kwargs, factory=Connection))
    answer = search(sports_catalogue)
    assert answer['status'] == 'PARTIAL' and not answer['complete']
    assert {item['kind'] for item in answer['items']} == {'team', 'league', 'match'}
    assert len({(item['kind'], item['value']) for item in answer['items']}) == len(answer['items'])


def test_native_candidates_are_partial_until_unicode_scan_finishes(unicode_catalogue, monkeypatch):
    connect = sqlite3.connect

    class Connection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if 'FROM teams ' in sql and 'LIKE' not in sql:
                raise sqlite3.OperationalError('interrupted')
            return super().execute(sql, *args, **kwargs)

    monkeypatch.setattr(sqlite3, 'connect', lambda *args, **kwargs: connect(*args, **kwargs, factory=Connection))
    answer = search(unicode_catalogue, 'gra', 'team')
    assert answer['items'] and answer['status'] == 'PARTIAL' and not answer['complete']
    assert all('gra' in search_engine.fold(item['label']+' '+item['context']) for item in answer['items'])


def test_missing_one_catalogue_does_not_hide_the_others(sports_catalogue):
    with sqlite3.connect(sports_catalogue) as conn:
        conn.execute('DROP TABLE teams')
    answer = search(sports_catalogue)
    assert answer['status'] == 'PARTIAL' and not answer['complete']
    assert {item['kind'] for item in answer['items']} == {'league', 'match'}


def test_budget_is_shared_and_late_catalogue_hits_survive_cold_scan(sports_catalogue, monkeypatch):
    with sqlite3.connect(sports_catalogue) as conn:
        conn.execute('DELETE FROM teams')
        conn.executemany('INSERT INTO teams VALUES(?,?,?,?,?,?)',
            [(str(i), f'Club {i}', 'España', 'Liga QA', str(i), 'sportsdb') for i in range(1000)])
        conn.execute('INSERT INTO teams VALUES(?,?,?,?,?,?)',
                     ('last', 'Granada CF', 'España', 'Segunda', 'last', 'sportsdb'))
    clock = [0.0]
    matches = search_engine._matches

    def costly_match(*args):
        clock[0] += .005
        return matches(*args)

    monkeypatch.setattr(search_engine.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(search_engine, '_matches', costly_match)
    answer = search(sports_catalogue)
    assert answer['status'] == 'PARTIAL' and not answer['complete']
    assert any(item['value'] == '@team:last' for item in answer['items'])
    assert {item['kind'] for item in answer['items']} == {'team', 'league', 'match'}
    assert clock[0] <= .605


def test_normalization_work_reuses_public_fields_without_caching_responses(sports_catalogue, monkeypatch):
    total = 1000
    with sqlite3.connect(sports_catalogue) as conn:
        conn.execute('DELETE FROM teams')
        conn.executemany('INSERT INTO teams VALUES(?,?,?,?,?,?)',
            [(str(i), f'Club número {i}', 'España', 'Liga Única', str(i), 'sportsdb') for i in range(total)])
    search_engine.fold.cache_clear()
    normalize = search_engine.unicodedata.normalize
    normalized = []

    def count_normalization(form, value):
        normalized.append(value)
        return normalize(form, value)

    monkeypatch.setattr(search_engine.unicodedata, 'normalize', count_normalization)
    first = search(sports_catalogue, 'inexistente', 'team')
    assert first['complete'] and first['items'] == []
    assert len(normalized) == total + 2
    assert normalized.count('España') == normalized.count('Liga Única') == 1
    with sqlite3.connect(sports_catalogue) as conn:
        conn.execute("UPDATE teams SET name='Inexistente encontrado' WHERE key='999'")
    second = search(sports_catalogue, 'inexistente', 'team')
    assert second['complete'] and [item['value'] for item in second['items']] == ['@team:999']


def test_sql_has_no_python_udf_or_entity_sort_before_delivering_rows(sports_catalogue, monkeypatch):
    connect = sqlite3.connect
    statements = []

    class Connection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            statements.append(sql)
            return super().execute(sql, *args, **kwargs)

        def create_function(self, *args, **kwargs):
            pytest.fail('Per-row SQL to Python normalization was reintroduced')

    monkeypatch.setattr(sqlite3, 'connect', lambda *args, **kwargs: connect(*args, **kwargs, factory=Connection))
    before = sports_catalogue.read_bytes()
    assert search(sports_catalogue)['complete']
    assert sports_catalogue.read_bytes() == before
    assert all('ORDER BY' not in sql for sql in statements if 'FROM teams ' in sql or 'FROM competitions ' in sql)
    assert 'BEGIN' in statements
