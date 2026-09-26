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
    monkeypatch.setattr(app.sqlite3,"connect",lambda *_a,**_k: DummyConn())
    response=client.post("/api/automation/data-backup/run",headers={"X-Automation-Secret":"backup-test-secret"})
    payload=response.get_json()
    assert response.status_code==200
    assert payload["status"]=="SKIPPED_ALREADY_RUNNING"
    assert payload["backup_created"] is False
