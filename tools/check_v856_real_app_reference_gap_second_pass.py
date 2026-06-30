from pathlib import Path
import json
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION = "V856_REAL_APP_REFERENCE_GAP_SECOND_PASS_TOTAL_REBUILD_FINAL"
V855 = "V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL"
V857 = "V857_COMPANY_OPERATING_SYSTEM_PRODUCT_PERFECTION_FINAL"
V858 = "V858_VISUAL_DIRECTION_LOCK_FULL_APP_REFERENCE_FINAL"
V859 = "V859_COMPANY_WIDE_ECOSYSTEM_AUDIT_AND_PRODUCT_BOARD_FINAL"
V860 = "V860_PROJECT_CLEANUP_LEGACY_PURGE_VISUAL_REFERENCE_ALIGNMENT_FINAL"
V861 = "V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL"
V862 = "V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL"
V862_CONTINUOUS = "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL"
VALID_CURRENT_VERSIONS = {VERSION, V857, V858, V859, V860, V861, V862, V862_CONTINUOUS}


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

    ok(version_txt in VALID_CURRENT_VERSIONS, "VERSION.txt V856/V857", failures)
    ok(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in VALID_CURRENT_VERSIONS), "APP_VERSION V856/V857", failures)
    ok('data-v856-shell="true"' in base, "data-v856-shell", failures)
    ok("NEMESIS V856 REAL APP REFERENCE GAP SECOND PASS ACTIVE" in base, "comentario V856", failures)
    ok("V856_REAL_APP_REFERENCE_GAP_SECOND_PASS_TOTAL_REBUILD_FINAL" in base or "V857_COMPANY_OPERATING_SYSTEM_PRODUCT_PERFECTION_FINAL" in base or "V858_VISUAL_DIRECTION_LOCK_FULL_APP_REFERENCE_FINAL" in base or "V859_COMPANY_WIDE_ECOSYSTEM_AUDIT_AND_PRODUCT_BOARD_FINAL" in base or "V860_PROJECT_CLEANUP_LEGACY_PURGE_VISUAL_REFERENCE_ALIGNMENT_FINAL" in base or "V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL" in base or "V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL" in base or "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL" in base, "cache CSS V856/V857/V858/V859/V860/V861/V862", failures)
    ok("V856 REAL APP REFERENCE GAP SECOND PASS START" in css, "bloque CSS V856", failures)

    for engine in [
        "client_screen_experience_engine",
        "admin_command_center_experience_engine",
        "match_presentation_engine",
        "live_presentation_engine",
        "pick_presentation_engine",
        "telegram_presentation_engine",
        "shark_context_presentation_engine",
    ]:
        ok(engine in app_py, f"import {engine}", failures)
        ok((ROOT / "engines" / f"{engine}.py").exists(), f"archivo {engine}", failures)

    for report in [
        "reports/V856_PREFLIGHT_FROM_V855.md",
        "reports/V856_REAL_APP_REFERENCE_GAP_SECOND_PASS_AUDIT.md",
        "reports/V856_ADMIN_COMMAND_CENTER_SECOND_PASS_QA.md",
        "reports/V856_MEMBERSHIP_VALUE_SECOND_PASS_QA.md",
        "reports/V856_ROUTES_BUTTONS_SECOND_PASS_AUDIT.md",
        "reports/V856_SPANISH_COPY_SECOND_PASS_QA.md",
        "reports/V856_PRODUCTION_STABILITY_QA.md",
    ]:
        ok((ROOT / report).exists(), f"reporte {report}", failures)

    for token in [
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

    for route in ["/app", "/inicio", "/panel-cliente", "/partidos", "/calendar", "/live", "/directo", "/picks", "/shark", "/telegram", "/profile", "/support", "/track-record"]:
        ok(route in base or route in app_py, f"ruta cliente {route}", failures)
    for route in ["/admin/dashboard", "/admin/control-center", "/admin/data-center", "/admin/api-sports", "/admin/api-sports-audit", "/admin/telegram/command-center", "/admin/shark-ai", "/admin/daily-automation", "/admin/users", "/admin/memberships", "/admin/payments"]:
        ok(route in base or route in app_py, f"ruta admin {route}", failures)

    visible = "\n".join(read(path) for path in [
        "templates/base.html",
        "templates/client_app_center.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/shark.html",
        "templates/telegram.html",
        "templates/profile.html",
        "templates/support.html",
        "templates/admin_dashboard.html",
    ] if (ROOT / path).exists())
    for bad in ["Ãƒ", "Ã‚", "ï¿½", "EspaÃ", "proximo", "analisis", "competicion", "informacion", "conexion", "senales"]:
        ok(bad not in visible, f"sin mojibake/copy roto {bad}", failures)
    for phrase in ["garantizado", "apuesta segura", "sin riesgo", "apuesta fija"]:
        ok(phrase not in (base + css + visible).lower(), f"sin promesa irresponsable {phrase}", failures)

    ok('body[data-v856-shell="true"].ns-admin .bottom-nav' in css, "sin bottom nav cliente en admin V856", failures)
    ok('body[data-v856-shell="true"].ns-admin .floating-shark' in css, "sin floating cliente en admin V856", failures)
    ok("V855 FULL ECOSYSTEM REFERENCE REBUILD START" in css, "V855 preservado", failures)
    ok(V855 in read("CHATGPT_CONTINUATION_REPORT.md"), "continuidad V855 documentada", failures)

    manifest = json.loads(read("RELEASE_MANIFEST_V856.json"))
    ok(manifest.get("version") == VERSION, "manifest V856", failures)
    ok(manifest.get("has_internal_zips") is False, "manifest sin ZIP interno", failures)
    ok(manifest.get("forbidden_folders_included") == [], "manifest sin carpetas prohibidas", failures)

    if failures:
        raise SystemExit("V856 check failed:\n- " + "\n- ".join(failures))
    print("V856 real app reference gap second pass OK")


if __name__ == "__main__":
    main()
