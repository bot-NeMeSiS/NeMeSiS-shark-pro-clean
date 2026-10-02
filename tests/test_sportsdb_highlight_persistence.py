"""Persisted media cache, provider payload reuse and honest diagnostic evidence."""
import json
import sqlite3
from datetime import date
import urllib.error

import pytest
from engines import sportsdb_highlights_engine as media
from engines import sportsdb_enrichment_engine as enrichment


@pytest.fixture
def store(tmp_path, monkeypatch):
    path = tmp_path / 'media.sqlite'
    monkeypatch.setattr(media, '_api_key', lambda: 'isolated-test')
    monkeypatch.setattr(media, '_today', lambda: date(2026, 10, 3))
    monkeypatch.setattr(media, '_sportsdb_v2', lambda *a: {'lookup': []})
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE matches(id TEXT PRIMARY KEY,external_id TEXT,source TEXT,home_team TEXT,away_team TEXT,match_date TEXT,competition_name TEXT,status TEXT,score TEXT)')
        conn.execute("INSERT INTO matches VALUES ('local','sportsdb-42','TheSportsDB','Home','Away','2026-10-03','League','FT','2-1')")
    return path


def event(video='abcdefghijk'):
    return {'idEvent': '42', 'strHomeTeam': 'Home', 'strAwayTeam': 'Away',
            'dateEvent': '2026-10-03', 'strLeague': 'League',
            'strVideo': 'https://www.youtube.com/watch?v=' + video}


@pytest.mark.parametrize('rows', [None, [], [event()]])
def test_repeated_sync_reuses_valid_feed_including_empty(store, monkeypatch, rows):
    calls = []
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: calls.append(a) or {'events': rows})
    first = media.sync_sportsdb_highlights(store, days_back=0)
    second = media.sync_sportsdb_highlights(store, days_back=0)
    assert first['external_calls'] == (1 if rows else 2)
    assert second['external_calls'] == 0 and second['persistent_cache_hits'] == 1
    assert len(calls) == 1
    run = media.sportsdb_highlights_summary(store)['recent_runs'][0]
    # Runs can share a second; evidence exists in persisted metrics regardless of ordering.
    with sqlite3.connect(store) as conn:
        assert conn.execute('SELECT SUM(persistent_cache_hits) FROM sportsdb_highlight_runs').fetchone()[0] == 1
    assert run['external_calls'] == 0


def test_forced_sync_bypasses_cache_and_revokes_changed_content(store, monkeypatch):
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: {'events': [event()]})
    media.sync_sportsdb_highlights(store, days_back=0)
    with sqlite3.connect(store) as conn:
        conn.execute("UPDATE sportsdb_match_highlights SET rights_status='LICENSED',commercial_use_status='ALLOWED'")
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: {'events': [event('zyxwvutsrqp')]})
    result = media.sync_sportsdb_highlights(store, days_back=0, force=True)
    assert result['external_calls'] == 1 and result['persistent_cache_hits'] == 0
    with sqlite3.connect(store) as conn:
        row = conn.execute('SELECT video_url,rights_status,match_id FROM sportsdb_match_highlights').fetchone()
    assert row == ('https://www.youtube.com/watch?v=zyxwvutsrqp', 'REVIEW_REQUIRED', 'local')


def test_expired_empty_cache_allows_later_video(store, monkeypatch):
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: {'events': None})
    media.sync_sportsdb_highlights(store, days_back=0)
    with sqlite3.connect(store) as conn:
        conn.execute("UPDATE sportsdb_highlight_feed_cache SET expires_at='2000-01-01T00:00:00+01:00'")
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: {'events': [event()]})
    result = media.sync_sportsdb_highlights(store, days_back=0)
    assert result['external_calls'] == 1 and result['highlights_found'] == 1


@pytest.mark.parametrize('payload', [{}, {'events': 'invalid'}, {'error': 'denied'}])
def test_invalid_responses_are_not_cached(store, monkeypatch, payload):
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: payload)
    result = media.sync_sportsdb_highlights(store, days_back=0)
    assert result['status'] == 'FAILED'
    with sqlite3.connect(store) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sportsdb_highlight_feed_cache').fetchone()[0] == 0


def test_profiles_feed_existing_catalogue_without_inventing_authorization(store, monkeypatch):
    enrichment.ensure_sportsdb_enrichment_schema(store)
    with enrichment._connect(store) as conn:
        enrichment._upsert_event(conn, event())
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: {'events': []})
    result = media.sync_sportsdb_highlights(store, days_back=0)
    assert result['profile_links_reused'] == 1 and result['linked_matches'] == 1
    snapshot = media.sportsdb_highlights_for_match(store, 'local')
    assert snapshot['highlights'] == []
    assert snapshot['all_highlights'][0]['rights_status'] == 'UNKNOWN_RIGHTS'


def test_new_feed_wins_over_old_profile(store, monkeypatch):
    enrichment.ensure_sportsdb_enrichment_schema(store)
    with enrichment._connect(store) as conn:
        enrichment._upsert_event(conn, event())
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: {'events': [event('zyxwvutsrqp')]})
    result = media.sync_sportsdb_highlights(store, days_back=0)
    assert result['profile_links_reused'] == 0
    with sqlite3.connect(store) as conn:
        assert conn.execute('SELECT video_url FROM sportsdb_match_highlights').fetchone()[0].endswith('zyxwvutsrqp')


def test_v2_lookup_uses_header_auth_and_keeps_key_out_of_url(monkeypatch):
    seen = {}
    monkeypatch.setattr(media, '_api_key', lambda: 'premium-secret')

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def read(self):
            return b'{"lookup": []}'

    def fake_urlopen(request, timeout):
        seen['request'] = request
        seen['timeout'] = timeout
        return Response()

    monkeypatch.setattr(media.urllib.request, 'urlopen', fake_urlopen)
    payload = media._sportsdb_v2('lookup/event_highlights/42')

    assert payload == {'lookup': []}
    request = seen['request']
    assert 'premium-secret' not in request.full_url
    headers = {key.lower(): value for key, value in request.header_items()}
    assert headers['x-api-key'] == 'premium-secret'
    assert request.full_url.endswith('/api/v2/json/lookup/event_highlights/42')


def test_targeted_v2_lookup_fills_finished_match_missing_highlight(store, monkeypatch):
    v2_calls = []
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: {'events': []})
    monkeypatch.setattr(media, '_sportsdb_v2', lambda path: v2_calls.append(path) or {'lookup': [event()]})

    result = media.sync_sportsdb_highlights(store, days_back=0)

    assert result['status'] == 'OK'
    assert result['external_calls'] == 2
    assert result['v2_event_lookups'] == 1
    assert result['v2_cache_hits'] == 0
    assert result['v2_highlights_found'] == 1
    assert v2_calls == ['lookup/event_highlights/42']
    with sqlite3.connect(store) as conn:
        row = conn.execute('SELECT match_id,video_url FROM sportsdb_match_highlights').fetchone()
    assert row[0] == 'local'
    assert row[1].startswith('https://www.youtube.com/watch?v=')


def test_empty_v2_lookup_is_cached_to_avoid_repeat_paid_calls(store, monkeypatch):
    v2_calls = []
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: {'events': []})
    monkeypatch.setattr(media, '_sportsdb_v2', lambda path: v2_calls.append(path) or {'lookup': []})

    first = media.sync_sportsdb_highlights(store, days_back=0)
    second = media.sync_sportsdb_highlights(store, days_back=0)

    assert first['v2_event_lookups'] == 1
    assert second['v2_event_lookups'] == 0
    assert second['v2_cache_hits'] == 1
    assert len(v2_calls) == 1


@pytest.mark.parametrize('payload', [{}, {'lookup': 'invalid'}, {'lookup': [{**event(), 'idEvent': '99'}]}])
def test_v2_malformed_or_wrong_identity_is_not_cached_or_published(store, monkeypatch, payload):
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: {'events': []})
    monkeypatch.setattr(media, '_sportsdb_v2', lambda *a: payload)
    result = media.sync_sportsdb_highlights(store, days_back=0)
    assert result['status'] == 'FAILED'
    with sqlite3.connect(store) as conn:
        assert conn.execute("SELECT COUNT(*) FROM sportsdb_highlight_feed_cache WHERE cache_key LIKE 'v2:%'").fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM sportsdb_match_highlights').fetchone()[0] == 0


def test_v2_does_not_treat_old_live_score_as_final(store, monkeypatch):
    with sqlite3.connect(store) as conn:
        conn.execute("UPDATE matches SET status='LIVE',match_date='2026-10-02'")
    calls = []
    monkeypatch.setattr(media, '_sportsdb_v1', lambda *a: {'events': []})
    monkeypatch.setattr(media, '_sportsdb_v2', lambda *a: calls.append(a) or {'lookup': []})
    result = media.sync_sportsdb_highlights(store, days_back=1)
    assert result['v2_event_lookups'] == 0 and calls == []
