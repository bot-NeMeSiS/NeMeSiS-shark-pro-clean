import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from engines.market_forecast_engine import market_implied_forecast


MADRID = ZoneInfo('Europe/Madrid')
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=MADRID)


def match(*, prices=(2.0, 4.0, 4.0), source='The Odds API', observed_at=None):
    observed_at = observed_at or NOW.isoformat()
    return {
        'id': 'market-forecast-synthetic',
        'home_team': 'Granada CF',
        'away_team': 'Visitante QA',
        'competition_name': 'Liga QA',
        'kickoff_iso': (NOW + timedelta(hours=3)).isoformat(),
        'match_date': (NOW + timedelta(hours=3)).date().isoformat(),
        'status': 'NS',
        'odds_h2h_json': json.dumps({
            'source': source,
            'bookmaker': 'Book QA',
            'last_update': observed_at,
            'outcomes': [
                {'name': 'Granada C.F.', 'price': prices[0]},
                {'name': 'Draw', 'price': prices[1]},
                {'name': 'Visitante QA', 'price': prices[2]},
            ],
        }),
    }


def test_current_complete_market_is_normalized_to_100_without_becoming_a_pick():
    result = market_implied_forecast(match(), is_upcoming=True, now=NOW)

    assert result['available'] is True
    assert result['state'] == 'CURRENT'
    assert [item['key'] for item in result['outcomes']] == ['home', 'draw', 'away']
    assert [item['probability_pct'] for item in result['outcomes']] == [50.0, 25.0, 25.0]
    assert sum(item['probability_pct'] for item in result['outcomes']) == 100.0
    assert result['favorite'] == {'key': 'home', 'label': 'Granada CF', 'probability_pct': 50.0}
    assert result['source'] == 'The Odds API'
    assert result['bookmaker'] == 'Book QA'
    assert result['external_calls'] == 0
    assert 'No es una probabilidad calibrada por SHARK' in result['disclaimer']


@pytest.mark.parametrize('prices', [
    (2.0, 4.0, 0),
    (2.0, 4.0, True),
    (float('nan'), 4.0, 4.0),
])
def test_incomplete_or_invalid_market_never_shows_percentages(prices):
    result = market_implied_forecast(match(prices=prices), is_upcoming=True, now=NOW)

    assert result['available'] is False
    assert result['state'] == 'INCOMPLETE_MARKET'
    assert result['outcomes'] == []


def test_stale_market_never_shows_percentages():
    old = (NOW - timedelta(hours=2)).isoformat()
    result = market_implied_forecast(match(observed_at=old), is_upcoming=True, now=NOW)

    assert result['available'] is False
    assert result['state'] == 'STALE_MARKET'
    assert result['outcomes'] == []


def test_unrecognized_source_and_non_upcoming_event_fail_closed():
    unsupported = market_implied_forecast(match(source='Manual import'), is_upcoming=True, now=NOW)
    finished = market_implied_forecast(match(), is_upcoming=False, now=NOW)

    assert unsupported['state'] == 'UNVERIFIED_SOURCE'
    assert unsupported['outcomes'] == []
    assert finished['state'] == 'NOT_UPCOMING'
    assert finished['outcomes'] == []
