"""Offline regression evidence: volume, chronology, identity and cached badges."""
from copy import deepcopy
from datetime import datetime, timezone
import sqlite3
from zoneinfo import ZoneInfo

import pytest
from engines.home_matchday import build_matchday
from engines.league_badge_read_model import badge_url, cached_profile_badge, match_badge
from test_home_matchday import LEAGUES, NOW, build, items, match


def test_default_today_expands_to_48_and_keeps_other_lanes_bounded():
    rows = [match(str(i), LEAGUES[i % len(LEAGUES)]) for i in range(70)]
    rows += [match('next' + str(i), hours=24) for i in range(20)]
    original = deepcopy(rows)
    result = build(rows)
    assert result['today']['shown'] == 48 and result['today']['total'] == 70
    assert result['today']['has_more'] and result['upcoming']['shown'] == 12
    assert len(result['today']['groups']) == 6
    assert all(len({m['competition_key'] for m in group['matches']}) == 1 for group in result['today']['groups'])
    assert rows == original


def test_matches_are_chronological_inside_a_league_not_input_order():
    result = build([match('late', hours=5), match('first', hours=1), match('second', hours=3)])
    assert [m['id'] for m in items(result, 'today')] == ['first', 'second', 'late']


def test_country_season_and_provider_scoped_ids_do_not_merge():
    rows = [match('eng', ('', 'Premier League', 'England'), competition_id='39', provider='api-football'),
            match('other', ('', 'Premier League', 'England'), competition_id='39', provider='sportsdb'),
            match('ghana', ('', 'Premier League', 'Ghana'), competition_id='39', provider='api-football'),
            match('season', ('', 'Premier League', 'England'), competition_id='39', provider='api-football', season='2027')]
    groups = build(rows)['today']['groups']
    assert len(groups) == 4
    assert len({g['anchor'] for g in groups}) == 4


def test_canonical_identity_callback_is_used_without_mutating_inputs():
    row = match('one')
    result = build_matchday([row], now=NOW, status_for=lambda m: {'is_upcoming': True},
        kickoff_for=lambda m: datetime.fromisoformat(m['kickoff_iso']), priority_for=lambda m: {'rank': 1},
        identity_for=lambda m: {'group_key':'canonical-proof','display_name':'LaLiga','country':'España','route_id':'la-liga'})
    group = result['today']['groups'][0]
    assert group['key'] == 'canonical-proof' and group['country'] == 'España'
    assert group['route_id'] == 'la-liga' and 'status_info' not in row


def test_badge_can_come_from_a_later_fixture_or_local_static_cache():
    rows = [match('no-logo'), match('logo', competition_logo='/static/img/qa-league.svg')]
    group = build(rows)['today']['groups'][0]
    assert group['logo_url'] == '/static/img/qa-league.svg'
    assert match_badge({'home_logo': 'https://cdn.invalid/team.png', 'logo_url':'https://cdn.invalid/event.png'}) == ''
    assert match_badge({'league': {'logo':'https://cdn.invalid/league.png'}}) == 'https://cdn.invalid/league.png'


@pytest.mark.parametrize('value', ['javascript:alert(1)', 'data:image/svg+xml,<svg/>', '//evil.invalid/x',
    'http://cdn.invalid/a.png', 'https://name:pass@cdn.invalid/x', '/static/../admin', 'https://cdn.invalid/\nfoo'])
def test_unsafe_badge_references_rejected(value):
    assert badge_url(value) == ''


def test_madrid_date_not_utc_date_and_no_tomorrow_fill():
    now = datetime(2026, 10, 10, 23, 15, tzinfo=ZoneInfo('Europe/Madrid'))
    rows = [match('today', now=now, hours=.25), match('tomorrow', now=now, hours=2)]
    result = build_matchday(rows, now=now.astimezone(timezone.utc), status_for=lambda m: {'is_upcoming':True},
        kickoff_for=lambda m: datetime.fromisoformat(m['kickoff_iso']).astimezone(timezone.utc),
        priority_for=lambda m: {'rank':1})
    assert result['date'] == '2026-10-10'
    assert [m['id'] for m in items(result, 'today')] == ['today']
    assert [m['id'] for m in items(result, 'upcoming')] == ['tomorrow']


def test_tone_and_anchors_do_not_change_when_input_is_shuffled():
    rows = [match(str(i), LEAGUES[i % 6]) for i in range(18)]
    first, second = build(rows), build(list(reversed(rows)))
    assert [(g['anchor'], g['tone']) for g in first['today']['groups']] == [(g['anchor'], g['tone']) for g in second['today']['groups']]
    assert len({g['tone'] for g in first['today']['groups']}) > 1


def test_empty_zero_limit_and_invalid_limits_are_explicit():
    assert build([])['today']['total'] == 0
    limited = build([match('one')], limit=0)['today']
    assert limited['shown'] == 0 and limited['has_more']
    with pytest.raises(ValueError): build([], limit=-1)


def test_cached_profiles_require_country_or_scoped_id_and_make_no_writes():
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE sportsdb_league_profiles(sportsdb_league_id TEXT, league_name TEXT, alternate_name TEXT, country TEXT, badge_url TEXT, logo_url TEXT)')
    conn.executemany('INSERT INTO sportsdb_league_profiles VALUES(?,?,?,?,?,?)', [
        ('4328','Premier League','','England','https://cdn.invalid/eng.png',''),
        ('9000','Premier League','','Ghana','https://cdn.invalid/gha.png','')])
    conn.commit()
    before = conn.total_changes
    assert cached_profile_badge(conn, name='Premier League', country='England') == 'https://cdn.invalid/eng.png'
    assert cached_profile_badge(conn, name='Premier League', country='Ghana') == 'https://cdn.invalid/gha.png'
    assert cached_profile_badge(conn, name='Premier League') == ''
    assert cached_profile_badge(conn, league_id='4328', provider='api-football') == ''
    assert cached_profile_badge(conn, league_id='4328', provider='sportsdb') == 'https://cdn.invalid/eng.png'
    assert cached_profile_badge(conn, league_id='4328', provider='sportsdb', country='Ghana') == ''
    assert conn.total_changes == before
    conn.close()


def test_missing_profile_table_is_a_safe_fallback():
    conn = sqlite3.connect(':memory:')
    assert cached_profile_badge(conn, name='LaLiga', country='Spain') == ''
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0] == 0
    conn.close()
