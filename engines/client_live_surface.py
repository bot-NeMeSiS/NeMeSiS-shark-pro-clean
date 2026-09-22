"""Directo is a live-only surface, not an empty-list agenda fallback.

Pure projection of the existing read model; no provider, DB or inferred scores.
Explicit historical bookmarks remain labelled historical, never 'Ahora mismo'.
"""
from engines.v935_launch_trust_engine import match_status_truth


def live_surface(data, lane='live', *, now=None):
    source = (data or {}).get('live_experience') or {}
    lane = str(source.get('lane') or lane or 'live').lower()
    lane = {'all':'live', 'directo':'live', 'descanso':'break', 'halftime':'break',
            'picks':'with_pick', 'finalizados':'finished'}.get(lane, lane)
    if lane not in {'live','break','with_pick','finished'}:
        lane = 'live'
    records = list(source.get('matches') or [])
    if not records:
        for day in source.get('day_groups') or []:
            for league in day.get('leagues') or []:
                records.extend(league.get('matches') or [])
    accepted, seen = [], set()
    for row in records:
        if not isinstance(row,dict):
            continue
        identity = str(row.get('id') or row.get('match_id') or '')
        if not identity or identity in seen:
            continue
        truth = match_status_truth(row, now=now)
        confirmed = truth.get('is_live') is True and not truth.get('is_stale') and not truth.get('status_conflict')
        if lane == 'finished':
            allowed = truth.get('is_finished') is True and not truth.get('status_conflict')
        else:
            allowed = confirmed
            if lane == 'break':
                allowed = allowed and truth.get('lifecycle') == 'HALFTIME'
            # The route already scopes with_pick by the canonical published-pick IDs.
            # Do not reinterpret a missing presentation flag as absence of that pick.
        if allowed:
            seen.add(identity)
            accepted.append(dict(row))
    return {'contract':'NEMESIS-DIRECTO-LIVE-ONLY-V1','lane':lane, 'matches':accepted,
            'title':'Resultados finalizados' if lane == 'finished' else 'Ahora mismo',
            'historical':lane == 'finished','external_calls':0}
