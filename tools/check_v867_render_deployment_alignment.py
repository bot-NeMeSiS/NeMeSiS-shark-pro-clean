from __future__ import annotations

import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V867_RENDER_DEPLOYMENT_ALIGNMENT_AND_REAL_V866_CERTIFICATION_FINAL"
V866 = "V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL"
V868 = "V868_REAL_CLIENT_ADMIN_VISUAL_PRODUCTION_POLISH_AND_SENTINEL_VALUE_FINAL"
V868_PRO = "V868_PRO_MAX_CLIENT_ADMIN_MOBILE_VISUAL_REVENUE_SENTINEL_FINAL"
V869 = "V869_FULL_COMPANY_REFERENCE_ALIGNMENT_DEEP_CLEAN_VISUAL_REBUILD_FINAL"
V870 = "V870_REFERENCE_STYLE_MATCH_AND_WORKSPACE_PURGE_PRO_FINAL"
V870_PRO_MAX = "V870_REFERENCE_STYLE_MATCH_AND_WORKSPACE_PURGE_PRO_MAX_FINAL"
V871 = "V871_VISIBLE_UI_DEFECTS_EMPTY_SPACE_SCREEN_BY_SCREEN_PRO_MAX_FINAL"
V872 = "V872_REAL_RENDER_SCREEN_CAPTURE_REFERENCE_FINAL_PASS"
V873 = "V873_REAL_PRODUCTION_VISUAL_LOGOS_SHARK_HEADER_FINAL"
V874 = "V874_COMPANY_WIDE_PRODUCT_POLISH_VISUAL_DATA_SENTINEL_FINAL"
V875 = "V878_UI_LAYER_PURGE_LEGACY_CLEANUP_SINGLE_SYSTEM_FINAL"
ZIP_NAME = "NeMeSiS_SHARK_PRO_V867_RENDER_DEPLOYMENT_ALIGNMENT_AND_REAL_V866_CERTIFICATION_FINAL_RENDER_READY.zip"

REPORTS = [
    "V867_RENDER_DEPLOYMENT_ALIGNMENT_DIAGNOSIS.md",
    "V867_REPO_ROOT_AND_ZIP_STRUCTURE_QA.md",
    "V867_HEADER_SANITIZATION_DEPLOYMENT_QA.md",
    "V867_REAL_RENDER_RUNTIME_AFTER_DEPLOY_QA.md",
    "V867_REAL_PUBLIC_ROUTES_QA.md",
    "V867_REAL_SENTINEL_WORKFLOW_PRODUCTION_QA.md",
]


def fail(message: str) -> None:
    raise SystemExit(f"V867 deployment alignment FAILED: {message}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    build = read("tools/build_clean_release.py")

    require(read("VERSION.txt").strip() in {VERSION, V868, V868_PRO, V869, V870, V870_PRO_MAX, V871, V872, V873, V874, V875}, "VERSION.txt is not V867/V873")
    require(read("APP_VERSION").strip() in {VERSION, V868, V868_PRO, V869, V870, V870_PRO_MAX, V871, V872, V873, V874, V875}, "APP_VERSION is not V867/V873")
    require(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in {VERSION, V868, V868_PRO, V869, V870, V870_PRO_MAX, V871, V872, V873, V874, V875}), "app.py APP_VERSION is not V867/V873")
    require("has_v867_render_deployment_alignment" in app_py, "runtime V867 flag missing")
    require("has_v866_real_render_visual_telegram_picks_payments" in app_py, "V866 flag missing")
    require('data-v866-shell="true"' in base, "V866 shell marker missing")
    require('data-v867-shell="true"' in base, "V867 shell marker missing")
    require(VERSION in base or V868 in base or V868_PRO in base or V869 in base or V870 in base or V870_PRO_MAX in base or V871 in base or V872 in base or V873 in base or V874 in base or V875 in base, "base cache/version marker missing V867/V874")
    require("sanitize_runtime_error_value" in app_py, "header runtime sanitizer missing")
    require("reports/V867_" in build and "reports/RELEASE_ZIP_AUDIT_V867" in build, "release builder missing V867 reports")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v867_runtime_check.sqlite"))
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    response = client.get("/api/runtime-version")
    require(response.status_code == 200, f"runtime status {response.status_code}")
    payload = response.get_json() or {}
    require(payload.get("app_version") in {VERSION, V868, V868_PRO, V869, V870, V870_PRO_MAX, V871, V872, V873, V874, V875}, "runtime app_version not V867/V873")
    require(payload.get("version_txt") in {VERSION, V868, V868_PRO, V869, V870, V870_PRO_MAX, V871, V872, V873, V874, V875}, "runtime version_txt not V867/V873")
    require(payload.get("has_v867_render_deployment_alignment") is True, "runtime V867 flag false")
    require(payload.get("has_v866_real_render_visual_telegram_picks_payments") is True, "runtime V866 flag false")
    require("\n" not in str(payload.get("last_error", "")) and "\r" not in str(payload.get("last_error", "")), "runtime last_error contains unsafe newline")
    for header, value in response.headers.items():
        require("\n" not in str(value) and "\r" not in str(value), f"unsafe header value in {header}")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names, "ZIP missing root app.py")
            require("VERSION.txt" in names, "ZIP missing root VERSION.txt")
            require("templates/base.html" in names, "ZIP missing templates/base.html")
            require("static/app.css" in names, "ZIP missing static/app.css")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")
            require(not any(re.match(r"^[^/]+/.+/app\\.py$", name) for name in names), "ZIP appears nested")

    print("V867 render deployment alignment OK")


if __name__ == "__main__":
    main()





