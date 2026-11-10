"""Mixed today's presentation over accepted fixtures; no providers or clocks patched."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from engines.home_matchday import build_matchday
from engines.home_preview import home_preview
from test_home_matchday import build, match, NOW


def preview(day, **kwargs):
    return home_preview(day, mode='mixed_today', limit=12, featured_limit=8, **kwargs)


def displayed(value):
    return value['featured_items'] + [r for lane in ('live', 'today', 'upcoming', 'results')
        for group in value[lane]['groups'] for r in group['matches']]


@pytest.mark.parametrize('count', [0, 1, 2, 7, 8, 12, 20])
def test_mixed_real_lanes_are_bounded_unique_and_do_not_mutate(count):
    rows = [match(str(i), state='live' if i < 3 else 'upcoming', hours=-.5 if i < 3 else 2)
            for i in range(count)]
    day = build(rows)
    before = deepcopy(day)
    result = preview(day)
    ids = [r['id'] for r in displayed(result)]
    assert len(ids) == len(set(ids)) == min(count, 12) == result['featured_count']
    assert len(result['featured_items']) == min(count, 8)
    assert day == before
    assert all(result[lane]['total'] == day[lane]['total'] for lane in ('live', 'today', 'upcoming', 'results'))
    if count > 3:
        assert {r['status_info'].get('is_live', False) for r in result['featured_items']} == {True, False}
    if count == 7:
        assert {r['id'] for r in result['featured_items']} == {str(i) for i in range(7)}


def test_no_tomorrow_finished_stale_unknown_conflict_or_minor_filler():
    rows = [match('live', state='live', hours=-1), match('today'),
            match('tomorrow', hours=24), match('finished', state='finished', hours=-2),
            match('stale', state='live', hours=-1, is_stale=True),
            match('unknown', state='unknown'), match('conflict', status_conflict=True),
            match('minor', ('small', 'Minor competition', 'Spain'))]
    result = preview(build(rows))
    assert {r['id'] for r in result['featured_items']} == {'live', 'today'}
    assert {'tomorrow', 'finished', 'minor'} <= {r['id'] for r in displayed(result)}
    assert not {'stale', 'unknown', 'conflict'} & {r['id'] for r in displayed(result)}


def test_sport_rank_precedes_row_position_and_single_slot_takes_best_rank():
    day = build([match('a'), match('b'), match('c')])
    g = day['today']['groups'][0]
    first, second, third = g['matches']
    day['today']['groups'] = [dict(g, home_priority_rank=20, matches=[first]),
                              dict(g, home_priority_rank=1, matches=[second, third])]
    result = home_preview(day, mode='mixed_today', limit=1, featured_limit=1)
    assert result['featured_items'][0]['id'] == 'b'
    assert [r['id'] for r in preview(day)['featured_items']] == ['b', 'c', 'a']


def test_ordinary_round_robin_keeps_remaining_primary_rows_before_secondary_filler():
    from test_home_matchday import LEAGUES
    majors = [match(f'major-{i}-{j}', league) for i, league in enumerate(LEAGUES) for j in range(2)]
    secondary = [match(f'minor-{i}', (f'small-{i}', f'Minor {i}', 'Spain')) for i in range(10)]
    result = preview(build(majors + secondary))
    assert len(result['featured_items']) == 8
    assert {r['id'] for r in displayed(result)} == {r['id'] for r in majors}


@pytest.mark.parametrize('now', [datetime(2026, 3, 29, 0, 45, tzinfo=timezone.utc),
                               datetime(2026, 10, 25, 1, 15, tzinfo=timezone.utc),
                               datetime(2026, 11, 10, 23, 5, tzinfo=ZoneInfo('Europe/Madrid'))])
def test_madrid_date_dst_and_live_across_midnight(now):
    local = now.astimezone(ZoneInfo('Europe/Madrid'))
    rows = [dict(id='live', kickoff=local-timedelta(hours=2), live=True),
            dict(id='soon', kickoff=local+timedelta(minutes=10), live=False),
            dict(id='tomorrow', kickoff=local+timedelta(days=1), live=False)]
    day = build_matchday(rows, now=now,
        status_for=lambda r: {'is_live':r['live'], 'is_upcoming':not r['live']},
        kickoff_for=lambda r:r['kickoff'], priority_for=lambda r:{'rank':1})
    result = preview(day)
    assert day['date'] == local.date().isoformat()
    assert {r['id'] for r in result['featured_items']} == {'live', 'soon'}


@pytest.mark.parametrize('limit,featured', [(True, 8), (13, 8), (0, 8), (12, True), (12, 9)])
def test_invalid_mixed_limits_do_not_silently_expand(limit, featured):
    with pytest.raises(ValueError):
        home_preview({}, mode='mixed_today', limit=limit, featured_limit=featured)


def test_legacy_default_and_no_hero_are_explicit():
    day = build([match(str(i)) for i in range(10)])
    assert home_preview(day) == home_preview(day, mode='legacy')
    assert home_preview(day)['featured_count'] == 5
    no_hero = preview(day, with_hero=False)
    assert no_hero['hero'] is None and no_hero['featured_items'] == []
    assert len(displayed(no_hero)) == 10
    with pytest.raises(ValueError):
        home_preview(day, mode='unexpected')


@pytest.mark.parametrize('case', ['tomorrow', 'finished', 'secondary'])
def test_available_ordinary_fixtures_do_not_claim_an_empty_public_agenda(case):
    from test_home_canonical_consistency import render
    league = ('small', 'Minor competition', 'Spain') if case == 'secondary' else None
    options = {'hours': 24} if case == 'tomorrow' else (
        {'state': 'finished', 'hours': -2} if case == 'finished' else {})
    fixture = match('ordinary-available', league, **options) if league else match('ordinary-available', **options)
    day = build([fixture])
    assert preview(day)['featured_items'] == []
    html = render('home.html', {'home_matchday': day})
    assert 'data-v934-match-id="ordinary-available"' in html
    assert 'No hay partidos destacados para hoy. Consulta la agenda completa.' in html
    assert 'Consulta la agenda completa por ligas y fechas.' in html
    assert 'Todavía no hay partidos disponibles para esta jornada.' not in html


def test_prepared_aliases_across_live_today_share_one_actual_selection(app_module, monkeypatch):
    """Inject a provider phase disagreement, retaining real canonical identity guards."""
    import json
    from pathlib import Path
    from engines.fixture_snapshot_read_model import prepare_fixture_snapshot

    a = app_module
    f = json.loads(Path(__file__).with_name('v991_fixture_identity.json').read_bytes())['input']
    rows = deepcopy(f['rows'][:2])
    before = deepcopy(rows)
    stamp = a.match_kickoff_madrid_dt(rows[0])
    now = stamp - timedelta(hours=1)
    live = rows[1]
    summary = {'all_valid_matches':rows, 'valid_matches_today':rows, 'valid_live_events':[live]}
    snapshot = prepare_fixture_snapshot({'current':rows, 'history':()},
        lambda keys:[deepcopy(r) for r in f['catalogue'] if r['key'] in keys],
        kickoff_for=a.match_kickoff_madrid_dt)
    selected_date = stamp.date().isoformat()
    operation = a._V991Operation(summary, selected_date, a._v991_generation(snapshot, selected_date),
                                a._v991_membership(summary), snapshot)
    monkeypatch.setattr(a, 'canonical_match_status', lambda r, now=None: {
        'is_live':r is live, 'is_upcoming':r is not live,
        'is_finished':False, 'is_stale':False, 'status_conflict':False})
    result = a.home_matchday_context(summary, now=now, fixture_operation=operation,
        favorites={'team':set(), 'league':set(), 'match':set(), 'all':[]})
    assert result['live']['total'] == 1 and result['today']['total'] == 0
    assert result['live']['groups'][0]['matches'][0]['id'] == live['id']
    assert [r['id'] for r in preview(result)['featured_items']] == [live['id']]
    assert rows == before and snapshot.context_for(rows[0]).state == 'RESOLVED'
    # Without the original operation, the caller must not infer alias identity.
    independent = a.home_matchday_context(summary, now=now,
        favorites={'team':set(), 'league':set(), 'match':set(), 'all':[]})
    assert independent['identity_state'] == 'UNPREPARED'
    assert independent['live']['total'] + independent['today']['total'] == 2
