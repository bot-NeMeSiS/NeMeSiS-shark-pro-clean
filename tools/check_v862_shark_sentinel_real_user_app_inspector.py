from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION = "V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL"
NEXT_VERSION = "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL"
V863 = "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL"
V864 = "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL"
VALID_CURRENT_VERSIONS = {VERSION, NEXT_VERSION, V863, V864}


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
    engine = read("engines/shark_sentinel_engine.py")
    template = read("templates/admin_shark_sentinel.html")

    ok(version_txt in VALID_CURRENT_VERSIONS, "VERSION.txt V862", failures)
    ok(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in VALID_CURRENT_VERSIONS), "APP_VERSION V862", failures)
    ok('data-v862-shell="true"' in base, "data-v862-shell", failures)
    ok("NEMESIS V862 SHARK SENTINEL REAL USER APP INSPECTOR ACTIVE" in base, "comentario V862", failures)
    ok("V862 SHARK SENTINEL REAL USER APP INSPECTOR START" in css, "CSS V862 start", failures)
    ok("V862 SHARK SENTINEL REAL USER APP INSPECTOR END" in css, "CSS V862 end", failures)
    ok("V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL" in base or "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL" in base or "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL" in base or "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL" in base, "cache CSS V862/V863/V864", failures)

    for path in [
        "engines/shark_sentinel_engine.py",
        "templates/admin_shark_sentinel.html",
        "tools/run_shark_sentinel_static.py",
    ]:
        ok((ROOT / path).exists(), f"existe {path}", failures)

    for token in [
        "VISITOR", "FREE", "PRO", "ELITE", "ADMIN",
        "SentinelIssue", "run_static_flask_inspection",
        "build_static_sentinel_summary", "FORBIDDEN_AUTOMATIC_ACTIONS",
        "no_code_writes", "no_deploy", "no_external_calls", "no_fake_data",
    ]:
        ok(token in engine, f"engine token {token}", failures)

    for route in [
        "/admin/shark-sentinel",
        "/admin/app-inspector",
        "/admin/qa-bot",
        "/admin/bot-auditor",
        "/api/admin/shark-sentinel/summary",
        "/api/admin/shark-sentinel/run",
        "/api/automation/shark-sentinel/run",
    ]:
        ok(route in app_py or route in base or route in template, f"ruta {route}", failures)

    ok("admin_json_forbidden()" in app_py and "api_admin_shark_sentinel_summary" in app_py, "API admin protegida", failures)
    ok("automation_cron_access_allowed()" in app_py and "api_v862_shark_sentinel_run" in app_py, "cron protegido Sentinel", failures)

    for report in [
        "reports/V862_PREFLIGHT_SHARK_SENTINEL.md",
        "reports/V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_REPORT.md",
        "reports/V862_SENTINEL_USER_JOURNEYS_MATRIX.md",
        "reports/V862_SENTINEL_ISSUE_MODEL.md",
        "reports/V862_SENTINEL_SAFE_AUTOFIX_POLICY.md",
        "reports/V862_SENTINEL_ADMIN_QA.md",
        "reports/V862_SENTINEL_CRON_RUNBOOK.md",
        "reports/V862_SENTINEL_CODEX_PROMPT_GENERATOR.md",
        "reports/V862_RENDER_READY_SENTINEL_NOTES.md",
    ]:
        ok((ROOT / report).exists(), f"reporte {report}", failures)

    for token in [
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
        "templates/admin_shark_sentinel.html",
        "templates/admin_auto_improvement.html",
    ])
    for bad in ["Ã", "Â", "", "membresÃ", "acciÃ", "navegaciÃ"]:
        ok(bad not in visible, f"sin mojibake {bad}", failures)

    all_text = (app_py + base + css + template).lower()
    for phrase in ["apuesta segura", "garantizado", "apuesta fija"]:
        ok(phrase not in all_text, f"sin promesa irresponsable {phrase}", failures)
    for secret_pattern in ["TELEGRAM_BOT_TOKEN =", "OPENAI_API_KEY =", "STRIPE_SECRET_KEY =", "AUTOMATION_SECRET ="]:
        ok(secret_pattern not in app_py, f"sin secreto asignado {secret_pattern}", failures)
    for forbidden in ["deploy automatico\" in safe_actions", "modificar app.py\" in safe_actions", "borrar db\" in safe_actions"]:
        ok(forbidden not in engine.lower(), f"sin accion peligrosa automatica {forbidden}", failures)

    for route in ["/app", "/partidos", "/calendar", "/live", "/directo", "/picks", "/shark", "/telegram", "/profile", "/support", "/track-record"]:
        ok(route in base or route in app_py or route in engine, f"ruta cliente {route}", failures)
    for route in ["/admin/dashboard", "/admin/company-os", "/admin/company-audit", "/admin/auto-improvement", "/admin/shark-sentinel", "/admin/data-center", "/admin/api-sports", "/admin/telegram/command-center", "/admin/shark-ai", "/admin/daily-automation", "/admin/users", "/admin/memberships", "/admin/payments"]:
        ok(route in base or route in app_py or route in engine, f"ruta admin {route}", failures)

    if failures:
        raise SystemExit("V862 check failed:\n- " + "\n- ".join(failures))
    print("V862 SHARK Sentinel real user app inspector OK")


if __name__ == "__main__":
    main()
