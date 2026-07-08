from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.common import OUTBOX, RUNTIME, VERSION, print_json, read_json, workflow_arg_parser, write_report


VALID_STATUSES = {"BLOCKED_NO_SCREENSHOT", "READY_FOR_CODEX", "FIXABLE_SAFE", "NEEDS_HUMAN_VISUAL_REVIEW", "DANGEROUS_REQUIRES_APPROVAL", "FIXED_BY_V913"}


def run_visual_queue_manager(dry_run: bool = True) -> dict:
    queue = read_json(RUNTIME / "visual_fix_queue.json", [])
    if isinstance(queue, dict):
        queue = queue.get("items") or []
    counts = Counter(str(item.get("status") or "UNKNOWN") for item in queue if isinstance(item, dict))
    invalid = [status for status in counts if status not in VALID_STATUSES]
    payload = {
        "ok": not invalid,
        "version": VERSION,
        "dry_run": dry_run,
        "queue_total": len(queue),
        "status_counts": dict(counts),
        "invalid_statuses": invalid,
        "pixel_perfect_claim_allowed": False,
    }
    if not dry_run:
        OUTBOX.parent.mkdir(parents=True, exist_ok=True)
        OUTBOX.write_text("# Codex Outbox - V915 Visual Queue\n\npixel_perfect_claim_allowed: false\n\n## V915_VISUAL_QUEUE_STATUS\n\n" + "\n".join(f"- {k}: {v}" for k, v in sorted(counts.items())) + "\n", encoding="utf-8")
    write_report("V915_VISUAL_QUEUE_MANAGER_REPORT.md", "V915 Visual Queue Manager Report", payload)
    return payload


if __name__ == "__main__":
    args = workflow_arg_parser("V915 visual queue manager").parse_args()
    print_json(run_visual_queue_manager(dry_run=args.dry_run))
