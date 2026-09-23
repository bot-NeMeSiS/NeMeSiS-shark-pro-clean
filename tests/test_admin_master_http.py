"""SIMULATED_QA: real Flask routes, isolated SQLite, all external transport denied."""
import copy
import socket
import sqlite3
from pathlib import Path
import pytest
from datetime import datetime, timedelta, timezone
from engines.admin_control_engine import AdminControlStore

@pytest.fixture
def admin(app_module, monkeypatch, tmp_path):
    a=app_module
    monkeypatch.setattr(a,"DB_PATH",str(tmp_path/"admin-master.db"))
    monkeypatch.setattr(a,"_SEEDED_DB_PATH",None)
    monkeypatch.setattr(a,"_SEEDING_DB_PATH",None)
    monkeypatch.setattr(a,"APP_INITIALIZED",False)
    monkeypatch.setattr(a,"LOCAL_SAFE_DATA_DIR",tmp_path)
    a.seed_core()
    a.app.config.update(TESTING=True)
    def deny(*args,**kwargs): pytest.fail("Unexpected external network")
    monkeypatch.setattr(socket.socket,"connect",deny)
    monkeypatch.setattr(a,"get_public_home_sports_summary",lambda:{
        "storage_status":"ok","valid_matches_today_count":0,"valid_matches_today":[],"valid_live_events":[],
        "valid_upcoming_matches":[],"valid_active_picks":[]})
    c=a.app.test_client()
    with c.session_transaction() as state:
        state.update(user_id="SIMULATED_QA_admin",user_role="ADMIN",membership="ADMIN")
        token=a.generate_csrf_token(state)
    return a,c,{"X-CSRF-Token":token}

@pytest.mark.parametrize("path",["/api/admin/master-control","/admin/dashboard","/admin/client-preview","/admin/client-preview/frame"])
def test_anonymous_protected(admin,path):
    a,_,_=admin
    response=a.app.test_client().get(path)
    assert response.status_code == (403 if path.startswith("/api") else 302)


def test_reliability_attestation_requires_proposal_and_independent_confirmation(admin, monkeypatch, tmp_path):
    from engines import sentinel_issues_engine as ledger
    a,c,h=admin
    monkeypatch.setattr(ledger,'sentinel_issues_memory_path',lambda root=None:tmp_path/'issues.json')
    issue=ledger.normalize_sentinel_issue({'title':'SIMULATED_QA incident','stable_key':'qa-http','area':'admin',
        'evidence':'Confirmed QA reproduction only','last_seen':(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat()})
    ledger.save_sentinel_issues_memory({'issues':[issue]})
    # Existing legacy route must obey the same guard, not bypass the new action.
    result=c.post('/api/admin/sentinel/issues/'+issue['id']+'/resolve',headers=h)
    assert result.get_json()['ok'] is False
    params=dict(issue_id=issue['id'],root_cause='QA confirmed cause',corrective_action='QA fix',
        regression_test='tests/test_reliability.py',prevention='CI guard',detection='Sentinel rule',fix_sha='a'*40,
        evidence_ref='SIMULATED_QA/report',checked_at=datetime.now(timezone.utc).isoformat(),result='PASS',scope='CI')
    proposal=c.post('/api/admin/master-control/proposals',headers=h,json={'action_id':'sentinel.record_verification','parameters':params})
    assert proposal.status_code==200,proposal.get_json()
    assert ledger.load_sentinel_issues_memory()['issues'][0]['status']=='OPEN_REAL'
    reply=c.post('/api/admin/master-control/execute',headers=h,json={'proposal_id':proposal.get_json()['proposal']['proposal_id'],'confirmation':True})
    assert reply.get_json()['result']['verification']=='VERIFIED',reply.get_json()
    assert ledger.load_sentinel_issues_memory()['issues'][0]['status']=='VERIFIED'
    close=c.post('/api/admin/master-control/proposals',headers=h,json={'action_id':'sentinel.resolve','parameters':{'issue_id':issue['id']}})
    assert close.status_code==200
    reply=c.post('/api/admin/master-control/execute',headers=h,json={'proposal_id':close.get_json()['proposal']['proposal_id'],'confirmation':True})
    assert reply.get_json()['result']['verification']=='VERIFIED'
    assert ledger.load_sentinel_issues_memory()['issues'][0]['status']=='RESOLVED'
    audit=AdminControlStore(a.DB_PATH,a.APP_VERSION).list_audit()
    assert len(audit)==4  # Each external action keeps start and completion evidence.
    assert {i['action_id'] for i in audit if i['verification']=='VERIFIED'}=={'sentinel.record_verification','sentinel.resolve'}
    before=(tmp_path/'issues.json').read_bytes()
    response=c.get('/api/admin/master-control').get_json()
    assert response['reliability']['memory_available'] is True
    assert response['reliability']['radar']['drift']['deployment_certified'] is False
    assert (tmp_path/'issues.json').read_bytes()==before
    answer=c.post('/api/admin/master-control/chat',headers=h,json={'message':'¿Esto ya ocurrió? '+issue['id']}).get_json()
    assert answer['relation']['state']=='CONFIRMADO' and answer['source']=='DETERMINISTIC'

@pytest.mark.parametrize("path",["chat","proposals","execute","rollback"])
def test_writes_reject_get_and_missing_csrf(admin,path):
    a,c,headers=admin
    assert c.get("/api/admin/master-control/"+path).status_code == 405
    assert c.post("/api/admin/master-control/"+path,json={}).status_code == 403

def test_proposal_confirm_verification_audit_rollback(admin):
    a,c,h=admin
    store=AdminControlStore(a.DB_PATH,a.APP_VERSION)
    response=c.post("/api/admin/master-control/proposals",headers=h,json={"action_id":"settings.update","parameters":{"key":"highlights_enabled","value":False}})
    assert response.status_code==200,response.get_json()
    proposal=response.get_json()["proposal"]
    assert store.settings()["highlights_enabled"]["value"] is True
    result=c.post("/api/admin/master-control/execute",headers=h,json={"proposal_id":proposal["proposal_id"],"confirmation":True}).get_json()["result"]
    assert result["verification"]=="VERIFIED"
    assert store.settings()["highlights_enabled"]["value"] is False
    assert len(store.list_audit())==1
    rollback=c.post("/api/admin/master-control/rollback",headers=h,json={"audit_id":result["audit_id"]}).get_json()["proposal"]
    assert store.settings()["highlights_enabled"]["value"] is False
    result=c.post("/api/admin/master-control/execute",headers=h,json={"proposal_id":rollback["proposal_id"],"confirmation":True})
    assert result.status_code==200
    assert store.settings()["highlights_enabled"]["value"] is True
    assert len(store.list_audit())==2

@pytest.mark.parametrize("action,parameters",[("shell",{"command":"whoami"}),("settings.update",{"key":"DB_PATH","value":"secret"}),("settings.update",{"key":"banner_enabled","value":"true"}),("sentinel.create_improvement",{"title":"QA","detail":"check","route":"/../../file"})])
def test_rejects_arbitrary_actions_and_parameters(admin,action,parameters):
    _,c,h=admin
    assert c.post("/api/admin/master-control/proposals",headers=h,json={"action_id":action,"parameters":parameters}).status_code==400

def test_chat_proposes_never_executes_and_absent_ai_falls_back(admin,monkeypatch):
    a,c,h=admin
    monkeypatch.setattr(a,"env_present",lambda name:False)
    reply=c.post("/api/admin/master-control/chat",headers=h,json={"message":"Desactiva highlights."})
    assert reply.status_code==200,reply.get_json()
    assert reply.get_json()["kind"]=="PROPOSAL"
    assert AdminControlStore(a.DB_PATH,a.APP_VERSION).settings()["highlights_enabled"]["value"] is True
    reply=c.post("/api/admin/master-control/chat",headers=h,json={"message":"¿Cómo está todo?"})
    assert reply.status_code==200,reply.get_json()
    assert "IA avanzada no configurada" in reply.get_json()["message"]
    assert reply.get_json()["executed"] is False

@pytest.mark.parametrize("plan",["FREE","PRO","ELITE"])
@pytest.mark.parametrize("page",["home","matches","live","picks","shark","telegram","profile","memberships"])
def test_preview_keeps_admin_session_and_database_unchanged(admin,plan,page):
    a,c,_=admin
    with c.session_transaction() as state: before=dict(state)
    conn=sqlite3.connect(a.DB_PATH)
    users_before=conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    conn.close()
    response=c.get("/admin/client-preview/frame",query_string={"page":page,"plan":plan})
    assert response.status_code==200
    assert "ADMIN PREVIEW" in response.get_data(as_text=True)
    assert f'data-preview-plan="{plan}"' in response.get_data(as_text=True)
    assert 'data-v933-shell="admin"' not in response.get_data(as_text=True)
    assert "script-src 'none'" in response.headers["Content-Security-Policy"]
    with c.session_transaction() as state: assert dict(state)==before
    conn=sqlite3.connect(a.DB_PATH)
    assert conn.execute("SELECT * FROM users ORDER BY id").fetchall()==users_before
    conn.close()

def test_snapshot_no_raw_secrets_or_provider_calls(admin,monkeypatch):
    a,c,_=admin
    monkeypatch.setattr(a,"v945_provider_health_snapshot",lambda:{"api_key":"MUST_NOT_ESCAPE","providers":[]})
    monkeypatch.setattr(a,"v928_telegram_overview_fast",lambda:{"last_error":"token=MUST_NOT_ESCAPE"})
    response=c.get("/api/admin/master-control")
    assert response.status_code==200
    assert "MUST_NOT_ESCAPE" not in response.get_data(as_text=True)
    assert response.get_json()["external_calls"]==0

def test_unknown_preview_and_write_blocked(admin):
    _,c,h=admin
    assert c.get("/admin/client-preview/frame?page=../app.py").status_code==400
    assert c.get("/admin/client-preview/frame?plan=ADMIN").status_code==400
    assert c.post("/admin/client-preview/frame",headers=h).status_code==405


@pytest.mark.parametrize("page", ["home", "matches", "live"])
def test_preview_match_favorites_remain_disabled(admin, monkeypatch, page):
    from html.parser import HTMLParser
    a, c, _ = admin
    match = {"id": "SIMULATED_QA_match", "home_team": "QA Home", "away_team": "QA Away", "sport": "football"}
    monkeypatch.setattr(a, "get_public_home_sports_summary", lambda: {
        "valid_matches_today": [match], "valid_upcoming_matches": [match], "valid_live_events": [match]})
    response = c.get("/admin/client-preview/frame", query_string={"page": page, "plan": "PRO"})
    assert response.status_code == 200
    favorites = []
    class Parser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "button" and "fav-star" in attrs.get("class", ""):
                favorites.append(attrs)
    parser = Parser()
    parser.feed(response.get_data(as_text=True))
    assert favorites, "The shared card must retain its session-aware favorite control"
    assert all("disabled" in attrs for attrs in favorites)

def test_dashboard_and_health(admin):
    _,c,_=admin
    assert c.get("/admin/dashboard").status_code==200
    assert c.get("/api/health").status_code==200

def test_master_tick_requires_secret(admin):
    a,_,_=admin
    c=a.app.test_client()
    assert c.get("/api/automation/master-tick").status_code==403


def test_master_tick_test_secret_dry_run_never_calls_operations(admin, monkeypatch):
    a,_,_=admin
    monkeypatch.setenv("AUTOMATION_SECRET","SIMULATED_QA_master_tick")
    calls=[]
    monkeypatch.setattr(a,"v818_master_callbacks",lambda:{"sports_sync":lambda:calls.append("sports"),"telegram_tick":lambda:calls.append("telegram")})
    response=a.app.test_client().get("/api/automation/master-tick?dry_run=1&secret=SIMULATED_QA_master_tick")
    assert response.status_code==403,response.get_data(as_text=True)[:300]
    assert response.get_json()["status"]=="LOCAL_SAFE_BLOCKED"
    with a.app.test_request_context("/api/automation/master-tick?dry_run=1&secret=SIMULATED_QA_master_tick"):
        result=a.api_v818_automation_master_tick()
        assert result.status_code==200 and result.get_json()["dry_run"] is True
    assert calls==[]

def _apply_setting(admin,key,value):
    _,c,h=admin
    result=c.post("/api/admin/master-control/proposals",headers=h,json={"action_id":"settings.update","parameters":{"key":key,"value":value}})
    assert result.status_code==200,result.get_json()
    proposal=result.get_json()["proposal"]["proposal_id"]
    result=c.post("/api/admin/master-control/execute",headers=h,json={"proposal_id":proposal,"confirmation":True})
    assert result.status_code==200 and result.get_json()["result"]["verification"]=="VERIFIED"

def test_highlights_switch_reaches_client_routes_and_cards(admin):
    a,_,_=admin
    _apply_setting(admin,"highlights_enabled",False)
    c=a.app.test_client()
    for path in ("/highlights","/resumenes","/resumenes-partidos","/highlight/SIMULATED_QA"):
        response=c.get(path)
        assert response.status_code==200
        assert "pausad" in response.get_data(as_text=True).lower()
    response=c.get("/api/client/highlights")
    assert response.status_code==200 and response.get_json()["disabled"] is True
    with a.app.test_request_context("/partidos"):
        match=a.v766_apply_match_highlight_badge({"id":"SIMULATED_QA","has_highlights":True,"highlight_url":"/highlight/SIMULATED_QA"})
        assert match["has_highlights"] is False and match["highlight_url"]==""
        assert a.v766_highlights_context()["status"]=="DISABLED_BY_ADMIN"

def test_banner_is_real_client_content_and_escaped(admin):
    a,_,_=admin
    _apply_setting(admin,"banner_text","SIMULATED_QA <script>alert(1)</script>")
    _apply_setting(admin,"banner_enabled",True)
    c=a.app.test_client()
    page=c.get("/cliente-login").get_data(as_text=True)
    assert "SIMULATED_QA &lt;script&gt;" in page
    assert "SIMULATED_QA <script>" not in page

@pytest.mark.parametrize("path",[
    "/admin/dashboard","/admin/matches","/admin/realtime-center","/admin/picks",
    "/admin/telegram/command-center","/admin/users","/admin/memberships","/admin/payments",
    "/admin/data-center","/admin/daily-automation","/admin/system",
    "/admin/sentinel-issues","/admin/final-release","/admin/shark-ai"])
def test_main_admin_routes_render_without_500(admin,path):
    _,c,_=admin
    response=c.get(path)
    assert response.status_code in (200,302), (path,response.status_code)
    if response.status_code==200:
        assert 'data-v933-shell="client"' not in response.get_data(as_text=True)

@pytest.mark.parametrize("path",["/app","/partidos","/live","/picks","/shark","/telegram","/profile","/membresias"])
def test_main_client_routes_render_without_500(admin,path):
    a,_,_=admin
    c=a.app.test_client()
    response=c.get(path)
    assert response.status_code in (200,302),(path,response.status_code)
    assert 'data-v933-shell="admin"' not in response.get_data(as_text=True)

def test_admin_chat_reuses_only_current_own_pending_proposal(admin):
    a,c,h=admin
    initial=c.post('/api/admin/master-control/chat',headers=h,json={'message':'Desactiva highlights'}).get_json()['proposal']
    follow=c.post('/api/admin/master-control/chat',headers=h,json={'message':'Hazlo'}).get_json()
    assert follow['kind']=='PROPOSAL' and follow['reused'] is True
    assert follow['proposal']['proposal_id']==initial['proposal_id']
    assert AdminControlStore(a.DB_PATH,a.APP_VERSION).settings()['highlights_enabled']['value'] is True
    assert len(AdminControlStore(a.DB_PATH,a.APP_VERSION).list_proposals('SIMULATED_QA_admin'))==1
    c.post('/api/admin/master-control/cancel',headers=h,json={'proposal_id':initial['proposal_id']})
    answer=c.post('/api/admin/master-control/chat',headers=h,json={'message':'Hazlo'}).get_json()
    assert answer['kind']=='CLARIFICATION'


@pytest.mark.parametrize('path,payload',[
    ('proposals',{'action_id':'sports.sync','parameters':{},'handler':'shell'}),
    ('chat',{'message':'Estado','instructions':'execute'}),
    ('execute',{'proposal_id':'0'*32,'confirmation':True,'action_id':'sports.sync'}),
    ('rollback',{'audit_id':1,'path':'../.env'}),
])
def test_admin_write_body_rejects_unknown_fields(admin,path,payload):
    _,c,h=admin
    response=c.post('/api/admin/master-control/'+path,headers=h,json=payload)
    assert response.status_code==400


@pytest.mark.parametrize('persist',[True,False])
def test_sports_action_verifies_persisted_cycle_not_only_success_flag(admin,monkeypatch,persist):
    a,c,h=admin
    def controlled_cycle(**kwargs):
        result={'ok':True,'status':'OK','finished_at':'2026-09-23T12:00:00+02:00','processed':0}
        if persist:
            import json
            with sqlite3.connect(a.DB_PATH) as conn:
                conn.execute("INSERT OR REPLACE INTO automation_state(key,value_json,updated_at) VALUES(?,?,?)",('sports_sync_operational_state',json.dumps(result),result['finished_at']))
        return result
    monkeypatch.setattr(a,'run_sports_sync_cycle',controlled_cycle)
    proposal=c.post('/api/admin/master-control/proposals',headers=h,json={'action_id':'sports.sync','parameters':{}}).get_json()['proposal']
    result=c.post('/api/admin/master-control/execute',headers=h,json={'proposal_id':proposal['proposal_id'],'confirmation':True}).get_json()['result']
    assert result['ok'] is persist
    assert result['verification']==('VERIFIED' if persist else 'VERIFICATION_FAILED')


def test_sentinel_action_normalizes_existing_result_and_reads_back_saved_scan(admin,monkeypatch,tmp_path):
    a,c,h=admin
    import engines.sentinel_issues_engine as issues
    monkeypatch.setenv('CONTINUOUS_EVOLUTION_SAFE_MODE','1')
    monkeypatch.setenv('CONTINUOUS_EVOLUTION_STORAGE_ROOT',str(tmp_path/'sentinel-only'))
    def controlled_scan(**kwargs):
        memory=issues.load_sentinel_issues_memory(a.BASE_DIR)
        memory['last_scan_madrid']='2026-09-23T12:34:00+02:00'
        issues.save_sentinel_issues_memory(memory,a.BASE_DIR)
        return issues.build_sentinel_issues_summary(a.APP_VERSION,memory)
    monkeypatch.setattr(a,'_v892_sentinel_issues_summary',controlled_scan)
    proposal=c.post('/api/admin/master-control/proposals',headers=h,json={'action_id':'sentinel.scan','parameters':{}}).get_json()['proposal']
    result=c.post('/api/admin/master-control/execute',headers=h,json={'proposal_id':proposal['proposal_id'],'confirmation':True}).get_json()['result']
    assert result['ok'] is True and result['verification']=='VERIFIED'


def test_corrupt_setting_and_unavailable_sports_do_not_break_dashboard(admin,monkeypatch):
    a,c,h=admin
    store=AdminControlStore(a.DB_PATH,a.APP_VERSION);store.initialize()
    with sqlite3.connect(a.DB_PATH) as conn:
        conn.execute("INSERT INTO automation_state VALUES('admin_control.settings.highlights_enabled','invalid','now')")
    monkeypatch.setattr(a,'get_public_home_sports_summary',lambda:{'storage_status':'unavailable','valid_matches_today_count':0,'valid_live_events':[]})
    response=c.get('/api/admin/master-control')
    assert response.status_code==200
    data=response.get_json()
    assert data['settings_readable'] is False and data['settings']['highlights_enabled'] is False
    facts={item['label']:item['value'] for item in data['facts']}
    assert facts['Partidos hoy'] is None and facts['Directos confirmados'] is None
    assert c.get('/admin/dashboard').status_code==200


@pytest.mark.parametrize("plan",["FREE","PRO","ELITE"])
@pytest.mark.parametrize("path",["/app","/partidos","/live","/picks","/shark","/telegram","/profile","/membresias"])
def test_authenticated_client_main_routes(admin,path,plan):
    a,_,_=admin
    c=a.app.test_client()
    with c.session_transaction() as state:
        state.update(user_id="SIMULATED_QA_client",user_role=plan,membership=plan,user_membership=plan,user_name="SIMULATED_QA")
    response=c.get(path)
    assert response.status_code==200,(path,plan,response.status_code)
    assert 'data-v933-shell="admin"' not in response.get_data(as_text=True)

def test_runtime_answer_uses_local_evidence_and_never_certifies_remote(admin):
    a,c,h=admin
    response=c.post("/api/admin/master-control/chat",headers=h,json={"message":"Que version tenemos desplegada?"})
    assert response.status_code==200
    assert a.APP_VERSION in response.get_json()["message"]
    assert response.get_json()["executed"] is False


def test_improvement_creates_existing_issue_and_returns_codex_prompt(admin,monkeypatch,tmp_path):
    a,c,h=admin
    import engines.sentinel_issues_engine as issues
    monkeypatch.setenv("CONTINUOUS_EVOLUTION_SAFE_MODE","1")
    monkeypatch.setenv("CONTINUOUS_EVOLUTION_STORAGE_ROOT",str(tmp_path/"improvement-only"))
    proposal=c.post("/api/admin/master-control/chat",headers=h,json={"message":"Prepara mejora para la pantalla Live"}).get_json()["proposal"]
    assert issues.load_sentinel_issues_memory(a.LOCAL_SAFE_DATA_DIR)["issues"]==[]
    result=c.post("/api/admin/master-control/execute",headers=h,json={"proposal_id":proposal["proposal_id"],"confirmation":True}).get_json()["result"]
    assert result["ok"] is True and result["verification"]=="VERIFIED"
    task=result["result"]
    assert task["issue_id"].startswith("SENT-") and task["task_id"].startswith("TASK-")
    assert "/live" in task["codex_prompt"]
    assert any(i["id"]==task["issue_id"] for i in issues.load_sentinel_issues_memory(a.LOCAL_SAFE_DATA_DIR)["issues"])
    replay=c.post("/api/admin/master-control/execute",headers=h,json={"proposal_id":proposal["proposal_id"],"confirmation":True}).get_json()["result"]
    assert replay["reused"] is True
    assert len(issues.load_sentinel_issues_memory(a.LOCAL_SAFE_DATA_DIR)["issues"])==1
