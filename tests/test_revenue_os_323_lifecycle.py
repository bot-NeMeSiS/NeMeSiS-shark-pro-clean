"""Revenue OS #323: synthetic lifecycle regressions, never real Stripe activity."""
import json
import sqlite3
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from engines import stripe_payments_engine as billing


def _seed(db_path, *, paid=False):
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE users(
                id TEXT PRIMARY KEY, role TEXT, membership TEXT,
                membership_source TEXT, membership_admin_granted INTEGER DEFAULT 0,
                membership_started_at TEXT, membership_expires_at TEXT,
                membership_note TEXT, membership_updated_at TEXT, membership_updated_by TEXT,
                stripe_customer_id TEXT, stripe_subscription_id TEXT,
                stripe_subscription_status TEXT, stripe_price_id TEXT,
                stripe_current_period_end TEXT, last_payment_status TEXT, last_payment_at TEXT
            )
        """)
        conn.execute(
            "INSERT INTO users(id,role,membership,membership_source,stripe_customer_id,stripe_subscription_id,"
            "stripe_subscription_status,stripe_price_id,membership_expires_at) "
            "VALUES('user-1',?,?,?,?,?,?,?,?)",
            ("PRO" if paid else "FREE", "PRO" if paid else "FREE",
             "stripe" if paid else "", "cus-1", "sub-1" if paid else None,
             "active" if paid else None, "price_pro" if paid else None,
             "2027-01-01T00:00:00+00:00" if paid else None),
        )
    billing.ensure_stripe_schema(str(db_path))
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO stripe_checkout_sessions(id,user_id,plan,stripe_session_id,"
            "expected_price_id,billing_period,status) "
            "VALUES('cs-1','user-1','PRO','cs-1','price_pro','monthly','created')"
        )
        if paid:
            conn.execute(
                "INSERT INTO stripe_subscriptions(id,user_id,plan,stripe_customer_id,"
                "stripe_subscription_id,stripe_price_id,status,current_period_end,last_event_at) "
                "VALUES('sub-1','user-1','PRO','cus-1','sub-1','price_pro',"
                "'active','2027-01-01T00:00:00+00:00','2026-10-31T00:00:00Z')"
            )


def _sub(plan="PRO", status="active", end=1800000000):
    return {
        "id": "sub-1", "customer": "cus-1", "status": status,
        "metadata": {"user_id": "user-1", "plan": plan},
        "items": {"data": [{"price": {"id": "price_elite" if plan == "ELITE" else "price_pro"},
                            "current_period_start": 1767225600, "current_period_end": end}]},
        "cancel_at_period_end": False,
    }


def _event(event_id, event_type, obj):
    return {"id": event_id, "type": event_type, "data": {"object": obj}}


def _checkout_event():
    return _event("evt_checkout", "checkout.session.completed", {
        "id": "cs-1", "object": "checkout.session", "payment_status": "paid",
        "subscription": "sub-1", "customer": "cus-1",
        "client_reference_id": "user-1",
        "metadata": {"user_id": "user-1", "plan": "PRO"},
    })


def _invoice_event(event_id="evt_paid", plan="PRO", include_lines=True):
    obj = {
        "id": "in-1", "object": "invoice", "status": "paid", "customer": "cus-1",
        "parent": {"subscription_details": {"subscription": "sub-1"}},
    }
    if include_lines:
        obj["lines"] = {"data": [
            {"pricing": {"price_details": {"price": "price_elite" if plan == "ELITE" else "price_pro"}}}
        ]}
    return _event(event_id, "invoice.paid", obj)


def _state(db_path):
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT membership,stripe_subscription_status,membership_expires_at,"
            "last_payment_status FROM users WHERE id='user-1'"
        ).fetchone()


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("STRIPE_PRICE_PRO_MONTHLY", "price_pro")
    monkeypatch.setenv("STRIPE_PRICE_ELITE_MONTHLY", "price_elite")
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_pro")
    monkeypatch.setenv("STRIPE_PRICE_ELITE", "price_elite")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake_for_mock_only")
    monkeypatch.setenv("NEMESIS_LOCAL_SAFE_MODE", "false")
    path = tmp_path / "subscriptions.sqlite"
    _seed(path, paid=False)
    return str(path)


def _stub(monkeypatch, sub):
    calls = []
    def retrieve(subscription_id):
        calls.append(subscription_id)
        return sub
    monkeypatch.setattr(billing, "stripe_sdk", lambda: SimpleNamespace(
        Subscription=SimpleNamespace(retrieve=retrieve),
    ))
    return calls


def _deliver(monkeypatch, db_path, event):
    monkeypatch.setattr(billing, "parse_webhook_event", lambda payload, sig: event)
    return billing.process_stripe_webhook(db_path, b"synthetic_signed", "not_a_real_signature")


def test_stripe_item_period_is_read_without_invented_expiry(monkeypatch):
    monkeypatch.setenv("STRIPE_PRICE_PRO_MONTHLY", "price_pro")
    fields = billing.extract_subscription_fields(_sub())
    assert fields["current_period_end"] == datetime.fromtimestamp(
        1800000000, tz=timezone.utc
    ).isoformat(timespec="seconds")
    assert fields["plan"] == "PRO"


def test_payment_link_without_owned_checkout_never_grants_access(sandbox, monkeypatch):
    calls = _stub(monkeypatch, _sub())
    event = _checkout_event()
    event["data"]["object"]["id"] = "cs_external"
    result = _deliver(monkeypatch, sandbox, event)
    assert result["status"] == "checkout_not_initiated_in_app"
    assert _state(sandbox)[0] == "FREE"
    assert calls == []


def test_unpaid_subscription_event_cannot_activate_pro(sandbox, monkeypatch):
    calls = _stub(monkeypatch, _sub())
    result = _deliver(monkeypatch, sandbox, _event("evt_sub_created",
                    "customer.subscription.created", _sub()))
    assert result["status"] == "awaiting_confirmed_payment"
    assert _state(sandbox)[0] == "FREE"
    assert calls == []
    paid = _deliver(monkeypatch, sandbox, _checkout_event())
    assert paid["processed"] is True
    assert _state(sandbox)[0] == "PRO"
    assert calls == ["sub-1"]


def test_renewal_invoice_paid_extends_only_linked_subscription(sandbox, monkeypatch):
    _stub(monkeypatch, _sub())
    _deliver(monkeypatch, sandbox, _checkout_event())
    expiry_before = _state(sandbox)[2]
    renewed = _sub(end=1850000000)
    _stub(monkeypatch, renewed)
    event = _invoice_event("evt_renewal")
    result = _deliver(monkeypatch, sandbox, event)
    assert result["status"] == "payment_reconciled"
    assert _state(sandbox)[0] == "PRO"
    assert _state(sandbox)[2] != expiry_before
    assert _state(sandbox)[3] == "paid"
    duplicate = _deliver(monkeypatch, sandbox, event)
    assert duplicate["duplicate"] is True


def test_upgrade_requires_paid_invoice_with_matching_price(sandbox, monkeypatch):
    _stub(monkeypatch, _sub())
    _deliver(monkeypatch, sandbox, _checkout_event())
    prior_expiry = _state(sandbox)[2]
    upgrade = _sub("ELITE", end=1850000000)
    _stub(monkeypatch, upgrade)
    status_event = _event("evt_upgrade", "customer.subscription.updated", upgrade)
    result = _deliver(monkeypatch, sandbox, status_event)
    assert result["status"] == "awaiting_confirmed_payment"
    assert _state(sandbox)[0] == "PRO"
    wrong = _invoice_event("evt_wrong_price", plan="PRO")
    mismatch = _deliver(monkeypatch, sandbox, wrong)
    assert mismatch["status"] == "invoice_subscription_mismatch_or_unpaid"
    assert _state(sandbox)[0] == "PRO"
    assert _state(sandbox)[2] == prior_expiry
    paid = _deliver(monkeypatch, sandbox, _invoice_event("evt_upgrade_paid", plan="ELITE"))
    assert paid["status"] == "payment_reconciled"
    assert _state(sandbox)[0] == "ELITE"


def test_cancel_at_period_end_preserves_paid_access_until_deleted(sandbox, monkeypatch):
    _stub(monkeypatch, _sub())
    _deliver(monkeypatch, sandbox, _checkout_event())
    expiry_before = _state(sandbox)[2]
    changed = _sub(end=1850000000)
    changed["cancel_at_period_end"] = True
    result = _deliver(monkeypatch, sandbox, _event(
        "evt_cancel_pending", "customer.subscription.updated", changed
    ))
    assert result["status"] == "state_recorded_waiting_for_payment"
    assert _state(sandbox)[0] == "PRO"
    assert _state(sandbox)[2] == expiry_before
    with sqlite3.connect(sandbox) as conn:
        flag = conn.execute(
            "SELECT cancel_at_period_end FROM stripe_subscriptions WHERE stripe_subscription_id='sub-1'"
        ).fetchone()[0]
    assert flag == 1
    cancelled = _sub(status="canceled")
    result = _deliver(monkeypatch, sandbox, _event(
        "evt_cancelled", "customer.subscription.deleted", cancelled
    ))
    assert result["processed"] is True
    assert _state(sandbox)[0] == "FREE"


def test_cancel_current_subscription_after_price_retirement(sandbox, monkeypatch):
    _stub(monkeypatch, _sub())
    assert _deliver(monkeypatch, sandbox, _checkout_event())["processed"] is True
    assert _state(sandbox)[0] == "PRO"
    monkeypatch.delenv("STRIPE_PRICE_PRO_MONTHLY", raising=False)
    monkeypatch.delenv("STRIPE_PRICE_PRO", raising=False)
    canceled = _sub(status="canceled")
    canceled["items"]["data"] = []
    result = _deliver(monkeypatch, sandbox, _event(
        "evt_cancel_retired_price", "customer.subscription.deleted", canceled
    ))
    assert result["status"] == "processed"
    assert _state(sandbox)[0] == "FREE"
    with sqlite3.connect(sandbox) as conn:
        status = conn.execute(
            "SELECT status FROM stripe_subscriptions WHERE stripe_subscription_id='sub-1'"
        ).fetchone()[0]
    assert status == "canceled"


def test_cancellation_from_different_subscription_or_customer_cannot_demote(sandbox, monkeypatch):
    _stub(monkeypatch, _sub())
    assert _deliver(monkeypatch, sandbox, _checkout_event())["processed"] is True
    for name, sub_id, customer_id in (
        ("other_sub", "sub-other", "cus-1"),
        ("other_customer", "sub-1", "cus-other"),
    ):
        canceled = _sub(status="canceled")
        canceled["id"] = sub_id
        canceled["customer"] = customer_id
        result = _deliver(monkeypatch, sandbox, _event(
            "evt_cancel_" + name, "customer.subscription.deleted", canceled
        ))
        assert result["status"] == "verified_not_applied"
        assert _state(sandbox)[0] == "PRO"


def test_cancelled_stripe_subscription_preserves_manual_grant(sandbox, monkeypatch):
    _stub(monkeypatch, _sub())
    _deliver(monkeypatch, sandbox, _checkout_event())
    with sqlite3.connect(sandbox) as conn:
        conn.execute(
            "UPDATE users SET membership='ELITE',role='ELITE',"
            "membership_source='admin_manual',membership_admin_granted=1 "
            "WHERE id='user-1'"
        )
    canceled = _sub(status="canceled")
    canceled["items"]["data"] = []
    result = _deliver(monkeypatch, sandbox, _event(
        "evt_cancel_with_manual", "customer.subscription.deleted", canceled
    ))
    assert result["processed"] is True
    assert result["applied"]["membership_changed"] is False
    assert _state(sandbox)[0] == "ELITE"


def test_existing_paid_user_cannot_start_a_second_checkout(tmp_path, monkeypatch):
    db_path = str(tmp_path / "paid-checkout.sqlite")
    _seed(db_path, paid=True)
    class StripeStub:
        api_key = None
        class checkout:
            class Session:
                @staticmethod
                def create(**kwargs):
                    pytest.fail("Existing subscriber must not create another Stripe Checkout session")
    monkeypatch.setattr(billing, "stripe_sdk", lambda: StripeStub)
    for key, value in {
        "STRIPE_PRICE_PRO": "price_pro",
        "STRIPE_PRICE_ELITE": "price_elite",
        "STRIPE_PRICE_PRO_MONTHLY": "price_pro",
        "STRIPE_PRICE_ELITE_MONTHLY": "price_elite",
        "APP_PUBLIC_URL": "https://example.invalid",
        "STRIPE_SECRET_KEY": "sk_test_synthetic_only",
        "STRIPE_WEBHOOK_SECRET": "whsec_synthetic_only",
        "PAYMENTS_ENABLED": "true",
        "NEMESIS_LOCAL_SAFE_MODE": "false",
    }.items():
        monkeypatch.setenv(key, value)
    result = billing.create_checkout_session(db_path, {"id": "user-1"}, "ELITE", "monthly")
    assert result["ok"] is False
    assert result["reason"] == "existing_subscription_manage_in_portal"
    assert result["manage_url"] == "/mi-cuenta"


def test_payment_failed_records_issue_without_early_cancellation(sandbox, monkeypatch):
    _stub(monkeypatch, _sub())
    _deliver(monkeypatch, sandbox, _checkout_event())
    expiry_before = _state(sandbox)[2]
    event = _event("evt_payment_failed", "invoice.payment_failed", {
        "id": "in_failed", "object": "invoice", "subscription": "sub-1",
        "customer": "cus-1",
    })
    result = _deliver(monkeypatch, sandbox, event)
    assert result["status"] == "payment_issue_recorded"
    assert _state(sandbox)[0] == "PRO"
    assert _state(sandbox)[2] == expiry_before
    assert _state(sandbox)[3] == "payment_failed"
