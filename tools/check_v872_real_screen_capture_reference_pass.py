from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V872_REAL_RENDER_SCREEN_CAPTURE_REFERENCE_FINAL_PASS"
VERSION_V873 = "V873_REAL_PRODUCTION_VISUAL_LOGOS_SHARK_HEADER_FINAL"
V874 = "V874_COMPANY_WIDE_PRODUCT_POLISH_VISUAL_DATA_SENTINEL_FINAL"
VERSION_V874 = "V874_COMPANY_WIDE_PRODUCT_POLISH_VISUAL_DATA_SENTINEL_FINAL"
VERSION_V875 = "V876_RENDER_VERSION_ALIGNMENT_AND_FINAL_VISUAL_DEPLOY_CHECK_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"

REPORTS = [
    "V872_REAL_RENDER_SCREEN_CAPTURE_REFERENCE_FINAL_PASS_REPORT.md",
    "V872_PREFLIGHT_FROM_V871.md",
    "V872_RENDER_REAL_VS_LOCAL_RUNTIME_QA.md",
    "V872_REAL_SCREEN_CAPTURE_QA.md",
    "V872_REFERENCE_COMPARISON_SCREEN_BY_SCREEN.md",
    "V872_CLIENT_PC_FINAL_SCREEN_PASS_QA.md",
    "V872_MOBILE_FINAL_SCREEN_PASS_QA.md",
    "V872_ADMIN_FINAL_SCREEN_PASS_QA.md",
    "V872_LOGOS_CRESTS_VISUAL_DATA_QA.md",
    "V872_SENTINEL_SCREEN_RULES_QA.md",
    "V872_NEXT_STEPS.md",
]

FORBIDDEN_ZIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "release_output", "releases", "v636work", "tmp", "temp"}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def fail(message: str) -> None:
    raise SystemExit(f"V872 real screen capture reference pass FAILED: {message}")


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
    ui = read("templates/partials/ui_components.html")
    telegram = read("templates/telegram.html")
    templates = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").glob("*.html"))

    valid_versions = {VERSION, VERSION_V873, VERSION_V874, VERSION_V875}
    require(read("VERSION.txt").strip() in valid_versions, "VERSION.txt is not V872/V873")
    require(read("APP_VERSION").strip() in valid_versions, "APP_VERSION is not V872/V873")
    require(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in valid_versions), "app.py APP_VERSION is not V872/V873")
    require(VERSION in base or VERSION_V873 in base or VERSION_V874 in base or VERSION_V875 in base, "base.html missing V872/V873/V874 cache/version")
    require('data-v872-shell="true"' in base, "base.html missing data-v872-shell")
    require("NEMESIS V872 REAL RENDER SCREEN CAPTURE REFERENCE FINAL PASS ACTIVE" in base, "base.html missing V872 comment")
    require("has_v872_real_screen_capture_reference_pass" in app_py, "runtime V872 flag missing")
    require("V872 REAL RENDER SCREEN CAPTURE REFERENCE FINAL PASS START" in css, "CSS V872 marker missing")
    require("V872 REAL RENDER SCREEN CAPTURE REFERENCE FINAL PASS END" in css, "CSS V872 end marker missing")
    require("Invalid header value detectado en runtime" in app_py, "runtime invalid-header safe message missing")
    require("reports/V872_" in read("tools/build_clean_release.py"), "release builder does not include V872 reports")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    for token in [
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
        require(bad not in ui + telegram + base, f"visible mojibake/copy defect remains: {bad}")

    for text in interactive_texts(base + ui + telegram):
        require(not has_duplicate_words(text), f"duplicate visible CTA text remains: {text}")

    lower = templates.lower()
    for phrase in ["apuesta segura", "garantizado", "apuesta fija", "fijo seguro", "sin riesgo"]:
        require(phrase not in lower, f"irresponsible betting phrase found: {phrase}")
    require("Stripe operativo" not in templates, "false Stripe operative text found")
    require("Telegram filler" not in templates, "Telegram filler text found")

    for secret_hint in ["sk_live_", "sk_test_", "x-apisports-key", "telegram_bot_token=", "openai_api_key="]:
        require(secret_hint.lower() not in (app_py + templates).lower(), f"secret-like literal found: {secret_hint}")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v872_runtime_check.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v872-check")
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
    payload = runtime.get_json() or json.loads(runtime.get_data(as_text=True))
    require(payload.get("app_version") in valid_versions, "runtime app_version not V872/V873")
    require(payload.get("version_txt") in valid_versions, "runtime version_txt not V872/V873")
    require(payload.get("has_v872_real_screen_capture_reference_pass") is True, "runtime V872 flag false")
    require(payload.get("has_v871_visible_ui_empty_space_screen_fix") is True, "runtime V871 flag false")
    require(payload.get("has_v818_automation") is True, "runtime V818 flag false")
    serialized = json.dumps(payload, ensure_ascii=False)
    require("Invalid header value b'" not in serialized, "runtime exposes raw invalid-header value")
    require(client.get("/api/automation/master-tick?dry_run=1").status_code == 403, "master tick without secret is not 403")
    require(client.get("/api/automation/master-tick?dry_run=1&secret=codex-v872-check").status_code == 200, "master tick with secret is not 200")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names and "VERSION.txt" in names, "ZIP missing required files")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")
            require(not any(any(part in name.split("/") for part in FORBIDDEN_ZIP_PARTS) for name in names), "ZIP contains forbidden folder")
            require(not any(re.search(r"\.(db|sqlite|sqlite3|log|pyc|mp4|mov|avi|mkv)$", name, re.I) for name in names), "ZIP contains forbidden runtime/media file")

    print("V872 real screen capture reference pass OK")


if __name__ == "__main__":
    main()


