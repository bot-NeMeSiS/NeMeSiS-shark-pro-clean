"""LOCAL SAFE comparisons for omitted source Home derivations, current-main control."""
import cProfile
import json
import math
import pstats
import time
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import re
import html
from pathlib import Path
import os
import ast
import subprocess
import sys
import xml.etree.ElementTree as ET
import pytest
from test_picks_read_path_efficiency import (
    capture, business_state, assert_same_with_elapsed_age, _owned_supervisor,
    prepared_probe, shark_probe, differing_leaves,
)

def measured(a, client, route):
    profiler=cProfile.Profile()
    with capture(a) as contexts:
        started=datetime.now(timezone.utc)
        profiler.enable()
        try:
            response=client.get(route,base_url='http://127.0.0.1')
        finally:
            profiler.disable()
        ended=datetime.now(timezone.utc)
    stats=pstats.Stats(profiler).stats
    wanted=('build_sports_home_sections','build_sports_metrics_contract',
            '_v991_prepare_summary_operation','_v991_realtime_projection')
    calls={name:sum(v[1] for k,v in stats.items() if k[2]==name) for name in wanted}
    assert response.status_code==200 and contexts
    return response,contexts[-1],calls,(started,ended)

def same_age(a,b,elapsed):
    assert type(a) is type(b)
    if a==b:return
    assert type(a) in (int,float) and type(b) in (int,float)
    assert 0<=b-a<=elapsed

def same_evaluation(a,b,windows):
    for value,window in zip((a,b),windows):
        parsed=datetime.fromisoformat(value)
        assert parsed.tzinfo is not None
        # Whole-second clocks have up to one second of representational loss.
        assert window[0]-timedelta(seconds=1)<=parsed<=window[1]
    assert 0<=(datetime.fromisoformat(b)-datetime.fromisoformat(a)).total_seconds()<=math.ceil((windows[1][1]-windows[0][0]).total_seconds())+1

def same_state(a,b,windows,elapsed):
    if a is None or b is None:
        assert a==b
        return a,b
    assert a.keys()==b.keys() and a['contract']==b['contract']=='NEMESIS-REALTIME-STATE-V1'
    left,right=deepcopy(a),deepcopy(b)
    if 'evaluated_at_madrid' in a:
        same_evaluation(a['evaluated_at_madrid'],b['evaluated_at_madrid'],windows)
        left.pop('evaluated_at_madrid');right.pop('evaluated_at_madrid')
    if 'freshness_seconds' in a:
        same_age(a['freshness_seconds'],b['freshness_seconds'],elapsed)
        left.pop('freshness_seconds');right.pop('freshness_seconds')
    assert not differing_leaves(left,right)  # Own clocks, leases, identity, score and state stay exact.
    return left,right

def same_realtime(a,b,windows,elapsed):
    left,right=deepcopy(a),deepcopy(b)
    for lane in ('matches','live'):
        assert len(left.get(lane) or [])==len(right.get(lane) or [])
        for l,r in zip(left.get(lane) or [],right.get(lane) or []):
            l['realtime_state'],r['realtime_state']=same_state(l.get('realtime_state'),r.get('realtime_state'),windows,elapsed)
            if 'age_seconds' in l:
                same_age(l['age_seconds'],r['age_seconds'],elapsed)
                l.pop('age_seconds');r.pop('age_seconds')
            lt,rt=l.get('status_truth') or {},r.get('status_truth') or {}
            if 'live_age_seconds' in lt:
                same_age(lt['live_age_seconds'],rt['live_age_seconds'],elapsed)
                lt.pop('live_age_seconds');rt.pop('live_age_seconds')
    assert len(left.get('picks') or [])==len(right.get('picks') or [])
    for l,r in zip(left.get('picks') or [],right.get('picks') or []):
        lf,rf=l.get('odds_freshness') or {},r.get('odds_freshness') or {}
        if 'age_seconds' in lf:
            same_age(lf['age_seconds'],rf['age_seconds'],elapsed)
            lf.pop('age_seconds');rf.pop('age_seconds')
    if left.get('generated_at_madrid')!=right.get('generated_at_madrid'):
        same_evaluation(left['generated_at_madrid'],right['generated_at_madrid'],windows)
        left.pop('generated_at_madrid');right.pop('generated_at_madrid')
    assert not differing_leaves(left,right)

def same_bootstrap_html(candidate,original,data,prior,windows,elapsed):
    pattern=r'(<script type="application/json" data-directo-fixture-identity>)(.*?)(</script>)'
    left,right=candidate.get_data(as_text=True),original.get_data(as_text=True)
    lm,rm=list(re.finditer(pattern,left)),list(re.finditer(pattern,right))
    assert len(lm)==len(rm)==1
    lb,rb=json.loads(lm[0].group(2)),json.loads(rm[0].group(2))
    assert lb==data['live_experience']['fixture_bootstrap']
    assert rb==prior['live_experience']['fixture_bootstrap']
    assert len(lb['matches'])==len(rb['matches'])
    for l,r in zip(lb['matches'],rb['matches']):
        l['realtime_state'],r['realtime_state']=same_state(l.get('realtime_state'),r.get('realtime_state'),windows,elapsed)
    if lb['generated_at_madrid']!=rb['generated_at_madrid']:
        same_evaluation(lb['generated_at_madrid'],rb['generated_at_madrid'],windows)
        lb.pop('generated_at_madrid');rb.pop('generated_at_madrid')
    assert not differing_leaves(lb,rb)
    ls=re.findall(r'data-realtime-state="([^"]*)"',left)
    rs=re.findall(r'data-realtime-state="([^"]*)"',right)
    assert len(ls)==len(rs)>0
    lstate,rstate=[json.loads(html.unescape(s)) for s in ls],[json.loads(html.unescape(s)) for s in rs]
    for states,captured in ((lstate,data),(rstate,prior)):
        expected=[m['realtime_state'] for m in captured['live_experience']['matches']
                  if (m.get('realtime_state') or {}).get('contract')=='NEMESIS-REALTIME-STATE-V1']
        assert states==expected  # Emitted attributes must bind to the actual originals.
    for l,r in zip(lstate,rstate):same_state(l,r,windows,elapsed)
    for html_text,states,captured in ((left,lstate,data),(right,rstate,prior)):
        assert re.findall(r'data-realtime-evaluated-at="([^"]*)"',html_text)==[s['evaluated_at_madrid'] for s in states]
        assert re.findall(r'data-directo-evaluated-at="([^"]*)"',html_text)==[captured['v934_realtime']['generated_at_madrid']]
    if data['v934_realtime']['generated_at_madrid']!=prior['v934_realtime']['generated_at_madrid']:
        same_evaluation(data['v934_realtime']['generated_at_madrid'],prior['v934_realtime']['generated_at_madrid'],windows)
    def markup(text):
        text=re.sub(pattern,r'\1__CHECKED_BOOTSTRAP__\3',text)
        text=re.sub(r'(data-realtime-state=")[^"]*(")',r'\1__CHECKED_OWN_STATE__\2',text)
        text=re.sub(r'(data-realtime-evaluated-at=")[^"]*(")',r'\1__CHECKED_EVALUATION__\2',text)
        return re.sub(r'(data-directo-evaluated-at=")[^"]*(")',r'\1__CHECKED_GENERATION__\2',text)
    # Every substituted JSON payload/attribute has already been checked above.
    # All remaining markup, own clocks, prices, scores, labels and links are exact.
    assert markup(left)==markup(right)

def same_assistant(a,b,windows,elapsed):
    left,right=deepcopy(a),deepcopy(b)
    seen_left,seen_right=set(),set()
    for path in (('context',),('answer','context')):
        l,r=left,right
        for key in path:l,r=l[key],r[key]
        assert (id(l) in seen_left)==(id(r) in seen_right)
        if id(l) in seen_left:continue
        seen_left.add(id(l));seen_right.add(id(r))
        lv,rv=l['collections']['live'],r['collections']['live']
        assert len(lv['matches'])==len(rv['matches'])
        for lm,rm in zip(lv['matches'],rv['matches']):
            lm['realtime_state'],rm['realtime_state']=same_state(lm['realtime_state'],rm['realtime_state'],windows,elapsed)
        if lv['generated_at_madrid']!=rv['generated_at_madrid']:
            same_evaluation(lv['generated_at_madrid'],rv['generated_at_madrid'],windows)
            lv.pop('generated_at_madrid');rv.pop('generated_at_madrid')
        same_evaluation(l['briefing']['time'],r['briefing']['time'],windows)
        l['briefing'].pop('time');r['briefing'].pop('time')
    assert not differing_leaves(left,right)

if _owned_supervisor:
    @pytest.mark.parametrize('route',('/picks','/directo','/shark'))
    @pytest.mark.parametrize('principal',('ANONYMOUS','FREE','PRO','ELITE'))
    def test_source_prepare_view_equals_current_main(prepared_probe,monkeypatch,route,principal):
        probe=prepared_probe;a=probe['a']
        client=a.app.test_client() if principal=='ANONYMOUS' else probe['login'](principal)[0]
        assert client.get(route,base_url='http://127.0.0.1').status_code==200
        before=business_state(probe['path']);started=time.perf_counter()
        candidate,data,calls,window=measured(a,client,route)
        real=a.get_public_home_sports_summary
        def current_main_source(*args,**kwargs):
            kwargs.pop('_prepare_only',None)
            kwargs.pop('_home_only',None)
            return real(*args,**kwargs)
        with monkeypatch.context() as control:
            control.setattr(a,'get_public_home_sports_summary',current_main_source)
            original,prior,old_calls,old_window=measured(a,client,route)
        elapsed=math.ceil(time.perf_counter()-started)+1
        windows=(window,old_window)
        # Check the entire public metric contract, including sports_quality,
        # definitions and identity coverage; chosen KPI fields alone are insufficient.
        metric_left,metric_right=deepcopy(data['sports_metrics']),deepcopy(prior['sports_metrics'])
        if metric_left['generated_at_madrid']!=metric_right['generated_at_madrid']:
            same_evaluation(metric_left['generated_at_madrid'],metric_right['generated_at_madrid'],windows)
            metric_left.pop('generated_at_madrid');metric_right.pop('generated_at_madrid')
        assert not differing_leaves(metric_left,metric_right)
        if route=='/directo':same_bootstrap_html(candidate,original,data,prior,windows,elapsed)
        else:assert candidate.get_data()==original.get_data()
        for name in ('matches_today','matches_available','live_confirmed','picks_ready',
                     'matches_with_picks','finished_verified','incomplete_excluded',
                     'stale_live_excluded','snapshot_id'):
            assert data['sports_metrics'][name]==prior['sports_metrics'][name]
        if route in ('/picks','/directo'):
            same_realtime(data['v934_realtime'],prior['v934_realtime'],windows,elapsed)
            original_state=data['v934_realtime']['live'][0]['realtime_state']
        else:
            same_assistant(data['shark_assistant'],prior['shark_assistant'],windows,elapsed)
            original_state=data['shark_assistant']['context']['collections']['live']['matches'][0]['realtime_state']
        for protected in ('provider_observed_at','live_valid_until_madrid','score_home','fixture_id'):
            changed=deepcopy(original_state);changed[protected]='MUTATED_QA_OWN_EVIDENCE'
            with pytest.raises(AssertionError):same_state(original_state,changed,(window,window),elapsed)
        # All three views retain Home-derived quality; omit only unused metrics.
        assert calls['build_sports_home_sections']==old_calls['build_sports_home_sections']==1
        assert calls['build_sports_metrics_contract']<old_calls['build_sports_metrics_contract']
        assert calls['_v991_prepare_summary_operation']==old_calls['_v991_prepare_summary_operation']==1
        assert calls['_v991_realtime_projection']==old_calls['_v991_realtime_projection']
        assert business_state(probe['path'])==before
        assert probe['draft_canary'] not in candidate.get_data(as_text=True)
        print('PREPARE_VIEW_EQUIVALENCE '+json.dumps({'route':route,'principal':principal,
              'HTML_byte_equal':candidate.get_data()==original.get_data(),
              'HTML_equal_except_checked_evaluation':True,
              'business_unchanged':True,'candidate':calls,'main':old_calls}))

    @pytest.mark.parametrize('route',('/directo','/shark'))
    def test_current_main_repeat_has_only_bounded_evaluation_drift(prepared_probe,monkeypatch,route):
        probe=prepared_probe;a=probe['a'];client=probe['login']('ELITE')[0]
        source=a.get_public_home_sports_summary
        def main_source(*args,**kwargs):
            kwargs.pop('_prepare_only',None)
            kwargs.pop('_home_only',None)
            return source(*args,**kwargs)
        monkeypatch.setattr(a,'get_public_home_sports_summary',main_source)
        assert client.get(route,base_url='http://127.0.0.1').status_code==200
        before=business_state(probe['path']);started=time.perf_counter()
        first,data,calls,window=measured(a,client,route)
        time.sleep(1.1)  # Baseline against itself, using the real clock.
        second,prior,other,old_window=measured(a,client,route)
        windows=(window,old_window);elapsed=math.ceil(time.perf_counter()-started)+1
        assert calls==other and calls['build_sports_home_sections']==1
        if route=='/directo':
            same_bootstrap_html(first,second,data,prior,windows,elapsed)
            same_realtime(data['v934_realtime'],prior['v934_realtime'],windows,elapsed)
        else:
            assert first.get_data()==second.get_data()
            same_assistant(data['shark_assistant'],prior['shark_assistant'],windows,elapsed)
        assert business_state(probe['path'])==before
        print('BASELINE_REPEAT_EVALUATION '+json.dumps({'route':route,'real_sleep_seconds':1.1,'business_unchanged':True}))
else:
    def test_summary_views_in_original_guarded_process(tmp_path):
        root=Path(__file__).resolve().parents[1]
        runner=root/'tools/check_local_candidate.py'
        bootstrap=('import platform,runpy,sys;platform.uname();platform.platform();'
            "sys.argv=[sys.argv[1],sys.argv[2],'-s','--tb=short'];"
            "runpy.run_path(sys.argv[0],run_name='__main__')")
        env=dict(os.environ,PYTEST_ADDOPTS='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
        r=subprocess.run([sys.executable,'-B','-c',bootstrap,str(runner),str(Path(__file__).resolve())],
            cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
            encoding='utf-8',errors='replace',timeout=180)
        (tmp_path/'guarded.stdout.txt').write_text(r.stdout,encoding='utf-8')
        (tmp_path/'guarded.stderr.txt').write_text(r.stderr,encoding='utf-8')
        assert r.returncode==0,(r.stdout[-14000:],r.stderr[-2000:])
        paths=[line.removeprefix('QA_OUTPUT ') for line in r.stdout.splitlines() if line.startswith('QA_OUTPUT ')]
        boundaries=[line.removeprefix('BOUNDARY_EVENTS ') for line in r.stdout.splitlines() if line.startswith('BOUNDARY_EVENTS ')]
        assert len(paths)==len(boundaries)==1 and ast.literal_eval(boundaries[0])==[]
        output=Path(paths[0]).resolve()
        assert output.is_relative_to((root/'data/local_dev').resolve()) and output.name.startswith('candidate-')
        suite=ET.parse(output/'result.xml').find('testsuite')
        assert suite is not None and suite.attrib['tests']=='14'
        assert all(suite.attrib[k]=='0' for k in ('failures','errors','skipped'))
        print('PREPARE_VIEWS_STANDARD_PROOF '+json.dumps({'cases':14,'boundary':[],'output':str(output)}))
