"""Isolated feed imports: preserve identities with one shared team transaction."""
import sqlite3
import pytest
from datetime import date, timedelta


def prepare(app, tmp_path, monkeypatch):
    path = tmp_path / 'sports.sqlite'
    monkeypatch.setattr(app, 'DB_PATH', str(path))
    app.init_db()
    monkeypatch.setattr(app, 'seed_core', lambda: None)
    monkeypatch.setattr(app, 'thesportsdb_key', lambda: 'synthetic-test-key')
    monkeypatch.setattr(app, 'sportsdb_stale_external_ids', lambda **kwargs: [])
    monkeypatch.setattr(app, 'sportsdb_reconciliation_status', lambda ids, **kwargs: dict(resolved=0, remaining=0, missing=0))
    events = [({'idEvent': str(i), 'strSport': 'Soccer',
                'strHomeTeam': 'Real Madrid', 'strAwayTeam': 'Barcelona',
                'idHomeTeam': '133738', 'idAwayTeam': '133739',
                'strHomeTeamBadge': 'https://example.invalid/home.png',
                'strAwayTeamBadge': 'https://example.invalid/away.png',
                'dateEvent': (date(2026, 10, 6) + timedelta(days=i)).isoformat(), 'strTime': '18:00:00',
                'strLeague': 'La Liga', 'strStatus': 'Not Started'}, {}) for i in range(20)]
    monkeypatch.setattr(app, 'fetch_sportsdb_feed_events', lambda **kwargs: (events, [], 0))
    return path


def test_feed_uses_shared_connection_without_losing_names_ids_or_logos(app_module, tmp_path, monkeypatch):
    app = app_module
    path = prepare(app, tmp_path, monkeypatch)
    connections = []
    original = app.cache_team_identity
    def record(name, identity, *, connection=None):
        connections.append(connection)
        return original(name, identity, connection=connection)
    monkeypatch.setattr(app, 'cache_team_identity', record)
    result = app.sync_sportsdb_feed(limit=20)
    assert result['processed'] == 20
    assert len(connections) == 40
    assert connections[0] is not None and all(conn is connections[0] for conn in connections)
    with sqlite3.connect(path) as conn:
        teams = conn.execute('SELECT name,external_id,logo_url FROM teams ORDER BY external_id').fetchall()
        assert teams == [('Real Madrid', '133738', 'https://example.invalid/home.png'),
                         ('Barcelona', '133739', 'https://example.invalid/away.png')]
        assert conn.execute('SELECT count(*) FROM matches').fetchone()[0] == 20
    with pytest.raises(sqlite3.ProgrammingError):
        connections[0].execute('SELECT 1')


def test_failed_normalization_rolls_back_team_batch_and_closes_connection(app_module, tmp_path, monkeypatch):
    app = app_module
    path = prepare(app, tmp_path, monkeypatch)
    original = app.sportsdb_event_to_match
    connections = []
    def fail_second(event, *args, **kwargs):
        connections.append(kwargs['team_connection'])
        if len(connections) == 2:
            raise ValueError('synthetic normalization failure')
        return original(event, *args, **kwargs)
    monkeypatch.setattr(app, 'sportsdb_event_to_match', fail_second)
    result = app.sync_sportsdb_feed(limit=20)
    assert result['ok'] is False
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT count(*) FROM teams').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM matches').fetchone()[0] == 0
    with pytest.raises(sqlite3.ProgrammingError):
        connections[0].execute('SELECT 1')
