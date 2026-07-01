from __future__ import annotations

import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V869_FULL_COMPANY_REFERENCE_ALIGNMENT_DEEP_CLEAN_VISUAL_REBUILD_FINAL"
V870 = "V870_REFERENCE_STYLE_MATCH_AND_WORKSPACE_PURGE_PRO_FINAL"
V870_PRO_MAX = "V870_REFERENCE_STYLE_MATCH_AND_WORKSPACE_PURGE_PRO_MAX_FINAL"
V871 = "V871_VISIBLE_UI_DEFECTS_EMPTY_SPACE_SCREEN_BY_SCREEN_PRO_MAX_FINAL"
V872 = "V872_REAL_RENDER_SCREEN_CAPTURE_REFERENCE_FINAL_PASS"
V873 = "V873_REAL_PRODUCTION_VISUAL_LOGOS_SHARK_HEADER_FINAL"
V874 = "V874_COMPANY_WIDE_PRODUCT_POLISH_VISUAL_DATA_SENTINEL_FINAL"
V875 = "V875_REAL_PRODUCT_READINESS_RENDER_VISUAL_REVENUE_FINAL"
ZIP_NAME = "NeMeSiS_SHARK_PRO_V869_FULL_COMPANY_REFERENCE_ALIGNMENT_DEEP_CLEAN_VISUAL_REBUILD_FINAL_RENDER_READY.zip"

REPORTS = [
    "V869_PREFLIGHT_FROM_V868.md",
    "V869_FULL_COMPANY_REFERENCE_ALIGNMENT_REPORT.md",
    "V869_FULL_PROJECT_TREE_HIDDEN_FILES_AUDIT.md",
    "V869_DEEP_CLEANUP_ACTION_PLAN.md",
    "V869_VIDEO_REAL_VS_REFERENCE_VISUAL_AUDIT.md",
    "V869_CLIENT_PC_REFERENCE_ALIGNMENT_QA.md",
    "V869_MOBILE_REFERENCE_ALIGNMENT_QA.md",
    "V869_ADMIN_REFERENCE_COMMAND_CENTER_QA.md",
    "V869_VISUAL_COMPONENTS_REFERENCE_SYSTEM.md",
    "V869_PICKS_LIVE_SPORTS_VISUAL_RICHNESS_QA.md",
    "V869_SHARK_TELEGRAM_MEMBERSHIP_VALUE_QA.md",
    "V869_SENTINEL_WORKFLOW_COMPANY_EMPLOYEE_QA.md",
    "V869_RELEASE_CLEANLINESS_AND_LEGACY_PURGE_QA.md",
    "V869_NEXT_COMPANY_STEPS.md",
]

FORBIDDEN_ZIP_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "release_output",
    "releases",
    "v636work",
    "logs",
    "tmp",
    "temp",
}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def fail(message: str) -> None:
    raise SystemExit(f"V869 reference alignment check FAILED: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    ui = read("templates/partials/ui_components.html")
    build = read("tools/build_clean_release.py")
    audit = read("tools/audit_release_zip.py")
    templates = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").glob("*.html"))

    valid_versions = {VERSION, V870, V870_PRO_MAX, V871, V872, V873, V874, V875}
    require(read("VERSION.txt").strip() in valid_versions, "VERSION.txt is not V869/V870")
    require(read("APP_VERSION").strip() in valid_versions, "APP_VERSION is not V869/V870")
    require(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in valid_versions), "app.py APP_VERSION is not V869/V870")
    require(any(candidate in base for candidate in valid_versions), "base.html missing V869/V870 cache/version")
    require('data-v869-shell="true"' in base, "base.html missing data-v869-shell")
    require("NEMESIS V869 FULL COMPANY REFERENCE ALIGNMENT DEEP CLEAN VISUAL REBUILD ACTIVE" in base, "base.html missing V869 active comment")
    require("has_v869_full_company_reference_alignment" in app_py, "runtime V869 flag missing")
    require("V869 FULL COMPANY REFERENCE ALIGNMENT DEEP CLEAN VISUAL REBUILD START" in css, "CSS V869 marker missing")
    require("V869 FULL COMPANY REFERENCE ALIGNMENT DEEP CLEAN VISUAL REBUILD END" in css, "CSS V869 end marker missing")
    require("reference_dashboard_card" in ui and "v869-reference" in ui, "V869 reference component macros missing")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    for token in [
        "has_v868_real_client_admin_visual_polish",
        "has_v868_pro_max_client_admin_mobile_visual_revenue_sentinel",
        "has_v867_render_deployment_alignment",
        "has_v866_real_render_visual_telegram_picks_payments",
        "has_v865_sentinel_improvement_workflow",
        "has_v862_continuous_sentinel_loop",
        "has_v863_real_world_certification",
        "has_v859_company_audit_board",
        "has_v857_company_os",
        "has_v850_live_crests_api_sports_match_detail",
        "has_v847_company_brain_api_sports_provider_qa",
        "has_v845_shark_ai_product_assistant",
        "has_v844_telegram_quality_filter",
        "has_v818_automation",
    ]:
        require(token in app_py, f"preserved flag missing: {token}")

    for forbidden in FORBIDDEN_ZIP_PARTS:
        require(f'"{forbidden}"' in build or f'"{forbidden}"' in audit, f"release exclusion not declared for {forbidden}")

    for bad in ["Ãƒ", "Ã‚", "ï¿½", ">None<", ">null<", ">undefined<"]:
        require(bad not in templates, f"bad visible token in templates: {bad}")

    lower_templates = templates.lower()
    for phrase in ["apuesta segura", "garantizado", "apuesta fija", "sin riesgo"]:
        require(phrase not in lower_templates, f"irresponsible betting phrase found: {phrase}")
    require("Stripe operativo" not in templates, "false Stripe operative text found")
    require("Telegram filler" not in templates, "Telegram filler text found")
    require("body[data-v869-shell=\"true\"].ns-admin :is(.bottom-nav" in css, "admin client nav suppression missing")
    require("overflow-x: hidden" in css or "overflow-x: clip" in css, "mobile overflow guard missing")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v869_runtime_check.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v869-check")
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
    payload = runtime.get_json() or {}
    require(payload.get("app_version") in valid_versions, "runtime app_version not V869/V870")
    require(payload.get("version_txt") in valid_versions, "runtime version_txt not V869/V870")
    require(payload.get("has_v869_full_company_reference_alignment") is True, "runtime V869 flag false")
    require(payload.get("has_v868_real_client_admin_visual_polish") is True, "runtime V868 flag false")
    require(payload.get("has_v867_render_deployment_alignment") is True, "runtime V867 flag false")
    require(payload.get("has_v818_automation") is True, "runtime V818 flag false")

    no_secret = client.get("/api/automation/master-tick?dry_run=1")
    require(no_secret.status_code == 403, "master tick without secret is not 403")
    with_secret = client.get("/api/automation/master-tick?dry_run=1&secret=codex-v869-check")
    require(with_secret.status_code == 200, "master tick dry-run with secret is not 200")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names, "ZIP missing app.py")
            require("VERSION.txt" in names, "ZIP missing VERSION.txt")
            require("templates/base.html" in names, "ZIP missing templates/base.html")
            require("static/app.css" in names, "ZIP missing static/app.css")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")
            require(not any(any(part in name.split("/") for part in FORBIDDEN_ZIP_PARTS) for name in names), "ZIP contains forbidden folder")
            require(not any(re.search(r"\.(db|sqlite|sqlite3|log|pyc)$", name, re.I) for name in names), "ZIP contains forbidden runtime file")

    print("V869 full company reference alignment OK")


if __name__ == "__main__":
    main()



