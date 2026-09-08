"""SIMULATED_QA: provider-shaped input through the existing sports store."""
import copy
from datetime import datetime, timedelta
import json
import sqlite3
from zoneinfo import ZoneInfo

import pytest

from engines import historical_warehouse_engine as warehouse
from engines.v935_launch_trust_engine import match_status_truth


@pytest.fixture
def vertical(app_module, tmp_path, monkeypatch):
    path = tmp_path / 'sports-only.sqlite'
    monkeypatch.setattr(app_module, 'DB_PATH', str(path))
    monkeypatch.setattr(app_module, '_SEEDED_DB_PATH', None)
    monkeypatch.setattr(app_module, '_SEEDING_DB_PATH', None)
    app_module.init_db()
    now = datetime.now(ZoneInfo('Europe/Madrid'))
    monkeypatch.setattr(warehouse, 'utc_now', lambda: now.isoformat())
    event = {'idEvent':'QA-VERTICAL-ONLY', 'strSport':'Soccer',
             'strHomeTeam':'Real Madrid', 'strAwayTeam':'FC Barcelona',
             'idLeague':'4335', 'strLeague':'Spanish La Liga', 'strSeason':'2026-2027',
             'strTimestamp':now.isoformat(), 'dateEvent':now.date().isoformat(),
             'strTime':'18:00:00', 'strStatus':'LIVE', 'strProgress':'67',
             'intHomeScore':None, 'intAwayScore':None}
    return app_module, path, now, event


def persist(vertical, event, observed):
    app, path, _, _ = vertical
    before = copy.deepcopy(event)
    item = app.sportsdb_event_to_match(event, provider_observed_at=observed)
    assert event == before
    app.upsert_sportsdb_matches([item])
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        return dict(conn.execute('SELECT * FROM matches WHERE id=?', (item['id'],)).fetchone())


@pytest.mark.parametrize('home,away,expected,label', [(None,None,(None,None),'unknown'),('0','0',(0.0,0.0),'draw'),('2',None,(2.0,None),'unknown'),('1','0',(1.0,0.0),'home')])
def test_history_keeps_absence_distinct_from_confirmed_zero(vertical, home, away, expected, label):
    app, path, now, event = vertical
    event.update(intHomeScore=home, intAwayScore=away)
    row = persist(vertical, event, (now-timedelta(seconds=20)).isoformat())
    source_before = copy.deepcopy(row)
    warehouse.snapshot_warehouse(str(path))
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        fact = dict(conn.execute('SELECT * FROM warehouse_match_facts WHERE match_id=?', (row['id'],)).fetchone())
        assert dict(conn.execute('SELECT * FROM matches WHERE id=?', (row['id'],)).fetchone()) == source_before
    assert (fact['home_score'],fact['away_score']) == expected
    assert fact['result_label'] == label
    replay = json.loads(fact['payload_json'])
    assert replay['last_synced_at'] == row['last_synced_at']
    assert replay['external_id'] == 'QA-VERTICAL-ONLY'
    assert fact['match_id'] == row['id']
    display = app.client_match_display_context(row, now_madrid=now)
    assert display['status_info']['is_live'] is True
    assert display['client_live_minute'] == '67'


def test_same_snapshot_is_idempotent_and_correction_keeps_match_identity(vertical):
    app, path, now, event = vertical
    row = persist(vertical, event, now.isoformat())
    warehouse.snapshot_warehouse(str(path))
    warehouse.snapshot_warehouse(str(path))
    event.update(intHomeScore='0', intAwayScore='0')
    corrected = persist(vertical, event, now.isoformat())
    warehouse.snapshot_warehouse(str(path))
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_match_facts').fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM warehouse_sync_runs').fetchone()[0] == 3
        assert conn.execute('SELECT home_score,away_score FROM warehouse_match_facts').fetchone() == (0.0,0.0)
    assert corrected['id'] == row['id']


@pytest.mark.parametrize('status,age,expected', [('LIVE',20,True),('LIVE',600,False),('LIVE',-900,False),('LIVE',None,False),('HT',20,True),('POSTPONED',20,False),('FT',20,False)])
def test_history_does_not_rejuvenate_lifecycle(vertical, status, age, expected):
    app, path, now, event = vertical
    event.update(strStatus=status, intHomeScore='0', intAwayScore='0')
    row = persist(vertical, event, (now-timedelta(seconds=age)).isoformat() if age is not None else '')
    warehouse.snapshot_warehouse(str(path))
    with sqlite3.connect(path) as conn:
        payload = json.loads(conn.execute('SELECT payload_json FROM warehouse_match_facts').fetchone()[0])
    assert match_status_truth(payload, now=now)['is_live'] is expected
    assert payload['last_synced_at'] == row['last_synced_at']
    assert payload['minute'] == row['minute']


def test_raw_event_clock_cannot_replace_current_match_clock(vertical):
    app, path, now, event = vertical
    event['qa_event_history'] = [{'minute':'5', 'type':'goal'}]
    event.update(strProgress='91', intHomeScore='0', intAwayScore='0')
    row = persist(vertical, event, now.isoformat())
    warehouse.snapshot_warehouse(str(path))
    with sqlite3.connect(path) as conn:
        payload = json.loads(conn.execute('SELECT payload_json FROM warehouse_match_facts').fetchone()[0])
    assert payload['minute'] == '91'
    assert json.loads(payload['raw_json'])['qa_event_history'][0]['minute'] == '5'
    assert payload['season'] == '2026-2027'
    assert payload['competition_id'] == '4335'
    display = app.client_match_display_context(payload, now_madrid=now)
    assert display['client_live_minute'] == '91'
    assert match_status_truth(payload, now=now+timedelta(hours=1))['is_live'] is False
