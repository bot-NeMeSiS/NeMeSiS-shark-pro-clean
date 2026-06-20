#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    guard = (ROOT / "engines" / "api_usage_guard_engine.py").read_text(encoding="utf-8", errors="replace")
    master = (ROOT / "engines" / "daily_automation_engine.py").read_text(encoding="utf-8", errors="replace")
    checks = {
        "schema": "api_usage_guard" in guard and "api_response_cache" in guard,
        "budget_api_football": "API_FOOTBALL_DAILY_CALL_BUDGET" in guard,
        "budget_odds": "ODDS_API_DAILY_CALL_BUDGET" in guard,
        "guard_called": "allow_api_job" in master,
        "cache_helpers": "cache_get" in guard and "cache_set" in guard,
        "fallback_snapshot": "api_usage_snapshot" in master,
    }
    failed = [key for key, value in checks.items() if not value]
    print({"ok": not failed, "check": "v818_api_usage_guard", "failed": failed})
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())


