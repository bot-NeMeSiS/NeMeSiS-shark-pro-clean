from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION = "V858_VISUAL_DIRECTION_LOCK_FULL_APP_REFERENCE_FINAL"
NEXT_VERSION = "V859_COMPANY_WIDE_ECOSYSTEM_AUDIT_AND_PRODUCT_BOARD_FINAL"
NEXT_NEXT_VERSION = "V860_PROJECT_CLEANUP_LEGACY_PURGE_VISUAL_REFERENCE_ALIGNMENT_FINAL"
NEXT_NEXT_NEXT_VERSION = "V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL"
NEXT_NEXT_NEXT_NEXT_VERSION = "V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL"
NEXT_NEXT_NEXT_NEXT_NEXT_VERSION = "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL"
VALID_CURRENT_VERSIONS = {VERSION, NEXT_VERSION, NEXT_NEXT_VERSION, NEXT_NEXT_NEXT_VERSION, NEXT_NEXT_NEXT_NEXT_VERSION, NEXT_NEXT_NEXT_NEXT_NEXT_VERSION}


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

    ok(version_txt in VALID_CURRENT_VERSIONS, "VERSION.txt V858/V859", failures)
    ok(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in VALID_CURRENT_VERSIONS), "APP_VERSION V858/V859", failures)
    ok('data-v858-shell="true"' in base, "data-v858-shell", failures)
    ok("NEMESIS V858 VISUAL DIRECTION LOCK FULL APP REFERENCE ACTIVE" in base, "comentario V858", failures)
    ok("V858_VISUAL_DIRECTION_LOCK_FULL_APP_REFERENCE_FINAL" in base or "V859_COMPANY_WIDE_ECOSYSTEM_AUDIT_AND_PRODUCT_BOARD_FINAL" in base or "V860_PROJECT_CLEANUP_LEGACY_PURGE_VISUAL_REFERENCE_ALIGNMENT_FINAL" in base or "V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL" in base or "V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL" in base or "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL" in base, "cache CSS V858/V859/V860/V861/V862", failures)
    ok("V858 VISUAL DIRECTION LOCK FULL APP REFERENCE START" in css, "CSS V858 start", failures)
    ok("V858 VISUAL DIRECTION LOCK FULL APP REFERENCE END" in css, "CSS V858 end", failures)

    for report in [
        "reports/V858_PREFLIGHT_FROM_V857.md",
        "reports/V858_VISUAL_DIRECTION_GAP_AUDIT.md",
        "reports/V858_VISUAL_DIRECTION_LOCK_REPORT.md",
        "reports/V858_CLIENT_MOBILE_VISUAL_LOCK_QA.md",
        "reports/V858_CLIENT_PC_VISUAL_LOCK_QA.md",
        "reports/V858_ADMIN_VISUAL_LOCK_QA.md",
        "reports/V858_MEMBERSHIP_VISUAL_VALUE_QA.md",
        "reports/V858_PICKS_LIVE_SHARK_TELEGRAM_VISUAL_QA.md",
        "reports/V858_RENDER_READY_VISUAL_LOCK_NOTES.md",
    ]:
        ok((ROOT / report).exists(), f"reporte {report}", failures)

    for token in [
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

    ok((ROOT / "engines/company_operating_system_engine.py").exists(), "Company OS engine preservado", failures)
    ok((ROOT / "templates/admin_company_os.html").exists(), "Company OS template preservado", failures)
    ok("/admin/company-os" in app_py and "/api/admin/company-os/summary" in app_py, "Company OS rutas/API", failures)

    for marker in [
        "--v858-bg",
        "--v858-surface",
        "--v858-accent",
        "body[data-v858-shell=\"true\"].ns-admin .bottom-nav",
        "body[data-v858-shell=\"true\"].ns-admin .floating-shark",
        "v858-visual-lock",
    ]:
        ok(marker in css or marker in base or marker in read("templates/admin_company_os.html"), f"señal visual {marker}", failures)

    visible = "\n".join(read(path) for path in [
        "templates/base.html",
        "templates/admin_company_os.html",
        "templates/admin_dashboard.html",
        "templates/client_app_center.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/shark.html",
        "templates/telegram.html",
        "templates/profile.html",
        "templates/support.html",
    ] if (ROOT / path).exists())
    for bad in ["Ãƒ", "Ã‚", "ï¿½", "EspaÃ", "proximo", "analisis", "competicion", "informacion", "conexion", "senales"]:
        ok(bad not in visible, f"sin mojibake/copy roto {bad}", failures)
    for phrase in ["garantizado", "apuesta segura", "sin riesgo", "apuesta fija"]:
        ok(phrase not in (base + css + visible).lower(), f"sin promesa irresponsable {phrase}", failures)

    for route in ["/app", "/partidos", "/calendar", "/live", "/directo", "/picks", "/shark", "/telegram", "/profile", "/support", "/track-record"]:
        ok(route in base or route in app_py, f"ruta cliente {route}", failures)
    for route in ["/admin/dashboard", "/admin/company-os", "/admin/empresa", "/admin/operating-system", "/admin/data-center", "/admin/api-sports", "/admin/api-sports-audit", "/admin/telegram/command-center", "/admin/shark-ai", "/admin/daily-automation", "/admin/users", "/admin/memberships", "/admin/payments"]:
        ok(route in base or route in app_py, f"ruta admin {route}", failures)

    if (ROOT / "RELEASE_MANIFEST_V858.json").exists():
        manifest = json.loads(read("RELEASE_MANIFEST_V858.json"))
        ok(manifest.get("version") == VERSION, "manifest V858", failures)
        ok(manifest.get("has_internal_zips") is False, "manifest sin ZIP interno", failures)

    if failures:
        raise SystemExit("V858 check failed:\n- " + "\n- ".join(failures))
    print("V858 visual direction lock OK")


if __name__ == "__main__":
    main()
