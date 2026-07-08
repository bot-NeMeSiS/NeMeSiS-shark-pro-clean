from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V888_SENTINEL_AUTOPILOT_SELF_IMPROVEMENT_ENGINE_FINAL"
CURRENT_COMPATIBLE_PREFIXES = (
    "V888_",
    "V889_",
    "V890_",
    "V891_",
    "V892_",
    "V893_",
    "V894_",
    "V895_",
    "V896_",
    "V897_",
    "V898_",
    "V899_",
    "V900_",
    "V901_",
    "V902_",
    "V903_",
    "V904_",
    "V905_",
    "V906_",
    "V907_",
    "V908_",
    "V909_",
    "V910_",
    "V911_",
    "V912_",
    "V913_",
)
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
    base = read("templates/base.html")
    css = read("static/app.css")
    engine = read("engines/sentinel_autopilot_engine.py")
    continuous = read("engines/continuous_shark_sentinel_engine.py")

    require(version_txt.startswith(CURRENT_COMPATIBLE_PREFIXES), "VERSION.txt is not compatible with V888-V896 lineage", failures)
    require(app_version_file == version_txt, "APP_VERSION does not match VERSION.txt", failures)
    require(f"APP_VERSION = '{version_txt}'" in app_py, "app.py APP_VERSION mismatch", failures)
    require("has_v888_sentinel_autopilot_self_improvement" in app_py, "runtime V888 AutoPilot flag missing", failures)
    require("has_v887_telegram_queue_skipped_hotfix" in app_py, "V887 Telegram hotfix flag not preserved", failures)

    require("engines.sentinel_autopilot_engine" in app_py, "AutoPilot engine not imported", failures)
    require((ROOT / "engines/sentinel_autopilot_engine.py").exists(), "sentinel_autopilot_engine.py missing", failures)
    require((ROOT / "templates/admin_sentinel_autopilot.html").exists(), "admin_sentinel_autopilot.html missing", failures)
    for route in [
        "/admin/sentinel-autopilot",
        "/admin/autopilot",
        "/admin/self-improvement",
        "/admin/mejoras-automaticas",
        "/api/admin/sentinel-autopilot/summary",
        "/api/admin/sentinel-autopilot/run",
        "/api/admin/sentinel-autopilot/issues",
        "/api/admin/sentinel-autopilot/tasks",
        "/api/admin/sentinel-autopilot/generate-prompt",
        "/api/admin/sentinel-autopilot/mark-resolved",
        "/api/automation/sentinel-autopilot/run",
    ]:
        require(route in app_py, f"route missing: {route}", failures)

    for fn in [
        "build_autopilot_snapshot",
        "run_autopilot_scan",
        "classify_autopilot_issue",
        "create_autopilot_task",
        "generate_codex_prompt_for_issue",
        "build_safe_fix_plan",
        "build_priority_matrix",
        "build_next_best_actions",
        "build_autopilot_daily_report",
        "save_autopilot_memory",
        "load_autopilot_memory",
    ]:
        require(f"def {fn}" in engine, f"engine function missing: {fn}", failures)

    for token in [
        "production_alignment",
        "telegram",
        "sports_data",
        "picks_odds",
        "live",
        "navigation",
        "mobile",
        "visual_layout",
        "admin_ops",
        "shark_ai",
        "payments",
        "memberships",
        "logos",
        "security",
        "performance",
        "copy",
        "release_zip",
        "critical",
        "requires_approval",
        "safe_to_auto_fix",
        "codex_prompt",
    ]:
        require(token in engine, f"AutoPilot contract token missing: {token}", failures)

    require("sentinel_autopilot_rules_v888" in continuous, "Continuous Sentinel does not expose AutoPilot rules", failures)
    require("sentinel_autopilot_ready" in continuous, "Continuous Sentinel ready flag missing", failures)
    require("data-v888-autopilot-shell" in base, "base.html AutoPilot shell marker missing", failures)
    require("V888 SENTINEL AUTOPILOT SELF IMPROVEMENT ENGINE" in base, "base.html AutoPilot comment missing", failures)
    require("V888 SENTINEL AUTOPILOT SELF IMPROVEMENT ENGINE START" in css, "CSS AutoPilot marker missing", failures)
    require("/admin/sentinel-autopilot" in base, "Admin nav missing AutoPilot link", failures)

    for report in [
        "reports/V888_SENTINEL_AUTOPILOT_SELF_IMPROVEMENT_ENGINE_REPORT.md",
        "reports/V888_SENTINEL_AUTOPILOT_PREFLIGHT.md",
        "reports/V888_AUTOPILOT_MEMORY_QA.md",
        "reports/V888_AUTOPILOT_ADMIN_PANEL_QA.md",
        "reports/V888_AUTOPILOT_API_SECURITY_QA.md",
        "reports/V888_AUTOPILOT_CRON_QA.md",
        "reports/V888_AUTOPILOT_SENTINEL_INTEGRATION_QA.md",
        "reports/V888_AUTOPILOT_CODEX_PROMPTS_QA.md",
        "reports/V888_AUTOPILOT_SAFE_AUTOFIX_POLICY.md",
        "reports/V888_AUTOPILOT_NEXT_STEPS.md",
    ]:
        require((ROOT / report).exists(), f"report missing: {report}", failures)

    combined = "\n".join([app_py, engine, base])
    require(not re.search(r"(TELEGRAM_BOT_TOKEN\s*=|OPENAI_API_KEY\s*=|STRIPE_SECRET_KEY\s*=|AUTOMATION_SECRET\s*=|sk_live_)", combined), "possible secret assignment found", failures)
    require("auto_deploy" in engine and "auto_push" in engine and "send_real_telegram" in engine, "forbidden actions not declared", failures)
    require("QUEUE_SKIPPED" in app_py, "V887 QUEUE_SKIPPED preservation missing", failures)

    temp_db = ROOT / "tmp_v888_sentinel_autopilot_check.sqlite"
    if temp_db.exists():
        temp_db.unlink()
    os.environ["DB_PATH"] = str(temp_db)
    os.environ["AUTOMATION_SECRET"] = "v888-autopilot-secret"
    import app  # noqa: WPS433

    app.init_db()
    client = app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, "runtime-version not 200", failures)
    runtime_json = runtime.get_json() or {}
    require(runtime_json.get("app_version") == version_txt, "runtime app_version mismatch", failures)
    require(runtime_json.get("has_v888_sentinel_autopilot_self_improvement") is True, "runtime AutoPilot flag false", failures)
    require(runtime_json.get("has_v887_telegram_queue_skipped_hotfix") is True, "runtime V887 flag false", failures)

    for route in [
        "/api/admin/sentinel-autopilot/summary",
        "/api/admin/sentinel-autopilot/run",
        "/api/admin/sentinel-autopilot/issues",
        "/api/admin/sentinel-autopilot/tasks",
        "/api/admin/sentinel-autopilot/generate-prompt",
    ]:
        require(client.get(route).status_code == 403, f"admin API without session not 403: {route}", failures)
    require(client.post("/api/admin/sentinel-autopilot/mark-resolved", json={"issue_id": "AP-TEST"}).status_code == 403, "admin API without session not 403: mark-resolved", failures)

    require(client.get("/api/automation/sentinel-autopilot/run").status_code == 403, "AutoPilot cron without secret not 403", failures)
    cron = client.get("/api/automation/sentinel-autopilot/run?secret=v888-autopilot-secret&dry_run=1")
    require(cron.status_code == 200, "AutoPilot cron with secret dry_run not 200", failures)
    cron_json = cron.get_json() or {}
    require(cron_json.get("dangerous_actions_executed") is False, "AutoPilot executed dangerous action", failures)
    require(isinstance(cron_json.get("tasks"), list), "AutoPilot cron did not return tasks", failures)
    require(isinstance(cron_json.get("codex_prompts"), list), "AutoPilot cron did not return Codex prompts", failures)

    try:
        if temp_db.exists():
            temp_db.unlink()
    except OSError:
        pass

    if failures:
        print("V888 Sentinel AutoPilot check FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V888 Sentinel AutoPilot check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
