"""Preview changes presentation only; accepted fixture truth stays intact."""
from copy import deepcopy
from engines.home_preview import home_preview


def day_fixture():
    result = {}
    for lane in ('live', 'today', 'upcoming', 'results'):
        rows = [dict(id=lane + str(i), home_score=0, is_favorite=i == 4,
                     status_info={'is_live': lane == 'live'}) for i in range(6)]
        result[lane] = dict(total=60, shown=6, groups=[dict(key=lane, matches=rows, shown=6)])
    return result


def selected(result):
    return ([result['hero']] if result['hero'] else []) + [
        row for lane in ('live', 'today', 'upcoming', 'results')
        for group in result[lane]['groups'] for row in group['matches']]


def test_five_is_global_including_hero_not_per_lane_and_source_is_unchanged():
    day = day_fixture()
    before = deepcopy(day)
    result = home_preview(day)
    rows = selected(result)
    assert len(rows) == 5 == result['featured_count']
    assert len({row['id'] for row in rows}) == 5
    assert result['hero']['id'] == 'live4'
    assert day == before
    assert all(result[lane]['total'] == 60 for lane in day)
    assert all(row['home_score'] == 0 for row in rows)
    assert result['live']['preview_displayed'] == 5
    assert result['live']['shown'] == 4


def test_favorites_win_before_other_non_live_rows_without_copying_old_state():
    day = day_fixture()
    day['live'].update(total=0, shown=0, groups=[])
    result = home_preview(day)
    assert result['hero']['id'] == 'today4'
    assert {'today4', 'upcoming4', 'results4'} <= {row['id'] for row in selected(result)}
    assert result['hero']['status_info'] == {'is_live': False}


def test_duplicate_and_unidentifiable_rows_do_not_consume_preview_budget():
    day = day_fixture()
    day['live']['groups'][0]['matches'][:2] = [dict(id=''), dict(id='live4')]
    result = home_preview(day)
    ids = [row['id'] for row in selected(result)]
    assert len(ids) == 5 == len(set(ids))
    assert '' not in ids


def test_empty_and_noncanonical_context_remain_distinct():
    assert home_preview(None) is None
    result = home_preview({})
    assert result['hero'] is None
    assert result['featured_count'] == 0


def test_client_without_hero_uses_same_global_budget_and_preserves_all_counts():
    day = day_fixture()
    result = home_preview(day, with_hero=False)
    assert result['hero'] is None
    assert len(selected(result)) == 5
    assert result['live']['shown'] == result['live']['preview_displayed'] == 5
    assert result['upcoming']['total'] == 60
    assert result['upcoming']['shown'] == 0 and result['upcoming']['has_more']
