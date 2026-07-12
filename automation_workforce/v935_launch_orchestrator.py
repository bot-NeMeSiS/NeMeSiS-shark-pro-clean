"""Run the V935 launch workforce in a deterministic, read-only order."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from realtime_sports_worker import _db_path as realtime_db_path
from realtime_sports_worker import collect as collect_realtime
from v935_worker_common import ROOT, VERSION, run_role, write_evidence


MADRID = ZoneInfo("Europe/Madrid")


def _realtime_stage(db_path: str) -> dict:
    snapshot = collect_realtime(realtime_db_path(db_path))
    status = str(snapshot.get("worker_status") or "safe_unavailable")
    result = {
        "worker": "Realtime Sports Worker",
        "role": "realtime_sports",
        "status": "ok" if status in {"ok", "waiting_for_real_data", "db_missing_safe", "db_locked_safe"} else "attention",
        "ok": status in {"ok", "waiting_for_real_data", "db_missing_safe", "db_locked_safe"},
        "dry_run": True,
        "safe_message": snapshot.get("safe_message") or "Lectura realtime cache-first completada.",
        "next_action": "continue_launch_validation" if status == "ok" else "run_authorized_sports_sync",
        "findings": [],
        "metrics": {
            "counts": snapshot.get("counts") or {},
            "match_status": snapshot.get("realtime_match_status"),
            "live_status": snapshot.get("realtime_live_status"),
            "data_trust_status": (snapshot.get("data_trust") or {}).get("status"),
        },
        "external_calls": 0,
        "database_writes": 0,
        "secrets_visible": False,
        "generated_at_madrid": datetime.now(MADRID).isoformat(timespec="seconds"),
    }
    json_path, report_path = write_evidence(result, "realtime_sports")
    result["json_path"] = json_path
    result["report_path"] = report_path
    return result


def run(db_path: str = "") -> dict:
    stages = [
        ("route_performance", lambda: run_role("performance_budget", db_path, slug="route_performance")),
        ("match_lifecycle", lambda: run_role("match_lifecycle", db_path)),
        ("pick_lifecycle", lambda: run_role("pick_lifecycle", db_path)),
        ("odds_freshness", lambda: run_role("odds_freshness", db_path)),
        ("realtime_sports", lambda: _realtime_stage(db_path)),
        ("data_trust", lambda: run_role("data_trust", db_path)),
        ("customer_trust", lambda: run_role("customer_trust", db_path)),
        ("product_experience", lambda: run_role("product_experience", db_path)),
        ("visual_consistency", lambda: run_role("visual_consistency", db_path)),
        ("performance", lambda: run_role("performance_budget", db_path, slug="performance")),
        ("accessibility", lambda: run_role("accessibility", db_path)),
        ("launch_readiness", lambda: run_role("launch_readiness", db_path)),
    ]
    results: list[dict] = []
    for stage, callback in stages:
        try:
            result = callback()
        except Exception as exc:
            result = {
                "worker": stage,
                "role": stage,
                "status": "blocked",
                "ok": False,
                "dry_run": True,
                "safe_message": f"Worker blocked safely: {type(exc).__name__}",
                "next_action": f"repair_{stage}_worker",
                "findings": [],
                "external_calls": 0,
                "database_writes": 0,
                "secrets_visible": False,
            }
        results.append({"stage": stage, **result})
    blocked = [item for item in results if not item.get("ok")]
    attention = [item for item in results if item.get("status") == "attention"]
    browser_status_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "browser_qa_status.json"
    try:
        browser_status = json.loads(browser_status_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        browser_status = {}
    browser_screenshots = int(browser_status.get("screenshots_captured") or 0)
    browser_ready = (
        browser_status.get("browser_qa_status") == "CAPTURED"
        and browser_screenshots > 0
        and not (browser_status.get("capture_errors") or [])
        and not (browser_status.get("auth_redirect_issues") or [])
        and not (browser_status.get("overflow_issues") or [])
    )
    overall = "blocked" if blocked else "action_required" if attention else "ready_for_release_validation"
    default_action = "build_clean_release" if browser_ready else "run_browser_qa_and_package"
    next_action = (blocked or attention or [{"next_action": default_action}])[0].get("next_action")
    payload = {
        "version": VERSION,
        "dry_run": True,
        "overall_status": overall,
        "next_required_action": next_action,
        "workers_total": len(results),
        "workers_ok": sum(1 for item in results if item.get("ok")),
        "workers_blocked": len(blocked),
        "browser_qa_status": browser_status.get("browser_qa_status") or "not_run",
        "browser_screenshots": browser_screenshots,
        "browser_qa_ready": browser_ready,
        "stages": results,
        "external_calls": 0,
        "database_writes": 0,
        "secrets_visible": False,
        "generated_at_madrid": datetime.now(MADRID).isoformat(timespec="seconds"),
    }
    output = ROOT / "data" / "runtime" / "automation_workforce" / "v935_latest_run.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="V935 safe launch workforce orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Explicitly confirm read-only execution")
    parser.add_argument("--db-path", default="", help="Optional local DB path")
    args = parser.parse_args()
    payload = run(args.db_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("overall_status") != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
