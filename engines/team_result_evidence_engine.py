"""Pure Team Center result summaries over records already loaded by the caller.

This is a presentation adapter, not a provider, season backfill, or new lifecycle.
The shared Sports Truth owns finality. Coverage is always a loaded sample.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from datetime import timezone
from typing import Any, Mapping
from urllib.parse import quote

from engines.spanish_localization_engine import parse_datetime_to_madrid
from engines.v935_launch_trust_engine import match_status_truth

CONTRACT = "TEAM-RESULT-EVIDENCE-V1"


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def score_number(value: Any) -> int | None:
    """Accept whole, nonnegative scores, including zero; never truncate a float."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 0 <= value <= 999 else None
    if isinstance(value, float):
        return int(value) if math.isfinite(value) and value.is_integer() and 0 <= value <= 999 else None
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,3}", value.strip()):
        return int(value.strip())
    return None


def _pair(match: Mapping[str, Any]) -> tuple[int, int] | None:
    values = [match.get("home_score"), match.get("away_score")]
    parsed = [score_number(value) for value in values]
    # A malformed explicit component cannot be replaced by an older text score.
    if any(value is not None and _text(value) != "" and number is None
           for value, number in zip(values, parsed)):
        return None
    text = re.fullmatch(r"([0-9]{1,3})\s*[-:\u2013]\s*([0-9]{1,3})", _text(match.get("score")))
    fallback = tuple(map(int, text.groups())) if text else None
    if fallback and any(number is not None and number != fallback[index]
                        for index, number in enumerate(parsed)):
        return None
    if all(number is not None for number in parsed):
        return parsed[0], parsed[1]
    return fallback


def result_for_team(match: Mapping[str, Any], team_name: str) -> dict[str, Any]:
    """Describe a final score, not a live lead or a knockout qualification."""
    unavailable = {
        "available": False, "outcome": "No disponible", "goals_for": None,
        "goals_against": None, "limitation": "El marcador final o el lado del equipo no están confirmados.",
    }
    if any(_text(match.get(key)).casefold() in {"true", "1", "yes"}
           for key in ("is_fake", "is_demo", "simulated")):
        return {**unavailable, "reason": "non_production_record"}
    name = _text(team_name).casefold()
    home = _text(match.get("home_team") or match.get("safe_home")).casefold()
    away = _text(match.get("away_team") or match.get("safe_away")).casefold()
    if not name or not home or not away or home == away or name not in {home, away}:
        return {**unavailable, "reason": "team_unverified"}
    if not match_status_truth(dict(match)).get("is_finished"):
        return {**unavailable, "reason": "not_confirmed_final"}
    pair = _pair(match)
    if pair is None:
        return {**unavailable, "reason": "score_unverified"}
    side = "home" if home == name else "away"
    goals_for, goals_against = pair if side == "home" else pair[::-1]
    return {
        "available": True, "side": side, "goals_for": goals_for, "goals_against": goals_against,
        "outcome": "Victoria" if goals_for > goals_against else "Derrota" if goals_for < goals_against else "Empate",
        "home_score": pair[0], "away_score": pair[1],
        "score_scope": "recorded_final_score_not_qualification",
    }


def _kickoff(match: Mapping[str, Any]):
    value = match.get("kickoff_iso")
    if not value and match.get("match_date") and (match.get("kickoff_time") or match.get("match_time")):
        value = f"{_text(match['match_date'])[:10]}T{_text(match.get('kickoff_time') or match.get('match_time'))}"
    try:
        parsed = parse_datetime_to_madrid(value) if value else None
        return parsed.astimezone(timezone.utc) if parsed else None
    except (ValueError, TypeError, OverflowError):
        return None


def _provider(match: Mapping[str, Any]) -> str:
    source = _text(match.get("source") or match.get("provider")).casefold()
    if "sportsdb" in source:
        return "sportsdb"
    if "api_football" in source or "api-football" in source or "api football" in source:
        return "api-football"
    return source


def _scope(match: Mapping[str, Any]) -> tuple[str, str, str, str]:
    identity = match.get("competition_identity")
    identity = identity if isinstance(identity, Mapping) else {}
    provider = _provider(match)
    competition = _text(match.get("competition_id") or identity.get("provider_id") or identity.get("canonical_id"))
    name = _text(match.get("competition_name") or match.get("league_name") or identity.get("display_name"))
    # A name-only bucket is explicitly unverified, never merged with a numeric ID.
    scope_id = "id:" + competition if competition else "name:" + name.casefold()
    country = _text(match.get("country") or identity.get("country")).casefold()
    return provider, scope_id, _text(match.get("season")), country


def _totals(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "sample_size": len(items),
        "wins": sum(item["outcome"] == "Victoria" for item in items),
        "draws": sum(item["outcome"] == "Empate" for item in items),
        "losses": sum(item["outcome"] == "Derrota" for item in items),
        "goals_for": sum(item["goals_for"] for item in items),
        "goals_against": sum(item["goals_against"] for item in items),
    }


def build_team_result_evidence(matches: Any, team_name: str) -> dict[str, Any]:
    """Sort final results and group the loaded sample by provider/league/season.

    Ambiguous duplicate records are withheld, not repaired or timestamped here.
    No round number or number of loaded rows is promoted to a season total.
    """
    rows = [dict(row) for row in matches if isinstance(row, Mapping)] if isinstance(matches, (list, tuple)) else []
    rejected: Counter[str] = Counter()
    buckets: dict[tuple, list[dict[str, Any]]] = {}
    for row in rows:
        local_id = _text(row.get("id") or row.get("match_id"))
        provider = _provider(row)
        fixture_id = _text(row.get("external_id") or row.get("fixture_id"))
        key = ("provider", provider, fixture_id) if provider and fixture_id else ("local", local_id)
        if not local_id and not (provider and fixture_id):
            rejected["identity_missing"] += 1
            continue
        buckets.setdefault(key, []).append(row)
    items = []
    for duplicates in buckets.values():
        observations = [(row, result_for_team(row, team_name), _kickoff(row)) for row in duplicates]
        signatures = {
            (_scope(row), _text(row.get("home_team") or row.get("safe_home")).casefold(),
             _text(row.get("away_team") or row.get("safe_away")).casefold(),
             result.get("available"), result.get("outcome"), result.get("goals_for"),
             result.get("goals_against"), date)
            for row, result, date in observations
        }
        if len(signatures) != 1:
            rejected["conflicting_records"] += len(duplicates)
            continue
        row, result, date = observations[0]
        if not result["available"]:
            rejected[result["reason"]] += len(duplicates)
            continue
        if date is None:
            rejected["date_unverified"] += len(duplicates)
            continue
        rejected["duplicate_rows"] += len(duplicates) - 1
        local_id = _text(row.get("id") or row.get("match_id"))
        items.append({
            "match": row, **result, "kickoff": date.isoformat(),
            "date_label": parse_datetime_to_madrid(date.isoformat()).strftime("%d/%m/%Y %H:%M"),
            "href": "/match/" + quote(local_id, safe="") if local_id else None,
        })
    items.sort(key=lambda item: (item["kickoff"], _text(item["match"].get("id"))), reverse=True)
    grouped: dict[tuple, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(_scope(item["match"]), []).append(item)
    groups = []
    for (provider, competition_id, season, country), members in grouped.items():
        first = members[0]["match"]
        identity = first.get("competition_identity") or {}
        identity = identity if isinstance(identity, Mapping) else {}
        groups.append({
            "competition": _text(first.get("competition_name") or first.get("league_name") or identity.get("display_name")),
            "season": season, "provider": provider, "country": country,
            "scope_identified": bool(provider and season and competition_id != "id:" and competition_id.startswith("id:")),
            "totals": _totals(members),
            "home": _totals([item for item in members if item["side"] == "home"]),
            "away": _totals([item for item in members if item["side"] == "away"]),
            "items": members,
        })
    return {
        "contract": CONTRACT, "available": bool(items), "items": items, "groups": groups,
        "input_count": len(rows), "included_count": len(items), "omitted_count": sum(rejected.values()),
        "omission_reasons": {key: value for key, value in rejected.items() if value},
        "coverage_state": "LOADED_SAMPLE_ONLY", "season_complete": False,
        "expected_played": None, "external_calls": 0, "database_writes": 0,
    }
