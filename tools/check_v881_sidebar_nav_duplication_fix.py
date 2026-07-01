from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V883_VISUAL_COMPANY_WORKER_BOT_CONTINUOUS_IMPROVEMENT_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"

REPORTS = [
    "V881_SIDEBAR_NAV_DUPLICATION_ROOT_FIX_REPORT.md",
    "V881_PREFLIGHT_SIDEBAR_NAV_FIX.md",
    "V881_SIDEBAR_NAV_DUPLICATION_AUDIT.md",
    "V881_NAV_RENDER_SOURCE_MAP.md",
    "V881_ADMIN_CLIENT_NAV_ISOLATION_FIX.md",
    "V881_VISIBLE_NAV_DUPLICATES_FIX.md",
    "V881_NAV_CSS_ROOT_CAUSE_FIX.md",
    "V881_SIDEBAR_BUTTON_COPY_FIX.md",
    "V881_SENTINEL_NAV_DUPLICATION_RULES_QA.md",
    "V881_SCREEN_BY_SCREEN_NAV_QA.md",
    "V881_RENDER_NAV_VERSION_AWARENESS.md",
    "V881_NEXT_STEPS.md",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def strip_comments(text: str) -> str:
    return re.sub(r"(?is)<!--.*?-->|{#.*?#}", "", text)


def fail(message: str) -> None:
    raise SystemExit(f"V881 sidebar/nav duplication fix check FAILED: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def nav_block(base_no_comments: str, marker: str) -> str:
    match = re.search(rf"(?is)<nav\b[^>]*{re.escape(marker)}[^>]*>.*?</nav>", base_no_comments)
    return match.group(0) if match else ""


def hrefs(block: str) -> list[str]:
    return re.findall(r'href="([^"]+)"', block)


def labels(block: str) -> list[str]:
    cleaned = re.sub(r"(?is)<span\b.*?</span>", " ", block)
    cleaned = re.sub(r"(?is)<strong\b.*?</strong>", " ", cleaned)
    labels_found = []
    for match in re.finditer(r"(?is)<a\b[^>]*>(.*?)</a>", cleaned):
        text = re.sub(r"(?is)<[^>]+>", " ", match.group(1))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            labels_found.append(text)
    return labels_found


def duplicate_values(values: list[str]) -> set[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for value in values:
        if value in seen:
            dupes.add(value)
        seen.add(value)
    return dupes


def main() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    base_no_comments = strip_comments(base)
    css = read("static/app.css")
    sentinel = read("engines/continuous_shark_sentinel_engine.py")
    templates = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").rglob("*.html"))

    require(read("VERSION.txt").strip() == VERSION, "VERSION.txt is not V881")
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION is not V881")
    require(f"APP_VERSION = '{VERSION}'" in app_py, "app.py APP_VERSION is not V881")
    require('data-v881-shell="true"' in base, "base.html missing data-v881-shell")
    require("has_v881_sidebar_nav_duplication_fix" in app_py, "runtime V881 flag missing")
    require("V881 SIDEBAR NAV DUPLICATION ROOT FIX START" in css, "CSS V881 marker missing")
    require("V881_NAV_DUPLICATION_RULES" in sentinel, "Sentinel V881 rules missing")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    for token in [
        "has_v880_full_app_problem_sweep",
        "has_v879_final_product_polish",
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

    for retired in [
        '<aside class="v828-client-rail"',
        '<nav class="v829-mobile-quick"',
        '<div class="v797-session-pills"',
        '<section class="v808-admin-dock"',
        '<section class="v853-admin-command-strip"',
    ]:
        require(retired not in base_no_comments, f"retired duplicate nav still rendered: {retired}")

    require(base_no_comments.count('data-nav-zone="client-topbar"') == 1, "client topbar nav is not unique")
    require(base_no_comments.count('data-nav-zone="client-bottom"') == 1, "client bottom nav is not unique")
    require(base_no_comments.count('class="v808-admin-rail"') == 1, "admin rail is not unique")
    require(base_no_comments.count('class="shark-widget"') == 1, "shark widget markup is not unique")
    require("{% if show_floating_shark %}" in base, "floating SHARK not controlled by flag")
    require("{% if show_mobile_bottom_nav %}" in base, "bottom nav not controlled by flag")
    require("{% if show_admin_nav %}" in base, "admin nav not controlled by flag")

    for marker in ['data-nav-zone="client-topbar"', 'data-nav-zone="client-bottom"']:
        block = nav_block(base_no_comments, marker)
        require(block, f"missing nav block {marker}")
        href_dupes = duplicate_values(hrefs(block))
        label_dupes = duplicate_values(labels(block))
        # Bottom nav has authenticated/public Jinja branches; "Inicio" appears
        # once per branch, never twice at runtime.
        if marker == 'data-nav-zone="client-bottom"':
            label_dupes.discard("Inicio")
        require(not href_dupes, f"duplicate hrefs inside {marker}: {href_dupes}")
        require(not label_dupes, f"duplicate labels inside {marker}: {label_dupes}")

    for bad in ["Inicio Inicio", "Picks Picks", "SHARK SHARK", "Telegram Telegram", "Panel Panel", "Dashboard Dashboard"]:
        require(bad.lower() not in (base_no_comments + templates).lower(), f"duplicated label remains: {bad}")

    for secret_hint in ["sk_live_", "sk_test_", "x-apisports-key", "telegram_bot_token=", "openai_api_key="]:
        require(secret_hint.lower() not in (app_py + templates).lower(), f"secret-like literal found: {secret_hint}")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v881_runtime_check.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v881-check")
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
    payload = runtime.get_json() or json.loads(runtime.get_data(as_text=True))
    require(payload.get("app_version") == VERSION, "runtime app_version is not V881")
    require(payload.get("version_txt") == VERSION, "runtime version_txt is not V881")
    require(payload.get("has_v881_sidebar_nav_duplication_fix") is True, "runtime V881 flag false")
    require(payload.get("has_v880_full_app_problem_sweep") is True, "runtime V880 flag false")
    require(payload.get("has_v818_automation") is True, "runtime V818 flag false")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names and "VERSION.txt" in names and "requirements.txt" in names, "ZIP missing required root files")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")
            require(not any(name.startswith(".git/") or name.startswith(".venv/") or name.startswith("release_output/") for name in names), "ZIP contains forbidden folder")
            require(not any(re.search(r"\.(db|sqlite|sqlite3|db-wal|db-shm|log|pyc|mp4|mov|avi|mkv)$", name, re.I) for name in names), "ZIP contains forbidden runtime/media file")

    print("V881 sidebar nav duplication root fix OK")


if __name__ == "__main__":
    main()


