"""Match association stays exact while avoiding unrelated provider payloads."""
import sqlite3
from contextlib import closing

import pytest

from engines import sportsdb_highlights_engine as media


def event(**overrides):
    return {'idEvent':'123', 'strHomeTeam':'Home', 'strAwayTeam':'Away',
            'dateEvent':'2026-10-07', 'strLeague':'League', 'idLeague':'42',
            'strVideo':'https://www.youtube.com/watch?v=abcdefghijk', **overrides}


@pytest.fixture(params=[False, True], ids=['legacy', 'indexed'])
def database(tmp_path, request):
    path=tmp_path/'matches.sqlite'
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute('CREATE TABLE matches(id TEXT PRIMARY KEY,external_id TEXT,source TEXT,'
                     'provider TEXT,home_team TEXT,away_team TEXT,match_date TEXT,'
                     'competition_name TEXT,league_name TEXT,league_id TEXT,league TEXT,raw_json TEXT)')
        conn.execute('INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                     ('m1','sportsdb-123','TheSportsDB','','Home','Away','2026-10-07',
                      'League','','42','','x'*32768))
        if request.param:
            conn.execute('CREATE INDEX idx_matches_source_external ON matches(source,external_id)')
            conn.execute('CREATE INDEX idx_matches_date_status ON matches(match_date)')
    return path


def test_identity_lookup_never_reads_provider_payload(database):
    with closing(media._connect(database)) as conn:
        def only_identity(action, table, column, *_):
            return sqlite3.SQLITE_DENY if action==sqlite3.SQLITE_READ and table=='matches' and column=='raw_json' else sqlite3.SQLITE_OK
        conn.set_authorizer(only_identity)
        assert media._find_match(conn,event())=='m1'
        assert media._find_match(conn,event(idEvent='999'))=='m1'  # Dated fallback.


def test_provider_collision_and_duplicate_id_do_not_choose_arbitrarily(database):
    with closing(media._connect(database)) as conn, conn:
        conn.execute("INSERT INTO matches SELECT 'foreign','123','API-Football',provider,"
                     "home_team,away_team,match_date,competition_name,league_name,league_id,league,raw_json FROM matches")
        assert media._find_match(conn,event())=='m1'
        conn.execute("INSERT INTO matches SELECT 'duplicate','123','TheSportsDB',provider,"
                     "home_team,away_team,match_date,competition_name,league_name,league_id,league,raw_json FROM matches WHERE id='m1'")
        assert media._find_match(conn,event()) is None


def test_fallback_keeps_ambiguity_and_candidate_cap(database):
    with closing(media._connect(database)) as conn, conn:
        conn.execute("INSERT INTO matches SELECT 'duplicate','999','Other',provider,"
                     "home_team,away_team,match_date,competition_name,league_name,league_id,league,raw_json FROM matches")
        assert media._find_match(conn,event(idEvent='unknown')) is None
        conn.execute("DELETE FROM matches WHERE id='duplicate'")
        conn.executemany("INSERT INTO matches(id,home_team,away_team,match_date,competition_name) VALUES(?,'Other','Team','2026-10-07','League')",
                         [(str(i),) for i in range(500)])
        assert media._find_match(conn,event(idEvent='unknown')) is None
        conn.execute("DELETE FROM matches WHERE id='499'")
        assert media._find_match(conn,event(idEvent='unknown'))=='m1'


def test_midnight_and_competition_checks_survive_projection(database):
    with closing(media._connect(database)) as conn, conn:
        conn.execute("UPDATE matches SET match_date='2026-10-08',source='API-Football',competition_name='',league_name='',league='League'")
        item=event(strTimestamp='2026-10-07T23:30:00Z')
        assert media._find_match(conn,item)=='m1'
        assert media._find_match(conn,{**item,'strLeague':'Other'}) is None
        assert media._find_match(conn,{**item,'strTimestamp':'invalid'}) is None


def test_lookup_tracks_transaction_snapshot_and_next_committed_identity(database):
    with closing(media._connect(database)) as reader, closing(media._connect(database)) as writer:
        reader.execute('PRAGMA journal_mode=WAL')
        reader.execute('BEGIN')
        assert media._find_match(reader,event())=='m1'
        writer.execute("UPDATE matches SET away_team='New opponent' WHERE id='m1'")
        writer.commit()
        assert media._find_match(reader,event())=='m1'
        reader.commit()
        assert media._find_match(reader,event()) is None
        reader.execute("UPDATE matches SET away_team='Away' WHERE id='m1'")
        assert media._find_match(reader,event())=='m1'
        reader.rollback()
        assert media._find_match(reader,event()) is None


def test_changed_identity_revokes_existing_approval(database):
    media.ensure_sportsdb_highlights_schema(database)
    with closing(media._connect(database)) as conn, conn:
        saved=media._upsert_highlight(conn,event())
        conn.execute("UPDATE sportsdb_match_highlights SET rights_status='LICENSED',commercial_use_status='ALLOWED',rights_verified_at='2026-10-07'")
        conn.execute("UPDATE matches SET away_team='New opponent'")
        updated=media._upsert_highlight(conn,event())
        assert updated['id']==saved['id'] and updated['match_id']==''
        assert updated['rights_status']=='REVIEW_REQUIRED'
        assert tuple(conn.execute('SELECT commercial_use_status,rights_verified_at FROM sportsdb_match_highlights').fetchone())==('UNKNOWN','')
