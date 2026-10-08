"""Pure competition membership and season selection for existing local records.

Strong identifiers are provider scoped. A display-name match cannot overrule a
conflicting identifier. This module never repairs or removes persisted data.
"""
from __future__ import annotations

import re
import unicodedata

from engines.match_sync_engine import IMPORTANT_COMPETITIONS
from engines.spanish_localization_engine import provider_competition_facts, spanish_competition_name, spanish_country_name


def normalized(value):
    return re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()).strip("-")


def provider_family(value):
    value = normalized(value)
    if "sportsdb" in value:
        return "sportsdb"
    if "api-football" in value or "api-sports" in value:
        return "api-football"
    if "odds" in value:
        return "odds"
    return value


def competition_identity(competition):
    item = dict(competition or {})
    identifier = str(item.get("external_id") or item.get("competition_id") or "").strip()
    key = str(item.get("key") or item.get("competition_key") or "").strip()
    provider = provider_family(item.get("source"))
    # The population registry explicitly owns these provider mappings.
    registry = next((row for row in IMPORTANT_COMPETITIONS if row["key"] == key), {})
    if provider in {"population-engine", ""} and identifier:
        if identifier == registry.get("sportsdb_id"):
            provider = "sportsdb"
        elif identifier == registry.get("odds_key"):
            provider = "odds"
    return {
        "id": identifier, "key": normalized(key), "provider": provider,
        "name": normalized(spanish_competition_name(item.get("name") or item.get("competition_name"))),
        "country": normalized(spanish_country_name(item.get("country"))),
    }


def competition_contains(competition, match):
    expected = competition_identity(competition)
    item = dict(match or {})
    identifier = str(item.get("competition_id") or item.get("league_id") or "").strip()
    provider = provider_family(item.get("source") or item.get("provider"))
    country = normalized(spanish_country_name(item.get("country")))
    regional = {"global", "mundo", "world", "europa", "europe", "sudamerica", "south-america", "africa", "asia", "international"}
    if expected["country"] and country and expected["country"] != country and expected["country"] not in regional:
        return False
    if expected["id"] and identifier and expected["provider"] == provider:
        return expected["id"] == identifier
    # Numeric IDs are not shared across providers. Names can bridge feeds only
    # with a matching country; names alone never merge two generic leagues.
    facts = provider_competition_facts(item)
    name = normalized(spanish_competition_name(facts.get("name") or item.get("_raw_competition_name") or item.get("competition_name") or item.get("league_name")))
    key = normalized(item.get("competition_key"))
    same_country = bool(country and country == expected["country"])
    if expected["id"] and identifier and expected["provider"] == "population-engine":
        return False  # Unmapped prepared registry row has no cross-provider proof.
    if same_country and name and name == expected["name"]:
        return True
    return bool(not identifier and key and key == expected["key"] and same_country)


def season_key(value):
    """Provider 2026 and 2026-2027 denote the same season start, not two teams."""
    value = str(value or "").strip()
    if re.fullmatch(r"\d{4}(?:[-/]\d{2,4})?", value):
        return value[:4]
    return value.casefold()


def select_season(matches, requested=""):
    labels = {}
    for item in matches:
        label = str(item.get("season") or "").strip()
        if label:
            key = season_key(label)
            if len(label) > len(labels.get(key, "")):
                labels[key] = label
    options = sorted(labels.values(), key=season_key, reverse=True)
    selected = labels.get(season_key(requested), "") if requested else (options[0] if options else "")
    if requested and not selected:
        return [], "", options
    scoped = [item for item in matches if season_key(item.get("season")) == season_key(selected)] if selected else list(matches)
    return scoped, selected, options
