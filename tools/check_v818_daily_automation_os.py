#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def contains(path: str, *needles: str) -> list[str]:
    text = (ROOT / path).read_text(encoding="utf-8", errors="replace")
    return [needle for needle in needles if needle not in text]


def main() -> int:
    missing = []
    for path in [
        "engines/daily_automation_engine.py",
        "engines/api_usage_guard_engine.py",
        "engines/telegram_professional_scheduler.py",
        "templates/admin_daily_automation.html",
    ]:
        if not (ROOT / path).exists():
            missing.append(path)
    missing += contains(
        "app.py",
        "/api/automation/master-tick",
        "automation_cron_access_allowed()",
        "/api/automation/health-check",
        "/admin/daily-automation",
        "/api/admin/daily-automation/status",
    )
    version_txt = (ROOT / "VERSION.txt").read_text(encoding="utf-8", errors="replace")
    if not any(version in version_txt for version in {
        "V818_DAILY_AUTOMATION_OPERATING_SYSTEM_FINAL",
        "V819_REFERENCE_UI_DEDUP_LAYER_PURGE_CLIENT_ADMIN_FINAL",
        "V820_REAL_CRESTS_REFERENCE_VISUAL_PIXEL_POLISH_FINAL",
    }):
        missing.append("V818_DAILY_AUTOMATION_OPERATING_SYSTEM_FINAL_OR_NEWER")
    missing += contains(
        "engines/daily_automation_engine.py",
        "automation_jobs_state",
        "automation_job_runs",
        "automation_dedupe",
        "automation_health_events",
        "claim_dedupe",
        "Europe/Madrid",
        "next_recommended_run",
    )
    ok = not missing
    print({"ok": ok, "check": "v818_daily_automation_os", "missing": missing})
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
