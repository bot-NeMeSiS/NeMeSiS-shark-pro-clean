"""Synthetic archive metadata only. No production DB or external connections."""
from contextlib import closing
import socket
import sqlite3
import pytest
from engines import match_record_archive as archive

STAMP = '2026-09-22T10:00:00+00:00'

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('No network in archive metadata tests')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)

@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'synthetic.sqlite'
    with closing(sqlite3.connect(path)) as conn, conn:
        archive.ensure_match_record_schema(conn)
        archive.record_observation(conn, '123', 'events', [], received_at=STAMP)
    return path

def damage(path, column, value):
    assert column in {'byte_count', 'row_count'}
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute('UPDATE match_record_archive_budget SET '+column+'=? WHERE id=1', (value,))

def observations(conn):
    return conn.execute('SELECT * FROM match_record_observations ORDER BY id').fetchall()

@pytest.mark.parametrize('column', ['byte_count', 'row_count'])
@pytest.mark.parametrize('value', [-1, 0.5, 'unknown', b'\x01'])
def test_invalid_metadata_does_not_authorize_append(db, column, value):
    damage(db, column, value)
    with closing(sqlite3.connect(db)) as conn, conn:
        before = observations(conn)
        budget = conn.execute('SELECT * FROM match_record_archive_budget').fetchall()
        result = archive.record_observation(conn, '123', 'statistics', [], received_at=STAMP)
        assert result == {'stored':False, 'reason':'ARCHIVE_BUDGET_UNVERIFIABLE'}
        assert observations(conn) == before
        assert conn.execute('SELECT * FROM match_record_archive_budget').fetchall() == budget
        assert conn.execute('SELECT reason,count FROM match_record_archive_gaps').fetchall() == [('ARCHIVE_BUDGET_UNVERIFIABLE',1)]

@pytest.mark.parametrize('column', ['byte_count', 'row_count'])
@pytest.mark.parametrize('value', [-1, 0.5, 'unknown', b'\x01'])
def test_invalid_metadata_is_not_healthy(db, column, value):
    damage(db, column, value)
    before = db.read_bytes()
    with closing(sqlite3.connect(db)) as conn:
        assert archive.archive_health(conn) == {'state':'READ_UNAVAILABLE','coverage_complete':False}
    assert db.read_bytes() == before

def test_missing_budget_row_is_unknown_not_full(db):
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute('DELETE FROM match_record_archive_budget')
        before = observations(conn)
        result = archive.record_observation(conn,'123','statistics',[],received_at=STAMP)
        assert result['reason'] == 'ARCHIVE_BUDGET_UNVERIFIABLE'
        assert observations(conn) == before
        assert not conn.execute('SELECT 1 FROM match_record_archive_budget').fetchone()

def test_gap_remains_in_the_callers_transaction(db):
    damage(db,'row_count',-1)
    with closing(sqlite3.connect(db)) as conn:
        result = archive.record_observation(conn,'123','statistics',[],received_at=STAMP)
        assert result['reason'] == 'ARCHIVE_BUDGET_UNVERIFIABLE'
        assert conn.in_transaction
        conn.rollback()
    with closing(sqlite3.connect(db)) as conn:
        assert not conn.execute('SELECT 1 FROM match_record_archive_gaps').fetchone()
        assert len(observations(conn)) == 1

def test_full_archive_is_different_from_unverifiable_budget(db,monkeypatch):
    monkeypatch.setattr(archive,'MAX_OBSERVATIONS',1)
    with closing(sqlite3.connect(db)) as conn, conn:
        assert archive.record_observation(conn,'123','statistics',[],received_at=STAMP)['reason'] == 'ARCHIVE_CAP_REACHED'
        assert len(observations(conn)) == 1
        assert archive.archive_health(conn)['gap_count'] == 1

def test_new_empty_archive_has_real_zero_and_can_record(tmp_path):
    with closing(sqlite3.connect(tmp_path/'empty.sqlite')) as conn, conn:
        archive.ensure_match_record_schema(conn)
        health=archive.archive_health(conn)
        assert health['state'] == 'EMPTY' and health['observations'] == 0
        assert archive.record_observation(conn,'123','statistics',[],received_at=STAMP)['stored']
        assert archive.archive_health(conn)['observations'] == 1

def test_integer_stored_through_sqlite_affinity_is_valid(db):
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute('UPDATE match_record_archive_budget SET row_count=?', (str(len(observations(conn))),))
        assert conn.execute('SELECT typeof(row_count) FROM match_record_archive_budget').fetchone()[0] == 'integer'
        assert archive.record_observation(conn,'123','statistics',[],received_at=STAMP)['stored']

def test_health_never_claims_whole_database_reconciliation(db):
    with closing(sqlite3.connect(db)) as conn:
        health=archive.archive_health(conn)
        assert health['coverage_complete'] is False
        assert health['size_scope'] == 'ENCODED_PAYLOAD_AND_CONTEXT_NOT_SQLITE_FILE'
