#!/usr/bin/env python3
"""Validate V884 Render/Visual Worker/Matches QA behavior."""
from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V884_CLIENT_ADMIN_FUNCTIONAL_FLOW_AND_SCREEN_EXPERIENCE_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "V884_REAL_RENDER_VISUAL_WORKER_MATCHES_QA_AND_FIX_REPORT.md",
    "V884_PREFLIGHT_FROM_V883.md",
    "V884_REAL_RENDER_DEPLOYMENT_STATE_QA.md",
    "V884_VISUAL_WORKER_LOCAL_RUN_QA.md",
    "V884_MATCHES_LIVE_PICKS_PRODUCT_QA.md",
    "V884_ADMIN_DATA_OPERATIONS_WORKER_QA.md",
    "V884_VISUAL_LAYOUT_WORKER_QA.md",
    "V884_SENTINEL_VISUAL_WORKER_INTEGRATION_QA.md",
    "V884_CODEX_PROMPTS_FROM_WORKER_QA.md",
    "V884_RENDER_DEPLOY_RUNBOOK.md",
    "V884_NEXT_STEPS.md",
]


def fail(message: str) -> None:
    raise SystemExit(f"V884 check failed: {message}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def check_static_files() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    worker = read("engines/visual_company_worker_engine.py")
    sentinel = read("engines/shark_sentinel_engine.py")
    continuous = read("engines/continuous_shark_sentinel_engine.py")

    require(read("VERSION.txt").strip() == VERSION, "VERSION.txt is not V884")
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION is not V884")
    require(f"APP_VERSION = '{VERSION}'" in app_py, "app.py APP_VERSION is not V884")
    require("data-v884-shell" in base, "base.html missing data-v884-shell")
    require(VERSION in base, "base.html missing V884 cache/version")
    require("has_v884_real_render_visual_worker_matches_qa" in app_py, "runtime V884 flag missing")
    require("has_v883_visual_company_worker" in app_py, "V883 flag missing")
    require("/admin/visual-worker" in app_py, "visual worker admin route missing")
    require("/api/automation/visual-worker/run" in app_py, "visual worker cron route missing")
    require("Pantalla deportiva sin datos reales visibles" in worker, "worker does not detect sports screens without real rows")
    require("Pantalla deportiva sin filas reales visibles" in sentinel, "Sentinel does not detect sports safe-empty row absence")
    require("visual-worker" in continuous and "full-company-qa" in continuous, "Continuous Sentinel modes missing")
    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")


def check_runtime_and_worker() -> None:
    db_fd, db_path = tempfile.mkstemp(prefix="v884_check_", suffix=".db")
    os.close(db_fd)
    os.environ["DB_PATH"] = db_path
    os.environ["AUTOMATION_SECRET"] = "v884-check-secret"
    try:
        sys.path.insert(0, str(ROOT))
        app = importlib.import_module("app")
        app.app.config.update(TESTING=True)
        client = app.app.test_client()

        runtime = client.get("/api/runtime-version")
        require(runtime.status_code == 200, f"runtime returned {runtime.status_code}")
        payload = runtime.get_json() or {}
        require(payload.get("app_version") == VERSION, "runtime app_version is not V884")
        require(payload.get("version_txt") == VERSION, "runtime version_txt is not V884")
        require(payload.get("has_v884_real_render_visual_worker_matches_qa") is True, "runtime V884 flag false")
        require(payload.get("has_v883_visual_company_worker") is True, "runtime V883 flag false")
        require(payload.get("has_v882_core_product_recovery") is True, "runtime V882 flag false")

        for route in [
            "/api/admin/visual-worker/summary",
            "/api/admin/visual-worker/run",
            "/api/admin/visual-worker/issues",
            "/api/admin/visual-worker/tasks",
        ]:
            require(client.get(route).status_code == 403, f"{route} not protected with 403")
        require(client.get("/api/automation/visual-worker/run").status_code == 403, "visual worker cron without secret not 403")
        require(client.get("/api/automation/visual-worker/run?secret=v884-check-secret&dry_run=1").status_code == 200, "visual worker cron with secret not 200")

        result = app.run_visual_company_worker(client, app.APP_VERSION, mode="product", dry_run=True)
        require(result.get("no_auto_deploy") is True and result.get("no_fake_data") is True, "worker safety flags missing")
        issues = result.get("issues", [])
        require(any(issue.get("title") == "Pantalla deportiva sin datos reales visibles" for issue in issues), "worker did not create sports no-real-rows issue")
        require(result.get("suggested_tasks"), "worker did not create task for sports no-real-rows")

        sentinel = app.run_continuous_sentinel_cycle(client, app.APP_VERSION, mode="full-company-qa", dry_run=True)
        require("workflow" in sentinel, "full-company-qa did not create workflow")
        require(sentinel.get("no_fake_data") is True, "sentinel no_fake_data missing")
    finally:
        for suffix in ("", "-wal", "-shm"):
            try:
                Path(f"{db_path}{suffix}").unlink(missing_ok=True)
            except Exception:
                pass


def check_no_bad_claims() -> None:
    secret_corpus = "\n".join(
        read(path)
        for path in [
            "app.py",
            "templates/base.html",
            "templates/admin_visual_worker.html",
            "engines/visual_company_worker_engine.py",
        ]
    ).lower()
    for token in ["sk-", "stripe_live_", "telegram_bot_token=", "api_key="]:
        require(token not in secret_corpus, f"possible secret token found: {token}")
    visible_corpus = "\n".join(
        read(path)
        for path in [
            "templates/base.html",
            "templates/admin_visual_worker.html",
            "reports/V884_REAL_RENDER_VISUAL_WORKER_MATCHES_QA_AND_FIX_REPORT.md",
            "reports/V884_MATCHES_LIVE_PICKS_PRODUCT_QA.md",
            "reports/V884_VISUAL_WORKER_LOCAL_RUN_QA.md",
        ]
    ).lower()
    for phrase in ["apuesta segura", "sin riesgo", "garantizado"]:
        require(phrase not in visible_corpus, f"forbidden betting claim found: {phrase}")
    require("stripe operativo" not in visible_corpus, "false Stripe operative claim found")
    require("telegram filler" not in visible_corpus, "Telegram filler phrase found")
    require("openai activo real" not in visible_corpus, "false OpenAI active claim found")


def check_zip_if_present() -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    required = {"app.py", "VERSION.txt", "requirements.txt", "templates/base.html", "engines/visual_company_worker_engine.py"}
    require(not (required - names), f"zip missing root files: {sorted(required - names)}")
    forbidden = [
        name for name in names
        if name.startswith((".git/", ".venv/", "release_output/", "__pycache__/"))
        or name.endswith((".db", ".db-wal", ".db-shm", ".sqlite", ".zip", ".log", ".pyc"))
    ]
    require(not forbidden, f"zip forbidden entries: {forbidden[:8]}")


def main() -> None:
    check_static_files()
    check_runtime_and_worker()
    check_no_bad_claims()
    check_zip_if_present()
    print("V884 real render visual worker matches QA OK")


if __name__ == "__main__":
    main()

