from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL"
NEXT_VERSION = "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL"
NEXT_NEXT_VERSION = "V865_SENTINEL_ISSUE_TO_IMPROVEMENT_WORKFLOW_FINAL"
V866 = "V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL"
V867 = "V867_RENDER_DEPLOYMENT_ALIGNMENT_AND_REAL_V866_CERTIFICATION_FINAL"


REPORTS = [
    "V863_PREFLIGHT_FROM_V862.md",
    "V863_RENDER_REAL_DEPLOYMENT_CERTIFICATION.md",
    "V863_RENDER_VERSION_MISMATCH_BLOCKER.md",
    "V863_RENDER_DEPLOYMENT_MISMATCH_DIAGNOSIS.md",
    "V863_RUNTIME_HEADER_SANITIZATION_REPORT.md",
    "V863_PUBLIC_ROUTES_REAL_QA.md",
    "V863_ADMIN_ROUTES_REAL_QA.md",
    "V863_CONTINUOUS_SENTINEL_REAL_RUN_QA.md",
    "V863_MASTER_TICK_HEALTH_REAL_QA.md",
    "V863_API_SPORTS_REAL_PROVIDER_QA.md",
    "V863_THE_ODDS_API_REAL_QA.md",
    "V863_TELEGRAM_REAL_DELIVERY_QA.md",
    "V863_PAYMENTS_STRIPE_TEST_MODE_QA.md",
    "V863_AUTH_SESSIONS_USERS_REAL_QA.md",
    "V863_PC_MOBILE_REAL_VISUAL_QA.md",
    "V863_REAL_PERFORMANCE_QA.md",
    "V863_REAL_SECURITY_QA.md",
    "V863_REAL_WORLD_CERTIFICATION_MATRIX.md",
]


def fail(message: str) -> None:
    raise SystemExit(f"V863 real world certification FAILED: {message}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def main() -> None:
    version_txt = read("VERSION.txt").strip()
    app_version_file = (ROOT / "APP_VERSION")
    app_version_txt = app_version_file.read_text(encoding="utf-8").strip() if app_version_file.exists() else ""
    app_py = read("app.py")
    base_html = read("templates/base.html")

    if version_txt not in {VERSION, NEXT_VERSION, NEXT_NEXT_VERSION, V866, V867}:
        fail("VERSION.txt is not V863/V864/V865/V866/V867")
    if app_version_txt not in {VERSION, NEXT_VERSION, NEXT_NEXT_VERSION, V866, V867}:
        fail("APP_VERSION file is not V863/V864/V865/V866/V867")
    if not any(f"APP_VERSION = '{candidate}'" in app_py for candidate in {VERSION, NEXT_VERSION, NEXT_NEXT_VERSION, V866, V867}):
        fail("app.py APP_VERSION is not V863/V864/V865/V866/V867")
    if "has_v863_real_world_certification" not in app_py:
        fail("runtime flag V863 missing")
    if "data-v863-shell" not in base_html:
        fail("base.html missing data-v863-shell")
    if VERSION not in base_html and NEXT_VERSION not in base_html and NEXT_NEXT_VERSION not in base_html:
        fail("base.html cache/version marker missing V863/V864/V865/V866")

    critical_markers = [
        "has_v862_continuous_sentinel_loop",
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
    ]
    for marker in critical_markers:
        if marker not in app_py:
            fail(f"missing preserved marker {marker}")

    for report in REPORTS:
        if not (ROOT / "reports" / report).exists():
            fail(f"missing report {report}")

    if not (ROOT / "tools" / "check_v863_runtime_header_sanitization.py").exists():
        fail("missing header sanitization check")

    visible = "\n".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in [ROOT / "templates" / "base.html", ROOT / "static" / "app.css"]
        if p.exists()
    )
    for bad in ["Ã", "Â", ""]:
        if bad in visible:
            fail(f"visible shell contains suspicious token {bad}")

    forbidden_claims = ["apuesta segura", "garantizado", "sin riesgo", "fijo seguro"]
    if any(re.search(claim, visible, re.IGNORECASE) for claim in forbidden_claims):
        fail("irresponsible betting claim found in visible shell")

    secret_patterns = [
        r"sk_live_[A-Za-z0-9]",
        r"xox[baprs]-",
        r"TELEGRAM_BOT_TOKEN\s*=\s*['\"][^'\"]+",
        r"AUTOMATION_SECRET\s*=\s*['\"][^'\"]+",
    ]
    corpus = app_py + "\n" + base_html
    for pattern in secret_patterns:
        if re.search(pattern, corpus):
            fail(f"secret-looking value found: {pattern}")

    dangerous = ["git push", "render deploy", "auto_deploy=True", "send_real_telegram=True"]
    for token in dangerous:
        if token in app_py:
            fail(f"dangerous automatic action marker found: {token}")

    print("V863 real world certification OK")


if __name__ == "__main__":
    main()
