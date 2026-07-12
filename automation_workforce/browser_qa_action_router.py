from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.common import ROOT, RUNTIME, VERSION, print_json, read_json, run_command, workflow_arg_parser, write_report


VALID_STATUSES = {
    "LOCAL_BROWSER_READY",
    "GITHUB_ACTION_READY",
    "RESULTS_FOUND_READY_TO_IMPORT",
    "BLOCKED_NO_BROWSER_RUNTIME",
    "BLOCKED_NO_SCREENSHOTS",
    "RESULTS_VALIDATED",
}


def _results_dirs() -> list[Path]:
    roots = sorted(
        (ROOT / "reports").glob("browser_qa_v*_final"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    roots.append(ROOT / "reports" / "browser_qa_render")
    return list(dict.fromkeys(roots))


def _results_dir() -> Path:
    for root in _results_dirs():
        if root.exists() and ((root / "browser_qa_result.json").exists() or (root / "reference_comparison.json").exists()):
            return root
    return ROOT / "reports" / "browser_qa_render"


def _browser_env() -> dict:
    py = str((ROOT / ".venv" / "Scripts" / "python.exe") if (ROOT / ".venv" / "Scripts" / "python.exe").exists() else sys.executable)
    result = run_command([py, "tools/check_browser_qa_environment.py"], timeout=60)
    text = f"{result.get('stdout_tail') or ''}\n{result.get('stderr_tail') or ''}"
    return {
        "raw": result,
        "playwright_available": '"playwright_available": true' in text.lower(),
        "browsers_available": '"browsers_available": true' in text.lower(),
        "can_capture": '"can_capture": true' in text.lower(),
        "status_text": text,
    }


def _results_available() -> bool:
    results_dir = _results_dir()
    if not results_dir.exists():
        return False
    return (results_dir / "browser_qa_result.json").exists() or (results_dir / "reference_comparison.json").exists()


def _screenshots_available() -> bool:
    results_dir = _results_dir()
    return results_dir.exists() and any(results_dir.glob("**/*.png"))


def _queue_stats() -> dict:
    payload = read_json(RUNTIME / "visual_fix_queue.json", [])
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        items = []
    blocked = sum(1 for item in items if isinstance(item, dict) and item.get("status") == "BLOCKED_NO_SCREENSHOT")
    ready = sum(1 for item in items if isinstance(item, dict) and item.get("status") in {"READY_FOR_CODEX", "FIXABLE_SAFE"})
    screenshots = sum(1 for item in items if isinstance(item, dict) and (item.get("screenshot") or item.get("screenshot_path")))
    return {"total": len(items), "blocked": blocked, "ready": ready, "screenshots": screenshots}


def run_browser_qa_action_router(dry_run: bool = True) -> dict:
    env = _browser_env()
    queue = _queue_stats()
    github_action = (ROOT / ".github" / "workflows" / "browser-qa.yml").exists()
    results = _results_available()
    screenshots = _screenshots_available()
    results_dir = _results_dir()

    if results and screenshots:
        status = "RESULTS_VALIDATED"
        action = "human_review_browser_qa_then_authorized_deploy"
    elif env["can_capture"]:
        status = "LOCAL_BROWSER_READY"
        action = "run_local_browser_qa"
    elif github_action:
        status = "GITHUB_ACTION_READY"
        action = "run_github_browser_qa_workflow"
    elif not env["playwright_available"]:
        status = "BLOCKED_NO_BROWSER_RUNTIME"
        action = "install_playwright_or_run_github_action"
    else:
        status = "BLOCKED_NO_SCREENSHOTS"
        action = "run_browser_qa_or_import_results"

    payload = {
        "ok": status in VALID_STATUSES,
        "version": VERSION,
        "dry_run": dry_run,
        "status": status,
        "action": action,
        "playwright_available": env["playwright_available"],
        "browsers_available": env["browsers_available"],
        "can_capture": env["can_capture"],
        "github_action_available": github_action,
        "results_available": results,
        "browser_qa_json_available": results,
        "results_dir": str(results_dir.relative_to(ROOT)).replace("\\", "/") if results_dir.exists() else "",
        "visual_queue_total": queue["total"],
        "visual_queue_blocked": queue["blocked"],
        "visual_queue_ready": queue["ready"],
        "screenshots_available": bool(queue["screenshots"] or screenshots),
        "pixel_perfect_claim_allowed": False,
        "safe_message": "Browser QA Action Router no ejecuta deploy, no usa secretos y no declara pixel-perfect sin capturas.",
        "next_action": action,
        "results_without_screenshots": bool(results and not screenshots),
        "report_path": "reports/V919_BROWSER_QA_ACTION_ROUTER_QA.md",
    }
    write_report("V919_BROWSER_QA_ACTION_ROUTER_QA.md", "V919 Browser QA Action Router QA", payload)
    return payload


if __name__ == "__main__":
    args = workflow_arg_parser("V918 Browser QA action router").parse_args()
    print_json(run_browser_qa_action_router(dry_run=args.dry_run))
