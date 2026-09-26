"""V941 GET safety: canonical reads do not persist business-state changes."""
from __future__ import annotations
import sqlite3

BUSINESS_TABLES=(
    "users","matches","picks","favorites","telegram_queue",
    "subscription_accounts","stripe_subscriptions","revenue_daily_metrics",
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
    try: a.ensure_subscription_schema(db)
    except Exception: pass
    try: a.ensure_stripe_schema(db)
    except Exception: pass
    with sqlite3.connect(db) as conn:
        conn.execute("""INSERT OR REPLACE INTO users
          (id,name,username,email,password_hash,role,membership,membership_source,membership_expires_at,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?)""",
          ("qa-read-client","QA","qa_read","qa-read@example.invalid","x","PRO","PRO","admin_manual","2020-01-01T00:00:00+00:00","2020-01-01"))
        conn.commit()
    return a,db

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

def test_canonical_client_gets_do_not_mutate_business_tables(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    monkeypatch.setattr(a,"get_public_home_sports_summary",lambda:{
        "storage_status":"ok","valid_matches_today_count":0,"valid_matches_today":[],
        "valid_live_events":[],"valid_upcoming_matches":[],"valid_active_picks":[],"all_picks":[]})
    c=a.app.test_client()
    with c.session_transaction() as state:
        state.update(user_id="qa-read-client",user_role="PRO",membership="PRO",user_membership="PRO",
                     membership_expires_at="2030-01-01T00:00:00+00:00",user_name="QA")
    before=snapshot(db)
    for route in CLIENT_ROUTES:
        response=c.get(route)
        assert response.status_code in (200,302),(route,response.status_code)
    assert snapshot(db)==before

def test_canonical_admin_gets_do_not_mutate_business_tables(app_module,monkeypatch,tmp_path):
    a,db=isolated(app_module,monkeypatch,tmp_path)
    monkeypatch.setattr(a,"get_public_home_sports_summary",lambda:{
        "storage_status":"ok","valid_matches_today_count":0,"valid_matches_today":[],
        "valid_live_events":[],"valid_upcoming_matches":[],"valid_active_picks":[],"all_picks":[]})
    c=a.app.test_client()
    with c.session_transaction() as state:
        state.update(user_id="qa-admin-read",user_role="ADMIN",membership="ADMIN",user_membership="ADMIN",user_name="QA Admin")
    before=snapshot(db)
    for route in ADMIN_ROUTES:
        response=c.get(route)
        assert response.status_code in (200,302),(route,response.status_code)
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
