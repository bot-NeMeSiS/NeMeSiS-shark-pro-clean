from __future__ import annotations

import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V868_REAL_CLIENT_ADMIN_VISUAL_PRODUCTION_POLISH_AND_SENTINEL_VALUE_FINAL"
V868_PRO = "V868_PRO_MAX_CLIENT_ADMIN_MOBILE_VISUAL_REVENUE_SENTINEL_FINAL"
V869 = "V869_FULL_COMPANY_REFERENCE_ALIGNMENT_DEEP_CLEAN_VISUAL_REBUILD_FINAL"
V870 = "V870_REFERENCE_STYLE_MATCH_AND_WORKSPACE_PURGE_PRO_FINAL"
V870_PRO_MAX = "V870_REFERENCE_STYLE_MATCH_AND_WORKSPACE_PURGE_PRO_MAX_FINAL"
V871 = "V871_VISIBLE_UI_DEFECTS_EMPTY_SPACE_SCREEN_BY_SCREEN_PRO_MAX_FINAL"
V872 = "V872_REAL_RENDER_SCREEN_CAPTURE_REFERENCE_FINAL_PASS"
V873 = "V873_REAL_PRODUCTION_VISUAL_LOGOS_SHARK_HEADER_FINAL"
V874 = "V874_COMPANY_WIDE_PRODUCT_POLISH_VISUAL_DATA_SENTINEL_FINAL"
V875 = "V876_RENDER_VERSION_ALIGNMENT_AND_FINAL_VISUAL_DEPLOY_CHECK_FINAL"
ZIP_NAME = "NeMeSiS_SHARK_PRO_V868_REAL_CLIENT_ADMIN_VISUAL_PRODUCTION_POLISH_AND_SENTINEL_VALUE_FINAL_RENDER_READY.zip"

REPORTS = [
    "V868_PREFLIGHT_FROM_V867.md",
    "V868_REAL_VISUAL_GAP_AUDIT.md",
    "V868_REAL_CLIENT_ADMIN_VISUAL_PRODUCTION_POLISH_REPORT.md",
    "V868_CLIENT_PC_VISUAL_QA.md",
    "V868_CLIENT_MOBILE_VISUAL_QA.md",
    "V868_MOBILE_NO_HORIZONTAL_SCROLL_QA.md",
    "V868_PICKS_LIVE_STATE_QA.md",
    "V868_SHARK_TELEGRAM_VALUE_QA.md",
    "V868_ADMIN_COMMAND_CENTER_QA.md",
    "V868_SENTINEL_WORKFLOW_VALUE_QA.md",
    "V868_MEMBERSHIP_PAYMENT_VALUE_QA.md",
    "V868_NEXT_STEPS.md",
]


def fail(message: str) -> None:
    raise SystemExit(f"V868 visual production polish FAILED: {message}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    templates = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").glob("*.html"))
    admin_templates = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").glob("admin*.html"))
    client_templates = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").glob("*.html") if not path.name.startswith("admin"))

    valid_versions = {VERSION, V868_PRO, V869, V870, V870_PRO_MAX, V871, V872, V873, V874, V875}
    require(read("VERSION.txt").strip() in valid_versions, "VERSION.txt is not V868/V869")
    require(read("APP_VERSION").strip() in valid_versions, "APP_VERSION is not V868/V869")
    require(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in valid_versions), "app.py APP_VERSION is not V868/V869")
    require("has_v868_real_client_admin_visual_polish" in app_py, "runtime V868 flag missing")
    require('data-v868-shell="true"' in base, "base missing data-v868-shell")
    require(any(candidate in base for candidate in valid_versions), "base missing V868/V869 cache/version")
    require("V868 REAL CLIENT ADMIN VISUAL PRODUCTION POLISH START" in css, "CSS V868 start marker missing")
    require("V868 REAL CLIENT ADMIN VISUAL PRODUCTION POLISH END" in css, "CSS V868 end marker missing")

    for flag in [
        "has_v867_render_deployment_alignment",
        "has_v866_real_render_visual_telegram_picks_payments",
        "has_v865_sentinel_improvement_workflow",
        "has_v862_continuous_sentinel_loop",
        "has_v863_real_world_certification",
        "has_v818_automation",
    ]:
        require(flag in app_py, f"preserved runtime flag missing: {flag}")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    for bad in ["Ãƒ", "Ã‚", "ï¿½", "ESPAÃƒ", "EspaÁa"]:
        require(bad not in templates, f"visible mojibake found: {bad}")

    client_visible = re.sub(r"\{#[\s\S]*?#\}", "", client_templates)
    require(not re.search(r">\s*(None|null|undefined)\s*<", client_visible, re.I), "None/null/undefined visible in client HTML")
    require("Cuotas pendientes" in templates and "Selección pendiente" in templates and "Pick en revisión" in templates, "safe pick states missing")
    require("No configurado" in templates or "Acción pendiente" in templates, "payment/provider safe states missing")
    require("Stripe operativo" not in templates, "false Stripe operative copy found")
    require(not re.search(r"(apuesta segura|garantizado|apuesta fija|fijo seguro)", templates, re.I), "irresponsible betting claim found")
    require("body[data-v868-shell=\"true\"].ns-admin :is(.bottom-nav" in css, "admin client nav suppression missing")
    require("overflow-x: hidden" in css or "overflow-x: clip" in css, "horizontal overflow guard missing")
    require("/admin/continuous-sentinel" in base and "/admin/sentinel-workflow" in base, "Sentinel admin nav missing")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v868_runtime_check.sqlite"))
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    response = client.get("/api/runtime-version")
    require(response.status_code == 200, f"runtime status {response.status_code}")
    payload = response.get_json() or {}
    require(payload.get("app_version") in valid_versions, "runtime app_version not V868/V869")
    require(payload.get("version_txt") in valid_versions, "runtime version_txt not V868/V869")
    require(payload.get("has_v868_real_client_admin_visual_polish") is True, "runtime V868 flag false")
    require(payload.get("has_v867_render_deployment_alignment") is True, "runtime V867 flag false")
    require(payload.get("has_v866_real_render_visual_telegram_picks_payments") is True, "runtime V866 flag false")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names, "ZIP missing root app.py")
            require("VERSION.txt" in names, "ZIP missing root VERSION.txt")
            require("templates/base.html" in names, "ZIP missing templates/base.html")
            require("static/app.css" in names, "ZIP missing static/app.css")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")

    print("V868 real client/admin visual production polish OK")


if __name__ == "__main__":
    main()




