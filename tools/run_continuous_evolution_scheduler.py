"""Safe external runner for the Continuous Evolution OS.

This entrypoint is intentionally narrow: it only invokes the existing
Continuous Evolution scheduler. It never sends Telegram messages, calls Stripe,
deploys, pushes, mutates users, changes memberships, changes prices, or enables
external market research.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import APP_VERSION  # noqa: E402
from engines.product_review_system_engine import run_safe_continuous_evolution_runner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the safe Continuous Evolution OS scheduler task.")
    parser.add_argument("--task", default="daily_product_review", choices=["daily_product_review", "daily_founder_brief", "weekly_executive_review", "monthly_strategy_review"])
    parser.add_argument("--dry-run", action="store_true", help="Preview due state without writing runtime files.")
    parser.add_argument("--force", action="store_true", help="Force a local execution. Do not use for production cadence unless explicitly approved.")
    parser.add_argument("--trigger", default="SCHEDULED_LOCAL", choices=["MANUAL", "SCHEDULED_LOCAL", "SCHEDULED_PRODUCTION"])
    parser.add_argument("--storage-root", default="", help="Optional test storage root. Production should omit this.")
    parser.add_argument("--now", default="", help="Optional ISO datetime for controlled tests.")
    args = parser.parse_args()
    result = run_safe_continuous_evolution_runner(
        ROOT,
        APP_VERSION,
        task_name=args.task,
        dry_run=args.dry_run,
        trigger=args.trigger,
        now=args.now or None,
        storage_root=args.storage_root or None,
        force=args.force,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if result.get("ok") is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
