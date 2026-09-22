"""No providers or production DB: deterministic cache concurrency contracts."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta
import threading
from zoneinfo import ZoneInfo

import pytest
from engines import v934_realtime_sports_engine as engine
from engines.snapshot_copy_engine import clone_snapshot


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch):
    monkeypatch.setattr(engine, '_CACHE', {})
    monkeypatch.setattr(engine, '_CACHE_BUILD_LOCKS', {})
    monkeypatch.setattr(engine, '_CACHE_GENERATIONS', {})


def test_cache_keeps_builder_and_callers_independent():
    row = {'id': 'test', 'score': [0, 1]}
    original = {'a': row, 'b': row, 'clock': '2026-09-21T10:00:00+02:00'}
    first, status = engine.cached_realtime_snapshot('scope:one', lambda: original)
    assert status == 'refreshed' and first['a'] is first['b']
    original['a']['score'][0] = 9
    first['a']['score'][0] = 7
    second, status = engine.cached_realtime_snapshot('scope:one', lambda: pytest.fail('cache miss'))
    assert status == 'hit' and second['a']['score'] == [0, 1]
    second['b']['score'].append(2)
    third, _ = engine.cached_realtime_snapshot('scope:one', lambda: {})
    assert third['a']['score'] == [0, 1] and third['clock'] == original['clock']


def test_single_flight_preserved_for_concurrent_miss():
    gate = threading.Barrier(6)
    release, entered = threading.Event(), threading.Event()
    builds = []
    def build():
        builds.append(1); entered.set()
        assert release.wait(3)
        return {'data': [0]}
    def read():
        gate.wait(timeout=3)
        return engine.cached_realtime_snapshot('common', build)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(read) for _ in range(6)]
        try:
            assert entered.wait(3)
        finally:
            release.set()
        results = [future.result(timeout=3) for future in futures]
    assert len(builds) == 1
    assert sorted(status for _, status in results) == ['hit'] * 5 + ['refreshed']
    results[0][0]['data'][0] = 8
    assert all(value['data'] == [0] for value, _ in results[1:])


@pytest.mark.parametrize('phase', ['cache_hit', 'store', 'fallback'])
def test_copy_of_one_key_does_not_hold_global_index_lock(monkeypatch, phase):
    if phase != 'store':
        engine.cached_realtime_snapshot('slow', lambda: {'large': True})
    engine.cached_realtime_snapshot('fast', lambda: {'fast': True})
    entered, release = threading.Event(), threading.Event()
    def paused_copy(value):
        if value.get('large'):
            entered.set()
            assert release.wait(3)
        return clone_snapshot(value)
    monkeypatch.setattr(engine, 'clone_snapshot', paused_copy)
    def fail():
        raise RuntimeError('local simulated builder failure')
    def slow():
        return engine.cached_realtime_snapshot('slow', fail if phase == 'fallback' else lambda: {'large': True}, force=phase == 'fallback')
    with ThreadPoolExecutor(max_workers=2) as pool:
        slow_future = pool.submit(slow)
        try:
            assert entered.wait(3)
            # Event ordering, not a benchmark threshold: this must finish BEFORE
            # allowing the deliberately paused copy on another key to continue.
            fast_future = pool.submit(engine.cached_realtime_snapshot, 'fast', lambda: {})
            assert fast_future.result(timeout=1)[0] == {'fast': True}
        finally:
            release.set()
        assert slow_future.result(timeout=3)[0]['large'] is True


@pytest.mark.parametrize('prefix', ['', 'sports:'])
@pytest.mark.parametrize('seeded', [False, True])
def test_invalidation_during_build_cannot_republish_old_cache(prefix, seeded):
    key = 'sports:snapshot'
    if seeded:
        engine.cached_realtime_snapshot(key, lambda: {'revision': 0})
    entered, release = threading.Event(), threading.Event()
    def old_builder():
        entered.set()
        assert release.wait(3)
        return {'revision': 1}
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(engine.cached_realtime_snapshot, key, old_builder, force=True)
        try:
            assert entered.wait(3)
            engine.invalidate_realtime_cache(prefix)
        finally:
            release.set()
        # A caller already in flight can finish its point-in-time view.
        assert pending.result(timeout=3)[0]['revision'] == 1
    assert key not in engine._CACHE
    current, status = engine.cached_realtime_snapshot(key, lambda: {'revision': 2})
    assert status == 'refreshed' and current['revision'] == 2
    assert engine.cached_realtime_snapshot(key, lambda: {})[0]['revision'] == 2


def test_targeted_invalidation_leaves_other_build_eligible():
    entered, release = threading.Event(), threading.Event()
    def build():
        entered.set(); assert release.wait(3); return {'revision': 1}
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(engine.cached_realtime_snapshot, 'other', build)
        try:
            assert entered.wait(3)
            engine.invalidate_realtime_cache('sports:')
        finally:
            release.set()
        pending.result(timeout=3)
    assert engine.cached_realtime_snapshot('other', lambda: {})[1] == 'hit'


def test_fallback_is_isolated_and_never_renews_expiry(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(engine.time, 'monotonic', lambda: clock[0])
    engine.cached_realtime_snapshot('sample', lambda: {'rows': [0], 'provider_at': 'observed'}, ttl_seconds=5)
    clock[0] = 106.0
    def fail(): raise RuntimeError('synthetic offline')
    fallback, status = engine.cached_realtime_snapshot('sample', fail)
    assert status == 'stale_fallback'
    fallback['rows'][0] = 9
    assert engine._CACHE['sample']['payload']['rows'] == [0]
    assert engine._CACHE['sample']['expires_at'] == 105.0
    assert fallback['provider_at'] == 'observed'
    assert engine.cached_realtime_snapshot('absent', fail)[1] == 'safe_empty'


@pytest.mark.parametrize('ttl,expected', [(1, 5), (15, 15), (600, 300)])
def test_existing_ttl_clamp_and_force_preserved(monkeypatch, ttl, expected):
    clock = [100.0]
    monkeypatch.setattr(engine.time, 'monotonic', lambda: clock[0])
    first, _ = engine.cached_realtime_snapshot('x', lambda: {'v': 1}, ttl_seconds=ttl)
    assert engine._CACHE['x']['expires_at'] == 100 + expected
    clock[0] += expected - .01
    assert engine.cached_realtime_snapshot('x', lambda: {'v': 2})[0]['v'] == 1
    assert engine.cached_realtime_snapshot('x', lambda: {'v': 3}, force=True)[0]['v'] == 3


NOW = datetime(2026, 9, 21, 20, 0, tzinfo=ZoneInfo('Europe/Madrid'))


def match(identifier='qa', **extra):
    return dict(id=identifier, home_team='Local QA', away_team='Visitante QA',
        competition_name='Liga QA', match_date=NOW.date().isoformat(), kickoff_time='19:20',
        source='TheSportsDB API', last_synced_at=NOW.isoformat(), status='LIVE', minute='40',
        home_score=0, away_score=1, **extra)


def test_overlapping_collections_only_normalize_first_valid_identity(monkeypatch):
    real = engine.normalize_match
    called = []
    def observed(row, now):
        called.append(row)
        return real(row, now)
    monkeypatch.setattr(engine, 'normalize_match', observed)
    rows = [match('qa-' + str(i)) for i in range(25)]
    summary = {'valid_matches_today': rows, 'valid_upcoming_matches': deepcopy(rows), 'finished_matches': deepcopy(rows)}
    snapshot = engine.build_realtime_snapshot(summary, NOW)
    assert len(called) == 25 and snapshot['counts']['live'] == 25
    assert snapshot['matches'][0]['home_score'] == 0


def test_invalid_first_row_does_not_suppress_valid_duplicate():
    invalid = {**match(), 'source': ''}
    valid = match()
    snapshot = engine.build_realtime_snapshot({'valid_matches_today': [invalid], 'valid_upcoming_matches': [valid]}, NOW)
    assert len(snapshot['matches']) == 1 and snapshot['matches'][0]['source'] == valid['source']


@pytest.mark.parametrize('change', [{'id': '  qa  '}, {'id': '', 'match_id': 'qa'}, {'id': '', 'external_id': 'qa'}])
def test_same_normalized_identifier_preserves_original_precedence(change):
    first = match()
    later = {**match(), **change, 'home_score': 8}
    snapshot = engine.build_realtime_snapshot({'valid_matches_today': [first], 'valid_upcoming_matches': [later]}, NOW)
    assert len(snapshot['matches']) == 1 and snapshot['matches'][0]['home_score'] == 0


def test_final_and_stale_policy_unchanged_without_advancing_provider_clock():
    live = match()
    summary = {'valid_matches_today': [live], 'valid_upcoming_matches': [live]}
    now_snapshot = engine.build_realtime_snapshot(summary, NOW)
    late_snapshot = engine.build_realtime_snapshot(summary, NOW + timedelta(hours=1))
    assert now_snapshot['counts']['live'] == 1
    assert late_snapshot['counts']['live'] == 0
    assert late_snapshot['stale_live'][0]['updated_at'] == live['last_synced_at']
    finished = {**live, 'status': 'FT', 'minute': ''}
    result = engine.build_realtime_snapshot({'finished_matches': [finished]}, NOW)
    assert result['finished'][0]['is_finished'] and not result['finished'][0]['is_live']


def test_separate_scopes_and_database_keys_do_not_share_data():
    a, _ = engine.cached_realtime_snapshot('db-a:public', lambda: {'data': ['A']})
    b, _ = engine.cached_realtime_snapshot('db-b:public', lambda: {'data': ['B']})
    a['data'].append('private-local-decoration')
    assert b['data'] == ['B']
    engine.invalidate_realtime_cache('db-a:')
    assert engine.cached_realtime_snapshot('db-b:public', lambda: {})[0] == b


def test_real_request_contexts_never_reuse_mutated_summary(app_module, monkeypatch):
    import socket
    from flask import g, session
    attempts = []
    def forbidden(*args, **kwargs):
        attempts.append('external-network'); raise AssertionError('no provider calls')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    clock = datetime.now(ZoneInfo('Europe/Madrid'))
    row = {**match(), 'status': 'FT', 'minute': '', 'last_synced_at': clock.isoformat()}
    summary = {'all_valid_matches': [row], 'valid_matches_today': [row],
        'valid_upcoming_matches': [], 'finished_matches': [row], 'valid_live_events': [],
        'valid_active_picks': [], 'incomplete_matches': [], 'all_picks': [],
        'provider_status': 'observed_test_store', 'last_sync': clock.isoformat()}
    monkeypatch.setattr(app_module, '_build_public_home_sports_summary', lambda: summary)
    with app_module.app.test_request_context('/live'):
        session['qa_identity'] = 'client-one'
        first = app_module.get_public_home_sports_summary()
        assert first is app_module.get_public_home_sports_summary()
        first['all_valid_matches'][0]['private_note'] = session['qa_identity']
        assert g.v935_public_sports_summary is first
    with app_module.app.test_request_context('/calendar'):
        session['qa_identity'] = 'client-two'
        second = app_module.get_public_home_sports_summary()
        assert second is not first
        assert 'private_note' not in second['all_valid_matches'][0]
    assert 'private_note' not in row and attempts == []


def _benchmark_setup_node():
    import ast
    from pathlib import Path
    source = Path(__file__).resolve().parents[1] / 'tools/benchmark_snapshot_reads.py'
    nodes = ast.parse(source.read_text(encoding='utf-8')).body
    return next(node for node in nodes if isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and ast.unparse(node.value.func) == 'os.environ.update')


def test_benchmark_uses_generated_credentials_not_fixed_literals():
    import ast
    setup = _benchmark_setup_node().value
    arguments = {keyword.arg: keyword.value for keyword in setup.keywords}
    for name in ('SECRET_KEY', 'ADMIN_PASSWORD', 'AUTOMATION_SECRET'):
        value = arguments[name]
        assert isinstance(value, ast.Call)
        assert ast.unparse(value.func) == 'secrets.token_urlsafe'
        assert ast.literal_eval(value.args[0]) >= 32


def test_benchmark_setup_is_ephemeral_and_does_not_reuse_existing_credentials(tmp_path):
    import ast
    import secrets
    from pathlib import Path
    from types import SimpleNamespace
    setup = ast.Module(body=[_benchmark_setup_node()], type_ignores=[])
    ast.fix_missing_locations(setup)
    code = compile(setup, 'benchmark-isolated-setup', 'exec')
    names = ('SECRET_KEY', 'ADMIN_PASSWORD', 'AUTOMATION_SECRET')
    generated = []
    for _ in range(2):
        # Execute only the environment assignment against a private dictionary,
        # never the benchmark, app import or actual process environment.
        isolated = SimpleNamespace(environ={name: 'existing-test-value' for name in names})
        exec(code, {'os': isolated, 'TEMP': SimpleNamespace(name=str(tmp_path)),
                    'Path': Path, 'secrets': secrets})
        generated.extend(isolated.environ[name] for name in names)
        assert isolated.environ['DB_PATH'] == str(tmp_path / 'qa.sqlite')
        assert isolated.environ['BACKGROUND_JOBS_ENABLED'] == 'false'
        assert isolated.environ['AUTO_GENERATE_PICKS'] == 'false'
        assert isolated.environ['AUTO_SEND_TELEGRAM_PICKS'] == 'false'
    assert len(set(generated)) == 6 and all(len(value) >= 40 for value in generated)
