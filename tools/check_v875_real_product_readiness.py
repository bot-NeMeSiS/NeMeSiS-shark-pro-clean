from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V878_UI_LAYER_PURGE_LEGACY_CLEANUP_SINGLE_SYSTEM_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"

REPORTS = [
    "V875_REAL_PRODUCT_READINESS_RENDER_VISUAL_REVENUE_REPORT.md",
    "V875_RENDER_REAL_PRODUCT_READINESS_QA.md",
    "V875_CLIENT_PRODUCT_READINESS_QA.md",
    "V875_MOBILE_NATIVE_PRODUCT_QA.md",
    "V875_ADMIN_COMMAND_CENTER_PRODUCT_QA.md",
    "V875_SHARK_AI_PRODUCT_STATE_QA.md",
    "V875_LOGOS_CRESTS_PRODUCT_QA.md",
    "V875_PICKS_LIVE_PRODUCT_STATE_QA.md",
    "V875_TELEGRAM_PRODUCT_QA.md",
    "V875_REVENUE_MEMBERSHIP_PRODUCT_QA.md",
    "V875_SENTINEL_PRODUCT_WORKFLOW_QA.md",
    "V875_NEXT_STEPS.md",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def fail(message: str) -> None:
    raise SystemExit(f"V875 product readiness check FAILED: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def visible_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|template|svg|noscript)\b.*?</\1>", " ", html or "")
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def interactive_texts(html: str) -> list[str]:
    return [
        visible_text(match.group(2))
        for match in re.finditer(r"(?is)<(a|button)\b[^>]*>(.*?)</\1>", html or "")
        if visible_text(match.group(2))
    ]


def has_duplicate_words(text: str) -> bool:
    words = [word.strip("Â·:|/-").lower() for word in text.split() if word.strip("Â·:|/-")]
    return any(words[index] == words[index + 1] for index in range(len(words) - 1))


def main() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    templates = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").glob("*.html"))
    reports_text = "\n".join((ROOT / "reports" / name).read_text(encoding="utf-8", errors="replace") for name in REPORTS if (ROOT / "reports" / name).exists())

    require(read("VERSION.txt").strip() == VERSION, "VERSION.txt is not V875 product readiness")
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION is not V875 product readiness")
    require(f"APP_VERSION = '{VERSION}'" in app_py, "app.py APP_VERSION mismatch")
    require(VERSION in base, "base.html missing V875 cache/version")
    require('data-v875-shell="true"' in base, "base.html missing data-v875-shell")
    require("NEMESIS V875 REAL PRODUCT READINESS RENDER VISUAL REVENUE FINAL ACTIVE" in base, "base.html missing V875 readiness marker")
    require("has_v875_real_product_readiness" in app_py, "runtime V875 readiness flag missing")
    require("reports/V875_" in read("tools/build_clean_release.py"), "release builder missing V875 reports")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")
    require("V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL" in reports_text, "Render mismatch V855 not documented")
    require("BLOCKER" in reports_text, "Render blocker not documented")

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
        "has_v850_live_crests_api_sports_match_detail",
        "has_v847_company_brain_api_sports_provider_qa",
        "has_v845_shark_ai_product_assistant",
        "has_v844_telegram_quality_filter",
        "has_v818_automation",
    ]:
        require(token in app_py, f"preserved runtime flag missing: {token}")

    combined_visible = app_py + templates
    for bad in ["ÃƒÆ’", "Ãƒâ€š", "Ã¯Â¿Â½", "ÃƒÂ°Ã…Â¸", ">None<", ">null<", ">undefined<"]:
        require(bad not in combined_visible, f"visible mojibake/technical token remains: {bad}")
    for bad in ["Stripe operativo", "Telegram filler", "apuesta segura", "garantizado", "apuesta fija", "sin riesgo"]:
        require(bad.lower() not in combined_visible.lower(), f"blocked phrase remains: {bad}")
    for secret_hint in ["sk_live_", "sk_test_", "x-apisports-key", "telegram_bot_token=", "openai_api_key="]:
        require(secret_hint.lower() not in combined_visible.lower(), f"secret-like literal found: {secret_hint}")
    for text in interactive_texts(base + templates):
        require(not has_duplicate_words(text), f"duplicate visible CTA text remains: {text}")

    require("Modo seguro activo" in templates, "OpenAI safe mode copy missing")
    require("proveedor IA" in combined_visible and ("Modo seguro activo" in combined_visible or "Modo seguro" in combined_visible), "OpenAI limited analysis state missing")
    require("Escudo pendiente" in app_py + css + templates, "logo fallback state missing")
    require("Fallback premium activo" in app_py + reports_text, "fallback premium report/state missing")
    require("Cuota pendiente" in combined_visible, "pick pending odds state missing")
    require("SelecciÃ³n pendiente" in combined_visible or "Seleccion pendiente" in reports_text, "pick pending selection state missing")
    require("Pick en revisiÃ³n" in combined_visible or "Pick en revision" in reports_text, "pick review state missing")
    require("No configurado" in templates, "payments/config safe state missing")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v875_product_readiness_check.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v875-product-readiness")
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
    payload = runtime.get_json() or json.loads(runtime.get_data(as_text=True))
    serialized = json.dumps(payload, ensure_ascii=False)
    require(payload.get("app_version") == VERSION, "runtime app_version mismatch")
    require(payload.get("version_txt") == VERSION, "runtime version_txt mismatch")
    require(payload.get("has_v875_real_product_readiness") is True, "runtime readiness flag false")
    require(payload.get("has_v874_company_wide_product_polish") is True, "runtime V874 flag false")
    require(payload.get("has_v818_automation") is True, "runtime V818 flag false")
    require("Invalid header value b'" not in serialized, "runtime exposes raw invalid-header value")
    require(client.get("/api/automation/master-tick?dry_run=1").status_code == 403, "master tick without secret is not 403")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names and "VERSION.txt" in names, "ZIP missing required root files")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")
            require(not any(re.search(r"\.(db|sqlite|sqlite3|log|pyc|mp4|mov|avi|mkv)$", name, re.I) for name in names), "ZIP contains forbidden runtime/media file")

    print("V875 real product readiness OK")


if __name__ == "__main__":
    main()


