from __future__ import annotations

import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V871_VISIBLE_UI_DEFECTS_EMPTY_SPACE_SCREEN_BY_SCREEN_PRO_MAX_FINAL"
VERSION_V872 = "V872_REAL_RENDER_SCREEN_CAPTURE_REFERENCE_FINAL_PASS"
VERSION_V873 = "V873_REAL_PRODUCTION_VISUAL_LOGOS_SHARK_HEADER_FINAL"
V874 = "V874_COMPANY_WIDE_PRODUCT_POLISH_VISUAL_DATA_SENTINEL_FINAL"
VERSION_V874 = "V874_COMPANY_WIDE_PRODUCT_POLISH_VISUAL_DATA_SENTINEL_FINAL"
VERSION_V875 = "V875_REAL_PRODUCT_READINESS_RENDER_VISUAL_REVENUE_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"

REPORTS = [
    "V871_PREFLIGHT_FROM_V870.md",
    "V871_VISIBLE_UI_DEFECTS_EMPTY_SPACE_AND_REAL_PROGRESS_FIX_REPORT.md",
    "V871_BUTTONS_CTA_COPY_DUPLICATION_AUDIT.md",
    "V871_UI_COMPONENTS_MACRO_DEDUP_FIX_REPORT.md",
    "V871_EMPTY_SPACE_DENSITY_AUDIT.md",
    "V871_EMPTY_SPACE_REDUCTION_FIX_REPORT.md",
    "V871_SCREEN_BY_SCREEN_VISIBLE_FIX_QA.md",
    "V871_CLIENT_PC_DENSITY_DASHBOARD_QA.md",
    "V871_MOBILE_DENSITY_NATIVE_QA.md",
    "V871_ADMIN_DENSITY_COMMAND_CENTER_QA.md",
    "V871_REAL_PROGRESS_VISIBILITY_AUDIT.md",
    "V871_SENTINEL_VISIBLE_UI_AND_EMPTY_SPACE_RULES_QA.md",
    "V871_SCREEN_VISUAL_CONFIRMATION_QA.md",
    "V871_RELEASE_CLEANLINESS_QA.md",
    "V871_NEXT_STEPS.md",
]

FORBIDDEN_ZIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "release_output", "releases", "v636work", "tmp", "temp"}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def fail(message: str) -> None:
    raise SystemExit(f"V871 visible UI empty-space check FAILED: {message}")


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
    sentinel = read("engines/shark_sentinel_engine.py")
    templates = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").glob("*.html"))

    valid_versions = {VERSION, VERSION_V872, VERSION_V873, VERSION_V874, VERSION_V875}
    require(read("VERSION.txt").strip() in valid_versions, "VERSION.txt is not V871/V872")
    require(read("APP_VERSION").strip() in valid_versions, "APP_VERSION is not V871/V872")
    require(any(f"APP_VERSION = '{candidate}'" in app_py for candidate in valid_versions), "app.py APP_VERSION is not V871/V872")
    require(any(candidate in base for candidate in valid_versions), "base.html missing V871/V872/V873 cache/version")
    require('data-v871-shell="true"' in base, "base.html missing data-v871-shell")
    require("has_v871_visible_ui_empty_space_screen_fix" in app_py, "runtime V871 flag missing")
    require("V871 VISIBLE UI DEFECTS EMPTY SPACE SCREEN BY SCREEN PRO MAX START" in css, "CSS V871 marker missing")
    require("V871 VISIBLE UI DEFECTS EMPTY SPACE SCREEN BY SCREEN PRO MAX END" in css, "CSS V871 end marker missing")
    require("v871-action-clean" in ui and "aria-label" in ui, "ui components missing V871 clean action semantics")
    for density_signal in [
        "min-height: 0",
        "padding-block: clamp(16px",
        "grid-template-columns: 1fr",
        "overflow-x: clip",
        ".v870-reference-widget-grid",
        ".admin-table",
    ]:
        require(density_signal in css, f"missing V871 density signal: {density_signal}")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    for token in [
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

    require("<span></span>" not in base, "empty nav span remains")
    require("Panel <span>Panel</span>" not in base, "admin duplicate Panel remains")
    require("<span>Partidos</span><strong>Partidos</strong>" not in base, "client duplicate Partidos remains")
    require("return meta ? meta.getAttribute('content') : '';" in base, "CSRF ternary still broken")
    require("active ? 'DELETE' : 'POST'" in base, "favorite method ternary still broken")
    require("href === '/' ? path === '/'" in base, "active nav ternary still broken")
    require("w < 720 ? 'mobile'" in base, "device kind ternary still broken")
    require("touch ? 'ns-input-touch'" in base, "touch ternary still broken")
    require("el.dataset.seconds ? parseInt" in base, "clock ternary still broken")
    require("_interactive_texts_from_html" in sentinel and "_has_duplicate_cta_text" in sentinel, "Sentinel duplicate CTA rules missing")

    lower = templates.lower()
    for phrase in ["apuesta segura", "garantizado", "apuesta fija", "fijo seguro", "sin riesgo"]:
        require(phrase not in lower, f"irresponsible betting phrase found: {phrase}")
    require("Stripe operativo" not in templates, "false Stripe operative text found")
    require("Telegram filler" not in templates, "Telegram filler text found")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v871_runtime_check.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v871-check")
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
    payload = runtime.get_json() or {}
    require(payload.get("app_version") in valid_versions, "runtime app_version not V871/V872")
    require(payload.get("version_txt") in valid_versions, "runtime version_txt not V871/V872")
    require(payload.get("has_v871_visible_ui_empty_space_screen_fix") is True, "runtime V871 flag false")
    require(payload.get("has_v870_reference_style_match_workspace_purge") is True, "runtime V870 flag false")
    require(client.get("/api/automation/master-tick?dry_run=1").status_code == 403, "master tick without secret is not 403")
    require(client.get("/api/automation/master-tick?dry_run=1&secret=codex-v871-check").status_code == 200, "master tick with secret is not 200")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names and "VERSION.txt" in names, "ZIP missing required files")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")
            require(not any(any(part in name.split("/") for part in FORBIDDEN_ZIP_PARTS) for name in names), "ZIP contains forbidden folder")
            require(not any(re.search(r"\.(db|sqlite|sqlite3|log|pyc|mp4|mov|avi|mkv)$", name, re.I) for name in names), "ZIP contains forbidden runtime/media file")

    print("V871 visible UI empty-space/density OK")


if __name__ == "__main__":
    main()



