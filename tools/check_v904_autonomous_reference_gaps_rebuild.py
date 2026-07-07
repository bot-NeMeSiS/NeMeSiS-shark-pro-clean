from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V904_AUTONOMOUS_REFERENCE_GAPS_REBUILD_AND_SENTINEL_WORKFORCE_FINAL"
CURRENT_VERSION = "V905_FINAL_REFERENCE_GAPS_BROWSER_QA_AND_BOM_FIX_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "reports/V904_AUTONOMOUS_REFERENCE_GAPS_REBUILD_REPORT.md",
    "reports/V904_AUTONOMOUS_WORKFORCE_INPUT_INVENTORY.md",
    "reports/V904_ADMIN_COMMAND_CENTER_REBUILD_QA.md",
    "reports/V904_CLIENT_APP_REBUILD_QA.md",
    "reports/V904_PICKS_LIVE_CALENDAR_QA.md",
    "reports/V904_SENTINEL_OUTBOX_UPDATE_QA.md",
    "reports/V904_REFERENCE_GAPS_ADDRESSED.md",
    "reports/V904_AUTOMATION_MODES_QA.md",
    "reports/V904_NEXT_STEPS.md",
]
TEMPLATE_MARKERS = {
    "templates/admin_dashboard.html": "data-v904-template=\"admin_dashboard\"",
    "templates/admin_autonomous_company_sentinel.html": "data-v904-template=\"admin_autonomous_company_sentinel\"",
    "templates/admin_sentinel_issues.html": "data-v904-template=\"admin_sentinel_issues\"",
    "templates/admin_sentinel_codex_outbox.html": "data-v904-template=\"admin_sentinel_codex_outbox\"",
    "templates/client_app_center.html": "data-v904-template=\"client_app_center\"",
    "templates/calendar.html": "data-v904-template=\"calendar\"",
    "templates/live.html": "data-v904-template=\"live\"",
    "templates/picks.html": "data-v904-template=\"picks\"",
    "templates/telegram.html": "data-v904-template=\"telegram\"",
    "templates/shark.html": "data-v904-template=\"shark\"",
}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def require(ok: bool, message: str, failures: list[str]) -> None:
    if not ok:
        failures.append(message)


def app_version_from_source(text: str) -> str:
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", text)
    return match.group(1) if match else ""


def assert_no_raw_secrets(failures: list[str]) -> None:
    scan_paths = [
        ROOT / "app.py",
        ROOT / "tools" / "render_cron_telegram_tick.py",
        ROOT / "tools" / "check_v904_autonomous_reference_gaps_rebuild.py",
    ] + list((ROOT / "reports").glob("V904*.md"))
    unsafe = re.compile(r"(secret|token|api_key|apikey)=([^\s`'\"&<>)]+)", re.IGNORECASE)
    allowed = {"hidden", "configured", "missing", "***hidden***", "***missing***", "AUTOMATION_SECRET", "..."}
    for path in scan_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in unsafe.finditer(text):
            value = match.group(2).strip()
            before = text[max(0, match.start() - 5):match.start()]
            if "?" not in before and "&" not in before and path.name == "app.py":
                continue
            if value in allowed or value in {"?", "token"} or value.startswith("***") or value.startswith("{") or value.startswith("$"):
                continue
            if "AUTOMATION_SECRET" in value or value.startswith("codex-v904-local-secret") or re.match(r"v\d+[-_]", value, flags=re.IGNORECASE):
                continue
            failures.append(f"possible raw secret in {path.relative_to(ROOT)}")
            return


def zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    for rel in ["app.py", "VERSION.txt", "APP_VERSION", "requirements.txt", "templates/base.html", "static/app.css", "reference_images/reference_manifest.json"]:
        require(rel in names, f"zip missing {rel}", failures)
    forbidden = ["/.git/", "/.venv/", "__pycache__/", ".pytest_cache/", "release_output/", "v636work/"]
    for name in names:
        normalized = f"/{name}"
        if any(marker in normalized for marker in forbidden) or name.lower().endswith((".db", ".sqlite", ".sqlite3", ".log", ".zip")):
            failures.append(f"zip forbidden entry {name}")
            return


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")

    allowed_versions = {VERSION, CURRENT_VERSION}
    require(read("VERSION.txt").strip().lstrip("\ufeff") in allowed_versions, "VERSION.txt is not V904-compatible", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") in allowed_versions, "APP_VERSION file is not V904-compatible", failures)
    require(app_version_from_source(app_py) in allowed_versions, "app.py APP_VERSION is not V904-compatible", failures)
    require("data-v904-shell" in base, "base V904 shell marker missing", failures)
    require("V904 AUTONOMOUS REFERENCE GAPS REBUILD" in css, "V904 CSS block missing", failures)
    require(("NEMESIS_CACHE_V904" in app_py or "NEMESIS_CACHE_V905" in app_py) and "res.status===404" in app_py, "service worker V904+ 404 safety missing", failures)
    require("has_v904_autonomous_reference_gaps_rebuild" in app_py, "runtime V904 main flag missing", failures)
    require("has_v904_sentinel_workforce" in app_py, "runtime V904 workforce flag missing", failures)
    require("has_v904_reference_gaps_addressed" in app_py, "runtime V904 gaps flag missing", failures)
    engine_text = read("engines/autonomous_company_sentinel_engine.py")
    require("daily_reference_review" in engine_text, "V904 daily_reference_review mode missing from engine", failures)
    require("post_deploy_check" in engine_text, "V904 post_deploy_check mode missing from engine", failures)
    require("SAFE_AUTOFIX" in engine_text, "V904 SAFE_AUTOFIX policy missing", failures)
    require("CODEX_PROMPT_REQUIRED" in engine_text, "V904 CODEX_PROMPT_REQUIRED policy missing", failures)
    require("HUMAN_APPROVAL_REQUIRED" in engine_text, "V904 HUMAN_APPROVAL_REQUIRED policy missing", failures)
    require((ROOT / "reference_images").exists(), "reference_images missing", failures)
    require((ROOT / "reference_images" / "reference_manifest.json").exists(), "reference_manifest missing", failures)

    manifest = json.loads((ROOT / "reference_images" / "reference_manifest.json").read_text(encoding="utf-8"))
    require(int(manifest.get("reference_count") or 0) >= 16, "reference manifest has fewer than 16 images", failures)

    gap_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "reference_gap_report.json"
    require(gap_path.exists(), "reference gap report missing", failures)
    if gap_path.exists():
        gap = json.loads(gap_path.read_text(encoding="utf-8"))
        review = gap.get("v904_review") or {}
        require(int(review.get("gaps_read") or 0) >= 1, "V904 gaps_read missing", failures)
        require(int(review.get("gaps_addressed") or 0) >= 6, "V904 gaps addressed too low", failures)
        require(review.get("browser_qa_status") == "BROWSER_QA_UNAVAILABLE", "Browser QA status must remain honest", failures)
        automation_modes = gap.get("v904_automation_modes") or {}
        if automation_modes:
            require("daily_reference_review" in (automation_modes.get("supported_modes") or []), "V904 gap report missing daily mode", failures)
            require("post_deploy_check" in (automation_modes.get("supported_modes") or []), "V904 gap report missing post-deploy mode", failures)

    outbox = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "outbox" / "codex_outbox.md"
    require(outbox.exists(), "codex outbox missing", failures)
    outbox_text = outbox.read_text(encoding="utf-8", errors="replace") if outbox.exists() else ""
    require("V904_REFERENCE_GAPS_WORKFORCE_STATUS" in outbox_text, "outbox V904 status section missing", failures)
    require("dangerous_requires_approval" in outbox_text, "outbox dangerous approval section missing", failures)

    for rel, marker in TEMPLATE_MARKERS.items():
        require(marker in read(rel), f"{rel} missing {marker}", failures)

    admin_templates = "\n".join(read(rel) for rel in [
        "templates/admin_autonomous_company_sentinel.html",
        "templates/admin_sentinel_issues.html",
        "templates/admin_sentinel_codex_outbox.html",
    ])
    require('href="/api/admin' not in admin_templates, "direct admin API href remains in V904 admin templates", failures)
    require('href="#"' not in admin_templates and "javascript:void(0)" not in admin_templates, "dead links remain in V904 admin templates", failures)
    require("data-v904-fetch" in admin_templates, "V904 safe fetch buttons missing", failures)

    touched_templates = "\n".join(read(rel) for rel in TEMPLATE_MARKERS)
    for bad in ["Â", "Ã", "�"]:
        require(bad not in touched_templates, f"mojibake marker {bad!r} remains in V904 touched templates", failures)
    for bad in ["apuesta segura", "garantizado", "sin riesgo", "seguro fijo"]:
        require(bad not in touched_templates.lower(), f"unsafe betting claim remains: {bad}", failures)

    for report in REPORTS:
        require((ROOT / report).exists(), f"missing report {report}", failures)

    assert_no_raw_secrets(failures)

    os.environ.setdefault("AUTOMATION_SECRET", "codex-v904-local-secret")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    flask_app = app_module.app
    flask_app.testing = True
    client = flask_app.test_client()
    runtime_resp = client.get("/api/runtime-version")
    runtime = runtime_resp.get_json() or {}
    require(runtime_resp.status_code == 200 and runtime.get("app_version") in allowed_versions, "runtime is not V904-compatible", failures)
    require(runtime.get("has_v904_autonomous_reference_gaps_rebuild") is True, "runtime V904 main flag false", failures)
    require(runtime.get("has_v904_sentinel_workforce") is True, "runtime V904 workforce flag false", failures)
    require(runtime.get("has_v904_reference_gaps_addressed") is True, "runtime V904 gaps flag false", failures)
    require(int(runtime.get("v904_gaps_read") or 0) >= 1, "runtime V904 gaps_read missing", failures)

    for route in ["/admin-login", "/admin/dashboard", "/admin/autonomous-company-sentinel", "/admin/sentinel-issues", "/admin/sentinel-codex-outbox"]:
        resp = client.get(route)
        require(resp.status_code in {200, 302, 403}, f"{route} unexpected status {resp.status_code}", failures)
        require("Internal Server Error" not in resp.get_data(as_text=True), f"{route} leaked 500 page", failures)

    api = client.get("/api/admin/continuous-sentinel/run?mode=quick&dry_run=1")
    require(api.status_code == 403 and api.is_json, "admin continuous run must be protected JSON 403", failures)
    cron_forbidden = client.get("/api/automation/autonomous-company-sentinel/run?mode=daily_reference_review&dry_run=1")
    require(cron_forbidden.status_code == 403 and cron_forbidden.is_json, "V904 autonomous cron without secret must be 403 JSON", failures)
    cron_daily = client.get("/api/automation/autonomous-company-sentinel/run?secret=codex-v904-local-secret&mode=daily_reference_review&dry_run=1&runner=local_check")
    daily_json = cron_daily.get_json(silent=True) or {}
    require(cron_daily.status_code == 200 and daily_json.get("mode") == "daily_reference_review", "V904 daily_reference_review cron dry-run failed", failures)
    require(daily_json.get("dangerous_actions_executed") is False, "V904 daily_reference_review executed dangerous actions", failures)
    cron_post = client.get("/api/automation/autonomous-company-sentinel/run?secret=codex-v904-local-secret&mode=post_deploy_check&dry_run=1&runner=local_check")
    post_json = cron_post.get_json(silent=True) or {}
    require(cron_post.status_code == 200 and post_json.get("mode") == "post_deploy_check", "V904 post_deploy_check cron dry-run failed", failures)
    require(post_json.get("dangerous_actions_executed") is False, "V904 post_deploy_check executed dangerous actions", failures)
    api_404 = client.get("/api/ruta-inventada-v904")
    require(api_404.status_code == 404 and api_404.is_json, "API 404 must be JSON safe", failures)
    html_404 = client.get("/ruta-inventada-v904")
    require(html_404.status_code == 404 and "NeMeSiS" in html_404.get_data(as_text=True), "HTML 404 premium missing", failures)

    zip_clean(failures)

    if failures:
        print("V904 autonomous reference gaps rebuild check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V904 autonomous reference gaps rebuild check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
