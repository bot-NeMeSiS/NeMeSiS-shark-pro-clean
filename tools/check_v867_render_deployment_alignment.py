from __future__ import annotations

import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V867_RENDER_DEPLOYMENT_ALIGNMENT_AND_REAL_V866_CERTIFICATION_FINAL"
V866 = "V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL"
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

    require(read("VERSION.txt").strip() == VERSION, "VERSION.txt is not V867")
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION is not V867")
    require(f"APP_VERSION = '{VERSION}'" in app_py, "app.py APP_VERSION is not V867")
    require("has_v867_render_deployment_alignment" in app_py, "runtime V867 flag missing")
    require("has_v866_real_render_visual_telegram_picks_payments" in app_py, "V866 flag missing")
    require('data-v866-shell="true"' in base, "V866 shell marker missing")
    require('data-v867-shell="true"' in base, "V867 shell marker missing")
    require(VERSION in base, "base cache/version marker missing V867")
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
    require(payload.get("app_version") == VERSION, "runtime app_version not V867")
    require(payload.get("version_txt") == VERSION, "runtime version_txt not V867")
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
