from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION = "V857_COMPANY_OPERATING_SYSTEM_PRODUCT_PERFECTION_FINAL"
NEXT_VERSION = "V858_VISUAL_DIRECTION_LOCK_FULL_APP_REFERENCE_FINAL"
NEXT_NEXT_VERSION = "V859_COMPANY_WIDE_ECOSYSTEM_AUDIT_AND_PRODUCT_BOARD_FINAL"
NEXT_NEXT_NEXT_VERSION = "V860_PROJECT_CLEANUP_LEGACY_PURGE_VISUAL_REFERENCE_ALIGNMENT_FINAL"
NEXT_NEXT_NEXT_NEXT_VERSION = "V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL"
NEXT_NEXT_NEXT_NEXT_NEXT_VERSION = "V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL"
NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_VERSION = "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL"
V863 = "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL"
V864 = "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL"
VALID_CURRENT_VERSIONS = {VERSION, NEXT_VERSION, NEXT_NEXT_VERSION, NEXT_NEXT_NEXT_VERSION, NEXT_NEXT_NEXT_NEXT_VERSION, NEXT_NEXT_NEXT_NEXT_NEXT_VERSION, NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_VERSION, V863, V864}


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
    engine = read("engines/company_operating_system_engine.py")

    ok(version_txt in VALID_CURRENT_VERSIONS, "VERSION.txt V857/V858", failures)
    ok(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in VALID_CURRENT_VERSIONS), "APP_VERSION V857/V858", failures)
    ok('data-v857-shell="true"' in base, "data-v857-shell", failures)
    ok("NEMESIS V857 COMPANY OPERATING SYSTEM PRODUCT PERFECTION ACTIVE" in base, "comentario V857", failures)
    ok("V857_COMPANY_OPERATING_SYSTEM_PRODUCT_PERFECTION_FINAL" in base or "V858_VISUAL_DIRECTION_LOCK_FULL_APP_REFERENCE_FINAL" in base or "V859_COMPANY_WIDE_ECOSYSTEM_AUDIT_AND_PRODUCT_BOARD_FINAL" in base or "V860_PROJECT_CLEANUP_LEGACY_PURGE_VISUAL_REFERENCE_ALIGNMENT_FINAL" in base or "V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL" in base or "V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL" in base or "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL" in base or "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL" in base or "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL" in base, "cache CSS V857-V864", failures)
    ok("V857 COMPANY OPERATING SYSTEM PRODUCT PERFECTION START" in css, "CSS V857", failures)

    ok((ROOT / "engines/company_operating_system_engine.py").exists(), "company_operating_system_engine.py", failures)
    ok("build_company_os_summary" in engine, "build_company_os_summary", failures)
    for worker in [
        "Product CEO Worker",
        "Technical Director Worker",
        "Client Experience Worker",
        "Admin Command Center Worker",
        "Membership Value Worker",
        "SHARK Intelligence Worker",
        "Telegram Premium Worker",
        "Sports Data Worker",
        "Odds & Picks Worker",
        "Crest & Identity Worker",
        "Routes & Buttons Worker",
        "Spanish Copy Worker",
        "QA Visual Worker",
        "QA Data Reality Worker",
        "Render ZIP Worker",
    ]:
        ok(worker in engine, f"worker {worker}", failures)

    ok((ROOT / "templates/admin_company_os.html").exists(), "admin_company_os.html", failures)
    ok("/admin/company-os" in app_py, "ruta /admin/company-os", failures)
    ok("/api/admin/company-os/summary" in app_py, "API company-os summary", failures)
    ok("admin_json_forbidden" in app_py and "api_admin_company_os_summary" in app_py, "API admin protegida", failures)

    for report in [
        "reports/V857_PREFLIGHT_FROM_V856.md",
        "reports/V857_COMPANY_OS_PRODUCT_PERFECTION_REPORT.md",
        "reports/V857_WORKERS_MATRIX.md",
        "reports/V857_CLIENT_ADMIN_MEMBERSHIP_PERFECTION_QA.md",
        "reports/V857_DATA_REALITY_WORKERS_QA.md",
        "reports/V857_ROUTES_BUTTONS_WORKERS_QA.md",
        "reports/V857_RENDER_READY_COMPANY_OS_NOTES.md",
    ]:
        ok((ROOT / report).exists(), f"reporte {report}", failures)

    for token in [
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
        "templates/admin_company_os.html",
        "templates/admin_dashboard.html",
        "templates/client_app_center.html",
        "templates/shark.html",
        "templates/telegram.html",
    ] if (ROOT / path).exists())
    for bad in ["Ãƒ", "Ã‚", "ï¿½", "EspaÃ", "proximo", "analisis", "competicion", "informacion", "conexion", "senales"]:
        ok(bad not in visible, f"sin mojibake/copy roto {bad}", failures)
    for phrase in ["garantizado", "apuesta segura", "sin riesgo", "apuesta fija"]:
        ok(phrase not in (base + css + visible).lower(), f"sin promesa irresponsable {phrase}", failures)
    for secret_name in ["API_FOOTBALL_KEY =", "API_SPORTS_KEY =", "TELEGRAM_BOT_TOKEN =", "OPENAI_API_KEY ="]:
        ok(secret_name not in visible, f"sin secreto visible {secret_name}", failures)

    ok('body[data-v856-shell="true"].ns-admin .bottom-nav' in css, "sin bottom nav cliente en admin", failures)
    ok('body[data-v856-shell="true"].ns-admin .floating-shark' in css, "sin floating cliente en admin", failures)

    for route in ["/app", "/partidos", "/calendar", "/live", "/directo", "/picks", "/shark", "/telegram", "/profile", "/support", "/track-record"]:
        ok(route in base or route in app_py, f"ruta cliente {route}", failures)
    for route in ["/admin/dashboard", "/admin/company-os", "/admin/control-center", "/admin/data-center", "/admin/api-sports", "/admin/api-sports-audit", "/admin/telegram/command-center", "/admin/shark-ai", "/admin/daily-automation", "/admin/users", "/admin/memberships", "/admin/payments"]:
        ok(route in base or route in app_py, f"ruta admin {route}", failures)

    if (ROOT / "RELEASE_MANIFEST_V857.json").exists():
        manifest = json.loads(read("RELEASE_MANIFEST_V857.json"))
        ok(manifest.get("version") == VERSION, "manifest V857", failures)
        ok(manifest.get("has_internal_zips") is False, "manifest sin ZIP interno", failures)

    if failures:
        raise SystemExit("V857 check failed:\n- " + "\n- ".join(failures))
    print("V857 company operating system product perfection OK")


if __name__ == "__main__":
    main()
