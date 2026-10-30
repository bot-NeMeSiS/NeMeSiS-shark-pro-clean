"""Actual LOCAL SAFE HTTP equivalence; no change to sports/permission builders."""
from contextlib import contextmanager
from copy import deepcopy
import cProfile
import hashlib
import json
import math
import pstats
import sqlite3
import time

from flask import template_rendered
import pytest

from test_shark_functional_flow import prepared_probe as prepared_probe
from test_shark_selected_pick_boundary import shark_probe as shark_probe


@contextmanager
def capture(a):
    contexts=[]
    def receive(sender,template,context,**kwargs):
        contexts.append(deepcopy(context.get('data') or {}))
    template_rendered.connect(receive,a.app,weak=False)
    try:
        yield contexts
    finally:
        template_rendered.disconnect(receive,a.app)


def business_state(path):
    result={}
    with sqlite3.connect(path) as conn:
        names={row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ('matches','picks','combis','shark_memory','shark_context_snapshots'):
            if table in names:
                rows=conn.execute('SELECT * FROM '+table+' ORDER BY rowid').fetchall()
                result[table]=hashlib.sha256(json.dumps(rows,default=str,sort_keys=True).encode()).hexdigest()
    return result


def measured_page(a,client,**kwargs):
    profiler=cProfile.Profile()
    with capture(a) as contexts:
        profiler.enable()
        try:
            response=client.get('/picks',base_url='http://127.0.0.1',**kwargs)
        finally:
            profiler.disable()
    stats=pstats.Stats(profiler).stats
    wanted={'build_sports_metrics_contract','_v991_prepare_summary_operation','_v991_realtime_projection','_v931_minimal_client_data','_picks_client_data'}
    counts={name:sum(value[1] for key,value in stats.items() if key[2]==name) for name in wanted}
    assert contexts and response.status_code==200
    return response,contexts[-1],counts


def differing_leaves(left,right,path=''):
    if type(left) is not type(right):
        return [path+':TYPE']
    if isinstance(left,dict):
        return [item for key in left.keys()|right.keys() for item in (
            differing_leaves(left[key],right[key],path+'.'+str(key))
            if key in left and key in right else [path+'.'+str(key)+':MISSING'])]
    if isinstance(left,list):
        if len(left)!=len(right):return [path+':LENGTH']
        return [item for index,(a,b) in enumerate(zip(left,right)) for item in differing_leaves(a,b,path+'['+str(index)+']')]
    return [] if left==right else [path]


def assert_same_with_elapsed_age(left,right,max_elapsed):
    """Observation clocks/statuses remain exact; only evaluation age may grow."""
    assert type(left) is type(right)
    if isinstance(left,dict):
        assert left.keys()==right.keys()
        for key in left:
            if key=='age_seconds' and left[key]!=right[key]:
                assert type(left[key]) in (int,float) and type(right[key]) in (int,float)
                assert 0<=right[key]-left[key]<=max_elapsed
            else:
                assert_same_with_elapsed_age(left[key],right[key],max_elapsed)
    elif isinstance(left,list):
        assert len(left)==len(right)
        for a,b in zip(left,right):assert_same_with_elapsed_age(a,b,max_elapsed)
    else:
        assert left==right


@pytest.mark.parametrize('principal',('ANONYMOUS','FREE','PRO','ELITE'))
def test_picks_display_and_authorization_equal_original_with_less_recomputation(prepared_probe,monkeypatch,principal):
    probe=prepared_probe;a=probe['a']
    client=a.app.test_client() if principal=='ANONYMOUS' else probe['login'](principal)[0]
    # Warm only the owned fixture's actual normal source cache, never inject a
    # summary, identity result, principal, timestamp or membership predicate.
    warm=client.get('/picks',base_url='http://127.0.0.1')
    assert warm.status_code==200
    before=business_state(probe['path'])
    compared_at=time.perf_counter()
    candidate,data,calls=measured_page(a,client)
    if principal=='ELITE':
        time.sleep(1.1)  # Real elapsed time, to expose only evaluation metadata.
    actual=a.v932_safe_dashboard_data
    def previous_path(*args,**kwargs):
        kwargs.pop('_picks_view',None)
        return actual(*args,**kwargs)
    with monkeypatch.context() as control:
        control.setattr(a,'v932_safe_dashboard_data',previous_path)
        original,prior,old_calls=measured_page(a,client)
    max_elapsed=math.ceil(time.perf_counter()-compared_at)+1
    assert candidate.get_data()==original.get_data()
    for key in ('picks','locked_pick_count','pick_stats','v925_picks','v925_odds','pick_readiness','pick_watchlist'):
        if data[key]!=prior[key]:
            print('PICKS_CONTEXT_DIFFERENCES '+json.dumps({'key':key,'paths':differing_leaves(data[key],prior[key])}))
        assert_same_with_elapsed_age(data[key],prior[key],max_elapsed)
    for key in ('matches_today','matches_available','live_confirmed','picks_ready','matches_with_picks','finished_verified','incomplete_excluded','stale_live_excluded','snapshot_id'):
        assert data['sports_metrics'][key]==prior['sports_metrics'][key]
    assert calls['_picks_client_data']==1 and calls['_v931_minimal_client_data']==0
    assert old_calls['_v931_minimal_client_data']==1
    assert calls['build_sports_metrics_contract']<old_calls['build_sports_metrics_contract']
    assert calls['_v991_prepare_summary_operation']==old_calls['_v991_prepare_summary_operation']==1
    assert calls['_v991_realtime_projection']==old_calls['_v991_realtime_projection']==1
    html=candidate.get_data(as_text=True)
    assert probe['draft_canary'] not in html
    if principal in ('ANONYMOUS','FREE','PRO'):
        assert probe['published_canary'] not in html
    assert business_state(probe['path'])==before
    print('PICKS_EQUIVALENCE '+json.dumps({'principal':principal,'html_byte_equal':True,'business_tables_unchanged':True,'candidate_calls':calls,'original_calls':old_calls}))


@pytest.mark.parametrize('principal',('ANONYMOUS','ELITE'))
def test_picks_existing_locked_read_guard_is_preserved(prepared_probe,monkeypatch,principal):
    probe=prepared_probe;a=probe['a']
    client=a.app.test_client() if principal=='ANONYMOUS' else probe['login'](principal)[0]
    # Keep the actual diagnostic writers/content active. Only their filesystem
    # root is bound synchronously to this owned fixture, never the source tree.
    # No access/route/DB/freshness function is replaced by this adapter.
    for name in ('v931_record_client_route_issue','v932_record_authenticated_issue'):
        writer=getattr(a,name)
        def isolated_writer(*args,_writer=writer,**kwargs):
            with monkeypatch.context() as owned:
                owned.setattr(a,'BASE_DIR',probe['path'].parent)
                return _writer(*args,**kwargs)
        monkeypatch.setattr(a,name,isolated_writer)
    fault={'environ_overrides':{'nemesis.v932.database_locked':True}}
    candidate,data,_=measured_page(a,client,**fault)
    actual=a.v932_safe_dashboard_data
    def previous_path(*args,**kwargs):
        kwargs.pop('_picks_view',None)
        return actual(*args,**kwargs)
    with monkeypatch.context() as control:
        control.setattr(a,'v932_safe_dashboard_data',previous_path)
        original,prior,_=measured_page(a,client,**fault)
    assert candidate.get_data()==original.get_data()
    assert data['pick_readiness']==prior['pick_readiness']
    assert data['sports_metrics']['scope']==prior['sports_metrics']['scope']=='unprepared_observations'
    assert data['sports_metrics']['matches_available']==0
    assert data['pick_watchlist']==[]
    issue_path=probe['path'].parent/'data/runtime/sentinel_client_route_issues.json'
    issues=json.loads(issue_path.read_text(encoding='utf-8'))['issues']
    assert any(row['route']=='/picks' and row['count']==2 for row in issues)
