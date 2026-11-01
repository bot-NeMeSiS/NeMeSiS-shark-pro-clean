"""Real owned HTTP equivalence against the published text formatters."""
import ast,os,sys,subprocess,json,hashlib,math,time
from pathlib import Path
from contextlib import contextmanager
import xml.etree.ElementTree as ET
import pytest
from test_shark_input_preparation import measure,exact_briefing,full_assistant,prepared_probe,shark_probe
from test_picks_read_path_efficiency import business_state,assert_same_with_elapsed_age
from test_display_name_normalization import legacy

@contextmanager
def published_formatters(monkeypatch):
    from engines import team_identity_engine as teams
    from engines import spanish_localization_engine as spanish
    with monkeypatch.context() as control:
        control.setattr(teams,"_norm",legacy("TEAM_NORM"))
        control.setattr(spanish,"_norm",legacy("SPANISH_NORM"))
        control.setattr(spanish,"_title_preserving_acronyms",legacy("TITLE"))
        yield

_loaded_app=sys.modules.get("app")
_owned_supervisor=bool(_loaded_app is not None and _loaded_app.local_safe_mode_enabled()
    and Path(_loaded_app.DB_PATH).resolve().is_relative_to(Path(_loaded_app.LOCAL_SAFE_DATA_DIR).resolve()))

if _owned_supervisor:
    @pytest.mark.parametrize("principal",("ANONYMOUS","FREE","PRO","ELITE"))
    @pytest.mark.parametrize("route",("/picks","/shark","/shark-ai"))
    def test_customer_output_permissions_and_fresh_checks_are_unchanged(prepared_probe,monkeypatch,principal,route):
        p=prepared_probe;a=p["a"]
        client=a.app.test_client() if principal=="ANONYMOUS" else p["login"](principal)[0]
        assert client.get(route,base_url="http://127.0.0.1").status_code==200
        before=business_state(p["path"])
        left,ld,lc,lw=measure(a,client,route)
        with published_formatters(monkeypatch):
            right,rd,rc,rw=measure(a,client,route)
        assert left.status_code==right.status_code==200
        assert left.get_data()==right.get_data()
        elapsed=math.ceil((rw[1]-lw[0]).total_seconds())+1
        for key in ("matches_today","matches_available","live_confirmed","picks_ready","matches_with_picks","finished_verified","incomplete_excluded","stale_live_excluded","snapshot_id"):
            assert ld["sports_metrics"][key]==rd["sports_metrics"][key]
        assert lc==rc
        if route=="/picks":
            for key in ("picks","locked_pick_count","pick_stats","v925_picks","v925_odds","pick_readiness","pick_watchlist"):
                assert_same_with_elapsed_age(ld[key],rd[key],elapsed)
        else:
            exact_briefing(ld["briefing"],rd["briefing"],(lw,rw),elapsed)
            full_assistant(ld["shark_assistant"],rd["shark_assistant"],(lw,rw),elapsed)
        text=left.get_data(as_text=True)
        assert p["draft_canary"] not in text
        if principal!="ELITE":assert p["published_canary"] not in text
        assert business_state(p["path"])==before

    @pytest.mark.parametrize("principal",("ANONYMOUS","ELITE"))
    @pytest.mark.parametrize("route",("/picks","/shark","/shark-ai"))
    def test_locked_reads_keep_the_original_unknown_state(prepared_probe,monkeypatch,principal,route):
        p=prepared_probe;a=p["a"]
        client=a.app.test_client() if principal=="ANONYMOUS" else p["login"](principal)[0]
        for name in ("v931_record_client_route_issue","v932_record_authenticated_issue"):
            writer=getattr(a,name)
            def isolated_writer(*args,_writer=writer,**kwargs):
                with monkeypatch.context() as owned:
                    owned.setattr(a,"BASE_DIR",p["path"].parent)
                    return _writer(*args,**kwargs)
            monkeypatch.setattr(a,name,isolated_writer)
        kwargs={"environ_overrides":{"nemesis.v932.database_locked":True}}
        left,ld,lc,lw=measure(a,client,route,**kwargs)
        with published_formatters(monkeypatch):right,rd,rc,rw=measure(a,client,route,**kwargs)
        assert left.status_code==right.status_code==200
        assert left.get_data()==right.get_data()
        assert ld["sports_metrics"]["scope"]==rd["sports_metrics"]["scope"]=="unprepared_observations"
        assert ld["sports_metrics"]["matches_available"]==rd["sports_metrics"]["matches_available"]==0
        assert lc==rc
else:
    def test_name_output_contracts_in_original_guarded_process(tmp_path):
        root=Path(__file__).resolve().parents[1]
        bootstrap=("import platform,runpy,sys;platform.uname();platform.platform();"
            "sys.argv=[sys.argv[1],sys.argv[2],'-s','--tb=short'];runpy.run_path(sys.argv[0],run_name='__main__')")
        env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",PYTEST_ADDOPTS="",PYTHONDONTWRITEBYTECODE="1")
        r=subprocess.run([sys.executable,"-B","-c",bootstrap,str(root/"tools/check_local_candidate.py"),str(Path(__file__).resolve())],
            cwd=root,env=env,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=240)
        (tmp_path/"guarded.stdout.txt").write_text(r.stdout,encoding="utf-8")
        (tmp_path/"guarded.stderr.txt").write_text(r.stderr,encoding="utf-8")
        assert r.returncode==0,(r.stdout[-12000:],r.stderr[-2000:])
        qa=[line.removeprefix("QA_OUTPUT ") for line in r.stdout.splitlines() if line.startswith("QA_OUTPUT ")]
        events=[line.removeprefix("BOUNDARY_EVENTS ") for line in r.stdout.splitlines() if line.startswith("BOUNDARY_EVENTS ")]
        assert len(qa)==len(events)==1 and ast.literal_eval(events[0])==[]
        out=Path(qa[0]).resolve()
        assert out.is_relative_to((root/"data/local_dev").resolve()) and out.name.startswith("candidate-")
        suite=ET.parse(out/"result.xml").find("testsuite")
        assert suite is not None and suite.attrib["tests"]=="18"
        assert all(suite.attrib[k]=="0" for k in ("failures","errors","skipped"))
        proof={"actual_HTTP_cases":18,"failures":0,"errors":0,"skips":0,"boundary_events":[],"output":str(out)}
        (tmp_path/"guarded-proof.json").write_text(json.dumps(proof,indent=2),encoding="utf-8")
        print("NAME_OUTPUT_GUARDED_PROOF "+json.dumps(proof))
