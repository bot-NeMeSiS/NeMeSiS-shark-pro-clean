from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.common import ROOT, RUNTIME, VERSION, print_json, python_executable, read_json, run_command, workflow_arg_parser, write_report


def run_browser_qa_orchestrator(dry_run: bool = True) -> dict:
    py = python_executable()
    env = run_command([py, "tools/check_browser_qa_environment.py"])
    env_text = f"{env.get('stdout_tail') or ''}\n{env.get('stderr_tail') or ''}"
    package_available = "PACKAGE_MISSING" not in env_text and "playwright_available\": false" not in env_text.lower()
    browsers_available = "BROWSERS_MISSING" not in env_text and "browsers_available\": false" not in env_text.lower()
    queue_payload = read_json(RUNTIME / "visual_fix_queue.json", [])
    queue_items = queue_payload.get("items") if isinstance(queue_payload, dict) else queue_payload
    if not isinstance(queue_items, list):
        queue_items = []
    blocked = sum(1 for item in queue_items if isinstance(item, dict) and item.get("status") == "BLOCKED_NO_SCREENSHOT")
    github_action_available = (ROOT / ".github" / "workflows" / "browser-qa.yml").exists()
    screenshot_roots = [ROOT / "reports" / "browser_qa_render", ROOT / "reports" / "V918_browser_qa"]
    screenshots_available = any(root.exists() and any(root.glob("**/*.png")) for root in screenshot_roots)
    if package_available and browsers_available and not dry_run:
        qa = run_command([py, "tools/run_browser_reference_qa.py", "--base-url", "https://bot-apuestas-crgf.onrender.com", "--output", "reports/browser_qa_render", "--mobile", "--desktop", "--write-json"], timeout=180)
        importer = run_command([py, "tools/import_browser_qa_results.py", "--input", "reports/browser_qa_render", "--update-runtime-data"])
    else:
        qa = {"ok": True, "skipped": True, "reason": "dry_run_or_browser_unavailable"}
        importer = {"ok": True, "skipped": True, "reason": "no_new_browser_results"}
    payload = {
        "ok": bool(env.get("ok")) and bool(qa.get("ok")) and bool(importer.get("ok")),
        "version": VERSION,
        "dry_run": dry_run,
        "package_available": package_available,
        "browsers_available": browsers_available,
        "can_run_local": bool(package_available and browsers_available),
        "github_action_available": github_action_available,
        "screenshots_available": screenshots_available,
        "visual_queue_blocked": blocked,
        "next_action": "run_browser_qa" if package_available and browsers_available else "install_playwright_or_run_github_action",
        "status": "ok" if package_available and browsers_available else "package_missing",
        "safe_message": "Browser QA orchestrator no declara pixel-perfect sin capturas reales.",
        "report_path": "reports/V918_BROWSER_QA_ORCHESTRATOR_RUN_QA.md",
        "environment_check": env,
        "browser_qa": qa,
        "import_results": importer,
        "pixel_perfect_claim_allowed": False,
    }
    write_report("V918_BROWSER_QA_ORCHESTRATOR_RUN_QA.md", "V918 Browser QA Orchestrator Run QA", payload)
    return payload


if __name__ == "__main__":
    args = workflow_arg_parser("V915 browser QA orchestrator").parse_args()
    print_json(run_browser_qa_orchestrator(dry_run=args.dry_run))
