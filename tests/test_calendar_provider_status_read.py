"""Calendar provider status keeps the normal FULL contract and visible output.
Use only the original LOCAL SAFE supervisor; actual App, users and readers stay real.
"""
from contextlib import contextmanager
import sys
import time
import math
from flask import session, template_rendered
import pytest
from test_home_source_metrics_read import owned_home, _assert_principal
from v991_api_prepare_only_cases import digest

@contextmanager
def captured(a):
    records=[]
    def receive(sender,template,context,**kw):
        user=context.get("current_user") or {}
        records.append((template.name,context["data"],{"id":str(user.get("id") or ""),"role":str(user.get("role") or "")}))
    template_rendered.connect(receive,a.app,weak=False)
    try: yield records
    finally: template_rendered.disconnect(receive,a.app)

@contextmanager
def provider_metric_calls(a):
    calls=[]
    previous=sys.getprofile()
    def observe(frame,event,arg):
        if event=="call" and frame.f_code is a.build_sports_metrics_contract.__code__:
            caller=frame.f_back
            if caller and caller.f_code.co_name=="get_sports_metrics_contract":
                caller=caller.f_back
            if caller and caller.f_code.co_name=="_v931_provider_context":
                calls.append("provider_full_metric")
    sys.setprofile(observe)
    try: yield calls
    finally: sys.setprofile(previous)


def difference_paths(left,right,path="root"):
    if digest(left)==digest(right):return []
    if isinstance(left,dict) and isinstance(right,dict):
        return [p for key in sorted(set(left)|set(right)) for p in difference_paths(left.get(key),right.get(key),path+"."+str(key))][:30]
    if isinstance(left,list) and isinstance(right,list) and len(left)==len(right):
        return [p for i,(a,b) in enumerate(zip(left,right)) for p in difference_paths(a,b,path+"["+str(i)+"]")][:30]
    return [path]


def assert_temporal_parity(left,right,elapsed,path="root"):
    if path.endswith(".sports_relevance.kickoff_delta_minutes"):
        # App uses floor((kickoff-real_now)/60). Two sequential real reads can
        # cross an integer-minute boundary, including negative countdowns.
        # Only this field may decrease, within the MEASURED interval; all other
        # relevance, kickoff, status and identity fields retain exact parity.
        if left is None or right is None:
            assert left is right,(path,"kickoff presence changed")
            return
        assert type(left) is int and type(right) is int,(path,"integer countdown required")
        assert math.isfinite(elapsed) and elapsed>=0,(path,"invalid real read interval")
        assert 0 <= left-right <= math.ceil(elapsed/60),(path,"countdown drift outside real read interval")
        return
    if (path.endswith(".live_age_seconds") or path.endswith(".v935_freshness.age_seconds")) and isinstance(left,int) and not isinstance(left,bool) and isinstance(right,int) and not isinstance(right,bool):
        # Engine age=int(real_now-provider_timestamp), clamped to zero.
        # Real reads are sequential; permit only measured elapsed plus integer rounding.
        assert 0 <= right-left <= math.ceil(elapsed)+1,(path,"age drift outside real read interval")
        return
    if isinstance(left,dict) and isinstance(right,dict):
        assert left.keys()==right.keys(),path
        for key in left:assert_temporal_parity(left[key],right[key],elapsed,path+"."+str(key))
    elif isinstance(left,list) and isinstance(right,list):
        assert len(left)==len(right),path
        for i,(a,b) in enumerate(zip(left,right)):assert_temporal_parity(a,b,elapsed,path+"["+str(i)+"]")
    else:assert digest(left)==digest(right),path

def test_temporal_oracle_rejects_data_changes_and_unbounded_age():
    assert_temporal_parity({"live_age_seconds":30,"state":"UPCOMING"},{"live_age_seconds":31,"state":"UPCOMING"},0.5)
    for right in ({"live_age_seconds":40,"state":"UPCOMING"},{"live_age_seconds":29,"state":"UPCOMING"},{"live_age_seconds":31,"state":"LIVE"}):
        with pytest.raises(AssertionError):assert_temporal_parity({"live_age_seconds":30,"state":"UPCOMING"},right,0.5)

def test_freshness_temporal_oracle_preserves_status_and_other_age_fields():
    left={"v935_freshness":{"age_seconds":30,"status":"FRESH","is_stale":False}}
    assert_temporal_parity(left,{"v935_freshness":{"age_seconds":31,"status":"FRESH","is_stale":False}},0.5)
    for age,status,stale in ((40,"FRESH",False),(29,"FRESH",False),(31,"STALE",True)):
        with pytest.raises(AssertionError):
            assert_temporal_parity(left,{"v935_freshness":{"age_seconds":age,"status":status,"is_stale":stale}},0.5)
    with pytest.raises(AssertionError):assert_temporal_parity({"other":{"age_seconds":30}},{"other":{"age_seconds":31}},0.5)

@pytest.mark.parametrize("left,right,elapsed",[
    (1265,1264,1.1519627571105957),(0,-1,0.5),(-1,-2,0.01),
    (1265,1265,0),(2,1,60),(None,None,0.5),
])
def test_kickoff_countdown_oracle_accepts_only_bounded_real_minute_steps(left,right,elapsed):
    assert_temporal_parity({"sports_relevance":{"kickoff_delta_minutes":left}},
                          {"sports_relevance":{"kickoff_delta_minutes":right}},elapsed)


@pytest.mark.parametrize("left,right,elapsed",[
    (1265,1266,0.5),(1265,1263,1.1519627571105957),(0,-2,0.5),
    (1265,1264,0),(1,1,float("inf")),(True,True,0.5),
    (1.0,1.0,0.5),(None,0,0.5),(1,None,0.5),
])
def test_kickoff_countdown_oracle_rejects_reverse_excess_drift_and_type_changes(left,right,elapsed):
    with pytest.raises(AssertionError):
        assert_temporal_parity({"sports_relevance":{"kickoff_delta_minutes":left}},
                              {"sports_relevance":{"kickoff_delta_minutes":right}},elapsed)


@pytest.mark.parametrize("mutation",["score","status","kickoff"])
def test_countdown_tolerance_does_not_hide_other_sport_contract_changes(mutation):
    left={"sports_relevance":{"kickoff_delta_minutes":1265,"score":70},
          "status":"UPCOMING","kickoff":"synthetic-fixed-kickoff"}
    right={"sports_relevance":{"kickoff_delta_minutes":1264,"score":70},
           "status":"UPCOMING","kickoff":"synthetic-fixed-kickoff"}
    if mutation=="score":right["sports_relevance"]["score"]=71
    elif mutation=="status":right["status"]="LIVE"
    else:right["kickoff"]="changed-kickoff"
    with pytest.raises(AssertionError):assert_temporal_parity(left,right,0.5)


def test_countdown_tolerance_does_not_apply_to_other_numeric_fields():
    with pytest.raises(AssertionError):
        assert_temporal_parity({"other":{"kickoff_delta_minutes":1265}},
                              {"other":{"kickoff_delta_minutes":1264}},0.5)


@pytest.mark.parametrize("role",["anonymous","free","pro","elite","admin"])
@pytest.mark.parametrize("state",["upcoming","live","empty"])
def test_calendar_status_only_keeps_visible_contract_and_full_defaults(owned_home,role,state):
    r,a=owned_home,owned_home.app
    r.seed(live=state=="live",empty=state=="empty")
    date=a.today_iso() if state!="upcoming" else a.today_iso(1)
    before=r.table_hashes()
    started_real=time.time()
    with r.bounded("calendar real GET"),captured(a) as actual,provider_metric_calls(a) as calls:
        response=r.clients[role].get("/calendar",query_string={"date":date},base_url="http://localhost")
        body=response.get_data()
    assert response.status_code==200 and [x[0] for x in actual]==["calendar.html"]
    _assert_principal(actual[0][2],role)
    assert calls==[]
    data=actual[0][1]
    with r.clients[role].session_transaction() as stored: identity=dict(stored)
    with a.app.test_request_context("/calendar",query_string={"date":date},base_url="http://localhost"):
        session.update(identity)
        with r.bounded("calendar FULL control"),captured(a) as control:
            legacy,summary=a.v932_safe_dashboard_data("/calendar","today",date,compact=True,_calendar_view=True)
            summary=a._v940_hydrate_selected_date_results(summary,date)
            legacy["calendar"]=a.v940_calendar_context(summary,"today",date)
            legacy["matches"]=legacy["calendar"].get("matches",[])
            legacy["lane"]=legacy["calendar"]["filters"].get("lane","today")
            legacy["date"]=legacy["calendar"]["filters"].get("date",date)
            legacy["sports_metrics"]=legacy["calendar"]["sports_metrics"]
            with provider_metric_calls(a) as full_calls:
                legacy["v925_calendar"]=a._v940_calendar_provider_context(summary)
            assert full_calls==["provider_full_metric"]
            assert {"sports_metrics","counts"}<=legacy["v925_calendar"].keys()
            a.render_template("calendar.html",data=legacy)
            direct=a._v931_provider_context(summary)
            explicit=a._v931_provider_context(summary,_status_only=False)
            assert digest(direct)==digest(explicit)
    assert [x[0] for x in control]==["calendar.html"]
    _assert_principal(control[0][2],role)
    expected=control[0][1]
    elapsed_real=time.time()-started_real
    assert elapsed_real>=0
    for field in ("calendar","matches","sports_metrics","lane","date"):
        assert_temporal_parity(data[field],expected[field],elapsed_real,field)
    full_provider=expected["v925_calendar"]
    assert_temporal_parity(data["v925_calendar"],{k:v for k,v in full_provider.items() if k not in {"sports_metrics","counts"}},elapsed_real,"provider")
    assert b'data-v933-template="calendar"' in body
    assert r.table_hashes()==before
