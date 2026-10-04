"""Closed diagnostic codes from The Odds API; never return provider free text."""

KNOWN_ODDS_ERROR_CODES = frozenset({
    "MISSING_KEY", "INVALID_KEY", "DEACTIVATED_KEY", "EXCEEDED_FREQ_LIMIT",
    "OUT_OF_USAGE_CREDITS", "HISTORICAL_UNAVAILABLE_ON_FREE_USAGE_PLAN",
})
