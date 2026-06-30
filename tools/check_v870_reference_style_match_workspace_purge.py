from __future__ import annotations

import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V870_REFERENCE_STYLE_MATCH_AND_WORKSPACE_PURGE_PRO_FINAL"
VERSION_PRO_MAX = "V870_REFERENCE_STYLE_MATCH_AND_WORKSPACE_PURGE_PRO_MAX_FINAL"
ZIP_NAME = "NeMeSiS_SHARK_PRO_V870_REFERENCE_STYLE_MATCH_AND_WORKSPACE_PURGE_PRO_FINAL_RENDER_READY.zip"

REPORTS = [
    "V870_PREFLIGHT_FROM_V869.md",
    "V870_REFERENCE_STYLE_MATCH_AND_WORKSPACE_PURGE_REPORT.md",
    "V870_VIDEO_TO_REFERENCE_GAP_AUDIT.md",
    "V870_WORKSPACE_PURGE_AND_LEGACY_CONTROL_PLAN.md",
    "V870_RELEASE_CLEANER_HARDENING_QA.md",
    "V870_CLIENT_PC_REFERENCE_STYLE_QA.md",
    "V870_MOBILE_REFERENCE_STYLE_QA.md",
    "V870_ADMIN_COMMAND_CENTER_REFERENCE_STYLE_QA.md",
    "V870_SPORTS_PICKS_LIVE_REFERENCE_STYLE_QA.md",
    "V870_SHARK_TELEGRAM_MEMBERSHIP_REFERENCE_STYLE_QA.md",
    "V870_SENTINEL_EMPLOYEE_WORKFLOW_STYLE_QA.md",
    "V870_NEXT_REFERENCE_STYLE_STEPS.md",
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
    raise SystemExit(f"V870 reference style/workspace purge check FAILED: {message}")


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

    valid_versions = {VERSION, VERSION_PRO_MAX}
    current_version = read("VERSION.txt").strip()
    require(current_version in valid_versions, "VERSION.txt is not V870")
    require(read("APP_VERSION").strip() in valid_versions, "APP_VERSION is not V870")
    require(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in valid_versions), "app.py APP_VERSION is not V870")
    require(any(candidate in base for candidate in valid_versions), "base.html missing V870 cache/version")
    require('data-v870-shell="true"' in base, "base.html missing data-v870-shell")
    require("NEMESIS V870 REFERENCE STYLE MATCH AND WORKSPACE PURGE PRO" in base, "base.html missing V870 active comment")
    require("has_v870_reference_style_match_workspace_purge" in app_py, "runtime V870 flag missing")
    require("V870 REFERENCE STYLE MATCH AND WORKSPACE PURGE PRO" in css and "START" in css, "CSS V870 marker missing")
    require("V870 REFERENCE STYLE MATCH AND WORKSPACE PURGE PRO" in css and "END" in css, "CSS V870 end marker missing")
    require("v870_reference_widget" in ui and "v870-mini-chart" in ui, "V870 UI component markers missing")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    for token in [
        "has_v869_full_company_reference_alignment",
        "has_v868_real_client_admin_visual_polish",
        "has_v867_render_deployment_alignment",
        "has_v866_real_render_visual_telegram_picks_payments",
        "has_v865_sentinel_improvement_workflow",
        "has_v862_continuous_sentinel_loop",
        "has_v863_real_world_certification",
        "has_v857_company_os",
        "has_v850_live_crests_api_sports_match_detail",
        "has_v847_company_brain_api_sports_provider_qa",
        "has_v845_shark_ai_product_assistant",
        "has_v844_telegram_quality_filter",
        "has_v818_automation",
    ]:
        require(token in app_py, f"preserved runtime flag missing: {token}")

    for forbidden in FORBIDDEN_ZIP_PARTS:
        require(f'"{forbidden}"' in build or f'"{forbidden}"' in audit, f"release exclusion not declared for {forbidden}")
    require('".zip"' in build and 'lower_name.endswith(".zip")' in audit, "internal ZIP exclusion/audit missing")
    require('".db"' in build and '".sqlite"' in build, "DB exclusion missing")
    require('".mp4"' in build and '".mp4"' in audit, "video exclusion missing")

    client_templates = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").glob("*.html") if not path.name.startswith("admin"))
    for bad in ["Ã", "Â", "", ">None<", ">null<", ">undefined<"]:
        require(bad not in client_templates, f"bad visible client token found: {bad}")

    lower_templates = templates.lower()
    for phrase in ["apuesta segura", "garantizado", "apuesta fija", "fijo seguro"]:
        require(phrase not in lower_templates, f"irresponsible betting phrase found: {phrase}")
    require("Stripe operativo" not in templates, "false Stripe operative text found")
    require("Telegram filler" not in templates, "Telegram filler text found")
    require("body[data-v870-shell=\"true\"].ns-admin :is(.bottom-nav" in css, "admin client nav suppression missing")
    require("overflow-x: hidden" in css or "overflow-x: clip" in css, "mobile overflow guard missing")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v870_runtime_check.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v870-check")
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
    payload = runtime.get_json() or {}
    require(payload.get("app_version") in valid_versions, "runtime app_version not V870")
    require(payload.get("version_txt") in valid_versions, "runtime version_txt not V870")
    require(payload.get("has_v870_reference_style_match_workspace_purge") is True, "runtime V870 flag false")
    require(payload.get("has_v869_full_company_reference_alignment") is True, "runtime V869 flag false")
    require(payload.get("has_v818_automation") is True, "runtime V818 flag false")

    require(client.get("/api/automation/master-tick?dry_run=1").status_code == 403, "master tick without secret is not 403")
    require(client.get("/api/automation/master-tick?dry_run=1&secret=codex-v870-check").status_code == 200, "master tick with secret is not 200")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names, "ZIP missing app.py")
            require("VERSION.txt" in names, "ZIP missing VERSION.txt")
            require("templates/base.html" in names, "ZIP missing base.html")
            require("static/app.css" in names, "ZIP missing app.css")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")
            require(not any(any(part in name.split("/") for part in FORBIDDEN_ZIP_PARTS) for name in names), "ZIP contains forbidden folder")
            require(not any(re.search(r"\.(db|sqlite|sqlite3|log|pyc|mp4|mov|avi|mkv)$", name, re.I) for name in names), "ZIP contains forbidden runtime/media file")

    print("V870 reference style match and workspace purge OK")


if __name__ == "__main__":
    main()
