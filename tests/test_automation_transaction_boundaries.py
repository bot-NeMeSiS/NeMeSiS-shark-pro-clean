"""Temporary SQLite only; callbacks are synthetic, never providers or Telegram."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3
import secrets
import threading

import pytest
from engines import daily_automation_engine as daily
from engines import api_usage_guard_engine as usage


@pytest.fixture
def store(tmp_path, monkeypatch):
    db = str(tmp_path / 'synthetic.sqlite')
    daily.ensure_automation_schema(db)
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute('CREATE TABLE synthetic_effects(value TEXT)')
    # A fixed Madrid day keeps dedupe and quota windows deterministic.
    now = datetime(2026, 9, 21, 14, 0, tzinfo=daily.TZ)
    monkeypatch.setattr(daily, 'madrid_now', lambda: now)
    monkeypatch.setattr(usage, 'madrid_now', lambda: now)
    return db


def query(db, sql, args=()):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute(sql, args).fetchall()


def run(db, callbacks, **kwargs):
    return daily.run_master_tick(db, 'SIMULATED_QA', env={'AUTOMATION_SECRET': secrets.token_urlsafe(32)}, callbacks=callbacks, **kwargs)


def writer(db, value='synthetic'):
    def write():
        with closing(sqlite3.connect(db, timeout=.15)) as conn, conn:
            conn.execute('INSERT INTO synthetic_effects VALUES (?)', (value,))
        return {'ok': True, 'external_calls': 0}
    return write


@pytest.mark.parametrize('journal', ['DELETE', 'WAL'])
def test_callback_can_open_its_own_write_transaction(store, monkeypatch, journal):
    with closing(sqlite3.connect(store)) as conn:
        conn.execute('PRAGMA journal_mode=' + journal)
    monkeypatch.setattr(daily, 'jobs_due', lambda *a, **k: ['synthetic_writer'])
    result = run(store, {'synthetic_writer': writer(store)})
    assert result['ok'] and len(result['jobs_run']) == 1
    assert query(store, 'SELECT value FROM synthetic_effects') == [('synthetic',)]


def test_provider_guard_reservation_commits_before_callback(store, monkeypatch):
    monkeypatch.setattr(daily, 'jobs_due', lambda *a, **k: ['morning_fixtures_sync'])
    def callback():
        assert query(store, "SELECT estimated_calls FROM api_usage_guard WHERE status='ALLOWED'") == [(6,)]
        assert query(store, 'SELECT COUNT(*) FROM automation_dedupe') == [(1,)]
        return writer(store)()
    result = run(store, {'morning_fixtures_sync': callback})
    assert result['ok'] and result['api_calls_estimated'] == 6


@pytest.mark.parametrize('force', [False, True])
def test_dry_run_does_not_consume_dedupe_or_budget(store, monkeypatch, force):
    monkeypatch.setattr(daily, 'jobs_due', lambda *a, **k: ['morning_fixtures_sync'])
    def forbidden():
        pytest.fail('A dry run must not execute a callback')
    result = run(store, {'morning_fixtures_sync': forbidden}, dry_run=True, force=force)
    assert result['ok'] and result['jobs_skipped'][0]['reason'] == 'dry_run'
    assert query(store, 'SELECT COUNT(*) FROM automation_dedupe') == [(0,)]
    assert query(store, 'SELECT COUNT(*) FROM api_usage_guard') == [(0,)]
    assert query(store, 'SELECT status FROM automation_job_runs') == [('DRY_RUN',)]
    assert run(store, {'morning_fixtures_sync': writer(store)})['ok']
    assert len(query(store, 'SELECT * FROM synthetic_effects')) == 1


def test_dry_run_does_not_overwrite_existing_real_claim(store, monkeypatch):
    monkeypatch.setattr(daily, 'jobs_due', lambda *a, **k: ['telegram_daily_top_agenda'])
    assert run(store, {'telegram_daily_top_agenda': writer(store)})['ok']
    before = query(store, 'SELECT * FROM automation_dedupe')
    run(store, {}, dry_run=True)
    assert query(store, 'SELECT * FROM automation_dedupe') == before


def test_daily_claim_is_committed_once_across_concurrent_callers(store, monkeypatch):
    monkeypatch.setattr(daily, 'jobs_due', lambda *a, **k: ['telegram_daily_top_agenda'])
    barrier = threading.Barrier(6)
    count, lock = [], threading.Lock()
    def callback():
        with lock:
            count.append(1)
        return writer(store)()
    def invoke(_):
        barrier.wait(timeout=5)
        return run(store, {'telegram_daily_top_agenda': callback})
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(invoke, range(6)))
    assert len(count) == 1
    assert sum(len(r['jobs_run']) for r in results) == 1
    assert sum(len(r['jobs_skipped']) for r in results) == 5
    assert all(r['ok'] for r in results)
    assert len(query(store, 'SELECT * FROM synthetic_effects')) == 1


def test_unrelated_writer_completes_while_callback_waits(store, monkeypatch):
    monkeypatch.setattr(daily, 'jobs_due', lambda *a, **k: ['telegram_daily_top_agenda'])
    entered, release = threading.Event(), threading.Event()
    def callback():
        entered.set()
        assert release.wait(timeout=5)
        return {'ok': True}
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run, store, {'telegram_daily_top_agenda': callback})
        try:
            assert entered.wait(timeout=5)
            writer(store, 'unrelated')()
            assert not future.done()
        finally:
            release.set()
        assert future.result(timeout=5)['ok']


def test_failed_callback_keeps_daily_claim_and_atomic_audit(store, monkeypatch):
    monkeypatch.setattr(daily, 'jobs_due', lambda *a, **k: ['telegram_daily_top_agenda'])
    calls = []
    def fail():
        calls.append(1)
        raise RuntimeError('synthetic_failure')
    first = run(store, {'telegram_daily_top_agenda': fail})
    assert not first['ok']
    assert first['jobs_failed'] == [{'job_key': 'telegram_daily_top_agenda', 'error': 'synthetic_failure'}]
    second = run(store, {'telegram_daily_top_agenda': fail})
    assert second['jobs_skipped'][0]['reason'] == 'dedupe_already_done'
    assert len(calls) == 1
    assert query(store, 'SELECT COUNT(*) FROM automation_health_events') == [(1,)]


def test_completed_job_evidence_survives_later_callback_failure(store, monkeypatch):
    monkeypatch.setattr(daily, 'jobs_due', lambda *a, **k: ['first', 'second'])
    def second():
        assert query(store, "SELECT status FROM automation_job_runs WHERE job_key='first'") == [('OK',)]
        raise RuntimeError('synthetic_second_failure')
    result = run(store, {'first': writer(store), 'second': second})
    assert not result['ok'] and len(result['jobs_run']) == 1
    assert query(store, 'SELECT status FROM automation_job_runs ORDER BY id') == [('OK',), ('FAILED',)]


def test_audit_failure_does_not_retry_or_release_durable_claim(store, monkeypatch):
    monkeypatch.setattr(daily, 'jobs_due', lambda *a, **k: ['telegram_daily_top_agenda'])
    recorder = daily._record_run
    monkeypatch.setattr(daily, '_record_run', lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError('synthetic_audit_failure')))
    with pytest.raises(sqlite3.OperationalError):
        run(store, {'telegram_daily_top_agenda': writer(store)})
    monkeypatch.setattr(daily, '_record_run', recorder)
    result = run(store, {'telegram_daily_top_agenda': writer(store)})
    assert result['jobs_skipped'][0]['reason'] == 'dedupe_already_done'
    assert len(query(store, 'SELECT * FROM synthetic_effects')) == 1


def test_budget_rejection_never_calls_callback(store, monkeypatch):
    monkeypatch.setattr(daily, 'jobs_due', lambda *a, **k: ['morning_fixtures_sync'])
    result = daily.run_master_tick(store, 'SIMULATED_QA', env={'API_FOOTBALL_DAILY_CALL_BUDGET': '0'},
                                   callbacks={'morning_fixtures_sync': lambda: pytest.fail('budget bypass')})
    assert result['api_calls_estimated'] == 0
    assert result['jobs_skipped'][0]['reason'] == 'api_budget_exceeded'


def test_existing_force_semantics_are_not_silently_changed(store, monkeypatch):
    monkeypatch.setattr(daily, 'jobs_due', lambda *a, **k: ['telegram_daily_top_agenda'])
    for _ in range(2):
        assert run(store, {'telegram_daily_top_agenda': writer(store)}, force=True)['ok']
    assert len(query(store, 'SELECT * FROM synthetic_effects')) == 2


def test_master_connections_close_even_on_audit_error(store, monkeypatch):
    original = sqlite3.connect
    retained = []
    def track(*args, **kwargs):
        conn = original(*args, **kwargs)
        retained.append(conn)
        return conn
    monkeypatch.setattr(daily.sqlite3, 'connect', track)
    monkeypatch.setattr(daily, 'jobs_due', lambda *a, **k: ['test'])
    monkeypatch.setattr(daily, '_record_run', lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError('synthetic')))
    with pytest.raises(sqlite3.OperationalError):
        run(store, {'test': lambda: {'ok': True}})
    assert retained
    for conn in retained:
        with pytest.raises(sqlite3.ProgrammingError, match='closed'):
            conn.execute('SELECT 1')


def test_dry_run_does_not_claim_already_completed_job_would_run(store, monkeypatch):
    monkeypatch.setattr(daily, 'jobs_due', lambda *a, **k: ['telegram_daily_top_agenda'])
    run(store, {'telegram_daily_top_agenda': writer(store)})
    result = run(store, {}, dry_run=True)
    assert result['jobs_skipped'][0]['would_run'] is False
    assert result['jobs_skipped'][0]['reason'] == 'dedupe_already_done'
