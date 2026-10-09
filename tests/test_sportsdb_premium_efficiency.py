"""Real code, fake transports, temporary stores; never calls paid providers."""
import ast
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sqlite3
import urllib.error

import pytest

from engines.sportsdb_request_budget import SportsDBBudget, SportsDBStopped, request_timeout, fetch_feed
from engines import sportsdb_highlights_engine as media
from engines.postmatch_sources import OfficialSources
from engines.postmatch_store import Store
from engines.postmatch_recovery import tick

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError('Unexpected live network')
    monkeypatch.setattr('urllib.request.urlopen', no_network)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', no_network)
    monkeypatch.setenv('THESPORTSDB_KEY', 'test-key-not-production')


def load_app_function(name, **namespace):
    tree = ast.parse((ROOT/'app.py').read_bytes().decode())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'app.py', 'exec'), namespace)
    return namespace[name]


def test_timeout_outside_scope_unchanged():
    assert request_timeout(12) == 12


def test_nested_context_restores_timeout_after_exception():
    outer = SportsDBBudget(clock=lambda: 100, max_seconds=18)
    with outer:
        assert request_timeout() == 4
        with pytest.raises(ValueError):
            with SportsDBBudget(clock=lambda: 100, max_seconds=1):
                assert request_timeout() == 1
                raise ValueError('test')
        assert request_timeout() == 4
    assert request_timeout() == 12


def test_duplicate_query_uses_copy_without_another_call():
    scope = SportsDBBudget()
    calls=[]
    def fetch():
        calls.append(True)
        return {'events':[{'id':'one'}]}
    with scope:
        first=scope.call(1, 'eventsday.php', {'d':'today'}, fetch)
        first['events'][0]['id']='changed'
        assert scope.call(1, 'eventsday.php', {'d':'today'}, fetch)['events'][0]['id']=='one'
    assert len(calls)==1 and scope.calls==1 and scope.cache_hits==1


def test_cache_does_not_cross_operations():
    calls=[]
    for _ in range(2):
        with SportsDBBudget() as scope:
            scope.call(1,'eventsday.php',{},lambda:(calls.append(True) or {'events':None}))
    assert len(calls)==2


def test_request_budget_hard_count_even_with_empty_responses():
    scope=SportsDBBudget(max_calls=2)
    with scope, pytest.raises(SportsDBStopped,match='REQUEST_BUDGET'):
        for i in range(99):
            scope.call(1,'eventsday.php',{'d':str(i)},lambda:{'events':None})
    assert scope.calls==2


def test_deadline_checks_before_network_and_caps_transport():
    now=[100.]
    with SportsDBBudget(max_seconds=5,clock=lambda:now[0]) as scope:
        now[0]=104.5
        assert request_timeout(12)==.5
        now[0]=105
        with pytest.raises(SportsDBStopped,match='TIME_BUDGET'):
            scope.call(1,'x',{},lambda:pytest.fail('transport called past deadline'))
        assert scope.calls==0


@pytest.mark.parametrize('code,reason',[(401,'ACCESS_DENIED'),(403,'ACCESS_DENIED'),(429,'RATE_LIMIT'),(503,'NETWORK')])
def test_errors_stop_fanout_without_leaking_key(code,reason):
    scope=SportsDBBudget()
    def fail():
        raise urllib.error.HTTPError('https://host/SECRET-KEY/',code,'private provider response',{},None)
    with scope:
        for _ in range(2):
            with pytest.raises(SportsDBStopped,match=reason) as exc:
                scope.call(1,'x',{},fail)
            assert 'SECRET' not in str(exc.value)
    assert scope.calls==1


@pytest.mark.parametrize('payload',[[],None,{'error':'SECRET-KEY'},{'errors':{'private':'credential'}}])
def test_invalid_payload_does_not_become_success(payload):
    with SportsDBBudget() as scope, pytest.raises(SportsDBStopped):
        scope.call(1,'x',{},lambda:payload)
    assert scope.calls==1


def test_feed_acquires_live_before_fanout_but_returns_live_last():
    calls=[]
    def v1(ep,params):
        calls.append(ep)
        return {'events':[{'strLeague':'league','status':'old'}]}
    def v2(ep):
        calls.append(ep)
        return {'events':[{'strLeague':'league','status':'live'}]}
    result,errors,count=fetch_feed(v1=v1,v2=v2,today='2026-10-01',leagues=[{'id':str(x)} for x in range(50)],
        live_enabled=True,limit=100,prioritize=lambda rows,**kw:rows,slug=str,
        collect=lambda p:p['events'],budget=SportsDBBudget(max_calls=4))
    assert calls[:2]==['eventsday.php','livescore/soccer']
    assert result[-1][0]['status']=='live'
    assert errors==['REQUEST_BUDGET'] and count==4


def test_feed_application_delegation_missing_key_never_calls_provider():
    fn=load_app_function('fetch_sportsdb_feed_events',thesportsdb_key=lambda:'')
    assert fn()==([],['MISSING_KEY'],0)


def test_application_wrappers_use_context_timeout(monkeypatch):
    import urllib.parse
    observed=[]
    for name in ('sportsdb_v1','sportsdb_v2'):
        fn=load_app_function(name,thesportsdb_key=lambda:'test',urllib=__import__('urllib'),
                             fetch_json_url=lambda *a,**k:(observed.append(k['timeout']) or {}))
        with SportsDBBudget(max_seconds=2):
            fn('eventsday.php' if name.endswith('v1') else 'livescore/soccer')
    assert len(observed)==2 and all(0 < t <= 2 for t in observed)


@pytest.fixture
def db(tmp_path):
    path=tmp_path/'sports.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE matches (id TEXT PRIMARY KEY, external_id TEXT, home_team TEXT, away_team TEXT, match_date TEXT, kickoff_time TEXT, competition_name TEXT, league_name TEXT, league_id TEXT, source TEXT, status TEXT, score TEXT)')
        conn.execute("INSERT INTO matches VALUES ('match-one','sportsdb-1','Home','Away','2026-10-01','21:00','League','League','4328','TheSportsDB','FT','2-0')")
    return path


def event(i=1, league='4328'):
    return {'idEvent':str(i),'strHomeTeam':'Home','strAwayTeam':'Away',
            'dateEvent':'2026-10-01','strLeague':'League','idLeague':league,
            'strStatus':'Match Finished','strVideo':'https://www.youtube.com/watch?v=abcdefghijk'}


def test_missing_key_does_not_create_store(tmp_path,monkeypatch):
    monkeypatch.setattr(media,'_api_key',lambda:'')
    path=tmp_path/'absent.sqlite'
    result=media.sync_sportsdb_highlights(path)
    assert not path.exists() and result['external_calls']==0 and result['ok'] is False


def test_collection_has_no_write_lock_during_transport(db,monkeypatch):
    def fetch(*args):
        with sqlite3.connect(db,timeout=.05) as conn:
            conn.execute('BEGIN IMMEDIATE');conn.rollback()
        return {'events':[event()]}
    monkeypatch.setattr(media,'_sportsdb_v1',fetch)
    result=media.sync_sportsdb_highlights(db,days_back=0)
    assert result['ok'] and result['highlights_found']==1 and result['external_calls']==1
    with sqlite3.connect(db) as conn:
        row=conn.execute('SELECT status,rights_status FROM sportsdb_match_highlights').fetchone()
    assert row==('REVIEW_REQUIRED','UNKNOWN_RIGHTS')
    assert result['playback_verified'] is False


def test_capped_feed_partitions_without_duplicate_rows(db,monkeypatch):
    calls=[]
    def fetch(ep,params):
        calls.append(dict(params))
        return {'events':[event(x) for x in range(1,51)] if 'l' not in params else [event(1),event(51)]}
    monkeypatch.setattr(media,'_sportsdb_v1',fetch)
    result=media.sync_sportsdb_highlights(db,days_back=0)
    assert result['highlights_found']==51 and result['league_partitions']==1
    assert calls==[{'d':media._today().isoformat(),'s':'Soccer'},{'d':media._today().isoformat(),'s':'Soccer','l':'4328'}]
    assert result['status']=='PARTIAL' and not result['ok'] and not result['retryable']
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sportsdb_match_highlights').fetchone()[0]==51


def test_date_coverage_precedes_optional_partitioning(db,monkeypatch):
    calls=[]
    def fetch(ep,params):
        calls.append(params)
        return {'events':[event(x) for x in range(1,51)] if 'l' not in params else []}
    monkeypatch.setattr(media,'_sportsdb_v1',fetch)
    media.sync_sportsdb_highlights(db,days_back=2)
    assert all('l' not in row for row in calls[:3])


def test_limit_commits_actual_rows_and_reports_partial(db,monkeypatch):
    monkeypatch.setattr(media,'_sportsdb_v1',lambda *a:{'events':[event(x) for x in range(1,10)]})
    result=media.sync_sportsdb_highlights(db,days_back=0,limit=3)
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sportsdb_match_highlights').fetchone()[0]==3
    assert result['highlights_found']==3 and result['status']=='PARTIAL' and 'ITEM_BUDGET' in result['errors']


def test_http_failure_is_failed_and_never_contains_provider_exception(db,monkeypatch):
    def fail(*a):
        raise urllib.error.HTTPError('https://secret/KEY',429,'SECRET message',{},None)
    monkeypatch.setattr(media,'_sportsdb_v1',fail)
    result=media.sync_sportsdb_highlights(db,days_back=7)
    assert result['external_calls']==1 and result['status']=='FAILED' and not result['ok']
    assert result['retryable'] is True and result['errors']==['RATE_LIMIT']
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT errors FROM sportsdb_highlight_runs').fetchone()[0]=='RATE_LIMIT'


@pytest.mark.parametrize('payload',[{}, {'error':'secret'}, {'events':'not a list'}, {'events':[None]}])
def test_malformed_highlight_response_not_empty_success(db,monkeypatch,payload):
    monkeypatch.setattr(media,'_sportsdb_v1',lambda *a:payload)
    result=media.sync_sportsdb_highlights(db,days_back=0)
    assert result['ok'] is False and result['status']=='FAILED'


def test_pending_rights_is_not_reported_as_provider_has_no_video(db,monkeypatch):
    monkeypatch.setattr(media,'_sportsdb_v1',lambda *a:{'events':[event()]})
    media.sync_sportsdb_highlights(db,days_back=0)
    with sqlite3.connect(db) as conn:
        summary=conn.execute('SELECT summary_text FROM sportsdb_match_enrichment').fetchone()[0]
    assert 'publicación pendiente' in summary and 'sin resumen disponible' not in summary


def test_failed_daily_sync_retries_after_cooldown_not_next_day():
    called=[]
    fn=load_app_function('v766_sync_highlights_daily',now_iso=lambda:'now',today_iso=lambda:'2026-10-01',
        automation_get=lambda *a:{'date':'2026-10-01','ok':False,'errors':['NETWORK'],'attempt_finished_epoch':1},
        sync_sportsdb_highlights=lambda *a,**k:(called.append(True) or {'ok':True}),DB_PATH='test',
        automation_set=lambda *a:None)
    assert fn()['ok'] is True and called==[True]


def test_completed_scoped_collection_is_not_repolled_every_tick():
    fn=load_app_function('v766_sync_highlights_daily',now_iso=lambda:'now',today_iso=lambda:'2026-10-01',
        automation_get=lambda *a:{'date':'2026-10-01','ok':False,'errors':['SCOPED_COVERAGE_ONLY'],'retryable':False})
    assert fn()['reason']=='scope_completed_with_gaps'


def test_successful_daily_sync_still_skips():
    fn=load_app_function('v766_sync_highlights_daily',now_iso=lambda:'now',today_iso=lambda:'2026-10-01',
        automation_get=lambda *a:{'date':'2026-10-01','days_back':7,'ok':True,'status':'OK','errors':[]})
    assert fn()['reason']=='already_synced_today'


def test_discovery_uses_utc_day_for_madrid_midnight(db,monkeypatch):
    match={'id':'match-one','external_id':'api-football-88','source':'API-Football',
           'home_team':'Home','away_team':'Away','match_date':'2026-10-02','kickoff_time':'00:30',
           'competition_name':'League','league_name':'League'}
    provider_event={**event(),'dateEvent':'2026-10-01','strTimestamp':'2026-10-01T22:30:00Z','idAPIfootball':'88'}
    store=Store(db)
    source=OfficialSources(store,{}, {'sources':['thesportsdb']},deadline=1000,clock=lambda:0)
    calls=[]
    monkeypatch.setattr(source,'request',lambda p,e,params:(calls.append(params) or {'events':[provider_event]}))
    assert source.sportsdb_event(match)['idEvent']=='1'
    assert calls==[{'d':'2026-10-01','s':'Soccer'}]
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE matches SET external_id='api-football-88',source='API-Football',match_date='2026-10-02',kickoff_time='00:30' WHERE id='match-one'")
        conn.row_factory=sqlite3.Row
        assert media._find_match(conn,provider_event)=='match-one'


def test_cross_provider_association_rejects_missing_competition(db):
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        conn.execute("UPDATE matches SET external_id='api-football-88',source='API-Football'")
        item=event();item.pop('strLeague')
        assert media._find_match(conn,item) is None


def test_empty_link_in_daily_feed_does_not_hide_later_league_video(db,monkeypatch):
    def fetch(ep,params):
        return {'events':[event()] if 'l' in params else [{**event(),'strVideo':''}] + [event(i) for i in range(2,51)]}
    monkeypatch.setattr(media,'_sportsdb_v1',fetch)
    result=media.sync_sportsdb_highlights(db,days_back=0)
    assert result['highlights_found']==50


def test_collector_never_uses_other_providers_numeric_league_ids(db,monkeypatch):
    calls=[]
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE matches SET source='API-Football',league_id='99999'")
    def fetch(ep,params):
        calls.append(params)
        return {'events':[event(i) for i in range(1,51)] if 'l' not in params else []}
    monkeypatch.setattr(media,'_sportsdb_v1',fetch)
    media.sync_sportsdb_highlights(db,days_back=0)
    assert all(row.get('l')!='99999' for row in calls)


def test_collector_never_exceeds_twelve_requests(db,monkeypatch):
    calls=[]
    def fetch(ep,params):
        calls.append(params)
        return {'events':[event(i,league=str(4300+i)) for i in range(1,51)] if 'l' not in params else []}
    monkeypatch.setattr(media,'_sportsdb_v1',fetch)
    result=media.sync_sportsdb_highlights(db,days_back=7)
    assert result['external_calls']==len(calls)==12
    assert all('l' not in row for row in calls[:8])
    assert result['retryable'] is False and 'PARTITION_BUDGET' in result['errors']


def test_timeout_never_exposes_raw_exception(db,monkeypatch):
    def fail(*a):
        raise TimeoutError('SECRET/API/KEY')
    monkeypatch.setattr(media,'_sportsdb_v1',fail)
    result=media.sync_sportsdb_highlights(db,days_back=0)
    assert result['errors']==['NETWORK'] and result['external_calls']==1


@pytest.mark.parametrize('age_days', [0, 8, 100])
def test_null_events_is_valid_empty_not_coverage_certificate(db,monkeypatch,age_days):
    # A fixed date silently moves a fixture into historical reconciliation.
    # Exercise both paths offline: an empty feed is valid, but a historical
    # event absent from the identity response must remain pending (NO_EVENT).
    day = (datetime.now(timezone.utc) - timedelta(days=age_days)).date().isoformat()
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE matches SET match_date=?', (day,))
    monkeypatch.setattr(media,'_sportsdb_v1',lambda *a:{'events':None})
    monkeypatch.setattr(media,'_sportsdb_v2',lambda *a:{'lookup':None})
    result=media.sync_sportsdb_highlights(db,days_back=0)
    assert result['highlights_found'] == 0
    assert result['status'] == ('OK' if age_days == 0 else 'PARTIAL'), result['errors']
    assert result['ok'] is (age_days == 0)
    assert result['errors'] == ([] if age_days == 0 else ['NO_EVENT'])
    assert result['provider_coverage_complete'] is False


def test_recent_failure_cooldown_avoids_hammering():
    import time
    fn=load_app_function('v766_sync_highlights_daily',now_iso=lambda:'now',today_iso=lambda:'2026-10-01',
        automation_get=lambda *a:{'date':'2026-10-01','ok':False,'errors':['NETWORK'],'attempt_finished_epoch':time.time()})
    assert fn()['reason']=='retry_cooldown'


def test_force_keeps_the_call_budget(db,monkeypatch):
    calls=[]
    event_calls=[]
    monkeypatch.setattr(media,'_sportsdb_v1',lambda *a:(calls.append(True) or {'events':None}))
    monkeypatch.setattr(media,'_sportsdb_v2',lambda *a:(event_calls.append(True) or {'lookup':[]}))
    result=media.sync_sportsdb_highlights(db,days_back=14,force=True)
    assert result['external_calls']==12 and len(calls)+len(event_calls)==12 and 'REQUEST_BUDGET' in result['errors']
    assert len(event_calls)==1  # The force flag cannot consume the budget before precise event recovery.


def test_shared_postmatch_cache_is_bound_to_credential(monkeypatch):
    class FakeStore:
        reserves=0
        def reserve(self,*a): self.reserves+=1
        def circuit(self,*a): pass
        def cached_request(self,*a): return None
        def cache_request(self,*a): pass
    store=FakeStore();calls=[]
    source=OfficialSources(store,{'identity':'test-match'}, {'sources':['thesportsdb'],'daily_limit':60},deadline=1000,clock=lambda:0,
        transport=lambda *a:(calls.append(True) or {'events':[event()]}))
    first=source.request('thesportsdb','lookupevent.php',{'id':'1'})
    first['events'][0]['strHomeTeam']='modified'
    assert source.request('thesportsdb','lookupevent.php',{'id':'1'})['events'][0]['strHomeTeam']=='Home'
    monkeypatch.setenv('THESPORTSDB_KEY','different-test-key')
    source.request('thesportsdb','lookupevent.php',{'id':'1'})
    assert source.calls==len(calls)==store.reserves==2
