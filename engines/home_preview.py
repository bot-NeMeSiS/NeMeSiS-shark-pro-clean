"""Presentation-only, globally bounded Home selection from accepted agenda rows."""
from collections.abc import Mapping
from datetime import date
import math
from urllib.parse import urlencode

LANES = ('live', 'today', 'upcoming', 'results')


def home_preview(day, with_hero=True, limit=5, *, featured_limit=1, active_first=False, mode='legacy', relevance_candidates=()):
    """Keep counts and source truth; never fetch, refresh or mutate the snapshot.

    By default LIVE wins, then favorites, then the existing canonical lane order.
    The hero consumes one of the same five slots, rather than duplicating a card.
    Opting into two featured items reallocates only the winning lane's already
    chosen rows. Results retain one static hero; other lanes keep their slots.
    Active-first presentation exhausts LIVE, today and upcoming in that order
    before results, with favorites ranked only within their existing lane.
    Mixed-today is an explicit8-feature/12-total opt-in. Supplied display
    relevance is retained only for the same fixture and accepted lifecycle.
    """
    if type(active_first) is not bool:
        raise ValueError('active_first must be a bool')
    if mode == 'mixed_today':
        selected = _mixed_today_preview(day, with_hero=with_hero, limit=limit, featured_limit=featured_limit)
        return _retain_current_relevance(selected, relevance_candidates)
    if mode != 'legacy':
        raise ValueError('unknown Home preview mode')
    if not isinstance(day, Mapping):
        return day
    if type(featured_limit) is not int or featured_limit not in (1, 2):
        raise ValueError('featured_limit must be 1 or 2')
    candidates = []
    for lane_index, lane in enumerate(LANES):
        for group in day.get(lane, {}).get('groups', ()):
            positions = {}
            for row in group.get('matches', ()):
                tier = ((lane_index, row.get('is_favorite') is not True) if active_first
                        else (lane != 'live', row.get('is_favorite') is not True, lane_index))
                position = positions.get(tier, 0)
                positions[tier] = position + 1
                candidates.append((tier, position, lane, group, row))
    # Keep canonical group order, but reserve a slot across peers before taking
    # a second fixture from one league within the selected phase/favorite tier.
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


def _mixed_today_preview(day, *, with_hero, limit, featured_limit):
    """Opt-in presentation of accepted fixtures; no IO or identity inference.

    The App supplies one jointly deduplicated, current identity selection before
    making the matchday. Exact IDs here only prevent displaying that selection
    twice; they are not proof that two provider aliases denote the same fixture.
    """
    if type(limit) is not int or not 1 <= limit <= 12:
        raise ValueError('mixed preview limit must be 1..12')
    if type(featured_limit) is not int or not 1 <= featured_limit <= 8:
        raise ValueError('mixed featured_limit must be 1..8')
    if not isinstance(day, Mapping):
        return day
    today = day.get('date')
    pool = []
    for lane in ('live', 'today'):
        for gi, group in enumerate((day.get(lane) or {}).get('groups') or ()):
            if lane == 'today' and group.get('date') != today:
                continue
            rank = group.get('home_priority_rank')
            if type(rank) not in (int, float) or not math.isfinite(rank) or rank < 0:
                rank = 999
            for pos, row in enumerate(group.get('matches') or ()):
                if not isinstance(row, Mapping):
                    continue
                state = row.get('status_info') or {}
                if not isinstance(state, Mapping) or state.get('is_stale') or state.get('status_conflict'):
                    continue
                if state.get('is_finished') or state.get('is_live') == state.get('is_upcoming'):
                    continue
                if state.get('is_live' if lane == 'live' else 'is_upcoming') is not True:
                    continue
                if not (group.get('home_primary') or row.get('is_favorite') is True):
                    continue
                identity = str(row.get('id') or '').strip()
                if not identity:
                    continue
                score = (row.get('is_favorite') is not True, rank, lane != 'live', pos, gi)
                pool.append((score, lane, group, row, identity))
    pool.sort(key=lambda entry: entry[0])
    featured, seen = [], set()
    capacity = min(featured_limit, limit) if with_hero else 0
    def include(entry, target):
        if entry[4] in seen:
            return False
        seen.add(entry[4])
        target.append(entry)
        return True
    # A single slot always takes the best ranked fixture. With two or more,
    # represent both phases when genuinely eligible fixtures exist in each.
    if capacity == 1 and pool:
        include(pool[0], featured)
    elif capacity:
        for lane in ('live', 'today'):
            entry = next((e for e in pool if e[1] == lane and e[4] not in seen), None)
            if entry is not None:
                include(entry, featured)
    for entry in pool:
        if len(featured) >= capacity:
            break
        include(entry, featured)
    featured.sort(key=lambda entry: entry[0])
    extra = []
    for lane in LANES:
        remaining = [(pos, gi, group, row)
                     for gi, group in enumerate((day.get(lane) or {}).get('groups') or ())
                     for pos, row in enumerate(group.get('matches') or ())]
        # Preserve the existing cross-league round robin in the ordinary list;
        # eight featured fixtures must not monopolize the twelve-card preview.
        for _, _, group, row in sorted(remaining, key=lambda entry: (
                not (entry[2].get('home_primary') or entry[3].get('is_favorite') is True),
                entry[0], entry[1])):
            if len(featured) + len(extra) >= limit:
                break
            identity = str(row.get('id') or '').strip()
            if identity:
                include((None, lane, group, row, identity), extra)
    # Reuse the existing validated date/link contract. Legacy selection stays
    # untouched and does not mutate or fetch anything.
    links = home_preview(day, with_hero=False)
    result = dict(day, hero=featured[0][3] if featured else None,
                  hero_lane=featured[0][1] if featured else '',
                  featured_items=[e[3] for e in featured],
                  featured_groups=[e[2] for e in featured],
                  featured_lane='mixed_today' if featured else '',
                  featured_count=len(featured) + len(extra),
                  agenda_href=links['agenda_href'], upcoming_href=links['upcoming_href'],
                  results_href=links['results_href'])
    for lane in LANES:
        original = day.get(lane) or {}
        groups = []
        for group in original.get('groups') or ():
            rows = [e[3] for e in extra if e[1] == lane and e[2] is group]
            if rows:
                favorite = any(r.get('is_favorite') is True for r in rows)
                groups.append(dict(group, matches=rows, shown=len(rows), home_favorite=favorite,
                                   home_primary=bool(group.get('home_primary') or favorite)))
        shown = sum(len(g['matches']) for g in groups)
        displayed = shown + sum(e[1] == lane for e in featured)
        result[lane] = dict(original, groups=groups, shown=shown, preview_displayed=displayed,
                            has_more=int(original.get('total') or 0) > displayed)
    return result


def _retain_current_relevance(day, candidates):
    """Carry only the same fixture's current display bucket, never old truth.

    A tomorrow fixture leaving the hero still keeps its existing relevance in
    the ordinary list. Exact IDs plus matching accepted lifecycle are required;
    no score, label, clock, row or provider alias is copied from cached metadata.
    """
    if not isinstance(day, Mapping) or not candidates:
        return day
    indexed = {}
    for candidate in candidates:
        if isinstance(candidate, Mapping):
            indexed.setdefault(str(candidate.get('id') or ''), []).append(candidate)
    def retain(row):
        if not isinstance(row, Mapping):
            return row
        own = row.get('sports_relevance') or {}
        if row.get('sports_relevance_bucket') or (isinstance(own, Mapping) and own.get('bucket')):
            return row
        state = row.get('status_info') or {}
        if not isinstance(state, Mapping):
            return row
        for candidate in indexed.get(str(row.get('id') or ''), ()):
            relevance = candidate.get('sports_relevance') or {}
            if not isinstance(relevance, Mapping):
                continue
            if relevance.get('is_stale') is not False or relevance.get('status_conflict') is not False:
                continue
            if any(relevance.get(key) != state.get(key, False)
                   for key in ('is_live', 'is_upcoming', 'is_finished')):
                continue
            bucket = candidate.get('sports_relevance_bucket') or relevance.get('bucket')
            if bucket in ('PRIORITY', 'STANDARD', 'LOW_PRIORITY', 'UNKNOWN'):
                return dict(row, sports_relevance_bucket=bucket)
        return row
    result = dict(day, hero=retain(day.get('hero')),
                  featured_items=[retain(row) for row in day.get('featured_items', ())])
    for lane in LANES:
        original = day.get(lane) or {}
        result[lane] = dict(original, groups=[dict(group, matches=[retain(row) for row in group.get('matches', ())])
                                            for group in original.get('groups', ())])
    return result
