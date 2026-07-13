#!/usr/bin/env python3
"""Non-destructive V937 P0 verification: sports Cron, latency and Stripe guards."""
from __future__ import annotations

import importlib
import inspect
import hashlib
import hmac
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def prepare_test_db(target: Path) -> None:
    source = ROOT / "data" / "database.db"
    if source.exists() and source.stat().st_size:
        shutil.copy2(source, target)


def local_db_snapshot() -> dict:
    source = (ROOT / "data" / "database.db").resolve()
    if not source.exists():
        return {"status": "LOCAL_DB_MISSING"}
    conn = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        table_names = {
            str(row[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        specs = {
            "matches": "updated_at",
            "api_sync_logs": "finished_at",
            "scheduler_locks": "last_run",
            "api_football_live_sync_state": "last_sync_at",
            "odds_snapshots": "created_at",
            "picks": "updated_at",
        }
        snapshot = {"status": "READ_ONLY", "bytes": source.stat().st_size, "tables": {}}
        for table, preferred_column in specs.items():
            if table not in table_names:
                snapshot["tables"][table] = {"status": "MISSING"}
                continue
            columns = {
                str(row[1])
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            latest = ""
            if preferred_column in columns:
                latest = conn.execute(
                    f"SELECT MAX({preferred_column}) FROM {table}"
                ).fetchone()[0] or ""
            snapshot["tables"][table] = {
                "rows": int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]),
                "latest": str(latest),
            }
        return snapshot
    finally:
        conn.close()


def ensure_stripe_test_user(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
              id TEXT PRIMARY KEY, name TEXT, email TEXT, password_hash TEXT,
              role TEXT DEFAULT 'FREE', membership TEXT DEFAULT 'FREE',
              membership_source TEXT DEFAULT '', membership_started_at TEXT DEFAULT '',
              membership_expires_at TEXT DEFAULT '', membership_note TEXT DEFAULT '',
              membership_updated_at TEXT DEFAULT '', membership_updated_by TEXT DEFAULT '',
              membership_admin_granted INTEGER DEFAULT 0,
              stripe_customer_id TEXT DEFAULT '', stripe_subscription_id TEXT DEFAULT '',
              stripe_subscription_status TEXT DEFAULT '', stripe_price_id TEXT DEFAULT '',
              stripe_current_period_end TEXT DEFAULT '', last_payment_status TEXT DEFAULT '',
              last_payment_at TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            "INSERT OR REPLACE INTO users(id,name,email,password_hash,role,membership) VALUES(?,?,?,?,?,?)",
            ("v937-stripe-user", "V937 Check", "v937-check@example.invalid", "not-a-login", "FREE", "FREE"),
        )
        conn.commit()
    finally:
        conn.close()


def subscription_event(event_id: str, status: str, plan: str) -> dict:
    return {
        "id": event_id,
        "type": "customer.subscription.updated" if status != "canceled" else "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_v937_check",
                "object": "subscription",
                "customer": "cus_v937_check",
                "status": status,
                "metadata": {"user_id": "v937-stripe-user", "plan": plan},
                "items": {"data": [{"price": {"id": f"price_{plan.lower()}_check"}}]},
                "current_period_start": 1_700_000_000,
                "current_period_end": 1_900_000_000,
                "cancel_at_period_end": False,
            }
        },
    }


def run() -> dict:
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
    require(version == EXPECTED, f"VERSION inesperada: {version}")
    render_text = (ROOT / "render.yaml").read_text(encoding="utf-8")
    app_text = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    engine_text = (ROOT / "engines" / "api_football_live_tracker_engine.py").read_text(encoding="utf-8")
    telegram_runner_text = (ROOT / "tools" / "render_cron_telegram_tick.py").read_text(encoding="utf-8")
    require("nemesis-sports-sync" in render_text, "Falta Render Cron deportivo")
    require('schedule: "*/15 * * * *"' in render_text, "Frecuencia Cron deportiva incorrecta")
    require("python tools/render_cron_sports_sync.py" in render_text, "Runner Cron no configurado")
    require("/api/automation/sports/sync" in app_text, "Endpoint deportivo protegido ausente")
    require("telegram_cron_with_sports_sync" in app_text, "Falta fallback deportivo sobre el Cron existente")
    require('"21600"' in engine_text, "Cache conservadora de fixtures no aplicada")
    require('"X-Automation-Secret": automation_secret' in telegram_runner_text, "Telegram Cron no usa cabecera protegida")
    require("urlencode({\"secret\"" not in telegram_runner_text and "?secret=" not in telegram_runner_text, "Telegram Cron expone el secreto en URL")
    source_db = local_db_snapshot()

    original_env = dict(os.environ)
    with tempfile.TemporaryDirectory(prefix="nemesis-v937-operational-") as tmp:
        db_path = Path(tmp) / "v937-operational.db"
        prepare_test_db(db_path)
        os.environ["DB_PATH"] = str(db_path)
        os.environ["AUTOMATION_SECRET"] = "v937-local-operational-check"
        os.environ["APP_PUBLIC_URL"] = "https://example.invalid"
        for key in (
            "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_PRO",
            "STRIPE_PRICE_ELITE", "THE_ODDS_API_KEY", "API_FOOTBALL_KEY",
            "API_SPORTS_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        ):
            os.environ.pop(key, None)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        module = importlib.import_module("app")
        module.DB_PATH = str(db_path)
        module.seed_core()
        client = module.app.test_client()

        summary_builds = []
        original_summary_builder = module._build_public_home_sports_summary
        module.invalidate_v934_realtime_cache("v934:sports:public-summary")
        module._build_public_home_sports_summary = lambda: (
            summary_builds.append(True)
            or {"valid_matches_today": [], "valid_active_picks": [], "no_render_api_call": True}
        )
        try:
            first_summary = module.get_public_home_sports_summary()
            second_summary = module.get_public_home_sports_summary()
        finally:
            module._build_public_home_sports_summary = original_summary_builder
            module.invalidate_v934_realtime_cache("v934:sports:public-summary")
        require(len(summary_builds) == 1, "El resumen deportivo no reutiliza la cache local de 15 segundos")
        require(first_summary.get("summary_cache_status") == "refreshed", "Primer resumen no refresco cache")
        require(second_summary.get("summary_cache_status") == "hit", "Segundo resumen no uso cache")

        canonical_route_sources = {
            "home": inspect.getsource(module.home),
            "calendar": inspect.getsource(module.calendar_page),
            "live": inspect.getsource(module.live_page),
            "picks": inspect.getsource(module.picks_page),
        }
        for route_name, route_source in canonical_route_sources.items():
            require("build_v757_app_center" not in route_source, f"{route_name} reconstruye contexto legado v757")
            require("v769_highlights_content_center" not in route_source, f"{route_name} reconstruye highlights no usados")
        require("activity_write" not in canonical_route_sources["picks"], "Picks escribe actividad durante render")

        require(client.get("/api/automation/sports/sync").status_code == 403, "Cron sin secreto no devuelve 403")
        module.sync_api_football_match_window = lambda *args, **kwargs: {
            "ok": True, "status": "cache", "fixtures_count": 3, "external_calls": 0,
        }
        module.sync_api_football_live_tracker = lambda *args, **kwargs: {
            "ok": True, "status": "cache", "fixtures_count": 0, "external_calls": 0,
        }
        module.sync_odds_events = lambda *args, **kwargs: {
            "ok": True, "status": "cache", "processed": 0, "external_calls": 0,
        }
        cron_response = client.get(
            "/api/automation/sports/sync?runner=render_cron",
            headers={"X-Automation-Secret": "v937-local-operational-check", "X-NeMeSiS-Cron-Runner": "render-cron"},
        )
        cron_payload = cron_response.get_json() or {}
        require(cron_response.status_code == 200, f"Cron protegido -> {cron_response.status_code}")
        require(cron_payload.get("ok") is True, f"Cron protegido no OK: {cron_payload}")
        require(cron_payload.get("no_telegram") is True, "Cron deportivo no acredita aislamiento Telegram")
        require(cron_payload.get("no_payments") is True, "Cron deportivo no acredita aislamiento pagos")
        require("v937-local-operational-check" not in cron_response.get_data(as_text=True), "Secreto expuesto")

        telegram_response = client.get(
            "/api/automation/telegram/tick?runner=render_cron&dry_run=1",
            headers={"X-Automation-Secret": "v937-local-operational-check", "X-NeMeSiS-Cron-Runner": "render-cron"},
        )
        telegram_payload = telegram_response.get_json() or {}
        require(telegram_response.status_code == 200, f"Telegram Cron protegido -> {telegram_response.status_code}")
        require(int(telegram_payload.get("sent_count", telegram_payload.get("sent", 0)) or 0) == 0, "Telegram dry-run informó un envío real")
        require("v937-local-operational-check" not in telegram_response.get_data(as_text=True), "Telegram Cron expuso el secreto")

        original_telegram_tick = module.telegram_scheduler_tick
        original_sports_cycle = module.run_sports_sync_cycle
        shared_trigger = {}
        module.telegram_scheduler_tick = lambda force=False: {
            "ok": True, "status": "QUEUE_EMPTY", "sent": 0, "inserted": 0, "processed": 0,
        }
        module.run_sports_sync_cycle = lambda force=False, trigger_type="sports_cron": (
            shared_trigger.update({"force": force, "trigger_type": trigger_type})
            or {"ok": True, "status": "OK", "no_telegram": True, "no_payments": True}
        )
        try:
            shared_response = client.get(
                "/api/automation/telegram/tick?runner=render_cron",
                headers={"X-Automation-Secret": "v937-local-operational-check", "X-NeMeSiS-Cron-Runner": "render-cron"},
            )
        finally:
            module.telegram_scheduler_tick = original_telegram_tick
            module.run_sports_sync_cycle = original_sports_cycle
        shared_payload = shared_response.get_json() or {}
        require(shared_response.status_code == 200, f"Cron compartido -> {shared_response.status_code}")
        require(int(shared_payload.get("sent_count", shared_payload.get("sent", 0)) or 0) == 0, "Cron compartido informo envio Telegram")
        require(shared_trigger.get("trigger_type") == "shared_telegram_cron", "Cron compartido no invoco el ciclo deportivo")

        client.get("/")
        route_timings = {}
        for route, budget in (("/", 1.0), ("/calendar", 2.0), ("/live", 2.0), ("/picks", 2.0)):
            started = time.perf_counter()
            response = client.get(route)
            elapsed = time.perf_counter() - started
            route_timings[route] = round(elapsed, 4)
            require(response.status_code == 200, f"{route} -> {response.status_code}")
            require(elapsed < budget, f"{route} excede presupuesto local: {elapsed:.3f}s")
        with client.session_transaction() as session:
            session["user_role"] = "ADMIN"
            session["user_id"] = "v937-operational-admin"
        started = time.perf_counter()
        admin_response = client.get("/admin/dashboard")
        admin_elapsed = time.perf_counter() - started
        route_timings["/admin/dashboard"] = round(admin_elapsed, 4)
        require(admin_response.status_code == 200, f"/admin/dashboard -> {admin_response.status_code}")
        require(admin_elapsed < 1.5, f"/admin/dashboard excede presupuesto local: {admin_elapsed:.3f}s")

        runtime = client.get("/api/runtime-version").get_json() or {}
        require(runtime.get("version") == EXPECTED, "Runtime local no es V937")
        require(runtime.get("v937_sports_cron_configured") is True, "Runtime no detecta Cron deportivo")
        require(runtime.get("v937_sports_cron_shared_runner_enabled") is True, "Runtime no detecta fallback Cron compartido")
        require(runtime.get("v937_sports_cron_trigger_type") in {"sports_cron", "shared_telegram_cron"}, "Runtime no acredita el trigger deportivo")
        require(runtime.get("v937_request_scoped_sqlite_reads") is True, "Runtime no detecta lecturas SQLite por request")
        require(runtime.get("v937_stripe_checkout_idempotency_guard") is True, "Guard idempotente Checkout ausente")
        require(runtime.get("v937_stripe_webhook_idempotency_guard") is True, "Guard idempotente webhook ausente")

        stripe = importlib.import_module("engines.stripe_payments_engine")
        ensure_stripe_test_user(str(db_path))
        stripe_module = stripe.stripe_sdk()
        require(stripe_module is not None, "Stripe SDK declarado pero no instalado")
        sdk_version = str(getattr(stripe_module, "VERSION", getattr(stripe_module, "__version__", "unknown")))

        os.environ["STRIPE_SECRET_KEY"] = "sk_test_v937_local_contract_only"
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_v937_local_contract_only"
        os.environ["STRIPE_PRICE_PRO"] = "price_v937_pro_contract"
        os.environ["STRIPE_PRICE_ELITE"] = "price_v937_elite_contract"
        os.environ["PAYMENTS_ENABLED"] = "true"
        os.environ["PAYMENTS_MODE"] = "stripe_test"
        os.environ["APP_PUBLIC_URL"] = "https://example.invalid"

        captured_checkout = {}
        captured_portal = {}
        original_checkout_create = stripe_module.checkout.Session.create
        original_portal_create = stripe_module.billing_portal.Session.create
        stripe_module.checkout.Session.create = lambda **kwargs: (
            captured_checkout.update(kwargs) or {"id": "cs_test_v937_contract", "url": "https://example.invalid/checkout"}
        )
        stripe_module.billing_portal.Session.create = lambda **kwargs: (
            captured_portal.update(kwargs) or {"url": "https://example.invalid/portal"}
        )
        try:
            checkout_contract = stripe.create_checkout_session(
                str(db_path),
                {"id": "v937-stripe-user", "email": "v937-check@example.invalid", "membership": "FREE"},
                "PRO",
            )
            require(checkout_contract.get("ok") is True, f"Contrato Checkout SDK falló: {checkout_contract}")
            require(captured_checkout.get("mode") == "subscription", "Checkout no usa modo subscription")
            require((captured_checkout.get("line_items") or [{}])[0].get("price") == "price_v937_pro_contract", "Checkout no usa Price configurado")
            require(bool(captured_checkout.get("idempotency_key")), "Checkout SDK no recibe idempotency_key")

            conn = sqlite3.connect(str(db_path))
            conn.execute("UPDATE users SET stripe_customer_id=? WHERE id=?", ("cus_v937_contract", "v937-stripe-user"))
            conn.commit()
            conn.close()
            portal_contract = stripe.create_customer_portal_session(str(db_path), {"id": "v937-stripe-user"})
            require(portal_contract.get("ok") is True, f"Contrato Portal SDK falló: {portal_contract}")
            require(captured_portal.get("customer") == "cus_v937_contract", "Portal no usa el Customer guardado")
        finally:
            stripe_module.checkout.Session.create = original_checkout_create
            stripe_module.billing_portal.Session.create = original_portal_create

        signed_event = subscription_event("evt_v937_signature", "active", "PRO")
        signed_event["object"] = "event"
        signed_payload = json.dumps(signed_event, separators=(",", ":")).encode("utf-8")
        signed_timestamp = int(time.time())
        signed_digest = hmac.new(
            os.environ["STRIPE_WEBHOOK_SECRET"].encode("utf-8"),
            str(signed_timestamp).encode("ascii") + b"." + signed_payload,
            hashlib.sha256,
        ).hexdigest()
        signed_header = f"t={signed_timestamp},v1={signed_digest}"
        verified_event = stripe.parse_webhook_event(signed_payload, signed_header)
        require(str(getattr(verified_event, "id", "") or "") == "evt_v937_signature", "Firma webhook SDK no validada")

        fixed = datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc)
        key_a = stripe.checkout_idempotency_key("v937-stripe-user", "PRO", fixed)
        key_b = stripe.checkout_idempotency_key("v937-stripe-user", "PRO", fixed + timedelta(minutes=5))
        key_c = stripe.checkout_idempotency_key("v937-stripe-user", "PRO", fixed + timedelta(minutes=11))
        require(key_a == key_b and key_a != key_c, "Ventana idempotente Checkout incorrecta")

        current_event = {"value": subscription_event("evt_v937_pro", "active", "PRO")}
        original_parser = stripe.parse_webhook_event
        stripe.parse_webhook_event = lambda payload, signature: current_event["value"]
        try:
            first = stripe.process_stripe_webhook(str(db_path), b"{}", "verified-local")
            duplicate = stripe.process_stripe_webhook(str(db_path), b"{}", "verified-local")
            current_event["value"] = subscription_event("evt_v937_elite", "active", "ELITE")
            upgraded = stripe.process_stripe_webhook(str(db_path), b"{}", "verified-local")
            current_event["value"] = subscription_event("evt_v937_cancel", "canceled", "ELITE")
            canceled = stripe.process_stripe_webhook(str(db_path), b"{}", "verified-local")
        finally:
            stripe.parse_webhook_event = original_parser
        require(first.get("processed") is True, f"Alta PRO no aplicada: {first}")
        require(duplicate.get("duplicate") is True and duplicate.get("status") == "idempotent_duplicate", "Webhook duplicado no deduplicado")
        require(upgraded.get("processed") is True, f"Upgrade ELITE no aplicado: {upgraded}")
        require(canceled.get("processed") is True, f"Cancelacion no aplicada: {canceled}")
        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT membership FROM users WHERE id='v937-stripe-user'").fetchone()
        events = conn.execute("SELECT COUNT(*) FROM payment_webhook_events").fetchone()[0]
        conn.close()
        require(row and row[0] == "FREE", "Cancelacion no devuelve a FREE")
        require(events == 3, f"Eventos webhook inesperados: {events}")

        result = {
            "ok": True,
            "version": EXPECTED,
            "sports_cron": "PASS_LOCAL_SAFE_SIMULATION",
            "telegram_cron_header_guard": "PASS",
            "telegram_cron_dry_run": "PASS_ZERO_SENDS",
            "route_timings_seconds": route_timings,
            "render_legacy_contexts_removed": True,
            "sports_summary_cache_15s": "PASS",
            "local_db_snapshot": source_db,
            "stripe_checkout_idempotency": "PASS",
            "stripe_sdk_version": sdk_version,
            "stripe_sdk_checkout_contract": "PASS_NO_NETWORK",
            "stripe_sdk_portal_contract": "PASS_NO_NETWORK",
            "stripe_webhook_signature_verification": "PASS_LOCAL_SIGNATURE",
            "stripe_webhook_idempotency": "PASS",
            "stripe_membership_transitions": "FREE_TO_PRO_TO_ELITE_TO_FREE_PASS",
            "real_provider_calls": 0,
            "real_telegram_sends": 0,
            "real_payments": 0,
        }
    os.environ.clear()
    os.environ.update(original_env)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=True, indent=2, sort_keys=True))
