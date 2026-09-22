"""Regression: preserve provider clock provenance, never substitute a render clock.

Pure projections of synthetic records; no Flask server, DB, or external requests.
The existing real-route and multilingual render tests remain unchanged in CI.
"""
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from engines.client_live_surface import live_surface
from engines.v934_realtime_sports_engine import normalize_match
from engines.v935_launch_trust_engine import LIVE_STALE_SECONDS, match_status_truth

NOW = datetime(2026, 9, 22, 18, 0, tzinfo=ZoneInfo('Europe/Madrid'))
CLOCKS = ('live_updated_at', 'provider_updated_at', 'last_synced_at')


def source(status='LIVE', **fields):
    return dict(id='clock-contract-qa', home_team='Local QA', away_team='Visitante QA',
                competition_name='Liga QA', source='SIMULATED_QA',
                match_date=NOW.date().isoformat(), kickoff_time='17:00',
                status=status, minute=0, home_score=0, away_score=0, **fields)


@pytest.mark.parametrize('field', CLOCKS)
@pytest.mark.parametrize('status', ['LIVE', 'HT', 'ET', 'P'])
def test_provider_clock_survives_normalization_and_live_filter(field, status):
    raw = source(status, **{field: (NOW-timedelta(seconds=10)).isoformat()})
    original = deepcopy(raw)
    normalized = normalize_match(raw, now=NOW)
    assert normalized[field] == raw[field]
    assert normalized['realtime_state']['provider_observed_at_source'] == field
    assert match_status_truth(normalized, now=NOW)['is_live'] is True
    saved_projection = deepcopy(normalized)
    result = live_surface({'live_experience': {'matches': [normalized]}}, now=NOW)
    assert len(result['matches']) == 1
    assert result['matches'][0]['minute'] == 0
    assert result['matches'][0]['home_score'] == 0
    assert result['matches'][0]['away_score'] == 0
    assert raw == original and normalized == saved_projection


@pytest.mark.parametrize('field', CLOCKS)
def test_a_previously_valid_snapshot_expires_on_a_later_read(field):
    raw = source(**{field: NOW.isoformat()})
    normalized = normalize_match(raw, now=NOW)
    data = {'live_experience': {'matches': [normalized]}}
    assert len(live_surface(data, now=NOW+timedelta(seconds=LIVE_STALE_SECONDS))['matches']) == 1
    assert live_surface(data, now=NOW+timedelta(seconds=LIVE_STALE_SECONDS+1))['matches'] == []
    assert normalized[field] == raw[field]  # No clock renewal during projection.


@pytest.mark.parametrize('value', ['not-a-time', '2020-01-01T00:00:00+00:00',
                                    (NOW+timedelta(hours=1)).isoformat()])
def test_priority_clock_cannot_be_replaced_by_a_fresh_lower_priority_clock(value):
    raw = source(live_updated_at=value, provider_updated_at=NOW.isoformat(),
                 last_synced_at=NOW.isoformat())
    normalized = normalize_match(raw, now=NOW)
    assert normalized['live_updated_at'] == value
    assert normalized['provider_updated_at'] == raw['provider_updated_at']
    assert match_status_truth(raw, now=NOW)['is_live'] is False
    assert match_status_truth(normalized, now=NOW)['is_live'] is False
    assert live_surface({'live_experience': {'matches': [normalized]}}, now=NOW)['matches'] == []


@pytest.mark.parametrize('field', ['updated_at', 'created_at', 'evaluated_at_madrid'])
def test_generic_or_render_clocks_do_not_establish_provider_freshness(field):
    normalized = normalize_match(source(**{field: NOW.isoformat()}), now=NOW)
    assert not any(field in normalized for field in CLOCKS)
    assert live_surface({'live_experience': {'matches': [normalized]}}, now=NOW)['matches'] == []


def test_twelve_projected_live_rows_are_retained_without_source_mutation():
    rows = [source(last_synced_at=(NOW-timedelta(seconds=10)).isoformat()) for _ in range(12)]
    for index, row in enumerate(rows):
        row['id'] = f'live-clock-{index}'
    normalized = [normalize_match(row, now=NOW) for row in rows]
    originals = deepcopy(normalized)
    result = live_surface({'live_experience': {'matches': normalized}}, now=NOW)
    assert [row['id'] for row in result['matches']] == [row['id'] for row in rows]
    assert normalized == originals


@pytest.mark.parametrize('status', ['NS', 'FT', 'PST', 'CANC', 'SUSP', 'ABD'])
def test_clock_preservation_never_promotes_nonlive_to_live(status):
    raw = source(status, last_synced_at=NOW.isoformat())
    if status == 'NS':
        raw['kickoff_time'] = '21:00'
    normalized = normalize_match(raw, now=NOW)
    assert live_surface({'live_experience': {'lane': 'all', 'matches': [normalized]}}, now=NOW)['matches'] == []
