#!/usr/bin/env python3
"""V813 full ecosystem certification checks."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def ok(name: str, condition: bool, detail: str = "") -> bool:
    status = "OK" if condition else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[V813_ECOSYSTEM] {status} {name}{suffix}")
    return condition


def main() -> int:
    failures = 0
    os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v813_check_runtime.db"))
    os.environ.setdefault("START_BACKGROUND_JOBS", "false")
    os.environ.setdefault("SCHEDULER_ENABLED", "false")

    import app as nemesis_app  # noqa: WPS433
    from engines.telegram_sport_filter_engine import telegram_sport_filter_reason

    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
    failures += not ok("VERSION.txt V813/V814", version in {"V813_CODEX_FULL_ECOSYSTEM_RESTRUCTURE_REFERENCE_SELL_READY", "V814_CODEX_DEEP_PROJECT_RECONCILIATION_CLIENT_ADMIN_REFERENCE_FINAL"})
    failures += not ok("APP_VERSION coincide con VERSION", nemesis_app.APP_VERSION == version)
    failures += not ok("DB_PATH no cambia en cÃ³digo", "DB_PATH = os.getenv(\"DB_PATH\", \"/data/database.db\")" in (ROOT / "app.py").read_text(encoding="utf-8", errors="replace"))

    now = datetime.now(nemesis_app.TZ)
    future = {"match_date": (now + timedelta(days=1)).date().isoformat(), "kickoff_time": "21:00", "status": "NS"}
    live = {"match_date": now.date().isoformat(), "kickoff_time": (now - timedelta(minutes=28)).strftime("%H:%M"), "status": "1H"}
    finished = {"match_date": (now - timedelta(days=1)).date().isoformat(), "kickoff_time": "20:00", "status": "FT", "score": "2-1"}
    past_without_result = {"match_date": (now - timedelta(days=2)).date().isoformat(), "kickoff_time": "20:00", "status": "NS"}

    failures += not ok("partido futuro sigue prÃ³ximo", nemesis_app.canonical_match_status(future)["is_upcoming"])
    failures += not ok("partido live no es prÃ³ximo", nemesis_app.canonical_match_status(live)["is_live"])
    failures += not ok("partido finalizado no es live", nemesis_app.canonical_match_status(finished)["is_finished"])
    failures += not ok(
        "partido pasado sin resultado no vuelve a prÃ³ximos",
        nemesis_app.canonical_match_status(past_without_result)["key"] == "RESULT_PENDING",
        nemesis_app.canonical_match_status(past_without_result).get("label", ""),
    )

    env = {"TELEGRAM_PRO_CHANNEL_STRICT": "true"}
    failures += not ok("Telegram bloquea NBA", telegram_sport_filter_reason({"sport_key": "basketball_nba"}, env) == "deporte_no_futbol")
    failures += not ok("Telegram bloquea regional", telegram_sport_filter_reason({"league_name": "AndalucÃ­a Regional"}, env) == "competicion_no_profesional")
    failures += not ok("Telegram bloquea juveniles", telegram_sport_filter_reason({"league_name": "Spain U19 Youth"}, env) == "competicion_no_profesional")
    failures += not ok("Telegram permite Champions", telegram_sport_filter_reason({"league_name": "UEFA Champions League", "sport_key": "soccer_uefa_champs_league"}, env) == "")

    expected_reports = [
        "reports/V813_INITIAL_AUDIT_AND_RESTRUCTURE_PLAN.md",
        "reports/V813_CODEX_FULL_ECOSYSTEM_RESTRUCTURE_REFERENCE_SELL_READY_REPORT.md",
        "reports/V813_PROJECT_CLEANUP_REPORT.md",
        "reports/V813_VISUAL_REFERENCE_QA_REPORT.md",
        "reports/V813_ROUTES_AND_LINKS_QA_REPORT.md",
        "reports/V813_TELEGRAM_PROFESSIONAL_CHANNEL_QA_REPORT.md",
        "CHATGPT_CONTINUATION_REPORT.md",
    ]
    for rel in expected_reports:
        failures += not ok(f"entregable {rel}", (ROOT / rel).exists())

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

