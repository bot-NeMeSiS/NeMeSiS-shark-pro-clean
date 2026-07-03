#!/usr/bin/env python3
"""Validate V883 Visual Company Worker integration."""
from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PRESERVED_VERSION = "V883_VISUAL_COMPANY_WORKER_BOT_CONTINUOUS_IMPROVEMENT_FINAL"
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
REPORTS = [
    "reports/V883_VISUAL_COMPANY_WORKER_BOT_CONTINUOUS_IMPROVEMENT_REPORT.md",
    "reports/V883_PREFLIGHT_VISUAL_COMPANY_WORKER.md",
    "reports/V883_VISUAL_RULES_MODEL.md",
    "reports/V883_PRODUCT_DATA_RULES_MODEL.md",
    "reports/V883_COMPANY_WORKERS_MODEL.md",
    "reports/V883_SENTINEL_VISUAL_WORKER_INTEGRATION.md",
    "reports/V883_CONTINUOUS_REVALIDATION_MODEL.md",
    "reports/V883_RENDER_GITHUB_AWARENESS_QA.md",
    "reports/V883_MATCHES_DATA_AWARENESS_QA.md",
    "reports/V883_BROWSER_VISUAL_WORKER_QA.md",
    "reports/V883_NEXT_STEPS.md",
]


def fail(message: str) -> None:
    print(f"V883 CHECK FAIL: {message}")
    raise SystemExit(1)


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def assert_contains(text: str, needle: str, label: str) -> None:
    if needle not in text:
        fail(f"{label} missing {needle}")


def check_files() -> None:
    if read_text("VERSION.txt").strip() != VERSION:
        fail("VERSION.txt does not match current version")
    if read_text("APP_VERSION").strip() != VERSION:
        fail("APP_VERSION does not match current version")
    app_py = read_text("app.py")
    base = read_text("templates/base.html")
    css = read_text("static/app.css")
    assert_contains(app_py, f"APP_VERSION = '{VERSION}'", "app.py")
    assert_contains(app_py, "visual_company_worker_engine", "app.py")
    assert_contains(app_py, "/admin/visual-worker", "app.py")
    assert_contains(app_py, "/api/admin/visual-worker/summary", "app.py")
    assert_contains(app_py, "/api/automation/visual-worker/run", "app.py")
    assert_contains(app_py, "has_v883_visual_company_worker", "runtime flag")
    assert_contains(base, "data-v883-shell", "base.html")
    if PRESERVED_VERSION not in base and "data-v883-shell" not in base:
        fail("base.html missing V883 preservation")
    assert_contains(base, "NEMESIS V883 VISUAL COMPANY WORKER BOT CONTINUOUS IMPROVEMENT ACTIVE", "base.html comment")
    assert_contains(css, "V883 VISUAL COMPANY WORKER BOT CONTINUOUS IMPROVEMENT START", "static/app.css")
    assert_contains(read_text("engines/continuous_shark_sentinel_engine.py"), "visual-worker", "continuous sentinel")
    assert_contains(read_text("engines/sentinel_improvement_workflow_engine.py"), "V883_VISUAL_WORKER_WORKFLOW", "workflow")
    for report in REPORTS:
        if not (ROOT / report).exists():
            fail(f"missing report {report}")


def check_engine_contract() -> None:
    sys.path.insert(0, str(ROOT))
    engine = importlib.import_module("engines.visual_company_worker_engine")
    for name in [
        "CEO/Product Owner Worker",
        "Visual QA Worker",
        "Mobile QA Worker",
        "Admin Operations Worker",
        "Data/API Worker",
        "Sentinel Workflow Worker",
    ]:
        if name not in [worker.name for worker in engine.WORKERS]:
            fail(f"worker missing: {name}")
    for mode in ["quick", "visual", "product", "admin", "full", "visual-worker", "company-worker", "full-company-qa"]:
        if mode not in engine.MODES:
            fail(f"mode missing: {mode}")
    summary = engine.build_visual_company_worker_summary(VERSION)
    for key in ["global_score", "visual_score", "suggested_tasks", "codex_prompts", "safe_actions", "blocked_actions"]:
        if key not in summary:
            fail(f"summary key missing: {key}")
    if not summary.get("no_auto_code") or not summary.get("no_auto_deploy") or not summary.get("no_fake_data"):
        fail("safety contract missing")


def check_flask_routes() -> None:
    db_fd, db_path = tempfile.mkstemp(prefix="v883_check_", suffix=".db")
    os.close(db_fd)
    os.environ["DB_PATH"] = db_path
    os.environ["AUTOMATION_SECRET"] = "v883-local-secret"
    try:
        sys.path.insert(0, str(ROOT))
        app_module = importlib.import_module("app")
        flask_app = app_module.app
        flask_app.config.update(TESTING=True)
        client = flask_app.test_client()

        runtime = client.get("/api/runtime-version")
        if runtime.status_code != 200:
            fail(f"runtime returned {runtime.status_code}")
        payload = runtime.get_json() or {}
        if payload.get("app_version") != VERSION or not payload.get("has_v883_visual_company_worker"):
            fail("runtime does not expose V883")

        for route in [
            "/api/admin/visual-worker/summary",
            "/api/admin/visual-worker/run",
            "/api/admin/visual-worker/issues",
            "/api/admin/visual-worker/tasks",
        ]:
            response = client.get(route)
            if response.status_code != 403:
                fail(f"{route} should be 403 without admin session, got {response.status_code}")

        if client.get("/admin/visual-worker").status_code not in {302, 303, 401, 403}:
            fail("/admin/visual-worker should be protected without admin session")

        no_secret = client.get("/api/automation/visual-worker/run")
        if no_secret.status_code != 403:
            fail(f"automation visual worker without secret should be 403, got {no_secret.status_code}")

        with_secret = client.get("/api/automation/visual-worker/run?secret=v883-local-secret&dry_run=1&mode=quick")
        if with_secret.status_code != 200:
            fail(f"automation visual worker with secret should be 200, got {with_secret.status_code}")
        data = with_secret.get_json() or {}
        if not data.get("ok") or data.get("no_auto_deploy") is not True or data.get("no_fake_data") is not True:
            fail("automation visual worker safety payload invalid")
    finally:
        try:
            Path(db_path).unlink(missing_ok=True)
        except Exception:
            pass


def check_zip_if_present() -> None:
    zip_path = ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    required = {"app.py", "VERSION.txt", "requirements.txt", "templates/base.html", "engines/visual_company_worker_engine.py"}
    missing = sorted(required - names)
    if missing:
        fail(f"zip missing root files: {missing}")
    forbidden = [name for name in names if name.startswith((".git/", ".venv/", "release_output/")) or name.endswith((".db", ".db-wal", ".db-shm", ".zip"))]
    if forbidden:
        fail(f"zip forbidden entries: {forbidden[:8]}")


def main() -> None:
    check_files()
    check_engine_contract()
    check_flask_routes()
    check_zip_if_present()
    print("V883 visual company worker check OK")


if __name__ == "__main__":
    main()


