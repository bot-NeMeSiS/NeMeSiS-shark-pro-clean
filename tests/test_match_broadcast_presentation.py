from datetime import datetime, timedelta, timezone
from engines.match_broadcast_presentation import broadcast_presentation

NOW = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)


def history(age=1, available=True):
    return {'details': {'broadcasts': [{'payload': {'observed_at': (NOW-timedelta(hours=age)).isoformat(), 'available': available, 'channels': [
        {'channel': 'Canal exterior', 'country': 'France'},
        {'channel': 'Canal de prueba', 'country': 'Spain'},
        {'channel': 'Canal de prueba', 'country': 'Spain'},
        {'channel': ''},
    ]}}]}}


def test_current_schedule_prioritizes_country_and_deduplicates():
    view = broadcast_presentation(history(), now=NOW)
    assert view['available']
    assert len(view['channels']) == 2
    assert view['channels'][0]['country'] == 'Spain'


def test_stale_future_missing_and_unavailable_do_not_confirm_tv():
    for source in (history(13), history(-1), {}, history(1, False)):
        view = broadcast_presentation(source, now=NOW)
        assert not view['available']
        assert view['channels'] == []
    assert broadcast_presentation(history(13), now=NOW)['stale']


def test_latest_empty_schedule_replaces_previous_channels():
    source = history(2)
    source['details']['broadcasts'] += history(1, False)['details']['broadcasts']
    view = broadcast_presentation(source, now=NOW)
    assert not view['available']
    assert view['channels'] == []
