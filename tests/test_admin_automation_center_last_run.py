"""Regression for production /admin/automation-center last_run rendering."""
from engines.automation_orchestrator_engine import build_automation_center_summary


def test_automation_center_summary_last_run_is_display_string():
    summary = build_automation_center_summary(
        "/tmp/qa.db",
        "SIMULATED_QA",
        env={
            "AUTOMATION_SECRET": "synthetic",
            "PUBLIC_BASE_URL": "https://example.invalid",
            "DATA_BACKUP_ENABLED": "1",
        },
        state={
            "last_cron_telegram_call": {
                "time": "2026-09-28T22:00:00+02:00",
                "result": {"status": "PASS"},
            }
        },
    )
    assert summary["jobs"][0]["last_run"] == "2026-09-28T22:00:00+02:00"
    assert isinstance(summary["jobs"][0]["last_run"], str)


def test_admin_automation_template_accepts_string_last_run(app_module):
    from flask import render_template

    summary = build_automation_center_summary(
        "/tmp/qa.db",
        "SIMULATED_QA",
        env={
            "AUTOMATION_SECRET": "synthetic",
            "PUBLIC_BASE_URL": "https://example.invalid",
            "DATA_BACKUP_ENABLED": "1",
        },
        state={
            "last_cron_telegram_call": {
                "time": "2026-09-28T22:00:00+02:00",
                "result": {"status": "PASS"},
            }
        },
    )
    with app_module.app.test_request_context("/admin/automation-center"):
        html = render_template(
            "admin_automation_center.html",
            data={"automation_center": summary},
        )
    assert "2026-09-28T22:00:00+02:00" in html
    assert "Centro de automatización" in html


def test_template_does_not_call_get_on_last_run_string():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "admin_automation_center.html").read_text(encoding="utf-8")
    assert "(job.get('last_run') or {}).get" not in template
    assert "job.get('last_run') or 'Sin ejecución'" in template
