"""Presentation-only, globally bounded Home selection from accepted agenda rows."""
from collections.abc import Mapping

LANES = ('live', 'today', 'upcoming', 'results')


def home_preview(day, with_hero=True, limit=5):
    """Keep counts and source truth; never fetch, refresh or mutate the snapshot.

    LIVE wins, then explicit favorites, then the existing canonical lane order.
    The hero consumes one of the same five slots, rather than duplicating a card.
    """
    if not isinstance(day, Mapping):
        return day
    candidates = [(lane, group, row) for lane in LANES
                  for group in day.get(lane, {}).get('groups', ())
                  for row in group.get('matches', ())]
    candidates.sort(key=lambda item: (item[0] != 'live', item[2].get('is_favorite') is not True))
    chosen, seen = [], set()
    for lane, group, row in candidates:
        identity = str(row.get('id') or '').strip()
        # An unidentifiable fixture must not consume a slot or fabricate identity.
        if not identity or identity in seen:
            continue
        seen.add(identity)
        chosen.append((lane, group, row))
        if len(chosen) >= max(1, min(int(limit), 5)):
            break
    hero = chosen[0] if chosen and with_hero else None
    result = dict(day, hero=hero[2] if hero else None,
                  hero_lane=hero[0] if hero else '', featured_count=len(chosen))
    for lane in LANES:
        original = day.get(lane) or {}
        groups = []
        for group in original.get('groups', ()):
            rows = [row for chosen_lane, chosen_group, row in (chosen[1:] if hero else chosen)
                    if chosen_lane == lane and chosen_group is group]
            if rows:
                favorite = any(row.get('is_favorite') is True for row in rows)
                groups.append(dict(group, matches=rows, shown=len(rows),
                                   home_favorite=favorite,
                                   home_primary=bool(group.get('home_primary') or favorite)))
        shown = sum(len(group['matches']) for group in groups)
        # The lane count includes its hero; preview groups deliberately exclude it.
        displayed = shown + int(bool(hero and hero[0] == lane))
        result[lane] = dict(original, groups=groups, shown=shown,
                            preview_displayed=displayed,
                            has_more=int(original.get('total', 0)) > displayed)
    return result
