from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V873_REAL_PRODUCTION_VISUAL_LOGOS_SHARK_HEADER_FINAL"
VERSION_V874 = "V874_COMPANY_WIDE_PRODUCT_POLISH_VISUAL_DATA_SENTINEL_FINAL"
VERSION_V875 = "V878_UI_LAYER_PURGE_LEGACY_CLEANUP_SINGLE_SYSTEM_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"

REPORTS = [
    "V873_REAL_PRODUCTION_VISUAL_LOGOS_SHARK_HEADER_REPORT.md",
    "V873_PREFLIGHT_FROM_V872_AND_RENDER_V871.md",
    "V873_REAL_RENDER_RUNTIME_QA.md",
    "V873_INVALID_HEADER_ROOT_CAUSE_FIX.md",
    "V873_SHARK_OPENAI_CONFIG_STATE_QA.md",
    "V873_LOGO_CREST_CACHE_ZERO_QA.md",
    "V873_REAL_PRODUCTION_VISUAL_QA.md",
    "V873_SENTINEL_RUNTIME_VISUAL_RULES_QA.md",
    "V873_NEXT_STEPS.md",
]

FORBIDDEN_ZIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "release_output", "releases", "v636work", "tmp", "temp"}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def fail(message: str) -> None:
    raise SystemExit(f"V873 production visual/logos/SHARK check FAILED: {message}")


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
    shark = read("templates/shark.html")
    admin_shark = read("templates/admin_shark_center.html")
    team_identity = read("templates/partials/team_identity.html")
    provider_engine = read("engines/api_sports_provider_engine.py")
    templates = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").glob("*.html"))

    require(read("VERSION.txt").strip() in {VERSION, VERSION_V874, VERSION_V875}, "VERSION.txt is not V873/V874")
    require(read("APP_VERSION").strip() in {VERSION, VERSION_V874, VERSION_V875}, "APP_VERSION is not V873/V874")
    require(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in {VERSION, VERSION_V874, VERSION_V875}), "app.py APP_VERSION is not V873/V874")
    require(VERSION in base or VERSION_V874 in base or VERSION_V875 in base, "base.html missing V873/V874 cache/version")
    require('data-v873-shell="true"' in base, "base.html missing data-v873-shell")
    require("NEMESIS V873 REAL PRODUCTION VISUAL LOGOS SHARK HEADER FINAL ACTIVE" in base, "base.html missing V873 comment")
    require("has_v873_real_production_visual_logos_shark_header" in app_py, "runtime V873 flag missing")
    require("V873 REAL PRODUCTION VISUAL LOGOS SHARK HEADER FINAL START" in css, "CSS V873 marker missing")
    require("V873 REAL PRODUCTION VISUAL LOGOS SHARK HEADER FINAL END" in css, "CSS V873 end marker missing")
    require("sanitize_provider_error" in provider_engine, "provider error sanitizer missing")
    require("last_error_state" in app_py, "runtime last_error_state missing")
    require("openai_state" in app_py and "shark_ai_mode" in app_py and "shark_ai_note" in app_py, "OpenAI/SHARK safe state missing")
    require("SHARK IA avanzada pendiente de configuración" in app_py + shark + admin_shark, "SHARK OpenAI pending state missing")
    require("logo_cache_state" in app_py and "logo_cache_note" in app_py, "logo cache safe state missing")
    require("data-real-logo" in team_identity and "crest-image-error" in team_identity, "team crest fallback markers missing")
    require("data-real-logo=\"false\"" in css and "Fallback premium activo" in app_py, "logo fallback CSS/state missing")
    require("reports/V873_" in read("tools/build_clean_release.py"), "release builder does not include V873 reports")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    for token in [
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

    for bad in ["\u00c3", "\u00c2", "\ufffd", "Conexin", "vinculacin", "cdigo", "Enva"]:
        require(bad not in base + shark + admin_shark, f"visible mojibake/copy defect remains: {bad}")
    for text in interactive_texts(base + shark + admin_shark):
        require(not has_duplicate_words(text), f"duplicate visible CTA text remains: {text}")

    lower = templates.lower()
    for phrase in ["apuesta segura", "garantizado", "apuesta fija", "fijo seguro", "sin riesgo"]:
        require(phrase not in lower, f"irresponsible betting phrase found: {phrase}")
    require("Stripe operativo" not in templates, "false Stripe operative text found")
    require("Telegram filler" not in templates, "Telegram filler text found")
    for secret_hint in ["sk_live_", "sk_test_", "x-apisports-key", "telegram_bot_token=", "openai_api_key="]:
        require(secret_hint.lower() not in (app_py + templates).lower(), f"secret-like literal found: {secret_hint}")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v873_runtime_check.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v873-check")
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
    payload = runtime.get_json() or json.loads(runtime.get_data(as_text=True))
    serialized = json.dumps(payload, ensure_ascii=False)
    require(payload.get("app_version") in {VERSION, VERSION_V874, VERSION_V875}, "runtime app_version not V873/V874")
    require(payload.get("version_txt") in {VERSION, VERSION_V874, VERSION_V875}, "runtime version_txt not V873/V874")
    require(payload.get("has_v873_real_production_visual_logos_shark_header") is True, "runtime V873 flag false")
    require(payload.get("has_v872_real_screen_capture_reference_pass") is True, "runtime V872 flag false")
    require(payload.get("has_v818_automation") is True, "runtime V818 flag false")
    require("Invalid header value b'" not in serialized, "runtime exposes raw invalid-header value")
    require(payload.get("openai_state") in {"Configurado", "SHARK IA avanzada pendiente de configuración"}, "runtime OpenAI state unsafe")
    require(payload.get("logo_cache_state") in {"Fallback premium activo", "Cache de logos disponible"}, "runtime logo cache state unsafe")
    require(client.get("/api/automation/master-tick?dry_run=1").status_code == 403, "master tick without secret is not 403")
    require(client.get("/api/automation/master-tick?dry_run=1&secret=codex-v873-check").status_code == 200, "master tick with secret is not 200")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names and "VERSION.txt" in names, "ZIP missing required files")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")
            require(not any(any(part in name.split("/") for part in FORBIDDEN_ZIP_PARTS) for name in names), "ZIP contains forbidden folder")
            require(not any(re.search(r"\.(db|sqlite|sqlite3|log|pyc|mp4|mov|avi|mkv)$", name, re.I) for name in names), "ZIP contains forbidden runtime/media file")

    print("V873 production visual/logos/SHARK header OK")


if __name__ == "__main__":
    main()



