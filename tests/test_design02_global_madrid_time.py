from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from engines.madrid_time_engine import normalize_kickoff_for_display, parse_match_datetime


@pytest.mark.parametrize('value,zone,expected', [
    ('2026-01-15T20:00:00', 'Europe/London', '2026-01-15T21:00:00+01:00'),
    ('2026-07-15T20:00:00', 'Europe/London', '2026-07-15T21:00:00+02:00'),
    ('2026-07-15T19:30:00', 'America/New_York', '2026-07-16T01:30:00+02:00'),
    ('2026-07-15T21:00:00', 'Asia/Tokyo', '2026-07-15T14:00:00+02:00'),
    ('2026-07-15T20:00:00', 'Europe/Paris', '2026-07-15T20:00:00+02:00'),
    ('2026-01-15T23:30:00Z', None, '2026-01-16T00:30:00+01:00'),
    ('2026-07-15T23:30:00Z', None, '2026-07-16T01:30:00+02:00'),
    ('2026-03-29T00:59:00Z', None, '2026-03-29T01:59:00+01:00'),
    ('2026-03-29T01:00:00Z', None, '2026-03-29T03:00:00+02:00'),
    ('2026-10-25T00:30:00Z', None, '2026-10-25T02:30:00+02:00'),
    ('2026-10-25T01:30:00Z', None, '2026-10-25T02:30:00+01:00'),
    ('2026-07-16T00:30:00+02:00', 'Asia/Tokyo', '2026-07-16T00:30:00+02:00'),
    ('2026-07-15T19:30:00-04:00', None, '2026-07-16T01:30:00+02:00'),
    ('2026-01-15T21:30:00+09:00', None, '2026-01-15T13:30:00+01:00'),
])
def test_absolute_instant_is_presented_in_madrid(value, zone, expected):
    row = normalize_kickoff_for_display({'kickoff_iso': value, 'source_timezone': zone})
    assert row['madrid_dt_iso'] == expected
    assert row['match_date'] == expected[:10]
    assert row['kickoff_time'] == expected[11:16]


def test_manual_db_madrid_is_not_shifted_twice():
    row = normalize_kickoff_for_display({'match_date': '2026-07-16', 'kickoff_time': '00:30'})
    assert row['madrid_dt_iso'] == '2026-07-16T00:30:00+02:00'
    assert normalize_kickoff_for_display(row)['madrid_dt_iso'] == row['madrid_dt_iso']


def test_explicit_foreign_parts_are_not_manual_madrid():
    row = normalize_kickoff_for_display({'match_date': '2026-07-15', 'kickoff_time': '19:30', 'source_timezone': 'America/New_York'})
    assert row['madrid_dt_iso'] == '2026-07-16T01:30:00+02:00'
    assert normalize_kickoff_for_display(row)['madrid_dt_iso'] == row['madrid_dt_iso']
    assert 'manual_madrid_local' not in row['time_warnings']


@pytest.mark.parametrize('zone', ['Invalid/Timezone', 'Europe/Paris'])
def test_unresolved_foreign_time_is_not_labelled_madrid(zone):
    row = normalize_kickoff_for_display({'match_date':'2026-10-25','kickoff_time':'02:30','source_timezone':zone})
    assert row['madrid_time'] == '' and row['madrid_date'] == ''
    assert '02:30' not in row['display_datetime']


def test_telegram_foreign_zone_uses_same_instant():
    from engines.madrid_time_engine import format_telegram_match_time_madrid
    row = format_telegram_match_time_madrid({'match_date':'2026-07-15','kickoff_time':'19:30','source_timezone':'America/New_York'})
    assert row['iso_madrid'] == '2026-07-16T01:30:00+02:00'


@pytest.mark.parametrize('raw,zone', [
    ('2026-03-29T02:30:00', 'Europe/Paris'),
    ('2026-10-25T02:30:00', 'Europe/Paris'),
    ('2026-07-16T12:30:00', 'Invalid/Timezone'),
])
def test_unknown_or_ambiguous_provider_zone_never_invents_instant(raw, zone):
    assert parse_match_datetime(raw, source_timezone=zone) is None


def test_sportsdb_utc_parts_roll_over_but_manual_parts_do_not(app_module):
    event = {'idEvent': 'tz-qa', 'strSport': 'Soccer', 'strHomeTeam': 'Club Norte',
             'strAwayTeam': 'Club Sur', 'strLeague': 'Liga QA', 'dateEvent': '2026-07-15',
             'strTime': '23:30:00', 'strStatus': 'NS'}
    result = app_module.sportsdb_event_to_match(event, cache_teams=False)
    assert result['match_date'] == '2026-07-16'
    assert result['kickoff_time'] == '01:30'
    assert result['kickoff_iso'] == '2026-07-16T01:30:00+02:00'


def test_autumn_repeated_hour_sorts_by_instant_not_wall_clock():
    values = ['2026-10-25T01:15:00Z', '2026-10-25T00:45:00Z']
    ordered = sorted(values, key=parse_match_datetime)
    assert ordered == list(reversed(values))
    assert datetime.fromisoformat(normalize_kickoff_for_display({'kickoff_iso': ordered[0]})['madrid_dt_iso']).astimezone(ZoneInfo('UTC')).hour == 0


def test_calendar_chronological_order_uses_absolute_instant(app_module):
    rows = [
        {'id':'later','kickoff_iso':'2026-10-25T01:15:00Z','status':'NS','sports_relevance':{'competition_rank':1}},
        {'id':'earlier','kickoff_iso':'2026-10-25T00:45:00Z','status':'NS','sports_relevance':{'competition_rank':1}},
    ]
    assert [row['id'] for row in app_module._calendar_sort(rows,'time')] == ['earlier','later']


def test_calendar_group_uses_madrid_day_not_provider_day(app_module):
    rows = [{'id':'midnight','kickoff_iso':'2026-07-15T23:30:00Z','match_date':'2026-07-15',
             'calendar_competition':'QA','calendar_competition_id':'qa','calendar_rank':1}]
    groups = app_module._calendar_group(rows)
    assert groups[0]['date'] == '2026-07-16'


def test_template_cannot_reinterpret_unresolved_provider_datetime(app_module):
    with app_module.app.test_request_context('/calendar'):
        row = {'match_date':'2026-10-25','kickoff_time':'02:30','source_timezone':'Europe/Paris'}
        assert app_module.ui_match_datetime(row) == 'Fecha pendiente'


@pytest.mark.parametrize('language', ['es','en','fr'])
@pytest.mark.parametrize('country', ['England','France','Italy','Germany','Argentina','Brazil','USA','Japan'])
def test_country_and_locale_never_change_shared_fixture_time(app_module, language, country):
    with app_module.app.test_request_context('/', headers={'Accept-Language': language}):
        row = {'kickoff_iso': '2026-07-15T23:30:00Z', 'country': country}
        label = app_module.ui_match_datetime(row)
        assert '01:30' in label and '16' in label


def test_remaining_shared_clocks_and_admin_kickoff_use_canonical_presenter():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    admin = (root/'templates/admin_realtime_center.html').read_text(encoding='utf-8')
    assert '{{ ui_match_datetime(match) }}' in admin
    assert "{{ match.get('kickoff_time') }}" not in admin
    base = (root/'templates/base.html').read_text(encoding='utf-8')
    assert '.toLocaleTimeString(' not in base and '.getHours()' not in base
    javascript = (root/'static/ui-localization.js').read_text(encoding='utf-8')
    assert "timeZone:'Europe/Madrid'" in javascript
