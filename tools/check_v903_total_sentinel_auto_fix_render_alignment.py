from __future__ import annotations

import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VERSION = "V903_TOTAL_SENTINEL_AUTO_FIX_RENDER_ALIGNMENT_AND_STABILITY_FINAL"
CURRENT_VERSION = "V906_REAL_BROWSER_QA_SCREENSHOT_REFERENCE_COMPARISON_FINAL"
V904_VERSION = "V904_AUTONOMOUS_REFERENCE_GAPS_REBUILD_AND_SENTINEL_WORKFORCE_FINAL"
ALLOWED_VERSIONS = {VERSION, V904_VERSION, CURRENT_VERSION}
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "reports/V903_TOTAL_SENTINEL_AUTO_FIX_RENDER_ALIGNMENT_AND_STABILITY_REPORT.md",
    "reports/V903_TOTAL_ACTIVE_ERRORS_INVENTORY.md",
    "reports/V903_SECRET_EXPOSURE_AND_ROTATION_QA.md",
    "reports/V903_DEPLOY_ROOT_ALIGNMENT_QA.md",
    "reports/V903_ADMIN_CLIENT_TELEGRAM_FIX_QA.md",
    "reports/V903_CODEX_OUTBOX_TRUTH_QA.md",
    "reports/V903_REFERENCE_GAPS_STATUS.md",
    "reports/V903_NEXT_STEPS.md",
]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def require(ok: bool, message: str, failures: list[str]) -> None:
    if not ok:
        failures.append(message)


def app_version_from_source(app_py: str) -> str:
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", app_py)
    return match.group(1) if match else ""


def secret_scan(failures: list[str]) -> None:
    safe_values = {"***hidden***", "***missing***", "***", "...", "AUTOMATION_SECRET", "[redacted]"}
    files = [ROOT / "app.py", ROOT / "tools" / "render_cron_telegram_tick.py"] + list((ROOT / "reports").glob("*.md"))
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"(secret|token|api_key|apikey)=([^\s`'\"&<>)]+)", text, flags=re.IGNORECASE):
            value = match.group(2).strip()
            before = text[max(0, match.start() - 5):match.start()]
            if "?" not in before and "&" not in before and path.name == "app.py":
                continue
            if value in safe_values or value.startswith("***") or value.startswith("{") or value.startswith("$"):
                continue
            if "AUTOMATION_SECRET" in value or value.startswith("codex-") or re.match(r"v\d+[-_]", value, flags=re.IGNORECASE):
                continue
            failures.append(f"possible unsafe secret placeholder in {path.relative_to(ROOT)}")


def zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    required = ["app.py", "VERSION.txt", "APP_VERSION", "requirements.txt", "templates/base.html", "static/app.css"]
    for rel in required:
        require(rel in names, f"zip missing {rel}", failures)
    bad_markers = ["/.git/", "/.venv/", "__pycache__/", ".pytest_cache/", "release_output/", "v636work/"]
    for name in names:
        normalized = f"/{name}"
        if any(marker in normalized for marker in bad_markers) or name.lower().endswith((".db", ".sqlite", ".sqlite3", ".log", ".zip")):
            failures.append(f"zip forbidden entry {name}")
            break


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    service_worker_ok = ("NEMESIS_CACHE_V903" in app_py or "NEMESIS_CACHE_V904" in app_py or "NEMESIS_CACHE_V905" in app_py or "NEMESIS_CACHE_V906" in app_py) and "res.status===404" in app_py

    require(read("VERSION.txt").strip().lstrip("\ufeff") in ALLOWED_VERSIONS, "VERSION.txt is not V903-compatible", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") in ALLOWED_VERSIONS, "APP_VERSION file is not V903-compatible", failures)
    require(app_version_from_source(app_py) in ALLOWED_VERSIONS, "app.py APP_VERSION is not V903-compatible", failures)
    require("data-v903-shell" in base, "base V903 marker missing", failures)
    require("has_v903_total_sentinel_auto_fix_render_alignment" in app_py, "runtime V903 main flag missing", failures)
    require("has_v903_secret_rotation_guard" in app_py, "runtime V903 secret flag missing", failures)
    require("has_v903_active_errors_inventory" in app_py, "runtime V903 inventory flag missing", failures)
    require(service_worker_ok, "service worker V903/404 safety missing", failures)
    require((ROOT / "reference_images").exists(), "reference_images missing", failures)
    require((ROOT / "reference_images" / "reference_manifest.json").exists(), "reference_manifest.json missing", failures)
    require((ROOT / "tools" / "print_release_identity.py").exists(), "print_release_identity missing", failures)
    require((ROOT / "tools" / "check_deploy_root_identity.py").exists(), "check_deploy_root_identity missing", failures)

    for report in REPORTS:
        require((ROOT / report).exists(), f"missing report {report}", failures)

    outbox = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "codex_outbox.md"
    require(outbox.exists(), "codex outbox missing", failures)
    if outbox.exists():
        outbox_text = outbox.read_text(encoding="utf-8", errors="replace")
        for section in ["ACTIVE_FIX_PROMPTS", "VISUAL_REFERENCE_PROMPTS", "ARCHIVED_OBSOLETE_PROMPTS", "FALSE_POSITIVE_PROMPTS"]:
            require(section in outbox_text, f"outbox section missing {section}", failures)

    secret_scan(failures)

    os.environ.setdefault("AUTOMATION_SECRET", "codex-v903-local-secret")
    import app as app_module

    flask_app = app_module.app
    flask_app.testing = True
    client = flask_app.test_client()
    runtime_resp = client.get("/api/runtime-version")
    runtime = runtime_resp.get_json() or {}
    require(runtime_resp.status_code == 200 and runtime.get("app_version") in ALLOWED_VERSIONS, "runtime is not V903-compatible", failures)
    require(runtime.get("has_v903_total_sentinel_auto_fix_render_alignment") is True, "runtime V903 main flag false", failures)
    require(runtime.get("has_v903_secret_rotation_guard") is True, "runtime V903 secret flag false", failures)
    require(runtime.get("secret_masking_ok") is True, "runtime secret masking not OK", failures)

    smoke = {
        "/": 200,
        "/cliente-login": 200,
        "/registro": 200,
        "/calendar": 200,
        "/live": 200,
        "/picks": 200,
        "/admin-login": 200,
        "/api/runtime-version": 200,
        "/manifest.json": 200,
        "/service-worker.js": 200,
    }
    for route, expected in smoke.items():
        resp = client.get(route)
        require(resp.status_code == expected, f"{route} expected {expected}, got {resp.status_code}", failures)

    for route in ["/admin/dashboard", "/admin/continuous-sentinel", "/admin/shark-sentinel", "/admin/autonomous-company-sentinel", "/admin/sentinel-issues", "/admin/sentinel-codex-outbox", "/admin/not-found-events"]:
        resp = client.get(route)
        require(resp.status_code in {302, 403}, f"{route} without session must be protected, got {resp.status_code}", failures)
        html = resp.get_data(as_text=True)
        require("Traceback" not in html and "Internal Server Error" not in html, f"{route} leaked error page", failures)

    api_run = client.get("/api/admin/continuous-sentinel/run?mode=quick&dry_run=1")
    require(api_run.status_code == 403 and api_run.is_json, "admin continuous run without session must be JSON 403", failures)
    api_404 = client.get("/api/ruta-inventada-v903")
    require(api_404.status_code == 404 and api_404.is_json, "API 404 must be JSON", failures)
    html_404 = client.get("/ruta-inventada-v903")
    require(html_404.status_code == 404 and "NeMeSiS" in html_404.get_data(as_text=True), "HTML 404 premium missing", failures)

    for route in ["/admin-login", "/admin/continuous-sentinel"]:
        html = client.get(route).get_data(as_text=True)
        require('data-nav-zone="client-bottom"' not in html, f"client bottom nav visible in {route}", failures)
        require('<div class="shark-widget"' not in html and "shark-widget ns-floating" not in html, f"floating client SHARK visible in {route}", failures)

    unsafe_templates = "\n".join((ROOT / rel).read_text(encoding="utf-8", errors="replace") for rel in [
        "templates/admin_continuous_sentinel.html",
        "templates/admin_sentinel_workflow.html",
        "templates/admin_shark_sentinel.html",
    ] if (ROOT / rel).exists())
    require('href="/api/admin/continuous-sentinel/run' not in unsafe_templates, "direct API href remains in admin Sentinel templates", failures)
    require('href="#"' not in unsafe_templates and "javascript:void(0)" not in unsafe_templates, "dead admin links remain", failures)

    zip_clean(failures)

    if failures:
        print("V903 total Sentinel auto fix render alignment check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V903 total Sentinel auto fix render alignment check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
