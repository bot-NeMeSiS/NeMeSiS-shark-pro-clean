import json
import sqlite3
from datetime import datetime, timedelta

import pytest
from engines.match_sync_engine import h2h_price_snapshot


@pytest.fixture
def odds_db(app_module, monkeypatch, tmp_path):
    path = tmp_path / 'isolated.sqlite'
    app_module.init_db()
    source = sqlite3.connect(app_module.DB_PATH)
    target = sqlite3.connect(path)
    source.backup(target)
    source.close()
    for table in ('matches', 'live_matches', 'odds_snapshots', 'automation_state', 'api_sync_logs'):
        target.execute(f'DELETE FROM {table}')
    target.commit()
    target.close()
    monkeypatch.setattr(app_module, 'DB_PATH', str(path))
    monkeypatch.setattr(app_module, 'seed_core', lambda: None)
    monkeypatch.setenv('THE_ODDS_API_KEY', 'simulated-qa')
    monkeypatch.setenv('ENABLE_ODDS_API', 'true')
    return app_module


def fixture(app):
    stamp = datetime.now(app.TZ) + timedelta(days=1)
    sport = {'key': 'laliga', 'name': 'LaLiga EA Sports', 'odds_key': 'soccer_spain_la_liga'}
    event = {'id': 'provider-odds-qa', 'home_team': 'Atletico Madrid', 'away_team': 'Real Madrid',
             'commence_time': stamp.isoformat(), 'bookmakers': [
                 {'title': 'No 1X2', 'markets': [{'key': 'totals', 'outcomes': [{'name': 'Over', 'price': 2}]}]},
                 {'title': 'QA bookmaker', 'last_update': datetime.now(app.TZ).isoformat(),
                  'markets': [{'key': 'h2h', 'outcomes': [
                      {'name': 'Atletico Madrid', 'price': 2.1}, {'name': 'Draw', 'price': 3.4},
                      {'name': 'Real Madrid', 'price': 3.2}]}]}]}
    match = app.odds_event_to_match(sport, event)
    match.update(id='sportsdb-qa', external_id='sportsdb-id-qa', source='TheSportsDB API',
                 bookmaker='', odds_h2h_json='', odds_updated_at='')
    return sport, event, match


def test_selector_searches_all_bookmakers_and_rejects_totals():
    assert h2h_price_snapshot({'bookmakers': [{'markets': [{'key': 'totals', 'outcomes': [{'price': 2}]}]}]}) == {}


def test_sync_links_translated_teams_and_preserves_provider_identity(odds_db, monkeypatch):
    app = odds_db
    sport, event, match = fixture(app)
    app.upsert_sportsdb_matches([match])
    before = app.one("SELECT value_json FROM automation_state WHERE key='sportsdb_feed_sync'")
    monkeypatch.setattr(app, 'fetch_odds_events', lambda **kw: ([(sport, event)], [], {'http_status': 200, 'requests_remaining': 999}))
    result = app.sync_odds_events(force=True)
    assert result['ok'] and result['linked_matches'] == 1
    row = app.one('SELECT * FROM matches WHERE id=?', (match['id'],))
    assert row['external_id'] == 'sportsdb-id-qa' and row['source'] == 'TheSportsDB API'
    assert row['bookmaker'] == 'QA bookmaker'
    assert app.v565_extract_odds(row)['home'] == 2.1
    snapshot = app.one('SELECT * FROM odds_snapshots')
    assert snapshot['match_id'] == match['id'] and snapshot['external_id'] == event['id']
    assert app.one("SELECT value_json FROM automation_state WHERE key='sportsdb_feed_sync'") == before
    assert app.one('SELECT COUNT(*) AS n FROM matches')['n'] == 1
    app.upsert_sportsdb_matches([match])
    assert app.v565_extract_odds(app.one('SELECT * FROM matches'))['home'] == 2.1


def test_matching_tolerates_time_but_rejects_reverse_competition_and_ambiguity(odds_db):
    app = odds_db
    sport, event, match = fixture(app)
    match['kickoff_iso'] = (datetime.fromisoformat(match['kickoff_iso']) + timedelta(minutes=10)).isoformat()
    app.upsert_sportsdb_matches([match])
    conn = app.db()
    try:
        assert app._odds_fixture_target(conn.cursor(), sport, event)['id'] == match['id']
        assert app._odds_fixture_target(conn.cursor(), {**sport, 'key': 'other', 'name': 'Other'}, event) is None
        assert app._odds_fixture_target(conn.cursor(), sport, {**event, 'home_team': event['away_team'], 'away_team': event['home_team']}) is None
        conn.execute("UPDATE matches SET kickoff_iso=?", ((datetime.fromisoformat(event['commence_time']) + timedelta(hours=2)).isoformat(),))
        assert app._odds_fixture_target(conn.cursor(), sport, event) is None
        conn.execute('UPDATE matches SET kickoff_iso=?', (event['commence_time'],))
        columns = [r[1] for r in conn.execute('PRAGMA table_info(matches)')]
        values = dict(conn.execute('SELECT * FROM matches').fetchone())
        values['id'] = 'ambiguous-qa'
        conn.execute(f"INSERT INTO matches ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", [values[c] for c in columns])
        assert app._odds_fixture_target(conn.cursor(), sport, event) is None
    finally:
        conn.close()


def test_legacy_snapshot_sync_uses_canonical_pipeline(odds_db, monkeypatch):
    monkeypatch.setattr(odds_db, 'sync_odds_events', lambda **kw: {'ok': True, 'canonical': kw})
    assert odds_db.sync_odds_snapshots(limit=10)['canonical'] == {'limit': 10, 'force': False}


def test_empty_json_sportsdb_refresh_preserves_quotes(odds_db):
    app = odds_db
    sport, event, match = fixture(app)
    app.upsert_sportsdb_matches([match])
    app.upsert_odds_snapshots([(sport, event)])
    match['odds_h2h_json'] = '{}'
    app.upsert_sportsdb_matches([match])
    assert app.v565_extract_odds(app.one('SELECT * FROM matches'))['home'] == 2.1


def test_structural_competitions_sync_requires_no_provider_quota(odds_db):
    result = odds_db.sync_sportsdb_competitions()
    assert result['ok'] and result['processed'] > 0


def test_linked_quotes_keep_odds_provider_provenance_for_client_analysis(odds_db):
    app = odds_db
    sport, event, match = fixture(app)
    app.upsert_sportsdb_matches([match])
    app.upsert_odds_snapshots([(sport, event)])
    row = app.one('SELECT * FROM matches')
    assert row['source'] == 'TheSportsDB API'
    assert app.v565_extract_odds(row)['source'] == 'The Odds API'


def test_non_h2h_event_does_not_erase_linked_quotes(odds_db):
    app = odds_db
    sport, event, match = fixture(app)
    app.upsert_sportsdb_matches([match])
    app.upsert_odds_snapshots([(sport, event)])
    event['bookmakers'] = event['bookmakers'][:1]
    result = app.upsert_odds_snapshots([(sport, event)])
    assert result['skipped'] == 1 and result['linked'] == 0
    assert app.v565_extract_odds(app.one('SELECT * FROM matches'))['home'] == 2.1


def test_cached_utc_quotes_link_to_next_madrid_calendar_day(odds_db):
    app = odds_db
    sport, event, match = fixture(app)
    event['commence_time'] = '2026-10-03T23:30:00+00:00'
    match.update(match_date='2026-10-04', kickoff_iso='2026-10-04T01:30:00+02:00')
    app.upsert_odds_snapshots([(sport, event)])
    app.upsert_sportsdb_matches([match])
    assert app.v565_extract_odds(app.one('SELECT * FROM matches'))['home'] == 2.1


def test_http_error_preserves_headers_without_leaking_url(odds_db, monkeypatch):
    from urllib.error import HTTPError
    def fail(*args, **kwargs):
        raise HTTPError('https://example.invalid/?apiKey=simulated-qa', 429, 'secret',
                        {'x-requests-remaining': '0', 'x-requests-used': '100', 'x-requests-last': '1'}, None)
    monkeypatch.setattr(odds_db, 'fetch_json_response', fail)
    result = odds_db.odds_api_request('sports/test/odds')
    assert result['http_status'] == 429 and result['quota']['requests_used'] == 100
    assert 'simulated-qa' not in json.dumps(result) and 'secret' not in json.dumps(result)


def test_cached_odds_attach_when_sportsdb_arrives_later_without_api_call(odds_db, monkeypatch):
    app = odds_db
    sport, event, match = fixture(app)
    app.upsert_odds_snapshots([(sport, event)])
    monkeypatch.setattr(app, 'odds_api_request', lambda *a, **k: pytest.fail('must reuse cache'))
    match['kickoff_iso'] = (datetime.fromisoformat(match['kickoff_iso']) + timedelta(minutes=10)).isoformat()
    app.upsert_sportsdb_matches([match])
    row = app.one('SELECT * FROM matches WHERE id=?', (match['id'],))
    assert app.v565_extract_odds(row)['home'] == 2.1
    assert app.one('SELECT * FROM odds_snapshots')['match_id'] == match['id']


def test_newer_quotes_cannot_be_overwritten_by_old_observations(odds_db):
    app = odds_db
    sport, event, match = fixture(app)
    app.upsert_sportsdb_matches([match])
    app.upsert_odds_snapshots([(sport, event)])
    event['bookmakers'][1]['last_update'] = '2000-01-01T00:00:00Z'
    event['bookmakers'][1]['markets'][0]['outcomes'][0]['price'] = 9
    app.upsert_odds_snapshots([(sport, event)])
    assert app.v565_extract_odds(app.one('SELECT * FROM matches'))['home'] == 2.1

def test_pipeline_errors_persist_safe_diagnostics(odds_db, monkeypatch):
    def broken(**kwargs):
        raise ValueError('apiKey=DO-NOT-EXPOSE')
    monkeypatch.setattr(odds_db, 'fetch_odds_events', broken)
    result = odds_db.sync_odds_events(force=True)
    assert result['status'] == 'PIPELINE_ERROR'
    diag = odds_db.odds_diagnostics()
    assert diag['last_error'] == 'ValueError' and 'DO-NOT-EXPOSE' not in json.dumps(diag)



def test_odds_diagnostics_explains_client_visibility_without_provider_call(odds_db, monkeypatch):
    app = odds_db
    sport, event, match = fixture(app)
    app.upsert_sportsdb_matches([match])
    app.upsert_odds_snapshots([(sport, event)])
    monkeypatch.setattr(app, 'odds_api_request', lambda *a, **k: pytest.fail('diagnostics must stay local'))

    diag = app.odds_diagnostics()
    visibility = diag['visibility']

    assert diag['client_displayed'] == 1
    assert visibility['state'] == 'VISIBLE_CLIENT'
    assert visibility['valid_odds_matches'] == 1
    assert visibility['visible_upcoming'] == 1
    assert visibility['sporting_linked_snapshots'] == 1
    assert visibility['odds_only_snapshots'] == 0
    assert visibility['orphan_snapshots'] == 0
    assert visibility['window_start'] <= match['match_date'] <= visibility['window_end']


def test_admin_odds_partial_renders_unknown_credit_and_escapes_errors(odds_db):
    from flask import render_template
    with odds_db.app.test_request_context('/admin/matches-sync'):
        html = render_template('partials/admin_odds_diagnostics.html', data={'odds': {
            'key_present': True, 'enabled': True, 'quota': {'requests_remaining': 0, 'requests_used': None},
            'last_error': '<script>secret</script>', 'last_sync': {}}})
    assert 'Créditos restantes</span><strong>0<' in html
    assert 'Créditos usados</span><strong>No disponible automáticamente<' in html
    assert '&lt;script&gt;' in html and '<script>secret</script>' not in html
    assert 'Visibles en cliente' in html
    assert 'Diagnóstico de cobertura' in html
