from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.common import VERSION, print_json, python_executable, run_command, version_identity, workflow_arg_parser, write_report


def run_release_manager(dry_run: bool = True) -> dict:
    py = python_executable()
    commands = [
        [py, "-m", "py_compile", "app.py"],
        [py, "-m", "compileall", "app.py", "engines", "tools", "automation_workforce"],
        [py, "tools/check_madrid_times.py"],
        [py, "tools/check_v915_automated_company_workforce.py"],
        [py, "tools/check_v916_workforce_activation.py"],
        [py, "tools/run_continuous_sentinel_static.py"],
        [py, "tools/verify_imports_and_routes.py"],
    ]
    from automation_workforce.common import ROOT
    if (ROOT / "tools" / "check_v914_total_self_discovered_corrections.py").exists():
        commands.insert(3, [py, "tools/check_v914_total_self_discovered_corrections.py"])
    results = [run_command(cmd, timeout=180) for cmd in commands]
    payload = {
        "ok": all(item.get("ok") for item in results),
        "version": VERSION,
        "dry_run": dry_run,
        "identity": version_identity(),
        "commands": results,
        "status": "ok" if all(item.get("ok") for item in results) else "action_required",
        "safe_message": "Release Manager dry-run completado sin push ni deploy.",
        "next_action": "review_failed_checks" if not all(item.get("ok") for item in results) else "continue_to_runtime_verifier",
        "report_path": "reports/V917_WORKFORCE_FIRST_FULL_AUTOMATED_RUN_REPORT.md",
        "release_policy": "build/audit/deploy-root require explicit release step; no push/deploy here",
    }
    write_report("V917_WORKFORCE_FIRST_FULL_AUTOMATED_RUN_REPORT.md", "V917 Release Manager Worker Report", payload)
    return payload


if __name__ == "__main__":
    args = workflow_arg_parser("V915 release manager worker").parse_args()
    print_json(run_release_manager(dry_run=args.dry_run))
