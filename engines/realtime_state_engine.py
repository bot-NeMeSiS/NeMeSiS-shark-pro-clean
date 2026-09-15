"""Canonical read-only real-time projection for NeMeSiS sports surfaces.

This module deliberately does not open databases, call providers, mutate inputs,
or decide lifecycle independently. MATCH-STATUS-TRUTH-V2 remains the authority.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from math import isfinite
import re
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
    # Match Sports Truth precedence, including an invalid first-present clock.
    # Skipping an invalid priority clock would invent fallback provenance.
    for field in _PROVIDER_CLOCK_FIELDS:
        value = item.get(field)
        if value not in (None, "", "None", "null", "undefined"):
            parsed = _parse_iso(value)
            return field, _text(value, 100) if parsed is not None else "", parsed
    return "", "", None


def _score_value(value: Any) -> int | float | None:
    if value in (None, "", "None", "null", "undefined"):
        return None
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    if not isfinite(number) or number < 0:
        return None
    return int(number) if number.is_integer() else number


def _score_pair(item: dict[str, Any]) -> tuple[int | float | None, int | float | None]:
    home = _score_value(item.get("home_score"))
    away = _score_value(item.get("away_score"))
    # Explicit invalid numeric evidence remains unknown. A cached display
    # string must not silently resurrect a rejected NaN/Infinity/invalid pair.
    if any(item.get(key) not in (None, "", "None", "null", "undefined")
           for key in ("home_score", "away_score")):
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
        value = item.get(field)
        normalized = str(value).strip().strip("'’") if value is not None else ""
        if re.fullmatch(r"[0-9]{1,3}", normalized) and int(normalized) <= 130:
            extra = item.get("extra") or item.get("stoppage_time")
            suffix = str(extra).strip() if extra is not None else ""
            return f"{int(normalized)}+{suffix}" if re.fullmatch(r"[0-9]{1,2}", suffix) else str(int(normalized))
        if re.fullmatch(r"[0-9]{1,3}\+[0-9]{1,2}", normalized) and int(normalized.split("+", 1)[0]) <= 130:
            return normalized
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


def _coverage_result(state: str = "NOT_ESTABLISHED", available: bool | None = None,
                     observed: bool = False, count: int | None = None) -> dict[str, Any]:
    return dict(state=state, available=available, observed=observed, count=count)


def _coverage_descriptor(value: dict[str, Any]) -> dict[str, Any]:
    """Project declared capability metadata, never the number of its keys.

    Availability is not a claim about completeness/freshness. Conflicting or
    malformed declarations fail to unknown; operational states stay explicit.
    """
    status = _text(value.get("state") or value.get("status"), 40).upper()
    available, observed, count = value.get("available"), value.get("observed"), value.get("count")
    if status == "NOT_REQUESTED":
        return _coverage_result("NOT_REQUESTED")
    if observed is False or (observed is not None and type(observed) is not bool):
        return _coverage_result()
    if available is not None and type(available) is not bool:
        return _coverage_result()
    if count is not None and (type(count) is not int or count < 0):
        return _coverage_result()
    if status in {"NOT_ESTABLISHED", "UNKNOWN"}:
        return _coverage_result()
    if status in {"UNAVAILABLE", "ACCESS_FAILED", "UNSUPPORTED"}:
        return _coverage_result() if available is True else _coverage_result(status, False, True)
    if status in {"PARTIAL", "STALE"}:
        return _coverage_result(status, available, True, count)
    if status == "EMPTY_OBSERVED":
        if available is True or count not in (None, 0):
            return _coverage_result()
        return _coverage_result(status, False, True, 0)
    rows = value.get("data", value.get("response"))
    if isinstance(rows, (list, tuple, set)):
        if count is not None and count != len(rows):
            return _coverage_result()
        count = len(rows)
    if status == "AVAILABLE":
        if available is not True or count == 0:
            return _coverage_result()
        return _coverage_result(status, True, True, count)
    if status:
        return _coverage_result()
    if available is False:
        return _coverage_result("UNAVAILABLE", False, True)
    if available is True and count != 0:
        return _coverage_result("AVAILABLE", True, True, count)
    return _coverage_result()


def _capability_state(item: dict[str, Any], name: str) -> dict[str, Any]:
    payload = item.get(name)
    nested = item.get("coverage")
    explicit = item.get(f"{name}_available")
    descriptor_keys = {"state", "status", "available", "observed", "count", "error", "errors"}
    # Explicit coverage/operational metadata wins over payload shape. A global
    # positive flag may not turn NOT_REQUESTED into an observed lineup.
    if isinstance(nested, dict) and name in nested:
        value = nested[name]
        if isinstance(value, dict):
            result = _coverage_descriptor(value)
        elif type(value) is bool:
            result = _coverage_result("AVAILABLE" if value else "UNAVAILABLE", value, True)
        else:
            result = _coverage_result()
    elif isinstance(payload, dict) and descriptor_keys.intersection(payload):
        result = _coverage_descriptor(payload)
    elif type(explicit) is bool:
        result = _coverage_result("AVAILABLE" if explicit else "UNAVAILABLE", explicit, True)
    else:
        # Only explicit row sequences/wrappers prove observed content. An
        # arbitrary metadata dict is not a lineup and is not counted as rows.
        rows = payload
        if isinstance(payload, dict):
            rows = payload.get("data", payload.get("response"))
        if isinstance(rows, (list, tuple, set)):
            count = len(rows)
            result = _coverage_result("AVAILABLE" if count else "EMPTY_OBSERVED", bool(count), True, count)
        else:
            result = _coverage_result()
    if result["available"] is True:
        if explicit is False:
            return _coverage_result()
        if isinstance(nested, dict) and name in nested and isinstance(payload, dict) and descriptor_keys.intersection(payload):
            # Positive metadata cannot override an explicit unavailable payload.
            if _coverage_descriptor(payload)["available"] is not True:
                return _coverage_result()
        rows = payload.get("data", payload.get("response")) if isinstance(payload, dict) else payload
        if isinstance(rows, (list, tuple, set)):
            if not rows or (result["count"] is not None and result["count"] != len(rows)):
                return _coverage_result()
            result["count"] = len(rows)
    return result


def _confidence_state(truth: dict[str, Any], provider: str, observed_at: str) -> str:
    if truth.get("status_conflict"):
        return "CONFLICT"
    if truth.get("is_stale"):
        return "DEGRADED"
    if truth.get("is_live"):
        return "CURRENT" if provider and observed_at else "NOT_ESTABLISHED"
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
    evaluated_at = madrid_now(now)
    truth = match_status_truth(source, now=evaluated_at)
    provider = get_match_source(source)
    clock_field, observed_at, observed_dt = _provider_clock(source)
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
    evaluated_at = madrid_now(now)
    states = [build_realtime_match_state(item, now=evaluated_at) for item in (items or [])]
    return {
        "contract": REALTIME_STATE_CONTRACT,
        "evaluated_at_madrid": evaluated_at.isoformat(),
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
