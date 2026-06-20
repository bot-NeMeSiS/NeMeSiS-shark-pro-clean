#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    master = (ROOT / "engines" / "daily_automation_engine.py").read_text(encoding="utf-8", errors="replace")
    app = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    checks = {
        "job_exists": "match_lifecycle_reconciler" in master,
        "past_pending": "Resultado pendiente" in master,
        "future_upcoming": "Proximo" in master,
        "finalized": "Finalizado" in master,
        "no_fake_score": "no_invented_results" in master or "no_invented_score" in app,
        "api_window_reused": "sync_api_football_match_window" in app,
        "grading_reused": "run_pick_grading" in app,
        "old_endpoints_preserved": "/api/automation/telegram/tick" in app and "/api/automation/highlights/sync" in app and "/api/automation/data-backup/run" in app,
    }
    failed = [key for key, value in checks.items() if not value]
    print({"ok": not failed, "check": "v818_match_lifecycle_automation", "failed": failed})
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())


