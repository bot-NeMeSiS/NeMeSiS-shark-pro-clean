"""Route contract tests; Stripe and external I/O are mocked."""
from __future__ import annotations

import pytest


def test_elite_plus_is_a_separate_client_role(app_module):
    assert "ELITE+" in app_module.VALID_ROLES
    assert app_module.normalize_role("ELITE+") == "ELITE+"
    assert app_module._selected_paid_plan("ELITE+") == "ELITE+"
    assert "plan=ELITE%2B" in app_module._membership_next_for_plan("ELITE+")


def test_api_checkout_forwards_authenticated_plan_and_billing_period(app_module, monkeypatch):
    captured = {}
    monkeypatch.setattr(app_module, "current_session_user", lambda: {"id": "qa-only"})
    monkeypatch.setattr(app_module, "enforce_checkout_legal_gate", lambda user, plan: (True, None))

    def fake_checkout(db_path, user, plan, billing_period="monthly"):
        captured.update(user=user["id"], plan=plan, period=billing_period)
        return {"ok": False, "error": "Simulated; no charge"}

    monkeypatch.setattr(app_module, "create_checkout_session", fake_checkout)
    with app_module.app.test_request_context(
        "/api/payments/checkout", method="POST",
        json={"plan": "ELITE+", "billing_period": "yearly"}
    ):
        response, status = app_module.api_payments_checkout()
    assert status == 400
    assert captured == {"user": "qa-only", "plan": "ELITE+", "period": "yearly"}
    assert response.get_json()["ok"] is False


def test_web_checkout_forwards_yearly_and_never_contacts_stripe(app_module, monkeypatch):
    captured = {}
    monkeypatch.setattr(app_module, "current_session_user", lambda: {"id": "qa-only"})
    monkeypatch.setattr(app_module, "enforce_checkout_legal_gate", lambda user, plan: (True, None))

    def fake_checkout(db_path, user, plan, billing_period="monthly"):
        captured.update(user=user["id"], plan=plan, period=billing_period)
        return {"ok": True, "url": "https://example.invalid/never-opened"}

    monkeypatch.setattr(app_module, "create_checkout_session", fake_checkout)
    with app_module.app.test_request_context(
        "/pagos/checkout/ELITE+", method="POST",
        data={"billing_period": "yearly"}
    ):
        response = app_module.payments_checkout_plan("ELITE+")
    assert response.status_code == 302
    assert captured == {"user": "qa-only", "plan": "ELITE+", "period": "yearly"}
    assert response.location == "https://example.invalid/never-opened"
