from __future__ import annotations

import json
import sqlite3

import pytest

from engines import data_vault_engine as vault
from engines import security_engine
from engines import stripe_payments_engine as billing


def _source_db(path):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO users VALUES('qa-user', 'QA')")


def test_manual_backup_delete_preserves_last_verified_and_removes_manifest_pair(tmp_path):
    source = tmp_path / "source.sqlite"
    _source_db(source)
    backup_dir = tmp_path / "backups"
    first = vault.create_sqlite_backup(source, tmp_path, "QA", directory=backup_dir)
    assert first["ok"] is True

    denied = vault.delete_sqlite_backup(tmp_path, first["backup_file"], directory=backup_dir)
    assert denied == {"ok": False, "error": "last_verified_backup"}
    assert (backup_dir / first["backup_file"]).is_file()
    assert (backup_dir / first["backup_file"]).with_suffix(".json").is_file()

    second = vault.create_sqlite_backup(source, tmp_path, "QA", directory=backup_dir)
    assert second["ok"] is True
    removed = vault.delete_sqlite_backup(tmp_path, first["backup_file"], directory=backup_dir)
    assert removed["ok"] is True
    assert removed["verified"] is True
    assert not (backup_dir / first["backup_file"]).exists()
    assert not (backup_dir / first["backup_file"]).with_suffix(".json").exists()
    assert vault.validate_backup(tmp_path, second["backup_file"], directory=backup_dir)["ok"] is True


def test_rate_limit_slots_are_shared_scoped_and_fail_closed(tmp_path, monkeypatch):
    db_path = str(tmp_path / "security.sqlite")
    first = security_engine.claim_rate_limit_slot(
        db_path, scope="telegram_manual_dispatch", subject="admin-one", limit=2, minutes=60
    )
    second = security_engine.claim_rate_limit_slot(
        db_path, scope="telegram_manual_dispatch", subject="admin-one", limit=2, minutes=60
    )
    third = security_engine.claim_rate_limit_slot(
        db_path, scope="telegram_manual_dispatch", subject="admin-one", limit=2, minutes=60
    )
    other_actor = security_engine.claim_rate_limit_slot(
        db_path, scope="telegram_manual_dispatch", subject="admin-two", limit=2, minutes=60
    )

    assert first["allowed"] and second["allowed"]
    assert third["allowed"] is False and third["reason"] == "rate_limited"
    assert other_actor["allowed"] is True
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT subject_hash FROM security_action_attempts").fetchall()
    assert all("admin-one" not in row[0] and "admin-two" not in row[0] for row in rows)

    monkeypatch.setattr(security_engine, "ensure_security_schema", lambda _path: (_ for _ in ()).throw(OSError("unavailable")))
    unavailable = security_engine.claim_rate_limit_slot(
        db_path, scope="telegram_manual_dispatch", subject="admin-three", limit=2, minutes=60
    )
    assert unavailable == {"allowed": False, "reason": "rate_limit_store_unavailable"}


def test_stripe_audit_storage_keeps_state_but_excludes_customer_payment_details(tmp_path):
    db_path = str(tmp_path / "stripe.sqlite")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY, role TEXT, membership TEXT, membership_admin_granted TEXT, membership_source TEXT)")
        conn.execute("INSERT INTO users VALUES('qa-user','ADMIN','ELITE','1','admin_manual')")
    billing.ensure_stripe_schema(db_path)
    conn = billing.connect(db_path)
    event = {
        "id": "evt_qa",
        "type": "customer.subscription.updated",
        "created": 123,
        "livemode": False,
        "data": {"object": {
            "id": "sub_qa", "object": "subscription", "customer": "cus_qa", "status": "active",
            "current_period_end": 1800000000,
            "billing_details": {"email": "PRIVATE_EMAIL_SENTINEL", "address": {"line1": "PRIVATE_ADDRESS_SENTINEL"}},
            "metadata": {"unrelated": "PRIVATE_METADATA_SENTINEL"},
            "payment_method": {"id": "PRIVATE_PAYMENT_METHOD_SENTINEL"},
        }},
    }
    billing.record_event(conn, event, True, "processed", user_id="qa-user", plan="ELITE", processed=True)
    fields = {
        "user_id": "qa-user", "plan": "ELITE", "customer_id": "cus_qa", "subscription_id": "sub_qa",
        "status": "active", "price_id": "price_qa", "current_period_start": "", "current_period_end": "2030-01-15T00:00:00+00:00",
        "cancel_at_period_end": 0,
    }
    applied = billing.apply_subscription_to_user(conn, fields, "customer.subscription.updated", event["data"]["object"])
    conn.commit()
    webhook_payload = conn.execute("SELECT payload_json FROM payment_webhook_events WHERE event_id='evt_qa'").fetchone()[0]
    subscription_payload = conn.execute("SELECT raw_json FROM stripe_subscriptions WHERE stripe_subscription_id='sub_qa'").fetchone()[0]
    conn.close()

    assert applied["applied"] is True
    for serialized in (webhook_payload, subscription_payload):
        assert "PRIVATE_EMAIL_SENTINEL" not in serialized
        assert "PRIVATE_ADDRESS_SENTINEL" not in serialized
        assert "PRIVATE_METADATA_SENTINEL" not in serialized
        assert "PRIVATE_PAYMENT_METHOD_SENTINEL" not in serialized
    safe_event = json.loads(webhook_payload)
    assert safe_event["id"] == "evt_qa"
    assert safe_event["data"]["object"]["status"] == "active"
    safe_subscription = json.loads(subscription_payload)
    assert safe_subscription["id"] == "sub_qa"
    assert safe_subscription["plan"] == "ELITE"


def test_stripe_checkout_and_portal_failures_never_return_provider_exception_text(tmp_path, monkeypatch):
    class BrokenCheckout:
        class checkout:
            class Session:
                @staticmethod
                def create(**_kwargs):
                    raise RuntimeError("PRIVATE_STRIPE_RESPONSE_SENTINEL")

        class billing_portal:
            class Session:
                @staticmethod
                def create(**_kwargs):
                    raise RuntimeError("PRIVATE_PORTAL_RESPONSE_SENTINEL")

    db_path = str(tmp_path / "stripe-errors.sqlite")
    monkeypatch.setattr(billing, "local_safe_payments_blocked", lambda: False)
    monkeypatch.setattr(billing, "stripe_runtime_status", lambda _path: {"checkout_ready": True, "blockers": []})
    monkeypatch.setattr(billing, "stripe_sdk", lambda: BrokenCheckout())
    monkeypatch.setattr(billing, "public_base_url", lambda: "https://example.invalid")
    monkeypatch.setattr(billing, "plan_price_id", lambda _plan: "price_qa")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "synthetic-only")

    checkout = billing.create_checkout_session(db_path, {"id": "qa-user"}, "PRO")
    portal = billing.create_customer_portal_session(
        db_path,
        {"id": "qa-user", "stripe_customer_id": "cus_qa"},
    )

    assert checkout["error_code"] == "stripe_checkout_unavailable"
    assert checkout["error"] == "No se pudo iniciar el pago. Inténtalo de nuevo más tarde."
    assert "PRIVATE_STRIPE_RESPONSE_SENTINEL" not in str(checkout)
    assert portal["error_code"] == "stripe_portal_unavailable"
    assert portal["error"] == "No se pudo abrir la gestión de la suscripción. Inténtalo de nuevo más tarde."
    assert "PRIVATE_PORTAL_RESPONSE_SENTINEL" not in str(portal)


def test_manual_telegram_send_only_processes_a_new_queue_item(app_module, tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "is_admin_session", lambda: True)
    monkeypatch.setattr(app_module, "current_user_id", lambda: "qa-admin-telegram")
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "telegram-security.sqlite"))
    processed = []
    monkeypatch.setattr(app_module, "enqueue_telegram_message", lambda *args, **kwargs: {"ok": True, "queued": False, "reason": "duplicate"})
    monkeypatch.setattr(app_module, "process_premium_telegram_queue", lambda **kwargs: processed.append(kwargs) or {"sent": 1})

    with app_module.app.test_request_context("/api/telegram/send", method="POST", json={"text": "synthetic only"}):
        response = app_module.api_telegram_send()

    assert response.get_json()["status"] == "NOT_QUEUED"
    assert processed == []


def test_manual_telegram_routes_share_one_per_admin_limit(app_module, tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "telegram-rate.sqlite"))
    monkeypatch.setattr(app_module, "is_admin_session", lambda: True)
    monkeypatch.setattr(app_module, "current_user_id", lambda: "qa-admin-shared-limit")
    monkeypatch.setattr(app_module, "enqueue_telegram_message", lambda *args, **kwargs: {"ok": True, "queued": False, "reason": "duplicate"})
    processed = []
    monkeypatch.setattr(app_module, "process_premium_telegram_queue", lambda **kwargs: processed.append(kwargs) or {"ok": True, "sent": 0})
    routes = [
        ("/api/telegram/send", app_module.api_telegram_send),
        ("/api/telegram/send-test", app_module.api_telegram_send_test),
        ("/api/admin/telegram/test-send", app_module.api_admin_telegram_test_send),
        ("/api/telegram/process-queue", app_module.api_telegram_process_queue),
    ]

    for path, handler in routes:
        with app_module.app.test_request_context(path, method="POST", json={"text": "synthetic only"}):
            response = handler()
        assert response.status_code < 400

    with app_module.app.test_request_context("/api/telegram/send-test", method="POST", json={}):
        blocked = app_module.api_telegram_send_test()

    assert blocked.status_code == 429
    assert blocked.get_json()["error"] == "rate_limited"
    assert processed == [{"limit": 5, "force": False}]


def test_telegram_enqueue_endpoints_share_manual_dispatch_limit(app_module, tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "is_admin_session", lambda: True)
    monkeypatch.setattr(app_module, "current_user_id", lambda: "qa-admin-enqueue-limit")
    monkeypatch.setattr(app_module, "enqueue_daily_matches", lambda **_kwargs: pytest.fail("must not enqueue after limit"))
    monkeypatch.setattr(app_module, "enqueue_daily_picks", lambda **_kwargs: pytest.fail("must not enqueue after limit"))
    monkeypatch.setattr(app_module, "v566_template_recommendations", lambda **_kwargs: pytest.fail("must not build recommendations after limit"))
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "synthetic-chat")
    endpoints = [
        ("/api/telegram/enqueue-daily-matches", app_module.api_telegram_enqueue_daily_matches),
        ("/api/telegram/enqueue-daily-picks", app_module.api_telegram_enqueue_daily_picks),
        ("/api/telegram/enqueue-recommendations", app_module.api_v808_telegram_enqueue_recommendations),
    ]

    for index, (path, handler) in enumerate(endpoints):
        db_path = str(tmp_path / f"enqueue-limit-{index}.sqlite")
        monkeypatch.setattr(app_module, "DB_PATH", db_path)
        for _ in range(4):
            assert security_engine.claim_rate_limit_slot(
                db_path,
                scope="telegram_manual_dispatch",
                subject="qa-admin-enqueue-limit",
                limit=4,
                minutes=60,
            )["allowed"]
        with app_module.app.test_request_context(path, method="POST"):
            response = handler()
        assert response.status_code == 429
        assert response.get_json()["error"] == "rate_limited"


def test_controlled_auto_test_does_not_process_unrelated_pending_queue(app_module, tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "is_admin_session", lambda: True)
    monkeypatch.setattr(app_module, "current_user_id", lambda: "qa-admin-controlled-test")
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "controlled-test.sqlite"))
    monkeypatch.setattr(app_module, "create_telegram_test_candidate", lambda: {"ok": True, "id": "synthetic-candidate"})
    monkeypatch.setattr(
        app_module,
        "enqueue_auto_pick_alerts",
        lambda **_kwargs: {"ok": True, "status": "NO_ELIGIBLE_PICKS", "inserted": 0},
    )
    processed = []
    monkeypatch.setattr(
        app_module,
        "process_premium_telegram_queue",
        lambda **kwargs: processed.append(kwargs) or {"ok": True, "sent": 1},
    )
    monkeypatch.setattr(app_module, "dashboard_data", lambda: {})
    monkeypatch.setattr(app_module, "telegram_diagnostics", lambda: {})
    monkeypatch.setattr(app_module, "telegram_subscribers", lambda **_kwargs: [])
    monkeypatch.setattr(app_module, "rows", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(app_module, "render_template", lambda *_args, **_kwargs: "synthetic-response")

    with app_module.app.test_request_context(
        "/admin/telegram", method="POST", data={"action": "controlled_auto_test"}
    ):
        response = app_module.admin_telegram_page()

    assert response == "synthetic-response"
    assert processed == []
