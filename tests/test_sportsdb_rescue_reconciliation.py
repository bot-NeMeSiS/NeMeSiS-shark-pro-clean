import sqlite3
from engines import sports_history_engine as history
from engines import sports_history_adapters as adapters
from engines.sports_history_reconciliation import reconcile_identity


def test_roster_survives_team_and_player_redirects_without_duplicate_members(tmp_path):
    path = str(tmp_path / 'history.sqlite')
    with sqlite3.connect(path) as conn:
        history.ensure_schema(conn)
        team = history.entity(conn, 'team', 'thesportsdb', '10', {'name': 'Local QA team'})
        target_team = history.entity(conn, 'team', 'the_odds_api', 'team-qa', {'name': 'Local QA team'})
        player = history.entity(conn, 'player', 'thesportsdb', '20', {'name': 'Local QA player'})
        target_player = history.entity(conn, 'player', 'api_football', '20', {'name': 'Local QA player'})
        history.link_entities(conn, team, 'team_has_player', player, 'thesportsdb')
        reconcile_identity(conn, 'team', 'thesportsdb', '10', target_team, 'unit-test reviewed ID evidence')
        reconcile_identity(conn, 'player', 'thesportsdb', '20', target_player, 'unit-test reviewed ID evidence')
        history.link_entities(conn, team, 'team_has_player', player, 'thesportsdb')
    roster = history.team_roster(path, '10')
    assert [card['id'] for card in roster] == [target_player]
    assert history.team_profile(path, '10')['id'] == target_team
    assert history.linked_entity_cards(path, 'team', team, 'team_has_player')[0]['id'] == target_player
    assert history.history_summary(path)['reconciliations']


def test_wrong_roster_team_is_rejected_before_creating_entities():
    with sqlite3.connect(':memory:') as conn:
        history.ensure_schema(conn)
        before = conn.execute('SELECT count(*) FROM sports_history_entities').fetchone()[0]
        try:
            adapters.ingest_sportsdb_player_profile(conn, {'idPlayer': '20', 'strPlayer': 'Local QA player', 'idTeam': '999'}, team_external_id='10')
        except ValueError as error:
            assert 'identity mismatch' in str(error)
        else:
            raise AssertionError('A different team must not be accepted')
        assert conn.execute('SELECT count(*) FROM sports_history_entities').fetchone()[0] == before


def test_roster_sync_rotates_past_cached_empty_teams_and_rejects_bad_payload(tmp_path, monkeypatch, app_module):
    path = str(tmp_path / 'rosters.sqlite')
    with sqlite3.connect(path) as conn:
        conn.executescript('CREATE TABLE teams(key TEXT,name TEXT,external_id TEXT,last_sync_at TEXT,source TEXT); CREATE TABLE automation_state(key TEXT PRIMARY KEY,value_json TEXT,updated_at TEXT);')
        conn.executemany('INSERT INTO teams VALUES(?,?,?,?,?)', [('qa-a', 'Local QA A', '10', '', 'sportsdb'), ('qa-b', 'Local QA B', '11', '', 'sportsdb')])
    monkeypatch.setattr(app_module, 'DB_PATH', path)
    monkeypatch.setattr(app_module, 'seed_core', lambda: None)
    monkeypatch.setattr(app_module, 'thesportsdb_key', lambda: 'isolated-test-key')
    calls = []
    monkeypatch.setattr(app_module, 'sportsdb_v2', lambda endpoint: calls.append(endpoint) or {'list': []})
    first = app_module.sync_sportsdb_entity_memory(limit_teams=1)
    second = app_module.sync_sportsdb_entity_memory(limit_teams=1)
    assert calls == ['list/players/10', 'list/players/11']
    assert first['external_calls'] == second['external_calls'] == 1
    with sqlite3.connect(path) as conn:
        conn.execute('UPDATE sports_history_backfill SET cache_until=0')
    monkeypatch.setattr(app_module, 'sportsdb_v2', lambda endpoint: {'error': 'not a roster'})
    result = app_module.sync_sportsdb_entity_memory(limit_teams=1)
    assert result['ok'] is False
    assert result['teams'][0]['status'] == 'error'
