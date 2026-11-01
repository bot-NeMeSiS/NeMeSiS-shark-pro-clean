from pathlib import Path
import sqlite3
import pytest
from engines.bounded_fixture_read import read_match_rows as selected_match_rows


class Proxy:
    def __init__(self, conn, *, after_keys=None, fail_phase=None, missing_key=False, no_getlimit=False):
        self.conn=conn; self.sql=[]; self.after_keys=after_keys; self.fail_phase=fail_phase
        self.missing_key=missing_key; self.no_getlimit=no_getlimit
    @property
    def in_transaction(self): return self.conn.in_transaction
    def getlimit(self, category):
        if self.no_getlimit: raise AssertionError('unsupported getlimit should be tested with noncallable instance field')
        return self.conn.getlimit(category)
    def execute(self, sql, params=()):
        self.sql.append(sql)
        key_query=sql.startswith('SELECT "') and ' NOT INDEXED' in sql
        full_query=sql.startswith('SELECT "') and '", * FROM' in sql
        if self.fail_phase=='keys' and key_query:
            raise sqlite3.OperationalError('interrupted')
        if self.fail_phase=='rows' and full_query:
            raise sqlite3.OperationalError('database or disk is full')
        cur=self.conn.execute(sql,params)
        if key_query and self.after_keys:
            callback=self.after_keys
            class Cursor:
                def fetchall(inner):
                    rows=cur.fetchall();callback();return rows
            return Cursor()
        if full_query and self.missing_key:
            class Cursor:
                def fetchall(inner): return cur.fetchall()[1:]
            return Cursor()
        return cur

def make_db(schema, count=37):
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE matches('+schema+')')
    columns=[r[1] for r in db.execute('PRAGMA table_xinfo(matches)') if r[6]==0]
    fields=[c for c in columns if c in ('id','sort_key','home_team','raw_json','nullable')]
    records=[]
    for n in range(count):
        values={'id': n if 'INTEGER PRIMARY KEY' in schema else (None if n%7==0 else str(n)),
                'sort_key':n%3, 'home_team':f'OWNED_ñ_球队_{n}', 'raw_json':sqlite3.Binary(bytes([n%256])*256),
                'nullable':None if n%2==0 else 'owned'}
        records.append(tuple(values[k] for k in fields))
    db.executemany('INSERT INTO matches('+','.join('"'+k+'"' for k in fields)+') VALUES('+','.join('?' for _ in fields)+')',records)
    db.commit()
    return db

SCHEMAS=[
    'id TEXT, sort_key INTEGER, home_team TEXT, raw_json BLOB, nullable TEXT',
    'id TEXT PRIMARY KEY, sort_key INTEGER, home_team TEXT, raw_json BLOB, nullable TEXT',
    'id INTEGER PRIMARY KEY, sort_key INTEGER, home_team TEXT, raw_json BLOB, nullable TEXT',
    'id INTEGER PRIMARY KEY DESC, sort_key INTEGER, home_team TEXT, raw_json BLOB, nullable TEXT',
    'id TEXT, rowid TEXT, sort_key INTEGER, home_team TEXT, raw_json BLOB, nullable TEXT',
    'id TEXT, _rowid_ TEXT, sort_key INTEGER, home_team TEXT, raw_json BLOB, nullable TEXT',
    'id TEXT, _rowid_ TEXT, rowid TEXT, sort_key INTEGER, home_team TEXT, raw_json BLOB, nullable TEXT',
    'id TEXT, _rowid_ TEXT, rowid TEXT, oid TEXT, sort_key INTEGER, home_team TEXT, raw_json BLOB, nullable TEXT',
    'id TEXT, "_RoWiD_" TEXT GENERATED ALWAYS AS (home_team) VIRTUAL, sort_key INTEGER, home_team TEXT, raw_json BLOB, nullable TEXT',
    'id TEXT, _rowid_ TEXT, rowid TEXT, oid TEXT GENERATED ALWAYS AS (home_team) STORED, sort_key INTEGER, home_team TEXT, raw_json BLOB, nullable TEXT',
]
@pytest.mark.parametrize('schema',SCHEMAS)
@pytest.mark.parametrize('limit',[1,13,37,100,0,-1])
def test_schema_ties_types_full_dict_and_order(schema,limit):
    db=make_db(schema)
    try:
        db.execute('BEGIN')
        sql=' ORDER BY sort_key DESC, nullable ASC'
        expected=[dict(r) for r in db.execute('SELECT * FROM matches'+sql+' LIMIT ?',(limit,))]
        proxy=Proxy(db);actual=selected_match_rows(proxy,sql,[limit])
        assert actual==expected and [list(r) for r in actual]==[list(r) for r in expected]
        all_shadowed=all(name.casefold() in {r[1].casefold() for r in db.execute('PRAGMA table_xinfo(matches)')} for name in ('_rowid_','rowid','oid'))
        optimized=any('NOT INDEXED' in s for s in proxy.sql)
        assert optimized == (limit>0 and not all_shadowed)
        assert not any(s.startswith(('INSERT','UPDATE','DELETE','CREATE','DROP')) for s in proxy.sql)
        assert db.total_changes==37
    finally:db.close()

@pytest.mark.parametrize('kind',['index','cover','no_order','no_transaction','old_table_list','no_limit_api','unknown_plan','without_rowid','virtual'])
def test_conservative_fallback(kind):
    if kind=='without_rowid':
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
        db.execute('CREATE TABLE matches(id INTEGER PRIMARY KEY,sort_key INT, home_team TEXT) WITHOUT ROWID')
        db.executemany('INSERT INTO matches VALUES(?,?,?)',[(n,n%3,'OWNED') for n in range(37)]);db.commit()
    elif kind=='virtual':
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
        db.execute('CREATE VIRTUAL TABLE matches USING fts5(id, sort_key, home_team)')
        db.executemany('INSERT INTO matches VALUES(?,?,?)',[(str(n),str(n%3),'OWNED') for n in range(37)]);db.commit()
    else:db=make_db(SCHEMAS[0])
    order=' ORDER BY sort_key DESC'
    if kind in ('index','cover'):
        db.execute('CREATE INDEX owned_sort ON matches(sort_key DESC)')
    if kind=='no_order':order=''
    if kind!='no_transaction':db.execute('BEGIN')
    proxy=Proxy(db)
    if kind=='no_limit_api':proxy.getlimit=None
    original_execute=proxy.execute
    if kind in ('old_table_list','unknown_plan'):
        def execute(sql,params=()):
            if (kind=='old_table_list' and sql.startswith('PRAGMA main.table_list')) or (kind=='unknown_plan' and sql.startswith('EXPLAIN')):
                proxy.sql.append(sql)
                class Cursor:
                    def fetchall(self): return [] if kind=='old_table_list' else [(0,0,0,'UNKNOWN PLAN FORMAT')]
                    def __iter__(self): return iter(self.fetchall())
                return Cursor()
            return original_execute(sql,params)
        proxy.execute=execute
    try:
        expected=[dict(r) for r in db.execute('SELECT * FROM matches'+order+' LIMIT ?',(13,))]
        assert selected_match_rows(proxy,order,[13])==expected
        assert not any('NOT INDEXED' in s for s in proxy.sql)
        assert sum(s.startswith('SELECT *') for s in proxy.sql)==1
    finally:db.close()

@pytest.mark.parametrize('phase,message',[('keys','interrupted'),('rows','database or disk is full')])
def test_sql_errors_are_never_retried_as_old_query(phase,message):
    db=make_db(SCHEMAS[0]);db.execute('BEGIN');proxy=Proxy(db,fail_phase=phase)
    try:
        with pytest.raises(sqlite3.OperationalError,match=message):
            selected_match_rows(proxy,' ORDER BY sort_key',[13])
        assert not any(s.startswith('SELECT *') for s in proxy.sql)
    finally:db.close()

def test_missing_selected_key_fails_closed():
    db=make_db(SCHEMAS[0]);db.execute('BEGIN');proxy=Proxy(db,missing_key=True)
    try:
        with pytest.raises(sqlite3.OperationalError,match='snapshot changed'):
            selected_match_rows(proxy,' ORDER BY sort_key',[13])
        assert not any(s.startswith('SELECT *') for s in proxy.sql)
    finally:db.close()

@pytest.mark.parametrize('variable_limit',[7,200,999])
def test_chunks_respect_actual_sqlite_variable_limit(variable_limit):
    db=make_db(SCHEMAS[0],623);db.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER,variable_limit)
    db.execute('BEGIN');proxy=Proxy(db)
    try:
        expected=[dict(r) for r in db.execute('SELECT * FROM matches ORDER BY sort_key LIMIT 601')]
        assert selected_match_rows(proxy,' ORDER BY sort_key',[601])==expected
        assert sum('", * FROM' in s for s in proxy.sql)==(601+min(200,variable_limit)-1)//min(200,variable_limit)
    finally:db.close()

def test_reader_snapshot_survives_concurrent_update_delete_insert_and_schema(tmp_path):
    path=tmp_path/'OWNED_ONLY.sqlite';writer=sqlite3.connect(path,timeout=.1)
    writer.execute('PRAGMA journal_mode=WAL')
    writer.execute('CREATE TABLE matches(id INTEGER PRIMARY KEY,sort_key INTEGER,home_team TEXT)')
    writer.executemany('INSERT INTO matches VALUES(?,?,?)',[(i,i%3,'OWNED_'+str(i)) for i in range(37)])
    writer.commit()
    reader=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=.1);reader.row_factory=sqlite3.Row
    reader.execute('PRAGMA query_only=ON');reader.execute('BEGIN')
    expected=[dict(r) for r in reader.execute('SELECT * FROM matches ORDER BY sort_key LIMIT 13')]
    def change():
        writer.execute('UPDATE matches SET home_team="OWNED_CHANGED"')
        writer.execute('DELETE FROM matches WHERE id=3')
        writer.execute('INSERT INTO matches VALUES(400,0,"OWNED_NEW")')
        writer.execute('ALTER TABLE matches ADD COLUMN new_owned TEXT')
        writer.commit()
    try:
        proxy=Proxy(reader,after_keys=change)
        assert selected_match_rows(proxy,' ORDER BY sort_key',[13])==expected
        assert reader.total_changes==0
        reader.rollback()
        assert reader.execute('SELECT home_team FROM matches WHERE id=0').fetchone()[0]=='OWNED_CHANGED'
        assert len(reader.execute('PRAGMA table_info(matches)').fetchall())==4
    finally:reader.close();writer.close()


def test_actual_reader_matches_original_sql_and_keeps_metadata(app_module, monkeypatch, tmp_path):
    from engines import bounded_fixture_read
    a = app_module
    path = tmp_path / 'owned-reader-parity.sqlite'
    conn = sqlite3.connect(path)
    conn.execute('CREATE TABLE matches(id TEXT,match_date TEXT,kickoff_time TEXT,kickoff_iso TEXT,status TEXT,updated_at TEXT,last_synced_at TEXT,raw_json BLOB)')
    today = a.today_iso()
    values = []
    for i in range(257):
        day = today if i % 3 else '2020-01-01'
        values.append((str(i),day,'20:30',day+'T20:30:00+00:00',('NS','LIVE','FT','SUSP')[i%4],today+'T12:00:00+00:00',today+'T12:00:00+00:00',bytes([i%256])*1024))
    conn.executemany('INSERT INTO matches VALUES(?,?,?,?,?,?,?,?)',values)
    conn.commit()
    conn.close()
    before = path.read_bytes()
    monkeypatch.setattr(a,'DB_PATH',str(path))
    original_helper = bounded_fixture_read.read_match_rows
    def original_sql(connection, order_sql, params):
        return [dict(row) for row in connection.execute('SELECT * FROM "matches"'+order_sql+' LIMIT ?',tuple(params)).fetchall()]
    for limit in (1,2,99,800,0,-1):
        with monkeypatch.context() as patch:
            patch.setattr(bounded_fixture_read,'read_match_rows',original_sql)
            expected, metadata = a._v931_read_table_rows('matches',limit)
        actual, actual_metadata = a._v931_read_table_rows('matches',limit)
        assert actual == expected and actual_metadata == metadata
    assert bounded_fixture_read.read_match_rows is original_helper
    assert path.read_bytes() == before


@pytest.mark.parametrize('phase,message',[('keys','interrupted'),('rows','database or disk is full')])
def test_application_preserves_error_and_closes_reader(app_module,monkeypatch,tmp_path,phase,message):
    a = app_module
    path = tmp_path / 'owned-existing-path.sqlite'
    path.touch()
    db = make_db(SCHEMAS[0])
    class Reader(Proxy):
        closed = False
        @property
        def row_factory(self): return self.conn.row_factory
        @row_factory.setter
        def row_factory(self,value): self.conn.row_factory=value
        def close(self):
            self.closed=True
            self.conn.close()
    reader = Reader(db,fail_phase=phase)
    monkeypatch.setattr(a,'DB_PATH',str(path))
    with monkeypatch.context() as patch:
        patch.setattr(a.sqlite3,'connect',lambda *args,**kwargs:reader)
        rows,meta=a._v931_read_table_rows('matches',13)
    assert rows == [] and meta['status']=='schema_incomplete'
    assert meta['error_type']=='OperationalError' and meta['safe_error']==message
    assert reader.closed
    assert not any(sql.startswith('SELECT *') for sql in reader.sql)


@pytest.mark.parametrize('reverse',[False,True])
def test_ties_keep_original_scan_direction(reverse):
    db=make_db(SCHEMAS[0],800)
    db.execute('PRAGMA reverse_unordered_selects='+('ON' if reverse else 'OFF'))
    db.execute('BEGIN')
    try:
        expected=[dict(r) for r in db.execute('SELECT * FROM matches ORDER BY sort_key LIMIT 601')]
        assert selected_match_rows(db,' ORDER BY sort_key',[601])==expected
    finally:db.close()


def test_native_sqlite_interrupt_is_not_hidden_or_retried():
    db=make_db(SCHEMAS[0],800)
    db.execute('BEGIN')
    proxy=Proxy(db)
    execute=proxy.execute
    def interrupt_keys(sql,params=()):
        if ' NOT INDEXED' in sql:
            db.set_progress_handler(lambda:1,1)
        return execute(sql,params)
    proxy.execute=interrupt_keys
    try:
        with pytest.raises(sqlite3.OperationalError) as caught:
            selected_match_rows(proxy,' ORDER BY sort_key',[601])
        assert caught.value.sqlite_errorcode==sqlite3.SQLITE_INTERRUPT
        assert not any(sql.startswith('SELECT *') for sql in proxy.sql)
    finally:
        db.set_progress_handler(None,0)
        db.close()


@pytest.mark.parametrize('columns,column_limit,optimized', [
    (7, 7, False), (7, 8, True), (2000, 2000, False),
])
def test_full_row_at_sqlite_column_limit_keeps_original_result(columns, column_limit, optimized):
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE matches(' + ','.join('c' + str(i) + ' TEXT' for i in range(columns)) + ')')
    db.executemany('INSERT INTO matches(c0) VALUES(?)', [('b',), ('a',), ('c',)])
    db.commit()
    db.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, column_limit)
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    try:
        original = 'SELECT * FROM matches ORDER BY c0 LIMIT ?'
        expected = [dict(row) for row in db.execute(original, (2,))]
        assert len(expected) == 2 and all(len(row) == columns for row in expected)
        proxy = Proxy(db)
        assert selected_match_rows(proxy, ' ORDER BY c0', [2]) == expected
        assert any('NOT INDEXED' in sql for sql in proxy.sql) is optimized
        assert db.total_changes == 3
    finally:
        db.close()
