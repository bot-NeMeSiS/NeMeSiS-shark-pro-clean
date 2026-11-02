"""Presentation-only, globally bounded Home selection from accepted agenda rows."""
from collections.abc import Mapping
from datetime import date
from urllib.parse import urlencode

LANES = ('live', 'today', 'upcoming', 'results')


def home_preview(day, with_hero=True, limit=5, *, featured_limit=1):
    """Keep counts and source truth; never fetch, refresh or mutate the snapshot.

    LIVE wins, then explicit favorites, then the existing canonical lane order.
    The hero consumes one of the same five slots, rather than duplicating a card.
    Opting into two featured items reallocates only the winning lane's already
    chosen rows. Results retain one static hero; other lanes keep their slots.
    """
    if not isinstance(day, Mapping):
        return day
    if type(featured_limit) is not int or featured_limit not in (1, 2):
        raise ValueError('featured_limit must be 1 or 2')
    candidates = []
    for lane_index, lane in enumerate(LANES):
        for group in day.get(lane, {}).get('groups', ()):
            positions = {}
            for row in group.get('matches', ()):
                tier = (lane != 'live', row.get('is_favorite') is not True, lane_index)
                position = positions.get(tier, 0)
                positions[tier] = position + 1
                candidates.append((tier, position, lane, group, row))
    # Keep canonical group order, but reserve a slot across peers before taking
    # a second fixture from one league. Favorites and LIVE still win first.
    candidates.sort(key=lambda item: (item[0], item[1]))
    chosen, seen = [], set()
    for _, _, lane, group, row in candidates:
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
    featured = [hero] if hero else []
    remaining = chosen[1:] if hero else chosen
    if featured_limit == 2 and with_hero:
        if hero and hero[0] in ('live', 'today', 'upcoming'):
            for entry in chosen[1:]:
                if entry[0] == hero[0]:
                    featured.append(entry)
                    # Remove this occurrence by tuple identity, without comparing
                    # mutable rows or taking a slot from another chosen lane.
                    remaining = [item for item in remaining if item is not entry]
                    break
        result.update(featured_items=[entry[2] for entry in featured],
                      featured_groups=[entry[1] for entry in featured],
                      featured_lane=result['hero_lane'])
    def valid_date(value):
        try:
            return date.fromisoformat(str(value)).isoformat()
        except (TypeError, ValueError):
            return ''
    selected_date = valid_date(day.get('date'))
    result_dates = [valid_date(group.get('date')) for group in day.get('results', {}).get('groups', ())]
    result_date = max(filter(None, result_dates), default=selected_date)
    def href(lane='', selected=selected_date):
        query = dict(lane=lane) if lane else {}
        if selected:
            query['date'] = selected
        return '/calendario' + ('?' + urlencode(query) if query else '')
    result.update(agenda_href=href(), upcoming_href=href('week'),
                  results_href=href('finished', result_date))
    for lane in LANES:
        original = day.get(lane) or {}
        groups = []
        for group in original.get('groups', ()):
            rows = [row for chosen_lane, chosen_group, row in remaining
                    if chosen_lane == lane and chosen_group is group]
            if rows:
                favorite = any(row.get('is_favorite') is True for row in rows)
                groups.append(dict(group, matches=rows, shown=len(rows),
                                   home_favorite=favorite,
                                   home_primary=bool(group.get('home_primary') or favorite)))
        shown = sum(len(group['matches']) for group in groups)
        # Featured rows consume the same global slots and are absent from groups.
        displayed = shown + (len(featured) if hero and hero[0] == lane else 0)
        result[lane] = dict(original, groups=groups, shown=shown,
                            preview_displayed=displayed,
                            has_more=int(original.get('total', 0)) > displayed)
    return result
