"""Professional Telegram scheduler policy for V818."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from engines.telegram_sport_filter_engine import filter_telegram_football_items, telegram_sport_filter_reason, telegram_sport_mode_summary


ALLOWED_COMPETITIONS = [
    "LaLiga",
    "Premier League",
    "Champions League",
    "Europa League",
    "Conference League",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
    "Primeira Liga",
    "Mundial",
    "Eurocopa",
    "Copa America",
    "UEFA",
    "FIFA",
    "Copa del Rey",
]


def professional_telegram_summary(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    base = telegram_sport_mode_summary(env)
    base.update(
        {
            "public_channel_policy": "top_football_only",
            "admin_errors_destination": "admin_panel_or_admin_channel",
            "allowed_competitions": ALLOWED_COMPETITIONS,
            "no_public_technical_errors": True,
            "no_spam": True,
        }
    )
    return base


def filter_public_telegram_matches(items: Iterable[Mapping[str, Any]], env: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    return [dict(item) for item in filter_telegram_football_items(list(items or []), env=env)]


def explain_public_rejections(items: Iterable[Mapping[str, Any]], env: Mapping[str, str] | None = None) -> list[dict[str, str]]:
    rejected = []
    for item in items or []:
        reason = telegram_sport_filter_reason(item, env=env)
        if reason:
            rejected.append(
                {
                    "match_id": str(item.get("id") or item.get("match_id") or ""),
                    "competition": str(item.get("competition_name") or item.get("league_name") or ""),
                    "reason": reason,
                }
            )
    return rejected
