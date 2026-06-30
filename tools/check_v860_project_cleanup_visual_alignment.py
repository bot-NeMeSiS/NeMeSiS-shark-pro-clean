from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION = "V860_PROJECT_CLEANUP_LEGACY_PURGE_VISUAL_REFERENCE_ALIGNMENT_FINAL"
NEXT_VERSION = "V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL"
NEXT_NEXT_VERSION = "V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL"
NEXT_NEXT_NEXT_VERSION = "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL"
V863 = "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL"
V864 = "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL"
VALID_CURRENT_VERSIONS = {VERSION, NEXT_VERSION, NEXT_NEXT_VERSION, NEXT_NEXT_NEXT_VERSION, V863, V864}


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
    build = read("tools/build_clean_release.py")
    audit = read("tools/audit_release_zip.py")

    ok(version_txt in VALID_CURRENT_VERSIONS, "VERSION.txt V860/V861", failures)
    ok(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in VALID_CURRENT_VERSIONS), "APP_VERSION V860/V861", failures)
    ok('data-v860-shell="true"' in base, "data-v860-shell", failures)
    ok("NEMESIS V860 PROJECT CLEANUP LEGACY PURGE VISUAL REFERENCE ALIGNMENT ACTIVE" in base, "comentario V860", failures)
    ok("V860 PROJECT CLEANUP LEGACY PURGE VISUAL REFERENCE ALIGNMENT START" in css, "CSS V860 start", failures)
    ok("V860 PROJECT CLEANUP LEGACY PURGE VISUAL REFERENCE ALIGNMENT END" in css, "CSS V860 end", failures)

    for token in [
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

    for report in [
        "reports/V860_PREFLIGHT_FROM_V859.md",
        "reports/V860_PROJECT_CLEANUP_AND_LEGACY_AUDIT.md",
        "reports/V860_PROJECT_CLEANUP_ACTIONS.md",
        "reports/V860_REAL_VIDEO_VS_REFERENCE_VISUAL_AUDIT.md",
        "reports/V860_VISUAL_LAYER_PURGE_REPORT.md",
        "reports/V860_LEGACY_ROUTES_BUTTONS_AND_DUPLICATES_AUDIT.md",
        "reports/V860_PROJECT_CLEANUP_LEGACY_PURGE_VISUAL_REFERENCE_ALIGNMENT_REPORT.md",
        "reports/V860_RELEASE_CLEANLINESS_QA.md",
        "reports/V860_REFERENCE_ALIGNMENT_NEXT_STEPS.md",
    ]:
        ok((ROOT / report).exists(), f"reporte {report}", failures)

    ok(".venv" in build and "release_output" in build and "v636work" in build, "build_clean_release excluye basura", failures)
    ok(".db-journal" in build and ".sqlite-journal" in build, "build_clean_release excluye journals", failures)
    ok("missing_required_root" in audit, "audit_release_zip valida root requerido", failures)

    visible = "\n".join(read(path) for path in [
        "templates/base.html",
        "templates/client_app_center.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/admin_company_os.html",
        "templates/admin_company_audit.html",
        "templates/admin_memberships.html",
    ])
    for bad in ["Ãƒ", "Ã‚", "ï¿½", "TambiÃ", "membresÃ", "AuditorÃ", "Conversin", "Próximo foco", "Anlisis"]:
        ok(bad not in visible, f"sin mojibake {bad}", failures)
    for phrase in ["garantizado", "apuesta segura", "sin riesgo", "apuesta fija"]:
        ok(phrase not in (base + css + visible).lower(), f"sin promesa irresponsable {phrase}", failures)
    ok('body[data-v860-shell="true"].ns-admin .bottom-nav' in css, "sin bottom nav cliente en admin", failures)
    ok('body[data-v860-shell="true"].ns-admin .v825-public-floating-shark' in css, "sin floating SHARK cliente duplicado en admin", failures)

    if (ROOT / "RELEASE_MANIFEST_V860.json").exists():
        manifest = json.loads(read("RELEASE_MANIFEST_V860.json"))
        ok(manifest.get("version") == VERSION, "manifest V860", failures)
        ok(manifest.get("has_internal_zips") is False, "release sin ZIPs internos", failures)

    for route in ["/app", "/partidos", "/calendar", "/live", "/directo", "/picks", "/shark", "/telegram", "/profile", "/support", "/track-record"]:
        ok(route in base or route in app_py, f"ruta cliente {route}", failures)
    for route in ["/admin/dashboard", "/admin/company-os", "/admin/auditoria-empresa", "/admin/company-audit", "/admin/product-board", "/admin/data-center", "/admin/api-sports", "/admin/api-sports-audit", "/admin/telegram/command-center", "/admin/shark-ai", "/admin/daily-automation", "/admin/users", "/admin/memberships", "/admin/payments"]:
        ok(route in base or route in app_py, f"ruta admin {route}", failures)

    if failures:
        raise SystemExit("V860 check failed:\n- " + "\n- ".join(failures))
    print("V860 project cleanup visual alignment OK")


if __name__ == "__main__":
    main()
