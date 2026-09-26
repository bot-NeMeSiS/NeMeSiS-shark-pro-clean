from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("render_cron_data_backup",ROOT/"tools/render_cron_data_backup.py")
backup=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(backup)

class Response:
    def __init__(self,payload,status=200): self.status=status; self.payload=payload
    def read(self,_limit=-1): return json.dumps(self.payload).encode()
    def __enter__(self): return self
    def __exit__(self,*_): return False

def test_backup_runner_uses_header_secret_and_post(monkeypatch,capsys):
    seen=[]
    monkeypatch.setenv("PUBLIC_BASE_URL","https://example.invalid")
    monkeypatch.setenv("AUTOMATION_SECRET","synthetic-secret")
    def open_(request,timeout):
        seen.append((request,timeout))
        return Response({"ok":True,"backup_created":True,"status":"OK"})
    monkeypatch.setattr(backup.urllib.request,"urlopen",open_)
    assert backup.main()==0
    payload=json.loads(capsys.readouterr().out)
    req,timeout=seen[0]
    assert payload["ok"] is True and payload["backup_created"] is True
    assert req.get_method()=="POST"
    assert req.full_url=="https://example.invalid/api/automation/data-backup/run"
    assert req.headers["X-automation-secret"]=="synthetic-secret"
    assert "synthetic-secret" not in json.dumps(payload)
    assert timeout==backup.TIMEOUT_SECONDS

@pytest.mark.parametrize("missing",["PUBLIC_BASE_URL","AUTOMATION_SECRET"])
def test_backup_runner_missing_config_never_calls_http(monkeypatch,capsys,missing):
    monkeypatch.setenv("PUBLIC_BASE_URL","https://example.invalid")
    monkeypatch.setenv("AUTOMATION_SECRET","synthetic")
    monkeypatch.delenv(missing,raising=False)
    monkeypatch.setattr(backup.urllib.request,"urlopen",lambda *_a,**_k: pytest.fail("HTTP must not run"))
    assert backup.main()==2
    assert json.loads(capsys.readouterr().out)["ok"] is False
