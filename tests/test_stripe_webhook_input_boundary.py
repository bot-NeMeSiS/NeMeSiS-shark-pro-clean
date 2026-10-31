from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace

import pytest

from engines import stripe_payments_engine as billing


def _seed_membership_checkout(db_path, session_id="cs_1"):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE users (
            id TEXT PRIMARY KEY, role TEXT, membership TEXT, membership_source TEXT,
            membership_admin_granted INTEGER DEFAULT 0, membership_started_at TEXT,
            membership_expires_at TEXT, membership_note TEXT, membership_updated_at TEXT,
            membership_updated_by TEXT, stripe_customer_id TEXT, stripe_subscription_id TEXT,
            stripe_subscription_status TEXT, stripe_price_id TEXT, stripe_current_period_end TEXT,
            last_payment_status TEXT, last_payment_at TEXT
        )"""
    )
    conn.execute(
        "INSERT INTO users(id,role,membership,membership_source,membership_admin_granted,stripe_customer_id) VALUES(?,?,?,?,?,?)",
        ("user-1", "FREE", "FREE", "", 0, "cus_1"),
    )
    conn.commit()
    conn.close()
    billing.ensure_stripe_schema(str(db_path))
    conn = billing.connect(str(db_path))
    conn.execute(
        """INSERT INTO stripe_checkout_sessions
           (id,user_id,plan,stripe_session_id,status,created_at)
           VALUES(?,?,?,?,?,?)""",
        ("checkout-1", "user-1", "PRO", session_id, "created", billing.utc_now()),
    )
    conn.commit()
    conn.close()


def _active_subscription(subscription_id="sub_1"):
    return {
        "id": subscription_id,
        "object": "subscription",
        "customer": "cus_1",
        "status": "active",
        "metadata": {"user_id": "user-1", "plan": "PRO"},
        "items": {"data": [{"price": {"id": "price_pro"}}]},
        "current_period_start": 1792000000,
        "current_period_end": 1794592000,
        "cancel_at_period_end": False,
    }


def _checkout_event(event_id, event_type, payment_status, session_id="cs_1"):
    return {
        "id": event_id,
        "type": event_type,
        "data": {"object": {
            "id": session_id,
            "object": "checkout.session",
            "mode": "subscription",
            "payment_status": payment_status,
            "client_reference_id": "user-1",
            "customer": "cus_1",
            "subscription": "sub_1",
            "metadata": {"user_id": "user-1", "plan": "PRO"},
        }},
    }


def test_oversized_direct_webhook_input_is_rejected_before_schema_or_verification(tmp_path, monkeypatch):
    monkeypatch.setattr(billing, "local_safe_payments_blocked", lambda: False)
    parser_called = False

    def parse(_payload, _signature):
        nonlocal parser_called
        parser_called = True
        raise AssertionError("oversized payload reached signature verification")

    monkeypatch.setattr(billing, "parse_webhook_event", parse)
    db_path = tmp_path / "stripe.sqlite"
    payload = b"x" * (billing.MAX_STRIPE_WEBHOOK_BODY_BYTES + 1)

    result = billing.process_stripe_webhook(str(db_path), payload, "invalid")

    assert result["status"] == "payload_too_large"
    assert result["ok"] is False
    assert parser_called is False
    assert not db_path.exists()


def test_invalid_webhook_cannot_insert_or_overwrite_event_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(billing, "local_safe_payments_blocked", lambda: False)
    db_path = str(tmp_path / "stripe.sqlite")
    billing.ensure_stripe_schema(db_path)
    conn = billing.connect(db_path)
    trusted = {"id": "evt_trusted", "type": "invoice.paid", "data": {"object": {"id": "in_trusted"}}}
    billing.record_event(conn, trusted, True, "verified_stored", processed=True)
    conn.commit()
    before = conn.execute(
        "SELECT id,event_id,verified,processed,status,payload_json FROM payment_webhook_events ORDER BY id"
    ).fetchall()
    conn.close()

    monkeypatch.setattr(
        billing,
        "parse_webhook_event",
        lambda _payload, _signature: (_ for _ in ()).throw(ValueError("invalid test signature")),
    )
    attacker_payload = json.dumps(
        {
            "id": "evt_trusted",
            "type": "checkout.session.completed",
            "data": {"object": {"id": "attacker-session"}},
        }
    ).encode()
    result = billing.process_stripe_webhook(db_path, attacker_payload, "invalid")

    conn = billing.connect(db_path)
    after = conn.execute(
        "SELECT id,event_id,verified,processed,status,payload_json FROM payment_webhook_events ORDER BY id"
    ).fetchall()
    conn.close()
    assert result["ok"] is False
    assert result["verified"] is False
    assert result["status"] == "invalid_signature"
    assert [tuple(row) for row in after] == [tuple(row) for row in before]


@pytest.mark.parametrize("payload", [b"not-json", b"\xff", b"[]", b"null"])
def test_rejected_payload_shapes_return_without_persisting_or_raising(tmp_path, monkeypatch, payload):
    monkeypatch.setattr(billing, "local_safe_payments_blocked", lambda: False)
    db_path = str(tmp_path / "stripe.sqlite")
    monkeypatch.setattr(
        billing,
        "parse_webhook_event",
        lambda _payload, _signature: (_ for _ in ()).throw(ValueError("invalid")),
    )

    result = billing.process_stripe_webhook(db_path, payload, "invalid")

    assert result["ok"] is False
    assert result["status"] == "invalid_signature"
    assert not (tmp_path / "stripe.sqlite").exists()


def test_verified_payment_webhook_still_updates_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(billing, "local_safe_payments_blocked", lambda: False)
    db_path = str(tmp_path / "stripe.sqlite")
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE users (
            id TEXT PRIMARY KEY,
            role TEXT,
            membership TEXT,
            stripe_customer_id TEXT,
            last_payment_status TEXT,
            last_payment_at TEXT,
            membership_note TEXT
        )"""
    )
    conn.execute(
        "INSERT INTO users(id,role,membership,stripe_customer_id) VALUES(?,?,?,?)",
        ("user-1", "PRO", "PRO", "cus-1"),
    )
    conn.commit()
    conn.close()
    event = {
        "id": "evt_paid_1",
        "type": "invoice.paid",
        "data": {"object": {"id": "in-1", "customer": "cus-1", "subscription": "sub-1", "currency": "eur"}},
    }
    monkeypatch.setattr(billing, "parse_webhook_event", lambda _payload, _signature: event)

    first = billing.process_stripe_webhook(db_path, b"signed-event", "valid-signature")
    second = billing.process_stripe_webhook(db_path, b"signed-event", "valid-signature")

    conn = billing.connect(db_path)
    user = conn.execute("SELECT last_payment_status FROM users WHERE id='user-1'").fetchone()
    stored = conn.execute(
        "SELECT verified,processed,status FROM payment_webhook_events WHERE event_id='evt_paid_1'"
    ).fetchone()
    conn.close()
    assert first["ok"] is True and first["verified"] is True and first["processed"] is True
    assert second["duplicate"] is True
    assert user["last_payment_status"] == "paid"
    assert tuple(stored) == (1, 1, "payment_recorded")


def test_checkout_completed_waits_for_delayed_payment_then_async_success_activates(tmp_path, monkeypatch):
    monkeypatch.setattr(billing, "local_safe_payments_blocked", lambda: False)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_not_real")
    monkeypatch.setenv("STRIPE_PRICE_PRO_MONTHLY", "price_pro")
    db_path = str(tmp_path / "stripe-checkout.sqlite")
    _seed_membership_checkout(db_path)
    events = {
        "current": _checkout_event("evt_completed", "checkout.session.completed", "unpaid"),
    }
    monkeypatch.setattr(billing, "parse_webhook_event", lambda _payload, _signature: events["current"])

    class SubscriptionAPI:
        calls = 0

        @classmethod
        def retrieve(cls, subscription_id):
            cls.calls += 1
            return _active_subscription(subscription_id)

    monkeypatch.setattr(billing, "stripe_sdk", lambda: SimpleNamespace(Subscription=SubscriptionAPI))

    pending = billing.process_stripe_webhook(db_path, b"signed", "valid")
    conn = billing.connect(db_path)
    membership_while_pending = conn.execute("SELECT membership FROM users WHERE id='user-1'").fetchone()[0]
    conn.close()
    assert pending["ok"] is True
    assert pending["status"] == "awaiting_async_payment"
    assert membership_while_pending == "FREE"
    assert SubscriptionAPI.calls == 0

    events["current"] = _checkout_event("evt_async_paid", "checkout.session.async_payment_succeeded", "paid")
    completed = billing.process_stripe_webhook(db_path, b"signed", "valid")
    conn = billing.connect(db_path)
    membership_after_payment = conn.execute("SELECT membership FROM users WHERE id='user-1'").fetchone()[0]
    conn.close()
    assert completed["ok"] is True and completed["processed"] is True
    assert membership_after_payment == "PRO"
    assert SubscriptionAPI.calls == 1


def test_checkout_subscription_lookup_failure_is_retryable_and_never_grants_fallback_access(tmp_path, monkeypatch):
    monkeypatch.setattr(billing, "local_safe_payments_blocked", lambda: False)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_not_real")
    # The retried verified subscription has price_pro; configure its trusted mapping.
    # Do not weaken the production price-to-entitlement validation for mock data.
    monkeypatch.setenv("STRIPE_PRICE_PRO_MONTHLY", "price_pro")
    db_path = str(tmp_path / "stripe-retry.sqlite")
    _seed_membership_checkout(db_path)
    event = _checkout_event("evt_retryable", "checkout.session.completed", "paid")
    monkeypatch.setattr(billing, "parse_webhook_event", lambda _payload, _signature: event)

    class SubscriptionAPI:
        fail = True

        @classmethod
        def retrieve(cls, _subscription_id):
            if cls.fail:
                raise TimeoutError("simulated Stripe lookup timeout")
            return _active_subscription()

    monkeypatch.setattr(billing, "stripe_sdk", lambda: SimpleNamespace(Subscription=SubscriptionAPI))

    first = billing.process_stripe_webhook(db_path, b"signed", "valid")
    conn = billing.connect(db_path)
    membership_after_failure = conn.execute("SELECT membership FROM users WHERE id='user-1'").fetchone()[0]
    conn.close()
    assert first["ok"] is False and first["retryable"] is True
    assert first["status"] == "subscription_confirmation_retryable"
    assert membership_after_failure == "FREE"

    SubscriptionAPI.fail = False
    retry = billing.process_stripe_webhook(db_path, b"signed", "valid")
    conn = billing.connect(db_path)
    user = conn.execute("SELECT membership,stripe_subscription_status FROM users WHERE id='user-1'").fetchone()
    receipt = conn.execute(
        "SELECT verified,processed,status FROM payment_webhook_events WHERE event_id='evt_retryable'"
    ).fetchone()
    conn.close()
    assert retry["ok"] is True and retry["processed"] is True
    assert tuple(user) == ("PRO", "active")
    assert tuple(receipt) == (1, 1, "processed")


def test_checkout_return_does_not_grant_access_while_payment_is_unpaid(tmp_path, monkeypatch):
    monkeypatch.setattr(billing, "local_safe_payments_blocked", lambda: False)
    db_path = str(tmp_path / "stripe-return.sqlite")
    _seed_membership_checkout(db_path)
    session_obj = {
        "id": "cs_1",
        "client_reference_id": "user-1",
        "payment_status": "unpaid",
        "metadata": {"user_id": "user-1", "plan": "PRO"},
        "subscription": "sub_1",
    }

    class SessionAPI:
        @staticmethod
        def retrieve(_session_id, **_kwargs):
            return session_obj

    monkeypatch.setattr(billing, "env_present", lambda _name: True)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_not_real")
    monkeypatch.setattr(billing, "stripe_sdk", lambda: SimpleNamespace(checkout=SimpleNamespace(Session=SessionAPI)))

    result = billing.sync_checkout_session(db_path, {"id": "user-1"}, "cs_1")
    conn = billing.connect(db_path)
    membership = conn.execute("SELECT membership FROM users WHERE id='user-1'").fetchone()[0]
    conn.close()
    assert result["ok"] is False and result["pending"] is True
    assert membership == "FREE"


def test_checkout_return_subscription_lookup_failure_does_not_activate_membership(tmp_path, monkeypatch):
    monkeypatch.setattr(billing, "local_safe_payments_blocked", lambda: False)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_not_real")
    db_path = str(tmp_path / "stripe-return-retry.sqlite")
    _seed_membership_checkout(db_path)

    class SessionAPI:
        @staticmethod
        def retrieve(_session_id, **_kwargs):
            return {
                "id": "cs_1",
                "client_reference_id": "user-1",
                "payment_status": "paid",
                "metadata": {"user_id": "user-1", "plan": "PRO"},
                "subscription": "sub_1",
            }

    class SubscriptionAPI:
        @staticmethod
        def retrieve(_subscription_id):
            raise TimeoutError("simulated Stripe lookup timeout")

    monkeypatch.setattr(billing, "stripe_sdk", lambda: SimpleNamespace(
        checkout=SimpleNamespace(Session=SessionAPI), Subscription=SubscriptionAPI,
    ))

    result = billing.sync_checkout_session(db_path, {"id": "user-1"}, "cs_1")
    conn = billing.connect(db_path)
    membership = conn.execute("SELECT membership FROM users WHERE id='user-1'").fetchone()[0]
    conn.close()
    assert result["ok"] is False and result["retryable"] is True
    assert membership == "FREE"


def test_async_payment_failed_is_audited_without_granting_membership(tmp_path, monkeypatch):
    monkeypatch.setattr(billing, "local_safe_payments_blocked", lambda: False)
    db_path = str(tmp_path / "stripe-async-failed.sqlite")
    _seed_membership_checkout(db_path)
    event = _checkout_event("evt_async_failed", "checkout.session.async_payment_failed", "unpaid")
    monkeypatch.setattr(billing, "parse_webhook_event", lambda _payload, _signature: event)

    result = billing.process_stripe_webhook(db_path, b"signed", "valid")
    conn = billing.connect(db_path)
    user = conn.execute("SELECT membership FROM users WHERE id='user-1'").fetchone()[0]
    checkout_status = conn.execute(
        "SELECT status FROM stripe_checkout_sessions WHERE stripe_session_id='cs_1'"
    ).fetchone()[0]
    conn.close()
    assert result["status"] == "async_payment_failed"
    assert user == "FREE"
    assert checkout_status == "async_payment_failed"


def test_stripe_route_rejects_oversized_declared_body_before_engine(client, app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "process_stripe_webhook",
        lambda *_args: (_ for _ in ()).throw(AssertionError("oversized body reached engine")),
    )
    payload = b"x" * (app_module.MAX_STRIPE_WEBHOOK_BODY_BYTES + 1)

    response = client.post("/api/payments/stripe-webhook", data=payload)

    assert response.status_code == 413
    assert response.get_json()["status"] == "payload_too_large"


def test_stripe_route_allows_exact_supported_body_size_to_reach_verifier(client, app_module, monkeypatch):
    observed = {}

    def processor(_db_path, payload, _signature):
        observed["payload_length"] = len(payload)
        return {"ok": False, "verified": False, "status": "invalid_signature"}

    monkeypatch.setattr(app_module, "process_stripe_webhook", processor)
    payload = b"x" * app_module.MAX_STRIPE_WEBHOOK_BODY_BYTES

    response = client.post("/api/payments/stripe-webhook", data=payload)

    assert response.status_code == 400
    assert response.get_json()["status"] == "invalid_signature"
    assert observed["payload_length"] == app_module.MAX_STRIPE_WEBHOOK_BODY_BYTES


def test_stripe_route_bounds_unknown_length_stream_read(client, app_module, monkeypatch):
    payload_size = app_module.MAX_STRIPE_WEBHOOK_BODY_BYTES + 4096
    observed = {}

    def processor(_db_path, payload, _signature):
        observed["payload_length"] = len(payload)
        return {"ok": True, "status": "test-accepted"}

    monkeypatch.setattr(app_module, "process_stripe_webhook", processor)
    payload = b"x" * payload_size

    response = client.post(
        "/api/payments/stripe-webhook",
        data=payload,
        environ_overrides={"CONTENT_LENGTH": "", "wsgi.input_terminated": True},
    )

    assert response.status_code == 413
    assert response.get_json()["status"] == "payload_too_large"
    assert observed == {}


def test_stripe_route_returns_retryable_status_for_verified_transient_failure(client, app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "process_stripe_webhook",
        lambda *_args: {"ok": False, "verified": True, "retryable": True, "status": "subscription_confirmation_retryable"},
    )

    response = client.post("/api/payments/stripe-webhook", data=b"signed")

    assert response.status_code == 503
    assert response.get_json()["retryable"] is True
