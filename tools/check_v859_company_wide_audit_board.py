from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION = "V859_COMPANY_WIDE_ECOSYSTEM_AUDIT_AND_PRODUCT_BOARD_FINAL"
NEXT_VERSION = "V860_PROJECT_CLEANUP_LEGACY_PURGE_VISUAL_REFERENCE_ALIGNMENT_FINAL"
NEXT_NEXT_VERSION = "V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL"
NEXT_NEXT_NEXT_VERSION = "V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL"
NEXT_NEXT_NEXT_NEXT_VERSION = "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL"
V863 = "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL"
V864 = "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL"


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
    engine = read("engines/company_audit_board_engine.py")

    ok(version_txt in {VERSION, NEXT_VERSION, NEXT_NEXT_VERSION, NEXT_NEXT_NEXT_VERSION, NEXT_NEXT_NEXT_NEXT_VERSION, V863, V864}, "VERSION.txt V859-V864", failures)
    ok(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in {VERSION, NEXT_VERSION, NEXT_NEXT_VERSION, NEXT_NEXT_NEXT_VERSION, NEXT_NEXT_NEXT_NEXT_VERSION, V863, V864}), "APP_VERSION V859-V864", failures)
    ok('data-v859-shell="true"' in base, "data-v859-shell", failures)
    ok("NEMESIS V859 COMPANY WIDE ECOSYSTEM AUDIT PRODUCT BOARD ACTIVE" in base, "comentario V859", failures)
    ok("V859_COMPANY_WIDE_ECOSYSTEM_AUDIT_AND_PRODUCT_BOARD_FINAL" in base or "V860_PROJECT_CLEANUP_LEGACY_PURGE_VISUAL_REFERENCE_ALIGNMENT_FINAL" in base or "V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL" in base or "V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL" in base or "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL" in base or "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL" in base or "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL" in base, "cache CSS V859-V864", failures)
    ok("V859 COMPANY WIDE ECOSYSTEM AUDIT PRODUCT BOARD START" in css, "CSS V859", failures)

    ok((ROOT / "engines/company_audit_board_engine.py").exists(), "company_audit_board_engine.py", failures)
    ok("build_company_audit_summary" in engine, "build_company_audit_summary", failures)
    for board in [
        "Product Board", "Client Experience Board", "Admin Operations Board", "Membership Revenue Board",
        "Data Reality Board", "SHARK Intelligence Board", "Telegram Premium Board",
        "Technical Architecture Board", "Visual Reference Board", "Render/GitHub/Release Board",
    ]:
        ok(board in engine, f"board {board}", failures)

    ok((ROOT / "templates/admin_company_audit.html").exists(), "admin_company_audit.html", failures)
    ok("/admin/company-audit" in app_py, "ruta /admin/company-audit", failures)
    ok("/admin/auditoria-empresa" in app_py, "ruta /admin/auditoria-empresa", failures)
    ok("/admin/product-board" in app_py, "ruta /admin/product-board", failures)
    ok("/api/admin/company-audit/summary" in app_py, "API company-audit summary", failures)
    ok("api_admin_company_audit_summary" in app_py and "admin_json_forbidden" in app_py, "API audit protegida", failures)

    for report in [
        "reports/V859_PREFLIGHT_FROM_V858.md",
        "reports/V859_COMPANY_WIDE_AUDIT_REPORT.md",
        "reports/V859_PRODUCT_BOARD_AUDIT.md",
        "reports/V859_CLIENT_EXPERIENCE_BOARD_AUDIT.md",
        "reports/V859_ADMIN_OPERATIONS_BOARD_AUDIT.md",
        "reports/V859_MEMBERSHIP_REVENUE_BOARD_AUDIT.md",
        "reports/V859_DATA_REALITY_BOARD_AUDIT.md",
        "reports/V859_SHARK_TELEGRAM_BOARD_AUDIT.md",
        "reports/V859_TECHNICAL_ARCHITECTURE_BOARD_AUDIT.md",
        "reports/V859_VISUAL_REFERENCE_BOARD_AUDIT.md",
        "reports/V859_RENDER_GITHUB_RELEASE_BOARD_AUDIT.md",
        "reports/V859_NEXT_STEPS_PRIORITY_ROADMAP.md",
    ]:
        ok((ROOT / report).exists(), f"reporte {report}", failures)

    for token in [
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

    ok((ROOT / "engines/company_operating_system_engine.py").exists(), "Company OS preservado", failures)
    ok((ROOT / "templates/admin_company_os.html").exists(), "Company OS template preservado", failures)

    visible = "\n".join(read(path) for path in [
        "templates/base.html",
        "templates/admin_company_audit.html",
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

    ok('body[data-v858-shell="true"].ns-admin .bottom-nav' in css, "sin bottom nav cliente en admin", failures)
    ok('body[data-v858-shell="true"].ns-admin .floating-shark' in css, "sin floating cliente en admin", failures)

    for route in ["/app", "/partidos", "/calendar", "/live", "/directo", "/picks", "/shark", "/telegram", "/profile", "/support", "/track-record"]:
        ok(route in base or route in app_py, f"ruta cliente {route}", failures)
    for route in ["/admin/dashboard", "/admin/company-os", "/admin/company-audit", "/admin/auditoria-empresa", "/admin/product-board", "/admin/data-center", "/admin/api-sports", "/admin/api-sports-audit", "/admin/telegram/command-center", "/admin/shark-ai", "/admin/daily-automation", "/admin/users", "/admin/memberships", "/admin/payments"]:
        ok(route in base or route in app_py, f"ruta admin {route}", failures)

    if (ROOT / "RELEASE_MANIFEST_V859.json").exists():
        manifest = json.loads(read("RELEASE_MANIFEST_V859.json"))
        ok(manifest.get("version") == VERSION, "manifest V859", failures)
        ok(manifest.get("has_internal_zips") is False, "manifest sin ZIP interno", failures)

    if failures:
        raise SystemExit("V859 check failed:\n- " + "\n- ".join(failures))
    print("V859 company wide audit board OK")


if __name__ == "__main__":
    main()
