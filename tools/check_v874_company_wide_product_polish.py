from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V874_COMPANY_WIDE_PRODUCT_POLISH_VISUAL_DATA_SENTINEL_FINAL"
VERSION_V875 = "V881_SIDEBAR_NAV_DUPLICATION_ROOT_FIX_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"

REPORTS = [
    "V874_COMPANY_WIDE_PRODUCT_POLISH_VISUAL_DATA_SENTINEL_REPORT.md",
    "V874_PREFLIGHT_FROM_V873.md",
    "V874_PRODUCT_OWNER_COMPANY_REVIEW.md",
    "V874_RENDER_RUNTIME_AWARENESS_QA.md",
    "V874_CLIENT_PC_PRODUCT_POLISH_QA.md",
    "V874_MOBILE_PRODUCT_POLISH_QA.md",
    "V874_ADMIN_COMMAND_CENTER_PRODUCT_POLISH_QA.md",
    "V874_SENTINEL_WORKFLOW_COMPANY_QA.md",
    "V874_SHARK_SAFE_MODE_AND_VALUE_QA.md",
    "V874_LOGOS_CRESTS_FALLBACK_QA.md",
    "V874_PICKS_LIVE_MATCHES_STATE_QA.md",
    "V874_TELEGRAM_NO_FILLER_DEDUPE_QA.md",
    "V874_PAYMENTS_MEMBERSHIP_VALUE_QA.md",
    "V874_SPANISH_COPY_POLISH_QA.md",
    "V874_VISUAL_LAYER_CONTROL_QA.md",
    "V874_SENTINEL_RULES_AND_SCORE_QA.md",
    "V874_NEXT_COMPANY_STEPS.md",
]

FORBIDDEN_ZIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "release_output", "releases", "v636work", "tmp", "temp"}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def fail(message: str) -> None:
    raise SystemExit(f"V874 company-wide product polish check FAILED: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def visible_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style|template|svg|noscript)\b.*?</\1>", " ", html or "")
    text = re.sub(r"(?is)<!--.*?-->", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def interactive_texts(html: str) -> list[str]:
    return [
        visible_text(match.group(2))
        for match in re.finditer(r"(?is)<(a|button)\b[^>]*>(.*?)</\1>", html or "")
        if visible_text(match.group(2))
    ]


def has_duplicate_words(text: str) -> bool:
    words = [word.strip("·:|/-").lower() for word in text.split() if word.strip("·:|/-")]
    return any(words[index] == words[index + 1] for index in range(len(words) - 1))


def main() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    templates = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").glob("*.html"))
    visible_templates = visible_text(templates)

    valid_versions = {VERSION, VERSION_V875}
    require(read("VERSION.txt").strip() in valid_versions, "VERSION.txt is not V874/V875")
    require(read("APP_VERSION").strip() in valid_versions, "APP_VERSION is not V874/V875")
    require(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in valid_versions), "app.py APP_VERSION is not V874/V875")
    require(any(candidate in base for candidate in valid_versions), "base.html missing V874/V875 cache/version")
    require('data-v874-shell="true"' in base, "base.html missing data-v874-shell")
    require("NEMESIS V874 COMPANY WIDE PRODUCT POLISH VISUAL DATA SENTINEL FINAL ACTIVE" in base, "base.html missing V874 comment")
    require("has_v874_company_wide_product_polish" in app_py, "runtime V874 flag missing")
    require("V874 COMPANY WIDE PRODUCT POLISH VISUAL DATA SENTINEL FINAL START" in css, "CSS V874 marker missing")
    require("V874 COMPANY WIDE PRODUCT POLISH VISUAL DATA SENTINEL FINAL END" in css, "CSS V874 end marker missing")
    require("reports/V874_" in read("tools/build_clean_release.py"), "release builder does not include V874 reports")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    for token in [
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

    for bad in ["Ã", "Â", "�", "ðŸ", "âœ", "âš", "â—", "â†", "â˜", "âŒ", "â–", ">None<", ">null<", ">undefined<"]:
        require(bad not in app_py + templates, f"visible mojibake/technical token remains: {bad}")
    for bad in ["Stripe operativo", "Telegram filler", "apuesta segura", "garantizado", "apuesta fija", "sin riesgo"]:
        require(bad.lower() not in (app_py + templates).lower(), f"blocked phrase remains: {bad}")
    for secret_hint in ["sk_live_", "sk_test_", "x-apisports-key", "telegram_bot_token=", "openai_api_key="]:
        require(secret_hint.lower() not in (app_py + templates).lower(), f"secret-like literal found: {secret_hint}")
    for text in interactive_texts(base + templates):
        require(not has_duplicate_words(text), f"duplicate visible CTA text remains: {text}")

    require("Modo seguro activo" in templates, "OpenAI safe mode copy missing")
    require("Análisis limitado sin proveedor IA" in app_py + templates, "OpenAI limited analysis state missing")
    require("Escudo pendiente" in app_py + css + templates, "logo cache zero fallback state missing")
    require("Fallback premium activo" in app_py + reports_text(), "fallback premium state missing")
    require("No configurado" in templates, "payments/config safe state missing")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v874_runtime_check.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v874-check")
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
    payload = runtime.get_json() or json.loads(runtime.get_data(as_text=True))
    serialized = json.dumps(payload, ensure_ascii=False)
    require(payload.get("app_version") in valid_versions, "runtime app_version not V874/V875")
    require(payload.get("version_txt") in valid_versions, "runtime version_txt not V874/V875")
    require(payload.get("has_v874_company_wide_product_polish") is True, "runtime V874 flag false")
    require(payload.get("has_v873_real_production_visual_logos_shark_header") is True, "runtime V873 flag false")
    require(payload.get("has_v818_automation") is True, "runtime V818 flag false")
    require("Invalid header value b'" not in serialized, "runtime exposes raw invalid-header value")
    require(payload.get("openai_state") in {"Configurado", "SHARK IA avanzada pendiente de configuración"}, "runtime OpenAI state unsafe")
    require(payload.get("logo_cache_state") in {"Fallback premium activo", "Cache de logos disponible"}, "runtime logo cache state unsafe")
    require(client.get("/api/automation/master-tick?dry_run=1").status_code == 403, "master tick without secret is not 403")
    require(client.get("/api/automation/master-tick?dry_run=1&secret=codex-v874-check").status_code == 200, "master tick with secret is not 200")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names and "VERSION.txt" in names, "ZIP missing required files")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")
            require(not any(any(part in name.split("/") for part in FORBIDDEN_ZIP_PARTS) for name in names), "ZIP contains forbidden folder")
            require(not any(re.search(r"\.(db|sqlite|sqlite3|log|pyc|mp4|mov|avi|mkv)$", name, re.I) for name in names), "ZIP contains forbidden runtime/media file")

    print("V874 company-wide product polish OK")


def reports_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "reports").glob("V874_*.md"))


if __name__ == "__main__":
    main()



