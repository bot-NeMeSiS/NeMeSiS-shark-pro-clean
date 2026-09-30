"""SIMULATED_QA: snapshot summaries must not invent ordering or data certainty."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import inf, nan
from zoneinfo import ZoneInfo

import pytest

from engines.realtime_change_summary_engine import build_factual_change_summary
from engines.realtime_state_engine import build_realtime_match_state

NOW = datetime(2026, 9, 15, 20, 0, tzinfo=ZoneInfo('Europe/Madrid'))


def state(seconds=0, *, observed_seconds=None, **overrides):
    evaluated = NOW + timedelta(seconds=seconds)
    observed = NOW + timedelta(seconds=seconds - 30 if observed_seconds is None else observed_seconds)
    raw = dict(id='summary-safety-qa', fixture_id='summary-safety-qa',
        source='provider-cache', home_team='Local QA', away_team='Visitante QA',
        home_team_id='home-qa', away_team_id='away-qa', competition_id='league-qa',
        competition_name='Liga QA', season='2026', status='LIVE', minute='67',
        kickoff_iso='2026-09-15T19:00:00+02:00', home_score=1, away_score=0,
        last_synced_at=observed.isoformat())
    raw.update(overrides)
    return build_realtime_match_state(raw, now=evaluated)


def codes(result):
    return {event['code'] for event in result['events']}


def test_older_provider_response_is_not_a_new_score_update():
    result = build_factual_change_summary(state(home_score=2), state(10, observed_seconds=-60))
    assert result['same_fixture'] is True
    assert result['comparison_state'] == 'OUT_OF_ORDER'
    assert result['reason'] == 'OLDER_PROVIDER_OBSERVATION'
    assert result['changed'] is False and result['events'] == []


def test_older_evaluation_is_rejected_even_with_a_later_provider_clock():
    result = build_factual_change_summary(state(), state(-10, observed_seconds=-20, home_score=2))
    assert result['reason'] == 'OLDER_EVALUATION'
    assert result['events'] == []


@pytest.mark.parametrize('field,value', [
    ('provider', 'another-provider'), ('season', '2027'),
    ('competition_id', 'other-league'), ('home_team_id', 'other-home'),
    ('away_team_id', 'other-away'),
])
def test_same_numeric_id_is_not_enough_when_known_identity_conflicts(field, value):
    after = state(20, home_score=2)
    after[field] = value
    result = build_factual_change_summary(state(), after)
    assert result['comparable'] is False
    assert result['events'] == []
    assert result['reason'] in {'SOURCE_CHANGED', 'IDENTITY_CONFLICT'}


def test_conflicting_long_identity_suffix_is_not_hidden_by_display_truncation():
    before, after = state(), state(20, home_score=2)
    before['home_team_id'], after['home_team_id'] = 'x' * 110 + 'a', 'x' * 110 + 'b'
    result = build_factual_change_summary(before, after)
    assert result['events'] == []
    assert result['reason'] == 'IDENTITY_CONFLICT'


@pytest.mark.parametrize('field,value', [
    ('contract', 'other-contract'), ('evaluated_at_madrid', 'broken'),
    ('evaluated_at_madrid', '2026-09-15T20:00:20'),
    ('is_live', 'false'), ('status_conflict', None), ('is_stale', 0),
])
def test_invalid_snapshot_cannot_be_used_to_announce_updates(field, value):
    after = state(20, home_score=2)
    after[field] = value
    result = build_factual_change_summary(state(), after)
    assert result['comparable'] is False
    assert result['events'] == []


@pytest.mark.parametrize('before,after,reason', [
    (None, state(), 'NO_BASELINE'), (state(), None, 'NO_CURRENT_STATE'),
    ('not-a-state', state(), 'INVALID_INPUT'), (state(), [], 'INVALID_INPUT'),
])
def test_unusable_input_returns_an_explicit_reason(before, after, reason):
    result = build_factual_change_summary(before, after)
    assert result['changed'] is False and result['events'] == []
    assert result['reason'] == reason


def test_historical_observation_is_not_announced_as_recovered_freshness():
    before = state(observed_seconds=-400)
    after = state(30, observed_seconds=-300, status='FT')
    result = build_factual_change_summary(before, after)
    event = next(e for e in result['events'] if e['code'] == 'FRESHNESS_CHANGE')
    assert event['after'] == 'OBSERVED'
    assert 'recientes' not in event['message']
    assert 'frescura en directo no está certificada' in event['message']


def test_genuinely_fresh_live_recovery_still_announces_recovery():
    result = build_factual_change_summary(state(observed_seconds=-400), state(20))
    assert any(e['code'] == 'FRESHNESS_CHANGE' and 'vuelve' in e['message'] for e in result['events'])


def test_future_clock_is_not_clamped_to_a_new_fresh_observation():
    result = build_factual_change_summary(state(), state(20, observed_seconds=1000, home_score=2))
    assert result['comparable'] is False
    assert result['reason'] == 'FUTURE_PROVIDER_OBSERVATION'
    assert 'SCORE_UPDATE' not in codes(result)


def test_clock_does_not_advance_from_evaluation_alone():
    after = state(20, observed_seconds=-30, home_score=2)
    result = build_factual_change_summary(state(), after)
    assert 'SCORE_UPDATE' not in codes(result)
    assert 'score' in result['suppressed_changes']
    assert result['comparison_state'] == 'INSUFFICIENT_EVIDENCE'


def test_replaying_identical_snapshot_has_no_factual_update():
    before = state()
    result = build_factual_change_summary(before, deepcopy(before))
    assert result['comparison_state'] == 'COMPARABLE'
    assert result['changed'] is False
    assert result['events'] == []


def test_expiration_without_new_provider_data_still_reports_degradation():
    after = state(300, observed_seconds=-30)
    result = build_factual_change_summary(state(), after)
    assert 'FRESHNESS_CHANGE' in codes(result)
    assert 'SCORE_UPDATE' not in codes(result)
    assert after['is_live'] is False


def test_disappearing_score_is_reported_as_unknown_not_zero():
    result = build_factual_change_summary(state(), state(20, away_score=None))
    event = next(e for e in result['events'] if e['code'] == 'SCORE_UNAVAILABLE')
    assert event['before'] == '1-0' and event['after'] is None
    assert '0-0' not in event['message']
    assert 'SCORE_UPDATE' not in codes(result)


@pytest.mark.parametrize('invalid', [nan, inf, -inf, -1, True, '2', {'token': 'do-not-expose'}])
def test_invalid_score_cannot_leak_or_be_published(invalid):
    after = state(20)
    after['score_home'] = invalid
    result = build_factual_change_summary(state(), after)
    assert 'SCORE_UPDATE' not in codes(result)
    assert 'do-not-expose' not in str(result)


def test_confirmed_zero_score_is_preserved():
    result = build_factual_change_summary(state(), state(20, home_score=0))
    event = next(e for e in result['events'] if e['code'] == 'SCORE_UPDATE')
    assert event['after'] == '0-0'
    assert 'gol' not in event['message'].casefold()


def test_downward_score_correction_with_new_observation_is_not_a_goal():
    result = build_factual_change_summary(state(home_score=2), state(20, home_score=1))
    event = next(e for e in result['events'] if e['code'] == 'SCORE_UPDATE')
    assert event['message'] == 'Marcador actualizado: 2-0 → 1-0.'
    assert 'GOAL' not in codes(result)


@pytest.mark.parametrize('mode', ['stale', 'conflict', 'unknown_clock'])
def test_uncertain_new_snapshot_does_not_announce_score_or_minute(mode):
    after = state(20, home_score=2, minute='70')
    if mode == 'stale':
        after = state(300, observed_seconds=0, home_score=2, minute='70')
    elif mode == 'conflict':
        after['status_conflict'] = True
    else:
        after['provider_observed_at'] = ''
        after['freshness_state'] = 'NOT_ESTABLISHED'
    result = build_factual_change_summary(state(), after)
    assert not {'SCORE_UPDATE', 'MINUTE_UPDATE'} & codes(result)


def test_missing_conflict_flag_is_not_a_resolved_conflict():
    before, after = state(), state(20)
    before['status_conflict'] = True
    del after['status_conflict']
    result = build_factual_change_summary(before, after)
    assert 'STATUS_CONFLICT_RESOLVED' not in codes(result)


@pytest.mark.parametrize('available,observed', [(False, True), (None, True), (True, False), (True, None)])
def test_contradictory_coverage_cannot_announce_available(available, observed):
    after = state(20)
    after['coverage']['lineups'] = {'state': 'AVAILABLE', 'available': available, 'observed': observed}
    result = build_factual_change_summary(state(), after)
    assert 'CAPABILITY_AVAILABLE' not in codes(result)


@pytest.mark.parametrize('new_state,available,code', [
    ('EMPTY_OBSERVED', False, 'CAPABILITY_EMPTY'),
    ('PARTIAL', True, 'CAPABILITY_PARTIAL'),
    ('STALE', True, 'CAPABILITY_STALE'),
    ('UNAVAILABLE', False, 'CAPABILITY_LOST'),
    ('NOT_ESTABLISHED', None, 'CAPABILITY_LOST'),
])
def test_loss_of_complete_coverage_has_an_explicit_kind(new_state, available, code):
    before, after = state(), state(20)
    before['coverage']['lineups'] = {'state': 'AVAILABLE', 'available': True, 'observed': True}
    after['coverage']['lineups'] = {'state': new_state, 'available': available, 'observed': new_state != 'NOT_ESTABLISHED'}
    result = build_factual_change_summary(before, after)
    event = next(e for e in result['events'] if e['code'] == code)
    assert event['capability'] == 'lineups'
    assert event['after'] == new_state


def test_historical_standings_can_be_available_even_if_live_clock_is_stale():
    before, after = state(observed_seconds=-400), state(20, observed_seconds=-400)
    after['coverage']['standings'] = {'state': 'AVAILABLE', 'available': True, 'observed': True}
    result = build_factual_change_summary(before, after)
    event = next(e for e in result['events'] if e['code'] == 'CAPABILITY_AVAILABLE')
    assert event['capability'] == 'standings'
    assert 'fresca' not in event['message'].casefold()


def test_equivalent_offsets_are_compared_as_instants():
    before, after = state(), state(20, home_score=2)
    for key in ['evaluated_at_madrid', 'provider_observed_at']:
        after[key] = datetime.fromisoformat(after[key]).astimezone(timezone.utc).isoformat()
    result = build_factual_change_summary(before, after)
    assert result['comparable'] is True
    assert 'SCORE_UPDATE' in codes(result)


def test_dst_fold_order_is_not_compared_as_wall_clock_text():
    before, after = state(), state(20, home_score=2)
    before.update(evaluated_at_madrid='2026-10-25T02:50:00+02:00', provider_observed_at='2026-10-25T02:49:30+02:00')
    after.update(evaluated_at_madrid='2026-10-25T02:10:00+01:00', provider_observed_at='2026-10-25T02:09:30+01:00')
    result = build_factual_change_summary(before, after)
    assert result['comparable'] is True
    assert 'SCORE_UPDATE' in codes(result)


def test_summary_preserves_both_inputs_and_is_deterministic():
    before, after = state(), state(20, home_score=2, lineups=[{'team': 'QA'}])
    original = deepcopy((before, after))
    first = build_factual_change_summary(before, after)
    second = build_factual_change_summary(before, after)
    assert (before, after) == original
    assert first == second


@pytest.mark.parametrize('invalid', [None, [], {}, 42, 'UNKNOWN_STATUS'])
def test_invalid_status_is_rejected_without_echoing_raw_payload(invalid):
    after = state(20, home_score=2)
    after['status_canonical'] = invalid
    result = build_factual_change_summary(state(), after)
    assert result['reason'] == 'INVALID_STATUS'
    assert result['events'] == []


def test_missing_source_is_not_silently_treated_as_same_provider():
    after = state(20, home_score=2)
    after['provider'] = ''
    result = build_factual_change_summary(state(), after)
    assert result['reason'] == 'SOURCE_NOT_ESTABLISHED'
    assert result['events'] == []


def test_unknown_clock_provenance_cannot_announce_current_score():
    after = state(20, home_score=2)
    after['provider_observed_at_source'] = 'page_rendered_at'
    result = build_factual_change_summary(state(), after)
    assert result['reason'] == 'OBSERVATION_PROVENANCE_NOT_ESTABLISHED'
    assert result['events'] == []


def test_same_score_with_later_observation_is_not_a_new_event():
    result = build_factual_change_summary(state(), state(20))
    assert result['events'] == []
    assert result['changed'] is False


def test_duplicate_provider_observation_in_another_offset_is_not_new():
    before, after = state(), state(20, observed_seconds=-30, home_score=2)
    after['provider_observed_at'] = datetime.fromisoformat(before['provider_observed_at']).astimezone(timezone.utc).isoformat()
    result = build_factual_change_summary(before, after)
    assert 'SCORE_UPDATE' not in codes(result)
    assert result['comparison_state'] == 'INSUFFICIENT_EVIDENCE'


def test_current_conflict_resolution_requires_new_provider_evidence():
    before, after = state(), state(20)
    before['status_conflict'] = True
    result = build_factual_change_summary(before, after)
    assert 'STATUS_CONFLICT_RESOLVED' in codes(result)
    after['provider_observed_at'] = before['provider_observed_at']
    without_new_evidence = build_factual_change_summary(before, after)
    assert 'STATUS_CONFLICT_RESOLVED' not in codes(without_new_evidence)
    assert 'conflict_resolution' in without_new_evidence['suppressed_changes']


def test_future_tolerance_matches_canonical_policy_not_an_independent_threshold():
    from engines.v935_launch_trust_engine import LIVE_FUTURE_SKEW_SECONDS
    before = state()
    allowed = state(20, observed_seconds=20 + LIVE_FUTURE_SKEW_SECONDS, home_score=2)
    rejected = state(20, observed_seconds=21 + LIVE_FUTURE_SKEW_SECONDS, home_score=2)
    assert build_factual_change_summary(before, allowed)['comparable'] is True
    assert build_factual_change_summary(before, rejected)['reason'] == 'FUTURE_PROVIDER_OBSERVATION'


@pytest.mark.parametrize('count', [0, -1, True, '2'])
def test_invalid_or_empty_count_does_not_claim_capability_available(count):
    after = state(20)
    after['coverage']['lineups'] = {'state': 'AVAILABLE', 'available': True, 'observed': True, 'count': count}
    assert 'CAPABILITY_AVAILABLE' not in codes(build_factual_change_summary(state(), after))


def test_summary_does_not_attempt_network_database_or_file_io(monkeypatch):
    import builtins
    import socket
    import sqlite3
    before, after = state(), state(20, home_score=2)
    attempts = []
    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('Summary must remain pure')
    with monkeypatch.context() as guard:
        guard.setattr(socket, 'create_connection', forbidden)
        guard.setattr(socket.socket, 'connect', forbidden)
        guard.setattr(sqlite3, 'connect', forbidden)
        guard.setattr(builtins, 'open', forbidden)
        result = build_factual_change_summary(before, after)
    assert 'SCORE_UPDATE' in codes(result)
    assert attempts == []
