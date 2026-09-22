"""A failed provider envelope is not fresh fixture evidence. Synthetic, offline."""
from contextlib import closing
from copy import deepcopy
import sqlite3

import pytest
from test_match_record_ingestion import db, fixture_payload, no_network, stats, events
from engines import api_football_live_tracker_engine as live


@pytest.mark.parametrize('cached', [False, True])
def test_failed_live_response_cannot_ingest_rows_or_start_deep_calls(db, monkeypatch, cached):
    monkeypatch.setattr(live, 'tracker_enabled', lambda: True)
    monkeypatch.setattr(live, 'api_key_configured', lambda: True)
    original = fixture_payload()
    if cached:
        with closing(sqlite3.connect(db)) as conn:
            with conn:
                live._upsert_fixture(conn, original)
    before = {}
    with closing(sqlite3.connect(db)) as conn:
        for table in ('matches', 'api_football_live_snapshots'):
            before[table] = conn.execute('SELECT * FROM '+table).fetchall()
        before['archive'] = conn.execute('SELECT COUNT(*) FROM match_record_observations').fetchone()[0] if cached else 0
    malformed = deepcopy(original)
    malformed['goals'] = {'home': 8, 'away': 6}
    seen = []
    def fetch(path, params=None, timeout=18):
        seen.append(path)
        return {'ok': False, 'response': [malformed] if path == 'fixtures' else [],
                'errors': {'access': 'Synthetic rejected response'}}
    monkeypatch.setattr(live, '_api_get', fetch)
    result = live.sync_api_football_live_tracker(db, force=True, deep_limit=1)
    assert seen == ['fixtures']
    assert result['fixtures_count'] == result['events_count'] == result['stats_count'] == 0
    assert result['errors'] and result['external_calls'] == 1
    with closing(sqlite3.connect(db)) as conn:
        for table in ('matches', 'api_football_live_snapshots'):
            assert conn.execute('SELECT * FROM '+table).fetchall() == before[table]
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='match_record_observations'").fetchone()
        assert (conn.execute('SELECT COUNT(*) FROM match_record_observations').fetchone()[0] if exists else 0) == before['archive']


@pytest.mark.parametrize('failed_sections', [('events',), ('statistics',), ('events', 'statistics')])
def test_window_reports_missing_deep_sections_instead_of_full_success(db, monkeypatch, failed_sections):
    monkeypatch.setattr(live, 'tracker_enabled', lambda: True)
    monkeypatch.setattr(live, 'api_key_configured', lambda: True)
    monkeypatch.setattr(live, '_date_range', lambda *a: ['2026-09-22'])
    def fetch(path, params=None, timeout=18):
        section = path.rsplit('/', 1)[-1]
        if section in failed_sections:
            return {'ok': False, 'response': [], 'errors': {'access': 'Synthetic access denied'}}
        return {'ok': True, 'response': [fixture_payload()] if path == 'fixtures' else events() if section == 'events' else stats()}
    monkeypatch.setattr(live, '_api_get', fetch)
    result = live.sync_api_football_match_window(db, force=True, deep_limit=1)
    assert result['ok'] is False
    assert result['status'].startswith('PARTIAL_') and result['errors']
    assert result['fixtures_count'] == 1 and result['external_calls'] == 3
    with closing(sqlite3.connect(db)) as conn:
        sections = {r[0] for r in conn.execute('SELECT section FROM match_record_observations')}
        assert 'fixture' in sections
        assert not sections.intersection(failed_sections)
        assert {'events', 'statistics'} - set(failed_sections) <= sections
