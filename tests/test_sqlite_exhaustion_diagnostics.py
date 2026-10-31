"""Actual SQLite allocation/interruption failures; synthetic fixtures only."""
from contextlib import closing
import hashlib, json, random, sqlite3

import pytest
from engines import match_record_archive as archive
from engines import statistics_payload_store as store


def body(large=False):
    rng=random.Random(61327)
    text=(''.join(rng.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(150000))+' x '*25000) if large else 'preservar exactamente Águila\n'*150
    return {'team':{'id':10,'name':'Equipo de prueba'},'statistics':[{'type':'Shots on Goal','value':0}],
            'unknown_provider_field':text}


@pytest.fixture
def db(tmp_path):
    with closing(sqlite3.connect(tmp_path/'synthetic.sqlite3')) as conn:
        conn.execute('PRAGMA journal_mode=WAL')
        archive.ensure_match_record_schema(conn)
        assert archive.record_observation(conn,'123','statistics',[],received_at='2026-10-29T20:00:00Z')['stored']
        conn.execute('CREATE TABLE committed_values(id TEXT PRIMARY KEY,value TEXT NOT NULL)')
        conn.execute("INSERT INTO committed_values VALUES('before','preservado')")
        conn.execute('''CREATE TABLE api_football_match_stats_history(
            id TEXT PRIMARY KEY, fixture_id TEXT, team_id TEXT, team_name TEXT,
            stat_name TEXT, stat_value TEXT, numeric_value REAL, payload_json TEXT, captured_at TEXT)''')
        for i in range(4):
            conn.execute('INSERT INTO api_football_match_stats_history VALUES(?,?,?,?,?,?,?,?,?)',
                         (str(i),'123','10','Equipo de prueba','Shots on Goal','0',0,
                          json.dumps(body(),ensure_ascii=False,indent=2),'2026-10-29T20:00:00Z'))
        conn.commit()
        yield conn


def fingerprint(conn):
    result={}
    for name,sql in conn.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"):
        quoted='"'+name.replace('"','""')+'"'
        try:rows=conn.execute('SELECT rowid,* FROM '+quoted).fetchall()
        except sqlite3.OperationalError:rows=conn.execute('SELECT * FROM '+quoted).fetchall()
        encoded=sorted(json.dumps([{'blob':v.hex()} if isinstance(v,bytes) else v for v in row],
                                  ensure_ascii=True,separators=(',',':')) for row in rows)
        result[name]=(sql,len(rows),hashlib.sha256('\n'.join(encoded).encode()).hexdigest())
    return result


def invoke(conn,kind,large=False):
    if kind=='archive':
        return archive.record_observation(conn,'888','statistics',[body(large)],received_at='2026-10-29T21:00:00Z')
    return store.rewrite_history_batch(conn,limit=4)


@pytest.mark.parametrize('kind',['archive','rewrite'])
def test_real_sqlite_full_keeps_original_error_and_committed_rows(db,kind):
    before=fingerprint(db)
    old_cap=db.execute('PRAGMA max_page_count').fetchone()[0]
    pages=db.execute('PRAGMA page_count').fetchone()[0]
    # Rewrite must create its missing blob table. Archive's large receipt must
    # allocate more than two extra pages. No filesystem is filled or resized.
    cap=pages+(2 if kind=='archive' else 0)
    assert db.execute('PRAGMA max_page_count='+str(cap)).fetchone()[0]==cap
    try:
        db.execute('BEGIN IMMEDIATE')
        with pytest.raises(sqlite3.OperationalError) as caught:
            invoke(db,kind,large=True)
        assert caught.value.sqlite_errorcode==sqlite3.SQLITE_FULL
        # Whether FULL aborts a statement or the whole transaction depends on
        # where it happens. The caller must roll back either remaining state.
        db.rollback()
        assert fingerprint(db)==before
    finally:
        db.rollback();db.execute('PRAGMA max_page_count='+str(old_cap))
    assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
    db.execute("INSERT INTO committed_values VALUES('after','nueva transaccion valida')")
    db.commit()
    assert db.execute('SELECT COUNT(*) FROM committed_values').fetchone()[0]==2


@pytest.mark.parametrize('kind',['archive','rewrite'])
def test_real_sqlite_interrupt_keeps_original_error_and_committed_rows(db,kind):
    if kind=='rewrite':
        db.execute('BEGIN');store.ensure_schema(db);db.commit()
    before=fingerprint(db)
    target='INSERT INTO MATCH_RECORD_OBSERVATIONS' if kind=='archive' else 'INSERT INTO STATISTICS_PAYLOAD_BLOBS_V1'
    active=[False]
    def trace(sql):
        if sql.lstrip().upper().startswith(target):active[0]=True
    db.set_trace_callback(trace)
    db.set_progress_handler(lambda:int(active[0]),1)
    try:
        db.execute('BEGIN IMMEDIATE')
        with pytest.raises(sqlite3.OperationalError) as caught:
            invoke(db,kind)
    finally:
        db.set_progress_handler(None,0);db.set_trace_callback(None)
    assert active[0], 'The real INSERT interruption was not reached'
    assert caught.value.sqlite_errorcode==sqlite3.SQLITE_INTERRUPT
    db.rollback()
    assert fingerprint(db)==before
    assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]


@pytest.mark.parametrize('kind',['archive','rewrite'])
def test_native_transaction_abort_preserves_original_error_and_committed_rows(db,kind):
    table='match_record_observations' if kind=='archive' else 'api_football_match_stats_history'
    operation='INSERT' if kind=='archive' else 'UPDATE'
    condition="NEW.fixture_id='888'" if kind=='archive' else "NEW.id='2'"
    # Native SQLite RAISE(ROLLBACK) deterministically aborts the outer
    # transaction and removes all savepoints, without mocking a connection.
    db.execute('CREATE TRIGGER owned_transaction_abort BEFORE '+operation+' ON '+table+' WHEN '+condition+
               " BEGIN SELECT RAISE(ROLLBACK,'owned native transaction abort'); END")
    db.commit()
    before=fingerprint(db)
    db.execute('BEGIN IMMEDIATE')
    db.execute("INSERT INTO committed_values VALUES('outer','uncommitted work must abort')")
    with pytest.raises(sqlite3.IntegrityError) as caught:invoke(db,kind)
    assert caught.value.sqlite_errorcode==sqlite3.SQLITE_CONSTRAINT_TRIGGER
    assert not db.in_transaction
    assert fingerprint(db)==before
    assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]


@pytest.mark.parametrize('kind',['archive','rewrite'])
def test_statement_abort_keeps_outer_work_and_rolls_back_only_own_savepoint(db,kind):
    table='match_record_observations' if kind=='archive' else 'api_football_match_stats_history'
    operation='INSERT' if kind=='archive' else 'UPDATE'
    condition="NEW.fixture_id='888'" if kind=='archive' else "NEW.id='2'"
    db.execute('CREATE TRIGGER owned_statement_abort BEFORE '+operation+' ON '+table+' WHEN '+condition+
               " BEGIN SELECT RAISE(ABORT,'owned expected failure'); END")
    db.commit()
    db.execute('BEGIN IMMEDIATE')
    db.execute("INSERT INTO committed_values VALUES('outer','trabajo del llamador')")
    before=fingerprint(db)
    with pytest.raises(sqlite3.IntegrityError):invoke(db,kind)
    assert db.in_transaction
    assert fingerprint(db)==before
    db.commit()
    assert db.execute('SELECT COUNT(*) FROM committed_values').fetchone()[0]==2
    assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
