"""Home presentation over an existing sports snapshot. No IO or shared state."""
from copy import deepcopy
from datetime import timedelta


def build_matchday(matches, *, now, status_for, kickoff_for, priority_for, limit=12):
    """Live first; share bounded space across competitions of the same tier.

    A busy domestic league must not displace every other major league. This
    changes presentation only, never provider scope, ranking policy or quotas.
    """
    lanes = {name: [] for name in ('live', 'today', 'upcoming', 'results')}
    seen = set()
    for match in matches:
        identity = str(match.get('id') or '')
        if not identity or identity in seen:
            continue
        seen.add(identity)
        status = status_for(match)
        kickoff = kickoff_for(match)
        if status.get('is_live') and not status.get('is_stale') and not status.get('status_conflict'):
            lane = 'live'
        elif status.get('is_upcoming') and kickoff and kickoff >= now:
            lane = 'today' if kickoff.date() == now.date() else 'upcoming'
        elif status.get('is_finished') and kickoff and now - timedelta(days=2) <= kickoff <= now:
            lane = 'results'
        else:
            continue
        name = str(match.get('calendar_competition') or match.get('competition_name') or match.get('league_name') or '')
        country = str(match.get('country') or match.get('safe_country') or '')
        competition = str(match.get('competition_key') or match.get('competition_id') or name)
        rank = priority_for(match).get('rank', 95)
        stamp = kickoff.timestamp() if kickoff else 0
        day = kickoff.date().isoformat() if kickoff else now.date().isoformat()
        lanes[lane].append((day, rank, competition, country, name, stamp, identity, match, status))

    result = {'date': now.date().isoformat()}
    for lane, rows in lanes.items():
        # Choose nearest date first; finished dates run backwards. Within each
        # date, reserve a place per competition before taking its next fixture.
        by_day = {}
        for row in rows:
            by_day.setdefault(row[0], []).append(row)
        chosen = []
        for day in sorted(by_day, reverse=lane == 'results'):
            groups = {}
            for row in sorted(by_day[day], key=lambda r: (-r[5] if lane == 'results' else r[5], r[6])):
                groups.setdefault((row[1], row[2], row[3], row[4]), []).append(row)
            for rank in sorted({key[0] for key in groups}):
                queues = [groups[key] for key in sorted(groups) if key[0] == rank]
                while any(queues) and len(chosen) < limit:
                    for queue in queues:
                        if queue and len(chosen) < limit:
                            chosen.append(queue.pop(0))
            if len(chosen) >= limit:
                break
        ordered = {}
        for row in chosen:
            item = deepcopy(row[7])
            item['status_info'] = dict(row[8])
            ordered.setdefault((row[0], row[1], row[2], row[3], row[4]), []).append(item)
        sections = []
        days = sorted({key[0] for key in ordered}, reverse=lane == 'results')
        for day in days:
            for key in sorted(key for key in ordered if key[0] == day):
                sections.append({'date': day, 'competition': key[4], 'country': key[3], 'matches': ordered[key]})
        result[lane] = {'groups': sections, 'shown': len(chosen), 'total': len(rows), 'has_more': len(rows) > len(chosen)}
    return result
