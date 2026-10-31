"""Actual guarded SHARK input/read equivalence to the published PR318 baseline."""
import ast
import cProfile
from contextlib import contextmanager
from datetime import datetime,timezone
import hashlib,json,math,pstats,sqlite3,time
from pathlib import Path
import pytest
from copy import deepcopy
from test_client_view_preparation import same_assistant,same_state,same_evaluation
from test_picks_read_path_efficiency import capture,business_state,assert_same_with_elapsed_age,_owned_supervisor,prepared_probe,shark_probe
from shark_input_baseline import BASELINE_SOURCE,BASELINE_SOURCE_SHA256

def baseline(a):
    assert hashlib.sha256(BASELINE_SOURCE.encode('utf-8')).hexdigest()==BASELINE_SOURCE_SHA256
    ns={}
    exec(compile(BASELINE_SOURCE,'<published-main04b-v931>','exec'),a.__dict__,ns)
    return ns['v931_safe_dashboard_data']

def measure(a,client,route,**kwargs):
    p=cProfile.Profile()
    with capture(a) as contexts:
        begin=datetime.now(timezone.utc);p.enable()
        try:r=client.get(route,base_url='http://127.0.0.1',**kwargs)
        finally:p.disable()
        end=datetime.now(timezone.utc)
    stats=pstats.Stats(p).stats
    names=('build_sports_metrics_contract','build_sports_home_sections',
           '_v991_prepare_summary_operation','_v991_realtime_projection','_v931_provider_context')
    calls={n:sum(v[1] for k,v in stats.items() if k[2]==n) for n in names}
    assert r.status_code==200 and contexts
    return r,contexts[-1],calls,(begin,end)

def full_assistant(left,right,windows,elapsed):
    left,right=deepcopy(left),deepcopy(right)
    seen=set()
    for path in (('context',),('answer','context')):
        l,r=left,right
        for key in path:l,r=l[key],r[key]
        identity=(id(l),id(r))
        if identity in seen:continue
        seen.add(identity)
        lm,rm=l.get('match') or {},r.get('match') or {}
        assert ('realtime_state' in lm)==('realtime_state' in rm)
        if 'realtime_state' in lm:
            lm['realtime_state'],rm['realtime_state']=same_state(lm['realtime_state'],rm['realtime_state'],windows,elapsed)
    same_assistant(left,right,windows,elapsed)

def exact_briefing(left,right,windows,elapsed):
    left,right=deepcopy(left),deepcopy(right)
    assert left.keys()==right.keys() and 'time' in left
    same_evaluation(left['time'],right['time'],windows)
    left.pop('time');right.pop('time')
    assert_same_with_elapsed_age(left,right,elapsed)

def locked_metrics(left,right,windows):
    left,right=deepcopy(left),deepcopy(right)
    assert left.keys()==right.keys()
    same_evaluation(left['generated_at_madrid'],right['generated_at_madrid'],windows)
    left.pop('generated_at_madrid');right.pop('generated_at_madrid')
    assert left==right

def compare(probe,monkeypatch,client,route,**kwargs):
    a=probe['a']
    assert client.get(route,base_url='http://127.0.0.1',**kwargs).status_code==200
    before=business_state(probe['path']);started=time.perf_counter()
    current,data,calls,window=measure(a,client,route,**kwargs)
    with monkeypatch.context() as control:
        control.setattr(a,'v931_safe_dashboard_data',baseline(a))
        old,prior,old_calls,old_window=measure(a,client,route,**kwargs)
    elapsed=math.ceil(time.perf_counter()-started)+1
    assert current.get_data()==old.get_data()
    assert data['sports_metrics']==prior['sports_metrics']
    for key in ('picks','v925_picks','v925_odds','v932_sports_value','membership','shark_usage'):
        assert_same_with_elapsed_age(data[key],prior[key],elapsed)
    exact_briefing(data['briefing'],prior['briefing'],(window,old_window),elapsed)
    full_assistant(data['shark_assistant'],prior['shark_assistant'],(window,old_window),elapsed)
    selected_state=((data['shark_assistant'].get('context') or {}).get('match') or {}).get('realtime_state')
    if selected_state is not None:
        for field in ('provider_observed_at','live_valid_until_madrid','fixture_id','score_home'):
            changed=deepcopy(selected_state);changed[field]='MUTATED_OWN_EVIDENCE'
            with pytest.raises(AssertionError):same_state(selected_state,changed,(window,window),elapsed)

    assert calls['build_sports_home_sections']==old_calls['build_sports_home_sections']==1
    assert calls['_v991_prepare_summary_operation']==old_calls['_v991_prepare_summary_operation']==1
    assert calls['_v991_realtime_projection']==old_calls['_v991_realtime_projection']==1
    assert calls['build_sports_metrics_contract']==3 and old_calls['build_sports_metrics_contract']==5
    assert calls['_v931_provider_context']==0 and old_calls['_v931_provider_context']==1
    assert business_state(probe['path'])==before
    assert probe['draft_canary'] not in current.get_data(as_text=True)
    return current,data,calls,old_calls

if _owned_supervisor:
    @pytest.mark.parametrize('principal',('ANONYMOUS','FREE','PRO','ELITE'))
    @pytest.mark.parametrize('route',('/shark','/shark-ai'))
    def test_role_page_and_complete_context_remain_equal(prepared_probe,monkeypatch,principal,route):
        probe=prepared_probe
        client=probe['a'].app.test_client() if principal=='ANONYMOUS' else probe['login'](principal)[0]
        r,data,calls,old_calls=compare(probe,monkeypatch,client,route)
        if principal!='ELITE':assert probe['published_canary'] not in r.get_data(as_text=True)
        print('SHARK_INPUT_EQUIVALENCE '+json.dumps({'route':route,'principal':principal,'HTML_exact':True,'complete_context_compared':True,'candidate':calls,'published_main':old_calls}))

    @pytest.mark.parametrize('principal',('ANONYMOUS','FREE','PRO','ELITE'))
    def test_explicit_advice_selection_keeps_same_membership_boundary(prepared_probe,monkeypatch,principal):
        probe=prepared_probe
        client=probe['a'].app.test_client() if principal=='ANONYMOUS' else probe['login'](principal)[0]
        r,data,calls,old_calls=compare(probe,monkeypatch,client,'/shark',query_string={'pick_id':probe['published_pick']})
        if principal!='ELITE':assert probe['published_canary'] not in r.get_data(as_text=True)
        print('SHARK_SELECTED_EQUIVALENCE '+json.dumps({'principal':principal,'HTML_exact':True,'complete_context_compared':True}))

    @pytest.mark.parametrize('principal',('ANONYMOUS','ELITE'))
    def test_locked_source_retains_original_unknown_and_issue_writers(prepared_probe,monkeypatch,principal):
        probe=prepared_probe;a=probe['a'];client=a.app.test_client() if principal=='ANONYMOUS' else probe['login'](principal)[0]
        for name in ('v931_record_client_route_issue','v932_record_authenticated_issue'):
            original=getattr(a,name)
            def writer(*args,_original=original,**kwargs):
                with monkeypatch.context() as owned:
                    owned.setattr(a,'BASE_DIR',probe['path'].parent)
                    return _original(*args,**kwargs)
            monkeypatch.setattr(a,name,writer)
        fault={'environ_overrides':{'nemesis.v932.database_locked':True}}
        # The unchanged logged-in route initializes its existing quota table
        # on first visit. The explicit initial-schema controls below test both
        # versions from that missing-table state; this hash checks later reads.
        assert client.get('/shark',base_url='http://127.0.0.1').status_code==200
        before=business_state(probe['path'])
        c,cd,_,cw=measure(a,client,'/shark',**fault)
        with monkeypatch.context() as control:
            control.setattr(a,'v931_safe_dashboard_data',baseline(a))
            old,od,_,ow=measure(a,client,'/shark',**fault)
        assert c.get_data()==old.get_data()
        locked_metrics(cd['sports_metrics'],od['sports_metrics'],(cw,ow))
        assert cd['sports_metrics']['scope']=='unprepared_observations'
        assert cd['shark_assistant']==od['shark_assistant']
        assert cd['shark_assistant']['context']=={'data_state': {}}
        assert cd['shark_assistant']['answer']=={}
        assert business_state(probe['path'])==before
        recorded=json.loads((probe['path'].parent/'data/runtime/sentinel_client_route_issues.json').read_text(encoding='utf-8'))
        assert any(row['route']=='/shark' and row['count']==2 for row in recorded['issues'])

    def test_wrapper_still_rechecks_metrics_after_current_provider_state(prepared_probe,monkeypatch):
        probe=prepared_probe;a=probe['a'];real=a.get_v932_real_sports_value_context
        def change_after_input(summary=None):
            value=real(summary)
            if isinstance(summary,dict) and summary.get('all_valid_matches') and not summary.get('_qa_changed_after_input'):
                summary['_qa_changed_after_input']=True
                summary['all_valid_matches'][0]['home_score']=91
                summary['all_valid_matches'][0]['id']='qa-owned-identity-changed'
            return value
        monkeypatch.setattr(a,'get_v932_real_sports_value_context',change_after_input)
        client=probe['login']('ELITE')[0]
        r,data,calls,old_calls=compare(probe,monkeypatch,client,'/shark')
        assert data['sports_metrics']['identity_coverage']['state']=='PREPARED'



if _owned_supervisor:
    @pytest.mark.parametrize('selected',(False,True))
    def test_actual_main_against_itself_has_only_checked_evaluation_drift(prepared_probe,monkeypatch,selected):
        probe=prepared_probe;a=probe['a'];client=probe['login']('ELITE')[0]
        kwargs={'query_string':{'pick_id':probe['published_pick']}} if selected else {}
        with monkeypatch.context() as control:
            control.setattr(a,'v931_safe_dashboard_data',baseline(a))
            assert client.get('/shark',base_url='http://127.0.0.1',**kwargs).status_code==200
            left,ld,lc,lw=measure(a,client,'/shark',**kwargs)
            time.sleep(1.1)
            right,rd,rc,rw=measure(a,client,'/shark',**kwargs)
        elapsed=math.ceil((rw[1]-lw[0]).total_seconds())+1
        assert left.get_data()==right.get_data()
        assert ld['sports_metrics']==rd['sports_metrics']
        exact_briefing(ld['briefing'],rd['briefing'],(lw,rw),elapsed)
        full_assistant(ld['shark_assistant'],rd['shark_assistant'],(lw,rw),elapsed)
        assert lc['build_sports_metrics_contract']==rc['build_sports_metrics_contract']==5

if not _owned_supervisor:
    def test_shark_input_cases_in_original_guarded_process(tmp_path):
        import os,subprocess,sys,xml.etree.ElementTree as ET
        root=Path(__file__).resolve().parents[1]
        bootstrap=('import platform,runpy,sys;platform.uname();platform.platform();'
            "sys.argv=[sys.argv[1],sys.argv[2],'-s','--tb=short'];runpy.run_path(sys.argv[0],run_name='__main__')")
        env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTEST_ADDOPTS='',PYTHONDONTWRITEBYTECODE='1')
        r=subprocess.run([sys.executable,'-B','-c',bootstrap,str(root/'tools/check_local_candidate.py'),str(Path(__file__).resolve())],
            cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
        (tmp_path/'guarded.stdout.txt').write_text(r.stdout,encoding='utf-8')
        (tmp_path/'guarded.stderr.txt').write_text(r.stderr,encoding='utf-8')
        assert r.returncode==0,(r.stdout[-12000:],r.stderr[-1500:])
        qa=[line.removeprefix('QA_OUTPUT ') for line in r.stdout.splitlines() if line.startswith('QA_OUTPUT ')]
        boundary=[line.removeprefix('BOUNDARY_EVENTS ') for line in r.stdout.splitlines() if line.startswith('BOUNDARY_EVENTS ')]
        assert len(qa)==len(boundary)==1 and ast.literal_eval(boundary[0])==[]
        out=Path(qa[0]).resolve()
        assert out.is_relative_to((root/'data/local_dev').resolve()) and out.name.startswith('candidate-')
        suite=ET.parse(out/'result.xml').find('testsuite')
        assert suite is not None and suite.attrib['tests']=='19'
        assert all(suite.attrib[k]=='0' for k in ('failures','errors','skipped'))
        proof={'actual_cases':19,'failures':0,'errors':0,'skipped':0,'boundary_events':[],'guarded_output':str(out)}
        (tmp_path/'guarded-proof.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
        print('SHARK_INPUT_STANDARD_PROOF '+json.dumps(proof))

if _owned_supervisor:
    @pytest.mark.parametrize('implementation',('candidate','published_main'))
    def test_existing_first_visit_quota_schema_and_no_question_charge(prepared_probe,monkeypatch,implementation):
        probe=prepared_probe;a=probe['a'];client=probe['login']('ELITE')[0]
        # Only this fresh, wholly synthetic fixture can lack the original quota
        # table. Never run this setup against a real database or external store.
        with sqlite3.connect(probe['path']) as conn:
            if conn.execute("SELECT 1 FROM sqlite_master WHERE name='shark_memory'").fetchone():
                assert conn.execute('SELECT COUNT(*) FROM shark_memory').fetchone()[0]==0
                conn.execute('DROP TABLE shark_memory')
        for name in ('v931_record_client_route_issue','v932_record_authenticated_issue'):
            original=getattr(a,name)
            def original_owned_writer(*args,_original=original,**kwargs):
                with monkeypatch.context() as owned:
                    owned.setattr(a,'BASE_DIR',probe['path'].parent)
                    return _original(*args,**kwargs)
            monkeypatch.setattr(a,name,original_owned_writer)
        before=business_state(probe['path'])
        with monkeypatch.context() as control:
            if implementation=='published_main':control.setattr(a,'v931_safe_dashboard_data',baseline(a))
            r=client.get('/shark',base_url='http://127.0.0.1',environ_overrides={'nemesis.v932.database_locked':True})
        assert r.status_code==200
        after=business_state(probe['path'])
        assert set(after)==set(before)|{'shark_memory'}
        assert {k:v for k,v in after.items() if k!='shark_memory'}==before
        with sqlite3.connect(probe['path']) as conn:
            assert conn.execute('SELECT COUNT(*) FROM shark_memory').fetchone()[0]==0
            assert [row[1] for row in conn.execute('PRAGMA table_info(shark_memory)')]==['id','user_id','event_type','context_json','created_at']
            indexes={row[1] for row in conn.execute('PRAGMA index_list(shark_memory)')}
        assert {'idx_shark_memory_user','idx_shark_memory_event'}<=indexes
        print('EXISTING_INITIAL_SCHEMA_CONTROL '+json.dumps({'implementation':implementation,'same_original_empty_quota_table':True,'business_rows_unchanged':True,'question_charges':0}))
