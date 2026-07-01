from __future__ import annotations

import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V868_PRO_MAX_CLIENT_ADMIN_MOBILE_VISUAL_REVENUE_SENTINEL_FINAL"
ZIP_NAME = "NeMeSiS_SHARK_PRO_V868_PRO_MAX_CLIENT_ADMIN_MOBILE_VISUAL_REVENUE_SENTINEL_FINAL_RENDER_READY.zip"

REPORTS = [
    "V868_PRO_MAX_PREFLIGHT_FROM_V867.md",
    "V868_PRODUCT_CEO_PRO_MAX_REVIEW.md",
    "V868_MOBILE_APP_NATIVE_PRO_QA.md",
    "V868_RENDER_PRODUCTION_AWARENESS_QA.md",
    "V868_SENTINEL_SCORE_AND_WORKFLOW_QA.md",
    "V868_PRO_MAX_CLIENT_ADMIN_MOBILE_VISUAL_REVENUE_SENTINEL_REPORT.md",
    "V868_CLIENT_PC_PRO_DASHBOARD_QA.md",
    "V868_PICKS_LIVE_REVENUE_QA.md",
    "V868_SHARK_TELEGRAM_PRO_VALUE_QA.md",
    "V868_ADMIN_COMMAND_CENTER_PRO_QA.md",
    "V868_SENTINEL_WORKFLOW_PRO_QA.md",
    "V868_MEMBERSHIP_REVENUE_QA.md",
    "V868_NEXT_PRO_MAX_STEPS.md",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def fail(message: str) -> None:
    raise SystemExit(f"V868 Pro Max check FAILED: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    ui = read("templates/partials/ui_components.html")

    require(read("VERSION.txt").strip() == VERSION, "VERSION.txt is not V868 Pro Max")
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION is not V868 Pro Max")
    require(f"APP_VERSION = '{VERSION}'" in app_py, "app.py APP_VERSION is not V868 Pro Max")
    require(VERSION in base, "base.html missing V868 Pro Max cache/version")
    require('data-v868-shell="true"' in base, "base.html missing data-v868-shell")
    require("NEMESIS V868 PRO MAX CLIENT ADMIN MOBILE VISUAL REVENUE SENTINEL ACTIVE" in base, "base.html missing Pro Max comment")
    require("has_v868_pro_max_client_admin_mobile_visual_revenue_sentinel" in app_py, "runtime Pro Max flag missing")
    require("V868 PRO MAX CLIENT ADMIN MOBILE VISUAL REVENUE SENTINEL START" in css, "CSS Pro Max start marker missing")
    require("V868 PRO MAX CLIENT ADMIN MOBILE VISUAL REVENUE SENTINEL END" in css, "CSS Pro Max end marker missing")
    require("v868-pro-" in ui, "shared UI components missing Pro Max classes")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    for token in [
        "has_v867_render_deployment_alignment",
        "has_v866_real_render_visual_telegram_picks_payments",
        "has_v865_sentinel_improvement_workflow",
        "has_v862_continuous_sentinel_loop",
        "has_v859_company_audit_board",
        "has_v857_company_os",
        "has_v850_live_crests_api_sports_match_detail",
        "has_v847_company_brain_api_sports_provider_qa",
        "has_v845_shark_ai_product_assistant",
        "has_v844_telegram_quality_filter",
        "has_v818_automation",
    ]:
        require(token in app_py, f"preserved runtime flag missing: {token}")

    visible = "\n".join(read(path) for path in [
        "templates/base.html",
        "templates/partials/ui_components.html",
        "templates/admin_sentinel_workflow.html",
        "templates/admin_continuous_sentinel.html",
        "static/app.css",
    ])
    for bad in ["Ã", "Â", "", "None visible", ">None<", ">null<", ">undefined<"]:
        require(bad not in visible, f"visible bad token found: {bad}")

    lower_visible = visible.lower()
    for phrase in ["apuesta segura", "garantizado", "apuesta fija", "sin riesgo"]:
        require(phrase not in lower_visible, f"irresponsible betting copy found: {phrase}")

    for safe_state in ["Cuotas pendientes", "Selección pendiente", "Pick en revisión", "Sin directos reales"]:
        require(safe_state in app_py or safe_state in visible, f"safe state missing: {safe_state}")

    for secret_pattern in ["TELEGRAM_BOT_TOKEN =", "OPENAI_API_KEY =", "STRIPE_SECRET_KEY =", "AUTOMATION_SECRET ="]:
        require(secret_pattern not in app_py, f"possible secret assignment found: {secret_pattern}")

    require(".ns-admin :is(.bottom-nav" in css or ".ns-admin :is(.bottom-nav," in css, "admin bottom nav suppression missing")
    require("static_css_cache_busting" in app_py, "runtime cache-busting field missing")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v868_pro_max_check.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v868-pro-max-check")
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
    payload = runtime.get_json() or {}
    require(payload.get("app_version") == VERSION, "runtime app_version not Pro Max")
    require(payload.get("version_txt") == VERSION, "runtime version_txt not Pro Max")
    require(payload.get("has_v868_pro_max_client_admin_mobile_visual_revenue_sentinel") is True, "runtime Pro Max flag false")
    require(payload.get("has_v867_render_deployment_alignment") is True, "runtime V867 flag false")
    require(payload.get("has_v818_automation") is True, "runtime V818 flag false")

    no_secret = client.get("/api/automation/master-tick?dry_run=1")
    require(no_secret.status_code == 403, "master tick without secret is not 403")
    with_secret = client.get("/api/automation/master-tick?dry_run=1&secret=codex-v868-pro-max-check")
    require(with_secret.status_code == 200, "master tick dry-run with secret is not 200")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names, "ZIP missing app.py")
            require("VERSION.txt" in names, "ZIP missing VERSION.txt")
            require("templates/base.html" in names, "ZIP missing base.html")
            require("static/app.css" in names, "ZIP missing app.css")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")
            require(not any(re.match(r"(^|/)(\\.git|\\.venv|__pycache__|\\.pytest_cache)(/|$)", name) for name in names), "ZIP contains forbidden cache/git/venv")

    print("V868 Pro Max client/admin/mobile visual revenue Sentinel OK")


if __name__ == "__main__":
    main()
