"""Offline regression tests for Revenue OS #323 helper and checkout inputs.

Run: python -m unittest tests.test_revenue_os_323_checkout
No real Stripe keys, network calls, customers or charges.
"""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

from engines.stripe_payments_engine import (
    revenue_os_normalize_plan,
    revenue_os_price_id,
    resolve_plan_from_price,
    revenue_os_price_matches_plan,
    revenue_os_price_matches_period,
    extract_subscription_fields,
    apply_subscription_to_user,
    plan_catalog,
    create_checkout_session,
    revenue_os_checkout_idempotency_key,
    VALID_PAID_PLANS,
    REVENUE_OS_BILLING_PERIODS,
)


class RevenueOSCheckoutTests(unittest.TestCase):
    def test_elite_plus_is_distinct_and_not_live_yet(self):
        self.assertEqual(revenue_os_normalize_plan("elite_plus"), "ELITE+")
        self.assertEqual(revenue_os_normalize_plan("ELITE+"), "ELITE+")
        self.assertIn("ELITE+", VALID_PAID_PLANS)
        with patch.dict(os.environ, {"REVENUE_OS_SIX_PLANS_ENABLED": "false",
                                    "STRIPE_PRICE_ELITE_PLUS_MONTHLY": "price_plus"}, clear=False):
            self.assertFalse(plan_catalog()["ELITE+"]["available_for_checkout"])
        with patch.dict(os.environ, {"REVENUE_OS_SIX_PLANS_ENABLED": "true",
                                    "STRIPE_PRICE_ELITE_PLUS_MONTHLY": "price_plus"}, clear=False):
            self.assertTrue(plan_catalog()["ELITE+"]["available_for_checkout"])

    def test_unknown_period_or_plan_never_maps_to_a_price(self):
        with patch.dict(os.environ, {"STRIPE_PRICE_PRO_MONTHLY": "price_month"}, clear=False):
            self.assertEqual(revenue_os_price_id("PRO", "weekly"), "")
            self.assertEqual(revenue_os_price_id("FREE", "monthly"), "")
            self.assertEqual(revenue_os_price_id("UNKNOWN", "monthly"), "")
            self.assertEqual(revenue_os_price_id("PRO", "monthly"), "price_month")

    def test_all_six_price_keys_are_independent(self):
        pairs = {"STRIPE_PRICE_PRO_MONTHLY": "p1", "STRIPE_PRICE_PRO_YEARLY": "p2",
                 "STRIPE_PRICE_ELITE_MONTHLY": "p3", "STRIPE_PRICE_ELITE_YEARLY": "p4",
                 "STRIPE_PRICE_ELITE_PLUS_MONTHLY": "p5", "STRIPE_PRICE_ELITE_PLUS_YEARLY": "p6"}
        with patch.dict(os.environ, pairs, clear=False):
            self.assertEqual([revenue_os_price_id(p, t) for p in ("PRO", "ELITE", "ELITE+")
                              for t in REVENUE_OS_BILLING_PERIODS], list(pairs.values()))

    def test_entitlement_rejects_mismatched_or_unknown_price(self):
        prices = {"STRIPE_PRICE_PRO_MONTHLY": "price_pro_month",
                  "STRIPE_PRICE_ELITE_YEARLY": "price_elite_year",
                  "STRIPE_PRICE_ELITE_PLUS_MONTHLY": "price_plus_month"}
        with patch.dict(os.environ, prices, clear=False):
            self.assertEqual(resolve_plan_from_price("price_plus_month"), "ELITE+")
            self.assertTrue(revenue_os_price_matches_plan("price_pro_month", "PRO"))
            self.assertFalse(revenue_os_price_matches_plan("price_pro_month", "ELITE"))
            self.assertFalse(revenue_os_price_matches_plan("price_unknown", "PRO"))
            self.assertFalse(revenue_os_price_matches_plan("", "PRO"))

    def test_forged_plan_metadata_cannot_upgrade_price(self):
        with patch.dict(os.environ, {"STRIPE_PRICE_PRO_MONTHLY": "price_pro_good"}, clear=False):
            subscription = {
                "id": "sub_fake", "customer": "cus_fake", "status": "active",
                "metadata": {"plan": "ELITE+", "user_id": "u_fake"},
                "items": {"data": [{"price": {"id": "price_pro_good"}}]},
            }
            fields = extract_subscription_fields(subscription)
            self.assertEqual(fields["plan"], "PRO")
            self.assertEqual(fields["price_id"], "price_pro_good")
            fields["plan"] = "ELITE+"
            with sqlite3.connect(":memory:") as conn:
                result = apply_subscription_to_user(conn, fields, "test")
            self.assertFalse(result["applied"])
            self.assertEqual(result["reason"], "price_plan_unverified")

    def test_unknown_price_does_not_grant_access(self):
        with patch.dict(os.environ, {"STRIPE_PRICE_PRO_MONTHLY": "price_verified_pro"}, clear=False):
            fields = {
                "user_id": "u_fake", "subscription_id": "sub_fake",
                "customer_id": "cus_fake", "status": "active",
                "plan": "PRO", "price_id": "price_not_configured",
            }
            with sqlite3.connect(":memory:") as conn:
                result = apply_subscription_to_user(conn, fields, "test")
            self.assertFalse(result["applied"])
            self.assertEqual(result["reason"], "price_plan_unverified")

    def test_public_catalog_does_not_enable_unintegrated_elite_plus(self):
        with patch.dict(os.environ, {
            "STRIPE_PRICE_PRO": "price_pro_legacy",
            "STRIPE_PRICE_ELITE": "price_elite_legacy",
            "STRIPE_PRICE_ELITE_PLUS_MONTHLY": "price_plus_month",
            "STRIPE_PRICE_PRO_YEARLY": "price_pro_year",
            "REVENUE_OS_SIX_PLANS_ENABLED": "false",
        }, clear=False):
            catalog = plan_catalog()
            self.assertEqual(set(catalog), {"FREE", "PRO", "ELITE", "ELITE+"})
            self.assertEqual(catalog["ELITE+"]["price_label"], "44,99 €/mes")
            self.assertFalse(catalog["ELITE+"]["available_for_checkout"])
            self.assertEqual(catalog["PRO"]["yearly_price_label"], "149 €/año")
            self.assertTrue(catalog["PRO"]["available_for_checkout"])

    def test_missing_billing_period_does_not_fabricate_entitlement(self):
        with patch.dict(os.environ, {"STRIPE_PRICE_PRO_MONTHLY": "price_verified"}, clear=False):
            fields = {"user_id": "u1", "subscription_id": "sub1",
                      "customer_id": "cus1", "status": "active",
                      "plan": "PRO", "price_id": "price_verified",
                      "current_period_end": ""}
            with sqlite3.connect(":memory:") as conn:
                result = apply_subscription_to_user(conn, fields, "test")
            self.assertFalse(result["applied"])
            self.assertEqual(result["reason"], "subscription_period_unverified")

    def test_same_price_assigned_to_two_tiers_must_not_grant_either(self):
        with patch.dict(os.environ, {
            "STRIPE_PRICE_PRO_MONTHLY": "price_collision",
            "STRIPE_PRICE_ELITE_MONTHLY": "price_collision",
            "STRIPE_PRICE_PRO": "",
            "STRIPE_PRICE_ELITE": "",
        }, clear=False):
            self.assertEqual(resolve_plan_from_price("price_collision"), "")
            self.assertFalse(revenue_os_price_matches_plan("price_collision", "PRO"))
            self.assertFalse(revenue_os_price_matches_plan("price_collision", "ELITE"))

    def test_six_plan_checkout_requires_explicit_rollout_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "checkout.sqlite")
            with patch.dict(os.environ, {"NEMESIS_LOCAL_SAFE_MODE": "false",
                                        "REVENUE_OS_SIX_PLANS_ENABLED": "false",
                                        "STRIPE_PRICE_ELITE_PLUS_MONTHLY": "price_plus"}, clear=False):
                result = create_checkout_session(db_path, {"id": "qa-user"}, "ELITE+", "monthly")
                self.assertFalse(result["ok"])
                self.assertIn("aún no", result["error"])
                yearly = create_checkout_session(db_path, {"id": "qa-user"}, "PRO", "yearly")
                self.assertFalse(yearly["ok"])
                self.assertIn("pendiente", yearly["error"])

    def test_six_plan_checkout_uses_exact_annual_price_and_owner(self):
        import engines.stripe_payments_engine as billing

        class StripeStub:
            api_key = None
            class checkout:
                class Session:
                    @staticmethod
                    def create(**kwargs):
                        StripeStub.seen = kwargs
                        return {"id": "cs_qa_yearly", "url": "https://example.invalid/pay"}

        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "checkout.sqlite")
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY, email TEXT)")
                conn.execute("INSERT INTO users(id,email) VALUES('user_qa','user@example.invalid')")
            variables = {
                "NEMESIS_LOCAL_SAFE_MODE": "false",
                "REVENUE_OS_SIX_PLANS_ENABLED": "true",
                "PAYMENTS_ENABLED": "true",
                "APP_PUBLIC_URL": "https://example.invalid",
                "STRIPE_SECRET_KEY": "sk_test_synthetic_only",
                "STRIPE_WEBHOOK_SECRET": "whsec_synthetic_only",
                "STRIPE_PRICE_PRO": "price_pro_month",
                "STRIPE_PRICE_ELITE": "price_elite_month",
                "STRIPE_PRICE_PRO_MONTHLY": "price_pro_month",
                "STRIPE_PRICE_PRO_YEARLY": "price_pro_year",
            }
            with patch.dict(os.environ, variables, clear=False), patch.object(billing, "stripe_sdk", return_value=StripeStub):
                result = create_checkout_session(db_path, {"id": "user_qa"}, "PRO", "yearly")
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["billing_period"], "yearly")
            self.assertEqual(StripeStub.seen["line_items"], [{"price": "price_pro_year", "quantity": 1}])
            self.assertEqual(StripeStub.seen["client_reference_id"], "user_qa")
            self.assertEqual(StripeStub.seen["subscription_data"]["metadata"]["billing_period"], "yearly")
            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT user_id,plan,billing_period,expected_price_id FROM stripe_checkout_sessions "
                    "WHERE stripe_session_id='cs_qa_yearly'"
                ).fetchone()
            self.assertEqual(row, ("user_qa", "PRO", "yearly", "price_pro_year"))

    def test_same_stripe_price_cannot_be_both_monthly_and_yearly(self):
        with patch.dict(os.environ, {
            "STRIPE_PRICE_PRO": "",
            "STRIPE_PRICE_PRO_MONTHLY": "price_wrong_reused",
            "STRIPE_PRICE_PRO_YEARLY": "price_wrong_reused",
            "REVENUE_OS_SIX_PLANS_ENABLED": "true",
        }, clear=False):
            self.assertEqual(resolve_plan_from_price("price_wrong_reused"), "PRO")
            self.assertFalse(revenue_os_price_matches_period("price_wrong_reused", "PRO", "monthly"))
            self.assertFalse(revenue_os_price_matches_period("price_wrong_reused", "PRO", "yearly"))
            catalog = plan_catalog()
            self.assertFalse(catalog["PRO"]["available_for_checkout"])
            self.assertFalse(catalog["PRO"]["yearly_available_for_checkout"])

    def test_annual_subscription_mrr_is_monthly_equivalent(self):
        import engines.stripe_payments_engine as billing
        import engines.subscription_control_engine as revenue
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "mrr.sqlite")
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY, role TEXT, membership TEXT, "
                             "membership_source TEXT, membership_admin_granted INTEGER DEFAULT 0)")
                conn.execute("INSERT INTO users(id,role,membership,membership_source) "
                             "VALUES('paid-qa','PRO','PRO','stripe')")
            billing.ensure_stripe_schema(db_path)
            with sqlite3.connect(db_path) as conn:
                conn.execute("INSERT INTO stripe_subscriptions "
                             "(id,user_id,plan,stripe_price_id,status,current_period_end,last_event_at) "
                             "VALUES('sub-qa','paid-qa','PRO','price_pro_year','active',"
                             "'2030-01-01T00:00:00+00:00','2026-10-31T00:00:00Z')")
            with patch.dict(os.environ, {
                "STRIPE_PRICE_PRO_YEARLY": "price_pro_year",
                "STRIPE_PRICE_PRO_LABEL": "14,99 €/mes",
            }, clear=False):
                summary = revenue.subscription_summary(db_path, apply_rules=False, persist_metrics=False)
            self.assertEqual(summary["active_paid"], 1)
            self.assertEqual(summary["paid_by_tier"]["PRO"], 1)
            self.assertAlmostEqual(summary["estimated_mrr"], round(149 / 12, 2), places=2)
            self.assertFalse(summary["estimated_mrr_verified_by_provider"])

    def test_ambiguous_subscription_items_cannot_grant_any_plan(self):
        with patch.dict(os.environ, {"STRIPE_PRICE_PRO_MONTHLY": "price_pro",
                                    "STRIPE_PRICE_ELITE_MONTHLY": "price_elite"}, clear=False):
            subscription = {
                "id": "sub_multi", "customer": "cus_qa", "status": "active",
                "items": {"data": [
                    {"price": {"id": "price_pro"}, "current_period_end": 1800000000},
                    {"price": {"id": "price_elite"}, "current_period_end": 1800000000},
                ]},
            }
            fields = extract_subscription_fields(subscription)
            self.assertEqual(fields["plan"], "")
            self.assertEqual(fields["price_id"], "")
            self.assertFalse(revenue_os_price_matches_plan(fields["price_id"], "PRO"))

    def test_expired_subscription_period_cannot_grant_paid_access(self):
        with patch.dict(os.environ, {"STRIPE_PRICE_PRO_MONTHLY": "price_pro"}, clear=False):
            fields = {"user_id": "qa-user", "subscription_id": "sub_old",
                      "customer_id": "cus_old", "status": "active",
                      "plan": "PRO", "price_id": "price_pro",
                      "current_period_end": "2020-01-01T00:00:00+00:00"}
            with sqlite3.connect(":memory:") as conn:
                result = apply_subscription_to_user(conn, fields, "test")
            self.assertFalse(result["applied"])
            self.assertEqual(result["reason"], "subscription_period_expired")

    def test_past_due_cannot_upgrade_access_or_extend_period(self):
        import engines.stripe_payments_engine as billing
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            db_path = str(Path(folder) / "past-due.sqlite")
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "CREATE TABLE users(id TEXT PRIMARY KEY,role TEXT,membership TEXT,"
                    "membership_source TEXT,stripe_subscription_id TEXT,stripe_customer_id TEXT,"
                    "membership_expires_at TEXT,stripe_subscription_status TEXT,last_payment_status TEXT)"
                )
                conn.execute(
                    "INSERT INTO users(id,role,membership,membership_source,stripe_subscription_id,"
                    "stripe_customer_id,membership_expires_at) VALUES("
                    "'qa','PRO','PRO','stripe','sub_qa','cus_qa','2027-01-01T00:00:00+00:00')"
                )
            billing.ensure_stripe_schema(db_path)
            with patch.dict(os.environ, {"STRIPE_PRICE_ELITE_MONTHLY": "price_elite_qa"}, clear=False):
                with billing.connect(db_path) as conn:
                    result = billing.apply_subscription_to_user(conn, {
                        "user_id": "qa", "subscription_id": "sub_qa",
                        "customer_id": "cus_qa", "status": "past_due",
                        "plan": "ELITE", "price_id": "price_elite_qa",
                        "current_period_end": "2028-01-01T00:00:00+00:00",
                    }, "customer.subscription.updated")
                    conn.commit()
                    user = conn.execute(
                        "SELECT membership,membership_expires_at,stripe_subscription_status "
                        "FROM users WHERE id='qa'"
                    ).fetchone()
                self.assertFalse(result["applied"])
                self.assertEqual(result["reason"], "past_due_existing_access_preserved")
                self.assertEqual(tuple(user), ("PRO", "2027-01-01T00:00:00+00:00", "past_due"))

    def test_idempotency_changes_with_period_price_and_user(self):
        now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
        f = lambda user, period, price: revenue_os_checkout_idempotency_key(user, "PRO", period, price, now)
        self.assertEqual(f("u1", "monthly", "price_a"), f("u1", "monthly", "price_a"))
        self.assertNotEqual(f("u1", "monthly", "price_a"), f("u1", "yearly", "price_b"))
        self.assertNotEqual(f("u1", "monthly", "price_a"), f("u1", "monthly", "price_c"))
        self.assertNotEqual(f("u1", "monthly", "price_a"), f("u2", "monthly", "price_a"))
        self.assertEqual(f("u1", "invalid", "price_a"), "")
        self.assertEqual(f("u1", "monthly", ""), "")


if __name__ == "__main__":
    unittest.main()
