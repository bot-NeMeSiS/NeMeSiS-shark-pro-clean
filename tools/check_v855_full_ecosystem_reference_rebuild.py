from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION = "V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL"
NEXT_VERSION = "V856_REAL_APP_REFERENCE_GAP_SECOND_PASS_TOTAL_REBUILD_FINAL"
NEXT_NEXT_VERSION = "V857_COMPANY_OPERATING_SYSTEM_PRODUCT_PERFECTION_FINAL"
NEXT_NEXT_NEXT_VERSION = "V858_VISUAL_DIRECTION_LOCK_FULL_APP_REFERENCE_FINAL"
NEXT_NEXT_NEXT_NEXT_VERSION = "V859_COMPANY_WIDE_ECOSYSTEM_AUDIT_AND_PRODUCT_BOARD_FINAL"
NEXT_NEXT_NEXT_NEXT_NEXT_VERSION = "V860_PROJECT_CLEANUP_LEGACY_PURGE_VISUAL_REFERENCE_ALIGNMENT_FINAL"
NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_VERSION = "V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL"
NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_VERSION = "V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL"
NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_VERSION = "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL"
V863 = "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL"
V864 = "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL"
VALID_CURRENT_VERSIONS = {
    VERSION,
    NEXT_VERSION,
    NEXT_NEXT_VERSION,
    NEXT_NEXT_NEXT_VERSION,
    NEXT_NEXT_NEXT_NEXT_VERSION,
    NEXT_NEXT_NEXT_NEXT_NEXT_VERSION,
    NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_VERSION,
    NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_VERSION,
    NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_NEXT_VERSION,
    V863,
    V864,
}


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

    ok(version_txt in VALID_CURRENT_VERSIONS, "VERSION.txt V855/V856", failures)
    ok(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in VALID_CURRENT_VERSIONS), "APP_VERSION V855/V856", failures)
    ok("data-v855-shell=\"true\"" in base, "data-v855-shell", failures)
    ok("V855 FULL ECOSYSTEM REFERENCE REBUILD START" in css, "CSS V855", failures)
    ok("membership_experience_engine" in app_py and (ROOT / "engines/membership_experience_engine.py").exists(), "motor membresías V855", failures)

    for report in [
        "reports/V855_FULL_ECOSYSTEM_PREFLIGHT.md",
        "reports/V855_FULL_ECOSYSTEM_REFERENCE_GAP_AUDIT.md",
        "reports/V855_MEMBERSHIP_FULL_APP_VALUE_MATRIX.md",
        "reports/V855_ADMIN_FULL_COMMAND_CENTER_REBUILD_QA.md",
        "reports/V855_FULL_ROUTES_BUTTONS_FLOW_AUDIT.md",
    ]:
        ok((ROOT / report).exists(), f"reporte {report}", failures)

    for route in ["/app", "/partidos", "/calendar", "/live", "/directo", "/picks", "/shark", "/telegram", "/profile", "/support", "/track-record"]:
        ok(route in base or route in app_py, f"ruta cliente {route}", failures)
    for route in ["/admin/dashboard", "/admin/control-center", "/admin/data-center", "/admin/api-sports", "/admin/telegram/command-center", "/admin/shark-ai", "/admin/daily-automation", "/admin/users", "/admin/memberships", "/admin/payments"]:
        ok(route in base or route in app_py, f"ruta admin {route}", failures)

    for token in ["has_v818_automation", "has_v844_telegram_quality_filter", "has_v845_shark_ai_product_assistant", "has_v847_company_brain_api_sports_provider_qa", "has_v850_live_crests_api_sports_match_detail", "has_v853_admin_pc_command_center_reference", "has_v854_client_admin_real_render_final_polish", "has_v855_full_ecosystem_reference_rebuild"]:
        ok(token in app_py, f"runtime flag {token}", failures)

    for phrase in ["garantizado", "apuesta segura", "sin riesgo", "apuesta fija"]:
        ok(phrase not in (base + css).lower(), f"sin promesa irresponsable {phrase}", failures)

    visible_text = "\n".join(read(path) for path in [
        "templates/base.html",
        "templates/client_app_center.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/shark.html",
        "templates/telegram.html",
        "templates/profile.html",
        "templates/support.html",
        "templates/admin_dashboard.html",
    ])
    for bad in ["Ã", "Â", "", "diagnsticos", "produccin", "sincronizacin", "sesin", "prximo"]:
        ok(bad not in visible_text, f"sin mojibake común {bad}", failures)

    ok("body[data-v855-shell=\"true\"].ns-admin .bottom-nav" in css, "sin bottom nav cliente en admin", failures)
    ok("body[data-v855-shell=\"true\"].ns-admin .floating-shark" in css, "sin floating cliente en admin", failures)

    if failures:
        raise SystemExit("V855 check failed:\n- " + "\n- ".join(failures))
    print("V855 full ecosystem reference rebuild OK")


if __name__ == "__main__":
    main()
