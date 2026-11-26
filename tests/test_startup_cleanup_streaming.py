"""Bounded startup row retention with the unchanged SQLite cleanup contract."""
import sqlite3


def test_cleanup_bounds_live_rows_without_skipping_tail_or_committing(app_module):
    conn=sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE matches(id TEXT,home_team TEXT,away_team TEXT,source TEXT)')
    conn.executemany('INSERT INTO matches VALUES(?,?,?,?)',
        ((str(i),'Real Madrid','FC Barcelona','sportsdb') for i in range(4096)))
    conn.execute('INSERT INTO matches VALUES(?,?,?,?)',
        ('tail-seed','Real Madrid','FC Barcelona',' SÉED\t ESTRUCTURAL '))
    conn.commit()
    retained={'active':0,'peak':0,'created':0}
    class ObservedRow:
        def __init__(self, values):
            self.values=values
            retained['active']+=1; retained['created']+=1
            retained['peak']=max(retained['peak'],retained['active'])
        def __getitem__(self, index):
            return self.values[index]
        def __del__(self):
            retained['active']-=1
    conn.row_factory=lambda cursor,row: ObservedRow(row)
    assert app_module.cleanup_fake_matches(conn.cursor())==1
    # Observe retained SQLite row objects, not source text or a wall-time guess.
    assert retained['created']==4097
    assert retained['peak']<=1024, retained
    conn.row_factory=None
    assert conn.execute('SELECT count(*) FROM matches').fetchone()[0]==4096
    assert conn.in_transaction
    conn.rollback()
    assert conn.execute('SELECT count(*) FROM matches').fetchone()[0]==4097
    conn.close()


def test_partial_read_failure_never_deletes_already_seen_candidates(app_module):
    conn=sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE matches(id TEXT,home_team TEXT,away_team TEXT,source TEXT)')
    conn.executemany('INSERT INTO matches VALUES(?,?,?,?)',
        ((str(i),'Real Madrid','FC Barcelona','seed estructural') for i in range(1024)))
    conn.commit()
    class InterruptedCursor(sqlite3.Cursor):
        calls=0
        def fetchmany(self, size=None):
            self.calls+=1
            if self.calls==2:
                raise sqlite3.OperationalError('synthetic interrupted read')
            return super().fetchmany(size)
    sql=[];conn.set_trace_callback(sql.append)
    assert app_module.cleanup_fake_matches(conn.cursor(factory=InterruptedCursor))==0
    assert not any(query.lstrip().upper().startswith('DELETE') for query in sql)
    assert conn.execute('SELECT count(*) FROM matches').fetchone()[0]==1024
    assert not conn.in_transaction
    conn.close()


def test_streamed_read_and_predicate_timings_remain_separate(app_module, monkeypatch, capsys):
    import json
    conn=sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE matches(id TEXT,home_team TEXT,away_team TEXT,source TEXT)')
    conn.executemany('INSERT INTO matches VALUES(?,?,?,?)',
        ((str(i),'Real Madrid','FC Barcelona','sportsdb') for i in range(1024)))
    conn.commit()
    clock=[100.0];fetches=[];normalizations=[]
    monkeypatch.setattr(app_module.time,'monotonic',lambda:clock[0])
    original=app_module.normalized_label
    def normalize(value):
        clock[0]+=.003;normalizations.append(value)
        return original(value)
    monkeypatch.setattr(app_module,'normalized_label',normalize)
    class MeasuredCursor(sqlite3.Cursor):
        def execute(self, sql, *args):
            clock[0]+=.007
            return super().execute(sql,*args)
        def fetchmany(self, size=None):
            clock[0]+=.005;fetches.append(1)
            return super().fetchmany(size)
    with app_module.app.test_request_context('/api/automation/sports/sync'):
        assert app_module.cleanup_fake_matches(conn.cursor(factory=MeasuredCursor))==0
    records={item['stage']:item for line in capsys.readouterr().out.splitlines()
             if (item:=json.loads(line)).get('event')=='sports_stage'}
    assert abs(records['startup_cleanup_read']['duration_ms']-(7+5*len(fetches)))<=1
    assert abs(records['startup_cleanup_predicate']['duration_ms']-3*len(normalizations))<=1
    assert all(set(item)=={'event','stage','duration_ms'} for item in records.values())
    conn.close()


def test_existing_database_migration_covers_the_actual_cleanup_read(app_module, tmp_path, monkeypatch):
    """An existing wide table keeps the same data rules through a narrower read."""
    app = app_module
    monkeypatch.setattr(app, 'DB_PATH', str(tmp_path / 'cleanup-read.sqlite'))
    app.init_db()
    conn = app.db()
    conn.execute('DROP INDEX IF EXISTS idx_matches_startup_cleanup')
    conn.execute('DELETE FROM matches')
    conn.executemany(
        'INSERT INTO matches(id,match_date,home_team,away_team,source,raw_json) VALUES(?,?,?,?,?,?)',
        ((str(i), '2026-11-26', 'Real Madrid', 'FC Barcelona', 'sportsdb', 'x' * 16384)
         for i in range(512)))
    conn.execute(
        'INSERT INTO matches(id,match_date,home_team,away_team,source,raw_json) VALUES(?,?,?,?,?,?)',
        ('tail-seed', '2026-11-26', 'Real Madrid', 'FC Barcelona', ' SÉED\t ESTRUCTURAL ', 'x' * 16384))
    conn.commit()
    app.run_schema_migrations(conn)
    conn.commit()
    root_page = conn.execute(
        "SELECT rootpage FROM sqlite_master WHERE name='idx_matches_startup_cleanup'").fetchone()[0]
    app.run_schema_migrations(conn)
    conn.commit()
    assert conn.execute(
        "SELECT rootpage FROM sqlite_master WHERE name='idx_matches_startup_cleanup'").fetchone()[0] == root_page
    assert conn.execute('SELECT count(*) FROM matches').fetchone()[0] == 513
    plans = []
    class ObservedCursor(sqlite3.Cursor):
        def execute(self, sql, *args):
            if sql == 'SELECT id, home_team, away_team, source FROM matches':
                plans.extend(str(row[3]) for row in self.connection.execute('EXPLAIN QUERY PLAN ' + sql))
            return super().execute(sql, *args)
    assert app.cleanup_fake_matches(conn.cursor(factory=ObservedCursor)) == 1
    assert conn.execute('SELECT count(*) FROM matches').fetchone()[0] == 512
    assert conn.in_transaction
    conn.rollback()
    assert conn.execute('SELECT count(*) FROM matches').fetchone()[0] == 513
    assert any('COVERING INDEX idx_matches_startup_cleanup' in plan for plan in plans), plans
    conn.close()


def test_unavailable_cleanup_index_preserves_existing_read_and_delete(app_module, tmp_path, monkeypatch):
    app = app_module
    monkeypatch.setattr(app, 'DB_PATH', str(tmp_path / 'cleanup-fallback.sqlite'))
    app.init_db()
    conn = app.db()
    conn.execute('DROP INDEX IF EXISTS idx_matches_startup_cleanup')
    conn.execute('DELETE FROM matches')
    conn.executemany(
        'INSERT INTO matches(id,match_date,home_team,away_team,source) VALUES(?,?,?,?,?)',
        [('real', '2026-11-26', 'Málaga CF', 'Córdoba CF', 'sportsdb'),
         ('seed', '2026-11-26', 'Málaga CF', 'Córdoba CF', ' SÉED\t ESTRUCTURAL ')])
    conn.commit()
    class RefusedOptionalIndex:
        def execute(self, sql, *args):
            if sql.startswith('CREATE INDEX IF NOT EXISTS idx_matches_startup_cleanup '):
                raise sqlite3.OperationalError('synthetic optional index unavailable')
            return conn.execute(sql, *args)
        def __getattr__(self, name):
            return getattr(conn, name)
    app.run_schema_migrations(RefusedOptionalIndex())
    conn.commit()
    assert not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name='idx_matches_startup_cleanup'").fetchone()
    assert app.cleanup_fake_matches(conn.cursor()) == 1
    assert conn.execute('SELECT id FROM matches').fetchone()[0] == 'real'
    assert conn.in_transaction
    conn.rollback()
    assert conn.execute('SELECT count(*) FROM matches').fetchone()[0] == 2
    conn.close()
