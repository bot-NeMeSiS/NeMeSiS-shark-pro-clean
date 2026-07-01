from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION = "V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL"
NEXT_VERSION = "V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL"
NEXT_NEXT_VERSION = "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL"
V863 = "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL"
V864 = "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL"
VALID_CURRENT_VERSIONS = {VERSION, NEXT_VERSION, NEXT_NEXT_VERSION, V863, V864}


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
    engine = read("engines/auto_improvement_engine.py")
    template = read("templates/admin_auto_improvement.html")

    ok(version_txt in VALID_CURRENT_VERSIONS, "VERSION.txt V861/V862", failures)
    ok(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in VALID_CURRENT_VERSIONS), "APP_VERSION V861/V862", failures)
    ok('data-v861-shell="true"' in base, "data-v861-shell", failures)
    ok("NEMESIS V861 SELF IMPROVING OPERATIONS OS SAFE AUTOMATION ACTIVE" in base, "comentario V861", failures)
    ok("V861 SELF IMPROVING OPERATIONS OS SAFE AUTOMATION START" in css, "CSS V861 start", failures)
    ok("V861 SELF IMPROVING OPERATIONS OS SAFE AUTOMATION END" in css, "CSS V861 end", failures)
    ok("V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL" in base or "V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL" in base or "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL" in base or "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL" in base or "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL" in base, "cache CSS V861-V864", failures)

    for path in [
        "engines/auto_improvement_engine.py",
        "templates/admin_auto_improvement.html",
    ]:
        ok((ROOT / path).exists(), f"existe {path}", failures)

    for token in [
        "build_auto_improvement_summary",
        "run_auto_improvement_diagnostic",
        "FORBIDDEN_AUTOMATIC_ACTIONS",
        "no_code_writes",
        "no_deploy",
        "no_external_calls",
        "no_db_write_during_render",
    ]:
        ok(token in engine, f"engine token {token}", failures)

    for route in [
        "/admin/auto-improvement",
        "/admin/mejora-continua",
        "/admin/shark-ops",
        "/admin/continuous-improvement",
        "/api/admin/auto-improvement/summary",
        "/api/automation/auto-improvement/run",
    ]:
        ok(route in app_py or route in base or route in template, f"ruta {route}", failures)

    ok("automation_cron_access_allowed()" in app_py and "api_v861_auto_improvement_run" in app_py, "cron protegido V861", failures)
    ok("admin_json_forbidden()" in app_py and "api_admin_auto_improvement_summary" in app_py, "API admin protegida V861", failures)

    for report in [
        "reports/V861_PREFLIGHT_FROM_V860.md",
        "reports/V861_SELF_IMPROVING_OPERATIONS_OS_REPORT.md",
        "reports/V861_AUTO_IMPROVEMENT_SAFETY_MODEL.md",
        "reports/V861_SAFE_ACTION_LEVELS.md",
        "reports/V861_AUTO_IMPROVEMENT_ADMIN_QA.md",
        "reports/V861_CRON_AUTO_IMPROVEMENT_RUNBOOK.md",
        "reports/V861_CODEX_PROMPT_GENERATOR_NOTES.md",
        "reports/V861_RENDER_READY_AUTO_IMPROVEMENT_NOTES.md",
    ]:
        ok((ROOT / report).exists(), f"reporte {report}", failures)

    for token in [
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
        "templates/admin_auto_improvement.html",
        "templates/admin_company_os.html",
        "templates/admin_company_audit.html",
    ])
    for bad in ["Ã", "Â", "", "membresÃ", "AuditorÃ", "PrÃ", "acciÃ", "sin riesgo garantizado"]:
        ok(bad not in visible, f"sin mojibake {bad}", failures)

    all_text = (app_py + base + css + template + engine).lower()
    for phrase in ["apuesta segura", "garantizado", "apuesta fija"]:
        ok(phrase not in all_text, f"sin promesa irresponsable {phrase}", failures)

    for secret_pattern in ["TELEGRAM_BOT_TOKEN =", "OPENAI_API_KEY =", "STRIPE_SECRET_KEY =", "AUTOMATION_SECRET ="]:
        ok(secret_pattern not in app_py, f"sin secreto asignado {secret_pattern}", failures)

    for forbidden in ["deploy automatico a Render\" in safe_auto_actions", "Modificar app.py\" in safe_auto_actions", "borrar DB\" in safe_auto_actions"]:
        ok(forbidden not in engine, f"sin accion peligrosa automatica {forbidden}", failures)

    for route in ["/app", "/partidos", "/calendar", "/live", "/directo", "/picks", "/shark", "/telegram", "/profile", "/support", "/track-record"]:
        ok(route in base or route in app_py, f"ruta cliente {route}", failures)
    for route in ["/admin/dashboard", "/admin/company-os", "/admin/company-audit", "/admin/auto-improvement", "/admin/data-center", "/admin/api-sports", "/admin/telegram/command-center", "/admin/shark-ai", "/admin/daily-automation", "/admin/users", "/admin/memberships", "/admin/payments"]:
        ok(route in base or route in app_py, f"ruta admin {route}", failures)

    if failures:
        raise SystemExit("V861 check failed:\n- " + "\n- ".join(failures))
    print("V861 self improving operations OS OK")


if __name__ == "__main__":
    main()
