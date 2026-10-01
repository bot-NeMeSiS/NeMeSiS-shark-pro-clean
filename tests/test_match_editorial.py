"""Editorial: factual copy, scoped news publication and safe failure states.

Synthetic records only; no network, real accounts, subscriptions or credentials.
"""
import copy
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

import pytest
from flask import Flask
from engines.match_editorial_engine import build_editorial
from engines import match_news_store as news
from engines.postmatch_store import identity
from blueprints.media_review import create_media_review_blueprint

NOW = datetime(2026,10,1,14,tzinfo=timezone.utc).timestamp()
MATCH = dict(id='ed-qa', home_team='Equipo Uno', away_team='Equipo Dos',
             match_date='2026-09-30', kickoff_time='18:00', competition_name='Liga QA', source='test-source')
CONTEXT = dict(lifecycle={'key':'FINISHED','is_finished':True,'label':'Finalizado'},
    score={'confirmed':True,'home':0,'away':0,'label':'0-0'},
    story={'summary':'Equipo Uno y Equipo Dos finalizaron con marcador 0-0.'},
    evidence={'source':'Fuente QA','updated_at':'2026-09-30T20:00:00Z'},
    statistics={'available':True,'source':'Fuente QA','items':[{'label':'Córners','home':'0','away':'3'}]},
    event_summary={'available':False},media={'visible_videos':[]})


@pytest.fixture
def db(tmp_path):
    path=tmp_path/'editorial.sqlite'
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE matches ('+','.join(k+' TEXT' for k in MATCH)+')')
        c.execute('INSERT INTO matches VALUES('+','.join('?' for _ in MATCH)+')',tuple(MATCH.values()))
    return path


def entry():
    return {'identity':identity(MATCH),'url':'https://sports.example.com/report?utm_source=test',
        'title':'Referencia descriptiva de prueba','publisher':'Medio QA',
        'published_at':'2026-09-30T21:00:00+02:00',
        'evidence_url':'https://sports.example.com/terms',
        'basis':'Fixture sintética; no se atribuyen permisos a un medio real.','confirmed':'1'}


def publish(db):
    nid=news.save_draft(db,MATCH['id'],entry(),actor='qa',now=NOW)
    row=news.snapshot(db,MATCH['id'],admin=True)['items'][0]
    news.decide(db,MATCH['id'],nid,{'action':'PUBLISH','confirmed':'1','revision':row['revision']},actor='qa',now=NOW+1)
    return nid


def test_projection_is_pure_and_preserves_confirmed_nil_draw():
    before=copy.deepcopy(CONTEXT)
    result=build_editorial(CONTEXT)
    assert CONTEXT==before
    assert '0-0' in result['summary']
    assert result['facts'][0]['home']=='0'
    assert result['generative_ai_calls']==result['external_calls']==0
    assert result['revision']==build_editorial(CONTEXT)['revision']


def test_no_score_infers_finish():
    ctx=copy.deepcopy(CONTEXT);ctx['lifecycle']={'key':'UPCOMING'}
    ctx['story']={'summary':'Encuentro programado.'}
    result=build_editorial(ctx)
    assert result['title']=='Antes del partido'
    assert '0-0' not in result['summary']


def test_stale_does_not_generate_live_chronicle():
    ctx=copy.deepcopy(CONTEXT);ctx['lifecycle']['is_stale']=True
    ctx['lifecycle']['is_live']=True
    result=build_editorial(ctx)
    assert not result['facts'] and not result['moments']
    assert 'no se presenta como información actual' in result['summary']


def test_fact_blocks_require_source():
    ctx=copy.deepcopy(CONTEXT);ctx['statistics'].pop('source')
    assert not build_editorial(ctx)['facts']


def test_events_deduplicated_bounded_not_invented():
    ctx=copy.deepcopy(CONTEXT)
    event={'id':'g1','type':'goal','label':'Gol','minute_label':"14′",'player':'Jugador QA'}
    ctx['event_summary']={'available':True,'source':'QA','items':[event,event,{'type':'unknown','label':'Ruido'}]}
    result=build_editorial(ctx)
    assert len(result['moments'])==1
    assert result['moments'][0]['player']=='Jugador QA'
    assert 'domin' not in result['summary'] and 'merec' not in result['summary']


@pytest.mark.parametrize('bad',[
 'http://sports.example.com','javascript:alert(1)','https://user:pw@example.com',
 'https://127.0.0.1/a','https://127.1/a','https://0x7f.1/a','https://[::1]/','https://local/a','https://test.internal/a',
 'https://safe.example.com\\@evil.com','https://safe.example.com/?token=secret',
 'https://safe.example.com:443/a','https://safe.example.com/\nfoo',
 'https://safe.example.com./','https://safe.example.com/?api_key=x'])
def test_dangerous_urls_rejected(bad):
    with pytest.raises(news.NewsError):news.safe_url(bad)


def test_tracking_params_removed_without_fetching():
    assert news.safe_url('https://sports.example.com/a?id=2&utm_campaign=x#z')=='https://sports.example.com/a?id=2'


def test_read_missing_database_does_not_create_file(tmp_path):
    p=tmp_path/'absent.sqlite'
    assert news.snapshot(p,'x')['state']=='READ_UNAVAILABLE'
    assert not p.exists()


def test_read_uninitialized_keeps_schema_and_bytes(db):
    before=db.read_bytes()
    result=news.snapshot(db,MATCH['id'])
    assert result['state']=='NOT_INITIALIZED'
    assert db.read_bytes()==before
    with sqlite3.connect(db) as c: assert not c.execute("SELECT name FROM sqlite_master WHERE name='match_news_references'").fetchall()


def test_draft_not_visible_and_publish_retract_audited(db):
    nid=news.save_draft(db,MATCH['id'],entry(),actor='qa',now=NOW)
    assert not news.snapshot(db,MATCH['id'])['items']
    row=news.snapshot(db,MATCH['id'],admin=True)['items'][0]
    action={'action':'PUBLISH','confirmed':'1','revision':row['revision']}
    news.decide(db,MATCH['id'],nid,action,actor='qa',now=NOW+1)
    public=news.snapshot(db,MATCH['id'])['items'][0]
    assert 'basis' not in public and 'reviewed_by' not in public and 'evidence_url' not in public
    news.decide(db,MATCH['id'],nid,{'action':'RETRACT','confirmed':'1','revision':public['revision']},actor='qa',now=NOW+2)
    assert not news.snapshot(db,MATCH['id'])['items']
    with sqlite3.connect(db) as c: assert c.execute('SELECT count(*) FROM match_news_audit').fetchone()[0]==3


def test_identity_change_removes_old_reference_from_client(db):
    publish(db)
    with sqlite3.connect(db) as c:c.execute("UPDATE matches SET away_team='Otro equipo'")
    assert not news.snapshot(db,MATCH['id'])['items']
    with sqlite3.connect(db) as c:assert c.execute('SELECT count(*) FROM match_news_references').fetchone()[0]==1


def test_double_submission_does_not_duplicate_or_unpublish(db):
    publish(db)
    with pytest.raises(news.NewsError):news.save_draft(db,MATCH['id'],entry(),actor='qa',now=NOW+4)
    assert len(news.snapshot(db,MATCH['id'])['items'])==1


def test_stale_decision_cannot_override_later_review(db):
    nid=publish(db)
    with pytest.raises(news.NewsError):news.decide(db,MATCH['id'],nid,{'action':'RETRACT','confirmed':'1','revision':'old'},actor='qa',now=NOW+2)
    assert len(news.snapshot(db,MATCH['id'])['items'])==1


@pytest.mark.parametrize('changes',[{'confirmed':''},{'identity':'different'},{'published_at':'2027-10-01T00:00:00Z'},
 {'published_at':'2026-09-30T20:00:00'},{'published_at':'2025-10-01T00:00:00Z'},{'basis':''}])
def test_invalid_editorial_input_does_not_create_schema(db,changes):
    with pytest.raises(news.NewsError):news.save_draft(db,MATCH['id'],{**entry(),**changes},actor='qa',now=NOW)
    with sqlite3.connect(db) as c:assert not c.execute("SELECT name FROM sqlite_master WHERE name='match_news_references'").fetchall()


def test_one_match_does_not_receive_other_match_news(db):
    publish(db)
    with sqlite3.connect(db) as c:
        other={**MATCH,'id':'other'}
        c.execute('INSERT INTO matches VALUES('+','.join('?' for _ in other)+')',tuple(other.values()))
    assert not news.snapshot(db,'other')['items']


def test_corrupt_database_not_presented_as_empty(tmp_path):
    p=tmp_path/'bad.sqlite';p.write_bytes(b'not-a-database')
    result=news.snapshot(p,'a')
    assert result['state']=='READ_UNAVAILABLE'
    assert build_editorial(CONTEXT,result)['news_state']=='READ_UNAVAILABLE'


def test_editorial_routes_require_admin_and_csrf(db):
    app=Flask(__name__);app.secret_key='local-only'
    flag={'admin':False}
    app.register_blueprint(create_media_review_blueprint(str(db),lambda:flag['admin']))
    c=app.test_client()
    assert c.get('/admin/highlights-review/news').status_code==403
    assert c.post('/admin/highlights-review/news/ed-qa/save',data=entry()).status_code==403
    flag['admin']=True
    assert c.post('/admin/highlights-review/news/ed-qa/save',data=entry()).status_code==403


def test_unverified_news_snapshot_never_promoted():
    result=build_editorial(CONTEXT,{'state':'READ_UNAVAILABLE','items':[{'title':'hidden'}]})
    assert not result['news']


def test_positive_http_editorial_write_flow(db):
    app=Flask(__name__);app.secret_key='local-test-only'
    app.register_blueprint(create_media_review_blueprint(str(db),lambda:True))
    c=app.test_client()
    with c.session_transaction() as session:
        session['csrf_token']='csrf-offline-qa';session['user_id']='admin-qa'
    response=c.post('/admin/highlights-review/news/ed-qa/save',data={**entry(),'csrf_token':'csrf-offline-qa'})
    assert response.status_code==303
    assert response.headers['Cache-Control']=='private, no-store'
    row=news.snapshot(db,'ed-qa',admin=True)['items'][0]
    endpoint=f"/admin/highlights-review/news/ed-qa/{row['id']}/decision"
    response=c.post(endpoint,data={'action':'PUBLISH','revision':row['revision'],'confirmed':'1','csrf_token':'csrf-offline-qa'})
    assert response.status_code==303 and len(news.snapshot(db,'ed-qa')['items'])==1
    row=news.snapshot(db,'ed-qa')['items'][0]
    response=c.post(endpoint,data={'action':'RETRACT','revision':row['revision'],'confirmed':'1','csrf_token':'csrf-offline-qa'})
    assert response.status_code==303 and not news.snapshot(db,'ed-qa')['items']


def test_restart_retains_review_and_schema(db):
    nid=publish(db)
    # Every call opens a new readonly connection; nothing depends on process memory.
    first=news.snapshot(str(db),'ed-qa')
    second=news.snapshot(Path(db),'ed-qa')
    assert first['items']==second['items']
    assert second['items'][0]['id']==nid
