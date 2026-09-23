"""Synthetic fixtures only. Every external connection is blocked by this module."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import zlib

import pytest
from engines import match_record_archive as archive
from engines import api_football_live_tracker_engine as live
from engines import api_exploitation_engine as deep
from tools.inspect_match_record_archive import inspect_archive

T0='2026-09-22T18:00:00+00:00'
T1='2026-09-22T18:01:00+00:00'
T2='2026-09-22T19:00:00+00:00'

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*a,**kw):
        raise AssertionError('External network forbidden in archive regressions')
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(socket,'create_connection',deny)


def fixture_payload(**values):
    result={'fixture':{'id':123,'date':'2026-09-22T17:30:00+00:00','referee':'Árbitro SIMULATED_QA',
      'venue':{'id':5,'name':'Estadio SIMULATED_QA','city':'Ciudad de prueba'},'attendance':12345,
      'status':{'short':'1H','long':'First Half','elapsed':30}},
      'league':{'id':1,'name':'Liga SIMULATED_QA','country':'Spain','season':2026,'round':'7'},
      'teams':{'home':{'id':10,'name':'Norte QA'},'away':{'id':20,'name':'Sur QA'}},
      'goals':{'home':0,'away':0},'score':{'halftime':{'home':None,'away':None}}}
    result.update(values);return result


def stats(possession='55%',corners=0):
    return [{'team':{'id':10,'name':'Norte QA'},'statistics':[
      {'type':'Ball Possession','value':possession},{'type':'Corner Kicks','value':corners},
      {'type':'Yellow Cards','value':0},{'type':'Throw-ins','value':None}]},
      {'team':{'id':20,'name':'Sur QA'},'statistics':[{'type':'Ball Possession','value':'45%'},
      {'type':'Red Cards','value':0},{'type':'Throw-ins','value':8}]}]


def events(assist='Asistente QA'):
    return [{'time':{'elapsed':30,'extra':None},'team':{'id':10,'name':'Norte QA'},
      'player':{'id':9,'name':'Goleador QA'},'assist':{'id':8,'name':assist},
      'type':'Goal','detail':'Normal Goal','comments':None}]


@pytest.fixture
def db(tmp_path):
    path=str(tmp_path/'synthetic.db')
    live.ensure_live_tracker_schema(path)
    deep.ensure_api_exploitation_schema(path)
    columns='id external_id sport_key match_date kickoff_time match_time kickoff_iso competition_id competition_key competition_name league_name country home_team away_team home_team_id away_team_id home_logo away_logo status minute score home_score away_score venue season round priority source legal_note raw_json sync_status last_synced_at updated_at'.split()
    with closing(sqlite3.connect(path)) as conn:
        conn.execute('CREATE TABLE matches('+','.join(n+' TEXT'+(' PRIMARY KEY' if n=='id' else '') for n in columns)+')')
        conn.commit()
    return path


def read_all(db,section):
    with closing(sqlite3.connect(db)) as conn:
        conn.row_factory=sqlite3.Row
        rows=conn.execute('SELECT * FROM match_record_observations WHERE section=? ORDER BY received_at,id',(section,)).fetchall()
        return [archive.decode_observation(row) for row in rows]


def test_ingested_live_stats_preserve_old_values_nulls_zeros_and_restart(db,monkeypatch):
    for stamp,payload in [(T0,stats()),(T1,stats('57%',1)),(T2,stats(None,0))]:
        monkeypatch.setattr(live,'utc_stamp',lambda:archive.utc_stamp(stamp))
        with closing(sqlite3.connect(db)) as conn:
            with conn:live._upsert_statistics(conn,'123',payload)
    rows=read_all(db,'statistics')
    assert len(rows)==3
    assert [row['payload'][0]['statistics'][0]['value'] for row in rows]==['55%','57%',None]
    assert rows[0]['payload'][0]['statistics'][1]['value']==0
    result=inspect_archive(db,'123',as_of=T1,include_payload=True)
    assert result['sections']['statistics']['payload']==stats('57%',1)
    assert result['observations']==2


def test_event_corrections_and_empty_response_survive_old_cache_insert_ignore(db,monkeypatch):
    for stamp,payload in [(T0,events()),(T1,events('Corrección QA')),(T2,[])]:
        monkeypatch.setattr(live,'utc_stamp',lambda:archive.utc_stamp(stamp))
        with closing(sqlite3.connect(db)) as conn:
            with conn:live.persist_api_football_events(conn,'123',payload)
    rows=read_all(db,'events')
    assert len(rows)==3 and rows[-1]['payload']==[]
    assert rows[1]['payload'][0]['assist']['name']=='Corrección QA'
    current=inspect_archive(db,'123',include_payload=True)
    assert current['sections']['events']['state']=='EMPTY_RECEIVED'
    assert current['sections']['events']['payload']==[]
    before=inspect_archive(db,'123',as_of=T0,include_payload=True)
    assert before['sections']['events']['payload']==events()


def test_fixture_metadata_and_embedded_sections_are_kept_without_extra_calls(db,monkeypatch):
    monkeypatch.setattr(live,'utc_stamp',lambda:archive.utc_stamp(T0))
    item=fixture_payload(statistics=stats(),events=events(),lineups=[],players=[])
    with closing(sqlite3.connect(db)) as conn:
        with conn:assert live._upsert_fixture(conn,item)==1
    row=read_all(db,'fixture')[0]
    assert row['payload']==item
    assert row['context']['status_at_receipt']=='1H'
    assert row['context']['elapsed']==30
    assert row['payload']['fixture']['attendance']==12345
    assert row['payload']['fixture']['referee']=='Árbitro SIMULATED_QA'
    for section in ('statistics','events','lineups','players'):
        assert len(read_all(db,section))==1
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute('SELECT id,home_score,away_score FROM matches').fetchone()==('af-123','0','0')


def test_deep_statistics_zero_is_not_lost_and_archive_receives_same_response(db,monkeypatch):
    monkeypatch.setattr(deep,'_api_get',lambda *a,**kw:{'ok':True,'response':stats()})
    with closing(sqlite3.connect(db)) as conn:
        with conn:count,error,trace=deep._sync_statistics(conn,'123')
        assert error is None and count==7 and trace['persisted']==7
        assert conn.execute("SELECT stat_value FROM api_football_match_stats_history WHERE stat_name='Corner Kicks'").fetchone()[0]=='0'
        assert conn.execute("SELECT stat_value FROM api_football_match_stats_history WHERE stat_name='Throw-ins' AND team_id='10'").fetchone()[0]==''
    assert read_all(db,'statistics')[0]['payload']==stats()


def test_deep_lineups_full_formation_coach_bench_preserved(db,monkeypatch):
    rows=[{'team':{'id':10,'name':'Norte QA'},'formation':'4-4-2','coach':{'id':5,'name':'Entrenador QA'},
           'startXI':[{'player':{'id':9,'name':'Goleador QA','number':0,'pos':'F','grid':'1:1'}}],
           'substitutes':[{'player':{'id':8,'name':'Suplente QA'}}]}]
    monkeypatch.setattr(deep,'_api_get',lambda *a,**kw:{'ok':True,'response':rows})
    with closing(sqlite3.connect(db)) as conn:
        with conn:count,error,trace=deep._sync_lineups(conn,'123')
    assert count==2 and error is None
    assert read_all(db,'lineups')[0]['payload']==rows


@pytest.mark.parametrize('function',[deep._sync_lineups,deep._sync_statistics,deep._sync_events])
def test_failed_response_never_appears_as_empty_success(db,monkeypatch,function):
    monkeypatch.setattr(deep,'_api_get',lambda *a,**kw:{'ok':False,'error':'access denied','response':[]})
    with closing(sqlite3.connect(db)) as conn:
        with conn:count,error,trace=function(conn,'123')
        assert count==0 and error
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='match_record_observations'").fetchone()


@pytest.mark.parametrize('function,section',[(deep._sync_lineups,'lineups'),(deep._sync_statistics,'statistics'),(deep._sync_events,'events')])
def test_empty_success_is_a_distinct_receipt(db,monkeypatch,function,section):
    monkeypatch.setattr(deep,'_api_get',lambda *a,**kw:{'ok':True,'response':[]})
    with closing(sqlite3.connect(db)) as conn:
        with conn:count,error,trace=function(conn,'123')
    assert count==0 and error is None
    assert read_all(db,section)[0]['payload']==[]


@pytest.mark.parametrize('journal',['DELETE','WAL'])
def test_caller_rollback_keeps_cache_archive_and_budget_atomic(db,journal):
    with closing(sqlite3.connect(db)) as conn:
        conn.execute('PRAGMA journal_mode='+journal)
        archive.ensure_match_record_schema(conn);conn.commit()
        live._upsert_statistics(conn,'123',stats())
        assert conn.in_transaction
        conn.rollback()
        assert conn.execute('SELECT COUNT(*) FROM match_record_observations').fetchone()[0]==0
        assert conn.execute('SELECT row_count,byte_count FROM match_record_archive_budget').fetchone()==(0,0)
        assert conn.execute('SELECT COUNT(*) FROM api_football_live_stats').fetchone()[0]==0


def test_archive_insert_error_does_not_leak_budget(db):
    with closing(sqlite3.connect(db)) as conn:
        archive.ensure_match_record_schema(conn)
        conn.execute("CREATE TRIGGER reject_archive BEFORE INSERT ON match_record_observations BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        conn.commit()
        with pytest.raises(sqlite3.Error):
            archive.record_observation(conn,'123','statistics',stats(),received_at=T0)
        assert conn.execute('SELECT row_count,byte_count FROM match_record_archive_budget').fetchone()==(0,0)
        conn.rollback()


def test_schema_setup_never_commits_unrelated_work(db):
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("INSERT INTO matches(id) VALUES('keep-private')")
        archive.ensure_match_record_schema(conn)
        conn.rollback()
        assert not conn.execute("SELECT 1 FROM matches WHERE id='keep-private'").fetchone()
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='match_record_observations'").fetchone()


def test_same_receipt_is_idempotent_but_later_confirmation_is_kept(db):
    with closing(sqlite3.connect(db)) as conn:
        with conn:
            assert archive.record_observation(conn,'123','events',events(),received_at=T0)['stored']
            assert archive.record_observation(conn,'123','events',events(),received_at=T0)['reason']=='DUPLICATE_RECEIPT'
            assert archive.record_observation(conn,'123','events',events(),received_at=T1)['stored']
    assert len(read_all(db,'events'))==2


def test_correction_at_same_receipt_keeps_both_versions(db):
    with closing(sqlite3.connect(db)) as conn:
        with conn:
            archive.record_observation(conn,'123','events',events(),received_at=T0)
            archive.record_observation(conn,'123','events',events('Corregido'),received_at=T0)
    result=inspect_archive(db,'123',as_of=T0,include_payload=True)
    assert result['observations']==2 and result['sections']['events']['payload']==events('Corregido')


@pytest.mark.parametrize('invalid',[None,{'not':'an array'},[1], [True], [{'n':float('nan')}], [{'n':float('inf')}], [{1:'bad-key'}]])
def test_invalid_payload_is_gap_not_invented_zero(db,invalid):
    with closing(sqlite3.connect(db)) as conn:
        with conn:result=archive.record_observation(conn,'123','statistics',invalid,received_at=T0)
        assert not result['stored']
        assert conn.execute('SELECT COUNT(*) FROM match_record_observations').fetchone()[0]==0
        assert conn.execute('SELECT SUM(count) FROM match_record_archive_gaps').fetchone()[0]==1


@pytest.mark.parametrize('invalid',['af-123','sportsdb-123','123 OR 1=1','-1',''])
def test_archive_identity_does_not_accept_aliases(db,invalid):
    with closing(sqlite3.connect(db)) as conn:
        with pytest.raises(ValueError):archive.record_observation(conn,invalid,'statistics',stats())


def test_mismatched_fixture_payload_refused(db):
    with closing(sqlite3.connect(db)) as conn:
        with conn:result=archive.record_observation(conn,'987','fixture',fixture_payload())
    assert result['reason']=='IDENTITY_MISMATCH'


def test_archive_caps_do_not_purge_old_data_or_stop_current_cache(db,monkeypatch):
    monkeypatch.setattr(archive,'MAX_OBSERVATIONS',1)
    with closing(sqlite3.connect(db)) as conn:
        with conn:
            live._upsert_statistics(conn,'123',stats())
            live._upsert_statistics(conn,'123',stats('60%',3))
        assert conn.execute('SELECT COUNT(*) FROM match_record_observations').fetchone()[0]==1
        assert conn.execute("SELECT stat_value FROM api_football_live_stats WHERE stat_name='Corner Kicks'").fetchone()[0]=='3'
        assert conn.execute('SELECT reason,count FROM match_record_archive_gaps').fetchone()==('ARCHIVE_CAP_REACHED',1)


def test_byte_cap_checked_and_gap_keys_bounded(db,monkeypatch):
    monkeypatch.setattr(archive,'MAX_ARCHIVE_BYTES',1);monkeypatch.setattr(archive,'MAX_GAP_KEYS',2)
    with closing(sqlite3.connect(db)) as conn:
        with conn:
            for n in range(100):assert not archive.record_observation(conn,str(n),'statistics',stats())['stored']
        assert conn.execute('SELECT row_count FROM match_record_archive_budget').fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM match_record_archive_gaps').fetchone()[0]==3
        assert conn.execute('SELECT SUM(count) FROM match_record_archive_gaps').fetchone()[0]==100


def test_concurrent_receipts_share_atomic_cap(db,monkeypatch):
    monkeypatch.setattr(archive,'MAX_OBSERVATIONS',5)
    with closing(sqlite3.connect(db)) as conn:
        archive.ensure_match_record_schema(conn);conn.commit()
    def ingest(n):
        with closing(sqlite3.connect(db,timeout=5)) as conn:
            with conn:return archive.record_observation(conn,str(n),'statistics',stats(),received_at=T0)['stored']
    with ThreadPoolExecutor(max_workers=4) as pool:accepted=list(pool.map(ingest,range(16)))
    assert sum(accepted)==5
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute('SELECT row_count FROM match_record_archive_budget').fetchone()[0]==5
        assert conn.execute('SELECT COUNT(*) FROM match_record_observations').fetchone()[0]==5
        assert conn.execute('SELECT SUM(count) FROM match_record_archive_gaps').fetchone()[0]==11


def test_sensitive_keys_removed_not_spread_to_history(db):
    payload=stats();payload[0]['api_key']='not-real';payload[0]['statistics'].append({'type':'QA','value':None,'headers':{'Authorization':'not-real'}})
    with closing(sqlite3.connect(db)) as conn:
        with conn:archive.record_observation(conn,'123','statistics',payload)
    restored=read_all(db,'statistics')[0]['payload']
    assert 'api_key' not in restored[0] and 'headers' not in restored[0]['statistics'][-1]
    assert 'not-real' not in json.dumps(restored)


@pytest.mark.parametrize('oversized',[[{'value':'x'*(archive.MAX_RAW_BYTES+1)}],[{}]*2001])
def test_oversized_input_is_recorded_as_gap(db,oversized):
    with closing(sqlite3.connect(db)) as conn:
        with conn:assert not archive.record_observation(conn,'123','statistics',oversized)['stored']
        assert conn.execute('SELECT SUM(count) FROM match_record_archive_gaps').fetchone()[0]==1


@pytest.mark.parametrize('corruption',['compressed','hash','raw-length','bomb','trailing'])
def test_corrupt_observation_does_not_decode(db,corruption):
    with closing(sqlite3.connect(db)) as conn:
        conn.row_factory=sqlite3.Row
        with conn:archive.record_observation(conn,'123','statistics',stats())
        row=dict(conn.execute('SELECT * FROM match_record_observations').fetchone())
    if corruption=='compressed':row['payload_z']=b'bad'
    if corruption=='hash':row['payload_hash']='f'*64
    if corruption=='raw-length':row['raw_bytes']+=1
    if corruption=='bomb':row['payload_z']=zlib.compress(b'x'*(archive.MAX_RAW_BYTES+1))
    if corruption=='trailing':row['payload_z']+=b'trailing'
    with pytest.raises(archive.ArchivePayloadError):archive.decode_observation(row)


def test_as_of_does_not_read_future_context_or_legacy_data(db):
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("INSERT INTO api_football_live_snapshots(fixture_id,elapsed,last_synced_at) VALUES('123',90,?)",(T2,))
        with conn:archive.record_observation(conn,'123','statistics',stats(),received_at=T0)
    row=read_all(db,'statistics')[0];assert row['context']=={}
    assert inspect_archive(db,'123',as_of='2026-09-22T17:00:00Z')['state']=='NO_OBSERVATIONS_AT_CUTOFF'
    assert inspect_archive(db,'456',include_payload=True)['sections']=={}


def test_inspector_read_only_and_missing_db_not_created(db,tmp_path):
    path=tmp_path/'never.db'
    assert inspect_archive(path,'123')['state']=='DATABASE_NOT_FOUND' and not path.exists()
    before=Path(db).read_bytes();assert inspect_archive(db,'123')['state']=='NOT_INITIALIZED'
    assert Path(db).read_bytes()==before
    with closing(sqlite3.connect(db)) as conn:
        with conn:archive.record_observation(conn,'123','statistics',stats(),received_at=T0)
    before=Path(db).read_bytes();assert inspect_archive(db,'123')['observations']==1
    assert Path(db).read_bytes()==before


def test_inspector_rejects_naive_cutoff(db):
    with pytest.raises(ValueError):inspect_archive(db,'123',as_of='2026-09-22T18:00:00')


@pytest.mark.parametrize('runner',['live','detail','window'])
def test_positive_sync_archives_and_releases_previous_write_before_next_request(db,monkeypatch,runner):
    monkeypatch.setattr(live,'tracker_enabled',lambda:True)
    monkeypatch.setattr(live,'api_key_configured',lambda:True)
    calls=[]
    def fetch(path,params=None,timeout=18):
        # Independent writer must be able to progress during simulated provider I/O.
        with closing(sqlite3.connect(db,timeout=.05)) as other:
            other.execute('BEGIN IMMEDIATE');other.rollback()
        calls.append(path)
        response=[fixture_payload()] if path=='fixtures' else events() if path.endswith('/events') else stats()
        return {'ok':True,'response':response}
    monkeypatch.setattr(live,'_api_get',fetch)
    if runner=='live':result=live.sync_api_football_live_tracker(db,force=True,deep_limit=1)
    elif runner=='detail':result=live.sync_api_football_fixture_detail(db,'af-123',force=True)
    else:result=live.sync_api_football_match_window(db,days_back=0,days_ahead=0,force=True,deep_limit=1)
    assert result['ok'] and len(calls)==3,result
    assert calls==['fixtures','fixtures/events','fixtures/statistics']
    assert len(read_all(db,'fixture'))==len(read_all(db,'events'))==len(read_all(db,'statistics'))==1
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute('SELECT id FROM matches').fetchone()[0]=='af-123'


def test_full_deep_cycle_commits_each_capability_before_next_request(db,monkeypatch):
    with closing(sqlite3.connect(db)) as conn:
        with conn:live._upsert_fixture(conn,fixture_payload())
    monkeypatch.setattr(deep,'_api_football_enabled',lambda:True)
    monkeypatch.setattr(deep,'probe_api_football_account',lambda:{'ok':True,'plan':'QA','quota':{}})
    row={'id':'af-123','external_id':'123','source':'api_football_live','home_team':'Norte QA','away_team':'Sur QA','home_team_id':'10','away_team_id':'20','league_id':'1','season':'2026'}
    monkeypatch.setattr(deep,'_recent_fixture_rows',lambda *a,**kw:[row])
    monkeypatch.setattr(deep,'_build_form_snapshots',lambda *a,**kw:0)
    monkeypatch.setattr(deep,'_snapshot_odds_movements',lambda *a,**kw:0)
    monkeypatch.setattr(deep,'rebuild_api_exploitation_signals',lambda *a,**kw:{})
    monkeypatch.setattr(deep,'rebuild_player_intelligence',lambda *a,**kw:{})
    calls=[]
    def fetch(path,params=None,timeout=18):
        with closing(sqlite3.connect(db,timeout=.05)) as other:
            other.execute('BEGIN IMMEDIATE');other.rollback()
        calls.append(path)
        response=stats() if path.endswith('/statistics') else events() if path.endswith('/events') else []
        return {'ok':True,'response':response}
    monkeypatch.setattr(deep,'_api_get',fetch)
    result=deep.run_api_exploitation_cycle(db,deep_limit=1,max_external_calls=7)
    assert result['status']=='OK',result
    assert len(calls)==6
    assert len(read_all(db,'statistics'))==len(read_all(db,'events'))==len(read_all(db,'lineups'))==1


def test_archive_health_never_claims_complete_coverage_and_reports_caps(db,monkeypatch):
    with closing(sqlite3.connect(db)) as conn:
        assert archive.archive_health(conn)['state']=='NOT_INITIALIZED'
        with conn:archive.record_observation(conn,'123','statistics',stats())
        health=archive.archive_health(conn)
        assert health['observations']==1 and health['coverage_complete'] is False
        monkeypatch.setattr(archive,'MAX_OBSERVATIONS',1)
        with conn:archive.record_observation(conn,'123','statistics',stats('60%',1))
        assert archive.archive_health(conn)['state']=='GAPS_RECORDED'
        assert archive.archive_health(conn)['gap_count']==1


def test_window_keeps_completed_sections_if_later_provider_call_fails(db,monkeypatch):
    monkeypatch.setattr(live,'tracker_enabled',lambda:True)
    monkeypatch.setattr(live,'api_key_configured',lambda:True)
    def fetch(path,params=None,timeout=18):
        if path.endswith('/statistics'):raise RuntimeError('synthetic unavailable')
        return {'ok':True,'response':[fixture_payload()] if path=='fixtures' else events()}
    monkeypatch.setattr(live,'_api_get',fetch)
    result=live.sync_api_football_match_window(db,days_back=0,days_ahead=0,force=True,deep_limit=1)
    assert result['ok'] is False
    assert len(read_all(db,'fixture'))==len(read_all(db,'events'))==1
    assert read_all(db,'statistics')==[]


def test_successful_ingestion_reports_observation_count(db,monkeypatch):
    monkeypatch.setattr(live,'tracker_enabled',lambda:True)
    monkeypatch.setattr(live,'_api_get',lambda path,*a,**kw:{'ok':True,'response':[fixture_payload()] if path=='fixtures' else []})
    result=live.sync_api_football_match_window(db,days_back=0,days_ahead=0,force=True,deep_limit=1)
    assert result['archive']['observations']==3 and result['archive']['coverage_complete'] is False


def test_as_of_receipts_ordered_in_utc_across_madrid_clock_change(db):
    with closing(sqlite3.connect(db)) as conn:
        with conn:
            archive.record_observation(conn,'123','statistics',stats('60%',3),received_at='2026-10-25T02:15:00+01:00')
            archive.record_observation(conn,'123','statistics',stats('55%',2),received_at='2026-10-25T02:30:00+02:00')
    assert read_all(db,'statistics')[0]['payload']==stats('55%',2)
    result=inspect_archive(db,'123',as_of='2026-10-25T00:45:00Z',include_payload=True)
    assert result['sections']['statistics']['payload']==stats('55%',2)


def test_every_requested_stat_stays_verbatim_when_provider_sends_it(db):
    names=['Ball Possession','Fouls','Corner Kicks','Yellow Cards','Red Cards','Throw-ins','Goal Kicks',
           'Free Kicks','Shots on Goal','Shots off Goal','Total Shots','Blocked Shots','Offsides',
           'Goalkeeper Saves','Total passes','Passes accurate','Passes %','expected_goals']
    payload=[{'team':{'id':10,'name':'Norte QA'},'statistics':[{'type':name,'value':idx} for idx,name in enumerate(names)]}]
    with closing(sqlite3.connect(db)) as conn:
        with conn:live._upsert_statistics(conn,'123',payload)
    assert read_all(db,'statistics')[0]['payload']==payload


def test_unknown_provider_clock_is_not_filled_with_receipt(db):
    with closing(sqlite3.connect(db)) as conn:
        with conn:archive.record_observation(conn,'123','statistics',stats(),received_at=T0)
    row=read_all(db,'statistics')[0]
    assert row['received_at']==archive.utc_stamp(T0) and row['context']=={}
    assert 'provider_observed_at' not in row


@pytest.mark.parametrize('module',[live,deep])
@pytest.mark.parametrize('body',[{}, {'response':None}, {'response':{}}, {'response':'not an array'}])
def test_http_success_with_malformed_section_does_not_become_empty_observation(monkeypatch,module,body):
    import io
    import urllib.request
    monkeypatch.setattr(module,'_api_key' if module is live else '_api_football_key',lambda:'synthetic-'+hashlib.sha256(b'not-a-key').hexdigest())
    response=io.BytesIO(json.dumps(body).encode());response.headers={};response.status=200
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**kw:response)
    result=module._api_get('fixtures/statistics',{'fixture':'123'})
    assert result['ok'] is False
    assert result['errors']['response']=='INVALID_RESPONSE_SHAPE'


@pytest.mark.parametrize('module',[live,deep])
def test_explicit_empty_array_from_provider_is_supported(monkeypatch,module):
    import io
    import urllib.request
    monkeypatch.setattr(module,'_api_key' if module is live else '_api_football_key',lambda:'synthetic')
    response=io.BytesIO(b'{"response":[],"errors":[]}');response.headers={};response.status=200
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**kw:response)
    assert module._api_get('fixtures/statistics',{'fixture':'123'})['ok'] is True


def test_account_status_dictionary_shape_is_preserved(monkeypatch):
    import io
    import urllib.request
    monkeypatch.setattr(deep,'_api_football_key',lambda:'synthetic')
    response=io.BytesIO(b'{"response":{"subscription":{"plan":"QA"}},"errors":[]}');response.headers={};response.status=200
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**kw:response)
    result=deep._api_get('status')
    assert result['ok'] and result['response']['subscription']['plan']=='QA'


@pytest.mark.parametrize('field,replacement',[('fixture_id','456'),('section','events'),('received_at',T2),('provider','sportsdb')])
def test_archive_identity_metadata_corruption_detected(db,field,replacement):
    with closing(sqlite3.connect(db)) as conn:
        conn.row_factory=sqlite3.Row
        with conn:archive.record_observation(conn,'123','statistics',stats(),received_at=T0)
        row=dict(conn.execute('SELECT * FROM match_record_observations').fetchone())
    row[field]=replacement
    with pytest.raises(archive.ArchivePayloadError):archive.decode_observation(row)
