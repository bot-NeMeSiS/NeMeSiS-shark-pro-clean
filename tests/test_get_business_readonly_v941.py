"""V941 GET safety: canonical reads do not persist business-state changes."""
from __future__ import annotations
import sqlite3
import pytest

BUSINESS_TABLES=(
    "users","matches","picks","favorites","telegram_queue",
    "subscription_accounts","stripe_subscriptions","revenue_daily_metrics",
    "client_profiles","payment_readiness_daily","settings","user_activity",
    "telegram_subscribers","payment_webhook_events","subscription_events",
    "shark_context_snapshots","shark_memory",
    "telegram_settings","telegram_logs","telegram_deliveries","auto_alerts",
    "pick_grading_results","pick_grading_runs",
)
# /combis and /combinadas are owned by the dedicated client_combis blueprint.
# Its isolated suite verifies both aliases share one handler and GET leaves the DB
# byte-for-byte unchanged. This generic fixture swaps DB_PATH after blueprint
# registration, so including that captured-path adapter here would test the fixture,
# not request-time mutation safety.
CLIENT_ROUTES=("/app","/calendar","/live","/picks","/track-record","/shark","/telegram","/profile","/memberships","/mi-cuenta","/actividad","/alertas","/mi-dia","/briefing","/experiencia","/modo-app","/adaptive","/adaptativo")
ADMIN_ROUTES=(
    "/admin/dashboard","/admin/matches","/admin/realtime-center","/admin/picks",
    "/admin/telegram/command-center","/admin/users","/admin/memberships","/admin/payments",
    "/admin/shark-center","/admin/data-center","/admin/automation-center","/admin/sentinel-issues",
    "/admin/highlights-center","/admin/system","/admin/final-release",
)

def snapshot(path):
    result={}
    with sqlite3.connect(path) as conn:
        for table in BUSINESS_TABLES:
            exists=conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()
            result[table]=conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall() if exists else []
    return result

def isolated(app_module,monkeypatch,tmp_path):
    a=app_module
    db=str(tmp_path/"read-only-business.sqlite")
    monkeypatch.setattr(a,"DB_PATH",db)
    monkeypatch.setattr(a,"_SEEDED_DB_PATH",None)
    monkeypatch.setattr(a,"_SEEDING_DB_PATH",None)
    monkeypatch.setattr(a,"APP_INITIALIZED",False)
    a.seed_core()
    from engines.subscription_control_engine import ensure_subscription_schema
    from engines.payment_readiness_engine import ensure_payment_schema
    ensure_subscription_schema(db)
    ensure_payment_schema(db)
    a.ensure_stripe_schema(db)
    with sqlite3.connect(db) as conn:
        conn.execute("""INSERT OR REPLACE INTO users
          (id,name,username,email,password_hash,role,membership,membership_source,membership_expires_at,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?)""",
          ("qa-read-client","QA","qa_read","qa-read@example.invalid","x","PRO","PRO","admin_manual","2020-01-01T00:00:00+00:00","2020-01-01"))
        conn.commit()
    return a,db


def observe_business_writes(monkeypatch):
    """Observe (do not suppress) DML, including attempted same-value updates."""
    writes=[]
    original=sqlite3.connect
    def observe(op,table,column,*rest):
        if op in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) and table in BUSINESS_TABLES:
            writes.append((op,table,column))
        return sqlite3.SQLITE_OK
    def connect(*args,**kwargs):
        conn=original(*args,**kwargs)
        conn.set_authorizer(observe)
        return conn
    monkeypatch.setattr(sqlite3,"connect",connect)
    return writes


@pytest.mark.parametrize("stored", [False, True])
def test_telegram_settings_get_does_not_initialize_or_reenable(app_module,monkeypatch,tmp_path,stored):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    with sqlite3.connect(db) as conn:
        if stored:
            conn.execute("UPDATE telegram_settings SET enabled=0,auto_daily_picks=0 WHERE id='default'")
        else:
            conn.execute("DELETE FROM telegram_settings")
    monkeypatch.setattr(a,"telegram_env_should_enable",lambda: True)
    client=a.app.test_client()
    with client.session_transaction() as state:
        state.update(user_id="qa-admin-read",user_role="ADMIN",membership="ADMIN")
    before=snapshot(db)
    writes=observe_business_writes(monkeypatch)
    for method in ("GET","HEAD","GET"):
        response=client.open("/api/telegram/settings",method=method)
        assert response.status_code==200
        assert snapshot(db)==before
        assert not writes,writes
    assert response.get_json()["settings"]["enabled"] is False


def test_telegram_auto_posts_get_previews_without_replacing_saved_alerts(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    monkeypatch.setattr(a,"match_hub",lambda *_a,**_k:{
        "live":[],"with_picks":[{"id":"qa-alert-match","competition_name":"QA League"}],"popular":[]})
    # Seed through the real explicit preparation flow, then simulate a delivered alert.
    a.prepare_auto_posts()
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE auto_alerts SET status='SENT',created_at='2026-01-01',updated_at='2026-01-02'")
    client=a.app.test_client()
    with client.session_transaction() as state:
        state.update(user_id="qa-admin-read",user_role="ADMIN",membership="ADMIN")
    before=snapshot(db)
    writes=observe_business_writes(monkeypatch)
    for method in ("GET","HEAD","GET"):
        response=client.open("/api/telegram/auto-posts",method=method)
        assert response.status_code==200
        assert snapshot(db)==before
        assert not writes,writes
    payload=response.get_json()
    assert payload["prepared"][0]["target_key"]=="qa-alert-match"
    assert payload["saved"][0]["status"]=="SENT"


def test_live_diagnostic_get_cannot_force_provider_sync(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    calls=[]
    monkeypatch.setattr(a,"ensure_client_live_fresh",lambda **kw:calls.append(kw) or {})
    client=a.app.test_client()
    with client.session_transaction() as state:
        state.update(user_id="qa-admin-read",user_role="ADMIN",membership="ADMIN")
    for value in ("1","true","yes","on"):
        assert client.get("/api/live/diagnostics?refresh="+value).status_code==405
    assert calls==[]
    assert client.get("/api/live/diagnostics").status_code==200
    assert calls==[{"force":False}]


def test_telegram_writes_remain_explicit_and_reads_preserve_admin_choice(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    monkeypatch.setattr(a,"telegram_env_should_enable",lambda: True)
    assert a._telegram_sync_env_on_startup()["settings"]["enabled"] is True
    updated=a.update_telegram_settings({"enabled":False,"auto_daily_picks":False})
    assert updated["enabled"] is False and updated["auto_daily_picks"] is False
    before=snapshot(db)
    assert a.get_telegram_settings()==updated
    assert snapshot(db)==before


def test_cold_telegram_settings_read_does_not_create_schema(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("DROP TABLE telegram_settings")
    assert a.get_telegram_settings()["enabled"] is False
    assert not a.db_table_exists("telegram_settings")


@pytest.mark.parametrize("plan", ["ANONYMOUS","FREE","PRO","ELITE","ADMIN","EXPIRED"])
def test_legacy_shark_summary_is_private_plan_scoped_and_readonly(app_module,monkeypatch,tmp_path,plan):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    effective="FREE" if plan in {"ANONYMOUS","EXPIRED"} else plan
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET role=?,membership=?,membership_expires_at=? WHERE id=?",
                     (effective,effective,"2020-01-01" if plan=="EXPIRED" else "2030-01-01","qa-read-client"))
    recommendations=[{"id":"qa-rec-"+tier,"membership_required":tier,"selection":"QA_CORE_SECRET_"+tier}
                     for tier in ("FREE","PRO","ELITE")]
    monkeypatch.setattr(a,"v566_template_recommendations",lambda **kw:recommendations)
    client=a.app.test_client()
    if plan!="ANONYMOUS":
        with client.session_transaction() as state:
            state.update(user_id="qa-read-client",user_role=effective,membership=effective,user_membership=effective)
    before=snapshot(db)
    writes=observe_business_writes(monkeypatch)
    for method in ("GET","HEAD","GET"):
        response=client.open("/api/shark/core-summary?public=1&membership=ADMIN&user_id=other",method=method)
        assert response.status_code==(401 if plan=="ANONYMOUS" else 200)
        assert snapshot(db)==before
        assert not writes,writes
    if plan=="ANONYMOUS":
        assert "QA_CORE_SECRET" not in response.get_data(as_text=True)
        return
    data=response.get_json()["shark"]
    body=response.get_data(as_text=True)
    for tier in ("FREE","PRO","ELITE"):
        assert ("QA_CORE_SECRET_"+tier in body)==a.membership_allows(effective,tier)
    assert set(data["user"]) <= {"name","membership"}


@pytest.mark.parametrize("path", ["/shark-core","/inteligencia"])
def test_legacy_shark_pages_do_not_record_business_memory(app_module,monkeypatch,tmp_path,path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    client=a.app.test_client()
    with client.session_transaction() as state:
        state.update(user_id="qa-read-client",user_role="FREE",membership="FREE")
    before=snapshot(db)
    writes=observe_business_writes(monkeypatch)
    response=client.get(path)
    assert response.status_code==200
    assert snapshot(db)==before
    assert not writes,writes


@pytest.mark.parametrize("plan", ["ANONYMOUS","FREE","PRO","ELITE","ADMIN","EXPIRED"])
def test_track_record_does_not_disclose_pending_payloads_or_locked_selections(app_module,monkeypatch,tmp_path,plan):
    import json
    from engines.pick_grading_engine import ensure_pick_grading_schema
    a,db=isolated(app_module,monkeypatch,tmp_path)
    ensure_pick_grading_schema(db)
    effective="FREE" if plan in {"ANONYMOUS","EXPIRED"} else plan
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET role=?,membership=?,membership_expires_at=? WHERE id=?",
                     (effective,effective,"2020-01-01" if plan=="EXPIRED" else "2030-01-01","qa-read-client"))
        for tier in ("FREE","PRO","ELITE","DRAFT"):
            identifier="qa-track-"+tier
            conn.execute("""INSERT INTO picks(id,home_team,away_team,selection,status,membership_required)
                VALUES(?,?,?,?,?,?)""",(identifier,"QA Home","QA Away","QA_TRACK_SELECTION_"+tier,
                    "draft" if tier=="DRAFT" else "won","FREE" if tier=="DRAFT" else tier))
            conn.execute("""INSERT INTO pick_grading_results
                (id,pick_id,result_status,odds,stake,profit,payload_json,graded_at)
                VALUES(?,?,?,?,?,?,?,?)""",(identifier,identifier,"won",2,1,1,
                    json.dumps({"pick":{"selection":"QA_TRACK_SELECTION_"+tier,"reasoning":"QA_INTERNAL_PAYLOAD"}}),"2026-09-01"))
        conn.execute("""INSERT INTO pick_grading_results(id,pick_id,result_status,payload_json,graded_at)
            VALUES('pending','qa-pending','pending','QA_PENDING_PRIVATE','2026-09-01')""")
    client=a.app.test_client()
    if plan!="ANONYMOUS":
        with client.session_transaction() as state:
            state.update(user_id="qa-read-client",user_role=effective,membership=effective)
    before=snapshot(db)
    for route in ("/api/track-record?membership=ADMIN","/track-record"):
        response=client.get(route)
        assert response.status_code==200
        body=response.get_data(as_text=True)
        if plan!="ADMIN":
            for marker in ("QA_PENDING_PRIVATE","QA_INTERNAL_PAYLOAD","QA_TRACK_SELECTION_DRAFT"):
                assert marker not in body
            for tier in ("FREE","PRO","ELITE"):
                assert ("QA_TRACK_SELECTION_"+tier in body)==a.membership_allows(effective,tier)
        assert snapshot(db)==before

def test_expired_membership_is_effective_free_without_persisting(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    before=snapshot(db)
    c=a.app.test_client()
    with c.session_transaction() as state:
        state.update(user_id="qa-read-client",user_role="PRO",membership="PRO",user_membership="PRO",
                     membership_expires_at="2020-01-01T00:00:00+00:00",user_name="QA")
    response=c.get("/profile")
    assert response.status_code==200
    with c.session_transaction() as state:
        assert state["membership"]=="FREE"
    assert snapshot(db)==before

@pytest.mark.parametrize("plan", ["FREE", "PRO", "ELITE"])
def test_canonical_client_gets_do_not_mutate_business_tables(app_module,monkeypatch,tmp_path,plan):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET role=?,membership=?,membership_expires_at=? WHERE id=?",
                     (plan,plan,"2030-01-01T00:00:00+00:00","qa-read-client"))
    monkeypatch.setattr(a,"get_public_home_sports_summary",lambda:{
        "storage_status":"ok","valid_matches_today_count":0,"valid_matches_today":[],
        "valid_live_events":[],"valid_upcoming_matches":[],"valid_active_picks":[],"all_picks":[]})
    c=a.app.test_client()
    with c.session_transaction() as state:
        state.update(user_id="qa-read-client",user_role=plan,membership=plan,user_membership=plan,
                     membership_expires_at="2030-01-01T00:00:00+00:00",user_name="QA")
    before=snapshot(db)
    writes=observe_business_writes(monkeypatch)
    for route in CLIENT_ROUTES:
        response=c.get(route)
        assert response.status_code == 200,(route,response.status_code)
        assert snapshot(db)==before, (plan,route)
        assert not writes, (plan,route,writes)

def test_canonical_admin_gets_do_not_mutate_business_tables(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    monkeypatch.setattr(a,"get_public_home_sports_summary",lambda:{
        "storage_status":"ok","valid_matches_today_count":0,"valid_matches_today":[],
        "valid_live_events":[],"valid_upcoming_matches":[],"valid_active_picks":[],"all_picks":[]})
    c=a.app.test_client()
    with c.session_transaction() as state:
        state.update(user_id="qa-admin-read",user_role="ADMIN",membership="ADMIN",user_membership="ADMIN",user_name="QA Admin")
    before=snapshot(db)
    writes=observe_business_writes(monkeypatch)
    for route in ADMIN_ROUTES:
        response=c.get(route)
        if route == "/admin/shark-center":
            assert response.status_code == 302
            assert response.location == "/admin/dashboard#master-ai-title"
            response=c.get(response.location)
        assert response.status_code == 200,(route,response.status_code)
        assert snapshot(db)==before, route
        assert not writes, (route,writes)


@pytest.mark.parametrize("state", ["missing", "expired", "valid", "linked"])
def test_telegram_reads_never_issue_or_rotate_codes(app_module,monkeypatch,tmp_path,state):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    code = "NSQAEXISTING" if state != "missing" else ""
    expiry = "2020-01-01T00:00:00+00:00" if state == "expired" else "2030-01-01T00:00:00+00:00"
    with sqlite3.connect(db) as conn:
        conn.execute("""UPDATE users SET telegram_link_code=?,telegram_link_expires_at=?,
                        telegram_link_expires=?,telegram_chat_id=? WHERE id=?""",
                     (code,expiry,expiry,"qa-chat" if state == "linked" else "","qa-read-client"))
    def forbidden(*args, **kwargs):
        pytest.fail("A read attempted to generate a Telegram linking code")
    monkeypatch.setattr(a,"generate_telegram_link_code",forbidden)
    client=a.app.test_client()
    with client.session_transaction() as session:
        session.update(user_id="qa-read-client",user_role="PRO",membership="PRO")
    before=snapshot(db)
    for _ in range(2):
        for route in ("/profile","/telegram","/api/telegram/link-status"):
            response=client.get(route)
            assert response.status_code == 200
            assert snapshot(db)==before, route
        result=response.get_json()["telegram_state"]
        assert result["code"] == (code if state == "valid" else "")
        assert bool(result["deep_link"]) == (state == "valid")
        assert result["linked"] == (state == "linked")


def test_link_code_requires_authenticated_csrf_post_and_survives_reads(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    # Exercise normal HTTP permissions against this disposable DB. LOCAL SAFE's
    # additional commercial-action prohibition remains independently verified.
    monkeypatch.setenv("NEMESIS_LOCAL_SAFE_MODE","0")
    monkeypatch.setattr(a,"NEMESIS_LOCAL_SAFE_MODE",False)
    client=a.app.test_client()
    before=snapshot(db)
    path="/telegram/regenerar-código"
    assert client.get(path).status_code == 405
    assert client.post(path).status_code == 403
    with client.session_transaction() as session:
        session["csrf_token"]="qa-link-csrf"
    assert client.post(path,data={"csrf_token":"qa-link-csrf"}).status_code == 302
    assert snapshot(db)==before
    with client.session_transaction() as session:
        session.update(user_id="qa-read-client",user_role="PRO",membership="PRO")
    assert client.post(path,data={"csrf_token":"wrong"}).status_code == 403
    assert snapshot(db)==before
    response=client.post(path,data={"csrf_token":"qa-link-csrf","user_id":"another-user"})
    assert response.status_code == 302 and response.location == "/telegram"
    with sqlite3.connect(db) as conn:
        rows=conn.execute("SELECT id,telegram_link_code,telegram_link_expires_at FROM users").fetchall()
    generated=next(row for row in rows if row[0]=="qa-read-client")
    assert generated[1].startswith("NS") and not a.telegram_code_expired(generated[2])
    assert all(not row[1] for row in rows if row[0]!="qa-read-client")
    after=snapshot(db)
    assert client.get("/telegram").status_code == 200
    assert client.get("/profile").status_code == 200
    assert client.get("/api/telegram/link-status").get_json()["telegram_state"]["code"] == generated[1]
    assert snapshot(db)==after


def test_autopilot_stored_evidence_is_not_current_certification(tmp_path):
    import json
    from engines.sentinel_autopilot_engine import read_autopilot_summary
    empty=read_autopilot_summary(tmp_path)
    assert not empty["evidence_available"] and empty["score"] is None
    path=tmp_path/"data/runtime/sentinel_autopilot_memory.json"
    assert not path.exists()
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"updated_at_madrid":"2026-09-20T21:00:00+02:00",
        "last_scan":{"version":"qa-previous-revision","score":0},
        "issues":[{"issue_id":"QA-RESOLVED","status":"resolved"},
                  {"issue_id":"QA-OPEN","status":"open","severity":"high"}],"tasks":[]}),encoding="utf-8")
    before=path.read_bytes()
    for _ in range(2):
        result=read_autopilot_summary(tmp_path)
        assert result["score"] == 0 and result["evidence_available"]
        assert result["version"] == "qa-previous-revision"
        assert result["status"] == "STORED_DIAGNOSTIC"
        assert result["render_local_aligned"] is None
        assert [i["issue_id"] for i in result["issues"]] == ["QA-OPEN"]
        assert result["priority_matrix"]["counts"]["high"] == 1
    assert path.read_bytes()==before


def test_autopilot_execution_remains_explicit_admin_csrf_post(app_module,monkeypatch,tmp_path):
    a,_=isolated(app_module,monkeypatch,tmp_path)
    calls=[]
    monkeypatch.setattr(a,"_v888_build_autopilot_scan",lambda **kwargs: calls.append(kwargs) or {"status":"QA_ONLY"})
    client=a.app.test_client()
    path="/api/admin/sentinel-autopilot/run"
    assert client.get(path).status_code == 405
    assert client.post(path).status_code == 403
    with client.session_transaction() as session:
        session.update(user_id="qa-read-client",user_role="PRO",membership="PRO",csrf_token="qa-only-csrf")
    assert client.post(path,headers={"X-CSRF-Token":"qa-only-csrf"}).status_code == 403
    with client.session_transaction() as session:
        session.update(user_id="qa-admin-read",user_role="ADMIN",membership="ADMIN")
    assert client.post(path,headers={"X-CSRF-Token":"bad"}).status_code == 403
    assert not calls
    assert client.post(path,headers={"X-CSRF-Token":"qa-only-csrf"}).status_code == 200
    assert calls == [{"save_memory":True,"mode":"quick"}]


def test_local_safe_keeps_telegram_mutations_blocked(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    monkeypatch.setenv("NEMESIS_LOCAL_SAFE_MODE","1")
    monkeypatch.setattr(a,"NEMESIS_LOCAL_SAFE_MODE",True)
    monkeypatch.setattr(a,"LOCAL_SAFE_DATA_DIR",tmp_path)
    client=a.app.test_client()
    with client.session_transaction() as session:
        session.update(user_id="qa-read-client",user_role="PRO",membership="PRO",csrf_token="qa-link-csrf")
    before=snapshot(db)
    response=client.post("/telegram/regenerar-código",data={"csrf_token":"qa-link-csrf"})
    assert response.status_code == 403
    assert snapshot(db)==before

def test_daily_master_is_membership_persistence_owner(app_module,monkeypatch):
    a=app_module
    seen=[]
    monkeypatch.setattr(a,"expire_user_memberships_if_needed",lambda *_a,**_k: seen.append("expiry") or True)
    monkeypatch.setattr(a,"ensure_client_match_lifecycle_fresh",lambda *_a,**_k: {"ok":True})
    monkeypatch.setattr(a,"run_pick_grading",lambda *_a,**_k: {"ok":True})
    monkeypatch.setattr(a,"v742_track_record_context",lambda: {"ok":True})
    result=a.v818_daily_close_previous_day()
    assert result["ok"] is True
    assert seen==["expiry"]
    assert result["membership_expiry"]["ok"] is True


def test_telegram_state_read_is_pure_and_generation_is_explicit(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    user=a.get_user_by_id("qa-read-client")
    before=snapshot(db)
    state=a.telegram_user_state(user)
    assert state["linked"] is False
    assert state["code"]==""
    assert state["generation_requires_post"] is True
    assert snapshot(db)==before

    code=a.generate_telegram_link_code("qa-read-client")
    assert code and code.startswith("NS")
    assert snapshot(db)!=before


def test_telegram_regenerate_get_is_method_not_allowed_and_read_only(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    client=a.app.test_client()
    with client.session_transaction() as state:
        state.update(user_id="qa-read-client",user_role="PRO",membership="PRO",user_membership="PRO",
                     membership_expires_at="2030-01-01T00:00:00+00:00",user_name="QA")
    before=snapshot(db)
    response=client.get("/telegram/regenerar-código")
    assert response.status_code==405
    assert snapshot(db)==before

@pytest.mark.parametrize("route", ["/admin/sentinel-autopilot", "/api/admin/sentinel-autopilot/summary",
    "/api/admin/sentinel-autopilot/issues", "/api/admin/sentinel-autopilot/tasks",
    "/api/admin/sentinel-autopilot/generate-prompt"])
def test_autopilot_navigation_does_not_start_diagnostics(app_module,monkeypatch,tmp_path,route):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    def forbidden(*args,**kwargs):
        pytest.fail("Opening AutoPilot started diagnostics")
    monkeypatch.setattr(a,"_v888_build_autopilot_scan",forbidden)
    client=a.app.test_client()
    with client.session_transaction() as session:
        session.update(user_id="qa-admin-read",user_role="ADMIN",membership="ADMIN")
    before=snapshot(db)
    assert client.get(route).status_code == 200
    assert snapshot(db)==before


@pytest.mark.parametrize('route', ['/api/shark/context', '/api/shark/briefing'])
@pytest.mark.parametrize('plan', ['ANONYMOUS','FREE','PRO','ELITE','ADMIN','EXPIRED'])
def test_shark_context_is_private_plan_scoped_and_read_only(app_module,monkeypatch,tmp_path,plan,route):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    effective='FREE' if plan in {'ANONYMOUS','EXPIRED'} else plan
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET role=?,membership=?,membership_expires_at=? WHERE id=?",
                     ('PRO' if plan=='EXPIRED' else effective,'PRO' if plan=='EXPIRED' else effective,
                      '2020-01-01' if plan=='EXPIRED' else '2030-01-01','qa-read-client'))
        for tier in ('FREE','PRO','ELITE'):
            conn.execute("""INSERT INTO picks
                (id,home_team,away_team,market,selection,reasoning,status,membership_required,odds,match_date,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                ('qa-context-'+tier,'QA Home','QA Away','1x2','QA_SELECTION_'+tier,
                 'QA_ANALYSIS_'+tier,'published',tier,1.8,a.today_iso(),a.now_iso()))
        conn.execute("INSERT INTO picks(id,selection,reasoning,status,membership_required) VALUES(?,?,?,?,?)",
                     ('qa-context-draft','QA_DRAFT_SELECTION','QA_DRAFT_REASON','draft','FREE'))
        conn.execute("INSERT OR REPLACE INTO client_profiles(id,name,membership_plan) VALUES(?,?,?)",
                     ('default','QA_OTHER_PERSON_PROFILE','ELITE'))
    # Both briefing collections deliberately contain all tiers and a draft.
    # Only the upstream cache is substituted; authorization and SQL are real.
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        picks=[dict(row) for row in conn.execute("SELECT * FROM picks WHERE id LIKE 'qa-context-%'")]
    monkeypatch.setattr(a,'get_public_home_sports_summary',lambda:{
        'storage_status':'ok','valid_matches_today':[], 'valid_live_events':[],
        'valid_upcoming_matches':[], 'all_picks':picks,'valid_active_picks':picks})
    client=a.app.test_client()
    if plan!='ANONYMOUS':
        with client.session_transaction() as state:
            state.update(user_id='qa-read-client',user_role='PRO' if plan=='EXPIRED' else effective,
                         membership='PRO' if plan=='EXPIRED' else effective,user_name='QA')
    before=snapshot(db)
    writes=observe_business_writes(monkeypatch)
    for _ in range(2):
        response=client.get(route+'?membership=ADMIN&user_id=other&admin=1')
        assert response.status_code == (401 if plan=='ANONYMOUS' else 200)
        body=response.get_data(as_text=True)
        assert 'QA_OTHER_PERSON_PROFILE' not in body
        assert 'QA_DRAFT_SELECTION' not in body and 'QA_DRAFT_REASON' not in body
        allowed={'ANONYMOUS':(),'FREE':('FREE',),'EXPIRED':('FREE',),
                 'PRO':('FREE','PRO'),'ELITE':('FREE','PRO','ELITE'),'ADMIN':('FREE','PRO','ELITE')}[plan]
        for tier in ('FREE','PRO','ELITE'):
            assert ('QA_ANALYSIS_'+tier in body) == (tier in allowed)
        if plan!='ANONYMOUS':
            result=response.get_json()
            if route=='/api/shark/context':
                assert result['snapshot_id'] is None
                context=result['context']
            else:
                context=result['briefing']['context']
            assert context['profile']['plan']==effective
        assert snapshot(db)==before
        assert not writes,writes


def test_shark_context_get_does_not_append_snapshots(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    client=a.app.test_client()
    with client.session_transaction() as state:
        state.update(user_id='qa-read-client',user_role='FREE',membership='FREE')
    before=snapshot(db)
    writes=observe_business_writes(monkeypatch)
    for _ in range(2):
        assert client.get('/api/shark/context').status_code==200
        assert not writes,writes
        assert snapshot(db)==before


@pytest.mark.parametrize('route', ['/api/profile','/api/membership','/api/shark/briefing'])
@pytest.mark.parametrize('plan', ['ANONYMOUS','FREE','PRO','ELITE'])
def test_client_read_apis_never_disclose_legacy_global_profile(app_module,monkeypatch,tmp_path,route,plan):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET role=?,membership=?,membership_expires_at='2030-01-01' WHERE id=?",
                     (plan,plan,'qa-read-client'))
        conn.execute("""INSERT OR REPLACE INTO client_profiles
            (id,name,membership_plan,telegram_chat_id,preferences_json)
            VALUES(?,?,?,?,?)""",('default','QA_LEGACY_PRIVATE_NAME','ELITE','QA_PRIVATE_CHAT','{"focus":"QA_PRIVATE_FOCUS"}'))
    client=a.app.test_client()
    if plan!='ANONYMOUS':
        with client.session_transaction() as state:
            state.update(user_id='qa-read-client',user_role=plan,membership=plan,user_name='QA')
    before=snapshot(db)
    for _ in range(2):
        response=client.get(route)
        expected=401 if plan=='ANONYMOUS' and route!='/api/membership' else 200
        assert response.status_code==expected
        body=response.get_data(as_text=True)
        assert all(value not in body for value in ('QA_LEGACY_PRIVATE_NAME','QA_PRIVATE_CHAT','QA_PRIVATE_FOCUS'))
        if expected==200 and plan!='ANONYMOUS':
            payload=response.get_json()
            profile=payload['briefing']['profile'] if route=='/api/shark/briefing' else payload['profile']
            assert profile['membership_plan']==plan
        assert snapshot(db)==before


@pytest.mark.parametrize('surface', ['detail','depth','html'])
@pytest.mark.parametrize('plan', ['ANONYMOUS','FREE','PRO','ELITE','ADMIN','EXPIRED'])
def test_match_read_surfaces_never_bypass_pick_entitlements(app_module,monkeypatch,tmp_path,surface,plan):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    effective='FREE' if plan in {'ANONYMOUS','EXPIRED'} else plan
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET role=?,membership=?,membership_expires_at=? WHERE id=?",
                     ('PRO' if plan=='EXPIRED' else effective,'PRO' if plan=='EXPIRED' else effective,
                      '2020-01-01' if plan=='EXPIRED' else '2030-01-01','qa-read-client'))
        conn.execute("""INSERT INTO matches(id,home_team,away_team,competition_name,match_date,
            kickoff_time,status,source) VALUES(?,?,?,?,?,?,?,?)""",
                     ('qa-entitlement-match','QA Norte','QA Sur','QA Competition',a.today_iso(),'20:00','NS','SIMULATED_QA'))
        for tier in ('FREE','PRO','ELITE'):
            conn.execute("""INSERT INTO picks(id,match_id,home_team,away_team,selection,reasoning,
                status,membership_required,market,odds,match_date,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                ('qa-entitlement-'+tier,'qa-entitlement-match','QA Norte','QA Sur','QA_PICK_'+tier,
                 'QA_REASON_'+tier,'published',tier,'1x2',1.8,a.today_iso(),a.now_iso()))
        conn.execute("INSERT INTO picks(id,match_id,selection,reasoning,status,membership_required) VALUES(?,?,?,?,?,?)",
                     ('qa-entitlement-draft','qa-entitlement-match','QA_DRAFT_PRIVATE','QA_DRAFT_REASON','draft','FREE'))
        conn.execute("INSERT OR REPLACE INTO client_profiles(id,name,membership_plan) VALUES(?,?,?)",
                     ('default','QA_UNRELATED_PROFILE','ELITE'))
    client=a.app.test_client()
    if plan!='ANONYMOUS':
        with client.session_transaction() as state:
            state.update(user_id='qa-read-client',user_role='PRO' if plan=='EXPIRED' else effective,
                         membership='PRO' if plan=='EXPIRED' else effective)
    route='/match/qa-entitlement-match' if surface=='html' else '/api/matches/qa-entitlement-match/'+surface
    before=snapshot(db)
    writes=observe_business_writes(monkeypatch)
    response=client.get(route+'?membership=ADMIN&include_admin=true')
    assert response.status_code==200
    body=response.get_data(as_text=True)
    assert 'QA_DRAFT_PRIVATE' not in body and 'QA_DRAFT_REASON' not in body
    assert 'QA_UNRELATED_PROFILE' not in body
    allowed={'FREE':('FREE',),'PRO':('FREE','PRO'),'ELITE':('FREE','PRO','ELITE'),
             'ADMIN':('FREE','PRO','ELITE')}[effective]
    for tier in ('FREE','PRO','ELITE'):
        if tier not in allowed:
            assert 'QA_PICK_'+tier not in body and 'QA_REASON_'+tier not in body
        elif surface!='html':
            assert 'QA_PICK_'+tier in body
    assert snapshot(db)==before
    assert not writes,writes


def test_client_activity_hides_internal_growth_funnel_without_mutating(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    with sqlite3.connect(db) as conn:
        conn.executemany("""INSERT INTO user_activity
            (id,user_id,activity_type,target_type,target_id,payload_json,created_at)
            VALUES(?,?,?,?,?,?,?)""",[
            ("qa-growth","qa-read-client","growth_first_value","growth_funnel","match-1","{}","2026-09-27T10:00:00+00:00"),
            ("qa-visible","qa-read-client","favorite","favorite","team:qa","{}","2026-09-27T11:00:00+00:00"),
        ])
    before=snapshot(db)
    visible=a.client_activity_feed(limit=20,user_id="qa-read-client")
    assert [item["id"] for item in visible]==["qa-visible"]
    assert visible[0]["label"]=="Favorito actualizado."
    internal=a.client_activity_feed(limit=20,user_id="qa-read-client",include_internal=True)
    assert [item["id"] for item in internal]==["qa-visible","qa-growth"]
    assert snapshot(db)==before


def test_activity_templates_state_navigation_is_not_logged():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    activity=(root/"templates/activity.html").read_text(encoding="utf-8")
    account=(root/"templates/account_center.html").read_text(encoding="utf-8")
    assert "Abrir una pantalla no crea un registro de navegación" in activity
    assert "La navegación normal no se registra en este historial" in activity
    assert "Abrir páginas o consultar pronósticos no añade un registro de navegación" in account
    assert "item.target_type or item.activity_type" not in account


def test_account_center_reflects_existing_telegram_link_without_generating_code(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("""UPDATE users
                       SET telegram_chat_id='qa-chat',telegram_username='qa_user',
                           telegram_link_code='',telegram_link_expires_at=''
                       WHERE id='qa-read-client'""")
    client=a.app.test_client()
    with client.session_transaction() as state:
        state.update(user_id="qa-read-client",user_role="PRO",membership="PRO",user_membership="PRO",user_name="QA")
    before=snapshot(db)
    response=client.get("/mi-cuenta")
    assert response.status_code==200
    body=response.get_data(as_text=True)
    assert "Vinculado" in body
    assert "@qa_user" in body
    assert snapshot(db)==before


@pytest.mark.parametrize("plan,source,granted,stripe_status,expected",[
    ("FREE","free_signup",0,"","Plan gratuito"),
    ("PRO","admin_manual",1,"","Acceso concedido"),
    ("ELITE","stripe",0,"active","Suscripción: Activa"),
])
def test_account_center_explains_real_plan_origin(app_module,monkeypatch,tmp_path,plan,source,granted,stripe_status,expected):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("""UPDATE users
                       SET role=?,membership=?,membership_source=?,membership_admin_granted=?,
                           membership_expires_at='2030-01-01T00:00:00+00:00',
                           stripe_customer_id=?,stripe_subscription_status=?,
                           stripe_current_period_end=?
                       WHERE id='qa-read-client'""",
                    (plan,plan,source,granted,
                     "cus_qa" if stripe_status else "",
                     stripe_status,
                     "2030-01-01T00:00:00+00:00" if stripe_status else ""))
    client=a.app.test_client()
    with client.session_transaction() as state:
        state.update(user_id="qa-read-client",user_role=plan,membership=plan,user_membership=plan,user_name="QA")
    before=snapshot(db)
    response=client.get("/mi-cuenta")
    assert response.status_code==200
    import re
    visible = re.sub(r'<[^>]+>', '', response.get_data(as_text=True))
    assert expected in visible
    assert snapshot(db)==before
