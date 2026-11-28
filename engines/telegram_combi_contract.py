"""Pure whole-set admission for Telegram; never edits or repairs stored picks."""
from collections.abc import Mapping
import math

from .telegram_sport_filter_engine import is_telegram_football_item


def _text(value):
    return " ".join(str(value if value is not None else "").split())


def _first(item, *keys):
    return next((item[key] for key in keys if _text(item.get(key))), None)


def _flag(value):
    return value is not None and value != 0 and _text(value).casefold() not in {"", "0", "false", "no"}


def combi_integrity_reason(combi):
    """Closed rejection code, or empty for a complete 2..15-leg representation.

    This checks the supplied snapshot, not current market freshness, entitlement,
    a joint probability or the legitimacy of a stored total quote.
    """
    if not isinstance(combi, Mapping):
        return "COMBI_INVALID_PAYLOAD"
    rows = combi.get("picks") if combi.get("picks") is not None else combi.get("legs")
    if not isinstance(rows, (list, tuple)) or not 2 <= len(rows) <= 15:
        return "COMBI_INCOMPLETE_SET"
    if combi.get("legs_count") is not None and _text(combi["legs_count"]) != str(len(rows)):
        return "COMBI_COUNT_MISMATCH"
    seen_ids, seen_contexts = set(), set()
    for leg in rows:
        if not isinstance(leg, Mapping):
            return "COMBI_INVALID_LEG"
        if not is_telegram_football_item(leg):
            return "COMBI_SPORT_FILTERED"
        if any(_flag(leg.get(key)) for key in ("market_closed", "suspended", "is_suspended")) or any(
            _text(leg.get(key)).casefold() in {"closed", "suspended", "removed", "cancelled"}
            for key in ("status", "market_status", "odds_status")
        ):
            return "COMBI_MARKET_UNAVAILABLE"
        fields = (_first(leg, "selection", "recommendation"), leg.get("market"))
        if any(not isinstance(value, str) or not _text(value)
               or _text(value).casefold() in {"none", "null", "undefined", "n/a", "nan", "pendiente", "mercado pendiente"}
               for value in fields):
            return "COMBI_SELECTION_INCOMPLETE"
        # The shared UI text helper abbreviates individual values at 320 chars.
        # Never abbreviate a selection/market into a different betting meaning.
        if any(len(_text(value)) > 320 for value in (*fields, leg.get("home_team"), leg.get("away_team"))):
            return "COMBI_MESSAGE_TOO_LONG"
        try:
            odds = float(str(leg.get("odds")).replace(",", "."))
        except (TypeError, ValueError, OverflowError):
            return "COMBI_ODDS_UNAVAILABLE"
        if isinstance(leg.get("odds"), bool) or not math.isfinite(odds) or odds <= 1:
            return "COMBI_ODDS_UNAVAILABLE"
        match_id = _text(_first(leg, "match_id", "fixture_id"))
        home, away = _text(leg.get("home_team")), _text(leg.get("away_team"))
        context = (home.casefold(), away.casefold(), _text(_first(leg, "kickoff_iso", "match_date"))) if home and away else None
        if not context or any(not isinstance(leg.get(key), str) for key in ("home_team", "away_team")):
            return "COMBI_IDENTITY_INCOMPLETE"
        if (match_id and match_id in seen_ids) or (context and context in seen_contexts):
            return "COMBI_DUPLICATE_MATCH"
        if match_id:
            seen_ids.add(match_id)
        if context:
            seen_contexts.add(context)
    return ""


def combi_legs(combi):
    return combi.get("picks") if combi.get("picks") is not None else combi.get("legs")
