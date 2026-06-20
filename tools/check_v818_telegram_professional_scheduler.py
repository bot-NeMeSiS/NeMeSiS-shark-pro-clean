#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    scheduler = (ROOT / "engines" / "telegram_professional_scheduler.py").read_text(encoding="utf-8", errors="replace")
    sport_filter = (ROOT / "engines" / "telegram_sport_filter_engine.py").read_text(encoding="utf-8", errors="replace")
    app = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    requirements = {
        "solo_futbol": "football_only" in sport_filter and "filter_telegram_football_items" in scheduler,
        "bloquea_nba": "nba" in sport_filter.lower(),
        "bloquea_juveniles": "juvenil" in sport_filter.lower() or "youth" in sport_filter.lower(),
        "bloquea_reservas": "reserve" in sport_filter.lower(),
        "bloquea_regional": "regional" in sport_filter.lower(),
        "competitions_top": "Premier League" in scheduler and "Champions League" in scheduler and "LaLiga" in scheduler,
        "public_no_technical_errors": "no_public_technical_errors" in scheduler,
        "admin_panel_wired": "professional_telegram_summary" in app,
    }
    failed = [key for key, value in requirements.items() if not value]
    print({"ok": not failed, "check": "v818_telegram_professional_scheduler", "failed": failed})
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

