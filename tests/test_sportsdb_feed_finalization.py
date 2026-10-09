"""Local fault injection: a feed receipt agrees with durable rows and calls."""
import json
import sqlite3

import pytest

from engines.cron_request_budget import CronRequestBudget, CronTimeBudget, request_timeout
from test_sportsdb_team_batch import prepare


@pytest.fixture
def feed(app_module, tmp_path, monkeypatch):
    app = app_module
    path = prepare(app, tmp_path, monkeypatch)
    original_fetch = app.fetch_sportsdb_feed_events
    monkeypatch.setattr(app, 'fetch_sportsdb_feed_events',
                        lambda **kwargs: (original_fetch(**kwargs)[0], [], 7))
    return app, path


def receipt(path):
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        log = dict(conn.execute('SELECT * FROM api_sync_logs ORDER BY started_at DESC LIMIT 1').fetchone())
        state = conn.execute("SELECT value_json FROM automation_state WHERE key='sportsdb_feed_sync'").fetchone()
        return dict(log=log, state=json.loads(state[0]) if state else None,
                    matches=conn.execute('SELECT count(*) FROM matches').fetchone()[0],
                    teams=conn.execute('SELECT count(*) FROM teams').fetchone()[0],
                    imports=[dict(row) for row in conn.execute('SELECT * FROM imports')])


def assert_closed(stored, count, calls, status):
    assert stored['log']['status'] == status
    assert stored['log']['finished_at']
    assert stored['log']['total_items'] == count
    assert stored['state']['processed'] == count
    assert stored['state']['external_calls'] == calls


def test_success_receipt_and_rows_share_one_connection(feed, monkeypatch):
    app, path = feed
    original_db = app.db
    connections = []
    def tracked_db():
        conn = original_db()
        connections.append(conn)
        return conn
    monkeypatch.setattr(app, 'db', tracked_db)
    result = app.sync_sportsdb_feed(limit=20)
    stored = receipt(path)
    assert result['processed'] == 20 and result['external_calls'] == 7
    assert_closed(stored, 20, 7, 'OK')
    assert stored['matches'] == 20 and stored['teams'] == 2
    assert len(stored['imports']) == 1 and stored['imports'][0]['rows_count'] == 20
    assert len(connections) == 1
    with pytest.raises(sqlite3.ProgrammingError):
        connections[0].execute('SELECT 1')


@pytest.mark.parametrize('fail_commit', [False, True])
def test_commit_boundary_publishes_counts_and_rows_together(feed, monkeypatch, fail_commit):
    app, path = feed
    original_db = app.db
    now = [0.0]
    commits = []
    class Connection:
        def __init__(self):
            self.raw = original_db()
        def __getattr__(self, name):
            return getattr(self.raw, name)
        def commit(self):
            commits.append(1)
            if len(commits) == 2:
                # Another reader sees neither the rows nor a premature receipt.
                before = receipt(path)
                assert before['matches'] == before['teams'] == 0
                assert before['log']['status'] == 'RUNNING'
                assert before['state'] is None and not before['imports']
                if fail_commit:
                    now[0] = 16.0
                    raise sqlite3.OperationalError('synthetic commit failure')
            self.raw.commit()
            if len(commits) == 2:
                now[0] = 16.0
                # Expiry immediately after commit cannot leave a RUNNING log.
                after = receipt(path)
                assert_closed(after, 20, 7, 'OK')
                assert after['matches'] == 20 and len(after['imports']) == 1
    monkeypatch.setattr(app, 'db', Connection)
    with CronRequestBudget(seconds=16, clock=lambda: now[0]):
        result = app._safe_sports_sync_call('sportsdb_calendar', app.sync_sportsdb_feed, limit=20)
        with pytest.raises(CronTimeBudget):
            request_timeout(4)
    stored = receipt(path)
    assert result['external_calls'] == 7
    if fail_commit:
        assert result['ok'] is False and result['processed'] == 0
        assert_closed(stored, 0, 7, 'ERROR')
        assert stored['matches'] == stored['teams'] == 0 and not stored['imports']
    else:
        assert result['processed'] == 20
        assert_closed(stored, 20, 7, 'OK')


def test_budget_expires_after_rows_before_receipt_preserves_durable_counts(feed, monkeypatch):
    app, path = feed
    now = [0.0]
    original = app._upsert_sportsdb_matches_transaction
    def expires(conn, rows):
        result = original(conn, rows)
        now[0] = 16.0
        return result
    monkeypatch.setattr(app, '_upsert_sportsdb_matches_transaction', expires)
    monkeypatch.setattr(app, 'sportsdb_reconciliation_status', lambda *a, **k: pytest.fail('new work after deadline'))
    with CronRequestBudget(seconds=16, clock=lambda: now[0]):
        result = app._safe_sports_sync_call('sportsdb_calendar', app.sync_sportsdb_feed, limit=20)
        with pytest.raises(CronTimeBudget):
            request_timeout(4)
    assert result['processed'] == 20 and result['external_calls'] == 7
    assert result['status'] == 'PARTIAL' and result['controlled_deferrals'] == ['TIME_BUDGET']
    assert 'stale_reconciliation_resolved' not in result
    stored = receipt(path)
    assert_closed(stored, 20, 7, 'PARTIAL')
    assert stored['matches'] == 20 and len(stored['imports']) == 1


@pytest.mark.parametrize('provider_errors', [[], ['NETWORK']])
def test_budget_expires_after_fetch_closes_without_starting_match_work(feed, monkeypatch, provider_errors):
    app, path = feed
    now = [0.0]
    original = app.fetch_sportsdb_feed_events
    def expires(**kwargs):
        rows, _, calls = original(**kwargs)
        now[0] = 16.0
        return rows, provider_errors, calls
    monkeypatch.setattr(app, 'fetch_sportsdb_feed_events', expires)
    monkeypatch.setattr(app, 'sportsdb_event_to_match', lambda *a, **k: pytest.fail('work after deadline'))
    with CronRequestBudget(seconds=16, clock=lambda: now[0]):
        result = app.sync_sportsdb_feed(limit=20)
    assert result['external_calls'] == 7 and result['processed'] == 0
    assert result['errors'] == provider_errors + ['TIME_BUDGET']
    stored = receipt(path)
    assert_closed(stored, 0, 7, 'ERROR' if provider_errors else 'TIME_BUDGET')
    assert stored['matches'] == stored['teams'] == 0 and not stored['imports']
    if provider_errors:
        monkeypatch.setattr(app, 'run_sports_sync_cycle', lambda **kwargs: {'fallback': result})
        monkeypatch.setattr(app, 'api_exploitation_summary', lambda *args: {})
        monkeypatch.setattr(app, '_build_sports_pipeline_diagnostics', lambda *args: {})
        assert app.bounded_sports_sync()['technical_errors'] == ['fallback_NETWORK_OR_TIMEOUT']


@pytest.mark.parametrize('failure', [CronTimeBudget(), ValueError('synthetic bad event')])
def test_partial_team_transform_rolls_back_and_closes(feed, monkeypatch, failure):
    app, path = feed
    original = app.sportsdb_event_to_match
    calls = []
    def interrupt(event, **kwargs):
        calls.append(event)
        if len(calls) == 2:
            raise failure
        return original(event, **kwargs)
    monkeypatch.setattr(app, 'sportsdb_event_to_match', interrupt)
    result = app.sync_sportsdb_feed(limit=20)
    stored = receipt(path)
    status = 'TIME_BUDGET' if isinstance(failure, CronTimeBudget) else 'ERROR'
    assert result['external_calls'] == 7 and result['processed'] == 0
    assert_closed(stored, 0, 7, status)
    assert stored['matches'] == stored['teams'] == 0 and not stored['imports']


def test_receipt_write_failure_rolls_back_matches_and_records_failure(feed):
    app, path = feed
    with sqlite3.connect(path) as conn:
        conn.execute("""CREATE TRIGGER fail_import BEFORE INSERT ON imports
                     BEGIN SELECT RAISE(ABORT, 'synthetic receipt failure'); END""")
    result = app.sync_sportsdb_feed(limit=20)
    stored = receipt(path)
    assert result['ok'] is False and result['processed'] == 0 and result['external_calls'] == 7
    assert_closed(stored, 0, 7, 'ERROR')
    assert stored['matches'] == stored['teams'] == 0 and not stored['imports']
    assert 'synthetic receipt failure' not in json.dumps(result)


def test_unwritable_finalization_is_explicit_technical_failure(feed):
    app, path = feed
    with sqlite3.connect(path) as conn:
        conn.execute("""CREATE TRIGGER fail_log BEFORE UPDATE ON api_sync_logs
                     BEGIN SELECT RAISE(ABORT, 'synthetic log failure'); END""")
    result = app.sync_sportsdb_feed(limit=20)
    stored = receipt(path)
    assert result['ok'] is False and result['status'] == 'ERROR'
    assert result['finalization_error'] == 'LOCAL_DB_OR_SCHEMA'
    assert result['external_calls'] == 7 and result['processed'] == 0
    assert stored['log']['status'] == 'RUNNING' and not stored['log']['finished_at']
    assert stored['matches'] == stored['teams'] == 0 and not stored['imports']
    assert stored['state'] is None


def test_cache_failure_after_commit_cannot_erase_import_counts(feed, monkeypatch):
    app, path = feed
    def fail(*args):
        raise RuntimeError('synthetic cache failure')
    monkeypatch.setattr(app, 'invalidate_v934_realtime_cache', fail)
    result = app.sync_sportsdb_feed(limit=20)
    assert result['ok'] is False and result['errors'] == ['CACHE_INVALIDATION_ERROR']
    assert result['processed'] == 20 and result['external_calls'] == 7
    stored = receipt(path)
    assert_closed(stored, 20, 7, 'OK')
    assert stored['matches'] == 20 and len(stored['imports']) == 1


def test_reconciliation_reads_pending_rows_in_the_owning_transaction(app_module, tmp_path, monkeypatch):
    original = app_module.sportsdb_reconciliation_status
    path = prepare(app_module, tmp_path, monkeypatch)
    monkeypatch.setattr(app_module, 'sportsdb_reconciliation_status', original)
    monkeypatch.setattr(app_module, 'sportsdb_stale_external_ids', lambda **kwargs: ['19'])
    result = app_module.sync_sportsdb_feed(limit=20)
    assert result['stale_reconciliation_observed'] == 1
    assert result['stale_reconciliation_missing'] == 0
    assert result['stale_reconciliation_resolved'] + result['stale_reconciliation_remaining'] == 1
    assert receipt(path)['state'] == result


def test_provider_error_keeps_observed_calls_when_budget_expires_before_error_log(app_module, tmp_path, monkeypatch):
    original_fetch = app_module.fetch_sportsdb_feed_events
    path = prepare(app_module, tmp_path, monkeypatch)
    now = [0.0]
    def provider(*args):
        now[0] = 16.0
        return {'error': 'synthetic rejection'}
    monkeypatch.setattr(app_module, 'fetch_sportsdb_feed_events', original_fetch)
    monkeypatch.setattr(app_module, 'sportsdb_v1', provider)
    monkeypatch.setattr(app_module, 'sportsdb_v2', provider)
    with CronRequestBudget(seconds=16, clock=lambda: now[0]):
        result = app_module.sync_sportsdb_feed(limit=20)
    assert result['external_calls'] == 1 and result['errors'] == ['PROVIDER_ERROR', 'TIME_BUDGET']
    assert result['ok'] is False and result['status'] == 'ERROR'
    assert_closed(receipt(path), 0, 1, 'ERROR')
