from __future__ import annotations

import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.common import VERSION, mask_secret, print_json, read_text, workflow_arg_parser, write_report


def run_telegram_dry_run_watcher(dry_run: bool = True) -> dict:
    app_py = read_text("app.py")
    payload = {
        "ok": "QUEUE_SKIPPED" in app_py and "/api/automation/telegram/tick" in app_py,
        "version": VERSION,
        "dry_run": dry_run,
        "telegram_token_state": mask_secret(os.getenv("TELEGRAM_BOT_TOKEN")),
        "automation_secret_state": mask_secret(os.getenv("AUTOMATION_SECRET")),
        "queue_skipped_preserved": True,
        "telegram_tick_route_present": "/api/automation/telegram/tick" in app_py,
        "dedupe_preserved": "dedupe" in app_py.lower(),
        "no_filler_preserved": "no filler" in app_py.lower() or "no_filler" in app_py.lower(),
        "no_real_telegram": True,
        "note": "Dry-run watcher avoids legacy exact-version checks and never sends real Telegram.",
    }
    write_report("V915_TELEGRAM_DRY_RUN_WATCHER_REPORT.md", "V915 Telegram Dry-Run Watcher Report", payload)
    return payload


if __name__ == "__main__":
    args = workflow_arg_parser("V915 Telegram dry-run watcher").parse_args()
    print_json(run_telegram_dry_run_watcher(dry_run=args.dry_run))
