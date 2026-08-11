"""Safe external runner for the Continuous Evolution OS.

This entrypoint is intentionally narrow: it only invokes the existing
Continuous Evolution scheduler. It never sends Telegram messages, calls Stripe,
deploys, pushes, mutates users, changes memberships, changes prices, or enables
external market research.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import APP_VERSION  # noqa: E402
from engines.product_review_system_engine import run_safe_continuous_evolution_runner  # noqa: E402

PROHIBITED_ACTIONS = {
    "MODIFY_APP_CODE": False,
    "COMMIT": False,
    "PUSH": False,
    "DEPLOY": False,
    "SEND_TELEGRAM": False,
    "CALL_STRIPE": False,
    "CHANGE_USERS": False,
    "CHANGE_MEMBERSHIPS": False,
    "CHANGE_PRICES": False,
    "DELETE_DATA": False,
    "CHANGE_SECRETS": False,
    "ACTIVATE_EXTERNAL_SOURCES": False,
    "RUN_MARKET_CRAWLING": False,
}


def _json_exit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if payload.get("ok") is not False else 1


def _safe_mode_enabled() -> bool:
    return os.getenv("CONTINUOUS_EVOLUTION_SAFE_MODE") == "1"


def _resolve_storage_root(explicit: str, trigger: str) -> str:
    if explicit:
        return explicit
    configured = os.getenv("CONTINUOUS_EVOLUTION_STORAGE_ROOT", "").strip()
    if configured:
        return configured
    if trigger == "SCHEDULED_PRODUCTION":
        db_path = os.getenv("DB_PATH", "").strip()
        if db_path:
            parent = Path(db_path).expanduser().parent
            if parent.is_absolute():
                return str(parent / "continuous_evolution_os")
    return ""


def _storage_is_repo_runtime(storage_root: str) -> bool:
    if not storage_root:
        return False
    resolved = Path(storage_root).expanduser().resolve()
    repo_runtime = (ROOT / "data" / "runtime").resolve()
    return resolved == repo_runtime or repo_runtime in resolved.parents


def _compact_result(result: dict, *, verbose: bool) -> dict:
    if verbose:
        return result
    payload = {
        "ok": result.get("ok"),
        "result": result.get("result") or ("DRY_RUN" if result.get("dry_run") else None),
        "task_name": result.get("task_name") or ((result.get("preview") or {}).get("task_name")),
        "runner_contract": result.get("runner_contract"),
        "safe_mode": result.get("safe_mode"),
        "storage_root": result.get("storage_root"),
        "guardrails": result.get("guardrails"),
        "prohibited_actions": result.get("prohibited_actions"),
        "dangerous_actions_executed": result.get("dangerous_actions_executed", False),
    }
    if result.get("dry_run"):
        payload["dry_run"] = True
        payload["preview"] = result.get("preview")
    job = result.get("job") or {}
    if job:
        payload["job"] = {
            "job_id": job.get("job_id"),
            "trigger": job.get("trigger"),
            "scheduled_for": job.get("scheduled_for"),
            "scheduled_for_utc": job.get("scheduled_for_utc"),
            "started_at": job.get("started_at"),
            "started_at_utc": job.get("started_at_utc"),
            "finished_at": job.get("finished_at"),
            "finished_at_utc": job.get("finished_at_utc"),
            "duration_ms": job.get("duration_ms"),
            "status": job.get("status"),
            "run_id": job.get("run_id"),
            "snapshot_id": job.get("snapshot_id"),
            "founder_brief_id": job.get("founder_brief_id"),
            "codex_ready_count": job.get("codex_ready_count"),
            "error_safe": job.get("error_safe"),
            "next_expected_run": job.get("next_expected_run"),
            "next_expected_run_utc": job.get("next_expected_run_utc"),
            "dangerous_actions_executed": job.get("dangerous_actions_executed", False),
        }
    cycle = result.get("cycle") or {}
    snapshot = cycle.get("snapshot") or {}
    memory = cycle.get("memory") or {}
    if snapshot:
        payload["cycle_summary"] = {
            "run_id": snapshot.get("run_id"),
            "snapshot_id": snapshot.get("snapshot_id"),
            "result": snapshot.get("result"),
            "systems_consulted": snapshot.get("systems_consulted") or [],
            "systems_unavailable": snapshot.get("systems_unavailable") or [],
            "memory_items": len((memory.get("recommendations") or {})),
            "comparison": (snapshot.get("temporal_comparison") or {}).get("summary"),
            "founder_brief_id": ((snapshot.get("founder_brief") or {}).get("brief_id")),
            "codex_ready_count": ((snapshot.get("prepared_for_codex") or {}).get("ready_count")),
            "telegram_sent": snapshot.get("telegram_sent", False),
            "stripe_called": snapshot.get("stripe_called", False),
            "production_modified": snapshot.get("production_modified", False),
        }
    scheduler = result.get("scheduler") or {}
    tasks = scheduler.get("tasks") or {}
    if tasks:
        payload["scheduler_summary"] = {
            key: {
                "last_result": value.get("last_result"),
                "run_count": value.get("run_count"),
                "failed_count": value.get("failed_count"),
                "last_run": value.get("last_run"),
                "next_expected_run": value.get("next_expected_run"),
            }
            for key, value in tasks.items()
        }
    if result.get("error_safe"):
        payload["error_safe"] = result.get("error_safe")
    return payload

def _production_preflight(args: argparse.Namespace, storage_root: str) -> dict | None:
    if args.trigger != "SCHEDULED_PRODUCTION":
        return None
    if not _safe_mode_enabled():
        return {
            "ok": False,
            "result": "SAFE_MODE_REQUIRED",
            "message": "Set CONTINUOUS_EVOLUTION_SAFE_MODE=1 before any SCHEDULED_PRODUCTION run.",
            "safe_mode": False,
            "dangerous_actions_executed": False,
            "prohibited_actions": PROHIBITED_ACTIONS,
        }
    if args.force:
        return {
            "ok": False,
            "result": "FORCE_NOT_ALLOWED_IN_PRODUCTION",
            "message": "SCHEDULED_PRODUCTION must rely on due/not-due idempotency, not --force.",
            "safe_mode": True,
            "dangerous_actions_executed": False,
            "prohibited_actions": PROHIBITED_ACTIONS,
        }
    if not storage_root:
        return {
            "ok": False,
            "result": "PERSISTENT_STORAGE_REQUIRED",
            "message": "Set CONTINUOUS_EVOLUTION_STORAGE_ROOT or DB_PATH on a persistent disk.",
            "safe_mode": True,
            "dangerous_actions_executed": False,
            "prohibited_actions": PROHIBITED_ACTIONS,
        }
    if _storage_is_repo_runtime(storage_root):
        return {
            "ok": False,
            "result": "EPHEMERAL_STORAGE_BLOCKED",
            "message": "Production scheduled runs must not use repo data/runtime storage.",
            "storage_root": str(Path(storage_root).expanduser().resolve()),
            "safe_mode": True,
            "dangerous_actions_executed": False,
            "prohibited_actions": PROHIBITED_ACTIONS,
        }
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the safe Continuous Evolution OS scheduler task.")
    parser.add_argument("--task", default="daily_product_review", choices=["daily_product_review", "daily_founder_brief", "weekly_executive_review", "monthly_strategy_review"])
    parser.add_argument("--dry-run", action="store_true", help="Preview due state without writing runtime files.")
    parser.add_argument("--force", action="store_true", help="Force a local execution. Blocked for SCHEDULED_PRODUCTION.")
    parser.add_argument("--trigger", default="SCHEDULED_LOCAL", choices=["MANUAL", "SCHEDULED_LOCAL", "SCHEDULED_PRODUCTION"])
    parser.add_argument("--storage-root", default="", help="Optional storage root. Production must use persistent storage.")
    parser.add_argument("--now", default="", help="Optional ISO datetime for controlled tests.")
    parser.add_argument("--verbose", action="store_true", help="Print full diagnostic payload. Default output is compact and sanitized.")
    args = parser.parse_args()

    storage_root = _resolve_storage_root(args.storage_root, args.trigger)
    blocked = _production_preflight(args, storage_root)
    if blocked:
        return _json_exit(blocked)

    result = run_safe_continuous_evolution_runner(
        ROOT,
        APP_VERSION,
        task_name=args.task,
        dry_run=args.dry_run,
        trigger=args.trigger,
        now=args.now or None,
        storage_root=storage_root or None,
        force=args.force,
    )
    result["safe_mode"] = _safe_mode_enabled()
    result["storage_root"] = str(Path(storage_root).expanduser().resolve()) if storage_root else "default_local_runtime"
    result["prohibited_actions"] = PROHIBITED_ACTIONS
    return _json_exit(_compact_result(result, verbose=args.verbose))


if __name__ == "__main__":
    raise SystemExit(main())