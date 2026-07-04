from __future__ import annotations

import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
VERSION_PREFIXES = ("V892_", "V894_", "V895_")
sys.path.insert(0, str(ROOT))


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    version_txt = read("VERSION.txt").strip().lstrip("\ufeff")
    app_version_file = read("APP_VERSION").strip().lstrip("\ufeff")
    app_py = read("app.py")
    css = read("static/app.css")
    template = read("templates/admin_autonomous_company_sentinel.html")

    require(version_txt.startswith(VERSION_PREFIXES), "VERSION.txt is not V892/V894/V895 company sentinel lineage", failures)
    require(app_version_file == version_txt, "APP_VERSION does not match VERSION.txt", failures)
    require(f"APP_VERSION = '{version_txt}'" in app_py, "app.py APP_VERSION mismatch", failures)
    for flag in [
        "has_v892_autonomous_company_sentinel",
        "has_v892_reference_qa_worker",
        "has_v892_codex_outbox",
        "has_v892_safe_autofix_planner",
        "has_v892_user_admin_journey_worker",
    ]:
        require(flag in app_py, f"runtime flag missing: {flag}", failures)

    for path in [
        "engines/autonomous_company_sentinel_engine.py",
        "engines/sentinel_user_admin_journey_engine.py",
        "engines/sentinel_reference_visual_engine.py",
        "engines/sentinel_codex_outbox_engine.py",
        "engines/sentinel_safe_autofix_engine.py",
        "engines/sentinel_render_alignment_engine.py",
        "engines/sentinel_telegram_quality_watch_engine.py",
        "templates/admin_autonomous_company_sentinel.html",
        "templates/admin_sentinel_codex_outbox.html",
        "tools/run_autonomous_company_sentinel.py",
        "tools/export_sentinel_codex_outbox.py",
        "tools/run_reference_visual_scan.py",
    ]:
        require((ROOT / path).exists(), f"missing file: {path}", failures)

    require("V894 AUTONOMOUS COMPANY SENTINEL REFERENCE CODEX WORKFORCE" in css, "V894 CSS marker missing", failures)
    require("href=\"#\"" not in template, "admin company sentinel template contains href #", failures)
    require("javascript:void" not in template.lower(), "admin company sentinel template contains javascript:void", failures)
    require("No Telegram real" in template, "safe Telegram copy missing", failures)

    for report in [
        "reports/V892_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_REPORT.md",
        "reports/V892_USER_ADMIN_JOURNEY_QA.md",
        "reports/V892_REFERENCE_VISUAL_GAP_QA.md",
        "reports/V892_CODEX_OUTBOX_AUTOFIX_PLAN.md",
        "reports/V892_TELEGRAM_AND_PICKS_WATCH_QA.md",
        "reports/V892_RENDER_ALIGNMENT_QA.md",
        "reports/V892_SECURITY_AUTOMATION_QA.md",
        "reports/V892_NEXT_STEPS.md",
    ]:
        require((ROOT / report).exists(), f"report missing: {report}", failures)

    os.environ["AUTOMATION_SECRET"] = "v892-company-secret"
    os.environ.pop("DB_PATH", None)
    import app  # noqa: WPS433

    client = app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, "runtime-version not 200", failures)
    runtime_json = runtime.get_json() or {}
    require(runtime_json.get("app_version") == version_txt, "runtime app_version mismatch", failures)
    for flag in [
        "has_v892_autonomous_company_sentinel",
        "has_v892_reference_qa_worker",
        "has_v892_codex_outbox",
        "has_v892_safe_autofix_planner",
        "has_v892_user_admin_journey_worker",
    ]:
        require(runtime_json.get(flag) is True, f"runtime flag false: {flag}", failures)

    for route in [
        "/admin/autonomous-company-sentinel",
        "/admin/company-sentinel",
        "/admin/auto-qa",
        "/admin/sentinel-empresa",
        "/admin/autonomous-sentinel",
        "/admin/sentinel-codex-outbox",
    ]:
        response = client.get(route)
        require(response.status_code in (302, 401, 403), f"{route} not protected without admin session", failures)

    for route in [
        "/api/admin/autonomous-company-sentinel/status",
        "/api/admin/autonomous-company-sentinel/latest-run",
        "/api/admin/autonomous-company-sentinel/issues",
        "/api/admin/autonomous-company-sentinel/outbox",
        "/api/admin/autonomous-company-sentinel/autofix-plan",
        "/api/admin/autonomous-company-sentinel/reference-gaps",
        "/api/admin/autonomous-company-sentinel/render-alignment",
        "/api/admin/autonomous-company-sentinel/run",
        "/api/admin/autonomous-company-sentinel/generate-codex-prompts",
        "/api/admin/autonomous-company-sentinel/sync-issues",
        "/api/admin/autonomous-company-sentinel/export-outbox",
    ]:
        response = client.get(route)
        require(response.status_code == 403, f"{route} without admin session is not 403", failures)

    require(client.get("/api/automation/autonomous-company-sentinel/run?dry_run=1").status_code == 403, "cron without secret is not 403", failures)
    cron = client.get("/api/automation/autonomous-company-sentinel/run?secret=v892-company-secret&mode=safe_scan&dry_run=1&runner=local")
    require(cron.status_code == 200, f"cron dry_run with secret is not 200: {cron.status_code}", failures)
    cron_json = cron.get_json() or {}
    require(cron_json.get("dangerous_actions_executed") is False, "cron reports dangerous actions", failures)
    require((ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "codex_outbox.md").exists(), "company codex outbox missing", failures)

    if failures:
        print("V892/V894 Autonomous Company Sentinel check FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V892/V894 Autonomous Company Sentinel check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
