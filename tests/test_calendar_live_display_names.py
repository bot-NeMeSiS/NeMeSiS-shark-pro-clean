"""Actual Calendar/Live consumers retain facts and permission boundaries.

All data are owned synthetic fixtures. The dense measurement is a local
component comparison, not evidence of cold/global production performance.
"""
from copy import deepcopy
from datetime import datetime, timedelta
import cProfile, json, pstats, time, math
from test_client_view_preparation import same_bootstrap_html, same_realtime, same_evaluation, same_age
from test_picks_read_path_efficiency import _owned_supervisor
from zoneinfo import ZoneInfo
import pytest
from test_display_name_read_paths import published_formatters
from test_picks_read_path_efficiency import prepared_probe, shark_probe, business_state, capture
from tests.test_v957_calendar_fixture_deduplication import _prepare, _summary
from tests.test_calendar_facet_batch_counts import _unique_primary
from engines import display_name_normalization as names


def _same_calendar_tree(left, right, windows, elapsed):
    """Only independently checked evaluation metadata may differ."""
    assert type(left) is type(right)
    if isinstance(left, dict):
        assert left.keys()==right.keys()
        if "sports_relevance" in left or "realtime_state" in left:
            l,r=deepcopy(left),deepcopy(right)
            if "sports_relevance" in l:
                lp,rp=l["sports_relevance"],r["sports_relevance"]
                assert lp.keys()==rp.keys()
                if lp["kickoff_delta_minutes"]!=rp["kickoff_delta_minutes"]:
                    for row,profile,window in ((l,lp,windows[0]),(r,rp,windows[1])):
                        kickoff=datetime.fromisoformat(row["kickoff_iso"])
                        assert kickoff.tzinfo is not None and type(profile["kickoff_delta_minutes"]) is int
                        minimum=int((kickoff-window[1]).total_seconds()//60)
                        maximum=int((kickoff-window[0]).total_seconds()//60)
                        assert minimum<=profile["kickoff_delta_minutes"]<=maximum
                    lp.pop("kickoff_delta_minutes");rp.pop("kickoff_delta_minutes")
            # These Calendar-specific ages are calculated from the same
            # untouched observations; freshness/status decisions stay exact.
            for family,field in (("v935_freshness","age_seconds"),
                                 ("v935_status_truth","live_age_seconds"),
                                 ("status_info","live_age_seconds")):
                lp,rp=l.get(family),r.get(family)
                if isinstance(lp,dict) and isinstance(rp,dict):
                    assert lp.keys()==rp.keys()
                    if field in lp and lp[field]!=rp[field]:
                        same_age(lp[field],rp[field],elapsed)
                        lp.pop(field);rp.pop(field)
            same_realtime({"matches":[l]},{"matches":[r]},windows,elapsed)
            return
        for key in left:_same_calendar_tree(left[key],right[key],windows,elapsed)
    elif isinstance(left,list):
        assert len(left)==len(right)
        for l,r in zip(left,right):_same_calendar_tree(l,r,windows,elapsed)
    else:assert left==right


if _owned_supervisor:

    @pytest.mark.parametrize("principal", ("ANONYMOUS", "FREE", "PRO", "ELITE"))
    @pytest.mark.parametrize("route", ("/calendar", "/live"))
    def test_calendar_live_http_output_keeps_facts_and_permissions(prepared_probe, monkeypatch, principal, route):
        p=prepared_probe;a=p["a"]
        client=a.app.test_client() if principal=="ANONYMOUS" else p["login"](principal)[0]
        assert client.get(route, base_url="http://127.0.0.1").status_code==200
        before=business_state(p["path"])
        cstart=datetime.now(ZoneInfo("UTC"))
        with capture(a) as current_data:
            current=client.get(route,base_url="http://127.0.0.1")
        cend=datetime.now(ZoneInfo("UTC"));pstart=cend
        with published_formatters(monkeypatch), capture(a) as previous_data:
            previous=client.get(route,base_url="http://127.0.0.1")
        pend=datetime.now(ZoneInfo("UTC"));windows=((cstart,cend),(pstart,pend))
        elapsed=math.ceil((pend-cstart).total_seconds())+1
        assert current.status_code==previous.status_code==200
        cd,pd=current_data[-1],previous_data[-1]
        if route=="/live":same_bootstrap_html(current,previous,cd,pd,windows,elapsed)
        else:assert current.get_data()==previous.get_data()
        cm,pm=deepcopy(cd["sports_metrics"]),deepcopy(pd["sports_metrics"])
        if cm["generated_at_madrid"]!=pm["generated_at_madrid"]:
            same_evaluation(cm.pop("generated_at_madrid"),pm.pop("generated_at_madrid"),windows)
        assert cm==pm
        if route=="/calendar":
            for field in ("filters","matches","counts","facets","day_groups","tabs","date_chips"):
                left,right=cd["calendar"][field],pd["calendar"][field]
                _same_calendar_tree(left,right,windows,elapsed)
            assert cd["calendar"]["no_render_api_call"] is True
            assert cd["calendar"]["database_written"] is False
        else:
            for field in ("matches","counts","tabs","active_lane"):
                if field in cd["live_experience"] or field in pd["live_experience"]:
                    left,right=cd["live_experience"].get(field),pd["live_experience"].get(field)
                    if field=="matches":same_realtime({"matches":left},{"matches":right},windows,elapsed)
                    else:assert left==right
        assert p["draft_canary"] not in current.get_data(as_text=True)
        if principal!="ELITE":assert p["published_canary"] not in current.get_data(as_text=True)
        assert business_state(p["path"])==before

    def _measure(a, summary, operation):
        profiler=cProfile.Profile();start=time.perf_counter();began=datetime.now(ZoneInfo("UTC"))
        profiler.enable()
        try: result=a.v940_calendar_context(summary,"week",a.today_iso(),fixture_operation=operation)
        finally:profiler.disable()
        elapsed=time.perf_counter()-start
        stats=pstats.Stats(profiler).stats
        totals={name:{"calls":sum(v[1] for k,v in stats.items() if k[2]==name),
                      "self_seconds":round(sum(v[2] for k,v in stats.items() if k[2]==name),6)}
                for name in ("_norm","_normalize_text","_title_preserving_acronyms","normalize","_v940_calendar_prepare_match")}
        hotspots=[{"function":k[2],"module":k[0].split("/")[-1].split(chr(92))[-1],
                   "calls":v[1],"self_seconds":round(v[2],6),"cumulative_seconds":round(v[3],6)}
                  for k,v in sorted(stats.items(),key=lambda kv:kv[1][2],reverse=True)[:12]]
        return result,{"window":(began,datetime.now(ZoneInfo("UTC"))),"seconds":round(elapsed,6),"calls":totals,"hotspots":hotspots}

    def test_dense_calendar_context_keeps_complete_output_with_less_text_work(app_module, monkeypatch):
        a=app_module;rows=[]
        for number in range(384):
            row=_unique_primary(a,number,home="Atlético QA Club "+str(number))
            offset=(1,2,5,10)[number%4]
            start=datetime.fromisoformat(row["kickoff_iso"])+timedelta(days=offset-1)
            raw=json.loads(row["raw_json"]);raw["fixture"]["date"]=start.isoformat()
            row.update(kickoff_iso=start.isoformat(),match_date=start.date().isoformat(),raw_json=json.dumps(raw))
            rows.append(row)
        # Same-provider exact native copies and aliases must remain original inputs,
        # not become extra fixtures because a display-name cache happens to be warm.
        rows += [dict(row,id="copy-"+row["id"],match_id="copy-"+row["id"]) for row in rows[:32]]
        summary=_summary(rows);original=deepcopy(summary)
        with a.app.test_request_context("/calendar?lane=week"):
            operation=_prepare(a,monkeypatch,summary)
            names._normalize_short_text.cache_clear()
            current,first=_measure(a,summary,operation)
            cached,warm=_measure(a,summary,operation)
            with published_formatters(monkeypatch): previous,old=_measure(a,summary,operation)
        windows=(first["window"],warm["window"],old["window"])
        elapsed=math.ceil((windows[2][1]-windows[0][0]).total_seconds())+1
        for value,measurement in ((current,first),(cached,warm),(previous,old)):
            generated=value["sports_metrics"].pop("generated_at_madrid")
            same_evaluation(generated,generated,(measurement["window"],measurement["window"]))
            measurement.pop("window")
        _same_calendar_tree(current,cached,(windows[0],windows[1]),elapsed)
        _same_calendar_tree(cached,previous,(windows[1],windows[2]),elapsed)
        changed=deepcopy(previous);changed["matches"][0]["home_score"]=99
        with pytest.raises(AssertionError):
            _same_calendar_tree(cached,changed,(windows[1],windows[2]),elapsed)
        changed=deepcopy(previous);changed["matches"][0]["sports_relevance"]["kickoff_delta_minutes"]+=10000
        with pytest.raises(AssertionError):
            _same_calendar_tree(cached,changed,(windows[1],windows[2]),elapsed)
        assert current["counts"]["visible"]==288
        assert len(current["matches"])==288
        assert summary==original
        assert names._normalize_short_text.cache_info().maxsize==2048
        report={"source_rows":416,"visible_fixtures":288,"complete_context_equal":True,
                "candidate_empty_name_cache":first,"candidate_warm_name_cache":warm,"published_formatters":old,
                "production_performance_claim":False}
        print("DENSE_CALENDAR_LOCAL_COMPARISON "+json.dumps(report))
else:
    def test_calendar_live_names_in_original_guarded_process(tmp_path):
        import ast,os,subprocess,sys
        from pathlib import Path
        import xml.etree.ElementTree as ET
        root=Path(__file__).resolve().parents[1]
        bootstrap=("import platform,runpy,sys;platform.uname();platform.platform();"
            "sys.argv=[sys.argv[1],sys.argv[2],'-s','--tb=short'];runpy.run_path(sys.argv[0],run_name='__main__')")
        env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",PYTEST_ADDOPTS="",PYTHONDONTWRITEBYTECODE="1")
        result=subprocess.run([sys.executable,"-B","-c",bootstrap,str(root/"tools/check_local_candidate.py"),str(Path(__file__).resolve())],
            cwd=root,env=env,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=180)
        (tmp_path/"guarded.stdout.txt").write_text(result.stdout,encoding="utf-8")
        (tmp_path/"guarded.stderr.txt").write_text(result.stderr,encoding="utf-8")
        assert result.returncode==0,(result.stdout[-10000:],result.stderr[-2000:])
        paths=[line.removeprefix("QA_OUTPUT ") for line in result.stdout.splitlines() if line.startswith("QA_OUTPUT ")]
        events=[line.removeprefix("BOUNDARY_EVENTS ") for line in result.stdout.splitlines() if line.startswith("BOUNDARY_EVENTS ")]
        assert len(paths)==len(events)==1 and ast.literal_eval(events[0])==[]
        output=Path(paths[0]).resolve()
        assert output.is_relative_to((root/"data/local_dev").resolve()) and output.name.startswith("candidate-")
        suite=ET.parse(output/"result.xml").find("testsuite")
        assert suite is not None and suite.attrib["tests"]=="9"
        assert all(suite.attrib[k]=="0" for k in ("failures","errors","skipped"))
