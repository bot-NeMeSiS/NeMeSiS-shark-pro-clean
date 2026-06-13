#!/usr/bin/env python3
"""Validate V750 client live screen polish."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()

CHECKS = []

def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))

live_template = (ROOT / "templates" / "live.html").read_text(encoding="utf-8")
live_engine = (ROOT / "engines" / "live_experience_engine.py").read_text(encoding="utf-8")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

check("version_v750_or_newer", VERSION in {
    "V750_CLIENT_LIVE_DAY_RELEVANCE_MADRID_RESULT_POLISH",
    "V751_TELEGRAM_PICK_ULTRA_PRO_MESSAGE_EXPERIENCE",
    "V752_TELEGRAM_FULL_AUTO_ARTILLERY_PRODUCTION_CERTIFICATION",
    "V753_TELEGRAM_PRODUCTION_AUTOPILOT_ENVIRONMENT_AUDIT_AND_REAL_CRON_CERTIFICATION",
    "V754_TELEGRAM_AUTO_PICK_CANDIDATE_WINDOW_DELIVERY_FIX", "V756_CLIENT_APP_PREMIUM_EXPERIENCE_TOTAL_POLISH",
}, VERSION)
check("live_day_groups_template", "live.day_groups" in live_template and "v750-live-day-group" in live_template)
check("live_scorebox_template", "v750-live-scorebox" in live_template and "live_score_label" in live_template)
check("live_madrid_time_copy", "hora Madrid" in live_template or "Hora Madrid" in live_template)
check("live_no_legacy_only_groups", "v750-live-card" in live_template and "league.matches" in live_template)
check("engine_day_grouping", "def _group_by_day" in live_engine and "day_groups" in live_engine)
check("engine_relevance_sort", "importance_score" in live_engine and "live_priority_score" in live_engine)
check("engine_no_fake_scores", "live_score_label" in live_engine and "score or" in live_engine)
check("engine_madrid_helper", "normalize_kickoff_for_display" in live_engine)
check("css_v750_present", "V750 · Client Live" in css and "v750-live-card" in css)
check("report_present", (ROOT / "reports" / "V750_CLIENT_LIVE_DAY_RELEVANCE_MADRID_RESULT_POLISH_REPORT.md").exists())

failed = [item for item in CHECKS if not item[1]]
for name, ok, detail in CHECKS:
    print(f"{'OK' if ok else 'FAIL'} {name} {detail}".rstrip())
if failed:
    print(f"V750 live experience check failed: {len(failed)}", file=sys.stderr)
    raise SystemExit(1)
print("V750 client live experience check OK")
