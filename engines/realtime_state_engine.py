"""Canonical read-only real-time projection for NeMeSiS sports surfaces.

This module deliberately does not open databases, call providers, mutate inputs,
or decide lifecycle independently. MATCH-STATUS-TRUTH-V2 remains the authority.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Iterable

from engines.v935_launch_trust_engine import (
    get_match_source,
    madrid_now,
    match_kickoff_madrid,
    match_status_truth,
)

REALTIME_STATE_CONTRACT = "NEMESIS-REALTIME-STATE-V1"
REALTIME_CHANGE_CONTRACT = "NEMESIS-REALTIME-CHANGE-V1"

_CAPABILITIES = (
    "events",
    "lineups",
    "stats",
    "standings",
    "odds",
    "injuries",
    "players",
)
_PROVIDER_CLOCK_FIELDS = (
    "live_updated_at",
    "provider_updated_at",
    "last_synced_at",
)


def _text(value: Any, limit: int = 180) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _parse_iso(value: Any) -> datetime | None:
    text = _text(value, 100)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return madrid_now(parsed)


def _provider_clock(item: dict[str, Any]) -> tuple[str, str, datetime | None]:
    for field in _PROVIDER_CLOCK_FIELDS:
        value = item.get(field)
        parsed = _parse_iso(value)
        if parsed is not None:
            return field, _text(value, 100), parsed
    return "", "", None


def _score_value(value: Any) -> int | float | None:
    if value in (None, "", "None", "null", "undefined"):
        return None
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    if number < 0:
        return None
    return int(number) if number.is_integer() else number


def _score_pair(item: dict[str, Any]) -> tuple[int | float | None, int | float | None]:
    home = _score_value(item.get("home_score"))
    away = _score_value(item.get("away_score"))
    if home is not None or away is not None:
        return home, away

    score = _text(item.get("score") or item.get("result"), 40)
    for separator in ("-", ":", "–"):
        if separator not in score:
            continue
        left, right = score.split(separator, 1)
        return _score_value(left), _score_value(right)
    return None, None


def _minute(item: dict[str, Any], *, is_live: bool) -> str | None:
    if not is_live:
        return None
    for field in ("minute", "elapsed", "live_minute", "strProgress"):
        value = _text(item.get(field), 24)
        if not value:
            continue
        normalized = value.replace("'", "").strip()
        if normalized.isdigit():
            return str(int(normalized))
    return None


def _identity(item: dict[str, Any]) -> dict[str, str]:
    return {
        "fixture_id": _text(item.get("fixture_id") or item.get("match_id") or item.get("external_id") or item.get("id"), 100),
        "competition_id": _text(item.get("competition_id") or item.get("league_id"), 100),
        "season": _text(item.get("season") or item.get("season_id"), 60),
        "home_team_id": _text(item.get("home_team_id") or item.get("home_id"), 100),
        "away_team_id": _text(item.get("away_team_id") or item.get("away_id"), 100),
        "home_team": _text(item.get("home_team") or item.get("client_home") or item.get("home_name"), 120),
        "away_team": _text(item.get("away_team") or item.get("client_away") or item.get("away_name"), 120),
        "competition": _text(item.get("competition_name") or item.get("league_name") or item.get("competition") or item.get("league"), 140),
    }


def _capability_state(item: dict[str, Any], name: str) -> dict[str, Any]:
    explicit_key = f"{name}_available"
    if explicit_key in item:
        available = item.get(explicit_key)
        if available is True:
            return {"state": "AVAILABLE", "available": True, "observed": True, "count": None}
        if available is False:
            return {"state": "UNAVAILABLE", "available": False, "observed": True, "count": None}

    nested = item.get("coverage")
    if isinstance(nested, dict) and name in nested:
        value = nested.get(name)
        if isinstance(value, dict):
            state = _text(value.get("state") or value.get("status"), 40).upper() or "NOT_ESTABLISHED"
            return {
                "state": state,
                "available": value.get("available") if isinstance(value.get("available"), bool) else None,
                "observed": True,
                "count": value.get("count") if isinstance(value.get("count"), int) else None,
            }
        if isinstance(value, bool):
            return {"state": "AVAILABLE" if value else "UNAVAILABLE", "available": value, "observed": True, "count": None}

    payload = item.get(name)
    if isinstance(payload, (list, tuple, set)):
        count = len(payload)
        return {"state": "AVAILABLE" if count else "EMPTY_OBSERVED", "available": bool(count), "observed": True, "count": count}
    if isinstance(payload, dict):
        count = len(payload)
        return {"state": "AVAILABLE" if count else "EMPTY_OBSERVED", "available": bool(count), "observed": True, "count": count}

    return {"state": "NOT_ESTABLISHED", "available": None, "observed": False, "count": None}


def _confidence_state(truth: dict[str, Any], provider: str, observed_at: str) -> str:
    if truth.get("status_conflict"):
        return "CONFLICT"
    if truth.get("is_stale"):
        return "DEGRADED"
    if truth.get("is_live"):
        return "CURRENT" if observed_at else "NOT_ESTABLISHED"
    if provider and observed_at:
        return "OBSERVED"
    return "NOT_ESTABLISHED"


def build_realtime_match_state(item: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Project one provider/cache record into the shared real-time contract.

    The function is pure. Lifecycle and LIVE truth are delegated to
    MATCH-STATUS-TRUTH-V2; this layer only adds identity, provenance, coverage,
    and presentation-safe values.
    """
    source = dict(item or {})
    truth = match_status_truth(source, now=now)
    provider = get_match_source(source)
    clock_field, observed_at, observed_dt = _provider_clock(source)
    evaluated_at = madrid_now(now)
    observed_age_seconds = None
    if observed_dt is not None:
        observed_age_seconds = max(0, int((evaluated_at - observed_dt).total_seconds()))

    home_score, away_score = _score_pair(source)
    kickoff = match_kickoff_madrid(source)
    identity = _identity(source)
    is_live = bool(truth.get("is_live"))

    if truth.get("is_stale"):
        freshness_state = "STALE"
    elif is_live and observed_at:
        freshness_state = "FRESH"
    elif observed_at:
        freshness_state = "OBSERVED"
    else:
        freshness_state = "NOT_ESTABLISHED"

    coverage = {name: _capability_state(source, name) for name in _CAPABILITIES}
    return {
        "contract": REALTIME_STATE_CONTRACT,
        **identity,
        "kickoff_madrid": kickoff.isoformat() if kickoff else "",
        "status_canonical": _text(truth.get("lifecycle"), 40) or "INCOMPLETE",
        "status_raw_canonical": _text(truth.get("raw_lifecycle"), 40) or "INCOMPLETE",
        "is_live": is_live,
        "is_finished": bool(truth.get("is_finished")),
        "is_stale": bool(truth.get("is_stale")),
        "score_home": home_score,
        "score_away": away_score,
        "minute": _minute(source, is_live=is_live),
        "provider": provider,
        "provider_observed_at": observed_at,
        "provider_observed_at_source": clock_field,
        "last_synced_at": _text(source.get("last_synced_at"), 100),
        "freshness_seconds": truth.get("live_age_seconds") if is_live or truth.get("is_stale") else observed_age_seconds,
        "freshness_state": freshness_state,
        "stale_reason": _text(truth.get("stale_reason"), 80),
        "confidence_state": _confidence_state(truth, provider, observed_at),
        "status_conflict": bool(truth.get("status_conflict")),
        "conflict_type": _text(truth.get("conflict_type"), 80),
        "coverage": coverage,
        "evaluated_at_madrid": evaluated_at.isoformat(),
        "sports_truth_contract": _text(truth.get("contract"), 80),
    }


def build_realtime_state_snapshot(items: Iterable[dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
    states = [build_realtime_match_state(item, now=now) for item in (items or [])]
    return {
        "contract": REALTIME_STATE_CONTRACT,
        "evaluated_at_madrid": madrid_now(now).isoformat(),
        "counts": {
            "total": len(states),
            "live": sum(1 for state in states if state["is_live"]),
            "finished": sum(1 for state in states if state["is_finished"]),
            "stale": sum(1 for state in states if state["is_stale"]),
            "conflicted": sum(1 for state in states if state["status_conflict"]),
            "freshness_not_established": sum(1 for state in states if state["freshness_state"] == "NOT_ESTABLISHED"),
        },
        "matches": states,
    }


def compare_realtime_match_state(previous: dict[str, Any] | None, current: dict[str, Any] | None) -> dict[str, Any]:
    """Return factual field changes only; no narrative or betting inference."""
    before = deepcopy(previous or {})
    after = deepcopy(current or {})
    tracked_fields = (
        "status_canonical",
        "is_live",
        "is_finished",
        "is_stale",
        "score_home",
        "score_away",
        "minute",
        "provider_observed_at",
        "freshness_state",
        "status_conflict",
    )
    changes = []
    for field in tracked_fields:
        old = before.get(field)
        new = after.get(field)
        if old != new:
            changes.append({"field": field, "before": old, "after": new})

    fixture_before = _text(before.get("fixture_id"), 100)
    fixture_after = _text(after.get("fixture_id"), 100)
    same_fixture = bool(fixture_before and fixture_after and fixture_before == fixture_after)
    return {
        "contract": REALTIME_CHANGE_CONTRACT,
        "fixture_id": fixture_after or fixture_before,
        "same_fixture": same_fixture,
        "changed": bool(changes) if same_fixture else False,
        "changes": changes if same_fixture else [],
    }
