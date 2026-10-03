"""Startup-only, validated editorial policy. No DB, network or pick decisions."""
from __future__ import annotations

import json
import logging
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[1] / 'config' / 'audience-priority.json'


def load_policy(known_keys, profile='ES_EU', path=DEFAULT_PATH):
    """Return validated overrides; legacy relevance remains the safe fallback.

    A deployment selects a profile; a reviewed config change defines its ranks.
    GLOBAL intentionally retains the existing catalog policy.
    """
    try:
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
        if payload['schema_version'] != 1:
            raise ValueError('Unsupported audience policy schema')
        selected = payload['profiles'][profile]
        if not isinstance(selected['evidence'], list) or not selected['evidence']:
            raise ValueError('Policy requires evidence references')
        rules = selected['rules']
        if not isinstance(rules, list) or len(rules) > 100:
            raise ValueError('Invalid policy rules')
        seen = set()
        for rule in rules:
            if not isinstance(rule, dict) or rule.get('key') not in known_keys or rule['key'] in seen:
                raise ValueError('Unknown or duplicate canonical competition')
            seen.add(rule['key'])
            if type(rule.get('rank')) is not int or not 1 <= rule['rank'] <= 94:
                raise ValueError('Invalid audience rank')
            if not isinstance(rule.get('rationale'), str) or not rule['rationale'].strip():
                raise ValueError('Policy requires an editorial rationale')
        return {'profile': profile, 'rules': rules, 'evidence': selected['evidence'],
                'basis': selected['basis'], 'reviewed_at': selected['reviewed_at']}
    except (OSError, ValueError, KeyError, TypeError):
        logging.getLogger(__name__).warning('Audience policy unavailable or invalid; using catalog relevance')
        return {'profile': 'GLOBAL', 'rules': [], 'evidence': [],
                'basis': 'catalog_fallback', 'reviewed_at': None}


def priority_registry(policy, catalog, legacy_registry):
    """Reuse canonical provider identities and country scopes, never fuzzy names."""
    overrides = []
    for rule in policy['rules']:
        competition = next(item for item in catalog if item['key'] == rule['key'])
        base = next((item for item in legacy_registry if rule['key'] in item.get('keys', [])), None)
        if base is None:
            continue
        # Aliases already recognized by the app are retained in the legacy
        # registry; the canonical name is scoped here to avoid name collisions.
        country = competition['country']
        country_aliases = {'Spain': ['Spain', 'España', 'Espana'],
                           'England': ['England', 'Inglaterra'],
                           'Italy': ['Italy', 'Italia'],
                           'Germany': ['Germany', 'Alemania'],
                           'France': ['France', 'Francia'],
                           'Europe': ['Europe', 'Europa', 'UEFA'],
                           'World': ['World', 'Global', 'International', 'Internacional']}
        aliases = {
            'laliga': ['LaLiga','La Liga','Spanish La Liga'],
            'segunda-division': ['Segunda División','LaLiga 2','Liga Hypermotion'],
            'uefa-champions-league': ['Champions League','UCL'],
            'uefa-europa-league': ['Europa League'],
            'uefa-conference-league': ['Conference League'],
            'fifa-world-cup': ['World Cup','Mundial'],
            'uefa-euro': ['Eurocopa'],
            'supercopa-espana': ['Supercopa de España'],
        }.get(rule['key'], [])
        overrides.append({
            'tier': base['tier'], 'weight': base['weight'], 'rank': rule['rank'],
            'label': base['label'], 'keys': [rule['key']], 'aliases': [],
            'scoped_aliases': {name: country_aliases.get(country, [country])
                               for name in [competition['name'], *aliases]},
        })
    return overrides + legacy_registry
