"""Regression: deduplication must retain a whole observed provider snapshot."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
import sqlite3
from zoneinfo import ZoneInfo

import pytest

from engines.realtime_state_engine import merge_match_observations
from engines.v935_launch_trust_engine import match_status_truth

MADRID = ZoneInfo('Europe/Madrid')


def snapshot(identifier, *, age=None, status='LIVE', score=(0, 1), **extra):
    now = datetime.now(MADRID)
    return {
        'id': identifier, 'external_id': 'provider-event-2440438',
        'source': 'TheSportsDB API', 'home_team': 'Tartu Kalev',
        'away_team': 'Jõhvi Phoenix', 'competition_name': 'Estonian Esiliiga B',
        'match_date': now.date().isoformat(), 'kickoff_time': '10:00',
        'match_time': '10:00', 'kickoff_iso': now.replace(hour=10, minute=0, second=0, microsecond=0).isoformat(),
        'status': status, 'minute': '71' if status == 'LIVE' else '',
        'score': f'{score[0]}-{score[1]}', 'home_score': score[0], 'away_score': score[1],
        'raw_json': json.dumps({'strStatus': status, 'intHomeScore': score[0], 'intAwayScore': score[1]}),
        'last_synced_at': '' if age is None else (now - timedelta(seconds=age)).isoformat(),
        'priority': 20, **extra,
    }


def test_visual_richness_keeps_id_not_old_sports_observation():
    old = snapshot('legacy', priority=999, home_logo='old-home.svg', bookmaker='Existing bookmaker')
    new = snapshot('hashed-provider-id', age=10, score=(0, 2))
    before = deepcopy((old, new))
    merged = merge_match_observations(old, new)
    assert merged['id'] == 'legacy'
    assert merged['home_logo'] == 'old-home.svg'
    assert merged['bookmaker'] == 'Existing bookmaker'
    assert merged['last_synced_at'] == new['last_synced_at']
    assert merged['home_score'] == 0
    assert merged['away_score'] == 2
    assert merged['raw_json'] == new['raw_json']
    assert match_status_truth(merged)['is_live'] is True
    assert (old, new) == before


@pytest.mark.parametrize('missing', ['last_synced_at', 'invalid_priority_clock'])
def test_merge_never_manufactures_or_repairs_unobserved_clock(missing):
    first = snapshot('first', updated_at=datetime.now(MADRID).isoformat())
    other = snapshot('second')
    if missing == 'invalid_priority_clock':
        first['live_updated_at'] = 'not-a-clock'
        first['last_synced_at'] = datetime.now(MADRID).isoformat()
    result = merge_match_observations(first, other)
    truth = match_status_truth(result)
    assert truth['is_stale'] is True
    assert truth['is_live'] is False
    assert truth['stale_reason'] == 'LIVE_TIMESTAMP_MISSING'


def test_older_but_richer_duplicate_cannot_replace_newer_score():
    latest = snapshot('keeper', age=10, score=(2, 1))
    old = snapshot('other', age=300, score=(1, 1), priority=999, home_logo='badge')
    result = merge_match_observations(latest, old)
    assert result['last_synced_at'] == latest['last_synced_at']
    assert (result['home_score'], result['away_score']) == (2, 1)


def test_newer_final_clears_old_minute_live_flags_and_raw_payload():
    old = snapshot('keeper', age=70, is_live=True, status_info={'is_live': True},
                   live_updated_at=(datetime.now(MADRID)-timedelta(seconds=70)).isoformat())
    final = snapshot('other', age=10, status='FT', score=(0, 0))
    result = merge_match_observations(old, final)
    assert 'live_updated_at' not in result
    assert 'status_info' not in result
    assert 'is_live' not in result
    assert result['minute'] == ''
    assert result['home_score'] == result['away_score'] == 0
    assert match_status_truth(result)['is_finished'] is True
    assert match_status_truth(result)['status_conflict'] is False


def test_new_observation_missing_score_cannot_borrow_old_score():
    old = snapshot('keeper', age=60, score=(2, 1))
    new = snapshot('other', age=10)
    for field in ('score', 'home_score', 'away_score', 'minute'):
        new.pop(field)
    new['raw_json'] = '{"strStatus":"LIVE"}'
    merged = merge_match_observations(old, new)
    assert all(field not in merged for field in ('score', 'home_score', 'away_score', 'minute'))
    assert merged['last_synced_at'] == new['last_synced_at']


def test_unknown_clock_cannot_roll_back_confirmed_final():
    final = snapshot('keeper', status='FT')
    live = snapshot('other', age=10)
    result = merge_match_observations(final, live)
    assert match_status_truth(result)['is_finished'] is True
    assert result['last_synced_at'] == ''


def test_provenance_and_external_id_follow_winning_observation():
    old = snapshot('local-id', age=90)
    new = snapshot('different-local-id', age=10, source='API-Football', external_id='different-provider-id')
    result = merge_match_observations(old, new)
    assert result['id'] == 'local-id'
    assert result['source'] == new['source']
    assert result['external_id'] == new['external_id']
    assert result['raw_json'] == new['raw_json']


def test_clock_order_is_absolute_across_madrid_dst_fold():
    old = snapshot('keeper', last_synced_at='2026-10-25T02:45:00+02:00', score=(0, 1))
    new = snapshot('other', last_synced_at='2026-10-25T02:15:00+01:00', score=(0, 2))
    assert merge_match_observations(old, new)['away_score'] == 2


@pytest.fixture()
def duplicate_db(app_module, tmp_path):
    conn = sqlite3.connect(tmp_path / 'duplicates.sqlite')
    conn.row_factory = sqlite3.Row
    fields = (
        'id', 'external_id', 'source', 'legal_note', 'home_team', 'away_team',
        'match_date', 'kickoff_time', 'match_time', 'kickoff_iso', 'competition_name',
        'competition_key', 'competition_id', 'league_name', 'country', 'home_team_id',
        'away_team_id', 'home_logo', 'away_logo', 'status', 'minute', 'score',
        'home_score', 'away_score', 'venue', 'season', 'round', 'bookmaker',
        'odds_h2h_json', 'odds_updated_at', 'raw_json', 'last_synced_at', 'updated_at',
    )
    conn.execute('CREATE TABLE matches (' + ','.join(f'{name} TEXT' for name in fields) + ',priority INTEGER)')
    conn.execute('CREATE TABLE picks (id TEXT, match_id TEXT)')
    conn.execute('CREATE TABLE live_matches (id TEXT PRIMARY KEY, match_id TEXT, status TEXT, minute TEXT,home_score TEXT, away_score TEXT,payload_json TEXT,source TEXT,updated_at TEXT)')
    old = snapshot('legacy', priority=999, home_logo='legacy.svg', bookmaker='Bookmaker')
    new = snapshot('provider-hash', age=10, score=(0, 2))
    for item in (old, new):
        names = list(item)
        conn.execute('INSERT INTO matches (' + ','.join(names) + ') VALUES (' + ','.join('?' for _ in names) + ')', [item[n] for n in names])
        conn.execute('INSERT INTO live_matches (id,match_id,status,minute,home_score,away_score,source,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                     ('live-'+item['id'],item['id'],'LIVE','62','4','3','wrong-old-live-cache','2020-01-01T00:00:00Z'))
    conn.execute('INSERT INTO picks VALUES (?,?)', ('retained-pick',new['id']))
    conn.commit()
    try:
        yield conn, old, new
    finally:
        conn.close()


def test_sqlite_cleanup_preserves_clock_zero_score_links_and_live_cache(app_module, duplicate_db):
    conn, old, new = duplicate_db
    result = app_module.cleanup_duplicate_matches(conn.cursor())
    conn.commit()
    assert result['duplicates_removed'] == 1
    matches = [dict(row) for row in conn.execute('SELECT * FROM matches')]
    assert len(matches) == 1
    kept = matches[0]
    assert kept['id'] == old['id']
    assert kept['last_synced_at'] == new['last_synced_at']
    assert kept['home_score'] == '0'
    assert kept['away_score'] == '2'
    assert kept['home_logo'] == old['home_logo']
    assert conn.execute('SELECT match_id FROM picks').fetchone()[0] == old['id']
    live = [dict(row) for row in conn.execute('SELECT * FROM live_matches')]
    assert len(live) == 1
    assert live[0]['match_id'] == old['id']
    assert live[0]['updated_at'] == new['last_synced_at']
    assert live[0]['home_score'] == '0' and live[0]['away_score'] == '2'
    assert match_status_truth(kept)['is_live'] is True
    # Idempotent second cleanup must not move any observation clock.
    again = app_module.cleanup_duplicate_matches(conn.cursor())
    conn.commit()
    assert again['duplicates_removed'] == 0
    assert dict(conn.execute('SELECT * FROM matches').fetchone()) == kept


def test_sqlite_cleanup_removes_live_cache_when_new_evidence_is_final(app_module, duplicate_db):
    conn, old, new = duplicate_db
    conn.execute('UPDATE matches SET status=?,minute=?,raw_json=? WHERE id=?',
                 ('FT', '', '{"strStatus":"FT","intHomeScore":0,"intAwayScore":2}', new['id']))
    app_module.cleanup_duplicate_matches(conn.cursor())
    kept = dict(conn.execute('SELECT * FROM matches').fetchone())
    assert kept['id'] == old['id']
    assert kept['last_synced_at'] == new['last_synced_at']
    assert match_status_truth(kept)['is_finished'] is True
    assert conn.execute('SELECT COUNT(*) FROM live_matches').fetchone()[0] == 0


def test_optional_priority_clock_column_is_cleared_with_old_snapshot(app_module, duplicate_db):
    conn, old, new = duplicate_db
    conn.execute('ALTER TABLE matches ADD COLUMN live_updated_at TEXT')
    conn.execute('UPDATE matches SET live_updated_at=? WHERE id=?', ('invalid-old-clock',old['id']))
    app_module.cleanup_duplicate_matches(conn.cursor())
    kept = dict(conn.execute('SELECT * FROM matches').fetchone())
    assert kept['live_updated_at'] is None
    assert kept['last_synced_at'] == new['last_synced_at']
    assert match_status_truth(kept)['is_live'] is True
