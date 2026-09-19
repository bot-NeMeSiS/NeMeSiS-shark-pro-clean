"""Rapid repeat navigation must not collide in the local activity ledger."""
import sqlite3
import pytest


def test_repeated_navigation_within_one_second_has_distinct_activity_ids(app_module, monkeypatch, tmp_path):
    path = tmp_path / 'navigation.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE user_activity(id TEXT PRIMARY KEY,user_id TEXT,activity_type TEXT,target_type TEXT,target_id TEXT,payload_json TEXT,created_at TEXT)')
    monkeypatch.setattr(app_module, 'db', lambda: sqlite3.connect(path))
    monkeypatch.setattr(app_module, 'now_iso', lambda: '2026-09-13T10:00:00+02:00')
    first = app_module.record_user_activity('view', 'alerts', 'client-alerts', user_id='SIMULATED_QA')
    second = app_module.record_user_activity('view', 'alerts', 'client-alerts', user_id='SIMULATED_QA')
    assert first != second
    with sqlite3.connect(path) as conn:
        rows = conn.execute('SELECT id,created_at FROM user_activity').fetchall()
    assert len(rows) == 2
    assert {row[1] for row in rows} == {'2026-09-13T10:00:00+02:00'}


def test_anonymous_activity_does_not_open_database(app_module, monkeypatch):
    monkeypatch.setattr(app_module, 'current_user_id', lambda: None)
    def forbidden():
        raise AssertionError('Anonymous activity opened storage')
    monkeypatch.setattr(app_module, 'db', forbidden)
    assert app_module.record_user_activity('view', 'alerts') is None


def test_activity_insert_error_closes_connection_without_hiding_error(app_module, monkeypatch):
    class FailingConnection:
        closed = False
        def execute(self, *args):
            raise sqlite3.OperationalError('SIMULATED_QA write failure')
        def close(self):
            self.closed = True
    conn = FailingConnection()
    monkeypatch.setattr(app_module, 'db', lambda: conn)
    with pytest.raises(sqlite3.OperationalError, match='SIMULATED_QA'):
        app_module.record_user_activity('view', 'alerts', user_id='SIMULATED_QA')
    assert conn.closed
