from __future__ import annotations

import json
import sqlite3

import pytest

from engines import stripe_payments_engine as billing


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
