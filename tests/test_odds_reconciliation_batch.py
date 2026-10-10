"""Replaying saved prices must keep identity and observation order in one transaction."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
import sqlite3

import pytest
from test_odds_admin_pipeline import odds_db, fixture


def save_snapshot(conn, sport, event, index):
    conn.execute("""INSERT INTO odds_snapshots
        (id,match_id,commence_time,created_at,payload_json,sport_key,league_name)
        VALUES(?,?,?,?,?,?,?)""", (str(index), 'unlinked', event['commence_time'],
        str(index).zfill(6), json.dumps(event), sport['odds_key'], sport['name']))


def test_replay_reads_identity_once_per_window_without_loading_raw_history(odds_db):
    app = odds_db
    sport, event, match = fixture(app)
    match['raw_json'] = json.dumps({'retained': 'x' * 32768})
    app.upsert_sportsdb_matches([match])
    with sqlite3.connect(app.DB_PATH) as conn:
        for i in range(40):
            save_snapshot(conn, sport, event, i)
    conn = app.db()
    statements = []
    conn.set_trace_callback(statements.append)
    try:
        app._reconcile_cached_odds(conn.cursor(), {match['match_date']})
        reads = [sql for sql in statements if 'FROM matches WHERE match_date BETWEEN' in sql]
        assert len(reads) == 1
        assert '*' not in reads[0] and 'raw_json' not in reads[0]
        assert conn.execute("SELECT count(*) FROM odds_snapshots WHERE match_id=?", (match['id'],)).fetchone()[0] == 40
        row = dict(conn.execute('SELECT * FROM matches').fetchone())
        assert row['raw_json'] == match['raw_json'] and row['source'] == match['source']
        assert app.v565_extract_odds(row)['home'] == 2.1
    finally:
        conn.close()


@pytest.mark.parametrize('second_time,second_price,accepted', [
    ('2000-01-01T00:00:00Z', 9, False),
    ('2099-01-01T00:00:00Z', 4, True),
    ('invalid-time', 5, False),
])
def test_replay_rereads_updated_price_clock_inside_same_transaction(odds_db, second_time, second_price, accepted):
    app = odds_db
    sport, event, match = fixture(app)
    app.upsert_sportsdb_matches([match])
    event['bookmakers'][1]['last_update'] = '2099-01-01T00:00:00Z'
    later = deepcopy(event)
    later['bookmakers'][1]['last_update'] = second_time
    later['bookmakers'][1]['markets'][0]['outcomes'][0]['price'] = second_price
    with sqlite3.connect(app.DB_PATH) as conn:
        save_snapshot(conn, sport, event, 1)
        save_snapshot(conn, sport, later, 2)
    conn = app.db()
    try:
        app._reconcile_cached_odds(conn.cursor(), {match['match_date']})
        row = dict(conn.execute('SELECT * FROM matches').fetchone())
        assert app.v565_extract_odds(row)['home'] == (second_price if accepted else 2.1)
        assert row['odds_updated_at'] == '2099-01-01T00:00:00Z'
        assert conn.execute("SELECT match_id FROM odds_snapshots WHERE id='2'").fetchone()[0] == (match['id'] if accepted else 'unlinked')
    finally:
        conn.close()


@pytest.mark.parametrize('other_source,expected', [('The Odds API', 'sportsdb-qa'), ('TheSportsDB API', None)])
def test_cached_candidates_preserve_provider_preference_and_ambiguity(odds_db, other_source, expected):
    app = odds_db
    sport, event, match = fixture(app)
    app.upsert_sportsdb_matches([match])
    conn = app.db()
    try:
        row = dict(conn.execute('SELECT * FROM matches').fetchone())
        row.update(id='other', source=other_source)
        conn.execute(f"INSERT INTO matches({','.join(row)}) VALUES({','.join('?' for _ in row)})", tuple(row.values()))
        save_snapshot(conn, sport, event, 1)
        app._reconcile_cached_odds(conn.cursor(), {match['match_date']})
        linked = conn.execute('SELECT match_id FROM odds_snapshots').fetchone()[0]
        assert linked == (expected or 'unlinked')
    finally:
        conn.close()


def test_payload_day_and_individual_window_govern_candidates(odds_db):
    app = odds_db
    sport, event, match = fixture(app)
    event['commence_time'] = '2026-10-10T23:30:00Z'
    match.update(match_date='2026-10-11', kickoff_iso='2026-10-11T01:30:00+02:00')
    app.upsert_sportsdb_matches([match])
    conn = app.db()
    try:
        # Same instant but outside this event's three-day calendar window.
        row = dict(conn.execute('SELECT * FROM matches').fetchone())
        row.update(id='out-of-window', match_date='2026-10-14')
        conn.execute(f"INSERT INTO matches({','.join(row)}) VALUES({','.join('?' for _ in row)})", tuple(row.values()))
        save_snapshot(conn, sport, event, 1)
        # Stored date selects the snapshot, payload controls actual identity.
        conn.execute("UPDATE odds_snapshots SET commence_time='2026-10-14T10:00:00Z'")
        app._reconcile_cached_odds(conn.cursor(), {'2026-10-14'})
        assert conn.execute('SELECT match_id FROM odds_snapshots').fetchone()[0] == match['id']
        assert not conn.execute("SELECT odds_h2h_json FROM matches WHERE id='out-of-window'").fetchone()[0]
    finally:
        conn.close()


def test_candidates_are_built_after_dedupe_and_see_uncommitted_sports_rows(odds_db):
    app = odds_db
    sport, event, match = fixture(app)
    app.upsert_odds_snapshots([(sport, event)])
    duplicate = dict(match, id='duplicate', external_id='different-provider-reference')
    result = app.upsert_sportsdb_matches([match, duplicate])
    assert result['duplicates_removed'] == 1
    with sqlite3.connect(app.DB_PATH) as conn:
        rows = conn.execute('SELECT id,odds_h2h_json FROM matches').fetchall()
        assert len(rows) == 1 and rows[0][1]
        assert conn.execute('SELECT match_id FROM odds_snapshots').fetchone()[0] == rows[0][0]


def test_price_failure_rolls_back_sports_and_earlier_price_links(odds_db, monkeypatch):
    app = odds_db
    sport, event, match = fixture(app)
    with sqlite3.connect(app.DB_PATH) as conn:
        save_snapshot(conn, sport, event, 1)
        save_snapshot(conn, sport, event, 2)
    original = app._attach_odds_snapshot
    calls = []
    def fail_second(*args):
        calls.append(1)
        if len(calls) == 2:
            raise sqlite3.OperationalError('synthetic write failure')
        return original(*args)
    monkeypatch.setattr(app, '_attach_odds_snapshot', fail_second)
    with pytest.raises(sqlite3.OperationalError):
        app.upsert_sportsdb_matches([match])
    with sqlite3.connect(app.DB_PATH) as conn:
        assert conn.execute('SELECT count(*) FROM matches').fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM odds_snapshots WHERE match_id='unlinked'").fetchone()[0] == 2
