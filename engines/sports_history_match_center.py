"""Project archived public sports facts into the existing Match Center contracts.

Never restores picks, user information or media access from raw history. Those
remain with the existing authorization and publication surfaces.
"""
from datetime import datetime, timezone
from engines.sports_history_engine import cached_match_details


def _observed(entry):
    value = entry['payload'].get('captured_at') or entry['captured_at']
    try:
        instant = datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return instant.astimezone(timezone.utc).isoformat() if instant.tzinfo else str(value)
    except (ValueError,TypeError):
        return entry['captured_at']


def attach_archived_sports_details(db_path, detail):
    match = detail.get('match') or {}
    identity = match.get('canonical_history_id') or match.get('id')
    if not identity:
        return detail
    entries = cached_match_details(db_path,identity)
    events = []
    lineups = []
    statistics = []
    for entry in entries.get('events') or []:
        payload = entry['payload']
        if str(payload.get('event_type') or payload.get('type') or '').lower() != 'state':
            events.append(dict(payload,source=entry['source']))
    lineup_entries = entries.get('lineups') or []
    if lineup_entries:
        preferred_source = max(lineup_entries,key=_observed)['source']
        lineup_entries = [entry for entry in lineup_entries if entry['source']==preferred_source]
    latest_teams = {}
    for entry in lineup_entries:
        payload = entry['payload']
        team = payload.get('team_id') or payload.get('team_name')
        latest_teams[team] = max(latest_teams.get(team,''),_observed(entry))
    for entry in lineup_entries:
        payload = entry['payload']
        team = payload.get('team_id') or payload.get('team_name')
        if _observed(entry) != latest_teams[team]:
            continue
        if payload.get('confirmed') is not True:
            continue
        players = payload.get('players') or payload.get('starters')
        if isinstance(players,list):
            for player in players:
                if not isinstance(player,dict) or not player.get('id') or not player.get('name'):
                    continue
                lineups.append(dict(player,player_id=player['id'],player_name=player['name'],
                                    team_id=payload.get('team_id'),team_name=payload.get('team_name'),
                                    formation=payload.get('formation'),is_starting=player.get('is_starting') if 'is_starting' in player else bool(payload.get('starters')),
                                    source=entry['source'],captured_at=payload.get('captured_at') or entry['captured_at']))
        elif payload.get('player_id') and payload.get('player_name'):
            lineups.append(dict(payload,source=entry['source']))
    existing_events = detail.get('timeline') or detail.get('events') or []
    if not any(str(event.get('event_type') or event.get('type') or '').lower() not in {'','state'} for event in existing_events):
        if events:
            detail['timeline'] = events
    if not detail.get('lineups') and lineups:
        detail['lineups'] = lineups
    for entry in entries.get('statistics') or []:
        payload = entry['payload']
        if payload.get('items') and isinstance(payload['items'],list):
            statistics.append((_observed(entry),entry['source'],payload['items']))
    raw_stats = [entry for entry in entries.get('statistics') or [] if entry['payload'].get('stat_name')]
    if raw_stats:
        latest = max(raw_stats,key=_observed)
        grouped = {}
        for entry in raw_stats:
            if entry['source']!=latest['source'] or _observed(entry)!=_observed(latest):
                continue
            payload = entry['payload']
            side = next((candidate for candidate in ('home','away') if str(payload.get('team_name') or '').strip().casefold()==str(match.get(candidate+'_team') or '').strip().casefold() and payload.get('team_name')),None)
            if not side or payload.get('stat_value') in (None,'','-','—'):
                continue
            label = str(payload['stat_name'])
            card = grouped.setdefault(label.casefold(),dict(key=label.casefold().replace(' ','_'),label=label,home=None,away=None,leader='even'))
            card[side] = payload['stat_value']
        if grouped:
            statistics.append((_observed(latest),latest['source'],list(grouped.values())))
    if not (detail.get('cached_statistics') or {}).get('available') and statistics:
        captured,source,items = max(statistics,key=lambda entry:entry[0])
        detail['cached_statistics'] = dict(available=True,items=items,source=source,updated_at=captured,external_calls=0)
    return detail
