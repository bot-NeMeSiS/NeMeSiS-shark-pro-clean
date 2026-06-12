"""Telegram sport filtering helpers for NeMeSiS SHARK PRO.

Telegram is a premium football channel by default. These helpers keep
basketball/NBA/other sports out of automatic messages without breaking the
main app, admin views or future multi-sport work.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping

_FALSE_VALUES = {"0", "false", "no", "off", "multi", "all", "multisport", "multi_sport"}
_TRUE_VALUES = {"1", "true", "yes", "on", "football", "football_only", "soccer", "soccer_only", "futbol", "fútbol"}

# Hard negative context. If any of these appears in sport/league/key text, it
# must not be pushed to Telegram automatic delivery while football-only mode is on.
_NON_FOOTBALL_RE = re.compile(
    r"\b("
    r"basket|basketball|nba|wnba|euroleague|liga\s+endesa|acb|ncaa|ncaab|cbb|"
    r"tennis|atp|wta|rugby|cricket|baseball|mlb|hockey|nhl|handball|volleyball|"
    r"ufc|mma|boxing|golf|motogp|formula\s*1|f1|esports|darts|snooker"
    r")\b",
    flags=re.I,
)

# Positive football context. It is intentionally broad because many existing DB
# rows were created before a dedicated sport column existed.
_FOOTBALL_RE = re.compile(
    r"\b("
    r"soccer|football|futbol|fútbol|fifa|uefa|laliga|liga|premier|serie\s*a|"
    r"bundesliga|ligue\s*1|champions|europa\s+league|conference|copa|mundial|"
    r"world\s+cup|euro|nations\s+league|libertadores|sudamericana|mls|"
    r"eredivisie|primeira|segunda|rfef|andalu"
    r")\b",
    flags=re.I,
)

_EXPLICIT_SPORT_FIELDS = (
    "sport",
    "strSport",
    "sport_name",
    "sport_title",
    "sport_key",
    "sportKey",
    "competition_id",
    "external_sport",
)

_CONTEXT_FIELDS = (
    *_EXPLICIT_SPORT_FIELDS,
    "competition_key",
    "competition_name",
    "league_name",
    "league",
    "country",
    "source",
    "market",
    "home_team",
    "away_team",
)


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def telegram_football_only_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return whether automatic Telegram delivery must be football-only.

    Default is ON because the current commercial product is positioned around
    football. It can be disabled later with TELEGRAM_SPORT_MODE=multi or
    TELEGRAM_FOOTBALL_ONLY=false.
    """
    env = env or os.environ
    mode = _text(env.get("TELEGRAM_SPORT_MODE") or env.get("TELEGRAM_ALLOWED_SPORTS") or "football_only").lower()
    explicit = _text(env.get("TELEGRAM_FOOTBALL_ONLY") or "").lower()
    if explicit in _FALSE_VALUES:
        return False
    if explicit in _TRUE_VALUES:
        return True
    return mode not in _FALSE_VALUES


def _raw_json_text(item: Mapping[str, Any]) -> str:
    raw = item.get("raw_json") or item.get("payload_json") or ""
    if isinstance(raw, (dict, list)):
        return json.dumps(raw, ensure_ascii=False)[:3000]
    raw_text = _text(raw)
    if len(raw_text) > 3000:
        raw_text = raw_text[:3000]
    return raw_text


def _context_text(item: Mapping[str, Any]) -> str:
    parts = []
    for key in _CONTEXT_FIELDS:
        value = item.get(key)
        if value not in (None, "", [], {}):
            parts.append(_text(value))
    raw = _raw_json_text(item)
    if raw:
        # Only a small slice: enough to catch sport_key/sport_title, not enough
        # to leak huge provider payloads into logs or memory.
        parts.append(raw)
    return " | ".join(parts).lower()


def telegram_sport_filter_reason(item: Mapping[str, Any] | None, env: Mapping[str, str] | None = None) -> str:
    """Return empty string if item can be sent; otherwise the discard reason."""
    if not telegram_football_only_enabled(env):
        return ""
    item = dict(item or {})
    context = _context_text(item)
    if _NON_FOOTBALL_RE.search(context):
        return "deporte_no_futbol"
    # The Odds API football keys start with soccer_. If there is an explicit
    # non-soccer sport key, block it even if team/league text is ambiguous.
    explicit = " | ".join(_text(item.get(k)).lower() for k in _EXPLICIT_SPORT_FIELDS if item.get(k))
    if explicit and not _FOOTBALL_RE.search(explicit) and any(token in explicit for token in ("basketball_", "tennis_", "baseball_", "icehockey_", "americanfootball_")):
        return "deporte_no_futbol"
    # Known football context passes.
    if _FOOTBALL_RE.search(context):
        return ""
    # Legacy rows may not have sport fields. Do not block unknown legacy data,
    # but all clear basketball/other-sport signals above are rejected.
    return ""


def is_telegram_football_item(item: Mapping[str, Any] | None, env: Mapping[str, str] | None = None) -> bool:
    return not telegram_sport_filter_reason(item or {}, env=env)


def filter_telegram_football_items(items, env: Mapping[str, str] | None = None):
    return [item for item in (items or []) if is_telegram_football_item(item, env=env)]


def telegram_sport_mode_summary(env: Mapping[str, str] | None = None) -> dict:
    enabled = telegram_football_only_enabled(env)
    return {
        "mode": "football_only" if enabled else "multi_sport",
        "football_only": enabled,
        "allowed": ["football", "soccer", "fútbol"] if enabled else ["multi_sport"],
        "blocked_examples": ["basketball", "NBA", "WNBA", "tennis", "baseball"] if enabled else [],
    }
