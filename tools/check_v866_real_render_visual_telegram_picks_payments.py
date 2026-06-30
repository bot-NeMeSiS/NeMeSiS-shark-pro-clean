from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL"
V867 = "V867_RENDER_DEPLOYMENT_ALIGNMENT_AND_REAL_V866_CERTIFICATION_FINAL"
V868 = "V868_REAL_CLIENT_ADMIN_VISUAL_PRODUCTION_POLISH_AND_SENTINEL_VALUE_FINAL"

REPORTS = [
    "V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_REPORT.md",
    "V866_RENDER_REAL_VS_LOCAL_RUNTIME_AUDIT.md",
    "V866_HEADER_INVALID_VALUE_HOTFIX_REPORT.md",
    "V866_MOBILE_REAL_VISUAL_QA.md",
    "V866_TELEGRAM_REAL_DELIVERY_AND_NO_FILLER_QA.md",
    "V866_PICKS_ODDS_STATE_QA.md",
    "V866_PAYMENTS_MEMBERSHIPS_STRIPE_CONFIG_QA.md",
    "V866_SENTINEL_WORKFLOW_FOLLOWUP.md",
]


def fail(message: str) -> None:
    raise SystemExit(f"V866 product QA FAILED: {message}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> None:
    version_txt = read("VERSION.txt").strip()
    app_version = read("APP_VERSION").strip()
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    build = read("tools/build_clean_release.py")
    combined_templates = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").glob("*.html"))

    require(version_txt in {VERSION, V867, V868}, "VERSION.txt not V866/V867/V868")
    require(app_version in {VERSION, V867, V868}, "APP_VERSION not V866/V867/V868")
    require(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in {VERSION, V867, V868}), "app.py APP_VERSION not V866/V867/V868")
    require('data-v866-shell="true"' in base, "base missing V866 shell")
    require("has_v866_real_render_visual_telegram_picks_payments" in app_py, "runtime V866 flag missing")
    require("V866 REAL RENDER VISUAL TELEGRAM PICKS PAYMENTS HOTFIX QA START" in css, "CSS V866 marker missing")
    require("overflow-x: hidden" in css and "max-width: 100%" in css, "mobile overflow guard missing")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")
    require("reports/V866_" in build, "release builder does not include V866 reports")
    require("reports/RELEASE_ZIP_AUDIT_V866" in build, "release builder does not include V866 zip audit")

    for marker in [
        "has_v865_sentinel_improvement_workflow",
        "has_v862_continuous_sentinel_loop",
        "has_v863_real_world_certification",
        "has_v818_automation",
        "telegram_quality_filter_engine",
        "shark_ai_product_assistant_engine",
        "api_sports_provider_engine",
    ]:
        require(marker in app_py, f"preserved marker missing: {marker}")

    for text in ["Cuota pendiente", "Selección pendiente", "Pick en revisión", "Sin pick real publicado", "Proveedor sin datos ahora mismo"]:
        require(text in app_py or text in combined_templates, f"safe pick/provider state missing: {text}")

    bad_visible = ["ESPAÃ", "Ã", "Â", "�"]
    for bad in bad_visible:
        require(bad not in combined_templates, f"visible mojibake found: {bad}")

    lower_templates = combined_templates.lower()
    for risky in ["apuesta segura", "garantizado", "apuesta fija"]:
        require(risky not in lower_templates, f"irresponsible betting copy found: {risky}")
    require(re.search(r"\bsin riesgo\b", lower_templates) is None, "irresponsible betting copy found: sin riesgo")

    for secret_hint in ["sk_live_", "sk_test_", "x-apisports-key", "telegram_bot_token="]:
        require(secret_hint.lower() not in (app_py + combined_templates).lower(), f"secret-like literal found: {secret_hint}")

    require("/api/admin/sentinel-workflow/summary" in app_py, "admin sentinel summary route missing")
    require("/api/automation/master-tick" in app_py, "master tick route missing")
    require("no filler" in (app_py + read("engines/telegram_quality_filter_engine.py")).lower() or "SKIPPED_NO_TOP_MATCHES" in app_py, "Telegram no filler marker missing")
    require("sanitize_runtime_error_value" in app_py, "header invalid value hotfix missing")

    print("V866 real render/visual/telegram/picks/payments QA OK")


if __name__ == "__main__":
    main()
