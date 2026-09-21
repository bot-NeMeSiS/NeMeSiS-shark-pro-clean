"""Synthetic media metadata only: no provider calls, secrets or video downloads."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pytest
from flask import Flask, session
from jinja2 import DictLoader
from engines import sportsdb_highlights_engine as media
from engines.highlight_review_engine import ReviewError, decide_highlight, review_snapshot
from engines.highlight_url_engine import public_https_url, safe_embed_url
from engines.security_engine import generate_csrf_token
from engines.video_highlights_engine import classify_match_video

URL = 'https://www.youtube.com/watch?v=officialQA1'
NEW = 'https://youtu.be/anotherQA12'

@pytest.fixture
def store(tmp_path):
    db = str(tmp_path / 'media.db')
    media.ensure_sportsdb_highlights_schema(db)
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE matches(id TEXT,external_id TEXT,source TEXT,home_team TEXT,away_team TEXT,match_date TEXT,league_id TEXT,league_name TEXT)')
        conn.execute("INSERT INTO matches VALUES ('m1','123','TheSportsDB API','Norte','Sur','2026-09-20','1','Liga QA')")
    return db


def payload(**kwargs):
    return {'idEvent':'123','dateEvent':'2026-09-20','strHomeTeam':'Norte','strAwayTeam':'Sur','strLeague':'Liga QA','strVideo':URL, **kwargs}


def save(db, item=None):
    with media._connect(db) as conn:
        return media._upsert_highlight(conn, item or payload())


def values(row, **kwargs):
    return {'decision':'LINK_ONLY','review_token':row['review_token'],'evidence_url':'https://example.org/licence',
            'attribution':'Fuente autorizada QA', 'basis':'Licencia sintética de prueba para esta URL en APP, no real.',
            'rights_status':'LICENSED','confirmed':'1', **kwargs}

@pytest.mark.parametrize('url', ['javascript:alert(1)','http://youtube.com/watch?v=a','https://user:pass@youtube.com/watch?v=a',
 'https://127.0.0.1/v','https://127.0.0.1.nip.io/v\nX','https://localhost/v','https://host.local/v','https://youtube.com:444/watch?v=a',
 'https://youtube.com\\@evil.org/v','https://youtube.com/watch?v=a\r\nX','https://[::1]/v'])
def test_invalid_urls_do_not_publish(url):
    assert public_https_url(url) == ''
    decision = classify_match_video({'original_url':url,'embed_url':url,'rights_status':'LICENSED','commercial_use_status':'ALLOWED'})
    assert not decision['show_block']

@pytest.mark.parametrize('url', ['https://youtube.com.evil.org/embed/a','https://notyoutube.com/embed/a','https://example.org/embed/a',
 'https://www.youtube.com/embed/a/extra','https://www.youtube.com/watch?v=a&v=b'])
def test_lookalike_or_ambiguous_players_rejected(url):
    assert safe_embed_url(url) == ''


def test_different_embed_video_cannot_replace_original():
    assert safe_embed_url(URL, 'https://www.youtube.com/embed/different') == ''
    assert '?autoplay' not in safe_embed_url(URL, 'https://www.youtube.com/embed/officialQA1?autoplay=1')


def test_provider_links_never_auto_approve(store):
    save(store, payload(rights_status='LICENSED', commercial_use_status='ALLOWED', official_source_verified=True))
    snapshot = review_snapshot(store)
    assert snapshot['counts']['stored'] == 1
    assert not snapshot['items'][0]['can_display']
    assert media.sportsdb_highlights_for_match(store, 'm1')['highlights'] == []

@pytest.mark.parametrize('missing', ['evidence_url','attribution','basis','confirmed','rights_status','review_token'])
def test_incomplete_review_cannot_approve(store, missing):
    save(store); row = review_snapshot(store)['items'][0]
    with pytest.raises(ReviewError):
        decide_highlight(store, row['id'], values(row, **{missing:''}), actor='test-admin')
    assert not review_snapshot(store)['items'][0]['can_display']


def test_review_is_audited_scoped_and_race_checked(store):
    save(store); row = review_snapshot(store)['items'][0]
    decide_highlight(store, row['id'], values(row), actor='test-admin')
    visible = media.sportsdb_highlights_for_match(store, 'm1')['highlights'][0]
    assert visible['can_link'] and not visible['can_embed']
    assert visible['allowed_channels'] == ['APP']
    assert not media.classify_stored_highlight(visible, channel='TELEGRAM')['show_block']
    from engines.telegram_activity_engine import should_send_highlight_alert
    assert not should_send_highlight_alert({'has_pick':True}, visible)
    with pytest.raises(ReviewError, match='cambiado'):
        decide_highlight(store, row['id'], values(row), actor='other-admin')
    with sqlite3.connect(store) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sportsdb_highlight_reviews').fetchone()[0] == 1
        assert conn.execute('SELECT actor,evidence_url FROM sportsdb_highlight_reviews').fetchone() == ('test-admin','https://example.org/licence')


def test_link_only_survives_resync_but_changed_video_requires_review(store):
    save(store); row = review_snapshot(store)['items'][0]
    decide_highlight(store, row['id'], values(row), actor='test-admin')
    save(store)
    h = media.sportsdb_highlights_for_match(store,'m1')['highlights'][0]
    assert h['can_link'] and not h['can_embed'] and h['allowed_channels'] == ['APP']
    save(store, payload(strVideo=NEW))
    assert media.sportsdb_highlights_for_match(store,'m1')['highlights'] == []
    with sqlite3.connect(store) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sportsdb_highlight_reviews').fetchone()[0] == 1


def test_embed_approval_and_revocation(store):
    save(store); row = review_snapshot(store)['items'][0]
    decide_highlight(store,row['id'], values(row, decision='EMBED', official='1'),actor='test-admin')
    h = media.sportsdb_highlights_for_match(store,'m1')['highlights'][0]
    assert h['can_embed'] and h['video_classification'] == 'OFFICIAL_EMBED'
    row = review_snapshot(store)['items'][0]
    decide_highlight(store,row['id'], values(row,decision='BLOCKED',confirmed=''),actor='test-admin')
    assert media.sportsdb_highlights_for_match(store,'m1')['highlights'] == []


def test_missing_or_deleted_match_cannot_approve(store):
    save(store); row = review_snapshot(store)['items'][0]
    with sqlite3.connect(store) as conn: conn.execute('DELETE FROM matches')
    with pytest.raises(ReviewError, match='no existe'):
        decide_highlight(store,row['id'],values(row),actor='test-admin')


def test_get_does_not_create_or_migrate_database(tmp_path):
    path = tmp_path/'missing.db'; assert review_snapshot(path)['state']=='NOT_SYNCED'; assert not path.exists()
    with sqlite3.connect(path) as conn: conn.execute('CREATE TABLE unrelated(id TEXT)')
    before=path.read_bytes(); review_snapshot(path); assert path.read_bytes()==before


def test_provider_id_is_scoped_and_substring_linking_removed(store):
    with media._connect(store) as conn:
        assert media._find_match(conn,payload())=='m1'
        conn.execute("UPDATE matches SET source='API-Football',home_team='Other',away_team='Teams'")
        assert media._find_match(conn,payload()) is None
        conn.execute("UPDATE matches SET home_team='Norte United',away_team='Sur'")
        assert media._find_match(conn,payload(idEvent='new')) is None


def test_ambiguous_pair_not_linked(store):
    with media._connect(store) as conn:
        conn.execute("INSERT INTO matches SELECT 'm2','456',source,home_team,away_team,match_date,league_id,league_name FROM matches")
        assert media._find_match(conn,payload(idEvent='unknown')) is None


def test_sync_is_bounded_and_does_not_hold_write_lock(store, monkeypatch):
    monkeypatch.setenv('THESPORTSDB_API_KEY','test-only')
    monkeypatch.setenv('THESPORTSDB_HIGHLIGHTS_DAILY_CALL_BUDGET','2')
    calls=[]
    def fetch(endpoint, params):
        # Prove an independent writer can acquire SQLite during provider I/O.
        with sqlite3.connect(store,timeout=.1) as conn:
            conn.execute('BEGIN IMMEDIATE');conn.execute("UPDATE matches SET league_name='Liga QA'");conn.commit()
        calls.append(params); return {'tv':[payload()]}
    # The documented highlights API uses tv in some historical payloads.
    monkeypatch.setattr(media,'_sportsdb_v1',fetch)
    monkeypatch.setattr(media,'rebuild_match_enrichment',lambda *a,**kw:{'updated':1})
    result=media.sync_sportsdb_highlights(store,days_back=1,limit=50)
    assert result['ok'] and result['external_calls']==2 and result['rights_auto_approved']==0
    result=media.sync_sportsdb_highlights(store,days_back=1,force=True)
    assert result['skipped'] and len(calls)==2
    with sqlite3.connect(store) as conn: conn.execute("UPDATE sportsdb_highlight_runs SET started_at='2020-01-01T00:00:00+01:00'")
    result=media.sync_sportsdb_highlights(store,days_back=1,force=True)
    assert not result['ok'] and result['external_calls']==0 and len(calls)==2
    assert result['errors']==['DAILY_BUDGET_REACHED']


def test_provider_error_never_echoes_key_or_returns_success(store,monkeypatch):
    monkeypatch.setenv('THESPORTSDB_API_KEY','TEST-NOT-A-REAL-KEY')
    def fail(*a,**kw):raise ValueError('https://api/TEST-NOT-A-REAL-KEY')
    monkeypatch.setattr(media,'_sportsdb_v1',fail)
    monkeypatch.setattr(media,'rebuild_match_enrichment',lambda *a,**kw:{})
    result=media.sync_sportsdb_highlights(store,days_back=7)
    assert not result['ok'] and result['external_calls']==1
    assert 'TEST-NOT-A-REAL-KEY' not in str(result)
    with sqlite3.connect(store) as conn: assert 'TEST-NOT-A-REAL-KEY' not in conn.execute('SELECT errors FROM sportsdb_highlight_runs').fetchone()[0]


def test_blueprint_authentication_csrf_and_post_only(store):
    from blueprints.media_review import create_media_review_blueprint
    app=Flask(__name__);app.secret_key='synthetic-test';app.testing=True
    app.jinja_loader=DictLoader({'admin_highlights_review.html':'{{ review.state }} {{ review_error }}'})
    app.register_blueprint(create_media_review_blueprint(store,lambda:session.get('is_admin',False)))
    client=app.test_client()
    assert client.get('/admin/highlights-review').status_code==403
    with client.session_transaction() as sess:sess['is_admin']=True;token=generate_csrf_token(sess)
    assert client.get('/admin/highlights-review').status_code==200
    assert client.get('/admin/highlights-review/x/decision').status_code==405
    assert client.post('/admin/highlights-review/sync').status_code==403
    save(store);row=review_snapshot(store)['items'][0]
    assert client.post('/admin/highlights-review/'+row['id']+'/decision',data={**values(row),'csrf_token':token}).status_code==303

@pytest.mark.parametrize('available',[False, True, 'false', 'true'])
def test_match_card_exposes_only_confirmed_highlight_flag(app_module,available):
    with app_module.app.test_request_context('/calendar'):
        macro=app_module.app.jinja_env.get_template('components/v933_ui.html').make_module({'current_user':None})
        result=str(macro.match_card({'id':'m1','home_team':'Norte','away_team':'Sur','competition_name':'Liga QA',
           'client_schedule_label':'20/09/2026 20:00','source':'SIMULATED_QA','has_highlights':available}))
    assert ('/match/m1#match-section-video' in result) is (available is True)


def test_main_app_registers_media_review_and_guards_it(app_module):
    routes={rule.rule for rule in app_module.app.url_map.iter_rules()}
    assert '/admin/highlights-review' in routes
    client=app_module.app.test_client()
    assert client.get('/admin/highlights-review').status_code==403
    with client.session_transaction() as sess:sess['user_role']='ADMIN'
    response=client.get('/admin/highlights-review')
    assert response.status_code==200
    assert 'Revisión de vídeo-resúmenes' in response.get_data(as_text=True)
    assert client.post('/admin/highlights-review/sync').status_code==403


def test_client_center_does_not_render_key_configuration(app_module):
    with app_module.app.test_request_context('/resumenes'):
        from flask import render_template
        result=render_template('highlights.html',data={'v769_highlights_center':{'headline':'THESPORTSDB_API_KEY secret configuration'}})
    assert 'THESPORTSDB_API_KEY secret configuration' not in result
    assert 'Resúmenes de partidos' in result
