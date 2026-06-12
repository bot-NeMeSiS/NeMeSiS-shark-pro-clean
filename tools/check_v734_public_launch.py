#!/usr/bin/env python3
"""Validate V734 public launch, payments and track-record foundation."""
from __future__ import annotations

import json
import os
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.payment_readiness_engine import payment_readiness_snapshot, record_payment_webhook_event
from engines.pick_grading_engine import pick_grading_summary, run_pick_grading
from engines.public_launch_engine import public_launch_snapshot
from engines.subscription_control_engine import subscription_summary


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "v734_check.db")
        payments = payment_readiness_snapshot(db_path)
        webhook = record_payment_webhook_event(db_path, "stripe", {"id": "evt_v734_check", "type": "checkout.session.completed", "data": {"object": {"metadata": {"user_id": "u-test", "plan": "PRO"}, "amount_total": 1999, "currency": "eur"}}}, signature_present=False)
        grading_run = run_pick_grading(db_path, limit=25, apply=False)
        grading = pick_grading_summary(db_path)
        subs = subscription_summary(db_path, apply_rules=True)
        launch = public_launch_snapshot(db_path, app_version="V734_CHECK")
        required_files = [
            "templates/admin_public_launch.html",
            "templates/admin_track_record.html",
            "templates/track_record.html",
            "templates/admin_payments.html",
            "engines/public_launch_engine.py",
            "engines/payment_readiness_engine.py",
        ]
        missing = [p for p in required_files if not (ROOT / p).exists()]
        ok = payments.get("ok") and webhook.get("ok") and grading_run.get("ok") and grading.get("schema") and subs.get("ok") and launch.get("ok") and not missing
        result = {
            "ok": bool(ok),
            "payments_score": payments.get("readiness_score"),
            "webhook_status": webhook.get("status"),
            "grading_checked": grading_run.get("picks_checked"),
            "track_record_schema": grading.get("schema"),
            "subscriptions_status": subs.get("status"),
            "launch_score": launch.get("global_score"),
            "missing": missing,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
