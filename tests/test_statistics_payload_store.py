"""Lossless migration and ordinary ingestion, SQLite and synthetic data only."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
import zlib

import pytest

from engines import statistics_payload_store as store
from engines import api_football_statistics_engine as stats
from engines import api_exploitation_engine as deep
from engines import match_record_archive as archive


def payload(team=10):
    return {'team': {'id': team, 'name': 'Equipo sintético Águila'},
            'statistics': [{'type': f'Metric {n}', 'value': None if n == 1 else n} for n in range(20)],
            'provider_unknown_field': {'verbatim': '  conservar todo\n' * 30}}


def raw(team=10):
    return json.dumps(payload(team), ensure_ascii=False, indent=2)


@pytest.fixture
def db(tmp_path):
    with closing(sqlite3.connect(tmp_path/'owned.sqlite')) as conn:
        conn.execute('''CREATE TABLE api_football_match_stats_history(
            id TEXT PRIMARY KEY,fixture_id TEXT,team_id TEXT,team_name TEXT,
            stat_name TEXT,stat_value TEXT,numeric_value REAL,payload_json TEXT,captured_at TEXT)''')
        for i in range(20):
            conn.execute('INSERT INTO api_football_match_stats_history VALUES(?,?,?,?,?,?,?,?,?)',
                         (str(i),str(200+i//5),str(10+i//10),'Águila','Metric '+str(i),
                          '' if i == 1 else str(i),None if i == 1 else i,raw(10+i//10),
                          '2026-10-29T21:00:00+00:00'))
        conn.commit()
        yield conn


def hydrate_all(db):
    rows=db.execute('SELECT rowid,* FROM api_football_match_stats_history ORDER BY rowid').fetchall()
    return [(*r[:8],store.read_payload(db,r[8]),r[9]) for r in rows]


def prepare(db):
    db.execute('BEGIN');store.ensure_schema(db)


def test_legacy_read_never_initializes_schema_or_transaction(db):
    before=db.execute('SELECT name FROM sqlite_master ORDER BY name').fetchall()
    assert store.read_payload(db,raw())==raw()
    assert store.read_payload(db,None) is None
    assert not db.in_transaction
    assert db.execute('SELECT name FROM sqlite_master ORDER BY name').fetchall()==before


def test_exact_unicode_serialization_deduplicates_independent_of_metric_rows(db):
    prepare(db)
    first=store.store_payload(db,raw())
    assert first!=raw() and store.read_payload(db,first).encode()==raw().encode()
    assert store.store_payload(db,raw())==first
    assert db.execute(f'SELECT COUNT(*) FROM {store.TABLE}').fetchone()[0]==1
    assert db.in_transaction


def test_different_team_payloads_never_share_a_reference(db):
    prepare(db)
    a,b=store.store_payload(db,raw(10)),store.store_payload(db,raw(20))
    assert a!=b and store.read_payload(db,b)==raw(20)


@pytest.mark.parametrize('text',['{}','x'*(store.MAX_RAW+1)],ids=['small','oversized'])
def test_size_boundaries_preserve_original_without_truncation(db,text):
    prepare(db)
    assert store.store_payload(db,text)==text
    assert db.execute(f'SELECT COUNT(*) FROM {store.TABLE}').fetchone()[0]==0


def test_provider_reserved_field_is_not_confused_with_storage_reference(db):
    prepare(db)
    original=json.dumps({store.MARKER:'provider supplied value',**payload()},ensure_ascii=False)
    ref=store.store_payload(db,original)
    assert store.read_payload(db,ref)==original


@pytest.mark.parametrize('method',[store.ensure_schema,lambda conn:store.store_payload(conn,raw()),store.rewrite_history_batch])
def test_callers_keep_control_of_transactions(db,method):
    with pytest.raises(store.PayloadStorageError,match='CALLER_TRANSACTION_REQUIRED'):method(db)
    assert not db.in_transaction


def test_forward_reverse_migration_preserves_every_value_rowid_and_timestamp(db):
    original=hydrate_all(db);prepare(db)
    result=store.rewrite_history_batch(db,limit=20)
    assert result['changed']==20 and result['scanned']==20 and result['last_rowid']==20
    assert hydrate_all(db)==original
    assert db.execute(f'SELECT COUNT(*) FROM {store.TABLE}').fetchone()[0]==2
    assert store.rewrite_history_batch(db,limit=20)['changed']==0
    assert store.rewrite_history_batch(db,limit=20,reverse=True)['changed']==20
    assert db.execute('SELECT rowid,* FROM api_football_match_stats_history ORDER BY rowid').fetchall()==original
    assert db.execute(f'SELECT COUNT(*) FROM {store.TABLE}').fetchone()[0]==2


def test_outer_rollback_keeps_original_rows_and_removes_new_schema(db):
    original=hydrate_all(db);prepare(db)
    store.rewrite_history_batch(db,limit=20);db.rollback()
    assert hydrate_all(db)==original
    assert not db.execute("SELECT 1 FROM sqlite_master WHERE name=?",(store.TABLE,)).fetchone()


def test_failed_batch_rolls_back_its_references_and_blobs_but_not_prior_work(db):
    original=hydrate_all(db)
    db.execute("CREATE TRIGGER stop_update BEFORE UPDATE ON api_football_match_stats_history WHEN OLD.id='3' BEGIN SELECT RAISE(ABORT,'SYNTHETIC FAILURE'); END")
    db.commit();prepare(db)
    db.execute("CREATE TABLE owned_outer_work(id INTEGER)");db.execute('INSERT INTO owned_outer_work VALUES(5)')
    with pytest.raises(sqlite3.IntegrityError):store.rewrite_history_batch(db,limit=20)
    assert hydrate_all(db)==original
    assert db.execute(f'SELECT COUNT(*) FROM {store.TABLE}').fetchone()[0]==0
    assert db.execute('SELECT id FROM owned_outer_work').fetchone()==(5,)


def test_budget_exhaustion_mid_batch_is_atomic(db,monkeypatch):
    original=hydrate_all(db);prepare(db)
    ticks=iter([0,0,0,2])
    monkeypatch.setattr(store.time,'monotonic',lambda:next(ticks))
    with pytest.raises(store.PayloadStorageError,match='MIGRATION_BUDGET_EXHAUSTED'):
        store.rewrite_history_batch(db,limit=20,deadline=1)
    assert hydrate_all(db)==original
    assert db.execute(f'SELECT COUNT(*) FROM {store.TABLE}').fetchone()[0]==0


@pytest.mark.parametrize('bounds',[{'limit':True},{'limit':1001},{'after_rowid':-1},{'after_rowid':True},{'reverse':'false'}])
def test_invalid_batch_never_changes_schema_or_history(db,bounds):
    db.execute('BEGIN')
    with pytest.raises(store.PayloadStorageError,match='INVALID_BATCH_BOUNDS'):store.rewrite_history_batch(db,**bounds)
    assert not db.execute("SELECT 1 FROM sqlite_master WHERE name=?",(store.TABLE,)).fetchone()


@pytest.mark.parametrize('corruption',['digest','size','trailing','truncated','bomb','missing'])
def test_corrupt_or_missing_reference_fails_explicitly_without_repair(db,corruption):
    prepare(db);ref=store.store_payload(db,raw());parsed=json.loads(ref)
    if corruption=='missing':db.execute(f'DELETE FROM {store.TABLE}')
    elif corruption=='digest':
        data=raw(99).encode();db.execute(f'UPDATE {store.TABLE} SET payload_z=?,raw_bytes=?',(zlib.compress(data),len(data)))
    elif corruption=='size':parsed['bytes']+=1;ref=json.dumps(parsed)
    elif corruption=='trailing':
        blob=db.execute(f'SELECT payload_z FROM {store.TABLE}').fetchone()[0]
        db.execute(f'UPDATE {store.TABLE} SET payload_z=?',(blob+b'EXTRA',))
    elif corruption=='truncated':
        blob=db.execute(f'SELECT payload_z FROM {store.TABLE}').fetchone()[0]
        db.execute(f'UPDATE {store.TABLE} SET payload_z=?',(blob[:-3],))
    else:db.execute(f'UPDATE {store.TABLE} SET payload_z=?',(zlib.compress(b'x'*(store.MAX_RAW+1)),))
    with pytest.raises(store.PayloadStorageError):store.read_payload(db,ref)


def test_reference_is_readable_after_reopen_in_readonly_mode(db):
    path=db.execute('PRAGMA database_list').fetchone()[2];prepare(db)
    ref=store.store_payload(db,raw());db.commit()
    with closing(sqlite3.connect('file:'+path.replace('\\','/')+'?mode=ro',uri=True)) as readonly:
        assert store.read_payload(readonly,'  '+ref)==raw()
        assert not readonly.in_transaction


def test_sports_history_consumes_original_payload_instead_of_storage_references(db):
    from engines import sports_history_engine as history
    history.ensure_schema(db)
    match=history.ingest_match(db,{'provider':'api_football','external_id':'200','internal_match_id':'af-200',
        'league_id':'4335','league_name':'LaLiga','season':'2026-2027','home_team_id':'10','away_team_id':'20',
        'home_team':'Norte','away_team':'Sur','kickoff_iso':'2026-10-29T19:00:00Z','status':'FT','home_score':0,'away_score':1})
    db.commit();prepare(db);store.rewrite_history_batch(db,limit=20)
    response=history.sync_existing_details(db)
    assert response['processed']==5
    details=db.execute("SELECT payload FROM sports_history_details WHERE match_id=? AND kind='statistics'",(match,)).fetchall()
    assert len(details)==5
    for text, in details:
        row=json.loads(text)
        assert row['payload_json']==raw(10)
        assert row['captured_at']=='2026-10-29T21:00:00+00:00'
    assert db.execute('SELECT payload_json FROM api_football_match_stats_history LIMIT 1').fetchone()[0].startswith(store.PREFIX)


@pytest.mark.parametrize('writer',['statistics','deep'])
def test_real_ingestion_keeps_full_payload_even_when_observation_archive_is_full(tmp_path,monkeypatch,writer):
    path=tmp_path/'ingestion.sqlite'
    monkeypatch.setattr(archive,'MAX_ARCHIVE_BYTES',0)
    body=[payload(10),payload(20)]
    with closing(sqlite3.connect(path)) as conn:
        stats._ensure_schema(conn);conn.commit()
        if writer=='statistics':
            count=stats._persist(conn,'12345',body,datetime(2026,10,29,tzinfo=timezone.utc))
        else:
            monkeypatch.setattr(deep,'_api_get',lambda *a,**kw:{'ok':True,'response':body})
            count,err,_=deep._sync_statistics(conn,'12345');assert err is None
        assert count==40
        assert conn.execute('SELECT COUNT(*) FROM match_record_observations').fetchone()[0]==0
        assert conn.execute(f'SELECT COUNT(*) FROM {store.TABLE}').fetchone()[0]==2
        rows=conn.execute('SELECT team_id,stat_name,stat_value,numeric_value,payload_json FROM api_football_match_stats_history').fetchall()
        assert len(rows)==40
        for team,name,value,number,text in rows:
            assert json.loads(store.read_payload(conn,text))==payload(int(team))
            index=int(name.split()[-1]);assert value==('' if index==1 else str(index))
        assert conn.in_transaction
