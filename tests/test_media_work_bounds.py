"""Bounded catalogue work and resumable media deadlines, entirely offline."""
import json
import sqlite3
import urllib.error
from datetime import date, datetime, timezone

import pytest

from engines import highlight_coverage as inventory
from engines import sportsdb_highlights_engine as media

NOW = datetime(2026, 10, 8, 18, tzinfo=timezone.utc).timestamp()


def make_matches(path, count, status='FT'):
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE matches(id TEXT PRIMARY KEY, external_id TEXT, source TEXT, '
                     'home_team TEXT, away_team TEXT, match_date TEXT, kickoff_time TEXT, '
                     'competition_name TEXT, league_id TEXT, status TEXT, score TEXT)')
        conn.executemany('INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?,?,?)', [
            (str(i), f'sportsdb-{1000+i}', 'TheSportsDB', f'Home {i}', f'Away {i}',
             '2026-10-07', '12:00', 'League', '42', status, '2-1') for i in range(count)])
    media.ensure_sportsdb_highlights_schema(path)


def event(i=0, video='abcdefghijk'):
    return {'idEvent':str(1000+i), 'strHomeTeam':f'Home {i}', 'strAwayTeam':f'Away {i}',
            'dateEvent':'2026-10-07', 'strLeague':'League', 'idLeague':'42',
            'strVideo':'https://www.youtube.com/watch?v='+video}


@pytest.fixture
def store(tmp_path, monkeypatch):
    path = tmp_path/'media.sqlite'
    make_matches(path, 2)
    monkeypatch.setattr(media, '_api_key', lambda:'test-key-never-log')
    monkeypatch.setattr(media, '_today', lambda:date(2026, 10, 7))
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: {'events':[]})
    monkeypatch.setattr(media, '_sportsdb_v2', lambda *a: {'lookup':[]})
    return path


def test_lifecycle_and_identity_evaluation_are_bounded_before_limit(tmp_path, monkeypatch):
    path=tmp_path/'catalogue.sqlite'
    make_matches(path, 600)
    inventory.Coverage(path, NOW).prepare(batch=1000)
    counts={'eligible':0, 'identity':0}
    real_eligible, real_identity=inventory.eligible, inventory.identity
    def eligible(*args):
        counts['eligible']+=1
        return real_eligible(*args)
    def identity(*args):
        counts['identity']+=1
        return real_identity(*args)
    monkeypatch.setattr(inventory, 'eligible', eligible)
    monkeypatch.setattr(inventory, 'identity', identity)
    inventory.Coverage(path, NOW).prepare(batch=11)
    assert 0 < counts['eligible'] <= 44
    assert 0 < counts['identity'] <= 88


def test_old_finalization_and_changed_identity_survive_restart_and_wrap(tmp_path):
    path=tmp_path/'rotation.sqlite'
    make_matches(path, 41, status='NS')
    inventory.Coverage(path, NOW).prepare(batch=100)
    # Recent non-final candidates may fill the fast lane indefinitely.
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE matches SET match_date='2025-01-01',status='FT' WHERE id='7'")
    for _ in range(7):
        inventory.Coverage(path, NOW).prepare(batch=7)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT state FROM highlight_coverage WHERE match_id='7'").fetchone()==('UNSCANNED',)
        conn.execute("UPDATE highlight_coverage SET state='CHECKED_NO_VIDEO',checked_at=? WHERE match_id='7'", (NOW,))
        conn.execute("UPDATE matches SET away_team='New opponent' WHERE id='7'")
    assert inventory.Coverage(path, NOW).snapshot()['checked']==0
    for _ in range(7):
        inventory.Coverage(path, NOW).prepare(batch=7)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT state,checked_at FROM highlight_coverage WHERE match_id='7'").fetchone()==('UNSCANNED',None)


def test_cursor_update_rolls_back_with_failed_inventory(tmp_path, monkeypatch):
    path=tmp_path/'rollback.sqlite'
    make_matches(path, 20)
    c=inventory.Coverage(path, NOW)
    c.prepare(batch=3)
    with sqlite3.connect(path) as conn:
        before=conn.execute('SELECT * FROM highlight_coverage_cursor').fetchone()
    def broken(*args):
        raise RuntimeError('failed eligibility')
    monkeypatch.setattr(inventory, 'eligible', broken)
    with pytest.raises(RuntimeError, match='failed eligibility'):
        c.prepare(batch=3)
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT * FROM highlight_coverage_cursor').fetchone()==before


def test_preparation_consumes_the_same_media_deadline(store, monkeypatch):
    clock=[0.]
    monkeypatch.setattr(media.time, 'monotonic', lambda:clock[0])
    real_prepare=inventory.Coverage.prepare
    def slow_prepare(self, *args, **kwargs):
        real_prepare(self, *args, **kwargs)
        clock[0]+=17
    monkeypatch.setattr(inventory.Coverage, 'prepare', slow_prepare)
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a:pytest.fail('late network call'))
    result=media.sync_sportsdb_highlights(store, days_back=0)
    assert result['status']=='PARTIAL'
    assert result['errors']==['TIME_BUDGET']
    assert result['external_calls']==result['highlights_found']==0
    assert result['stage_durations_ms']['inventory']==17000
    assert not result['provider_coverage_complete']


def test_expired_response_is_cached_and_processed_next_cycle(store, monkeypatch):
    clock=[0.]
    monkeypatch.setattr(media.time, 'monotonic', lambda:clock[0])
    calls=[]
    def slow_fetch(*args):
        calls.append(args)
        clock[0]+=17
        return {'events':[event(0),event(1)]}
    monkeypatch.setattr(media, '_sportsdb_v1', slow_fetch)
    first=media.sync_sportsdb_highlights(store, days_back=0)
    assert first['status']=='PARTIAL' and 'TIME_BUDGET' in first['errors']
    assert (first['external_calls'], first['highlights_found'])==(1,0)
    second=media.sync_sportsdb_highlights(store, days_back=0)
    assert second['highlights_found']==2 and second['external_calls']==0
    assert len(calls)==1
    with sqlite3.connect(store) as conn:
        assert conn.execute("SELECT COUNT(*) FROM sportsdb_match_highlights WHERE rights_status='UNKNOWN_RIGHTS'").fetchone()[0]==2


def test_deadline_rolls_back_partial_batch_and_existing_rights(store, monkeypatch):
    with media._connect(store) as conn:
        media._upsert_highlight(conn, event(0))
        conn.execute("UPDATE sportsdb_match_highlights SET rights_status='LICENSED', commercial_use_status='ALLOWED'")
    clock=[0.]
    monkeypatch.setattr(media.time, 'monotonic', lambda:clock[0])
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: {'events':[event(0,'zyxwvutsrqp'),event(1)]})
    real_upsert=media._upsert_highlight
    def slow_upsert(conn, item):
        result=real_upsert(conn, item)
        clock[0]+=17
        return result
    monkeypatch.setattr(media, '_upsert_highlight', slow_upsert)
    result=media.sync_sportsdb_highlights(store, days_back=0)
    assert result['status']=='PARTIAL' and result['highlights_found']==0
    with sqlite3.connect(store) as conn:
        assert conn.execute('SELECT video_url,rights_status FROM sportsdb_match_highlights').fetchall()==[(event(0)['strVideo'],'LICENSED')]


def test_provider_error_remains_failure_and_logs_only_fixed_metrics(store, monkeypatch, capsys):
    def fail(*args):
        raise urllib.error.HTTPError('https://provider.invalid/test-key-never-log',429,'secret-body',None,None)
    monkeypatch.setattr(media, '_sportsdb_v1', fail)
    result=media.sync_sportsdb_highlights(store, days_back=0)
    assert result['status']=='FAILED' and 'RATE_LIMIT' in result['errors']
    output=capsys.readouterr().out
    assert 'test-key-never-log' not in output and 'secret-body' not in output
    messages=[json.loads(line) for line in output.splitlines()]
    assert messages
    assert all(set(row)=={'event','stage','duration_ms'} and row['stage'] in media._MEDIA_STAGES for row in messages)


def test_logging_failure_cannot_discard_a_completed_media_result(store, monkeypatch):
    def broken_output(*args, **kwargs):
        raise OSError('log sink unavailable')
    monkeypatch.setattr('builtins.print', broken_output)
    result=media.sync_sportsdb_highlights(store, days_back=0)
    assert result['status']=='OK'
    with sqlite3.connect(store) as conn:
        assert conn.execute('SELECT status FROM sportsdb_highlight_runs').fetchone()==('OK',)
