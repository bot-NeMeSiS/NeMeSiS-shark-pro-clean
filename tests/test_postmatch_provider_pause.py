"""Exercise the real Postmatch lease/budget/cache with inert provider transports."""
from copy import deepcopy
from datetime import datetime, timedelta
import os
import sqlite3
import time
from zoneinfo import ZoneInfo

import pytest

from engines.postmatch_sources import OfficialSources, SourceError
from engines.postmatch_store import BudgetStopped, StaleLease, Store


SPORTSDB_FIELDS = {
    'lookupevent.php': 'events',
    'eventsday.php': 'events',
    'lookupeventstats.php': 'eventstats',
    'eventshighlights.php': 'tvhighlights',
    'lookuplineup.php': 'lineup',
    'lookuptimeline.php': 'timeline',
}


@pytest.fixture
def scenario(tmp_path, monkeypatch):
    monkeypatch.setenv('THESPORTSDB_KEY', 'synthetic-postmatch-key')
    monkeypatch.delenv('THESPORTSDB_API_KEY', raising=False)
    monkeypatch.setenv('THESPORTSDB_PAUSED', 'false')
    def deny_real_transport(*args, **kwargs):
        raise AssertionError('Real provider I/O is forbidden')
    monkeypatch.setattr('urllib.request.urlopen', deny_real_transport)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', deny_real_transport)
    day = datetime.now(ZoneInfo('Europe/Madrid')).date() - timedelta(days=1)
    match = {
        'id': 'pause-synthetic', 'external_id': 'sportsdb-987654321',
        'source': 'TheSportsDB', 'home_team': 'Synthetic Home',
        'away_team': 'Synthetic Away', 'league_id': '4328',
        'competition_name': 'Synthetic League', 'league_name': 'Synthetic League',
        'match_date': str(day), 'kickoff_time': '12:00', 'status': 'FT',
        'score': '1-0', 'home_score': 1, 'away_score': 0,
    }
    path = tmp_path / 'pause.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE matches (' + ','.join(
            k + (' INTEGER' if k.endswith('_score') else ' TEXT') for k in match) + ')')
        conn.execute('INSERT INTO matches VALUES (' + ','.join('?' for _ in match) + ')',
                     tuple(match.values()))
    store = Store(path)
    store.configure(enabled=True, sources=['thesportsdb', 'api_football'],
                    daily_limit=60, actor='synthetic-test', confirmed=True)
    store.discover(time.time())
    job = store.claim(time.time())
    assert job is not None
    calls = []
    def transport(request, timeout):
        endpoint = request.full_url.split('?', 1)[0].rsplit('/', 1)[-1]
        calls.append(endpoint)
        return {SPORTSDB_FIELDS.get(endpoint, 'response'): []}
    def source():
        return OfficialSources(store, job, store.config(),
                               deadline=time.time() + 20, transport=transport)
    return store, job, calls, source, match


def spent(store):
    with store.connection() as conn:
        return conn.execute('SELECT COALESCE(SUM(used),0) FROM postmatch_source_budget').fetchone()[0]


@pytest.mark.parametrize('endpoint', SPORTSDB_FIELDS)
@pytest.mark.parametrize('key_name', ['THESPORTSDB_KEY', 'THESPORTSDB_API_KEY'])
def test_paused_miss_preserves_lease_and_spends_nothing(scenario, monkeypatch, endpoint, key_name):
    store, job, calls, source, _ = scenario
    monkeypatch.delenv('THESPORTSDB_KEY', raising=False)
    monkeypatch.setenv(key_name, 'synthetic-postmatch-key')
    monkeypatch.setenv('THESPORTSDB_PAUSED', 'true')
    adapter = source()
    with store.connection() as conn:
        before = tuple(conn.execute('SELECT * FROM postmatch_jobs WHERE id=?', (job['id'],)).fetchone())
    with pytest.raises(SourceError, match='^SOURCE_DISABLED$'):
        adapter.request('thesportsdb', endpoint, {'id': '987654321'})
    assert adapter.calls == 0 and calls == [] and spent(store) == 0
    assert adapter.receipts == {} and adapter.cache == {}
    with store.connection() as conn:
        after = tuple(conn.execute('SELECT * FROM postmatch_jobs WHERE id=?', (job['id'],)).fetchone())
        assert conn.execute('SELECT COUNT(*) FROM postmatch_circuits').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM postmatch_request_cache').fetchone()[0] == 0
        assert conn.execute('SELECT score FROM matches').fetchone()[0] == '1-0'
    assert before == after
    assert os.environ[key_name] == 'synthetic-postmatch-key'


@pytest.mark.parametrize('endpoint', SPORTSDB_FIELDS)
def test_unpaused_control_keeps_real_attempt_accounting(scenario, endpoint):
    store, _, calls, source, _ = scenario
    adapter = source()
    assert adapter.request('thesportsdb', endpoint, {'id': '987654321'}) == {SPORTSDB_FIELDS[endpoint]: []}
    assert calls == [endpoint] and adapter.calls == spent(store) == 1


def test_live_pause_transition_preserves_memory_cache_and_blocks_new_requests(scenario, monkeypatch):
    store, _, calls, source, _ = scenario
    adapter = source()
    monkeypatch.setenv('THESPORTSDB_PAUSED', 'true')
    with pytest.raises(SourceError, match='^SOURCE_DISABLED$'):
        adapter.request('thesportsdb', 'lookupevent.php', {'id': '987654321'})
    monkeypatch.setenv('THESPORTSDB_PAUSED', 'false')
    original = adapter.request('thesportsdb', 'lookupevent.php', {'id': '987654321'})
    receipts = deepcopy(adapter.receipts)
    monkeypatch.setenv('THESPORTSDB_PAUSED', 'true')
    cached = adapter.request('thesportsdb', 'lookupevent.php', {'id': '987654321'})
    assert cached == original
    cached['events'].append({'idEvent': 'must-not-leak'})
    assert adapter.request('thesportsdb', 'lookupevent.php', {'id': '987654321'}) == original
    assert adapter.receipts == receipts
    with pytest.raises(SourceError, match='^SOURCE_DISABLED$'):
        adapter.request('thesportsdb', 'lookupevent.php', {'id': '987654322'})
    assert calls == ['lookupevent.php'] and adapter.calls == spent(store) == 1


def test_paused_restart_keeps_valid_identity_scoped_persistent_cache(scenario, monkeypatch):
    store, job, calls, source, _ = scenario
    first = source()
    original = first.request('thesportsdb', 'lookupevent.php', {'id': '987654321'})
    monkeypatch.setenv('THESPORTSDB_PAUSED', 'true')
    restarted = source()
    assert restarted.cache == {}
    assert restarted.request('thesportsdb', 'lookupevent.php', {'id': '987654321'}) == original
    assert restarted.calls == 0 and restarted.receipts == first.receipts
    restarted.job = {**job, 'identity': 'a-different-current-identity'}
    restarted.cache = {}
    with pytest.raises(SourceError, match='^SOURCE_DISABLED$'):
        restarted.request('thesportsdb', 'lookupevent.php', {'id': '987654321'})
    assert calls == ['lookupevent.php'] and spent(store) == 1


def test_paused_cache_is_not_shared_across_credentials(scenario, monkeypatch):
    store, _, calls, source, _ = scenario
    adapter = source()
    adapter.request('thesportsdb', 'lookupevent.php', {'id': '987654321'})
    monkeypatch.setenv('THESPORTSDB_PAUSED', 'true')
    monkeypatch.setenv('THESPORTSDB_KEY', 'different-synthetic-key')
    for instance in (adapter, source()):
        with pytest.raises(SourceError, match='^SOURCE_DISABLED$'):
            instance.request('thesportsdb', 'lookupevent.php', {'id': '987654321'})
    assert calls == ['lookupevent.php'] and spent(store) == 1


def test_expired_persistent_cache_does_not_grant_provider_io_during_pause(scenario, monkeypatch):
    store, _, calls, source, _ = scenario
    source().request('thesportsdb', 'lookupevent.php', {'id': '987654321'})
    with store.connection(True) as conn:
        conn.execute('UPDATE postmatch_request_cache SET expires_at=?', (time.time() - 1,))
    monkeypatch.setenv('THESPORTSDB_PAUSED', 'true')
    with pytest.raises(SourceError, match='^SOURCE_DISABLED$'):
        source().request('thesportsdb', 'lookupevent.php', {'id': '987654321'})
    assert calls == ['lookupevent.php'] and spent(store) == 1


@pytest.mark.parametrize('endpoint', ['fixtures', 'fixtures/statistics', 'fixtures/events', 'fixtures/lineups'])
def test_sportsdb_pause_does_not_disable_explicitly_allowed_football(scenario, monkeypatch, endpoint):
    from engines import api_sports_provider_engine as football
    store, _, calls, source, _ = scenario
    monkeypatch.setenv('THESPORTSDB_PAUSED', 'true')
    monkeypatch.setenv('ENABLE_API_FOOTBALL_PROVIDER', 'true')
    monkeypatch.setattr(football, '_provider_key', lambda: 'synthetic-football-key')
    monkeypatch.setattr(football, 'usage_guard', lambda: {'network_enabled': True})
    adapter = source()
    assert adapter.request('api_football', endpoint, {'fixture': '123'}) == {'response': []}
    assert len(calls) == 1 and adapter.calls == spent(store) == 1
    with store.connection() as conn:
        assert conn.execute("SELECT used FROM postmatch_source_budget WHERE source='api_football'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM postmatch_source_budget WHERE source='thesportsdb'").fetchone()[0] == 0


def test_cache_hit_does_not_override_explicit_source_allowlist(scenario, monkeypatch):
    store, _, calls, source, _ = scenario
    adapter = source()
    adapter.request('thesportsdb', 'lookupevent.php', {'id': '987654321'})
    monkeypatch.setenv('THESPORTSDB_PAUSED', 'true')
    adapter.config = {**adapter.config, 'sources': ['api_football']}
    with pytest.raises(SourceError, match='^SOURCE_NOT_ALLOWED$'):
        adapter.request('thesportsdb', 'lookupevent.php', {'id': '987654321'})
    assert calls == ['lookupevent.php'] and spent(store) == 1


def test_unpaused_miss_still_requires_current_lease(scenario):
    store, job, calls, source, _ = scenario
    adapter = source()
    adapter.job = {**job, 'lease_token': 'different-lease'}
    with pytest.raises(StaleLease, match='LEASE_LOST'):
        adapter.request('thesportsdb', 'lookupevent.php', {'id': '987654321'})
    assert calls == [] and adapter.calls == spent(store) == 0


def test_unpaused_miss_still_obeys_daily_cap(scenario):
    store, _, calls, source, _ = scenario
    adapter = source()
    adapter.config['daily_limit'] = 1
    adapter.request('thesportsdb', 'lookupevent.php', {'id': '987654321'})
    with pytest.raises(BudgetStopped, match='DAILY_BUDGET'):
        adapter.request('thesportsdb', 'lookupeventstats.php', {'id': '987654321'})
    assert calls == ['lookupevent.php'] and adapter.calls == spent(store) == 1


def test_worker_defers_paused_requests_without_exhausting_attempts(scenario, monkeypatch):
    from engines.postmatch_recovery import tick
    store, _, calls, _, _ = scenario
    # Release the fixture's owned synthetic claim for a real worker claim.
    with store.connection(True) as conn:
        conn.execute("UPDATE postmatch_jobs SET state='PENDING',attempts=0,lease_token=NULL,lease_until=0")
    store.configure(enabled=True, sources=['thesportsdb'], daily_limit=60,
                    actor='synthetic-test', confirmed=True)
    monkeypatch.setenv('THESPORTSDB_PAUSED', 'true')
    def inert_factory(*args, **kwargs):
        def transport(*unused):
            calls.append('forbidden')
            raise AssertionError('Paused worker reached transport')
        return OfficialSources(*args, transport=transport, **kwargs)
    result = tick(store.path, source_factory=inert_factory)
    assert result['external_calls'] == 0 and result['result'] == 'PARTIAL'
    assert len(result['jobs']) == 2
    assert all(row['state'] == 'RETRY' and row['reason'] == 'SOURCE_DISABLED' for row in result['jobs'])
    assert calls == [] and spent(store) == 0
    with store.connection() as conn:
        assert {row[0] for row in conn.execute('SELECT attempts FROM postmatch_jobs')} == {0}
        assert conn.execute('SELECT score FROM matches').fetchone()[0] == '1-0'
