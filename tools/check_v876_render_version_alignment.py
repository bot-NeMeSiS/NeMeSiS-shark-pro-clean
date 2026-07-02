from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V884_CLIENT_ADMIN_FUNCTIONAL_FLOW_AND_SCREEN_EXPERIENCE_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def fail(message: str) -> None:
    raise SystemExit(f"V876 render alignment check FAILED: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    reports = "\n".join(
        (ROOT / "reports" / name).read_text(encoding="utf-8", errors="replace")
        for name in [
            "V876_RENDER_VERSION_ALIGNMENT_DIAGNOSIS.md",
            "V876_GITHUB_ROOT_DEPLOYMENT_QA.md",
            "V876_RENDER_VERSION_ALIGNMENT_REPORT.md",
        ]
        if (ROOT / "reports" / name).exists()
    )

    require(read("VERSION.txt").strip() == VERSION, "VERSION.txt is not V876")
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION is not V876")
    require(f"APP_VERSION = '{VERSION}'" in app_py, "app.py APP_VERSION is not V876")
    require(VERSION in base, "base.html missing V876 version/cache")
    require('data-v876-shell="true"' in base, "base.html missing data-v876-shell")
    require("has_v876_render_version_alignment" in app_py, "runtime V876 flag missing")
    require("has_v875_real_product_readiness" in app_py, "V875 readiness flag not preserved")

    for report in [
        "V876_RENDER_VERSION_ALIGNMENT_DIAGNOSIS.md",
        "V876_GITHUB_ROOT_DEPLOYMENT_QA.md",
        "V876_RENDER_VERSION_ALIGNMENT_REPORT.md",
    ]:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")
    require("V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL" in reports, "real Render mismatch not documented")
    require("Clear build cache & deploy" in reports, "exact Render deploy action missing")
    require("gunicorn app:app" in reports, "start command guidance missing")

    for token in [
        "has_v874_company_wide_product_polish",
        "has_v873_real_production_visual_logos_shark_header",
        "has_v872_real_screen_capture_reference_pass",
        "has_v871_visible_ui_empty_space_screen_fix",
        "has_v870_reference_style_match_workspace_purge",
        "has_v869_full_company_reference_alignment",
        "has_v868_real_client_admin_visual_polish",
        "has_v867_render_deployment_alignment",
        "has_v866_real_render_visual_telegram_picks_payments",
        "has_v865_sentinel_improvement_workflow",
        "has_v862_continuous_sentinel_loop",
        "has_v863_real_world_certification",
        "has_v857_company_os",
        "has_v847_company_brain_api_sports_provider_qa",
        "has_v845_shark_ai_product_assistant",
        "has_v844_telegram_quality_filter",
        "has_v818_automation",
    ]:
        require(token in app_py, f"preserved flag missing: {token}")

    for required in ["app.py", "VERSION.txt", "render.yaml", "Procfile"]:
        require((ROOT / required).exists(), f"missing root file {required}")
    for bad in ["sk_live_", "sk_test_", "x-apisports-key", "telegram_bot_token=", "openai_api_key="]:
        require(bad.lower() not in (app_py + base).lower(), f"secret-like literal found: {bad}")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v876_runtime_check.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v876-check")
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
    payload = runtime.get_json() or json.loads(runtime.get_data(as_text=True))
    require(payload.get("app_version") == VERSION, "runtime app_version is not V876")
    require(payload.get("version_txt") == VERSION, "runtime version_txt is not V876")
    require(payload.get("has_v876_render_version_alignment") is True, "runtime V876 flag false")
    require(payload.get("has_v875_real_product_readiness") is True, "runtime V875 flag false")
    require(payload.get("has_v818_automation") is True, "runtime V818 flag false")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names, "ZIP missing root app.py")
            require("VERSION.txt" in names, "ZIP missing root VERSION.txt")
            require("render.yaml" in names, "ZIP missing root render.yaml")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")
            require(not any("/NeMeSiS shark pro/" in name or name.startswith("NeMeSiS shark pro/") for name in names), "ZIP contains nested project")
            require(not any(re.search(r"\.(db|sqlite|sqlite3|db-wal|db-shm|log|pyc|mp4|mov|avi|mkv)$", name, re.I) for name in names), "ZIP contains forbidden runtime/media file")
            require(zf.read("VERSION.txt").decode("utf-8-sig").strip() == VERSION, "ZIP VERSION.txt is not V876")

    print("V876 render version alignment OK")


if __name__ == "__main__":
    main()





