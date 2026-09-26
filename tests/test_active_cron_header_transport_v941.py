"""V941 active cron transport: secrets only in headers; active runner posts."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_active_cron_query_secret_is_rejected(client,app_module,monkeypatch):
    monkeypatch.setenv("AUTOMATION_SECRET","qa-active-cron-secret")
    for path in (
        "/api/automation/telegram/tick?runner=render_cron&secret=qa-active-cron-secret",
        "/api/automation/data-backup/run?secret=qa-active-cron-secret",
        "/api/automation/continuous-evolution/tick?secret=qa-active-cron-secret",
    ):
        response=client.post(path,json={})
        assert response.status_code==403,(path,response.status_code)
        payload=response.get_json()
        assert payload["query_secret_accepted"] is False
        assert payload["automation_secret_provided"] is False

def test_active_cron_header_is_accepted_before_business_logic(client,app_module,monkeypatch):
    monkeypatch.setenv("AUTOMATION_SECRET","qa-active-cron-secret")
    monkeypatch.setenv("DATA_BACKUP_ENABLED","0")
    monkeypatch.setattr(app_module,"automation_cron_result",lambda *_a,**_k: app_module.jsonify({"ok":True,"status":"QA_HEADER_ACCEPTED"}))
    telegram=client.post("/api/automation/telegram/tick",json={},headers={"X-Automation-Secret":"qa-active-cron-secret","X-NeMeSiS-Cron-Runner":"render-cron"})
    assert telegram.status_code==200
    assert telegram.get_json()["status"]=="QA_HEADER_ACCEPTED"
    backup=client.post("/api/automation/data-backup/run",json={},headers={"X-Automation-Secret":"qa-active-cron-secret"})
    assert backup.status_code==200
    assert backup.get_json()["status"]=="DISABLED"

def test_active_runners_use_post_and_no_runner_query_parameter():
    master=(ROOT/"tools/render_cron_master_tick.py").read_text(encoding="utf-8")
    standalone=(ROOT/"tools/render_cron_telegram_tick.py").read_text(encoding="utf-8")
    assert 'TELEGRAM_ENDPOINT = "/api/automation/telegram/tick"' in master
    assert 'telegram/tick?runner=render_cron' not in master
    assert 'method="POST"' in master
    assert 'return f"{base}{ENDPOINT}"' in standalone
    assert '?runner=render_cron' not in standalone
    assert 'method="POST"' in standalone
    assert '"X-Automation-Secret": automation_secret' in standalone


def test_standalone_manual_runners_also_use_post():
    sports=(ROOT/"tools/render_cron_sports_sync.py").read_text(encoding="utf-8")
    highlights=(ROOT/"tools/render_cron_highlights_sync.py").read_text(encoding="utf-8")
    assert 'method="POST"' in sports and 'method="GET"' not in sports
    assert 'method="POST"' in highlights and 'method="GET"' not in highlights


def test_legacy_telegram_automation_posts_accept_header_secret_without_browser_csrf(client,app_module,monkeypatch):
    monkeypatch.setenv("AUTOMATION_SECRET","qa-legacy-telegram-secret")
    monkeypatch.setattr(app_module,"telegram_config",lambda: {"enabled":True})
    monkeypatch.setattr(app_module,"telegram_scheduler_delivery",lambda force=False: {"ok":True,"status":"QA_LEGACY_AUTO","force":bool(force)})
    monkeypatch.setattr(app_module,"telegram_scheduler_tick",lambda force=False: {"ok":True,"status":"QA_LEGACY_TICK","force":bool(force)})

    headers={"X-Automation-Secret":"qa-legacy-telegram-secret"}
    for path,expected in (
        ("/api/telegram/auto-run","QA_LEGACY_AUTO"),
        ("/api/v495/telegram-auto-run","QA_LEGACY_AUTO"),
        ("/api/telegram/scheduler-tick","QA_LEGACY_TICK"),
    ):
        response=client.post(path,json={},headers=headers)
        assert response.status_code==200,(path,response.status_code,response.get_data(as_text=True))
        assert response.get_json()["status"]==expected


def test_legacy_telegram_automation_gets_cannot_execute(client,app_module,monkeypatch):
    monkeypatch.setattr(app_module,"telegram_scheduler_delivery",lambda *_a,**_k: (_ for _ in ()).throw(AssertionError("GET must never deliver")))
    monkeypatch.setattr(app_module,"telegram_scheduler_tick",lambda *_a,**_k: (_ for _ in ()).throw(AssertionError("GET must never tick")))
    for path in (
        "/api/telegram/auto-run",
        "/api/v495/telegram-auto-run",
        "/api/telegram/scheduler-tick",
    ):
        assert client.get(path).status_code==405,path

