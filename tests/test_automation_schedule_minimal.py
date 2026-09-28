"""V941 canonical schedule: minimal production recurrence, no duplicate schedulers."""
from pathlib import Path
import importlib.util
import json
import os

ROOT=Path(__file__).resolve().parents[1]


def test_render_yaml_has_only_one_master_cron():
    text=(ROOT/"render.yaml").read_text(encoding="utf-8")
    assert text.count("  - type: cron") == 1
    assert "name: telegram-auto-tick" in text
    assert 'schedule: "*/10 * * * *"' in text
    assert "startCommand: python tools/render_cron_master_tick.py" in text
    assert "name: nemesis-data-backup" not in text
    for setting in ("SCHEDULER_ENABLED","ENABLE_AUTO_SYNC","AUTO_SYNC_ON_STARTUP","DAILY_AUTOMATION_ENABLED"):
        assert f"- key: {setting}" in text
    assert '- key: DATA_BACKUP_ENABLED' in text


def test_legacy_scheduler_is_opt_in_not_default():
    from engines.scheduler_engine import scheduler_config
    cfg=scheduler_config({})
    assert cfg["enabled"] is False
    assert cfg["startup"] is False


def test_automation_center_lists_only_actual_recurring_jobs():
    from engines.automation_orchestrator_engine import build_automation_center_summary
    env={"AUTOMATION_SECRET":"synthetic","PUBLIC_BASE_URL":"https://example.invalid","DB_PATH":"/tmp/test.db","DATA_BACKUP_ENABLED":"1"}
    summary=build_automation_center_summary("/tmp/test.db","SIMULATED_QA",env=env,state={})
    assert summary["policy"]=="ONE_OPERATIONAL_MASTER"
    assert [j["name"] for j in summary["jobs"]]==["master_tick"]
    assert summary["jobs"][0]["cadence"]=="cada 10 min"
    assert "pick_grading" in summary["jobs"][0]["included_flows"]
    assert "data_backup" in summary["jobs"][0]["included_flows"]
    assert "Sincronización de destacados" in summary["manual_only"]


def test_legacy_admin_page_does_not_claim_old_jobs_are_render_scheduled():
    text=(ROOT/"templates/admin_daily_automation.html").read_text(encoding="utf-8")
    assert "Manual / compatibilidad" in text
    assert "Frecuencia real</td><td>Cada 10 minutos" in text
    assert "Cron anterior conservado" not in text


def test_app_level_legacy_scheduler_default_is_off():
    import app
    previous_scheduler=app.os.environ.pop("SCHEDULER_ENABLED", None)
    previous_sync=app.os.environ.pop("ENABLE_AUTO_SYNC", None)
    try:
        assert app.scheduler_env_enabled() is False
    finally:
        if previous_scheduler is not None:
            app.os.environ["SCHEDULER_ENABLED"]=previous_scheduler
        if previous_sync is not None:
            app.os.environ["ENABLE_AUTO_SYNC"]=previous_sync

def test_startup_scheduler_requires_explicit_startup_flag():
    source=(ROOT/"app.py").read_text(encoding="utf-8")
    assert 'RUN_STARTUP_SCHEDULER_NOW' in source
    assert 'env_bool("ENABLE_AUTO_SYNC", False)' in source
