"""Isolated execution of the actual app reader AST with its real classifiers.

Synthetic SQLite data, no Flask routes or real playback certified. Repository app.py is the default source. MEDIA_APP_SOURCE only supports
an explicit before/after control run; production code is never replaced at runtime.
"""
import ast
import copy
import os
import sqlite3
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
from engines.sportsdb_highlights_engine import classify_stored_highlight
from engines.video_highlights_engine import video_highlights_snapshot

@pytest.fixture
def reader(monkeypatch):
    def no_network(*a,**kw):
        raise AssertionError('NETWORK_FORBIDDEN_IN_ISOLATED_TEST')
    monkeypatch.setattr('urllib.request.urlopen', no_network)
    monkeypatch.setattr('socket.create_connection', no_network)
    source=Path(os.environ.get('MEDIA_APP_SOURCE',ROOT/'app.py')).read_text(encoding='utf-8-sig')
    module=ast.parse(source)
    function=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='_cached_match_media')
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE sportsdb_match_highlights(match_id TEXT, video_url TEXT, rights_status TEXT, commercial_use_status TEXT, updated_at TEXT, source TEXT)')
    calls=[]
    def query(sql,params):
        calls.append((sql,params));return [dict(r) for r in db.execute(sql,params)]
    space={'db_table_exists':lambda _:db.execute("SELECT 1 FROM sqlite_master WHERE name='sportsdb_match_highlights'").fetchone() is not None,
           'rows':query,'classify_stored_highlight':classify_stored_highlight,'video_highlights_snapshot':video_highlights_snapshot}
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(ROOT/'app.reader.ast.py'),'exec'),space)
    yield db,space['_cached_match_media'],calls
    db.close()

def add(db,local_id,rights='LICENSED',commercial='ALLOWED',url='https://www.youtube.com/watch?v=SIMULATED_QA',stamp='2026-09-20'):
    db.execute('INSERT INTO sportsdb_match_highlights VALUES(?,?,?,?,?,?)',(local_id,url,rights,commercial,stamp,'synthetic-test-only'))
    db.commit()

def visible(result):
    return [r['match_id'] for r in result['visible_videos']]

@pytest.mark.parametrize('external',['77',77,'sportsdb-77','af-77'])
def test_external_id_cannot_be_read_as_local_match_id(reader,external):
    db,read,_=reader;add(db,str(external))
    result=read({'id':'local-A','external_id':external})
    assert result['visible_count']==0
    assert result['videos']==[]

@pytest.mark.parametrize('match',[{},None,{'external_id':'77'},{'id':None,'external_id':'77'},{'id':'','external_id':'77'},{'id':'  ','external_id':'77'}])
def test_absent_local_identity_never_falls_back(reader,match):
    db,read,calls=reader;add(db,'77')
    assert read(match)['videos']==[]
    assert not calls

@pytest.mark.parametrize('local',['77',77,'local-A','af-77','sportsdb-77',0])
def test_explicit_local_association_is_preserved(reader,local):
    db,read,_=reader;add(db,str(local))
    assert visible(read({'id':local,'external_id':'different'}))==[str(local)]

def test_two_matches_with_colliding_identifiers_stay_separate(reader):
    db,read,_=reader;add(db,'local-A');add(db,'77')
    assert visible(read({'id':'local-A','external_id':'77'}))==['local-A']
    assert visible(read({'id':'77','external_id':'123'}))==['77']

@pytest.mark.parametrize('rights,commercial',[('UNKNOWN_RIGHTS','UNKNOWN'),('BLOCKED','ALLOWED'),('LICENSED','DENIED')])
def test_local_identity_does_not_approve_rights(reader,rights,commercial):
    db,read,_=reader;add(db,'local-A',rights,commercial)
    assert read({'id':'local-A','external_id':'77'})['visible_count']==0

def test_query_is_parameterized_and_does_not_accept_sql_as_an_alias(reader):
    db,read,calls=reader;add(db,'77');add(db,'local-A')
    bad="' OR 1=1 --"
    assert read({'id':bad,'external_id':'77'})['videos']==[]
    assert calls[-1][1][0]==bad and bad not in calls[-1][0]

def test_read_does_not_write_or_mutate_match(reader):
    db,read,_=reader;add(db,'local-A');add(db,'77')
    match={'id':'local-A','external_id':'77'};old=copy.deepcopy(match)
    before=list(db.iterdump());changes=db.total_changes
    assert visible(read(match))==['local-A']
    assert match==old and list(db.iterdump())==before and db.total_changes==changes

def test_missing_table_remains_empty_without_schema_creation(reader):
    db,read,calls=reader;db.execute('DROP TABLE sportsdb_match_highlights');count=db.total_changes
    assert read({'id':'local-A','external_id':'77'})['visible_count']==0
    assert not calls and db.total_changes==count

def test_existing_limit_still_applies_within_the_requested_match(reader):
    db,read,_=reader
    for i in range(4):add(db,'local-A',stamp=f'2026-09-2{i}')
    add(db,'77',stamp='2026-09-30')
    assert visible(read({'id':'local-A','external_id':'77'},limit=2))==['local-A','local-A']
