"""V941 GET safety: canonical reads do not persist business-state changes."""
from __future__ import annotations
import sqlite3
import pytest

BUSINESS_TABLES=(
    "users","matches","picks","favorites","telegram_queue",
    "subscription_accounts","stripe_subscriptions","revenue_daily_metrics",
    "client_profiles","payment_readiness_daily","settings",
    "telegram_subscribers","payment_webhook_events","subscription_events",
)
CLIENT_ROUTES=("/app","/calendar","/live","/picks","/track-record","/shark","/telegram","/profile","/memberships")
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
