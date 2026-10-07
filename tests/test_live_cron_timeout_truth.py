"""Separate local deadline cutoff from real API failures, with no network."""
import urllib.error
import pytest
from engines import api_football_live_tracker_engine as tracker
from engines.cron_request_budget import CronRequestBudget


@pytest.mark.parametrize('kind', ['deadline_timeout', 'provider_timeout', 'slow_dns_then_provider_timeout', 'http403'])
def test_live_cutoff_preserves_attempt_count_and_real_provider_errors(app_module, monkeypatch, kind):
    clock = [0.0]
    calls = []
    monkeypatch.setattr(tracker, '_api_key', lambda: 'synthetic-test-key')
    def network(*args, **kwargs):
        calls.append(kwargs['timeout'])
        clock[0] += {'deadline_timeout': 1.0, 'provider_timeout': 4.0,
                     'slow_dns_then_provider_timeout': 20.0, 'http403': 1.0}[kind]
        if kind == 'http403':
            raise urllib.error.HTTPError('https://example.invalid', 403, 'Forbidden', {}, None)
        raise TimeoutError('timed out')
    monkeypatch.setattr(tracker.urllib.request, 'urlopen', network)
    with CronRequestBudget(seconds=0.5 if kind in {'deadline_timeout', 'http403'} else 16, clock=lambda: clock[0]):
        result = app_module._safe_sports_sync_call('live', tracker._api_get, 'fixtures')
    assert len(calls) == 1
    if kind == 'deadline_timeout':
        assert result['status'] == 'TIME_BUDGET'
        assert result['ok'] and result['external_calls'] == 1
    else:
        assert result['ok'] is False
        assert result['error'] != 'TIME_BUDGET'
    monkeypatch.setattr(app_module, 'run_sports_sync_cycle', lambda **kwargs: {
        'ok': True, 'status': 'PARTIAL', 'fixtures': {'ok': True}, 'live': result,
        'errors': [result['error']] if result.get('error') else [],
    })
    classified = app_module.bounded_sports_sync()
    assert bool(classified['technical_errors']) == (kind != 'deadline_timeout')


def test_expired_budget_starts_no_api_call(app_module, monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(tracker, '_api_key', lambda: 'synthetic-test-key')
    monkeypatch.setattr(tracker.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('No network after deadline'))
    with CronRequestBudget(seconds=0.5, clock=lambda: clock[0]):
        clock[0] = 1.0
        # Direct adapter invocation verifies that the adapter preserves the
        # deadline exception even when the outer stage check ran earlier.
        from engines.cron_request_budget import CronTimeBudget
        with pytest.raises(CronTimeBudget):
            tracker._api_get('fixtures')


def test_cutoff_does_not_refresh_persisted_live_observation(app_module, tmp_path, monkeypatch):
    path = tmp_path / 'live.sqlite'
    monkeypatch.setattr(app_module, 'DB_PATH', str(path))
    app_module.init_db()
    tracker.ensure_live_tracker_schema(str(path))
    with tracker._connect(str(path)) as conn:
        tracker._write_sync_state(conn, {'status': 'ok'}, 0, 0, 0, 0, '')
        conn.execute("UPDATE api_football_live_sync_state SET last_sync_at='2000-01-01T00:00:00Z' WHERE key='live'")
        conn.commit()
        before = tuple(conn.execute("SELECT * FROM api_football_live_sync_state WHERE key='live'").fetchone())
    monkeypatch.setattr(tracker, '_api_key', lambda: 'synthetic-test-key')
    monkeypatch.setattr(tracker, 'api_key_configured', lambda: True)
    monkeypatch.setattr(tracker, 'tracker_enabled', lambda: True)
    clock = [0.0]
    def timeout(*a, **k):
        clock[0] = 1.0
        raise TimeoutError('timed out')
    monkeypatch.setattr(tracker.urllib.request, 'urlopen', timeout)
    with CronRequestBudget(seconds=0.5, clock=lambda: clock[0]):
        result = app_module._safe_sports_sync_call('live', tracker.sync_api_football_live_tracker, str(path), deep_limit=0)
    assert result['status'] == 'TIME_BUDGET' and result['external_calls'] == 1
    with tracker._connect(str(path)) as conn:
        assert tuple(conn.execute("SELECT * FROM api_football_live_sync_state WHERE key='live'").fetchone()) == before
