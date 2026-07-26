#!/usr/bin/env python3
"""Validate the V938 company operations, recovery and observability center."""
from __future__ import annotations

import os
import re
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
VERSION_MATCH = re.fullmatch(r"V(\d+)(?:_[A-Z0-9]+)*", VERSION)
EXPECTED_CACHE = f"NEMESIS_CACHE_{VERSION.split('_', 1)[0]}"
REPORTS = [
    "V938_PREFLIGHT_OPERATIONS_CENTER.md",
    "V938_FINDINGS_EVIDENCE_CLASSIFICATION.md",
    "V938_REPOSITORY_PRIVACY_SECRET_CLASSIFICATION.md",
    "V938_SECRET_GUARD_RECOVERY_QA.md",
    "V938_TELEGRAM_WEBHOOK_SECURITY_CERTIFICATION.md",
    "V938_AUTOMATION_SECRET_TRANSPORT_HARDENING.md",
    "V938_SESSION_COOKIE_SECURITY_QA.md",
    "V938_DISASTER_RECOVERY_DESIGN.md",
    "V938_OFFSITE_BACKUP_READINESS_QA.md",
    "V938_ISOLATED_RESTORE_RUNBOOK.md",
    "V938_RENDER_READ_ONLY_CERTIFICATION.md",
    "V938_TELEGRAM_OPERATIONS_CERTIFICATION.md",
    "V938_STRIPE_MEMBERSHIPS_CERTIFICATION.md",
    "V938_SPORTS_DATA_OPERATIONS_CERTIFICATION.md",
    "V938_EXTERNAL_MONITORING_DEAD_MAN_ALERTS.md",
    "V938_SECOND_OPERATOR_EMERGENCY_RUNBOOK.md",
    "V938_COMPANY_OPERATIONS_RECOVERY_OBSERVABILITY_CENTER_REPORT.md",
]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def admin_session(client) -> None:
    with client.session_transaction() as session:
        session["user_id"] = "v938-admin"
        session["user_name"] = "V938 Admin"
        session["username"] = "v938-admin"
        session["user_email"] = "admin@example.invalid"
        session["user_role"] = "ADMIN"
        session["user_membership"] = "ADMIN"
        session["membership"] = "ADMIN"


def csrf_from_page(html: str) -> str:
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    return match.group(1) if match else ""


def check_zip_if_present(failures: list[str]) -> None:
    path = ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
    if not path.exists():
        return
    with zipfile.ZipFile(path) as archive:
        names = [name.replace("\\", "/") for name in archive.namelist()]
    forbidden = (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/", "logs/")
    require(not any(any(marker in name for marker in forbidden) for name in names), "ZIP contains forbidden directory", failures)
    require(not any(name.endswith((".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".zip")) for name in names), "ZIP contains database or nested ZIP", failures)
    for required in ["app.py", "VERSION.txt", "templates/admin_operations_center.html", "engines/company_operations_center_engine.py", "tools/check_v938_company_operations_center.py"]:
        require(required in names, f"ZIP missing {required}", failures)


def main() -> int:
    failures: list[str] = []
    app_source = read("app.py")
    base = read("templates/base.html")
    template = read("templates/admin_operations_center.html")
    engine = read("engines/company_operations_center_engine.py")
    recovery = read("engines/disaster_recovery_engine.py")
    monitor = read("engines/operations_monitoring_engine.py")
    version_bytes = (ROOT / "VERSION.txt").read_bytes()

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(bool(VERSION_MATCH and int(VERSION_MATCH.group(1)) >= 938), "unsupported successor version", failures)
    require(version_bytes.decode("utf-8").strip() == VERSION, "VERSION.txt mismatch", failures)
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION file mismatch", failures)
    require(f"APP_VERSION = '{VERSION}'" in app_source, "app.py APP_VERSION mismatch", failures)
    require("V890_COMPANY_OPERATIONS_RECOVERY_OBSERVABILITY_CENTER" not in version_bytes.decode("utf-8"), "V890 was used as release identity", failures)

    required_files = [
        "engines/company_operations_center_engine.py",
        "engines/disaster_recovery_engine.py",
        "engines/operations_monitoring_engine.py",
        "automation_workforce/security_secret_guard.py",
        "tools/check_repository_privacy_and_secrets.py",
        "templates/admin_operations_center.html",
    ]
    for relative in required_files:
        require((ROOT / relative).exists(), f"missing {relative}", failures)

    for route in [
        "/admin/operations-center",
        "/admin/operations",
        "/admin/company-operations",
        "/admin/centro-operaciones",
        "/admin/sala-control",
        "/api/admin/operations-center/summary",
        "/api/admin/operations-center/incidents",
        "/api/admin/operations-center/readiness",
        "/api/admin/operations-center/run-safe-scan",
        "/api/admin/operations-center/generate-prompt",
        "/api/admin/operations-center/mark-reviewed",
        "/api/automation/operations-center/run",
    ]:
        require(route in app_source, f"route missing: {route}", failures)

    for token in [
        "CONFIRMADO",
        "NO_CERTIFICADO",
        "HIPOTESIS",
        "BLOQUEADO_POR_ACCESO",
        "REQUIERE_REVISION",
        "production_modified",
        "dangerous_actions_executed",
        "generate_operations_codex_prompt",
        "build_operations_monitoring",
    ]:
        require(token in engine or token in app_source, f"evidence contract missing: {token}", failures)

    require("data-v938-operations-shell" in base, "base V938 shell marker missing", failures)
    require("/admin/operations-center" in base, "admin navigation link missing", failures)
    require("data-v938-template=\"admin_operations_center\"" in template, "operations template marker missing", failures)
    require(EXPECTED_CACHE in app_source, "service worker cache does not match active version", failures)
    require("has_v938_company_operations_recovery_observability_center" in app_source, "runtime V938 flag missing", failures)
    require("has_v937_product_perfection_closeout" in app_source, "V937 runtime flag not preserved", failures)
    require("has_v929_navigation_integrity" in app_source and "has_v931_production_client_routes_hotfix" in app_source, "historical navigation/hotfix flags missing", failures)
    require("SESSION_COOKIE_HTTPONLY=True" in app_source, "HttpOnly cookie hardening missing", failures)
    require("SESSION_COOKIE_SECURE=env_bool" in app_source, "Secure cookie hardening missing", failures)
    require("SESSION_COOKIE_SAMESITE=same_site" in app_source, "SameSite cookie hardening missing", failures)
    require("X-Telegram-Bot-Api-Secret-Token" in app_source, "Telegram webhook signature header missing", failures)
    require("query_secret_accepted\": False" in app_source, "V938 Cron query secret rejection marker missing", failures)
    require("production_database_touched" in recovery and "production_database_is_not_a_restore_fixture" in recovery, "restore production refusal missing", failures)
    require("external_monitor_required" in monitor and "admin_or_internal_only" in monitor, "dead-man contract missing", failures)

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}", failures)

    previous = {name: os.environ.get(name) for name in ["DB_PATH", "SECRET_KEY", "AUTOMATION_SECRET", "TELEGRAM_WEBHOOK_SECRET", "RENDER", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"]}
    with tempfile.TemporaryDirectory(prefix="nemesis_v938_check_") as temporary:
        temp_root = Path(temporary)
        db_path = temp_root / "v938.sqlite3"
        os.environ["DB_PATH"] = str(db_path)
        os.environ["SECRET_KEY"] = "v938-production-cookie-test-placeholder"
        os.environ["AUTOMATION_SECRET"] = "v938-test-placeholder"
        os.environ["TELEGRAM_WEBHOOK_SECRET"] = "v938-webhook-placeholder"
        os.environ["RENDER"] = "1"
        os.environ["TELEGRAM_BOT_TOKEN"] = ""
        os.environ["TELEGRAM_CHAT_ID"] = ""
        os.environ["STRIPE_SECRET_KEY"] = ""
        os.environ["STRIPE_WEBHOOK_SECRET"] = ""
        try:
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            import app as app_module
            app_module.app.config.update(TESTING=True, SECRET_KEY="v938-session-placeholder")
            app_module.init_db()
            client = app_module.app.test_client()

            runtime_response = client.get("/api/runtime-version")
            runtime = runtime_response.get_json(silent=True) or {}
            require(runtime_response.status_code == 200, "runtime not 200", failures)
            require(runtime.get("version") == VERSION, "runtime version mismatch", failures)
            require(runtime.get("version_files_match") is True, "runtime files mismatch", failures)
            require(runtime.get("deployment_alignment_status") == "aligned_local_files", "runtime alignment mismatch", failures)
            require(runtime.get("has_v938_company_operations_recovery_observability_center") is True, "runtime V938 flag false", failures)
            require(runtime.get("service_worker_cache_name") == EXPECTED_CACHE, "runtime service worker cache mismatch", failures)

            admin_gets = [
                "/api/admin/operations-center/summary",
                "/api/admin/operations-center/incidents",
                "/api/admin/operations-center/readiness",
            ]
            for route in admin_gets:
                require(client.get(route).status_code == 403, f"unprotected admin GET: {route}", failures)
            for route in [
                "/api/admin/operations-center/run-safe-scan",
                "/api/admin/operations-center/generate-prompt",
                "/api/admin/operations-center/mark-reviewed",
            ]:
                require(client.post(route, json={}).status_code == 403, f"unprotected admin POST: {route}", failures)

            require(client.post("/api/automation/operations-center/run").status_code == 403, "V938 Cron without secret not 403", failures)
            require(client.post("/api/automation/operations-center/run?secret=v938-test-placeholder").status_code == 403, "V938 Cron accepted query secret", failures)
            original_save = app_module.save_operations_snapshot
            app_module.save_operations_snapshot = lambda root, snapshot: Path(root) / "data" / "runtime" / "v938_test_no_write.json"
            cron = client.post("/api/automation/operations-center/run", headers={"X-Automation-Secret": "v938-test-placeholder"})
            app_module.save_operations_snapshot = original_save
            require(cron.status_code == 200, f"V938 Cron header status {cron.status_code}", failures)
            cron_json = cron.get_json(silent=True) or {}
            require(cron_json.get("query_secret_accepted") is False, "V938 Cron query contract false", failures)
            require(cron_json.get("external_calls") == 0, "V938 Cron reported external call", failures)
            require(cron_json.get("production_database_written") is False, "V938 Cron reported DB write", failures)

            invalid_webhook = client.post("/telegram/webhook", json={"update_id": 1})
            require(invalid_webhook.status_code == 403, "Telegram webhook accepted missing signature", failures)
            valid_webhook = client.post("/telegram/webhook", json={"update_id": 2}, headers={"X-Telegram-Bot-Api-Secret-Token": "v938-webhook-placeholder"})
            require(valid_webhook.status_code == 200, f"Telegram signed webhook status {valid_webhook.status_code}", failures)

            admin_session(client)
            page = client.get("/admin/operations-center")
            html = page.get_data(as_text=True)
            require(page.status_code == 200, "admin Operations Center not 200", failures)
            require("Centro de Operaciones" in html, "Operations Center title missing", failures)
            require('data-nav-zone="client-bottom"' not in html, "admin page mixes client bottom navigation", failures)
            require("TELEGRAM_BOT_TOKEN=" not in html and "STRIPE_SECRET_KEY=" not in html, "admin page exposes secret values", failures)
            for route in admin_gets:
                response = client.get(route)
                require(response.status_code == 200, f"admin route not 200: {route}", failures)
            token = csrf_from_page(html)
            require(bool(token), "CSRF token missing from admin page", failures)
            prompt = client.post("/api/admin/operations-center/generate-prompt", json={}, headers={"X-CSRF-Token": token})
            require(prompt.status_code in {200, 404}, f"prompt endpoint unexpected {prompt.status_code}", failures)

            snapshot = app_module.v938_operations_snapshot()
            require(snapshot.get("mode") == "read_only", "snapshot is not read-only", failures)
            require(snapshot.get("readiness", {}).get("dangerous_actions_executed") is False, "snapshot executed dangerous action", failures)
            require(all(item.get("evidence_state") in {"CONFIRMADO", "NO_CERTIFICADO", "HIPOTESIS", "BLOQUEADO_POR_ACCESO", "REQUIERE_REVISION"} for item in snapshot.get("systems", [])), "invalid evidence classification", failures)
            require(all("score" in score and "gaps" in score and "evidence" in score for score in snapshot.get("scores", {}).values()), "scores lack evidence or gaps", failures)
            require(app_module.app.config.get("SESSION_COOKIE_HTTPONLY") is True, "HttpOnly runtime false", failures)
            require(app_module.app.config.get("SESSION_COOKIE_SECURE") is True, "Secure cookie false in Render mode", failures)
            require(app_module.app.config.get("SESSION_COOKIE_SAMESITE") in {"Lax", "Strict", "None"}, "SameSite runtime invalid", failures)

            connection = sqlite3.connect(db_path)
            connection.execute("CREATE TABLE IF NOT EXISTS v938_close_test(id INTEGER PRIMARY KEY)")
            connection.commit()
            connection.close()
            from engines.data_vault_engine import table_names
            table_names(db_path)
            renamed = temp_root / "v938-renamed.sqlite3"
            os.replace(db_path, renamed)
            os.replace(renamed, db_path)
        except Exception as exc:
            failures.append(f"runtime exception: {exc.__class__.__name__}: {str(exc)[:240]}")
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    from automation_workforce.security_secret_guard import run_security_secret_guard
    secret_guard = run_security_secret_guard(dry_run=True)
    require(secret_guard.get("ok") is True, f"Secret Guard findings: {secret_guard.get('findings_count')}", failures)
    require(secret_guard.get("values_printed") is False, "Secret Guard printed values", failures)
    check_zip_if_present(failures)

    if failures:
        print("V938 company operations center check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V938 company operations center check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
