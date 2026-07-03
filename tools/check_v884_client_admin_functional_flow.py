#!/usr/bin/env python3
"""Validate V884 client/admin functional flow and screen experience."""
from __future__ import annotations

import importlib
import os
from pathlib import Path
import re
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PRESERVED_VERSION = "V884_CLIENT_ADMIN_FUNCTIONAL_FLOW_AND_SCREEN_EXPERIENCE_FINAL"
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"

REPORTS = [
    "V884_CLIENT_ADMIN_FUNCTIONAL_FLOW_AND_SCREEN_EXPERIENCE_REPORT.md",
    "V884_PREFLIGHT_CLIENT_ADMIN_FUNCTIONAL_FLOW.md",
    "V884_BUTTONS_ACTIONS_FUNCTIONAL_AUDIT.md",
    "V884_CLIENT_USER_JOURNEY_FLOW_QA.md",
    "V884_ADMIN_OPERATOR_FLOW_QA.md",
    "V884_SCREEN_REDUNDANCY_AND_CLEANUP_QA.md",
    "V884_CORE_SPORTS_FUNCTIONALITY_QA.md",
    "V884_VISUAL_LAYOUT_FUNCTIONALITY_QA.md",
    "V884_SENTINEL_VISUAL_WORKER_FUNCTIONAL_QA.md",
    "V884_FEATURES_FUNCTIONALITY_AND_VALUE_QA.md",
    "V884_SECURITY_ROLES_FLOW_QA.md",
    "V884_RENDER_CODEX_DEPLOY_AWARENESS_QA.md",
    "V884_NEXT_STEPS.md",
]

CLIENT_ROUTES = [
    "/",
    "/app",
    "/partidos",
    "/calendar",
    "/live",
    "/directo",
    "/picks",
    "/shark",
    "/telegram",
    "/profile",
    "/track-record",
    "/support",
]

ADMIN_API_ROUTES = [
    "/api/admin/visual-worker/summary",
    "/api/admin/visual-worker/run",
    "/api/admin/visual-worker/issues",
    "/api/admin/visual-worker/tasks",
    "/api/admin/continuous-sentinel/summary",
    "/api/admin/sentinel-workflow/summary",
]


def fail(message: str) -> None:
    raise SystemExit(f"V884 functional flow check failed: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def visible_text(html: str) -> str:
    html = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", html or "")
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def check_static_files() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    worker = read("engines/visual_company_worker_engine.py")
    continuous = read("engines/continuous_shark_sentinel_engine.py")

    require(read("VERSION.txt").strip() == VERSION, "VERSION.txt does not match current version")
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION file does not match current version")
    require(f"APP_VERSION = '{VERSION}'" in app_py, "app.py APP_VERSION is not V884 functional flow")
    require("data-v884-shell" in base, "base.html missing data-v884-shell")
    require(PRESERVED_VERSION in base or "data-v884-shell" in base, "base.html missing V884 functional preservation")
    require("NEMESIS V884 CLIENT ADMIN FUNCTIONAL FLOW SCREEN EXPERIENCE ACTIVE" in base, "base.html V884 comment missing")

    require("has_v884_client_admin_functional_flow" in app_py, "runtime V884 functional flag missing")
    require("has_v884_real_render_visual_worker_matches_qa" in app_py, "previous V884 worker flag not preserved")
    require("has_v883_visual_company_worker" in app_py, "V883 worker flag not preserved")

    require("FUNCTIONAL_FLOW_RULES" in worker, "functional flow rules missing in Visual Worker")
    require("BAD_HREFS" in worker and "_links_from_html" in worker, "link audit missing in Visual Worker")
    require("Boton o enlace sin destino real" in worker, "bad link issue missing in Visual Worker")
    require("Enlace admin visible en cliente" in worker, "client/admin crossing issue missing")
    require("Pantalla deportiva sin datos reales visibles" in worker, "sports no-real-rows issue missing")
    require("client_admin_functional_flow_rules_v884" in continuous, "Continuous Sentinel V884 rules missing")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")


def check_runtime_and_routes() -> None:
    db_fd, db_path = tempfile.mkstemp(prefix="v884_functional_", suffix=".db")
    os.close(db_fd)
    os.environ["DB_PATH"] = db_path
    os.environ["AUTOMATION_SECRET"] = "v884-functional-secret"
    try:
        sys.path.insert(0, str(ROOT))
        app = importlib.import_module("app")
        app.app.config.update(TESTING=True)
        client = app.app.test_client()

        runtime = client.get("/api/runtime-version")
        require(runtime.status_code == 200, f"runtime returned {runtime.status_code}")
        payload = runtime.get_json() or {}
        require(payload.get("app_version") == VERSION, "runtime app_version does not match current version")
        require(payload.get("version_txt") == VERSION, "runtime version_txt does not match current version")
        require(payload.get("has_v884_client_admin_functional_flow") is True, "runtime V884 functional flag false")
        require(payload.get("has_v884_real_render_visual_worker_matches_qa") is True, "previous V884 flag false")
        require(payload.get("has_v883_visual_company_worker") is True, "V883 flag false")
        require(payload.get("has_v882_core_product_recovery") is True, "V882 flag false")
        require(payload.get("has_v818_automation") is True, "V818 automation flag false")

        for route in CLIENT_ROUTES:
            response = client.get(route, follow_redirects=False)
            require(response.status_code in {200, 302, 303, 401, 403}, f"{route} unexpected status {response.status_code}")
            text = visible_text(response.get_data(as_text=True) or "")
            lowered = text.lower()
            for bad in ["Ãƒ", "Ã‚", "ï¿½", "undefined", "traceback", "sqlite3."]:
                require(bad.lower() not in lowered, f"{route} visible bad token {bad}")
            require(" apuesta segura " not in f" {lowered} ", f"{route} forbidden betting claim")
            require(" sin riesgo " not in f" {lowered} ", f"{route} forbidden betting claim")
            require("garantizado" not in lowered, f"{route} forbidden betting claim")

        for route in ADMIN_API_ROUTES:
            require(client.get(route).status_code == 403, f"{route} not protected with 403")
        require(client.get("/api/automation/master-tick").status_code == 403, "master tick without secret not 403")
        require(client.get("/api/automation/visual-worker/run").status_code == 403, "visual worker cron without secret not 403")
        require(
            client.get("/api/automation/visual-worker/run?secret=v884-functional-secret&dry_run=1&mode=product").status_code == 200,
            "visual worker cron with secret not 200",
        )

        worker_run = app.run_visual_company_worker(client, app.APP_VERSION, mode="full-company-qa", dry_run=True)
        require(worker_run.get("no_auto_deploy") is True, "worker no_auto_deploy missing")
        require(worker_run.get("no_fake_data") is True, "worker no_fake_data missing")
        require("functional_flow_rules" in worker_run, "worker runtime missing functional_flow_rules")
        require(worker_run.get("suggested_tasks") is not None, "worker tasks missing")

        sentinel_summary = app.build_continuous_sentinel_summary(app.APP_VERSION)
        require("client_admin_functional_flow_rules_v884" in sentinel_summary, "sentinel summary missing V884 rules")
    finally:
        for suffix in ("", "-wal", "-shm"):
            try:
                Path(f"{db_path}{suffix}").unlink(missing_ok=True)
            except Exception:
                pass


def check_no_secret_or_false_operational_claims() -> None:
    corpus = "\n".join(
        read(path)
        for path in [
            "app.py",
            "templates/base.html",
            "templates/admin_visual_worker.html",
            "engines/visual_company_worker_engine.py",
            "engines/continuous_shark_sentinel_engine.py",
        ]
        if (ROOT / path).exists()
    ).lower()
    for token in ["sk-", "stripe_live_", "telegram_bot_token=", "api_key="]:
        require(token not in corpus, f"possible secret marker found: {token}")
    for bad_claim in ["stripe operativo", "openai activo real", "telegram enviado real"]:
        require(bad_claim not in corpus, f"false operational claim found: {bad_claim}")


def check_zip_if_present() -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    required = {
        "app.py",
        "VERSION.txt",
        "APP_VERSION",
        "requirements.txt",
        "templates/base.html",
        "static/app.css",
        "engines/visual_company_worker_engine.py",
        "tools/check_v884_client_admin_functional_flow.py",
    }
    missing = sorted(required - names)
    require(not missing, f"zip missing root files: {missing}")
    forbidden = [
        name
        for name in names
        if name.startswith((".git/", ".venv/", "release_output/", "__pycache__/", ".pytest_cache/"))
        or name.endswith((".db", ".db-wal", ".db-shm", ".sqlite", ".zip", ".log", ".pyc"))
    ]
    require(not forbidden, f"zip forbidden entries: {forbidden[:10]}")


def main() -> None:
    check_static_files()
    check_runtime_and_routes()
    check_no_secret_or_false_operational_claims()
    check_zip_if_present()
    print("V884 client/admin functional flow OK")


if __name__ == "__main__":
    main()
