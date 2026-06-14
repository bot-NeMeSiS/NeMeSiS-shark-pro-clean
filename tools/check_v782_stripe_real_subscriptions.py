#!/usr/bin/env python3
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="ignore")


def check_files() -> None:
    if not VERSION.startswith(("V782_STRIPE_REAL_SUBSCRIPTIONS_MEMBERSHIP_BILLING","V783_HOME_MEMBERSHIP_CLIENT_EXPERIENCE_COMPACT_FINAL")):
        fail(f"VERSION inesperada: {VERSION}")
    app = read("app.py")
    required = [
        "create_checkout_session",
        "create_customer_portal_session",
        "process_stripe_webhook",
        '@app.route("/api/payments/checkout", methods=["POST"])',
        '@app.route("/pagos/checkout/<plan>", methods=["POST"])',
        '@app.route("/api/payments/stripe-webhook", methods=["POST"])',
        '@app.route("/pagos/exito")',
        '@app.route("/pagos/cancelado")',
        "stripe_runtime_status(DB_PATH)",
    ]
    for token in required:
        if token not in app:
            fail(f"falta token app.py: {token}")
    engine = ROOT / "engines" / "stripe_payments_engine.py"
    if not engine.exists():
        fail("falta engines/stripe_payments_engine.py")
    engine_text = engine.read_text(encoding="utf-8")
    for token in ["stripe.checkout.Session.create", "stripe.Webhook.construct_event", "customer.subscription.deleted", "membership_source='stripe'", "stripe_subscriptions"]:
        if token not in engine_text:
            fail(f"falta token engine: {token}")
    req = read("requirements.txt")
    if "stripe" not in req.lower():
        fail("requirements.txt no incluye stripe")
    membership = read("templates/membership.html")
    for token in ["/pagos/checkout/PRO", "/pagos/checkout/ELITE", "csrf_token()", "Gestionar facturación en Stripe"]:
        if token not in membership:
            fail(f"membership sin {token}")
    account = read("templates/account_center.html")
    if "/pagos/portal" not in account or "Pagos y membresía" not in account:
        fail("mi cuenta no muestra gestión Stripe")
    admin = read("templates/admin_payments.html")
    for token in ["Stripe Checkout", "Webhook verificado", "Suscripciones Stripe recientes"]:
        if token not in admin:
            fail(f"admin payments sin {token}")
    env = read(".env.example") + read(".env.render.clean")
    for token in ["PAYMENTS_ENABLED", "PAYMENTS_MODE=stripe_real", "STRIPE_WEBHOOK_SECRET", "STRIPE_CUSTOMER_PORTAL_ENABLED", "APP_PUBLIC_URL"]:
        if token not in env:
            fail(f"env sin {token}")


def check_engine_schema_and_membership() -> None:
    import sys
    sys.path.insert(0, str(ROOT))
    from engines.stripe_payments_engine import ensure_stripe_schema, apply_subscription_to_user, stripe_runtime_status

    with tempfile.TemporaryDirectory() as td:
        db_path = str(Path(td) / "test.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("""CREATE TABLE users(
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            role TEXT DEFAULT 'FREE',
            membership TEXT DEFAULT 'FREE',
            membership_source TEXT,
            membership_started_at TEXT,
            membership_expires_at TEXT,
            membership_note TEXT,
            membership_updated_at TEXT,
            membership_updated_by TEXT,
            membership_admin_granted INTEGER DEFAULT 0
        )""")
        conn.execute("INSERT INTO users(id,name,email,role,membership) VALUES('u1','Test','test@example.com','FREE','FREE')")
        conn.commit(); conn.close()
        ensure_stripe_schema(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        fields = {
            "user_id": "u1",
            "plan": "PRO",
            "customer_id": "cus_test",
            "subscription_id": "sub_test",
            "status": "active",
            "price_id": "price_pro",
            "current_period_start": "2026-06-01T00:00:00+00:00",
            "current_period_end": "2026-07-01T00:00:00+00:00",
            "cancel_at_period_end": 0,
        }
        applied = apply_subscription_to_user(conn, fields, "customer.subscription.updated", {})
        conn.commit()
        user = dict(conn.execute("SELECT * FROM users WHERE id='u1'").fetchone())
        if not applied.get("applied") or user.get("membership") != "PRO" or user.get("membership_source") != "stripe":
            fail("la suscripción active no aplica PRO")
        fields["status"] = "canceled"
        applied = apply_subscription_to_user(conn, fields, "customer.subscription.deleted", {})
        conn.commit()
        user = dict(conn.execute("SELECT * FROM users WHERE id='u1'").fetchone())
        if not applied.get("applied") or user.get("membership") != "FREE":
            fail("la cancelación no devuelve a FREE")
        conn.close()
        status = stripe_runtime_status(db_path)
        if "plans" not in status or "PRO" not in status["plans"]:
            fail("stripe_runtime_status sin catálogo")


def main() -> None:
    check_files()
    check_engine_schema_and_membership()
    print("OK V782/V783 Stripe real subscriptions/membership billing compatibility")


if __name__ == "__main__":
    main()
