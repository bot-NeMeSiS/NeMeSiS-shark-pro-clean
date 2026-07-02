from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V884_CLIENT_ADMIN_FUNCTIONAL_FLOW_AND_SCREEN_EXPERIENCE_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"

REPORTS = [
    "V880_FULL_APP_PROBLEM_SWEEP_AND_FIX_ALL_SAFE_REPORT.md",
    "V880_PREFLIGHT_FULL_PROBLEM_SWEEP.md",
    "V880_FULL_APP_PROBLEM_INVENTORY.md",
    "V880_RENDER_GITHUB_CODEX_ALIGNMENT_QA.md",
    "V880_ROUTES_SECURITY_PROTECTION_QA.md",
    "V880_UI_COPY_VISUAL_FIX_SWEEP.md",
    "V880_MATCHES_FIX_SWEEP.md",
    "V880_PICKS_ODDS_FIX_SWEEP.md",
    "V880_SENTINEL_REAL_QA_FIX_SWEEP.md",
    "V880_ADMIN_OPERATIONS_FIX_SWEEP.md",
    "V880_SHARK_OPENAI_FIX_SWEEP.md",
    "V880_TELEGRAM_FIX_SWEEP.md",
    "V880_PAYMENTS_MEMBERSHIPS_FIX_SWEEP.md",
    "V880_LOGOS_CRESTS_FIX_SWEEP.md",
    "V880_RELEASE_WORKSPACE_FIX_SWEEP.md",
    "V880_NEXT_STEPS.md",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def fail(message: str) -> None:
    raise SystemExit(f"V880 full app problem sweep check FAILED: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def visible_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style|template|svg|noscript)\b.*?</\1>", " ", html or "")
    text = re.sub(r"(?is)<!--.*?-->", " ", text)
    text = re.sub(r"(?is)\{\{.*?\}\}", " ", text)
    text = re.sub(r"(?is)\{%.*?%\}", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    sentinel = read("engines/continuous_shark_sentinel_engine.py")
    templates = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").rglob("*.html"))
    visible_templates = visible_text(templates)

    require(read("VERSION.txt").strip() == VERSION, "VERSION.txt is not V880")
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION file is not V880")
    require(f"APP_VERSION = '{VERSION}'" in app_py, "app.py APP_VERSION is not V880")
    require(VERSION in base, "base.html missing V880 cache/version")
    require('data-v880-shell="true"' in base, "base.html missing data-v880-shell")
    require("has_v880_full_app_problem_sweep" in app_py, "runtime V880 flag missing")
    require("V880 FULL APP PROBLEM SWEEP AND FIX ALL SAFE START" in css, "CSS V880 marker missing")
    require("V881 SIDEBAR NAV DUPLICATION ROOT FIX START" in css, "CSS V881 marker missing")
    require("V880_PROBLEM_SWEEP_RULES" in sentinel, "Sentinel V880 rules missing")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    for token in [
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

    for state in [
        "Sin datos reales",
        "Esperando proveedor",
        "Sin directos reales",
        "Sin picks activos",
        "Cuota pendiente",
        "Selección pendiente",
        "Pick en revisión",
        "No configurado",
        "Modo seguro activo",
        "Fallback visual activo",
    ]:
        require(state in app_py + templates + "\n".join(read(f"reports/{r}") for r in REPORTS), f"safe state missing: {state}")

    for bad in [">None<", ">null<", ">undefined<", "ÃƒÆ’Ã†â€™", "ÃƒÆ’Ã¢â‚¬Å¡", "ÃƒÂ¯Ã‚Â¿Ã‚Â½", "EspaÃƒ", "EspaÃ"]:
        require(bad not in app_py + templates, f"technical/mojibake token remains: {bad}")

    for bad in ["Stripe operativo", "Telegram filler", "OpenAI operativo", "apuesta segura", "garantizado", "apuesta fija", "sin riesgo"]:
        require(bad.lower() not in (app_py + templates).lower(), f"blocked phrase remains: {bad}")

    for secret_hint in ["sk_live_", "sk_test_", "x-apisports-key", "telegram_bot_token=", "openai_api_key="]:
        require(secret_hint.lower() not in (app_py + templates).lower(), f"secret-like literal found: {secret_hint}")

    require("traceback" not in visible_templates.lower(), "traceback visible in templates")
    require("debug=true" not in (app_py + templates).lower(), "debug=true literal found")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v880_runtime_check.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v880-check")
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
    payload = runtime.get_json() or json.loads(runtime.get_data(as_text=True))
    require(payload.get("app_version") == VERSION, "runtime app_version is not V880")
    require(payload.get("version_txt") == VERSION, "runtime version_txt is not V880")
    require(payload.get("has_v880_full_app_problem_sweep") is True, "runtime V880 flag false")
    require(payload.get("has_v881_sidebar_nav_duplication_fix") is True, "runtime V881 flag false")
    require(payload.get("has_v818_automation") is True, "runtime V818 flag false")
    require(client.get("/api/automation/master-tick").status_code == 403, "master tick without secret is not 403")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names and "VERSION.txt" in names and "requirements.txt" in names, "ZIP missing required root files")
            require(not any(name.lower().endswith(".zip") for name in names), "ZIP contains internal zip")
            require(not any(name.startswith(".git/") or name.startswith(".venv/") or name.startswith("release_output/") for name in names), "ZIP contains forbidden folder")
            require(not any(re.search(r"\.(db|sqlite|sqlite3|db-wal|db-shm|log|pyc|mp4|mov|avi|mkv)$", name, re.I) for name in names), "ZIP contains forbidden runtime/media file")

    print("V880 full app problem sweep and safe fixes OK")


if __name__ == "__main__":
    main()




