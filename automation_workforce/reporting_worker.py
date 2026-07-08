from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.common import REPORTS, VERSION, print_json, workflow_arg_parser, write_report


def run_reporting_worker(dry_run: bool = True) -> dict:
    reports = sorted(p.name for p in REPORTS.glob("V915_*.md"))
    payload = {
        "ok": True,
        "version": VERSION,
        "dry_run": dry_run,
        "v915_reports": reports,
        "reports_count": len(reports),
        "next_action": "deploy V915 manually, then verify runtime and post-deploy sentinel",
    }
    write_report("V915_AUTOMATED_COMPANY_WORKFORCE_REPORT.md", "V915 Automated Company Workforce Report", payload)
    return payload


if __name__ == "__main__":
    args = workflow_arg_parser("V915 reporting worker").parse_args()
    print_json(run_reporting_worker(dry_run=args.dry_run))
