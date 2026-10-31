"""Offline regression tests for Revenue OS #323 helper and checkout inputs.

Run: python -m unittest tests.test_revenue_os_323_checkout
No real Stripe keys, network calls, customers or charges.
"""
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from engines.stripe_payments_engine import (
    revenue_os_normalize_plan,
    revenue_os_price_id,
    resolve_plan_from_price,
    revenue_os_price_matches_plan,
    revenue_os_checkout_idempotency_key,
    VALID_PAID_PLANS,
    REVENUE_OS_BILLING_PERIODS,
)


class RevenueOSCheckoutTests(unittest.TestCase):
    def test_elite_plus_is_distinct_and_not_live_yet(self):
        self.assertEqual(revenue_os_normalize_plan("elite_plus"), "ELITE+")
        self.assertEqual(revenue_os_normalize_plan("ELITE+"), "ELITE+")
        self.assertNotIn("ELITE+", VALID_PAID_PLANS)

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
