#!/usr/bin/env python3
"""V814 full ecosystem reconciliation checks."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


EXPECTED_VERSION = "V814_CODEX_DEEP_PROJECT_RECONCILIATION_CLIENT_ADMIN_REFERENCE_FINAL"
CURRENT_ACCEPTED_VERSION = "V815_RENDER_VISIBLE_REFERENCE_REBUILD_REPO_RECONCILIATION_FINAL"


def ok(name: str, condition: bool, detail: str = "") -> bool:
    print(f"[V814_ECOSYSTEM] {'OK' if condition else 'FAIL'} {name}{(' - ' + detail) if detail else ''}")
    return bool(condition)


def main() -> int:
    failures = 0
    os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v814_check_runtime.db"))
    os.environ.setdefault("START_BACKGROUND_JOBS", "false")
    os.environ.setdefault("SCHEDULER_ENABLED", "false")

    import app as nemesis_app  # noqa: WPS433
    from engines.telegram_sport_filter_engine import telegram_sport_filter_reason, telegram_sport_mode_summary

    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
    app_text = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
    build = (ROOT / "tools" / "build_clean_release.py").read_text(encoding="utf-8", errors="replace")

    failures += not ok("VERSION.txt V814/V815", version in {EXPECTED_VERSION, CURRENT_ACCEPTED_VERSION})
    failures += not ok("APP_VERSION coincide", nemesis_app.APP_VERSION == version)
    failures += not ok("DB_PATH Render intacto", 'DB_PATH = os.getenv("DB_PATH", "/data/database.db")' in app_text)
    failures += not ok("shell V814 base", 'data-v814-shell="true"' in base)
    failures += not ok("CSS V814 activo", EXPECTED_VERSION in css)
    failures += not ok(
        "build incluye V814/V815",
        "reports/V814_" in build and "RELEASE_ZIP_AUDIT_V814" in build
        and "reports/V815_" in build and "RELEASE_ZIP_AUDIT_V815" in build,
    )

    now = datetime.now(nemesis_app.TZ)
    cases = {
        "futuro": ({"match_date": (now + timedelta(days=1)).date().isoformat(), "kickoff_time": "21:00", "status": "NS"}, "UPCOMING"),
        "empezado_sin_score": ({"kickoff_iso": (now - timedelta(minutes=35)).isoformat(), "status": "NS"}, "LIVE_PENDING"),
        "live_api": ({"match_date": now.date().isoformat(), "kickoff_time": (now - timedelta(minutes=12)).strftime("%H:%M"), "status": "1H", "minute": "12"}, "LIVE"),
        "finalizado": ({"match_date": (now - timedelta(days=1)).date().isoformat(), "kickoff_time": "20:00", "status": "FT", "score": "2-1"}, "FT"),
        "madrugada_pasado": ({"match_date": (now - timedelta(days=1)).date().isoformat(), "kickoff_time": "00:30", "status": "NS"}, "RESULT_PENDING"),
        "sin_score_api": ({"match_date": (now - timedelta(days=2)).date().isoformat(), "kickoff_time": "18:00", "status": ""}, "RESULT_PENDING"),
    }
    for name, (payload, expected) in cases.items():
        got = nemesis_app.canonical_match_status(payload).get("key")
        failures += not ok(f"lifecycle {name}", got == expected, f"{got} != {expected}")

    env = {"TELEGRAM_PRO_CHANNEL_STRICT": "true"}
    failures += not ok("Telegram modo profesional activo", telegram_sport_mode_summary(env).get("professional_channel") is True)
    failures += not ok("Telegram bloquea NBA", telegram_sport_filter_reason({"sport_key": "basketball_nba"}, env) == "deporte_no_futbol")
    failures += not ok("Telegram bloquea regional", telegram_sport_filter_reason({"league_name": "Andalucía Regional"}, env) == "competicion_no_profesional")
    failures += not ok("Telegram bloquea reservas", telegram_sport_filter_reason({"league_name": "Premier League Reserves"}, env) == "competicion_no_profesional")
    failures += not ok("Telegram bloquea amistoso menor", telegram_sport_filter_reason({"league_name": "Club Friendly"}, env) == "competicion_no_profesional")
    failures += not ok("Telegram permite LaLiga", telegram_sport_filter_reason({"league_name": "LaLiga", "sport_key": "soccer_spain_la_liga"}, env) == "")
    failures += not ok("Telegram permite Champions", telegram_sport_filter_reason({"league_name": "UEFA Champions League", "sport_key": "soccer_uefa_champs_league"}, env) == "")

    expected_reports = [
        "reports/V814_DEEP_PROJECT_RECONCILIATION_AUDIT.md",
        "reports/V814_PROJECT_PURGE_AND_STRUCTURE_REPORT.md",
        "reports/V814_CODEX_DEEP_PROJECT_RECONCILIATION_CLIENT_ADMIN_REFERENCE_FINAL_REPORT.md",
        "reports/V814_VISUAL_CLIENT_ADMIN_REFERENCE_QA.md",
        "reports/V814_MATCH_LIFECYCLE_AND_LIVE_DATA_QA.md",
        "reports/V814_TELEGRAM_PRO_CHANNEL_QA.md",
        "reports/V814_ROUTES_LINKS_NAVIGATION_QA.md",
        "CHATGPT_CONTINUATION_REPORT.md",
    ]
    for rel in expected_reports:
        failures += not ok(f"entregable {rel}", (ROOT / rel).exists())

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
