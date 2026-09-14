"""Isolated tests of real functions, without importing/starting the Flask app.

AST extraction avoids startup, DB creation and external effects. It does NOT
claim Flask/authentication/deployment coverage. Existing smoke remains required.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import io
import json
import time
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

from engines.sportsdb_fetch_budget_engine import (
    SportsDBBudgetExhausted, SportsDBFetchBudget, SportsDBResponseTooLarge, fallback_budget,
)

ROOT = Path(__file__).resolve().parents[1]
APP_AST = ast.parse((ROOT / 'app.py').read_text(encoding='utf-8'))


def functions(*names, **extra):
    nodes = [n for n in APP_AST.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    assert len(nodes) == len(names)
    namespace = dict(json=json, time=time, hashlib=hashlib, urllib=urllib,
                     SportsDBBudgetExhausted=SportsDBBudgetExhausted,
                     fallback_budget=fallback_budget)
    namespace.update(extra)
    for n in nodes:
        n = ast.FunctionDef(name=n.name, args=n.args, body=n.body, decorator_list=[], returns=n.returns, type_comment=n.type_comment)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[n], type_ignores=[])), 'app.py', 'exec'), namespace)
    return namespace


class Clock:
    def __init__(self): self.value = 0.0
    def __call__(self): return self.value
    def advance(self, seconds): self.value += seconds


class Response(io.BytesIO):
    def __init__(self, payload=b'{"events": []}', clock=None, delay=0):
        super().__init__(payload)
        self.clock, self.delay = clock, delay
    def read1(self, n=-1):
        if self.clock: self.clock.advance(self.delay)
        return super().read(n)


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    import socket
    def blocked(*args, **kwargs): raise AssertionError('External network forbidden in ops QA')
    monkeypatch.setattr(socket.socket, 'connect', blocked)
    monkeypatch.setattr(socket, 'getaddrinfo', blocked)


@pytest.mark.parametrize('kwargs', [dict(seconds=-1),dict(seconds=float('nan')),dict(seconds=float('inf')),dict(per_request_seconds=0),dict(max_response_bytes=0)])
def test_rejects_invalid_budget(kwargs):
    with pytest.raises(ValueError): SportsDBFetchBudget(**kwargs)


def test_expired_budget_never_opens_transport():
    b = SportsDBFetchBudget(seconds=0)
    with pytest.raises(SportsDBBudgetExhausted):
        b.read_json('unused', opener=lambda *a,**k: pytest.fail('must not call'))
    assert b.requests_started == 0 and b.exhausted


def test_timeout_clamped_to_remainder_and_response_closed():
    c=Clock(); b=SportsDBFetchBudget(seconds=1, clock=c); c.advance(.6)
    r=Response(b'{"score": [0, null], "team": "Betis"}'); observed=[]
    def opener(req,timeout): observed.append(timeout); return r
    assert b.read_json('unused',opener=opener)['score'] == [0,None]
    assert observed[0] == pytest.approx(.4)
    assert r.closed and b.responses_completed == 1


def test_slow_body_stops_at_deadline_and_closes():
    c=Clock(); b=SportsDBFetchBudget(seconds=1,clock=c)
    r=Response(clock=c,delay=.6)
    with pytest.raises(SportsDBBudgetExhausted): b.read_json('unused',opener=lambda *a,**k:r)
    assert r.closed and b.responses_completed==0 and b.requests_started==1


def test_oversized_body_is_rejected():
    b=SportsDBFetchBudget(max_response_bytes=8)
    r=Response(b'{"unbounded":"body"}')
    with pytest.raises(SportsDBResponseTooLarge): b.read_json('unused',opener=lambda *a,**k:r)
    assert r.closed


def test_malformed_response_is_not_counted_completed():
    b=SportsDBFetchBudget(); r=Response(b'not json')
    with pytest.raises(json.JSONDecodeError): b.read_json('unused',opener=lambda *a,**k:r)
    assert b.responses_completed==0 and r.closed


@pytest.mark.parametrize('elapsed,expected',[(0,8),(8,6),(13,1),(14,0),(30,0)])
def test_fallback_respects_prior_cycle_work(elapsed, expected):
    c=Clock(); c.advance(elapsed)
    assert fallback_budget(0,clock=c).seconds==expected


def feed_functions(**extra):
    defaults=dict(today_iso=lambda:'2026-09-14', slug=lambda x:x,
                  SPORTSDB_FEED_LEAGUES=[{'id':str(i),'name':f'League{i}'} for i in range(5)],
                  sportsdb_live_enabled=lambda:True,save_thesportsdb_error=lambda e:None)
    defaults.update(extra)
    return functions('fetch_sportsdb_feed_events','sportsdb_event_collection',**defaults)


def test_deferred_batch_preserves_completed_events_and_skips_remaining():
    c=Clock(); b=SportsDBFetchBudget(seconds=1,clock=c); calls=[]
    def v1(path,params,budget):
        budget.request_timeout(); calls.append(path); c.advance(.6)
        return {'events':[{'idEvent':str(len(calls)),'strLeague':'League'}]}
    f=feed_functions(sportsdb_v1=v1, sportsdb_v2=lambda *a,**k:pytest.fail('live must not be called'))
    events,errors=f['fetch_sportsdb_feed_events'](budget=b)
    assert len(events)==2 and len(calls)==2
    assert errors==['SPORTSDB_TIME_BUDGET_EXHAUSTED']


def test_healthy_unbudgeted_call_contract_unchanged():
    calls=[]
    def v1(path,params): calls.append(path); return {'events':[]}
    f=feed_functions(sportsdb_v1=v1,sportsdb_v2=lambda path:{'events':[]})
    assert f['fetch_sportsdb_feed_events']()==([],[])
    assert len(calls)==6


def test_no_new_request_when_batch_limit_met():
    f=feed_functions(sportsdb_v1=lambda *a,**k:{'events':[{'idEvent':'1'}]},sportsdb_live_enabled=lambda:False)
    result,errors=f['fetch_sportsdb_feed_events'](limit=1)
    assert len(result)==1 and not errors


def test_empty_deferred_fetch_never_calls_upsert_or_changes_match_store():
    b=SportsDBFetchBudget(seconds=0); b.exhausted=True; logs=[]
    f=functions('sync_sportsdb_feed', seed_core=lambda:None,thesportsdb_key=lambda:'test',
                sync_log_start=lambda *a:1,sync_log_finish=lambda *a:logs.append(a),
                fetch_sportsdb_feed_events=lambda **k:([],['SPORTSDB_TIME_BUDGET_EXHAUSTED']),
                upsert_sportsdb_matches=lambda *a:pytest.fail('empty deferred fetch must not touch matches'),
                save_thesportsdb_error=lambda *a:pytest.fail('not a provider authentication error'))
    result=f['sync_sportsdb_feed'](budget=b)
    assert result['ok'] is False and result['status']=='PARTIAL'
    assert result['external_calls']==0 and logs[0][1]=='PARTIAL'


def test_v1_and_v2_use_budget_and_no_extra_transport(monkeypatch):
    requests=[]
    class Budget:
        def read_json(self,req): requests.append(req); return {'ok':True}
    f=functions('sportsdb_v1','sportsdb_v2',thesportsdb_key=lambda:'qa-key',fetch_json_url=lambda *a,**k:pytest.fail('unbounded transport used'))
    assert f['sportsdb_v1']('eventsday.php',{'d':'2026-09-14'},budget=Budget())=={'ok':True}
    assert f['sportsdb_v2']('livescore/soccer',budget=Budget())=={'ok':True}
    assert len(requests)==2 and requests[1].get_header('X-api-key')=='qa-key'


def test_missing_key_does_not_call_budget():
    class Budget:
        def read_json(self,*a): pytest.fail('must not call')
    f=functions('sportsdb_v1','sportsdb_v2',thesportsdb_key=lambda:'')
    assert f['sportsdb_v1']('anything',budget=Budget())=={}
    assert f['sportsdb_v2']('anything',budget=Budget())=={}


def test_health_function_is_light_and_does_not_initialize():
    f=functions('health',jsonify=lambda p:p,APP_NAME='test',APP_VERSION='test',
                now_iso=lambda:'test-time',APP_INITIALIZED=False,DB_PATH='/qa/nonexistent.db')
    result=f['health']()
    assert result['ok'] is True and result['initialized'] is False
    assert 'db_path' not in result
    # Function-level contract only: not HTTP readiness or auth certification.
    node=next(n for n in APP_AST.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='LIGHT_STARTUP_ENDPOINTS' for t in n.targets))
    assert 'health' in ast.literal_eval(node.value)


def diagnostic_functions():
    return functions('_build_sports_pipeline_diagnostics',
      _sports_diagnostic_text=lambda x,limit=120:str(x or '')[:limit],
      as_int=lambda x,d=0:int(x) if x not in [None,''] else d)


def test_missing_fixture_is_not_mislabelled_as_timer_not_due():
    f=diagnostic_functions()
    result=f['_build_sports_pipeline_diagnostics']({'deep_status':'SKIPPED_NO_API_FOOTBALL_FIXTURE'})
    assert result['deep_execution']['state']=='NO_ELIGIBLE_FIXTURE'
    assert result['deep_execution']['status']=='SKIPPED_NO_API_FOOTBALL_FIXTURE'
    assert result['data_freshness']['state']=='NOT_ESTABLISHED'


def test_historical_access_is_not_current_authentication():
    f=diagnostic_functions()
    history={'latest_run':{'finished_at':'2026-09-10T22:20:23+00:00','payload_json':json.dumps({'account':{'ok':False,'configured':True,'quota':{'daily_remaining':99}}})}}
    result=f['_build_sports_pipeline_diagnostics']({'deep_status':'SKIPPED_NOT_DUE'},history)
    assert result['provider_access']['current_state']=='NOT_CHECKED'
    assert result['provider_access']['is_current_observation'] is False
    assert result['data_freshness']['entity_timestamps_evaluated'] is False


def test_master_allowlist_preserves_budget_but_drops_arbitrary_secrets():
    spec=importlib.util.spec_from_file_location('ops_master_test',ROOT/'tools/render_cron_master_tick.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    payload={'sports_pipeline':{'fallback_execution':{'status':'PARTIAL','external_calls':3,
         'budget':{'elapsed_ms':8010,'requests_started':3,'responses_completed':1,'budget_exhausted':True,'secret':'do-not-log'}},
         'provider_access':{'current_state':'NOT_CHECKED','is_current_observation':False}}}
    result=m.sanitized_sports_pipeline(payload,'do-not-log')
    assert 'do-not-log' not in json.dumps(result)
    assert result['fallback_execution']['budget']['budget_exhausted'] is True
    assert result['provider_access']['current_state']=='NOT_CHECKED'


def test_scheduler_passes_budget_only_to_fallback_and_reports_partial():
    seen=[]
    def fallback(**kwargs):
        seen.append(kwargs)
        return {'ok':True,'status':'PARTIAL','processed':2,'external_calls':3,
                'errors':['SPORTSDB_TIME_BUDGET_EXHAUSTED']}
    f=functions('_safe_sports_sync_call','run_sports_sync_cycle',
      now_iso=lambda:'2026-09-14T18:00:00+02:00',DB_PATH='not-used',
      sports_sync_window_state=lambda:{'live_refresh_required':False},
      has_request_context=lambda:False,
      sync_api_football_match_window=lambda *a,**k:{'ok':False,'status':'ERROR','external_calls':1},
      sync_sportsdb_calendar=fallback,
      _api_football_deep_enrichment_candidates=lambda limit:[],
      run_api_exploitation_if_due=lambda *a,**k:{'ok':True,'status':'SKIPPED_NO_API_FOOTBALL_FIXTURE','external_calls':0},
      sync_odds_events=lambda **k:{'ok':True,'skipped':True},
      run_pick_grading=lambda *a,**k:{'ok':True},
      invalidate_v934_realtime_cache=lambda *a:None,
      automation_safe_set=lambda *a:None,masked_admin_text=lambda v,n:v,
      as_int=lambda v,d=0:int(v) if v not in (None,'') else d)
    result=f['run_sports_sync_cycle']()
    assert isinstance(seen[0]['budget'],SportsDBFetchBudget)
    assert seen[0]['budget'].seconds<=8 and seen[0]['limit']==180
    assert result['status']=='PARTIAL'
    assert result['external_calls']==4
    assert 'fallback_PARTIAL' in result['errors']


def test_sportsdb_healthy_legacy_transport_timeout_unchanged():
    calls=[]
    f=functions('sportsdb_v1','sportsdb_v2',thesportsdb_key=lambda:'qa-key',
                fetch_json_url=lambda *a,**k:calls.append(k) or {'events':[]})
    f['sportsdb_v1']('eventsday.php');f['sportsdb_v2']('livescore/soccer')
    assert all(c['timeout']==12 for c in calls)


def test_budgets_do_not_share_state_or_extend_each_other():
    c=Clock(); first=SportsDBFetchBudget(seconds=1,clock=c)
    c.advance(.5);second=SportsDBFetchBudget(seconds=2,clock=c)
    c.advance(.6)
    with pytest.raises(SportsDBBudgetExhausted): first.request_timeout()
    assert second.request_timeout()==pytest.approx(1.4)
    assert second.requests_started==0 and not second.exhausted
