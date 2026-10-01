"""Readiness diagnostics and visible failure states; no live content authorizations."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, select_autoescape
from engines import sportsdb_highlights_engine as media
from engines.highlight_read_model import read_highlights_readiness

ROOT=Path(__file__).resolve().parents[1]


def env():
    e=Environment(loader=ChoiceLoader([DictLoader({'base.html':'{% block content %}{% endblock %}'}),FileSystemLoader(ROOT/'templates')]),autoescape=select_autoescape())
    e.globals.update(url_for=lambda *a,**kw:'/static/'+kw.get('filename',''),csrf_token=lambda:'synthetic')
    e.filters['madrid_datetime_label']=str
    e.filters['match_madrid_context']=lambda x:x
    return e


@pytest.mark.parametrize('state',['READ_UNAVAILABLE','NO_DATABASE','CATALOGUE_NOT_INITIALIZED'])
def test_client_does_not_render_absence_counts_for_failed_catalogue(state):
    html=env().get_template('highlights.html').render(data={'v766_highlights':{'status':state},'v769_highlights_center':{'counts':{'videos':0,'linked_matches':0,'pending':0,'embeddable':0}}})
    assert 'Disponibilidad sin comprobar' in html
    assert '<strong>0</strong>' not in html
    assert 'No hay resúmenes disponibles' not in html
    assert 'Partidos sin vídeo disponible' not in html


@pytest.mark.parametrize('state',['READ_UNAVAILABLE','NOT_SYNCED'])
def test_admin_does_not_print_zero_stored_during_read_failure(state):
    html=env().get_template('admin_highlights_review.html').render(review={'state':state,'counts':{},'sample_limit':40,'runs':[],'items':[]},review_error='')
    assert '0 registros guardados' not in html
    assert 'Recuento no verificable' in html
    assert 'No hay enlaces para revisar' not in html
    assert 'No se ha podido establecer la lista' in html
    assert '/api/admin/highlights/readiness' in html


def test_verified_empty_admin_catalogue_is_valid_zero():
    html=env().get_template('admin_highlights_review.html').render(review={'state':'NO_LINKS_RECORDED','counts':{'stored':0},'sample_limit':40,'runs':[],'items':[]},review_error='')
    assert '0 registros guardados' in html


def test_diagnostic_excludes_raw_records_keys_and_paths(tmp_path,monkeypatch):
    path=tmp_path/'private.sqlite';media.ensure_sportsdb_highlights_schema(path)
    monkeypatch.setenv('THESPORTSDB_KEY','SYNTHETIC_SECRET_NEVER_REAL')
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("INSERT INTO sportsdb_match_highlights(id,match_id,video_url,raw_json) VALUES('h','m','https://example.org/private-url','private-payload')");conn.commit()
    before=path.read_bytes();r=read_highlights_readiness(path);blob=json.dumps(r)
    assert r['ok'] and r['metadata']['stored_media_total']==1
    assert r['storage']['database_bytes']==len(before)
    assert r['storage']['filesystem_free_bytes']>0
    assert r['external_calls']==0 and not r['production_activation_certified'] and not r['playback_verified']
    for value in (str(path),'private-url','private-payload','SYNTHETIC_SECRET_NEVER_REAL'):
        assert value not in blob
    assert path.read_bytes()==before


def test_unknown_storage_is_not_zero_free_space(tmp_path,monkeypatch):
    path=tmp_path/'media.sqlite';media.ensure_sportsdb_highlights_schema(path)
    def fail(*a):raise OSError('sensitive mount path')
    monkeypatch.setattr('shutil.disk_usage',fail)
    r=read_highlights_readiness(path)
    assert r['ok'] is True  # this flag refers to the catalogue, not capacity approval
    assert r['storage']['state']=='READ_UNAVAILABLE'
    assert r['storage']['filesystem_free_bytes'] is None
    assert 'sensitive' not in json.dumps(r)
    assert r['production_activation_certified'] is False


def test_cli_is_read_only_and_failure_is_not_pass(tmp_path):
    path=tmp_path/'absent.sqlite'
    r=subprocess.run([sys.executable,str(ROOT/'tools/check_highlights_readiness.py'),'--db-path',str(path)],capture_output=True,text=True,timeout=10)
    assert r.returncode==2 and not path.exists()
    assert json.loads(r.stdout)['read_state']=='NO_DATABASE'
    media.ensure_sportsdb_highlights_schema(path);before=path.read_bytes()
    r=subprocess.run([sys.executable,str(ROOT/'tools/check_highlights_readiness.py'),'--db-path',str(path)],capture_output=True,text=True,timeout=10)
    assert r.returncode==0 and path.read_bytes()==before
    assert not json.loads(r.stdout)['production_activation_certified']


def test_admin_endpoint_is_protected_private_and_read_only(tmp_path):
    from flask import Flask,session
    from blueprints.media_review import create_media_review_blueprint
    path=tmp_path/'media.sqlite';media.ensure_sportsdb_highlights_schema(path);before=path.read_bytes()
    app=Flask(__name__);app.secret_key='synthetic-test-only';app.testing=True
    app.register_blueprint(create_media_review_blueprint(path,lambda:session.get('admin',False)))
    c=app.test_client()
    assert c.get('/api/admin/highlights/readiness').status_code==403
    with c.session_transaction() as s:s['admin']=True
    r=c.get('/api/admin/highlights/readiness')
    assert r.status_code==200 and r.json['metadata']['stored_media_total']==0
    assert 'no-store' in r.headers['Cache-Control'] and 'Cookie' in r.headers['Vary']
    assert path.read_bytes()==before
    assert c.post('/api/admin/highlights/readiness').status_code==405


def test_admin_endpoint_returns_unavailable_without_initializing(tmp_path):
    from flask import Flask
    from blueprints.media_review import create_media_review_blueprint
    path=tmp_path/'missing.sqlite'
    app=Flask(__name__);app.testing=True
    app.register_blueprint(create_media_review_blueprint(path,lambda:True))
    r=app.test_client().get('/api/admin/highlights/readiness')
    assert r.status_code==503 and r.json['read_state']=='NO_DATABASE' and not path.exists()
