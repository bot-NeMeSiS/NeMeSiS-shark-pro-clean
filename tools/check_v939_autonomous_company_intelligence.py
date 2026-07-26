#!/usr/bin/env python3
"""Local safety and integration gate for V939 company intelligence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
VERSION_MATCH = re.fullmatch(r"V(\d+)(?:_[A-Z0-9]+)*", VERSION)
EXPECTED_CACHE = f"NEMESIS_CACHE_{VERSION.split('_', 1)[0]}"
MADRID = ZoneInfo("Europe/Madrid")
REQUIRED_ENGINES = [
    "company_intelligence_engine.py",
    "shark_learning_engine.py",
    "pick_intelligence_pipeline_engine.py",
    "telegram_intelligence_engine.py",
    "product_analytics_engine.py",
    "experimentation_engine.py",
    "version_regression_engine.py",
    "recovery_simulator_engine.py",
    "autonomous_quality_platform_engine.py",
]
REQUIRED_REPORTS = [
    "V939_AUTONOMOUS_COMPANY_INTELLIGENCE_GROWTH_AND_QUALITY_PLATFORM_REPORT.md",
    "V939_PREFLIGHT_FROM_V938.md",
    "V939_EXISTING_ENGINES_AND_CAPABILITIES_MAP.md",
    "V939_NO_DOWNGRADE_TRACEABILITY_QA.md",
    "V939_SHARK_LEARNING_ENGINE_QA.md",
    "V939_SHARK_LEARNING_GOVERNANCE_POLICY.md",
    "V939_SHARK_SAMPLE_SIZE_AND_CONFIDENCE_RULES.md",
    "V939_PICK_INTELLIGENCE_PIPELINE_QA.md",
    "V939_PICK_QUALITY_THRESHOLDS.md",
    "V939_PICK_BLOCKING_REASONS_QA.md",
    "V939_TELEGRAM_INTELLIGENCE_QA.md",
    "V939_TELEGRAM_MEMBERSHIP_VALUE_QA.md",
    "V939_TELEGRAM_LEARNING_LIMITATIONS.md",
    "V939_PRODUCT_ANALYTICS_PRIVACY_QA.md",
    "V939_CUSTOMER_FUNNEL_DEFINITIONS.md",
    "V939_RETENTION_AND_CHURN_MEASUREMENT_PLAN.md",
    "V939_CEO_DASHBOARD_QA.md",
    "V939_EXPERIMENTATION_GOVERNANCE_QA.md",
    "V939_VERSION_REGRESSION_ENGINE_QA.md",
    "V939_RECOVERY_SIMULATOR_QA.md",
    "V939_RECOVERY_SCENARIOS.md",
    "V939_AUTONOMOUS_QUALITY_PLATFORM_QA.md",
    "V939_COMPANY_INTELLIGENCE_CRON_QA.md",
    "V939_COMPANY_INTELLIGENCE_MEMORY_QA.md",
    "V939_RESPONSIBLE_GAMBLING_AND_ETHICS_QA.md",
    "V939_SECURITY_PRIVACY_COMPANY_INTELLIGENCE_QA.md",
    "V939_NEXT_STEPS.md",
]
EVIDENCE_STATES = {
    "VERIFIED", "PARTIALLY_VERIFIED", "NOT_CERTIFIED", "NOT_CONFIGURED", "STALE",
    "BLOCKED_BY_ACCESS", "HYPOTHESIS", "INSUFFICIENT_DATA", "REQUIRES_REVIEW",
}


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def admin_session(client) -> None:
    with client.session_transaction() as session:
        session["user_id"] = "v939-admin"
        session["user_name"] = "V939 Admin"
        session["username"] = "v939-admin"
        session["user_email"] = "admin@example.invalid"
        session["user_role"] = "ADMIN"
        session["user_membership"] = "ADMIN"
        session["membership"] = "ADMIN"


def csrf_from_page(html: str) -> str:
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    return match.group(1) if match else ""


def create_engine_fixture(path: Path) -> None:
    now = datetime.now(MADRID)
    kickoff = (now + timedelta(hours=8)).isoformat(timespec="seconds")
    odds_at = (now - timedelta(minutes=5)).isoformat(timespec="seconds")
    stale_at = (now - timedelta(hours=2)).isoformat(timespec="seconds")
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE matches(id TEXT PRIMARY KEY, home_team TEXT, away_team TEXT, competition_name TEXT, kickoff_at TEXT, source TEXT);
        CREATE TABLE picks(id TEXT PRIMARY KEY, match_id TEXT, competition_name TEXT, home_team TEXT, away_team TEXT, market TEXT, selection TEXT, odds REAL, odds_recorded_at TEXT, provider TEXT, risk_level TEXT, stake_units REAL, reasoning TEXT, risk_notes TEXT, kickoff_at TEXT, status TEXT, membership_required TEXT);
        CREATE TABLE historical_picks(id INTEGER PRIMARY KEY, pick_id TEXT, match_id TEXT, competition_name TEXT, market TEXT, selection TEXT, odds REAL, stake REAL, result_status TEXT, profit REAL, confidence REAL, risk_level TEXT, source TEXT, created_at TEXT);
        CREATE TABLE users(id INTEGER PRIMARY KEY, membership TEXT, status TEXT, created_at TEXT);
        CREATE TABLE user_activity(id INTEGER PRIMARY KEY, activity_type TEXT, payload_json TEXT, created_at TEXT);
        CREATE TABLE stripe_events(id INTEGER PRIMARY KEY, event_type TEXT, created_at TEXT);
        CREATE TABLE telegram_delivery_logs(id INTEGER PRIMARY KEY, status TEXT, dedupe_key TEXT, created_at TEXT);
        CREATE TABLE api_sync_runs(id INTEGER PRIMARY KEY, status TEXT, finished_at TEXT);
    """)
    conn.execute("INSERT INTO matches VALUES(?,?,?,?,?,?)", ("m1", "Real Norte", "Real Sur", "Liga Test", kickoff, "fixture-test"))
    valid = ("p1", "m1", "Liga Test", "Real Norte", "Real Sur", "1X2", "Local", 1.85, odds_at, "fixture-test", "medio", 1.0, "Dato completo", "La cuota puede moverse", kickoff, "candidate", "PRO")
    stale = ("p2", "m1", "Liga Test", "Real Norte", "Real Sur", "1X2", "Visitante", 2.10, stale_at, "fixture-test", "alto", 0.5, "Dato stale", "Frescura insuficiente", kickoff, "candidate", "PRO")
    incomplete = ("p3", "m1", "Liga Test", "Real Norte", "Real Sur", "", "", None, None, "fixture-test", "", None, "", "", kickoff, "candidate", "PRO")
    conn.executemany("INSERT INTO picks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (valid, stale, incomplete))
    for index in range(35):
        won = index % 2 == 0
        conn.execute(
            "INSERT INTO historical_picks(pick_id,match_id,competition_name,market,selection,odds,stake,result_status,profit,confidence,risk_level,source,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"h{index}", "m1", "Liga Test", "1X2", "Local", 1.85, 1.0, "won" if won else "lost", 0.85 if won else -1.0, 62.0, "medio", "fixture-test", odds_at),
        )
    for index, plan in enumerate(("FREE", "PRO", "ELITE"), start=1):
        conn.execute("INSERT INTO users VALUES(?,?,?,?)", (index, plan, "active", odds_at))
    for activity in ("login", "view_app", "view_picks", "view_shark", "view_memberships"):
        conn.execute("INSERT INTO user_activity(activity_type,payload_json,created_at) VALUES(?,?,?)", (activity, "{}", odds_at))
    conn.execute("INSERT INTO stripe_events(event_type,created_at) VALUES(?,?)", ("checkout.session.completed", odds_at))
    conn.execute("INSERT INTO telegram_delivery_logs(status,dedupe_key,created_at) VALUES(?,?,?)", ("delivered", "existing-key", odds_at))
    conn.execute("INSERT INTO api_sync_runs(status,finished_at) VALUES(?,?)", ("success", odds_at))
    conn.commit()
    conn.close()


def check_zip_if_present(failures: list[str]) -> None:
    target = ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
    if not target.exists():
        return
    with zipfile.ZipFile(target) as archive:
        names = [name.replace("\\", "/") for name in archive.namelist()]
    forbidden_parts = (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/", "logs/")
    require(not any(any(part in name for part in forbidden_parts) for name in names), "ZIP contains forbidden directory", failures)
    require(not any(name.lower().endswith((".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".zip")) for name in names), "ZIP contains DB or nested ZIP", failures)
    for required in ("app.py", "VERSION.txt", "templates/admin_ceo_dashboard.html", "engines/company_intelligence_engine.py", "tools/check_v939_autonomous_company_intelligence.py"):
        require(required in names, f"ZIP missing {required}", failures)


def main() -> int:
    failures: list[str] = []
    app_source = read("app.py")
    base_source = read("templates/base.html")
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(bool(VERSION_MATCH and int(VERSION_MATCH.group(1)) >= 939), "VERSION.txt is not a canonical V939+ release", failures)
    require(version_bytes.decode("utf-8").strip() == VERSION, "VERSION.txt mismatch", failures)
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION file mismatch", failures)
    require(f"APP_VERSION = '{VERSION}'" in app_source, "app.py version mismatch", failures)
    require(EXPECTED_CACHE in app_source, "service worker cache does not match active release", failures)
    require("has_v939_autonomous_company_intelligence_growth_quality_platform" in app_source, "runtime V939 flag missing", failures)
    require("has_v938_company_operations_recovery_observability_center" in app_source, "V938 flag not preserved", failures)
    require("V890_" not in version_bytes.decode("utf-8"), "downgrade identity detected", failures)

    for engine in REQUIRED_ENGINES:
        require((ROOT / "engines" / engine).exists(), f"missing engine {engine}", failures)
    for template in ("admin_ceo_dashboard.html", "admin_experiments.html", "admin_recovery_simulator.html"):
        require((ROOT / "templates" / template).exists(), f"missing template {template}", failures)
    for report in REQUIRED_REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}", failures)

    for route in (
        "/admin/ceo-dashboard", "/admin/executive", "/admin/company-intelligence", "/admin/direccion", "/admin/empresa",
        "/admin/experiments", "/admin/recovery-simulator",
        "/api/admin/company-intelligence/summary", "/api/admin/company-intelligence/signals",
        "/api/admin/company-intelligence/priorities", "/api/admin/company-intelligence/learning",
        "/api/admin/company-intelligence/telegram", "/api/admin/company-intelligence/product",
        "/api/admin/company-intelligence/business", "/api/admin/company-intelligence/recovery",
        "/api/admin/company-intelligence/regressions", "/api/admin/company-intelligence/run",
        "/api/admin/company-intelligence/generate-prompt", "/api/admin/company-intelligence/approve-recommendation",
        "/api/admin/company-intelligence/reject-recommendation", "/api/automation/company-intelligence/run",
    ):
        require(route in app_source, f"missing route {route}", failures)
    require("/admin/ceo-dashboard" in base_source, "CEO navigation missing", failures)

    engine_sources = "\n".join(read(f"engines/{name}") for name in REQUIRED_ENGINES if name != "shark_learning_engine.py")
    require("automatic_weight_changes\": False" in read("engines/shark_learning_engine.py"), "automatic SHARK weight guard missing", failures)
    require("automatic_deploy\": False" in engine_sources, "automatic deploy guard missing", failures)
    require("automatic_push\": False" in engine_sources, "automatic push guard missing", failures)
    require("send_executed\": False" in engine_sources, "Telegram no-send contract missing", failures)
    require("payment_executed\": False" in engine_sources, "payment no-execute contract missing", failures)
    require(not re.search(r"\b(requests\.(post|get)|urllib\.request\.urlopen|stripe\.(checkout|PaymentIntent)|send_message\()", engine_sources), "new engines contain external execution path", failures)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from engines.company_intelligence_engine import EVIDENCE_STATES as ENGINE_STATES, build_company_intelligence_snapshot, save_company_intelligence_memory
    from engines.experimentation_engine import validate_experiment_definition
    from engines.pick_intelligence_pipeline_engine import build_pick_pipeline_snapshot
    from engines.product_analytics_engine import build_product_analytics_snapshot
    from engines.recovery_simulator_engine import simulate_recovery_scenario
    from engines.shark_learning_engine import build_v939_shark_learning_snapshot
    from engines.telegram_intelligence_engine import build_telegram_intelligence_snapshot

    require(set(ENGINE_STATES) == EVIDENCE_STATES, "evidence state contract mismatch", failures)
    with tempfile.TemporaryDirectory(prefix="nemesis_v939_engine_") as temporary:
        temp_root = Path(temporary)
        empty_db = temp_root / "empty.sqlite3"
        sqlite3.connect(empty_db).close()
        empty_product = build_product_analytics_snapshot(str(empty_db), VERSION)
        empty_learning = build_v939_shark_learning_snapshot(str(empty_db), VERSION)
        require(empty_product.get("certification_state") == "INSUFFICIENT_DATA", "empty product data not insufficient", failures)
        require(empty_learning.get("certification_state") == "INSUFFICIENT_DATA", "empty learning data not insufficient", failures)
        require((empty_learning.get("global") or {}).get("roi") is None, "empty learning invented ROI", failures)

        fixture_db = temp_root / "fixture.sqlite3"
        create_engine_fixture(fixture_db)
        before_hash = sha256(fixture_db)
        company = build_company_intelligence_snapshot(temp_root, fixture_db, VERSION)
        pipeline = build_pick_pipeline_snapshot(str(fixture_db), VERSION)
        telegram = build_telegram_intelligence_snapshot(str(fixture_db), VERSION)
        learning = build_v939_shark_learning_snapshot(str(fixture_db), VERSION)
        after_hash = sha256(fixture_db)
        require(before_hash == after_hash, "read-only engines changed fixture DB", failures)
        require(company.get("database_written") is False and company.get("external_calls") == 0, "company snapshot unsafe", failures)
        require(all(item.get("certification_state") in EVIDENCE_STATES for item in company.get("signals", [])), "invalid signal state", failures)
        require(pipeline.get("premium_ready_count") == 1, "valid pick was not preserved", failures)
        require((pipeline.get("counts") or {}).get("PROVIDER_STALE") == 1, "stale pick not blocked", failures)
        require((pipeline.get("counts") or {}).get("DATA_INCOMPLETE") == 1, "incomplete pick not blocked", failures)
        require(telegram.get("send_executed") is False and telegram.get("telegram_api_called") is False, "Telegram execution detected", failures)
        require(learning.get("certification_state") == "PARTIALLY_VERIFIED", "learning sample not observed", failures)
        require(learning.get("automatic_weight_changes") is False, "learning changed weights", failures)
        require(learning.get("mode") == "OBSERVE", "learning default mode changed", failures)
        prohibited = validate_experiment_definition({"surface": "payments"})
        require(prohibited.get("valid") is False and "PROHIBITED_SURFACE" in prohibited.get("errors", []), "unsafe experiment accepted", failures)
        recovery = simulate_recovery_scenario("database_corrupt")
        require(recovery.get("restore_executed") is False and recovery.get("actions_executed") == [], "recovery simulator executed action", failures)

        memory_snapshot = {"signals": [{"name": "safe", "api_key": "must-not-persist"}], "version": VERSION}
        memory_path = save_company_intelligence_memory(temp_root, memory_snapshot)
        memory_text = memory_path.read_text(encoding="utf-8")
        require("must-not-persist" not in memory_text and "[REDACTED]" in memory_text, "memory did not redact sensitive value", failures)

    previous = {name: os.environ.get(name) for name in ("DB_PATH", "SECRET_KEY", "AUTOMATION_SECRET", "RENDER", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET")}
    with tempfile.TemporaryDirectory(prefix="nemesis_v939_app_") as temporary:
        app_db = Path(temporary) / "app.sqlite3"
        os.environ["DB_PATH"] = str(app_db)
        os.environ["SECRET_KEY"] = "v939-session-test-placeholder"
        os.environ["AUTOMATION_SECRET"] = "v939-automation-test-placeholder"
        os.environ["RENDER"] = ""
        os.environ["TELEGRAM_BOT_TOKEN"] = ""
        os.environ["TELEGRAM_CHAT_ID"] = ""
        os.environ["STRIPE_SECRET_KEY"] = ""
        os.environ["STRIPE_WEBHOOK_SECRET"] = ""
        try:
            import app as app_module
            app_module.app.config.update(TESTING=True, SECRET_KEY="v939-flask-test-placeholder")
            app_module.init_db()
            app_module._V939_INTELLIGENCE_CACHE.update({"at": 0.0, "bundle": None})
            client = app_module.app.test_client()

            runtime_response = client.get("/api/runtime-version")
            runtime = runtime_response.get_json(silent=True) or {}
            require(runtime_response.status_code == 200, "runtime not 200", failures)
            require(runtime.get("version") == VERSION, "runtime version mismatch", failures)
            require(runtime.get("version_files_match") is True, "runtime files mismatch", failures)
            require(runtime.get("deployment_alignment_status") == "aligned_local_files", "runtime alignment mismatch", failures)
            require(runtime.get("service_worker_cache_name") == EXPECTED_CACHE, "runtime cache mismatch", failures)
            require(runtime.get("has_v939_autonomous_company_intelligence_growth_quality_platform") is True, "runtime V939 flag false", failures)
            require(runtime.get("has_v938_company_operations_recovery_observability_center") is True, "runtime V938 flag false", failures)

            admin_gets = [
                "/api/admin/company-intelligence/summary", "/api/admin/company-intelligence/signals",
                "/api/admin/company-intelligence/priorities", "/api/admin/company-intelligence/learning",
                "/api/admin/company-intelligence/telegram", "/api/admin/company-intelligence/product",
                "/api/admin/company-intelligence/business", "/api/admin/company-intelligence/recovery",
                "/api/admin/company-intelligence/regressions",
            ]
            for route in admin_gets:
                require(client.get(route).status_code == 403, f"unprotected admin GET {route}", failures)
            for route in (
                "/api/admin/company-intelligence/run", "/api/admin/company-intelligence/generate-prompt",
                "/api/admin/company-intelligence/approve-recommendation", "/api/admin/company-intelligence/reject-recommendation",
            ):
                require(client.post(route, json={}).status_code == 403, f"unprotected admin POST {route}", failures)
            require(client.post("/api/automation/company-intelligence/run").status_code == 403, "Cron without secret not 403", failures)
            require(client.post("/api/automation/company-intelligence/run?secret=v939-automation-test-placeholder").status_code == 403, "Cron accepted query secret", failures)
            for protected_cron in (
                "/api/automation/operations-center/run",
                "/api/automation/sentinel-autopilot/run",
                "/api/automation/telegram/tick",
                "/api/automation/master-tick",
            ):
                require(client.post(protected_cron).status_code == 403, f"protected Cron without secret not 403: {protected_cron}", failures)
            require(client.get("/api/health").status_code == 200, "health endpoint not 200", failures)

            original_save = app_module.save_company_intelligence_memory
            app_module.save_company_intelligence_memory = lambda root, snapshot: Path(temporary) / "memory.json"
            cron = client.post("/api/automation/company-intelligence/run", headers={"X-Automation-Secret": "v939-automation-test-placeholder"})
            app_module.save_company_intelligence_memory = original_save
            cron_json = cron.get_json(silent=True) or {}
            require(cron.status_code == 200, f"authorized Cron status {cron.status_code}", failures)
            require(cron_json.get("query_secret_accepted") is False, "Cron query policy missing", failures)
            require(cron_json.get("external_calls") == 0 and cron_json.get("production_database_written") is False, "Cron unsafe contract", failures)
            require(not any("v939-automation-test-placeholder" in str(value) for value in cron_json.values()), "Cron response exposed secret", failures)

            admin_session(client)
            for route in ("/admin/ceo-dashboard", "/admin/experiments", "/admin/recovery-simulator"):
                page = client.get(route)
                require(page.status_code == 200, f"admin page {route} status {page.status_code}", failures)
                html = page.get_data(as_text=True)
                require('data-nav-zone="client-bottom"' not in html, f"admin page mixes client nav {route}", failures)
                require("TELEGRAM_BOT_TOKEN=" not in html and "STRIPE_SECRET_KEY=" not in html, f"secret label exposed {route}", failures)
            for route in admin_gets:
                require(client.get(route).status_code == 200, f"admin API {route} not 200", failures)
            page = client.get("/admin/ceo-dashboard")
            csrf = csrf_from_page(page.get_data(as_text=True))
            require(bool(csrf), "CEO dashboard CSRF missing", failures)
            prompt = client.post("/api/admin/company-intelligence/generate-prompt", json={}, headers={"X-CSRF-Token": csrf})
            require(prompt.status_code == 200, f"prompt status {prompt.status_code}", failures)
            require((prompt.get_json(silent=True) or {}).get("action_executed") is False, "prompt endpoint executed action", failures)
        except Exception as exc:
            failures.append(f"runtime exception: {exc.__class__.__name__}: {str(exc)[:400]}")
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    check_zip_if_present(failures)
    if failures:
        print("V939 autonomous company intelligence check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V939 autonomous company intelligence check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
