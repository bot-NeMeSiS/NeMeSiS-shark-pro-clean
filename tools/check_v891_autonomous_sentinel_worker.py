from __future__ import annotations

import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
VERSION_PREFIXES = ("V891_", "V893_", "V894_")
sys.path.insert(0, str(ROOT))


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    version_txt = read("VERSION.txt").strip().lstrip("\ufeff")
    app_version_file = read("APP_VERSION").strip().lstrip("\ufeff")
    app_py = read("app.py")
    css = read("static/app.css")
    template = read("templates/admin_autonomous_sentinel.html")
    engine = read("engines/autonomous_sentinel_worker_engine.py")

    require(version_txt.startswith(VERSION_PREFIXES), "VERSION.txt is not V891/V893/V894 autonomous worker lineage", failures)
    require(app_version_file == version_txt, "APP_VERSION does not match VERSION.txt", failures)
    require(f"APP_VERSION = '{version_txt}'" in app_py, "app.py APP_VERSION mismatch", failures)
    require("has_v891_autonomous_sentinel_user_admin_reference_worker" in app_py, "runtime requested V891 flag missing", failures)
    require("has_v893_autonomous_sentinel_worker" in app_py, "runtime V893 flag missing", failures)
    require("has_v892_sentinel_issues_command_center" in app_py, "V892 issues flag not preserved", failures)
    require("has_v889_telegram_premium_picks_intelligence" in app_py, "V889 Telegram flag not preserved", failures)
    require("run_autonomous_sentinel_worker" in engine, "autonomous worker runner missing", failures)
    require("run_user_journey_checks" in engine, "user journey integration missing", failures)
    require("build_reference_gap_report" in engine, "reference QA integration missing", failures)
    require("build_autofix_plan" in engine, "autofix planner integration missing", failures)
    require("No auto deploy." in engine, "safe no deploy note missing", failures)
    require("No Telegram real." in engine, "safe no Telegram note missing", failures)
    require("dangerous_actions_executed" in engine, "dangerous action guard missing", failures)
    require("v893-autonomous-sentinel" in template, "admin autonomous template marker missing", failures)
    require("AUTONOMOUS_SENTINEL_AUTOFIX=0" in template, "safe autofix copy missing", failures)
    require("V893 AUTONOMOUS SENTINEL USER ADMIN REFERENCE QA WORKER" in css, "V893 CSS marker missing", failures)

    for path in [
        "engines/sentinel_user_journey_engine.py",
        "engines/sentinel_reference_qa_engine.py",
        "engines/sentinel_autofix_planner_engine.py",
        "engines/autonomous_sentinel_worker_engine.py",
        "templates/admin_autonomous_sentinel.html",
    ]:
        require((ROOT / path).exists(), f"missing file: {path}", failures)

    for report in [
        "reports/V891_AUTONOMOUS_SENTINEL_USER_ADMIN_REFERENCE_QA_WORKER_REPORT.md",
        "reports/V891_AUTONOMOUS_USER_JOURNEY_QA.md",
        "reports/V891_REFERENCE_VISUAL_GAP_QA.md",
        "reports/V891_CODEX_OUTBOX_AUTOFIX_PLAN.md",
        "reports/V891_SECURITY_AND_AUTOMATION_QA.md",
        "reports/V891_RENDER_ALIGNMENT_QA.md",
        "reports/V891_NEXT_STEPS.md",
    ]:
        require((ROOT / report).exists(), f"report missing: {report}", failures)

    os.environ["AUTOMATION_SECRET"] = "v891-autonomous-secret"
    os.environ.pop("DB_PATH", None)
    import app  # noqa: WPS433

    client = app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, "runtime-version not 200", failures)
    runtime_json = runtime.get_json() or {}
    require(runtime_json.get("app_version") == version_txt, "runtime app_version mismatch", failures)
    require(runtime_json.get("has_v891_autonomous_sentinel_user_admin_reference_worker") is True, "runtime V891 autonomous flag false", failures)
    require(runtime_json.get("has_v893_autonomous_sentinel_worker") is True, "runtime V893 autonomous flag false", failures)

    for route in [
        "/admin/autonomous-sentinel",
        "/admin/sentinel-worker",
        "/admin/qa-worker",
        "/admin/revision-automatica",
    ]:
        response = client.get(route)
        require(response.status_code in (302, 401, 403), f"{route} is not protected without admin session", failures)

    for route in [
        "/api/admin/autonomous-sentinel/status",
        "/api/admin/autonomous-sentinel/latest-run",
        "/api/admin/autonomous-sentinel/issues",
        "/api/admin/autonomous-sentinel/outbox",
        "/api/admin/autonomous-sentinel/autofix-plan",
        "/api/admin/autonomous-sentinel/run",
        "/api/admin/autonomous-sentinel/generate-codex-prompts",
        "/api/admin/autonomous-sentinel/sync-issues",
    ]:
        response = client.get(route)
        require(response.status_code == 403, f"{route} without admin session is not 403", failures)

    cron_no_secret = client.get("/api/automation/autonomous-sentinel/run?dry_run=1")
    require(cron_no_secret.status_code == 403, "autonomous cron without secret is not 403", failures)
    cron_dry_run = client.get("/api/automation/autonomous-sentinel/run?secret=v891-autonomous-secret&dry_run=1&mode=safe_scan")
    require(cron_dry_run.status_code == 200, "autonomous cron dry_run with secret is not 200", failures)
    cron_json = cron_dry_run.get_json() or {}
    require(cron_json.get("dangerous_actions_executed") is False, "autonomous cron reports dangerous actions", failures)
    require((ROOT / "data" / "runtime" / "autonomous_sentinel" / "outbox" / "codex_prompts.md").exists(), "Codex outbox was not generated", failures)

    if failures:
        print("V891/V893 autonomous Sentinel worker check FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V891/V893 autonomous Sentinel worker check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
