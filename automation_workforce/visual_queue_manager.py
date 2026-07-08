from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.common import OUTBOX, RUNTIME, VERSION, print_json, read_json, workflow_arg_parser, write_report


VALID_STATUSES = {"BLOCKED_NO_SCREENSHOT", "READY_FOR_CODEX", "FIXABLE_SAFE", "NEEDS_HUMAN_VISUAL_REVIEW", "DANGEROUS_REQUIRES_APPROVAL", "FIXED_BY_V913", "FIXED_BY_V919"}


def run_visual_queue_manager(dry_run: bool = True) -> dict:
    queue = read_json(RUNTIME / "visual_fix_queue.json", [])
    if isinstance(queue, dict):
        queue = queue.get("items") or []
    counts = Counter(str(item.get("status") or "UNKNOWN") for item in queue if isinstance(item, dict))
    invalid = [status for status in counts if status not in VALID_STATUSES]
    blocked = int(counts.get("BLOCKED_NO_SCREENSHOT", 0))
    ready = int(counts.get("READY_FOR_CODEX", 0) + counts.get("FIXABLE_SAFE", 0))
    invalid_ready_without_screenshot = [
        item.get("id") or item.get("route") or "unknown"
        for item in queue
        if isinstance(item, dict)
        and item.get("status") in {"READY_FOR_CODEX", "FIXABLE_SAFE", "FIXED_BY_V919"}
        and not (item.get("screenshot") or item.get("screenshot_path"))
    ]
    screenshots = [
        item.get("screenshot") or item.get("screenshot_path")
        for item in queue
        if isinstance(item, dict) and (item.get("screenshot") or item.get("screenshot_path"))
    ]
    payload = {
        "ok": not invalid,
        "version": VERSION,
        "dry_run": dry_run,
        "queue_total": len(queue),
        "blocked_no_screenshot": blocked,
        "ready_for_codex": ready,
        "screenshots_available": bool(screenshots),
        "needs_human_review": int(counts.get("NEEDS_HUMAN_VISUAL_REVIEW", 0)),
        "dangerous_requires_approval": int(counts.get("DANGEROUS_REQUIRES_APPROVAL", 0)),
        "status_counts": dict(counts),
        "invalid_statuses": invalid,
        "invalid_ready_without_screenshot": len(invalid_ready_without_screenshot),
        "next_action": "run_browser_qa_or_import_results" if len(queue) and blocked == len(queue) else "review_ready_visual_queue",
        "status": "blocked_no_screenshot" if len(queue) and blocked == len(queue) else "ready",
        "safe_message": "Visual Queue no marca resuelto nada sin screenshots reales.",
        "report_path": "reports/V919_VISUAL_QUEUE_GATE_QA.md",
        "pixel_perfect_claim_allowed": False,
    }
    if not dry_run:
        OUTBOX.parent.mkdir(parents=True, exist_ok=True)
        OUTBOX.write_text("# Codex Outbox - V915 Visual Queue\n\npixel_perfect_claim_allowed: false\n\n## V915_VISUAL_QUEUE_STATUS\n\n" + "\n".join(f"- {k}: {v}" for k, v in sorted(counts.items())) + "\n", encoding="utf-8")
    write_report("V919_VISUAL_QUEUE_GATE_QA.md", "V919 Visual Queue Gate QA", payload)
    return payload


if __name__ == "__main__":
    args = workflow_arg_parser("V915 visual queue manager").parse_args()
    print_json(run_visual_queue_manager(dry_run=args.dry_run))
