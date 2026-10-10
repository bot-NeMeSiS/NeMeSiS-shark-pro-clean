"""Bounded league-by-league Home agenda over an existing snapshot; no IO."""
from collections import deque
from collections.abc import Mapping
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
from zoneinfo import ZoneInfo

from engines.crest_engine import normalize_logo_key
from engines.league_badge_read_model import badge_url, match_badge

MADRID = ZoneInfo('Europe/Madrid')
DEFAULT_LIMITS = {'live': 12, 'today': 48, 'upcoming': 12, 'results': 12}


def _local(value):
    if value is None:
        return None
    return value.replace(tzinfo=MADRID) if value.tzinfo is None else value.astimezone(MADRID)


def _identity(match, identity_for):
    supplied = identity_for(match) if identity_for else {}
    supplied = supplied if isinstance(supplied, Mapping) else {}
    name = str(supplied.get('display_name') or match.get('calendar_competition') or
               match.get('competition_name') or match.get('league_name') or '').strip()
    country = str(supplied.get('country') or match.get('country') or match.get('safe_country') or '').strip()
    key = str(supplied.get('group_key') or match.get('client_competition_id') or
              match.get('calendar_competition_id') or match.get('competition_key') or '').strip()
    provider = str(match.get('provider') or match.get('source') or '').strip()
    identifier = str(supplied.get('provider_id') or match.get('competition_id') or match.get('league_id') or '')
    if not key:
        # Provider IDs are not globally unique, and a generic league name is not an ID.
        key = provider + ':' + identifier if identifier else name
    season = str(supplied.get('season') or match.get('season') or '')
    sport = str(match.get('sport') or match.get('sport_name') or '')
    identity = tuple(normalize_logo_key(value) for value in (key, country, season, sport))
    digest = sha256('\x1f'.join(identity).encode()).hexdigest()
    raw_name = str(match.get('_raw_competition_name') or match.get('competition_official_name') or name)
    return identity, {
        'competition': name, 'country': country, 'season': season,
        'key': key, 'anchor': 'league-' + digest[:14], 'tone': int(digest[:8], 16) % 6,
        'route_id': supplied.get('route_id') or match.get('competition_key') or identifier or name,
        'logo_key': normalize_logo_key(raw_name), 'logo_name': raw_name,
        'provider': provider, 'provider_id': identifier, 'logo_url': '',
    }


def build_matchday(matches, *, now, status_for, kickoff_for, priority_for, limit=None, identity_for=None):
    """Reserve space across peers, then render each league as one contiguous block.

    Today uses up to 48 cached matches. Other lanes stay at 12. An explicit
    integer limit retains the previous all-lanes contract. No provider query,
    database read, shared-snapshot mutation or invented match is permitted here.
    """
    limits = DEFAULT_LIMITS.copy()
    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 200:
            raise ValueError('limit must be an integer between 0 and 200')
        limits = dict.fromkeys(limits, limit)
    now = _local(now)
    lanes = {name: {} for name in limits}
    seen = set()
    for match in matches or []:
        if not isinstance(match, Mapping):
            continue
        identifier = str(match.get('id') or '').strip()
        if not identifier or identifier in seen:
            continue
        status = status_for(match)
        kickoff = _local(kickoff_for(match))
        if status.get('is_stale') or status.get('status_conflict'):
            continue
        if status.get('is_live'):
            lane = 'live'
        elif status.get('is_upcoming') and kickoff and kickoff >= now:
            lane = 'today' if kickoff.date() == now.date() else 'upcoming'
        elif status.get('is_finished') and kickoff and now - timedelta(days=2) <= kickoff <= now:
            lane = 'results'
        else:
            continue
        seen.add(identifier)
        identity, metadata = _identity(match, identity_for)
        day = (kickoff or now).date().isoformat()
        group_key = (day, identity)
        rank = priority_for(match).get('rank', 95)
        group = lanes[lane].setdefault(group_key, dict(metadata, date=day, rank=rank, rows=[]))
        group['rank'] = min(group['rank'], rank)
        # A later fixture may carry the badge missing from the first fixture.
        group['logo_url'] = group['logo_url'] or match_badge(match)
        stamp = kickoff.timestamp() if kickoff else 0
        group['rows'].append((stamp, identifier, match, dict(status)))

    result = {'date': now.date().isoformat()}
    for lane, groups in lanes.items():
        total = sum(len(group['rows']) for group in groups.values())
        selected = {}
        shown = 0
        for day in sorted({key[0] for key in groups}, reverse=lane == 'results'):
            keys = [key for key in groups if key[0] == day]
            for key in keys:
                groups[key]['rows'].sort(key=lambda row: (-row[0] if lane == 'results' else row[0], row[1]))
            for rank in sorted({groups[key]['rank'] for key in keys}):
                peers = sorted((key for key in keys if groups[key]['rank'] == rank),
                               key=lambda key: (groups[key]['competition'].casefold(), key))
                queues = {key: deque(groups[key]['rows']) for key in peers}
                while any(queues.values()) and shown < limits[lane]:
                    for key in peers:
                        if queues[key] and shown < limits[lane]:
                            selected.setdefault(key, []).append(queues[key].popleft())
                            shown += 1
            if shown >= limits[lane]:
                break
        sections = []
        for day in sorted({key[0] for key in selected}, reverse=lane == 'results'):
            for key in sorted((key for key in selected if key[0] == day),
                              key=lambda key: (groups[key]['rank'], groups[key]['competition'].casefold(), key)):
                group = groups[key]
                section = {k: v for k, v in group.items() if k not in {'rows', 'rank'}}
                section['matches'] = []
                for _, _, match, status in selected[key]:
                    item = deepcopy(match)
                    item['status_info'] = status
                    section['matches'].append(item)
                section.update(shown=len(section['matches']), total=len(group['rows']))
                section['logo_url'] = badge_url(section['logo_url'])
                sections.append(section)
        result[lane] = {'groups': sections, 'shown': shown, 'total': total,
                        'has_more': total > shown, 'limit': limits[lane],
                        'competition_count': len(groups)}
    return result
