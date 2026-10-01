"""Synthetic metadata only. Reads must not migrate, invent coverage or approve video."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from engines import sportsdb_highlights_engine as media


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError('NETWORK_FORBIDDEN')
    monkeypatch.setattr('urllib.request.urlopen', reject)
    monkeypatch.setattr('socket.create_connection', reject)


@pytest.fixture
def catalogue(tmp_path):
    path=tmp_path/'media.sqlite'
    media.ensure_sportsdb_highlights_schema(path)
    return path


def add(path, ident='h1', match='m1', rights='UNKNOWN_RIGHTS', stamp='2026-09-22T20:00:00+00:00'):
    with closing(sqlite3.connect(path)) as conn:
        conn.execute('''INSERT INTO sportsdb_match_highlights
            (id,match_id,video_url,rights_status,commercial_use_status,source,updated_at)
            VALUES(?,?,?,?,?,?,?)''',
            (ident,match,'https://www.youtube.com/watch?v=SIMULATED_QA',rights,
             'ALLOWED' if rights=='LICENSED' else 'UNKNOWN','Synthetic QA',stamp))
        conn.commit()


@pytest.mark.parametrize('kind',['summary','match'])
def test_missing_database_is_not_created(tmp_path,kind):
    path=tmp_path/'absent.sqlite'
    result=(media.sportsdb_highlights_summary(path) if kind=='summary'
            else media.sportsdb_highlights_for_match(path,'m1'))
    assert not path.exists()
    assert result['read_state']=='NO_DATABASE' and result['ok'] is False
    assert result.get('stored_media_total',result.get('rights_warnings')) is None


@pytest.mark.parametrize('kind',['summary','match'])
def test_foreign_database_is_not_initialized(tmp_path,kind):
    path=tmp_path/'unrelated.sqlite'
    with closing(sqlite3.connect(path)) as conn:
        conn.execute('CREATE TABLE unrelated(id INTEGER)');conn.commit()
    before=path.read_bytes()
    result=(media.sportsdb_highlights_summary(path) if kind=='summary'
            else media.sportsdb_highlights_for_match(path,'m1'))
    assert path.read_bytes()==before
    assert result['read_state']=='CATALOGUE_NOT_INITIALIZED'
    assert result['ok'] is False


@pytest.mark.parametrize('kind',['summary','match'])
def test_corrupt_database_is_explicit_and_not_empty(tmp_path,kind):
    path=tmp_path/'broken.sqlite';path.write_bytes(b'not-a-sqlite-database')
    before=path.read_bytes()
    result=(media.sportsdb_highlights_summary(path) if kind=='summary'
            else media.sportsdb_highlights_for_match(path,'m1'))
    assert result['ok'] is False and result['read_state']=='READ_UNAVAILABLE'
    assert path.read_bytes()==before
    assert result.get('stored_media_total',result.get('rights_warnings')) is None
    assert str(path) not in json.dumps(result)


def test_configured_key_and_empty_catalogue_do_not_mean_active(catalogue,monkeypatch):
    monkeypatch.setenv('THESPORTSDB_KEY','SYNTHETIC-DO-NOT-USE')
    result=media.sportsdb_highlights_summary(catalogue)
    assert result['read_state']=='VERIFIED'
    assert result['status']=='NO_LINKS_RECORDED'
    assert result['stored_media_total']==0
    assert result['readiness_score'] is None and result['playback_verified'] is False
    assert 'SYNTHETIC-DO-NOT-USE' not in json.dumps(result)


def test_pending_media_cannot_make_a_hundred_percent_score(catalogue,monkeypatch):
    monkeypatch.setenv('THESPORTSDB_KEY','SYNTHETIC-DO-NOT-USE')
    add(catalogue)
    with closing(sqlite3.connect(catalogue)) as conn:
        conn.execute("INSERT INTO sportsdb_match_enrichment(id,match_id) VALUES('e1','m1')");conn.commit()
    result=media.sportsdb_highlights_summary(catalogue)
    assert result['authorized_highlights']==0
    assert result['status']=='REVIEW_REQUIRED'
    assert result['readiness_score'] is None and result['playback_verified'] is False


def test_authorized_metadata_is_not_actual_playback(catalogue):
    add(catalogue,rights='LICENSED')
    result=media.sportsdb_highlights_summary(catalogue)
    assert result['authorized_highlights']==1
    assert result['status']=='AUTHORIZED_METADATA_RECORDED'
    assert result['playback_verified'] is False
    assert result['readiness_score'] is None
    assert result['latest_highlights'][0]['can_link'] is True


@pytest.mark.parametrize('rights',['UNKNOWN_RIGHTS','BLOCKED','REVIEW_REQUIRED'])
def test_permission_denials_are_preserved(catalogue,rights):
    add(catalogue,rights=rights)
    assert media.sportsdb_highlights_summary(catalogue)['latest_highlights']==[]
    assert media.sportsdb_highlights_for_match(catalogue,'m1')['highlights']==[]


@pytest.mark.parametrize('kind',['summary','match'])
def test_legacy_optional_tables_not_created(catalogue,kind):
    add(catalogue,rights='LICENSED')
    with closing(sqlite3.connect(catalogue)) as conn:
        conn.execute('DROP TABLE sportsdb_match_enrichment')
        conn.execute('DROP TABLE sportsdb_highlight_runs');conn.commit()
    before=catalogue.read_bytes()
    result=(media.sportsdb_highlights_summary(catalogue) if kind=='summary'
            else media.sportsdb_highlights_for_match(catalogue,'m1'))
    assert catalogue.read_bytes()==before
    assert result['read_state']=='VERIFIED'
    if kind=='summary':
        assert result['enriched_matches'] is None
        assert result['runs_available'] is False
    else: assert result['enrichment_available'] is False


@pytest.mark.parametrize('kind',['summary','match'])
def test_all_connections_close_and_queries_are_read_only(catalogue,monkeypatch,kind):
    add(catalogue,rights='LICENSED');before=catalogue.read_bytes()
    original=sqlite3.connect;connections=[];statements=[]
    def connect(*a,**kw):
        conn=original(*a,**kw);connections.append(conn)
        conn.set_trace_callback(statements.append)
        return conn
    monkeypatch.setattr(sqlite3,'connect',connect)
    result=(media.sportsdb_highlights_summary(catalogue) if kind=='summary'
            else media.sportsdb_highlights_for_match(catalogue,'m1'))
    assert result['ok'] is True
    assert len(connections)==1
    assert not any(s.lstrip().upper().startswith(('CREATE','INSERT','UPDATE','ALTER','DELETE','REPLACE')) for s in statements)
    assert any('query_only' in s.lower() for s in statements)
    assert 'BEGIN' in statements
    for conn in connections:
        with pytest.raises(sqlite3.ProgrammingError): conn.execute('SELECT 1')
    assert catalogue.read_bytes()==before


@pytest.mark.parametrize('kind',['summary','match'])
def test_exclusive_lock_is_not_zero_or_new_schema(catalogue,kind):
    add(catalogue)
    with closing(sqlite3.connect(catalogue)) as lock:
        lock.execute('BEGIN EXCLUSIVE')
        try:
            result=(media.sportsdb_highlights_summary(catalogue) if kind=='summary'
                    else media.sportsdb_highlights_for_match(catalogue,'m1'))
            assert result['read_state']=='READ_UNAVAILABLE'
            assert result['ok'] is False
        finally: lock.rollback()


def test_counts_declare_sample_instead_of_all_catalogue(catalogue):
    for i in range(251):add(catalogue,ident=f'h{i}',match=f'm{i}',rights='LICENSED')
    r=media.sportsdb_highlights_summary(catalogue)
    assert r['stored_media_total']==251
    assert r['sample_limit']==250 and r['sampled_media']==250 and r['sample_truncated'] is True
    assert r['visible_counts_scope']=='LAST_250_STORED_ROWS'
    assert r['authorized_highlights']==250 and len(r['latest_highlights'])==8
    assert r['playback_verified'] is False


@pytest.mark.parametrize('match',[None,'','  '])
def test_missing_identity_does_not_initialize_or_query(tmp_path,match):
    path=tmp_path/'never-created.sqlite'
    r=media.sportsdb_highlights_for_match(path,match)
    assert r['read_state']=='MATCH_ID_MISSING'
    assert not path.exists()


def test_numeric_zero_identity_is_preserved(catalogue):
    add(catalogue,match='0',rights='LICENSED');add(catalogue,ident='other',match='external',rights='LICENSED')
    r=media.sportsdb_highlights_for_match(catalogue,0)
    assert [x['match_id'] for x in r['highlights']]==['0']
    assert r['read_state']=='VERIFIED'


def test_historical_provider_error_is_redacted(catalogue):
    with closing(sqlite3.connect(catalogue)) as conn:
        conn.execute('INSERT INTO sportsdb_highlight_runs(id,started_at,errors) VALUES(?,?,?)',
          ('r1','2026-09-22T20:00:00Z','https://example.invalid/api/SYNTHETIC_PRIVATE_VALUE'))
        conn.commit()
    r=media.sportsdb_highlights_summary(catalogue)
    assert r['recent_runs'] and 'SYNTHETIC_PRIVATE_VALUE' not in json.dumps(r)
