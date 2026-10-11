"""Shared client display ranks. Startup config only; no IO while ordering rows.

The owner chooses Spanish professional competitions first. This does not change
provider weights, qualification, match truth, scores, picks or authorization.
Numeric IDs require their provider; ambiguous names require their country.
"""
from collections.abc import Mapping
import math
import os
import re
import unicodedata

from engines.audience_priority_policy import load_policy, priority_registry
from engines.match_sync_engine import IMPORTANT_COMPETITIONS


def _norm(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    return re.sub(r'[^a-z0-9]+', '-', text.encode('ascii', 'ignore').decode().lower()).strip('-')


_POLICY = load_policy({row['key'] for row in IMPORTANT_COMPETITIONS},
                      profile=os.environ.get('NEMESIS_AUDIENCE_PROFILE', 'ES_EU'))
# Reuse the existing alias/country policy, instead of matching team or league substrings.
_BASE = [{'keys':[row['key']], 'tier':'DISPLAY', 'weight':0, 'rank':95, 'label':''}
         for row in IMPORTANT_COMPETITIONS]
_CONFIGS = priority_registry(_POLICY, IMPORTANT_COMPETITIONS, _BASE)[:len(_POLICY['rules'])]
def _compile_display_rules():
    compiled = []
    for config in _CONFIGS:
        catalog = next(row for row in IMPORTANT_COMPETITIONS if row['key'] == config['keys'][0])
        aliases = {_norm(name): frozenset(_norm(country) for country in scopes)
                   for name, scopes in config['scoped_aliases'].items()}
        compiled.append((config['rank'], catalog, aliases, frozenset().union(*aliases.values())))
    return tuple(compiled)


_RULES = _compile_display_rules()


def spanish_first_enabled():
    return _POLICY['profile'] == 'ES_EU'


def _rank(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 999 and math.isfinite(value) else 95


def competition_display_rank(match, fallback=95):
    """Use the same ES_EU config as Calendar; never mutate or relabel a fixture."""
    fallback = _rank(fallback)
    if not spanish_first_enabled() or not isinstance(match, Mapping):
        return fallback
    sport = _norm(match.get('sport') or match.get('sport_name'))
    if sport and sport not in {'soccer', 'football', 'futbol', 'association-football'}:
        return fallback
    country = next((match.get(key) for key in ('country','league_country','competition_country','calendar_country','safe_country')
                    if str(match.get(key) or '').strip()), '')
    countries = {_norm(country)} - {''}
    names = {_norm(match.get(key)) for key in ('competition_name','league_name','calendar_competition','client_competition','safe_competition')} - {''}
    keys = {_norm(match.get(key)) for key in ('competition_key','league_key','calendar_competition_key')} - {''}
    ids = {str(match.get(key) or '').strip() for key in ('competition_id','league_id')} - {''}
    source = _norm(match.get('provider') or match.get('source'))
    family = 'sportsdb' if 'sportsdb' in source else 'odds' if 'odds' in source else ''
    for rank, catalog, aliases, allowed_countries in _RULES:
        if countries and not countries.intersection(allowed_countries):
            continue
        provider_id = catalog.get('sportsdb_id' if family == 'sportsdb' else 'odds_key') if family else ''
        if provider_id and ids:
            if str(provider_id) in ids:
                return rank
            # A provider ID for a different competition cannot inherit a familiar name.
            continue
        if not countries.intersection(allowed_countries):
            continue
        if _norm(catalog['key']) in keys or any(name in names and countries.intersection(scopes) for name, scopes in aliases.items()):
            return rank
    return fallback


def live_display_key(match):
    """Stable within a league: preserve the existing order of equally ranked rows."""
    relevance = match.get('sports_relevance') or {}
    fallback = relevance.get('competition_rank', match.get('calendar_rank', 95)) if isinstance(relevance, Mapping) else 95
    return competition_display_rank(match, fallback)
