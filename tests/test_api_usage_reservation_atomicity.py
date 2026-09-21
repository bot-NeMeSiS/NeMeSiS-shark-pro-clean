"""Reservation safety on temporary SQLite; no real API credits or network."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
import sqlite3
import threading

import pytest
from engines import api_usage_guard_engine as guard


@pytest.fixture
def store(tmp_path, monkeypatch):
    db = str(tmp_path / 'quota.sqlite')
    with closing(sqlite3.connect(db)) as conn, conn:
        guard.ensure_api_usage_guard_schema(conn)
    monkeypatch.setattr(guard, 'madrid_now', lambda: datetime(2026, 9, 21, 23, 50, tzinfo=guard.TZ))
    return db


def rows(db):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute('SELECT provider,window_key,estimated_calls,status FROM api_usage_guard ORDER BY id').fetchall()


@pytest.mark.parametrize('bad', [-1, 1.5, '2', None, True, False])
def test_invalid_estimate_never_grants_or_changes_budget(store, bad):
    result = guard.allow_api_job(store, 'api_football', 'test', bad)
    assert not result['ok'] and result['reason'] == 'invalid_api_estimate'
    assert rows(store) == []


def test_unknown_provider_never_grants(store):
    result = guard.allow_api_job(store, 'unknown', 'test', 0)
    assert not result['ok'] and rows(store) == []


def test_budget_and_keys_use_explicit_env_not_process_env(store, monkeypatch):
    monkeypatch.setenv('API_FOOTBALL_DAILY_CALL_BUDGET', '100')
    result = guard.allow_api_job(store, 'api_football', 'test', 2, env={'API_FOOTBALL_DAILY_CALL_BUDGET': '1'})
    assert result['budget'] == 1 and not result['ok']
    assert rows(store)[0][2:] == (0, 'BLOCKED')


def test_reservations_are_atomic_across_simultaneous_callers(store):
    barrier = threading.Barrier(12)
    def reserve(index):
        barrier.wait(timeout=5)
        return guard.allow_api_job(store, 'api_football', f'qa-{index}', 1,
                                   env={'API_FOOTBALL_DAILY_CALL_BUDGET': '5'})
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(reserve, range(12)))
    assert sum(result['ok'] for result in results) == 5
    assert sum(row[2] for row in rows(store)) == 5
    assert len(rows(store)) == 12
    assert sum(row[3] == 'BLOCKED' for row in rows(store)) == 7


def test_rejections_do_not_consume_estimated_budget(store):
    env = {'API_FOOTBALL_DAILY_CALL_BUDGET': '3'}
    assert not guard.allow_api_job(store, 'api_football', 'too-large', 4, env)['ok']
    assert guard.allow_api_job(store, 'api_football', 'fits', 3, env)['ok']
    assert not guard.allow_api_job(store, 'api_football', 'exhausted', 1, env)['ok']
    assert [r[2] for r in rows(store)] == [0, 3, 0]
    snapshot = guard.api_usage_snapshot(store, env)
    assert snapshot['used_estimated']['api_football'] == 3
    assert snapshot['remaining_estimated']['api_football'] == 0


def test_legacy_blocked_or_negative_rows_do_not_spend_or_create_credit(store):
    with closing(sqlite3.connect(store)) as conn, conn:
        for estimate, status in [(100, 'BLOCKED'), (-100, 'ALLOWED'), (2, 'ALLOWED')]:
            conn.execute('INSERT INTO api_usage_guard(provider,window_key,estimated_calls,status) VALUES (?,?,?,?)',
                         ('api_football', '2026-09-21', estimate, status))
    result = guard.allow_api_job(store, 'api_football', 'fits', 1, {'API_FOOTBALL_DAILY_CALL_BUDGET': '3'})
    assert result['ok'] and result['remaining_before'] == 1
    assert not guard.allow_api_job(store, 'api_football', 'exhausted', 1, {'API_FOOTBALL_DAILY_CALL_BUDGET': '3'})['ok']


def test_locked_storage_is_not_an_authorization(store, monkeypatch):
    original = sqlite3.connect
    def fast(*args, **kwargs):
        kwargs['timeout'] = .08
        return original(*args, **kwargs)
    with closing(original(store)) as held:
        held.execute('BEGIN IMMEDIATE')
        monkeypatch.setattr(guard.sqlite3, 'connect', fast)
        result = guard.allow_api_job(store, 'api_football', 'test', 1)
        assert not result['ok'] and result['reason'] == 'api_budget_storage_unavailable'
        assert result['remaining_before'] is None
        held.rollback()
    assert rows(store) == []


def test_unavailable_storage_has_no_exception_details(tmp_path):
    result = guard.allow_api_job(str(tmp_path / 'missing' / 'private-db-name'), 'api_football', 'test', 1)
    assert not result['ok']
    assert 'private-db-name' not in str(result)


def test_failed_commit_never_authorizes_and_rolls_back(store, monkeypatch):
    original = sqlite3.connect
    retained = []
    class FailingCommit(sqlite3.Connection):
        def __exit__(self, kind, value, trace):
            if self.in_transaction:
                self.rollback()
                raise sqlite3.OperationalError('synthetic commit failure')
            return super().__exit__(kind, value, trace)
    def connection(*args, **kwargs):
        kwargs['factory'] = FailingCommit
        conn = original(*args, **kwargs)
        retained.append(conn)
        return conn
    monkeypatch.setattr(guard.sqlite3, 'connect', connection)
    result = guard.allow_api_job(store, 'api_football', 'test', 1)
    assert not result['ok'] and result['reason'] == 'api_budget_storage_unavailable'
    with closing(original(store)) as conn:
        assert conn.execute('SELECT COUNT(*) FROM api_usage_guard').fetchone()[0] == 0
    for conn in retained:
        with pytest.raises(sqlite3.ProgrammingError, match='closed'):
            conn.execute('SELECT 1')


def test_quota_day_is_madrid_and_resets_at_midnight(store, monkeypatch):
    env = {'API_FOOTBALL_DAILY_CALL_BUDGET': '1'}
    assert guard.allow_api_job(store, 'api_football', 'before', 1, env)['ok']
    monkeypatch.setattr(guard, 'madrid_now', lambda: datetime(2026, 9, 22, 0, 1, tzinfo=guard.TZ))
    assert guard.allow_api_job(store, 'api_football', 'after', 1, env)['ok']
    assert [row[1] for row in rows(store)] == ['2026-09-21', '2026-09-22']


def test_zero_cost_is_allowed_but_does_not_change_usage(store):
    result = guard.allow_api_job(store, 'api_football', 'local-only', 0, {'API_FOOTBALL_DAILY_CALL_BUDGET': '0'})
    assert result['ok'] and rows(store)[0][2] == 0


def test_reservation_limit_holds_across_independent_processes(store):
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    script = '''
import json,sys
from datetime import datetime
from engines import api_usage_guard_engine as g
g.madrid_now=lambda: datetime(2026,9,21,23,50,tzinfo=g.TZ)
print(json.dumps([g.allow_api_job(sys.argv[1],'api_football','child',1,{'API_FOOTBALL_DAILY_CALL_BUDGET':'5'})['ok'] for _ in range(3)]))
'''
    root = Path(__file__).resolve().parents[1]
    env = {key: value for key, value in os.environ.items() if key in {'PATH', 'HOME', 'LANG', 'LD_LIBRARY_PATH', 'SYSTEMROOT'}}
    env['PYTHONPATH'] = str(root)
    processes = [subprocess.Popen([sys.executable, '-c', script, store], cwd=root, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(4)]
    try:
        accepted = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=12)
            assert process.returncode == 0, stderr
            accepted.extend(json.loads(stdout))
        assert sum(accepted) == 5
        assert sum(row[2] for row in rows(store)) == 5
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
