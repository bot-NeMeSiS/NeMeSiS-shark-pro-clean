"""V941 canonical schedule: minimal production recurrence, no duplicate schedulers."""
from pathlib import Path
import importlib.util
import json
import os

ROOT=Path(__file__).resolve().parents[1]


def test_render_yaml_has_only_master_and_daily_backup_crons():
    text=(ROOT/"render.yaml").read_text(encoding="utf-8")
    assert text.count("  - type: cron") == 2
    assert "name: telegram-auto-tick" in text
    assert 'schedule: "*/10 * * * *"' in text
    assert "startCommand: python tools/render_cron_master_tick.py" in text
    assert "name: nemesis-data-backup" in text
    assert 'schedule: "30 2 * * *"' in text
    assert "startCommand: python tools/render_cron_data_backup.py" in text
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
    assert summary["policy"]=="ONE_OPERATIONAL_MASTER_PLUS_DAILY_BACKUP"
    assert [j["name"] for j in summary["jobs"]]==["master_tick","data_backup"]
    assert summary["jobs"][0]["cadence"]=="cada 10 min"
    assert summary["jobs"][1]["cadence"]=="02:30 UTC · diario (03:30/04:30 Madrid)"
    assert "pick_grading" in summary["jobs"][0]["included_flows"]
    assert "highlights sync" in summary["manual_only"]


def test_legacy_admin_page_does_not_claim_old_jobs_are_render_scheduled():
    text=(ROOT/"templates/admin_daily_automation.html").read_text(encoding="utf-8")
    assert "Manual / compatibilidad" in text
    assert "Frecuencia real</td><td>Cada 10 minutos" in text
    assert "Cron anterior conservado" not in text
