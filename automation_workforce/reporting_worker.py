from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.browser_qa_orchestrator import run_browser_qa_orchestrator
from automation_workforce.common import REPORTS, ROOT, VERSION, madrid_now_iso, print_json, read_json, workflow_arg_parser, write_json, write_report
from automation_workforce.post_deploy_sentinel import run_post_deploy_sentinel
from automation_workforce.release_manager import run_release_manager
from automation_workforce.runtime_verifier import run_runtime_verifier
from automation_workforce.security_secret_guard import run_security_secret_guard
from automation_workforce.telegram_dry_run_watcher import run_telegram_dry_run_watcher
from automation_workforce.visual_queue_manager import run_visual_queue_manager


WORKFORCE_RUNTIME = ROOT / "data" / "runtime" / "automation_workforce"
LATEST_RUN = WORKFORCE_RUNTIME / "latest_run.json"


def _status(result: dict[str, Any]) -> str:
    return str(result.get("status") or ("ok" if result.get("ok") else "action_required"))


def run_reporting_worker(dry_run: bool = True, worker_results: dict[str, dict[str, Any]] | None = None) -> dict:
    results = worker_results or {
        "release_manager": run_release_manager(dry_run=True),
        "runtime_verifier": run_runtime_verifier(dry_run=True),
        "post_deploy_sentinel": run_post_deploy_sentinel(dry_run=True),
        "secret_guard": run_security_secret_guard(dry_run=True),
        "browser_qa_orchestrator": run_browser_qa_orchestrator(dry_run=True),
        "visual_queue_manager": run_visual_queue_manager(dry_run=True),
        "telegram_dry_run_watcher": run_telegram_dry_run_watcher(dry_run=True),
    }
    visual = results.get("visual_queue_manager") or {}
    browser = results.get("browser_qa_orchestrator") or {}
    secret = results.get("secret_guard") or {}
    runtime = results.get("runtime_verifier") or {}
    status_map = {name: _status(result) for name, result in results.items()}
    blocking_statuses = {status for status in status_map.values() if status not in {"ok", "ready"}}
    next_action = "run_browser_qa_then_refresh_visual_queue"
    if secret.get("findings_count"):
        next_action = "review_secret_guard_findings"
    elif runtime.get("alignment_status") == "DEPLOY_ALIGNMENT_FAILED":
        next_action = "deploy_v917_and_verify_runtime"
    elif browser.get("status") == "package_missing":
        next_action = "install_playwright_or_run_github_action"
    elif visual.get("blocked_no_screenshot"):
        next_action = "run_browser_qa_then_refresh_visual_queue"
    payload = {
        "ok": True,
        "version": VERSION,
        "dry_run": dry_run,
        "generated_at_madrid": madrid_now_iso(),
        "release_manager_status": status_map.get("release_manager"),
        "runtime_verifier_status": status_map.get("runtime_verifier"),
        "post_deploy_sentinel_status": status_map.get("post_deploy_sentinel"),
        "secret_guard_status": status_map.get("secret_guard"),
        "browser_qa_orchestrator_status": status_map.get("browser_qa_orchestrator"),
        "visual_queue_manager_status": status_map.get("visual_queue_manager"),
        "telegram_dry_run_watcher_status": status_map.get("telegram_dry_run_watcher"),
        "reporting_worker_status": "ok",
        "overall_status": "action_required" if blocking_statuses else "ok",
        "next_required_action": next_action,
        "workers": results,
        "reports": sorted(p.name for p in REPORTS.glob("V917_*.md")),
        "safe_message": "Full workforce run consolidado sin secretos, sin Telegram real, sin pagos y sin deploy automatico.",
        "report_path": "reports/V917_WORKER_STATUS_SUMMARY.md",
    }
    write_json(LATEST_RUN, payload)
    write_report("V917_WORKER_STATUS_SUMMARY.md", "V917 Worker Status Summary", payload)
    write_report("V917_WORKFORCE_FIRST_FULL_AUTOMATED_RUN_REPORT.md", "V917 Workforce First Full Automated Run Report", payload)
    return payload


if __name__ == "__main__":
    args = workflow_arg_parser("V917 reporting worker").parse_args()
    print_json(run_reporting_worker(dry_run=args.dry_run))
