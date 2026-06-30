from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION = "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL"
NEXT_VERSION = "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL"
V864 = "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL"
V865 = "V865_SENTINEL_ISSUE_TO_IMPROVEMENT_WORKFLOW_FINAL"
V866 = "V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL"
V867 = "V867_RENDER_DEPLOYMENT_ALIGNMENT_AND_REAL_V866_CERTIFICATION_FINAL"
V868 = "V868_REAL_CLIENT_ADMIN_VISUAL_PRODUCTION_POLISH_AND_SENTINEL_VALUE_FINAL"
V868_PRO = "V868_PRO_MAX_CLIENT_ADMIN_MOBILE_VISUAL_REVENUE_SENTINEL_FINAL"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def ok(condition: bool, label: str, failures: list[str]) -> None:
    if not condition:
        failures.append(label)


def main() -> None:
    failures: list[str] = []
    version_txt = read("VERSION.txt").strip()
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    engine = read("engines/continuous_shark_sentinel_engine.py")
    template = read("templates/admin_continuous_sentinel.html")

    ok(version_txt in {VERSION, NEXT_VERSION, V864, V865, V866, V867, V868, V868_PRO}, "VERSION.txt V862 continuous/V863/V868", failures)
    ok(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in {VERSION, NEXT_VERSION, V864, V865, V866, V867, V868, V868_PRO}), "APP_VERSION V862 continuous/V863/V868", failures)
    ok('data-v862-shell="true"' in base, "data-v862-shell", failures)
    ok("NEMESIS V862 CONTINUOUS SHARK SENTINEL AUTO IMPROVEMENT LOOP ACTIVE" in base, "comentario V862 continuous", failures)
    ok("V862 CONTINUOUS SHARK SENTINEL AUTO IMPROVEMENT LOOP START" in css, "CSS V862 continuous start", failures)
    ok("V862 CONTINUOUS SHARK SENTINEL AUTO IMPROVEMENT LOOP END" in css, "CSS V862 continuous end", failures)
    ok("V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL" in base or "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL" in base or "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL" in base or "V865_SENTINEL_ISSUE_TO_IMPROVEMENT_WORKFLOW_FINAL" in base or "V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL" in base or "V867_RENDER_DEPLOYMENT_ALIGNMENT_AND_REAL_V866_CERTIFICATION_FINAL" in base or V868 in base or V868_PRO in base, "cache CSS V862 continuous/V863/V868", failures)

    for path in [
        "engines/continuous_shark_sentinel_engine.py",
        "templates/admin_continuous_sentinel.html",
        "tools/run_continuous_sentinel_static.py",
    ]:
        ok((ROOT / path).exists(), f"existe {path}", failures)

    for token in [
        "quick", "client", "admin", "visual", "data", "telegram", "improvement", "full",
        "run_continuous_sentinel_cycle", "build_continuous_sentinel_summary",
        "ISSUE_STATUSES", "ACTION_LEVELS", "no_code_writes", "no_deploy", "no_fake_data",
    ]:
        ok(token in engine, f"engine token {token}", failures)

    for route in [
        "/admin/continuous-sentinel",
        "/admin/shark-sentinel",
        "/admin/app-inspector",
        "/admin/bot-auditor",
        "/admin/mejora-continua",
        "/api/admin/continuous-sentinel/summary",
        "/api/admin/continuous-sentinel/run",
        "/api/admin/continuous-sentinel/issues",
        "/api/automation/continuous-sentinel/run",
    ]:
        ok(route in app_py or route in base or route in template, f"ruta {route}", failures)

    ok("admin_json_forbidden()" in app_py and "api_admin_continuous_sentinel_summary" in app_py, "APIs admin protegidas", failures)
    ok("automation_cron_access_allowed()" in app_py and "api_v862_continuous_sentinel_run" in app_py, "cron protegido continuous", failures)

    for report in [
        "reports/V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_REPORT.md",
        "reports/V862_SENTINEL_LOOP_SAFETY_MODEL.md",
        "reports/V862_SENTINEL_ISSUE_TRACKING_MODEL.md",
        "reports/V862_SENTINEL_USER_PROFILES_AND_JOURNEYS.md",
        "reports/V862_SENTINEL_CRON_RUNBOOK.md",
        "reports/V862_SENTINEL_CODEX_PROMPT_GENERATOR.md",
        "reports/V862_SENTINEL_BROWSER_QA_OPTIONAL_NOTES.md",
        "reports/V862_SENTINEL_COMPANY_OS_INTEGRATION.md",
        "reports/V862_RENDER_READY_CONTINUOUS_SENTINEL_NOTES.md",
    ]:
        ok((ROOT / report).exists(), f"reporte {report}", failures)

    for token in [
        "has_v862_continuous_sentinel_loop",
        "has_v862_shark_sentinel",
        "has_v861_auto_improvement_os",
        "has_v860_project_cleanup_visual_alignment",
        "has_v859_company_audit_board",
        "has_v858_visual_direction_lock",
        "has_v857_company_os",
        "has_v856_real_app_reference_gap_second_pass",
        "has_v855_full_ecosystem_reference_rebuild",
        "has_v854_client_admin_real_render_final_polish",
        "has_v853_admin_pc_command_center_reference",
        "has_v850_live_crests_api_sports_match_detail",
        "has_v847_company_brain_api_sports_provider_qa",
        "has_v845_shark_ai_product_assistant",
        "has_v844_telegram_quality_filter",
        "has_v818_automation",
    ]:
        ok(token in app_py, f"runtime flag {token}", failures)

    visible = "\n".join(read(path) for path in [
        "templates/base.html",
        "templates/admin_continuous_sentinel.html",
        "templates/admin_shark_sentinel.html",
    ])
    for bad in ["Ã", "Â", "�", "navegaciÃ", "acciÃ"]:
        ok(bad not in visible, f"sin mojibake {bad}", failures)

    visible_lower = visible.lower()
    for phrase in ["apuesta segura", "garantizado", "apuesta fija"]:
        ok(phrase not in visible_lower, f"sin promesa irresponsable visible {phrase}", failures)

    for secret_pattern in ["TELEGRAM_BOT_TOKEN =", "OPENAI_API_KEY =", "STRIPE_SECRET_KEY =", "AUTOMATION_SECRET ="]:
        ok(secret_pattern not in app_py, f"sin secreto asignado {secret_pattern}", failures)

    for route in ["/app", "/partidos", "/calendar", "/live", "/directo", "/picks", "/shark", "/telegram", "/profile", "/support", "/track-record"]:
        ok(route in base or route in app_py or route in engine, f"ruta cliente {route}", failures)
    for route in ["/admin/dashboard", "/admin/company-os", "/admin/company-audit", "/admin/continuous-sentinel", "/admin/data-center", "/admin/api-sports", "/admin/telegram/command-center", "/admin/shark-ai", "/admin/daily-automation", "/admin/users", "/admin/memberships", "/admin/payments"]:
        ok(route in base or route in app_py or route in engine, f"ruta admin {route}", failures)

    if failures:
        raise SystemExit("V862 continuous check failed:\n- " + "\n- ".join(failures))
    print("V862 continuous SHARK Sentinel loop OK")


if __name__ == "__main__":
    main()
