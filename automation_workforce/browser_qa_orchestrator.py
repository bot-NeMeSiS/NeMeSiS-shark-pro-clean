from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.common import VERSION, print_json, python_executable, run_command, workflow_arg_parser, write_report


def run_browser_qa_orchestrator(dry_run: bool = True) -> dict:
    py = python_executable()
    env = run_command([py, "tools/check_browser_qa_environment.py"])
    qa = run_command([py, "tools/run_browser_reference_qa.py", "--base-url", "https://bot-apuestas-crgf.onrender.com", "--output", "reports/browser_qa_render", "--mobile", "--desktop", "--write-json"], timeout=180)
    importer = run_command([py, "tools/import_browser_qa_results.py", "--input", "reports/browser_qa_render", "--update-runtime-data"])
    payload = {
        "ok": env.get("ok") and qa.get("ok") and importer.get("ok"),
        "version": VERSION,
        "dry_run": dry_run,
        "environment_check": env,
        "browser_qa": qa,
        "import_results": importer,
        "pixel_perfect_claim_allowed": False,
    }
    write_report("V915_BROWSER_QA_ORCHESTRATOR_REPORT.md", "V915 Browser QA Orchestrator Report", payload)
    return payload


if __name__ == "__main__":
    args = workflow_arg_parser("V915 browser QA orchestrator").parse_args()
    print_json(run_browser_qa_orchestrator(dry_run=args.dry_run))
