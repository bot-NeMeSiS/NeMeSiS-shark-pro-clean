"""Preview changes presentation only; accepted fixture truth stays intact."""
from copy import deepcopy
import pytest
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


def test_global_budget_reserves_space_across_competitions_before_second_fixture():
    day=day_fixture()
    day['live'].update(total=0,groups=[])
    for lane in ('upcoming','results'):
        day[lane].update(total=0,groups=[])
    day['today']['groups']=[dict(key=str(i),matches=[
        dict(id=str(i)+'-'+str(j)) for j in range(6)]) for i in range(6)]
    result=home_preview(day,with_hero=False)
    assert [group['key'] for group in result['today']['groups']]==['0','1','2','3','4']
    assert all(group['shown']==1 for group in result['today']['groups'])
    assert len(selected(result))==5


def test_complete_agenda_links_preserve_snapshot_day_and_latest_result_day():
    day=day_fixture()
    day['date']='2026-10-26'
    day['results']['groups'][0]['date']='2026-10-25'
    result=home_preview(day)
    assert result['agenda_href']=='/calendario?date=2026-10-26'
    assert result['upcoming_href']=='/calendario?lane=week&date=2026-10-26'
    assert result['results_href']=='/calendario?lane=finished&date=2026-10-25'
    assert result['results']['total']==60


def test_invalid_snapshot_date_never_becomes_navigation_markup_or_query():
    day=day_fixture()
    day['date']='"><script>alert(1)</script>'
    result=home_preview(day)
    assert result['agenda_href']=='/calendario'
    assert result['results_href']=='/calendario?lane=finished'


def featured_selection(result):
    return result['featured_items'] + [
        row for lane in ('live', 'today', 'upcoming', 'results')
        for group in result[lane]['groups'] for row in group['matches']]


def test_default_keeps_original_shape_and_featured_limit_is_explicit():
    day = day_fixture()
    result = home_preview(day)
    assert result == home_preview(day, featured_limit=1)
    assert set(result) == set(day) | {
        'hero', 'hero_lane', 'featured_count',
        'agenda_href', 'upcoming_href', 'results_href',
    }
    assert [row['id'] for row in selected(result)] == [
        'live4', 'live0', 'live1', 'live2', 'live3',
    ]
    assert 'featured_items' not in result and 'featured_lane' not in result
    assert 'featured_groups' not in result
    without_hero = home_preview(day, with_hero=False, featured_limit=2)
    assert without_hero == home_preview(day, with_hero=False)
    assert 'featured_items' not in without_hero
    assert 'featured_lane' not in without_hero
    assert 'featured_groups' not in without_hero


def test_two_live_featured_rows_reuse_the_same_five_slots_and_original_objects():
    day = day_fixture()
    before = deepcopy(day)
    baseline = home_preview(day)
    result = home_preview(day, featured_limit=2)
    assert [row['id'] for row in result['featured_items']] == ['live4', 'live0']
    assert result['hero'] is result['featured_items'][0]
    assert result['featured_items'][0] is day['live']['groups'][0]['matches'][4]
    assert result['featured_items'][1] is day['live']['groups'][0]['matches'][0]
    assert len(result['featured_groups']) == len(result['featured_items']) == 2
    assert result['featured_groups'][0] is day['live']['groups'][0]
    assert result['featured_groups'][1] is result['featured_groups'][0]
    assert result['featured_lane'] == result['hero_lane'] == 'live'
    rows = featured_selection(result)
    assert len(rows) == len({row['id'] for row in rows}) == result['featured_count'] == 5
    assert {id(row) for row in rows} == {id(row) for row in selected(baseline)}
    assert all(row['home_score'] == 0 for row in rows)
    assert result['live']['shown'] == 3
    assert result['live']['preview_displayed'] == 5
    for lane in day:
        assert result[lane]['total'] == baseline[lane]['total'] == 60
        assert result[lane]['has_more'] == baseline[lane]['has_more']
        assert result[lane]['preview_displayed'] == baseline[lane]['preview_displayed']
    assert day == before


def test_second_featured_row_can_follow_other_lanes_without_taking_their_slots():
    day = day_fixture()
    day['live'].update(total=0, shown=0, groups=[])
    baseline = home_preview(day)
    result = home_preview(day, featured_limit=2)
    assert {row['id'] for row in selected(baseline)} == {
        'today4', 'upcoming4', 'results4', 'today0', 'today1',
    }
    assert [row['id'] for group in baseline['today']['groups']
            for row in group['matches']] == ['today0', 'today1']
    assert [row['id'] for row in result['featured_items']] == ['today4', 'today0']
    assert result['featured_lane'] == 'today'
    assert [row['id'] for row in result['today']['groups'][0]['matches']] == ['today1']
    for lane in ('upcoming', 'results'):
        assert result[lane] == baseline[lane]
    assert result['today']['shown'] == 1
    assert result['today']['preview_displayed'] == 3
    assert {id(row) for row in featured_selection(result)} == {
        id(row) for row in selected(baseline)}


def test_single_winning_live_row_does_not_backfill_from_other_lanes():
    day = day_fixture()
    day['live']['groups'][0]['matches'] = [day['live']['groups'][0]['matches'][0]]
    day['live']['total'] = 1
    baseline = home_preview(day)
    result = home_preview(day, featured_limit=2)
    assert [row['id'] for row in result['featured_items']] == ['live0']
    assert result['featured_count'] == 5
    assert result['live']['shown'] == 0
    assert result['live']['preview_displayed'] == 1
    assert result['live']['has_more'] is False
    for lane in ('today', 'upcoming', 'results'):
        assert result[lane] == baseline[lane]
    assert {row['id'] for row in featured_selection(result)} == {
        row['id'] for row in selected(baseline)}


def test_upcoming_pair_keeps_results_and_complete_agenda_dates():
    day = day_fixture()
    for lane in ('live', 'today'):
        day[lane].update(total=0, shown=0, groups=[])
    day['date'] = '2026-11-03'
    day['results']['groups'][0]['date'] = '2026-11-02'
    baseline = home_preview(day)
    result = home_preview(day, featured_limit=2)
    assert [row['id'] for row in result['featured_items']] == ['upcoming4', 'upcoming0']
    assert result['featured_lane'] == result['hero_lane'] == 'upcoming'
    assert result['upcoming']['shown'] == 2
    assert result['upcoming']['preview_displayed'] == 4
    assert result['results'] == baseline['results']
    assert {id(row) for row in featured_selection(result)} == {
        id(row) for row in selected(baseline)}
    assert result['featured_count'] == 5
    assert result['agenda_href'] == '/calendario?date=2026-11-03'
    assert result['upcoming_href'] == '/calendario?lane=week&date=2026-11-03'
    assert result['results_href'] == '/calendario?lane=finished&date=2026-11-02'


def test_results_keep_one_static_hero_in_featured_opt_in():
    day = day_fixture()
    for lane in ('live', 'today', 'upcoming'):
        day[lane].update(total=0, shown=0, groups=[])
    baseline = home_preview(day)
    result = home_preview(day, featured_limit=2)
    assert result['featured_items'] == [result['hero']]
    assert len(result['featured_groups']) == 1
    assert result['featured_groups'][0] is day['results']['groups'][0]
    assert result['hero'] is baseline['hero']
    assert result['featured_lane'] == result['hero_lane'] == 'results'
    assert result['results'] == baseline['results']
    assert len(featured_selection(result)) == result['featured_count'] == 5


@pytest.mark.parametrize('limit', [1, 3, 5])
def test_featured_opt_in_never_expands_the_existing_global_limit(limit):
    day = day_fixture()
    baseline = home_preview(day, limit=limit)
    result = home_preview(day, limit=limit, featured_limit=2)
    rows = featured_selection(result)
    assert len(rows) == len({row['id'] for row in rows}) == result['featured_count'] == limit
    assert len(result['featured_items']) == min(2, limit)
    assert {id(row) for row in rows} == {id(row) for row in selected(baseline)}


def test_empty_featured_opt_in_keeps_canonical_empty_and_passthrough_distinct():
    result = home_preview({}, featured_limit=2)
    assert result['hero'] is None and result['hero_lane'] == ''
    assert result['featured_items'] == [] and result['featured_lane'] == ''
    assert result['featured_groups'] == []
    assert result['featured_count'] == 0
    assert all(result[lane]['preview_displayed'] == 0 for lane in ('live', 'today', 'upcoming', 'results'))
    assert home_preview(None, featured_limit=2) is None
    marker = object()
    assert home_preview(marker, featured_limit=2) is marker


@pytest.mark.parametrize('invalid', [None, True, False, 0, 3, 1.5, '2'])
def test_featured_limit_rejects_other_values_without_mutating_input(invalid):
    day = day_fixture()
    before = deepcopy(day)
    with pytest.raises(ValueError, match='featured_limit must be 1 or 2'):
        home_preview(day, featured_limit=invalid)
    assert day == before


@pytest.mark.parametrize('count', [1, 3])
def test_featured_groups_pair_with_original_rows_without_new_group_objects(count):
    day = day_fixture()
    for lane in ('today', 'upcoming', 'results'):
        day[lane].update(total=0, shown=0, groups=[])
    groups = [dict(
        key='accepted-' + str(number), competition='League ' + str(number),
        country='Japan' if number == 0 else 'Spain',
        date='2026-11-03', metadata={'source': 'accepted'},
        matches=[dict(id='paired-' + str(number), home_score=0,
                      is_favorite=False, status_info={'is_live': True})],
        shown=1,
    ) for number in range(count)]
    day['live'].update(total=count, shown=count, groups=groups)
    before = deepcopy(day)
    result = home_preview(day, featured_limit=2)
    assert len(result['featured_items']) == len(result['featured_groups']) == min(2, count)
    for position, (row, group) in enumerate(zip(result['featured_items'], result['featured_groups'])):
        assert group is groups[position]
        assert row is group['matches'][0]
        assert group['metadata'] is groups[position]['metadata']
    assert {id(group) for group in result['featured_groups']} <= {id(group) for group in groups}
    assert result['featured_groups'][0]['country'] == 'Japan'
    assert result['featured_groups'][0]['date'] == '2026-11-03'
    assert len(featured_selection(result)) == result['featured_count'] == count
    assert day == before


def active_day_fixture():
    day = day_fixture()
    day['date'] = '2026-11-03'
    day['metadata'] = {'owner': 'accepted-home-snapshot'}
    for lane in ('live', 'today', 'upcoming', 'results'):
        group = day[lane]['groups'][0]
        fixture_date = ('2026-11-02' if lane == 'results' else
                        '2026-11-04' if lane == 'upcoming' else day['date'])
        group.update(competition='Accepted league ' + lane, country='Spain',
                     date=fixture_date, metadata={'lane': lane})
        day[lane]['total'] = 6
        for row in group['matches']:
            row.update(home_team='Home ' + row['id'], away_team='Away ' + row['id'],
                       competition_name=group['competition'], match_date=fixture_date,
                       calendar_time='18:00', source='SIMULATED_QA',
                       metadata={'fixture': row['id']}, status_info={
                           'key': 'LIVE' if lane == 'live' else
                                  'FINISHED' if lane == 'results' else 'UPCOMING',
                           'is_live': lane == 'live', 'is_finished': lane == 'results',
                           'is_upcoming': lane in ('today', 'upcoming'),
                       })
    return day


@pytest.mark.parametrize('with_hero', [True, False])
@pytest.mark.parametrize('featured_limit', [1, 2])
def test_active_first_default_retains_favorite_priority_and_exact_output_shape(with_hero, featured_limit):
    day = active_day_fixture()
    day['live'].update(total=0, shown=0, groups=[])
    before = deepcopy(day)
    default = home_preview(day, with_hero=with_hero, featured_limit=featured_limit)
    explicit = home_preview(day, with_hero=with_hero, featured_limit=featured_limit,
                            active_first=False)
    assert explicit == default
    assert set(explicit) == set(default) and 'active_first' not in explicit
    rows = (featured_selection(default) if with_hero and featured_limit == 2
            else selected(default))
    assert {row['id'] for row in rows} == {
        'today4', 'upcoming4', 'results4', 'today0', 'today1',
    }
    if not with_hero or featured_limit == 1:
        assert not {'featured_items', 'featured_groups', 'featured_lane'} & set(explicit)
    assert day == before


@pytest.mark.parametrize('winning_lane', ['live', 'today', 'upcoming'])
def test_active_phase_nonfavorites_cannot_be_displaced_by_later_phase_favorites(winning_lane):
    day = active_day_fixture()
    lanes = ('live', 'today', 'upcoming', 'results')
    winning_index = lanes.index(winning_lane)
    for lane in lanes[:winning_index]:
        day[lane].update(total=0, shown=0, groups=[])
    for lane in lanes[winning_index:]:
        for row in day[lane]['groups'][0]['matches']:
            row['is_favorite'] = lane != winning_lane
    before = deepcopy(day)
    group = day[winning_lane]['groups'][0]
    result = home_preview(day, featured_limit=2, active_first=True)
    rows = featured_selection(result)
    assert result['hero'] is group['matches'][0]
    assert result['hero_lane'] == result['featured_lane'] == winning_lane
    assert [row['id'] for row in result['featured_items']] == [winning_lane + '0', winning_lane + '1']
    assert len(rows) == result['featured_count'] == 5
    assert {row['id'] for row in rows} == {winning_lane + str(i) for i in range(5)}
    assert all(row['is_favorite'] is False for row in rows)
    assert {id(row) for row in rows} == {id(row) for row in group['matches'][:5]}
    assert all(row['metadata'] is group['matches'][int(row['id'][-1])]['metadata'] for row in rows)
    assert all(featured_group is group for featured_group in result['featured_groups'])
    assert result['metadata'] is day['metadata']
    assert result[winning_lane]['shown'] == 3
    assert result[winning_lane]['preview_displayed'] == 5
    assert all(result[lane]['total'] == day[lane]['total'] for lane in lanes)
    assert day == before


def test_active_first_keeps_favorites_and_stable_competition_peer_order_inside_phase():
    day = active_day_fixture()
    for lane in ('live', 'upcoming', 'results'):
        day[lane].update(total=0, shown=0, groups=[])
    template = day['today']['groups'][0]
    groups = [dict(template, key=key, competition='Accepted league ' + key,
                   metadata={'competition': key}, matches=[
                       dict(template['matches'][i], id=key + str(i), is_favorite=i == 2,
                            metadata={'fixture': key + str(i)}) for i in range(3)])
              for key in ('a', 'b', 'c')]
    day['today'].update(total=9, shown=9, groups=groups)
    before = deepcopy(day)
    result = home_preview(day, with_hero=False, active_first=True)
    assert [group['key'] for group in result['today']['groups']] == ['a', 'b', 'c']
    assert [[row['id'] for row in group['matches']] for group in result['today']['groups']] == [
        ['a2', 'a0'], ['b2', 'b0'], ['c2'],
    ]
    assert result['hero'] is None and result['featured_count'] == 5
    for source_group, output_group in zip(groups, result['today']['groups']):
        assert output_group['metadata'] is source_group['metadata']
        assert all(any(row is source for source in source_group['matches'])
                   for row in output_group['matches'])
    assert day == before


def test_active_first_with_only_results_preserves_one_static_hero_and_original_rows():
    day = active_day_fixture()
    for lane in ('live', 'today', 'upcoming'):
        day[lane].update(total=0, shown=0, groups=[])
    before = deepcopy(day)
    baseline = home_preview(day, featured_limit=2)
    result = home_preview(day, featured_limit=2, active_first=True)
    assert result == baseline
    assert result['hero'] is day['results']['groups'][0]['matches'][4]
    assert result['featured_items'] == [result['hero']]
    assert result['featured_groups'][0] is day['results']['groups'][0]
    assert len(featured_selection(result)) == result['featured_count'] == 5
    assert result['results']['preview_displayed'] == 5
    assert result['results_href'] == '/calendario?lane=finished&date=2026-11-02'
    assert day == before


@pytest.mark.parametrize('selected_date', ['2026-11-03', '"><script>alert(1)</script>'])
def test_active_first_retains_id_filters_dates_and_global_cap_without_mutation(selected_date):
    day = active_day_fixture()
    for lane in ('live', 'today'):
        day[lane].update(total=0, shown=0, groups=[])
    day['date'] = selected_date
    source = day['upcoming']['groups'][0]['matches']
    source[0]['id'] = ''
    source[1]['id'] = source[4]['id']
    before = deepcopy(day)
    result = home_preview(day, limit=99, featured_limit=2, active_first=True)
    rows = featured_selection(result)
    assert len(rows) == len({row['id'] for row in rows}) == result['featured_count'] == 5
    assert {row['id'] for row in rows} == {'upcoming2', 'upcoming3', 'upcoming4', 'upcoming5', 'results4'}
    assert result['hero'] is source[4]
    assert result['upcoming']['preview_displayed'] == 4
    assert result['results']['preview_displayed'] == 1
    date_query = '&date=2026-11-03' if selected_date == '2026-11-03' else ''
    assert result['agenda_href'] == ('/calendario?date=2026-11-03' if date_query else '/calendario')
    assert result['upcoming_href'] == '/calendario?lane=week' + date_query
    assert result['results_href'] == '/calendario?lane=finished&date=2026-11-02'
    source_rows = source + day['results']['groups'][0]['matches']
    assert all(any(row is original for original in source_rows) for row in rows)
    assert all(row['home_score'] == 0 and row['source'] == 'SIMULATED_QA' for row in rows)
    assert day == before


@pytest.mark.parametrize('invalid', [None, 0, 1, 'true', [], {}])
def test_active_first_rejects_non_bool_values_without_mutating_input(invalid):
    day = active_day_fixture()
    before = deepcopy(day)
    with pytest.raises(ValueError, match='active_first must be a bool'):
        home_preview(day, active_first=invalid)
    with pytest.raises(ValueError, match='active_first must be a bool'):
        home_preview(None, active_first=invalid)
    assert day == before
