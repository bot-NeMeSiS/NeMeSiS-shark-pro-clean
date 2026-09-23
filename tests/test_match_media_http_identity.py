"""Actual Flask views and SQLite media reads: synthetic records, no provider I/O.

These tests import the real app and render its templates. They do not replace
match_detail, _cached_match_media, the classifier or template rendering.
"""
from __future__ import annotations

from contextlib import contextmanager
import sqlite3

import pytest
from flask import template_rendered

from engines.sportsdb_highlights_engine import ensure_sportsdb_highlights_schema

LOCAL_A = 'media-qa-local-A'
LOCAL_B = '7700051'
URL_A = 'https://www.youtube.com/watch?v=localVideo1'
URL_B = 'https://www.youtube.com/watch?v=otherVideo2'


@contextmanager
def rendered_contexts(app):
    records = []
    def record(sender, template, context, **extra):
        records.append(context)
    template_rendered.connect(record, app)
    try:
        yield records
    finally:
        template_rendered.disconnect(record, app)


@pytest.fixture
def media_http(app_module, tmp_path, monkeypatch):
    calls = []
    def no_network(*args, **kwargs):
        calls.append('blocked')
        raise AssertionError('External I/O is not allowed in synthetic media tests')
    monkeypatch.setattr('urllib.request.urlopen', no_network)
    monkeypatch.setattr('socket.create_connection', no_network)
    monkeypatch.setattr('requests.sessions.Session.request', no_network)
    path = tmp_path / 'media-http.sqlite'
    monkeypatch.setattr(app_module, 'DB_PATH', str(path))
    monkeypatch.setattr(app_module, 'APP_INITIALIZED', False)
    monkeypatch.setattr(app_module, '_SEEDED_DB_PATH', '')
    app_module.initialize_once()
    ensure_sportsdb_highlights_schema(str(path))
    with sqlite3.connect(path) as conn:
        for local_id, external, home, away in (
            (LOCAL_A, LOCAL_B, 'QA Norte', 'QA Sur'),
            (LOCAL_B, 'different-provider-id', 'QA Este', 'QA Oeste'),
        ):
            conn.execute('''INSERT INTO matches
                (id,external_id,sport_key,home_team,away_team,competition_name,
                 source,status,match_date,kickoff_iso,home_score,away_score)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (local_id,external,'soccer',home,away,'Liga QA','TheSportsDB API',
                 'FT','2026-09-20','2026-09-20T18:00:00+00:00',2,1))
    def add(local_id, *, rights='LICENSED', commercial='ALLOWED', embed=False):
        video_id = 'qa-video-A' if local_id == LOCAL_A else 'qa-video-B'
        original = URL_A if local_id == LOCAL_A else URL_B
        iframe = original.replace('www.youtube.com/watch?v=', 'www.youtube-nocookie.com/embed/') if embed else ''
        with sqlite3.connect(path) as conn:
            conn.execute('''INSERT INTO sportsdb_match_highlights
                (id,match_id,title,video_url,embed_url,source,rights_status,
                 commercial_use_status,attribution,attribution_required,
                 rights_verified_at,allowed_channels_json,embed_policy,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (video_id,local_id,'SIMULATED_QA summary',original,iframe,
                 'synthetic-test-only',rights,commercial,'Synthetic QA attribution',1,
                 '2026-09-22T19:00:00Z','["APP"]','EMBED' if embed else 'LINK_ONLY',
                 '2026-09-22T19:00:00Z'))
        return video_id
    try:
        yield app_module, app_module.app.test_client(), path, add
        assert calls == [], 'A request attempted external I/O even if it caught the error'
    finally:
        app_module.invalidate_v934_realtime_cache('v934:sports:')


def media_rows(path):
    with sqlite3.connect(path) as conn:
        return conn.execute('SELECT * FROM sportsdb_match_highlights ORDER BY id').fetchall()


@pytest.mark.parametrize('prefix', ['/match/', '/partido/'])
def test_http_external_id_collision_never_displays_foreign_video(media_http, prefix):
    module, client, path, add = media_http
    add(LOCAL_B)
    before = media_rows(path)
    with rendered_contexts(module.app) as contexts:
        response = client.get(prefix + LOCAL_A)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert URL_B not in html and 'otherVideo2' not in html
    assert contexts[-1]['detail']['media']['videos'] == []
    assert contexts[-1]['match_context']['media']['visible_count'] == 0
    assert 'data-highlight-availability="unavailable"' in html
    assert media_rows(path) == before


@pytest.mark.parametrize('prefix', ['/match/', '/partido/'])
def test_http_two_fixtures_keep_only_their_own_authorized_video(media_http, prefix):
    module, client, path, add = media_http
    add(LOCAL_A); add(LOCAL_B)
    before = media_rows(path)
    for local_id, own, other in ((LOCAL_A, URL_A, URL_B), (LOCAL_B, URL_B, URL_A)):
        with rendered_contexts(module.app) as contexts:
            response = client.get(prefix + local_id)
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert own in html and other not in html
        assert [row['match_id'] for row in contexts[-1]['detail']['media']['visible_videos']] == [local_id]
        assert '<iframe' not in html
        assert 'data-match-region="authorized-video"' in html
    assert media_rows(path) == before


@pytest.mark.parametrize('rights,commercial', [('UNKNOWN_RIGHTS','UNKNOWN'), ('BLOCKED','ALLOWED'), ('LICENSED','DENIED')])
def test_http_local_rights_denial_cannot_fall_back_to_foreign_authorization(media_http, rights, commercial):
    module, client, path, add = media_http
    add(LOCAL_A, rights=rights, commercial=commercial); add(LOCAL_B)
    response = client.get('/match/' + LOCAL_A)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert URL_A not in html and URL_B not in html
    assert 'data-match-region="authorized-video"' not in html


def test_http_revocation_is_visible_on_next_request_without_caching_old_permission(media_http):
    module, client, path, add = media_http
    video_id = add(LOCAL_A); add(LOCAL_B)
    assert URL_A in client.get('/match/' + LOCAL_A).get_data(as_text=True)
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE sportsdb_match_highlights SET rights_status='BLOCKED' WHERE id=?", (video_id,))
    html = client.get('/match/' + LOCAL_A).get_data(as_text=True)
    assert URL_A not in html and URL_B not in html


def test_http_authorized_embed_is_not_loaded_during_render(media_http):
    module, client, path, add = media_http
    add(LOCAL_A, embed=True); add(LOCAL_B, embed=True)
    html = client.get('/match/' + LOCAL_A).get_data(as_text=True)
    assert 'data-highlight-load' in html and 'localVideo1' in html
    assert 'otherVideo2' not in html and '<iframe' not in html
    assert 'autoplay=1' not in html


def test_http_missing_match_stays_404_without_foreign_fallback(media_http):
    module, client, path, add = media_http
    add(LOCAL_B)
    response = client.get('/match/media-qa-missing')
    assert response.status_code == 404
    assert URL_B not in response.get_data(as_text=True)


@pytest.mark.parametrize('local_id', [LOCAL_A, LOCAL_B])
def test_existing_match_detail_api_preserves_local_identity(media_http, local_id):
    # This API does not promise a media section; assert its existing data contract.
    module, client, path, add = media_http
    add(LOCAL_A); add(LOCAL_B)
    response = client.get('/api/matches/' + local_id + '/detail')
    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] and str(data['detail']['match']['id']) == local_id
    assert data['side_effects'] == {'database_writes': 0, 'external_calls': 0}


def test_http_reader_and_classifiers_do_not_modify_saved_metadata(media_http):
    module, client, path, add = media_http
    add(LOCAL_A)
    before = media_rows(path)
    assert client.get('/match/' + LOCAL_A + '?refresh=1').status_code == 200
    assert media_rows(path) == before
