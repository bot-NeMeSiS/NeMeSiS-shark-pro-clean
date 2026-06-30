from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL"
NEXT_VERSION = "V865_SENTINEL_ISSUE_TO_IMPROVEMENT_WORKFLOW_FINAL"
V866 = "V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL"

REPORTS = [
    "V864_PREFLIGHT_FROM_V863.md",
    "V864_PC_MOBILE_REAL_VISUAL_GAP_AUDIT.md",
    "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REPORT.md",
    "V864_CLIENT_PC_DASHBOARD_VISUAL_QA.md",
    "V864_CLIENT_MOBILE_APP_VISUAL_QA.md",
    "V864_PARTIDOS_LIVE_VISUAL_QA.md",
    "V864_PICKS_PRODUCT_VISUAL_QA.md",
    "V864_SHARK_TELEGRAM_VISUAL_QA.md",
    "V864_ADMIN_COMMAND_CENTER_VISUAL_QA.md",
    "V864_SENTINEL_VISUAL_QA.md",
    "V864_MEMBERSHIP_VISUAL_VALUE_QA.md",
    "V864_VISUAL_COMPONENTS_UNIFICATION_REPORT.md",
    "V864_BROWSER_VISUAL_QA_NOTES.md",
    "V864_NEXT_VISUAL_STEPS.md",
]


def fail(message: str) -> None:
    raise SystemExit(f"V864 PC/mobile visual big leap FAILED: {message}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def main() -> None:
    version_txt = read("VERSION.txt").strip()
    app_version_txt = read("APP_VERSION").strip()
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    components = read("templates/partials/ui_components.html")
    sentinel = read("engines/continuous_shark_sentinel_engine.py")

    if version_txt not in {VERSION, NEXT_VERSION, V866}:
        fail("VERSION.txt is not V864/V865/V866")
    if app_version_txt not in {VERSION, NEXT_VERSION, V866}:
        fail("APP_VERSION is not V864/V865/V866")
    if not any(f"APP_VERSION = '{candidate}'" in app_py for candidate in {VERSION, NEXT_VERSION, V866}):
        fail("app.py APP_VERSION is not V864/V865/V866")
    if "data-v864-shell" not in base:
        fail("base.html missing data-v864-shell")
    if VERSION not in base and NEXT_VERSION not in base and V866 not in base:
        fail("base.html missing V864/V865/V866 cache/version marker")
    if "has_v864_pc_mobile_visual_big_leap" not in app_py:
        fail("runtime flag V864 missing")

    css_markers = [
        "V864 PC MOBILE VISUAL REFERENCE BIG LEAP START",
        "V864 PC MOBILE VISUAL REFERENCE BIG LEAP END",
        "--v864-bg",
        "--v864-surface",
        "v864-match-row",
        "v864-pick-card",
        "v864-sentinel",
        "bottom-nav",
        "body[data-v864-shell=\"true\"].ns-admin",
    ]
    for marker in css_markers:
        if marker not in css:
            fail(f"missing CSS marker {marker}")

    component_markers = [
        "section_header",
        "match_row",
        "pick_card",
        "sentinel_issue_card",
        "v864-action-button",
        "v864-status-chip",
        "v864-empty-state",
        "command-center-card",
    ]
    for marker in component_markers:
        if marker not in components:
            fail(f"missing component marker {marker}")

    sentinel_markers = [
        "V864_VISUAL_RULES",
        "bottom_nav_duplicada",
        "floating_shark_duplicado",
        "admin_con_navegacion_cliente",
        "visual_big_leap_ready",
    ]
    for marker in sentinel_markers:
        if marker not in sentinel:
            fail(f"missing Sentinel visual rule {marker}")

    preserved = [
        "has_v863_real_world_certification",
        "has_v862_continuous_sentinel_loop",
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
        "sanitize_http_header_value",
        "sanitize_runtime_value",
    ]
    for marker in preserved:
        if marker not in app_py:
            fail(f"missing preserved marker {marker}")

    for report in REPORTS:
        if not (ROOT / "reports" / report).exists():
            fail(f"missing report {report}")

    visible_shell = base + "\n" + css
    for bad in ["Ã", "Â", "�"]:
        if bad in visible_shell:
            fail(f"mojibake marker found in shell/CSS: {bad}")

    if re.search(r"(apuesta segura|garantizado|sin riesgo|fijo seguro)", visible_shell, re.I):
        fail("irresponsible betting claim found")

    if re.search(r"(sk_live_|TELEGRAM_BOT_TOKEN\s*=|AUTOMATION_SECRET\s*=)", app_py + "\n" + base):
        fail("secret-looking assignment found")

    admin_css_required = [
        "body[data-v864-shell=\"true\"].ns-admin :is(.bottom-nav",
        ".floating-shark",
    ]
    for marker in admin_css_required:
        if marker not in css:
            fail(f"missing admin isolation CSS {marker}")

    print("V864 PC/mobile visual reference big leap OK")


if __name__ == "__main__":
    main()
