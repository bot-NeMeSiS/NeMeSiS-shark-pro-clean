from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V865_SENTINEL_ISSUE_TO_IMPROVEMENT_WORKFLOW_FINAL"


def fail(message: str) -> None:
    raise SystemExit(f"V865 Sentinel workflow FAILED: {message}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> None:
    app = read("app.py")
    base = read("templates/base.html")
    template = read("templates/admin_sentinel_workflow.html")
    engine = read("engines/sentinel_improvement_workflow_engine.py")
    continuous = read("engines/continuous_shark_sentinel_engine.py")
    build_release = read("tools/build_clean_release.py")

    require(read("VERSION.txt").strip() == VERSION, "VERSION.txt is not V865")
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION is not V865")
    require(f"APP_VERSION = '{VERSION}'" in app, "app.py APP_VERSION is not V865")
    require("data-v865-shell=\"true\"" in base, "base.html missing data-v865-shell")
    require(VERSION in base, "base.html missing V865 cache marker")

    for route in [
        "/admin/sentinel-workflow",
        "/admin/issue-to-improvement",
        "/admin/fix-pipeline",
        "/api/admin/sentinel-workflow/summary",
        "/api/admin/sentinel-workflow/tasks",
        "/api/admin/sentinel-workflow/generate-prompt",
        "/api/admin/sentinel-workflow/update-issue",
    ]:
        require(route in app or route in template or route in base, f"missing V865 route {route}")

    require('href="/admin/sentinel-workflow"' in base, "admin nav does not expose V865 workflow")
    require("admin_sentinel_workflow.html" in app, "V865 template not rendered")
    require("build_workflow_from_sentinel_result" in continuous, "continuous sentinel not wired to workflow")
    require('mode == "workflow"' in continuous, "workflow mode not handled")

    for marker in [
        "ISSUE_LIFECYCLE",
        "SAFE_ACTIONS",
        "APPROVAL_REQUIRED_ACTIONS",
        "BLOCKED_ACTIONS",
        "build_codex_prompt",
        "build_improvement_tasks",
        "suggested_next_version",
        "update_issue_state",
        "no_code_writes",
        "no_deploy",
        "no_secret_access",
        "no_real_telegram_send",
        "no_external_api_calls",
        "no_fake_data",
    ]:
        require(marker in engine, f"workflow engine missing {marker}")

    preserved = [
        "has_v864_pc_mobile_visual_big_leap",
        "has_v863_real_world_certification",
        "has_v862_continuous_sentinel_loop",
        "has_v861_auto_improvement_os",
        "has_v859_company_audit_board",
        "has_v857_company_os",
        "has_v850_live_crests_api_sports_match_detail",
        "has_v847_company_brain_api_sports_provider_qa",
        "has_v845_shark_ai_product_assistant",
        "has_v818_automation",
        "sanitize_http_header_value",
        "sanitize_runtime_value",
    ]
    for marker in preserved:
        require(marker in app, f"missing preserved marker {marker}")

    visible = "\n".join([base, template])
    for bad in ["Ã", "Â", "�", "aprobaciÃ", "revalidaciÃ", "cÃ³digo"]:
        require(bad not in visible, f"visible mojibake marker found: {bad}")

    require(not re.search(r"(apuesta segura|garantizado|sin riesgo|fijo seguro)", visible, re.I), "irresponsible claim found")
    require(not re.search(r"(TELEGRAM_BOT_TOKEN\s*=|OPENAI_API_KEY\s*=|STRIPE_SECRET_KEY\s*=|AUTOMATION_SECRET\s*=|sk_live_)", app + "\n" + template), "secret-looking assignment found")
    require("reports/V865_" in build_release, "release builder does not include V865 reports")
    require("reports/DAILY_" in build_release, "release builder does not include daily reports")

    print("V865 Sentinel issue-to-improvement workflow OK")


if __name__ == "__main__":
    main()
