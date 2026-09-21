"""Connection ownership, transactions and read results; synthetic SQLite only."""
from contextlib import closing
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from engines import observability_engine as engine


def _operation(name, db):
    if name == 'schema': return engine.ensure_observability_schema(db)
    if name == 'event': return engine.record_observability_event(db, event_type='qa', message='Synthetic test')
    if name == 'error': return engine.record_observability_error(db, error_id='qa-error', exception_type='SyntheticError', exception_message='Synthetic test')
    if name == 'list': return engine.latest_observability_errors(db)
    if name == 'detail': return engine.observability_error_detail(db, 'qa-error')
    if name == 'summary': return engine.observability_summary(db, app_version='SIMULATED_QA')
    if name == 'route': return engine.mark_route_check(db, '/qa', status='ok')
    raise AssertionError(name)


@pytest.fixture
def tracked(tmp_path, monkeypatch):
    db = str(tmp_path / 'observability.sqlite')
    engine.ensure_observability_schema(db)
    opened = []
    mode = {'sql': '', 'commit': False}
    class Connection(sqlite3.Connection):
        qa_closed = False
        def close(self):
            result = super().close()
            self.qa_closed = True
            self.qa_closed_thread = threading.get_ident()
            return result
        def execute(self, sql, *a, **kw):
            if mode['sql'] and mode['sql'].casefold() in sql.casefold():
                raise sqlite3.OperationalError('synthetic database failure')
            return super().execute(sql, *a, **kw)
        def commit(self):
            if mode['commit'] and self.in_transaction:
                raise sqlite3.OperationalError('synthetic commit failure')
            return super().commit()
    def connect(path):
        conn = sqlite3.connect(path, factory=Connection, timeout=2)
        conn.row_factory = sqlite3.Row
        conn.qa_owner = threading.get_ident()
        opened.append(conn)
        return conn
    monkeypatch.setattr(engine, '_connect', connect)
    yield db, opened, mode
    for conn in opened:
        if not conn.qa_closed and conn.qa_owner == threading.get_ident():
            conn.close()


def assert_closed(opened):
    assert opened
    for conn in opened:
        assert conn.qa_closed and conn.qa_closed_thread == conn.qa_owner
        if conn.qa_owner == threading.get_ident():
            with pytest.raises(sqlite3.ProgrammingError, match='closed'):
                conn.execute('SELECT 1')


@pytest.mark.parametrize('operation', ['schema','event','error','list','detail','summary','route'])
def test_every_operation_explicitly_closes_connections(tracked, operation):
    db, opened, _ = tracked
    _operation(operation, db)
    assert_closed(opened)


@pytest.mark.parametrize('operation', ['schema','event','error','list','detail','summary','route'])
def test_schema_exception_never_leaves_open_connections(tracked, operation):
    db, opened, mode = tracked
    mode['sql'] = 'CREATE TABLE'
    try:
        _operation(operation, db)
    except sqlite3.OperationalError:
        pass  # Existing public propagation/fallback is preserved, not weakened.
    mode['sql'] = ''
    assert_closed(opened)


@pytest.mark.parametrize('operation,table', [('event','observability_events'),('error','observability_errors'),('route','observability_route_checks')])
def test_failed_commit_rolls_back_and_closes(tracked, operation, table):
    db, opened, mode = tracked
    mode['commit'] = True
    _operation(operation, db)
    assert_closed(opened)
    with closing(sqlite3.connect(db)) as check:
        assert check.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] == 0


@pytest.mark.parametrize('operation', ['list','detail','summary'])
def test_read_exception_closes_connection_and_preserves_safe_fallback(tracked, operation):
    db, opened, mode = tracked
    mode['sql'] = 'SELECT'
    result = _operation(operation, db)
    mode['sql'] = ''
    assert_closed(opened)
    assert isinstance(result, (dict,list))


def test_committed_data_and_error_details_survive_closure(tracked):
    db, opened, _ = tracked
    assert engine.record_observability_event(db, event_type='qa', message='persisted')
    assert engine.record_observability_error(db, error_id='qa-error', exception_type='SyntheticError', exception_message='persisted')
    engine.mark_route_check(db, '/qa', status='ok')
    assert engine.latest_observability_errors(db)[0]['error_id'] == 'qa-error'
    assert engine.observability_error_detail(db, 'qa-error')['exception_message'] == 'persisted'
    summary = engine.observability_summary(db)
    assert summary['ok'] and summary['traced_errors_total'] == 1 and summary['routes_checked'] == 1
    assert_closed(opened)


def test_repeated_summaries_do_not_depend_on_garbage_collection(tracked):
    db, opened, _ = tracked
    for _ in range(40):
        assert engine.observability_summary(db)['ok']
    assert len(opened) == 160
    assert_closed(opened)  # References intentionally retained: no GC can hide missing close().


def test_independent_threads_do_not_share_or_lose_connections(tracked):
    db, opened, _ = tracked
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: engine.observability_summary(db)['ok'], range(15)))
    assert all(results) and len(opened) == 60
    assert len({id(conn) for conn in opened}) == 60
    assert_closed(opened)
