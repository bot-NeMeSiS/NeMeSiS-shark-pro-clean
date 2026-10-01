"""Actual production blueprints and protections in an isolated Flask harness.

Full application/browser is separately verified by the permanent editorial gate.
This harness never substitutes the worker, source policy, storage or Cron auth.
"""
from flask import Flask, session
import pytest
from engines import editorial_worker as w
from engines.match_news_store import snapshot
from engines.security_engine import generate_csrf_token
from blueprints.media_review import create_media_review_blueprint
from blueprints.postmatch_recovery import create_postmatch_blueprint
from test_editorial_worker import db, DATA, NOW, MATCH, transport, enable


@pytest.fixture
def http(db,monkeypatch):
    a=Flask(__name__);a.secret_key='isolated-editorial-http-secret';a.testing=True
    a.register_blueprint(create_media_review_blueprint(str(db),lambda:session.get('is_admin') is True))
    a.register_blueprint(create_postmatch_blueprint(str(db),lambda:session.get('is_admin') is True))
    monkeypatch.setenv('AUTOMATION_SECRET','isolated-editorial-cron-secret')
    client=a.test_client()
    with client.session_transaction() as s:
        s['is_admin']=True;s['admin_id']='admin-qa';token=generate_csrf_token(s)
    return a,client,token


def test_admin_mutations_require_session_and_csrf(http,db):
    a,c,token=http
    assert c.post('/admin/highlights-review/editor/sources',data=DATA).status_code==403
    visitor=a.test_client()
    assert visitor.get('/api/admin/editorial/status').status_code==403
    assert visitor.post('/admin/highlights-review/editor/run',data={'csrf_token':token}).status_code==403
    assert not w.state(db)['sources']


def test_admin_source_save_redirects_instead_of_dumping_json(http,db,monkeypatch):
    _,c,token=http
    r=c.post('/admin/highlights-review/editor/sources',data={**DATA,'csrf_token':token})
    assert r.status_code==303 and r.location.endswith('#editorial-worker')
    assert not w.state(db)['enabled']
    revision=w.state(db)['revision']
    r=c.post('/admin/highlights-review/editor/configure',data={'csrf_token':token,'revision':revision,'enabled':'1','confirmed':'1','daily_limit':'5'})
    assert r.status_code==303 and w.state(db)['enabled']


def test_current_cron_invokes_editor_with_header_and_shared_deadline(http,db,monkeypatch):
    _,c,_=http;enable(db)
    real_tick=w.tick
    received=[]
    def tick(path,**kwargs):
        received.append(kwargs)
        return real_tick(path,clock=lambda:NOW,fetcher=transport,**kwargs)
    monkeypatch.setattr(w,'tick',tick)
    url='/api/automation/postmatch/tick'
    assert c.post(url).status_code==403
    assert c.post(url+'?secret=isolated-editorial-cron-secret').status_code==403
    assert not received
    r=c.post(url,headers={'X-Automation-Secret':'isolated-editorial-cron-secret'})
    assert r.status_code==200,r.json
    assert received and received[0]['deadline']>0
    assert r.json['editorial']['published']==1 and r.json['external_calls']==1
    assert len(snapshot(db,MATCH['id'])['items'])==1


def test_dry_run_cron_does_not_write_or_publish(http,db,monkeypatch):
    _,c,_=http;enable(db);before=db.read_bytes()
    r=c.post('/api/automation/postmatch/tick?dry_run=1',headers={'X-Automation-Secret':'isolated-editorial-cron-secret'})
    assert r.status_code==200 and r.json['editorial']['database_writes']==0
    assert db.read_bytes()==before and not snapshot(db,MATCH['id'])['items']


def test_operator_run_returns_to_panel_without_bypassing_pause(http,db):
    _,c,token=http
    r=c.post('/admin/highlights-review/editor/run',data={'csrf_token':token})
    assert r.status_code==303
    assert w.state(db)['state']=='NOT_INITIALIZED'


def test_status_private_and_has_no_lease_secrets(http,db):
    _,c,_=http;enable(db);job,_=w.claim(db,NOW)
    r=c.get('/api/admin/editorial/status')
    assert r.status_code==200 and 'no-store' in r.headers['Cache-Control']
    assert job['token'] not in r.text and 'lease_token' not in r.text
