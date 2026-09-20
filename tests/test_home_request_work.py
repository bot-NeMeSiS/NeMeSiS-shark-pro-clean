"""Bounded repeated Home work without cross-request/user/DB state."""
import copy

import pytest


def test_home_queries_once_and_returns_independent_values(app_module, monkeypatch):
    calls = []
    original = app_module.rows

    def counted(query, params=()):
        calls.append((query, tuple(params)))
        return original(query, params)

    monkeypatch.setattr(app_module, 'rows', counted)
    with app_module.app.test_request_context('/app'):
        first = app_module.get_upcoming_matches(days=21, limit=300)
        expected = copy.deepcopy(first)
        first.clear()
        assert app_module.get_upcoming_matches(days=21, limit=300) == expected
        app_module.get_favorites(user_id='qa-one')
        app_module.get_favorites(user_id='qa-one')
        fixture = {'id': 'local-match-2'}
        app_module.match_timeline(fixture)
        app_module.match_timeline(fixture)
    for marker in ('FROM matches', 'FROM favorites', 'FROM match_timeline'):
        assert len([q for q, _ in calls if marker in q]) == 1, marker


def test_home_candidate_enrichment_is_not_repeated(app_module, monkeypatch):
    calls = []
    original = app_module.annotate_match
    def counted(*args, **kwargs):
        calls.append(args[0]['id'])
        return original(*args, **kwargs)
    monkeypatch.setattr(app_module, 'annotate_match', counted)
    fixture = {'id':'qa-candidate','home_team':'Local QA','away_team':'Visitante QA','status':'NS'}
    monkeypatch.setattr(app_module, 'get_upcoming_matches', lambda *args, **kwargs: [dict(fixture)])
    monkeypatch.setattr(app_module, 'canonical_match_status', lambda item: {'is_upcoming': True})
    with app_module.app.test_request_context('/app'):
        first = app_module.pick_candidate_matches()
        assert first
        second = app_module.pick_candidate_matches()
        assert first == second and first is not second
    assert len(calls) == len(first)


def test_home_favorites_are_scoped_by_user_db_and_request(app_module, monkeypatch):
    calls = []
    def read(query, params=()):
        calls.append((app_module.DB_PATH, tuple(params)))
        return [{'value': params[0], 'kind': 'team'}]
    monkeypatch.setattr(app_module, 'rows', read)
    original_db = app_module.DB_PATH
    for _ in range(2):
        with app_module.app.test_request_context('/app'):
            assert app_module.get_favorites(user_id='a')[0]['value'] == 'a'
            assert app_module.get_favorites(user_id='b')[0]['value'] == 'b'
            app_module.get_favorites(user_id='a')[0]['value'] = 'mutated'
            assert app_module.get_favorites(user_id='a')[0]['value'] == 'a'
            monkeypatch.setattr(app_module, 'DB_PATH', str(original_db) + '.other')
            app_module.get_favorites(user_id='a')
            monkeypatch.setattr(app_module, 'DB_PATH', original_db)
    assert len(calls) == 6


@pytest.mark.parametrize('path,method', [('/app','POST'), ('/favorites','GET')])
def test_mutating_and_other_routes_do_not_reuse_home_reads(app_module, monkeypatch, path, method):
    calls = []
    monkeypatch.setattr(app_module, 'rows', lambda *args: calls.append(args) or [])
    with app_module.app.test_request_context(path, method=method):
        app_module.get_favorites(user_id='a')
        app_module.get_favorites(user_id='a')
    assert len(calls) == 2


def test_timeline_fallback_tracks_input_even_when_database_is_empty(app_module, monkeypatch):
    calls = []
    monkeypatch.setattr(app_module, 'rows', lambda *args: calls.append(args) or [])
    monkeypatch.setattr(app_module, 'fallback_timeline', lambda match: [match['status']])
    with app_module.app.test_request_context('/app'):
        assert app_module.match_timeline({'id':'qa', 'status':'NS'}) == ['NS']
        assert app_module.match_timeline({'id':'qa', 'status':'FT'}) == ['FT']
    assert len(calls) == 1


def test_match_hub_cache_does_not_cross_users_or_favorite_changes(app_module, monkeypatch):
    user = {'id':'hub-user-a', 'role':'FREE', 'membership':'FREE'}
    favorites = []
    monkeypatch.setattr(app_module, 'current_session_user', lambda: user)
    monkeypatch.setattr(app_module, 'get_favorites', lambda *a, **kw: copy.deepcopy(favorites))
    keys = []
    original = app_module.cache_get
    def read(key):
        if key.startswith('match-hub:'):
            keys.append(key)
        return original(key)
    monkeypatch.setattr(app_module, 'cache_get', read)
    for identifier in ('hub-user-a','hub-user-b','hub-user-b'):
        user['id'] = identifier
        if len(keys) == 2:
            favorites.append({'kind':'match','value':'local-match-2'})
        with app_module.app.test_request_context('/app'):
            app_module.match_hub()
    assert len(set(keys)) == 3


@pytest.mark.parametrize('reader', ['get_matches', 'get_upcoming_matches', 'pick_candidate_matches'])
def test_home_cached_values_equal_uncached_values(app_module, reader):
    func = getattr(app_module, reader)
    with app_module.app.test_request_context('/app'):
        expected = func.__wrapped__()
        assert func() == expected
        assert func() == expected


def test_home_normalization_reuses_text_without_changing_unicode(app_module, monkeypatch):
    calls = []
    original = app_module.unicodedata.normalize
    def counted(*args):
        calls.append(args)
        return original(*args)
    monkeypatch.setattr(app_module.unicodedata, 'normalize', counted)
    for _ in range(2):
        with app_module.app.test_request_context('/app'):
            assert app_module.normalized_label('  Espa\u00f1a  FC ') == 'espana fc'
            assert app_module.normalized_label('  Espa\u00f1a  FC ') == 'espana fc'
    assert len(calls) == 2


def test_home_timeline_batches_preserve_per_match_limit_and_fallback(app_module,monkeypatch):
    ids=['batch-home-qa-'+str(i) for i in range(24)]
    with app_module.db() as conn:
        for match_id in ids:
            for i in range(23):
                conn.execute('INSERT OR REPLACE INTO match_timeline(id,match_id,created_at) VALUES(?,?,?)',
                             (match_id+'-'+str(i),match_id,f'2026-09-19T12:{i:02}:00'))
    matches=[{'id':value} for value in ids]
    expected=[app_module.match_timeline(match) for match in matches]
    calls=[]
    original=app_module.rows
    def counted(query,params=()):
        if 'FROM match_timeline' in query: calls.append(query)
        return original(query,params)
    monkeypatch.setattr(app_module,'rows',counted)
    with app_module.app.test_request_context('/app'):
        app_module._prefetch_home_timelines(matches)
        assert [app_module.match_timeline(match) for match in matches]==expected
        assert len(calls)==1
        assert all(len(events)==20 for events in expected)
        app_module.match_timeline(matches[0]).clear()
        assert app_module.match_timeline(matches[0])==expected[0]

