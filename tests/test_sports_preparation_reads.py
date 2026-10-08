"""Provider selection remains bounded, current and backed by full status evidence."""
import json
import sqlite3

import pytest


def catalogue(indexed):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('''CREATE TABLE matches(id TEXT PRIMARY KEY, external_id TEXT,
        source TEXT, status TEXT, raw_json TEXT, updated_at TEXT, last_synced_at TEXT)''')
    if indexed:
        conn.execute('CREATE INDEX idx_matches_source_external ON matches(source,external_id)')
    return conn


def insert(conn, identity, external, *, source='TheSportsDB API', status='LIVE',
           raw='{}', updated='2026-10-08T12:00:00', observed=''):
    conn.execute('INSERT INTO matches VALUES(?,?,?,?,?,?,?)',
                 (identity, external, source, status, raw, updated, observed))


def read_with(app, conn, monkeypatch):
    queries = []
    def rows(sql, params=()):
        queries.append((sql, params))
        return [dict(row) for row in conn.execute(sql, params)]
    monkeypatch.setattr(app, 'rows', rows)
    return queries


@pytest.mark.parametrize('indexed', [False, True])
def test_reconciliation_retains_duplicate_stale_evidence_and_provider_scope(app_module, monkeypatch, indexed):
    conn = catalogue(indexed)
    insert(conn, 'done', 'one', status='FT', raw='{"score":"1-0"}')
    insert(conn, 'pending-duplicate', 'one', status='NS', raw='{"fixture":{"status":{"short":"LIVE"}}}')
    insert(conn, 'foreign', 'two', source='Other', status='LIVE')
    insert(conn, 'done-two', 'two', status='FT')
    read_with(app_module, conn, monkeypatch)
    assert app_module.sportsdb_reconciliation_status(['one', 'one', 'two', 'missing']) == {
        'requested': 3, 'resolved': 1, 'remaining': 1, 'missing': 1}
    conn.execute("UPDATE matches SET raw_json='{}',status='FT' WHERE id='pending-duplicate'")
    assert app_module.sportsdb_reconciliation_status(['one'])['resolved'] == 1
    conn.close()


@pytest.mark.parametrize('indexed', [False, True])
def test_batch_identities_cross_chunk_boundary_and_see_transaction_changes(app_module, indexed):
    conn = catalogue(indexed)
    for i in range(505):
        insert(conn, f'local-{i}', str(i))
        insert(conn, f'foreign-{i}', str(i), source='Other')
    insert(conn, 'legacy-0', '0')
    insert(conn, 'not-requested', '9999')
    conn.commit()
    incoming = [{'external_id': str(i)} for i in range(505)] + [{'external_id': '0'}, {}, None]
    result = app_module._sportsdb_provider_ids_for_batch(conn.cursor(), incoming)
    assert len(result) == 505
    assert set(result['0']) == {'local-0', 'legacy-0'}
    assert result['504'] == ['local-504']
    assert not any(identity.startswith('foreign-') for group in result.values() for identity in group)
    conn.execute("UPDATE matches SET external_id='0' WHERE id='local-504'")
    assert 'local-504' in app_module._sportsdb_provider_ids_for_batch(conn.cursor(), incoming)['0']
    conn.rollback()
    assert app_module._sportsdb_provider_ids_for_batch(conn.cursor(), incoming)['504'] == ['local-504']
    conn.close()


def test_stage_diagnostics_are_closed_and_do_not_include_record_content(app_module, capsys):
    with app_module.app.test_request_context('/api/automation/sports/sync', method='POST'):
        for stage in ('startup_cleanup_read', 'startup_cleanup_predicate', 'sportsdb_candidates',
                      'sportsdb_fetch', 'sportsdb_transform', 'sportsdb_persist', 'sportsdb_reconciliation'):
            app_module._log_sports_stage_duration(stage, app_module.time.monotonic())
        app_module._log_sports_stage_duration('unknown-sensitive-value', app_module.time.monotonic())
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(records) == 7
    assert all(set(record) == {'event', 'stage', 'duration_ms'} for record in records)
    assert all(record['duration_ms'] >= 0 for record in records)
    with app_module.app.test_request_context('/app'):
        app_module._log_sports_stage_duration('sportsdb_candidates', app_module.time.monotonic())
    assert not capsys.readouterr().out
