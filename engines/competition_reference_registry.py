"""Closed, versioned competition references, never a fixture/team alias service.

The sources independently identify the Spanish men's top football division.
Their equivalence below is a reviewed local inference, not a provider-published
cross-ID bridge. No display-name matching or season completion is performed.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import re

from engines.competition_read_model import normalized
from engines.spanish_localization_engine import spanish_country_name


@dataclass(frozen=True)
class ProviderCompetitionReference:
    version: str
    canonical_key: str
    provider: str
    native_id: str
    observed_keys: tuple[str, ...]
    country: str
    sport: str
    gender: str
    season_policy: str
    counterpart_ids: tuple[tuple[str, str], ...]
    sources: tuple[tuple[str, str], ...]
    inference: str


CURATED_COMPETITION_REFERENCES = (
    ProviderCompetitionReference(
        version="2026-10-26.laliga.1", canonical_key="laliga",
        provider="api-football", native_id="140",
        observed_keys=("la-liga-spain",), country="Spain",
        sport="Soccer", gender="Male", season_policy="API_START_YEAR_REQUIRED",
        counterpart_ids=(("sportsdb", "4335"),),
        sources=(
            ("https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide",
             "La Liga has native ID 140; spanning seasons use their starting year."),
            ("https://www.api-football.com/coverage",
             "La Liga is listed under Spain, separately from Primera Division Femenina."),
            ("https://www.thesportsdb.com/league/4335",
             "Spanish La Liga; Soccer; Spain; Male; season 2026-2027."),
        ),
        inference="CURATED_SAME_DIVISION_FROM_INDEPENDENT_PRIMARY_IDENTITIES_NOT_DIRECT_CROSS_ID",
    ),
)


def explicit_competition_reference(namespace, native_ids, explicit_key):
    """Only an exact provider/ID/key triple can select this reviewed relation."""
    matches = tuple(reference for reference in CURATED_COMPETITION_REFERENCES
                    if namespace == reference.provider
                    and native_ids == (reference.native_id,)
                    and explicit_key in reference.observed_keys)
    return matches[0] if len(matches) == 1 else None


def _text(value):
    return str(value).strip() if type(value) in {str, int} else ""


def _sport(value):
    value = normalized(value)
    return "soccer" if value in {"soccer", "football", "association-football", "futbol"} else value


def _gender_conflict(value):
    words = set(normalized(value).split("-"))
    return bool(words & {"female", "femenina", "femenino", "women", "woman", "ladies", "w"})


def _scope_conflicts(reference, item):
    issues = set()
    for field in ("sport", "sport_name", "sport_key", "strSport"):
        if _text(item.get(field)) and _sport(item[field]) != _sport(reference.sport):
            issues.add("CONFLICT_REFERENCE_SPORT")
    for field in ("gender", "strGender", "competition_name", "league_name", "name"):
        if _gender_conflict(item.get(field)):
            issues.add("CONFLICT_REFERENCE_GENDER")
    for field in ("gender", "strGender"):
        gender = normalized(item.get(field))
        if gender and gender not in {"male", "men", "masculino", "masculina"} and not _gender_conflict(gender):
            issues.add("UNKNOWN_REFERENCE_SCOPE_GENDER")
    for field in ("category", "age_group"):
        value = normalized(item.get(field))
        if value and value not in {"male", "men", "senior", "seniors", "first-team"}:
            issues.add("CONFLICT_REFERENCE_CATEGORY")
    country = _text(item.get("country"))
    if country and normalized(spanish_country_name(country)) != normalized(spanish_country_name(reference.country)):
        issues.add("CONFLICT_COUNTRY")
    return issues


def observation_reference_issues(reference, row):
    """Require local sport/country/season evidence; contradictory raw facts win.

    Gender is the independently documented native league's category when absent.
    Any explicit women's/category evidence contradicts that category. No season
    is inferred for another provider or copied back to the observation.
    """
    # These are the same row identity inputs captured by the snapshot guard.
    # Arbitrary provider metadata must not silently become a new identity input.
    scope_fields = ("sport", "sport_name", "sport_key", "gender", "category", "age_group",
                    "competition_name", "league_name", "country")
    issues = _scope_conflicts(reference, {field: row.get(field) for field in scope_fields})
    if not any(_text(row.get(field)) for field in ("sport", "sport_name", "sport_key")):
        issues.add("UNKNOWN_REFERENCE_SCOPE_SPORT")
    if not _text(row.get("country")):
        issues.add("UNKNOWN_REFERENCE_SCOPE_COUNTRY")
    season = _text(row.get("season"))
    if not re.fullmatch(r"[1-9]\d{3}", season):
        issues.add("UNKNOWN_REFERENCE_SCOPE_SEASON")
    raw = row.get("raw_json") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            issues.add("UNKNOWN_REFERENCE_PAYLOAD")
            raw = {}
    if not isinstance(raw, Mapping):
        issues.add("UNKNOWN_REFERENCE_PAYLOAD")
    elif raw:
        league = raw.get("league")
        if not isinstance(league, Mapping):
            issues.add("UNKNOWN_REFERENCE_PAYLOAD")
        elif _text(league.get("id")) != reference.native_id:
            issues.add("CONFLICT_REFERENCE_PAYLOAD_ID")
        else:
            # API's documented league identity projection is id/name/country/
            # season. Sport and gender above belong to the guarded row scope.
            issues.update(_scope_conflicts(reference, {field: league.get(field) for field in ("name", "country")}))
            raw_season = _text(league.get("season"))
            if raw_season and (not re.fullmatch(r"[1-9]\d{3}", raw_season) or raw_season != season):
                issues.add("CONFLICT_REFERENCE_SEASON")
            elif league.get("season") not in (None, "") and not raw_season:
                issues.add("UNKNOWN_REFERENCE_PAYLOAD_SEASON")
    return tuple(sorted(issues))


def catalog_reference_issues(reference, key, country, namespace, native_id, scope):
    """An existing alternate PK is evidence to verify, never a row to hide."""
    issues = _scope_conflicts(reference, dict(scope))
    if country and country != normalized(spanish_country_name(reference.country)):
        issues.add("CONFLICT_COUNTRY")
    expected = dict(reference.counterpart_ids)
    expected[reference.provider] = reference.native_id
    if namespace in expected and native_id and native_id != expected[namespace]:
        issues.add("CONFLICT_REFERENCE_NATIVE_ID")
    if key != reference.canonical_key:
        if namespace in {"sportsdb", "odds", "api-football"} and namespace != reference.provider:
            issues.add("CONFLICT_ALIAS_REFERENCE_NAMESPACE")
        elif namespace != reference.provider or native_id != reference.native_id:
            issues.add("UNKNOWN_ALIAS_REFERENCE")
    elif not ((namespace in expected and native_id == expected[namespace])
              or (namespace == "population-engine" and native_id == expected.get("sportsdb"))):
        issues.add("UNKNOWN_CANONICAL_REFERENCE_IDENTITY")
    return tuple(sorted(issues))
