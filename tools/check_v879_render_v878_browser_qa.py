from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V879_FINAL_PRODUCT_UI_UX_LAYOUT_FUNCTIONALITY_POLISH_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"

REPORTS = [
    "V879_RENDER_DEPLOY_V878_BROWSER_QA_AND_LEGACY_REMOVAL_PLAN_REPORT.md",
    "V879_RENDER_V878_RUNTIME_QA.md",
    "V879_BROWSER_QA_REAL_SCREEN_CHECK.md",
    "V879_DEPRECATED_VISUAL_CLASS_USAGE_AUDIT.md",
    "V879_NS_SYSTEM_MIGRATION_QA.md",
    "V879_SENTINEL_LEGACY_RULES_QA.md",
    "V879_NEXT_LEGACY_REMOVAL_STEPS.md",
]

PRIMARY_TEMPLATES = [
    "home.html",
    "client_login.html",
    "register.html",
    "client_app_center.html",
    "calendar.html",
    "live.html",
    "picks.html",
    "shark.html",
    "telegram.html",
    "profile.html",
    "track_record.html",
    "admin_dashboard.html",
    "admin_continuous_sentinel.html",
    "admin_sentinel_workflow.html",
    "admin_fix_pipeline.html",
]

NS_TOKENS = [
    "ns-card",
    "ns-card-compact",
    "ns-button",
    "ns-button-primary",
    "ns-button-secondary",
    "ns-button-ghost",
    "ns-chip",
    "ns-badge",
    "ns-stat",
    "ns-table",
    "ns-empty",
    "ns-match-row",
    "ns-pick-card",
    "ns-admin-card",
    "ns-command-card",
    "ns-plan-card",
    "ns-sentinel-card",
    "ns-mobile-section",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def fail(message: str) -> None:
    raise SystemExit(f"V879 render/browser QA check FAILED: {message}")


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


def collect_templates() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (ROOT / "templates").rglob("*.html")
    )


def collect_primary_templates() -> str:
    chunks: list[str] = []
    for name in PRIMARY_TEMPLATES:
        path = ROOT / "templates" / name
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def main() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    partial = read("templates/partials/ui_components.html")
    sentinel = read("engines/continuous_shark_sentinel_engine.py")
    templates = collect_templates()
    primary_templates = collect_primary_templates()

    require(read("VERSION.txt").strip() == VERSION, "VERSION.txt is not V879")
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION file is not V879")
    require(f"APP_VERSION = '{VERSION}'" in app_py, "app.py APP_VERSION is not V879")
    require(VERSION in base, "base.html missing V879 version/cache")
    require('data-v879-shell="true"' in base, "base.html missing data-v879-shell")
    require("NEMESIS V879 FINAL PRODUCT UI UX LAYOUT FUNCTIONALITY POLISH FINAL ACTIVE" in base, "base.html missing V879 active comment")
    require("has_v879_render_v878_browser_qa" in app_py, "runtime V879 flag missing")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    for token in [
        "has_v878_ui_layer_purge_single_system",
        "has_v876_render_version_alignment",
        "has_v875_real_product_readiness",
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
        "has_v818_automation",
    ]:
        require(token in app_py, f"preserved runtime flag missing: {token}")

    for token in NS_TOKENS:
        require(token in css or token in partial, f"canonical ns token missing: {token}")

    require("V878 UI LAYER PURGE LEGACY CLEANUP SINGLE SYSTEM START" in css, "V878 CSS marker missing")
    require("v878-deprecated-visual-class" in partial, "deprecated bridge marker missing in partial")
    require("v878-deprecated-visual-class" not in primary_templates, "deprecated class used directly in primary screens")
    require("V878_LAYER_PURGE_RULES" in sentinel and "deprecated_visual_classes_in_primary_templates" in sentinel, "Sentinel V878 rules missing")

    for text in interactive_texts(base + primary_templates):
        require(not has_duplicate_words(text), f"duplicate visible button text: {text}")

    for bad in [">None<", ">null<", ">undefined<", "ÃƒÆ’", "Ãƒâ€š", "Ã¯Â¿Â½", "EspaÃ", "EspaÁ"]:
        require(bad not in app_py + templates, f"technical/mojibake token remains: {bad}")

    for bad in ["Stripe operativo", "Telegram filler", "OpenAI operativo", "apuesta segura", "garantizado", "apuesta fija", "sin riesgo"]:
        require(bad.lower() not in (app_py + templates).lower(), f"blocked phrase remains: {bad}")

    for secret_hint in ["sk_live_", "sk_test_", "x-apisports-key", "telegram_bot_token=", "openai_api_key="]:
        require(secret_hint.lower() not in (app_py + templates).lower(), f"secret-like literal found: {secret_hint}")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v879_runtime_check.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v879-check")
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
    payload = runtime.get_json() or json.loads(runtime.get_data(as_text=True))
    require(payload.get("app_version") == VERSION, "runtime app_version is not V879")
    require(payload.get("version_txt") == VERSION, "runtime version_txt is not V879")
    require(payload.get("has_v879_final_product_polish") is True, "runtime V879 final flag false")
    require(payload.get("has_v878_ui_layer_purge_single_system") is True, "runtime V878 flag false")
    require(payload.get("has_v818_automation") is True, "runtime V818 flag false")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names and "VERSION.txt" in names and "requirements.txt" in names, "ZIP missing required root files")
            require("templates/base.html" in names and "static/app.css" in names, "ZIP missing core UI files")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")
            require(not any(name.startswith(".git/") or name.startswith(".venv/") or name.startswith("release_output/") for name in names), "ZIP contains forbidden folder")
            require(not any(re.search(r"\.(db|sqlite|sqlite3|db-wal|db-shm|log|pyc|mp4|mov|avi|mkv)$", name, re.I) for name in names), "ZIP contains forbidden runtime/media file")

    print("V879 render deploy V878 browser QA and legacy removal plan OK")


if __name__ == "__main__":
    main()
