"""V941 backup is a master-cron subflow with durable day dedupe."""
import pytest

def _client(monkeypatch):
    import app
    monkeypatch.setenv("AUTOMATION_SECRET","backup-test-secret")
    monkeypatch.setenv("DATA_BACKUP_ENABLED","1")
    return app, app.app.test_client()

def test_backup_endpoint_skips_when_success_already_recorded_today(monkeypatch):
    app,client=_client(monkeypatch)
    today=app.today_iso()
    monkeypatch.setattr(app,"automation_get",lambda key,default=None: {"time":today+"T03:00:00+02:00","result":{"ok":True,"backup_created":True}} if key=="last_successful_data_backup_call" else (default or {}))
    monkeypatch.setattr(app,"create_sqlite_backup",lambda *_a,**_k: pytest.fail("backup must not run twice"))
    monkeypatch.setattr(app,"automation_safe_set",lambda *_a,**_k: None)
    response=client.post("/api/automation/data-backup/run",headers={"X-Automation-Secret":"backup-test-secret"})
    payload=response.get_json()
    assert response.status_code==200
    assert payload["status"]=="SKIPPED_ALREADY_DONE"
    assert payload["backup_created"] is False

def test_backup_endpoint_uses_atomic_claim_before_copy(monkeypatch):
    app,client=_client(monkeypatch)
    monkeypatch.setattr(app,"automation_get",lambda *_a,**_k: {})
    monkeypatch.setattr(app,"ensure_automation_schema_conn",lambda conn: None)
    monkeypatch.setattr(app,"v818_claim_dedupe",lambda conn,job,key,ttl_hours=1: False)
    monkeypatch.setattr(app,"create_sqlite_backup",lambda *_a,**_k: pytest.fail("copy must wait for claim"))
    monkeypatch.setattr(app,"automation_safe_set",lambda *_a,**_k: None)
    class DummyConn:
        def __enter__(self): return self
        def __exit__(self,*_): return False
        def commit(self): return None
        def close(self): return None
    monkeypatch.setattr(app.sqlite3,"connect",lambda *_a,**_k: DummyConn())
    response=client.post("/api/automation/data-backup/run",headers={"X-Automation-Secret":"backup-test-secret"})
    payload=response.get_json()
    assert response.status_code==200
    assert payload["status"]=="SKIPPED_ALREADY_RUNNING"
    assert payload["backup_created"] is False


def test_backup_endpoint_commits_claim_before_copy(monkeypatch):
    app,client=_client(monkeypatch)
    events=[]
    monkeypatch.setattr(app,"automation_get",lambda *_a,**_k: {})
    monkeypatch.setattr(app,"ensure_automation_schema_conn",lambda conn: events.append("schema"))
    monkeypatch.setattr(app,"v818_claim_dedupe",lambda conn,job,key,ttl_hours=1: events.append("claim") or True)
    monkeypatch.setattr(app,"automation_safe_set",lambda *_a,**_k: None)
    class DummyConn:
        def commit(self): events.append("commit")
        def close(self): events.append("close")
    monkeypatch.setattr(app.sqlite3,"connect",lambda *_a,**_k: DummyConn())
    def copy(*_a,**_k):
        assert "commit" in events
        assert events.index("commit") < events.index("close")
        events.append("copy")
        return {"ok":True,"backup_created":True,"status":"PASS"}
    monkeypatch.setattr(app,"create_sqlite_backup",copy)
    response=client.post("/api/automation/data-backup/run",headers={"X-Automation-Secret":"backup-test-secret"})
    assert response.status_code==200
    assert response.get_json()["backup_created"] is True
    assert events[:4]==["schema","claim","commit","close"]
    assert events[-1]=="copy"


def test_backup_endpoint_exposes_only_safe_failure_classification(monkeypatch):
    app,client=_client(monkeypatch)
    monkeypatch.setattr(app,"automation_get",lambda *_a,**_k: {})
    monkeypatch.setattr(app,"ensure_automation_schema_conn",lambda conn: None)
    monkeypatch.setattr(app,"v818_claim_dedupe",lambda conn,job,key,ttl_hours=1: True)
    monkeypatch.setattr(app,"automation_safe_set",lambda *_a,**_k: None)
    class DummyConn:
        def commit(self): return None
        def close(self): return None
    monkeypatch.setattr(app.sqlite3,"connect",lambda *_a,**_k: DummyConn())
    monkeypatch.setattr(app,"create_sqlite_backup",lambda *_a,**_k: {
        "ok":False,"backup_created":False,"error":"database or disk is full"
    })
    response=client.post("/api/automation/data-backup/run",headers={"X-Automation-Secret":"backup-test-secret"})
    payload=response.get_json()
    assert response.status_code==200
    assert payload["ok"] is False
    assert payload["backup_created"] is False
    assert payload["error_code"]=="STORAGE_FULL"
