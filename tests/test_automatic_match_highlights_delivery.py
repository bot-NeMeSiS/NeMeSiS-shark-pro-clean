import json
import sqlite3
import time
from datetime import date
import pytest
from engines import sportsdb_highlights_engine as media


@pytest.fixture
def store(tmp_path, monkeypatch):
    path = str(tmp_path / 'highlights.sqlite')
    monkeypatch.setattr(media, '_api_key', lambda: 'isolated-test-key')
    monkeypatch.setattr(media, '_today', lambda: date(2026, 10, 3))
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *args: {'events': []})
    monkeypatch.setattr(media, '_sportsdb_v2', lambda *args: {'lookup': []})
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE matches(id TEXT PRIMARY KEY,external_id TEXT,source TEXT,home_team TEXT,away_team TEXT,match_date TEXT,competition_name TEXT,status TEXT,score TEXT)')
    return path


def add_match(path, number, day='2026-10-03', source='TheSportsDB', status='FT'):
    with sqlite3.connect(path) as conn:
        conn.execute('INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?)',
                     (str(number), 'sportsdb-' + str(number) if source == 'TheSportsDB' else str(number), source, 'Local QA Home', 'Local QA Away', day, 'Local QA League', status, '1-0'))


def event(number='1'):
    return {'idEvent': number, 'strHomeTeam': 'Local QA Home', 'strAwayTeam': 'Local QA Away', 'dateEvent': '2026-10-03', 'strLeague': 'Local QA League', 'strVideo': 'https://www.youtube.com/watch?v=abcdefghijk'}


def test_empty_newest_events_do_not_starve_other_finished_matches(store, monkeypatch):
    for number in range(1, 9):
        add_match(store, number)
    calls = []
    monkeypatch.setattr(media, '_sportsdb_v2', lambda path: calls.append(path) or {'lookup': []})
    first = media.sync_sportsdb_highlights(store, days_back=7)
    second = media.sync_sportsdb_highlights(store, days_back=7)
    assert first['external_calls'] <= 12 and second['external_calls'] <= 12
    assert len(calls) == 8 and len(set(calls)) == 8
    with sqlite3.connect(store) as conn:
        conn.execute("UPDATE sportsdb_highlight_feed_cache SET expires_at='2000-01-01T00:00:00+01:00' WHERE cache_key LIKE 'v2:%'")
    third = media.sync_sportsdb_highlights(store, days_back=7)
    assert third['v2_event_lookups'] == 4


def test_seven_day_recovery_only_looks_up_final_sportsdb_events(store, monkeypatch):
    add_match(store, 1, '2026-09-26')
    add_match(store, 2, '2026-09-25')
    add_match(store, 3, source='API-Football')
    add_match(store, 4, status='LIVE')
    calls = []
    monkeypatch.setattr(media, '_sportsdb_v2', lambda path: calls.append(path) or {'lookup': []})
    result = media.sync_sportsdb_highlights(store, days_back=7)
    assert calls == ['lookup/event_highlights/1']
    assert result['external_calls'] <= 12


def test_video_received_before_fixture_is_associated_later_without_publication(store):
    media.ensure_sportsdb_highlights_schema(store)
    with media._connect(store) as conn:
        media._upsert_highlight(conn, event())
    add_match(store, 1)
    result = media.sync_sportsdb_highlights(store, days_back=7)
    assert result['associations_reconciled'] == 1
    snapshot = media.sportsdb_highlights_for_match(store, '1')
    assert snapshot['all_highlights'][0]['match_id'] == '1'
    assert snapshot['highlights'] == []
    assert snapshot['all_highlights'][0]['rights_status'] == 'REVIEW_REQUIRED'


def test_ambiguous_association_revokes_stored_approval(store):
    add_match(store, 1)
    media.ensure_sportsdb_highlights_schema(store)
    with media._connect(store) as conn:
        media._upsert_highlight(conn, event())
        conn.execute("UPDATE sportsdb_match_highlights SET rights_status='LICENSED',commercial_use_status='ALLOWED',rights_verified_at='2026-10-03T10:00:00+02:00'")
        conn.execute("INSERT INTO matches SELECT 'duplicate',external_id,source,home_team,away_team,match_date,competition_name,status,score FROM matches WHERE id='1'")
    assert media.reconcile_cached_highlight_links(store) == 1
    with sqlite3.connect(store) as conn:
        row = conn.execute('SELECT match_id,rights_status,rights_verified_at FROM sportsdb_match_highlights').fetchone()
    assert row == ('', 'REVIEW_REQUIRED', '')


def test_broader_recovery_window_is_not_hidden_by_narrower_success(monkeypatch, app_module):
    monkeypatch.setenv('HIGHLIGHTS_SYNC_INTERVAL_MINUTES', '360')
    monkeypatch.setattr(app_module, 'automation_get', lambda *args: {'ok': True, 'status': 'OK', 'errors': [], 'days_back': 2, 'attempt_finished_epoch': time.time() - 1800})
    monkeypatch.setattr(app_module, 'automation_set', lambda *args: None)
    seen = []
    monkeypatch.setattr(app_module, 'sync_sportsdb_highlights', lambda *args, **kwargs: seen.append(kwargs) or {'ok': True, 'status': 'OK', 'days_back': kwargs['days_back']})
    assert app_module.v766_sync_highlights_daily(days_back=7)['ok'] is True
    assert seen[0]['days_back'] == 7
