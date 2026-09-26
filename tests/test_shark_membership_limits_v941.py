"""V941 SHARK plan limits: no anonymous or direct-API bypass."""
import sqlite3


def test_free_daily_limit_is_consumed_atomically(app_module,tmp_path,monkeypatch):
    path=str(tmp_path/"shark-limit.sqlite")
    con=sqlite3.connect(path)
    con.execute("CREATE TABLE shark_memory(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT,event_type TEXT,context_json TEXT,created_at TEXT)")
    con.commit(); con.close()
    monkeypatch.setattr(app_module,"db",lambda: sqlite3.connect(path))
    monkeypatch.setattr(app_module,"ensure_shark_memory_table",lambda: None)
    monkeypatch.setattr(app_module,"today_iso",lambda: "2026-09-26")
    monkeypatch.setattr(app_module,"now_iso",lambda: "2026-09-26T12:00:00+02:00")
    user={"id":"qa-free-shark","membership":"FREE","role":"FREE"}
    assert [app_module.consume_shark_question(user)["allowed"] for _ in range(3)] == [True,True,True]
    blocked=app_module.consume_shark_question(user)
    assert blocked["allowed"] is False and blocked["limit_reached"] is True
    assert blocked["used"]==3 and blocked["remaining"]==0
    con=sqlite3.connect(path)
    payloads=[row[0] for row in con.execute("SELECT context_json FROM shark_memory").fetchall()]
    con.close()
    assert len(payloads)==3
    assert all("prompt_stored" in value and "qa-free-shark" not in value for value in payloads)


def test_shark_api_requires_login(client,app_module,monkeypatch):
    monkeypatch.setattr(app_module,"shark_answer",lambda *_: (_ for _ in ()).throw(AssertionError("must not answer anonymously")))
    response=client.get("/api/shark/ask?q=calendario")
    assert response.status_code==401
    assert response.get_json()["login_required"] is True


def test_shark_api_blocks_exhausted_plan_before_answer(client,app_module,monkeypatch):
    csrf="qa-shark-limit-csrf"
    with client.session_transaction() as state:
        state.update(user_id="qa-shark-limit",user_role="FREE",membership="FREE",user_membership="FREE",user_name="QA",csrf_token=csrf)
    monkeypatch.setattr(app_module,"consume_shark_question",lambda user: {"allowed":False,"login_required":False,"membership":"FREE","limit":3,"used":3,"remaining":0,"limit_reached":True})
    monkeypatch.setattr(app_module,"shark_answer",lambda *_: (_ for _ in ()).throw(AssertionError("must not bypass limit")))
    response=client.post("/api/shark/ask",json={"question":"¿Qué pronóstico hay?"},headers={"X-CSRF-Token":csrf})
    assert response.status_code==429
    payload=response.get_json()
    assert payload["usage"]["limit_reached"] is True
    assert "plan=PRO" in payload["upgrade_url"]


def test_shark_api_returns_usage_when_allowed(client,app_module,monkeypatch):
    csrf="qa-shark-pro-csrf"
    with client.session_transaction() as state:
        state.update(user_id="qa-shark-pro",user_role="PRO",membership="PRO",user_membership="PRO",user_name="QA",csrf_token=csrf)
    monkeypatch.setattr(app_module,"consume_shark_question",lambda user: {"allowed":True,"login_required":False,"membership":"PRO","limit":20,"used":1,"remaining":19,"limit_reached":False})
    monkeypatch.setattr(app_module,"shark_answer",lambda q: {"answer":"QA","focus":"summary","context":{}})
    monkeypatch.setattr(app_module,"save_shark_context",lambda *_a,**_k: "qa")
    response=client.post("/api/shark/ask",json={"question":"estado"},headers={"X-CSRF-Token":csrf})
    assert response.status_code==200
    payload=response.get_json()
    assert payload["usage"]["remaining"]==19
    assert payload["shark"]["answer"]=="QA"


def test_shark_template_exposes_login_or_quota_state():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    text=(root/"templates/shark.html").read_text(encoding="utf-8")
    assert "Consultas SHARK hoy" in text
    assert "Inicia sesión" in text
    assert "shark_usage" in text


def test_shark_api_post_requires_csrf(client,app_module,monkeypatch):
    with client.session_transaction() as state:
        state.update(user_id="qa-shark-csrf",user_role="PRO",membership="PRO",user_membership="PRO",user_name="QA")
    monkeypatch.setattr(app_module,"consume_shark_question",lambda _user: (_ for _ in ()).throw(AssertionError("quota must not be consumed before CSRF")))
    response=client.post("/api/shark/ask",json={"question":"estado"},headers={"X-CSRF-Token":"qa-shark-csrf-pro"})
    assert response.status_code==403
    assert response.get_json()["error"]=="csrf_required"
