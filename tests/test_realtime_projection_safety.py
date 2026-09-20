"""SIMULATED_QA regressions for one-clock projection and honest coverage."""
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

import engines.realtime_state_engine as projection
import engines.realtime_surface_adapter as surface
import engines.v935_launch_trust_engine as truth_engine
from engines.v935_launch_trust_engine import match_status_truth

NOW = datetime(2026, 9, 15, 20, 0, tzinfo=ZoneInfo('Europe/Madrid'))


def match(**overrides):
    row = dict(id='clock-qa', fixture_id='clock-qa', home_team='Local QA',
        away_team='Visitante QA', competition_name='Liga QA', source='provider-cache',
        kickoff_iso='2026-09-15T19:00:00+02:00', status='LIVE', home_score=1,
        away_score=0, minute='67', last_synced_at=(NOW-timedelta(seconds=30)).isoformat())
    row.update(overrides)
    return row


def legacy_clock(monkeypatch, value):
    original = truth_engine.madrid_now
    monkeypatch.setattr(truth_engine, 'madrid_now', lambda now=None: original(value if now is None else now))


@pytest.mark.parametrize('delta', [-600, 600])
def test_card_uses_explicit_clock_for_all_legacy_fields(monkeypatch, delta):
    legacy_clock(monkeypatch, NOW + timedelta(seconds=delta))
    row = match()
    card = surface.build_live_surface_state(row, now=NOW)
    state = card['realtime_state']
    truth = match_status_truth(row, now=NOW)
    assert card['status_label'] == 'En directo'
    assert card['minute_label'] == "67'"
    assert card['is_live'] is state['is_live'] is truth['is_live'] is True
    assert card['is_stale'] is state['is_stale'] is False
    assert card['live_age_seconds'] == state['freshness_seconds'] == 30
    assert card['stale_reason'] == state['stale_reason'] == ''
    assert card['status_conflict'] is state['status_conflict'] is False
    assert card['status_contract'] == state['sports_truth_contract']


def test_card_expiration_does_not_keep_a_legacy_live_status(monkeypatch):
    legacy_clock(monkeypatch, NOW)
    card = surface.build_live_surface_state(match(), now=NOW+timedelta(minutes=10))
    assert card['status_label'] == 'Datos retrasados'
    assert card['is_live'] is False and card['is_stale'] is True
    assert card['minute_label'] == ''
    assert card['live_age_seconds'] == card['realtime_state']['freshness_seconds'] == 630


def test_terminal_conflict_reconciles_legacy_flags_and_labels():
    card = surface.build_live_surface_state(match(strProgress='FT'), now=NOW)
    assert card['status_label'] == 'Finalizado'
    assert card['is_finished'] is True and card['is_live'] is False
    assert card['minute_label'] == ''
    assert card['status_conflict'] is True
    assert card['data_state'] == 'Señales deportivas en conflicto'


@pytest.mark.parametrize('status,label', [
    ('HT', 'Descanso'), ('FT', 'Finalizado'), ('SUSP', 'Suspendido'),
    ('PST', 'Aplazado'), ('CANC', 'Cancelado'), ('ABD', 'Abandonado'),
])
def test_canonical_lifecycle_label_is_preserved(status, label):
    card = surface.build_live_surface_state(match(status=status), now=NOW)
    assert card['status_label'] == label
    if not card['is_live']:
        assert card['minute_label'] == ''


@pytest.mark.parametrize('minute,extra,expected', [
    ('90+4', None, "90+4'"), ('45', '2', "45+2'"), ('67’', None, "67'"),
    ('0', None, "0'"), ('67', None, "67'"), ('bad', None, 'En directo'),
    ('999', None, 'En directo'),
])
def test_canonical_minute_and_card_label_agree(minute, extra, expected):
    card = surface.build_live_surface_state(match(minute=minute, extra=extra), now=NOW)
    assert card['minute_label'] == expected
    state_minute = card['realtime_state']['minute']
    if state_minute is not None:
        assert expected == f"{state_minute}'"


def test_card_restores_provider_clock_provenance_not_normalizer_alias():
    card = surface.build_live_surface_state(match(), now=NOW)
    assert card['realtime_state']['provider_observed_at_source'] == 'last_synced_at'
    assert card['provider_observed_at'] == match()['last_synced_at']


def test_invalid_priority_clock_never_falls_back_to_later_valid_field():
    row = match(live_updated_at='invalid-clock')
    state = projection.build_realtime_match_state(row, now=NOW)
    truth = match_status_truth(row, now=NOW)
    assert state['is_stale'] is truth['is_stale'] is True
    assert state['provider_observed_at'] == ''
    assert state['provider_observed_at_source'] == 'live_updated_at'
    assert state['freshness_seconds'] is None


def test_missing_source_not_invented_by_legacy_normalizer():
    row = match(); row.pop('source')
    card = surface.build_live_surface_state(row, now=NOW)
    assert card['provider'] == ''
    assert card['realtime_state']['provider'] == ''
    assert card['confidence_state'] == 'NOT_ESTABLISHED'


def test_supplied_partial_score_cannot_keep_an_old_full_legacy_label():
    card = surface.build_live_surface_state(match(away_score=None, score='9-9'), now=NOW)
    assert card['score_label'] == 'Resultado pendiente'
    assert card['is_pending'] is True
    assert card['realtime_state']['score_home'] == 1
    assert card['realtime_state']['score_away'] is None


def test_snapshot_freezes_one_evaluation_instant(monkeypatch):
    calls = []
    original = projection.madrid_now
    def ticking(now=None):
        if now is not None:
            return original(now)
        value = NOW + timedelta(seconds=300*len(calls)); calls.append(value)
        return value
    monkeypatch.setattr(projection, 'madrid_now', ticking)
    snapshot = projection.build_realtime_state_snapshot([match(), match(id='two', fixture_id='two')])
    assert len(calls) == 1
    assert {s['evaluated_at_madrid'] for s in snapshot['matches']} == {snapshot['evaluated_at_madrid']}
    assert snapshot['counts']['live'] == 2


def test_collection_freezes_clock_before_projecting_cards(monkeypatch):
    observed = []
    original = surface.build_live_surface_state
    def capture(row, now=None):
        observed.append(now)
        return original(row, now=now)
    monkeypatch.setattr(surface, 'build_live_surface_state', capture)
    surface.build_live_surface_collection([match(), match()])
    assert len(observed) == 2
    assert observed[0] is not None and observed[0] == observed[1]


@pytest.mark.parametrize('payload,state,available,observed', [
    ({'available': False, 'status': 'NOT_REQUESTED'}, 'NOT_REQUESTED', None, False),
    ({'available': False}, 'UNAVAILABLE', False, True),
    ({'available': True, 'observed': False}, 'NOT_ESTABLISHED', None, False),
    ({'status': 'ACCESS_FAILED', 'available': False}, 'ACCESS_FAILED', False, True),
    ({'status': 'PARTIAL', 'available': True, 'count': 1}, 'PARTIAL', True, True),
    ({'status': 'STALE', 'available': True, 'count': 2}, 'STALE', True, True),
    ({'state': 'AVAILABLE', 'available': False}, 'NOT_ESTABLISHED', None, False),
    ({'state': 'AVAILABLE', 'available': True, 'count': 0}, 'NOT_ESTABLISHED', None, False),
    ({'available': 'false'}, 'NOT_ESTABLISHED', None, False),
    ({'provider': 'api-football', 'note': 'configuration'}, 'NOT_ESTABLISHED', None, False),
    ({'errors': ['quota']}, 'NOT_ESTABLISHED', None, False),
])
@pytest.mark.parametrize('location', ['payload', 'coverage'])
def test_descriptor_is_not_counted_as_sporting_rows(payload, state, available, observed, location):
    row = match()
    if location == 'payload':
        row['lineups'] = payload
    else:
        row['coverage'] = {'lineups': payload}
    result = projection.build_realtime_match_state(row, now=NOW)['coverage']['lineups']
    assert result['state'] == state
    assert result['available'] is available
    assert result['observed'] is observed
    if 'count' not in payload:
        assert result['count'] is None


@pytest.mark.parametrize('count', [True, -1, '2', 2.5])
def test_invalid_descriptor_count_is_not_coverage(count):
    result = projection.build_realtime_match_state(match(lineups={'state':'AVAILABLE', 'available':True, 'count':count}), now=NOW)
    assert result['coverage']['lineups']['state'] == 'NOT_ESTABLISHED'
    assert result['coverage']['lineups']['available'] is None


@pytest.mark.parametrize('payload,expected_count', [([{'team':'QA'}], 1), ([], 0)])
def test_real_rows_keep_available_and_empty_observed(payload, expected_count):
    result = projection.build_realtime_match_state(match(lineups=payload), now=NOW)['coverage']['lineups']
    assert result['count'] == expected_count
    assert result['observed'] is True
    assert result['state'] == ('AVAILABLE' if expected_count else 'EMPTY_OBSERVED')


@pytest.mark.parametrize('key', ['data', 'response'])
def test_explicit_rows_wrapper_counts_rows_not_wrapper_metadata(key):
    result = projection.build_realtime_match_state(match(lineups={key:[{'team':'QA'}], 'provider':'provider-cache'}), now=NOW)
    assert result['coverage']['lineups']['count'] == 1
    assert result['coverage']['lineups']['available'] is True


def test_positive_flag_cannot_override_not_requested_descriptor():
    row = match(lineups_available=True, lineups={'available':False, 'status':'NOT_REQUESTED'})
    result = projection.build_realtime_match_state(row, now=NOW)['coverage']['lineups']
    assert result['state'] == 'NOT_REQUESTED'
    assert result['available'] is None


def test_negative_flag_cannot_be_overridden_by_nonempty_rows():
    row = match(lineups_available=False, lineups=[{'team':'QA'}])
    result = projection.build_realtime_match_state(row, now=NOW)['coverage']['lineups']
    assert result['available'] is False


def test_unknown_descriptor_does_not_leak_raw_error_fields():
    row = match(lineups={'errors':{'key':'PRIVATE_VALUE'}, 'arbitrary':'PRIVATE_VALUE'})
    result = projection.build_realtime_match_state(row, now=NOW)['coverage']['lineups']
    assert 'PRIVATE_VALUE' not in str(result)
    assert result['available'] is None


def test_same_observation_can_have_historical_coverage_with_stale_live_clock():
    row = match(last_synced_at=(NOW-timedelta(minutes=10)).isoformat(), standings=[{'position':1}])
    result = projection.build_realtime_match_state(row, now=NOW)
    assert result['is_stale'] is True
    assert result['coverage']['standings']['available'] is True
    assert result['coverage']['standings']['state'] == 'AVAILABLE'


def test_calls_are_pure_and_preserve_nested_inputs(monkeypatch):
    import builtins, socket, sqlite3
    row = match(lineups={'status':'NOT_REQUESTED', 'available':False})
    before = deepcopy(row)
    attempts = []
    def blocked(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('Unexpected I/O')
    with monkeypatch.context() as guard:
        guard.setattr(socket.socket, 'connect', blocked)
        guard.setattr(socket, 'create_connection', blocked)
        guard.setattr(sqlite3, 'connect', blocked)
        guard.setattr(builtins, 'open', blocked)
        result = surface.build_live_surface_state(row, now=NOW)
    assert attempts == []
    assert row == before
    result['realtime_state']['coverage']['lineups']['state'] = 'changed'
    assert row == before


@pytest.mark.parametrize('positive', [True, {'state':'AVAILABLE', 'available':True, 'count':2}])
def test_positive_coverage_does_not_override_unrequested_payload(positive):
    row = match(coverage={'lineups':positive}, lineups={'status':'NOT_REQUESTED', 'available':False})
    result = projection.build_realtime_match_state(row, now=NOW)['coverage']['lineups']
    assert result['state'] == 'NOT_ESTABLISHED'
    assert result['available'] is None


@pytest.mark.parametrize('payload', [[], {'state':'AVAILABLE', 'available':True, 'data':[]}])
def test_positive_flag_does_not_hide_observed_empty_content(payload):
    result = projection.build_realtime_match_state(match(lineups_available=True, lineups=payload), now=NOW)
    assert result['coverage']['lineups']['available'] is not True


def test_declared_count_must_agree_with_actual_rows():
    row = match(lineups={'state':'AVAILABLE', 'available':True, 'count':2, 'data':[{'team':'QA'}]})
    result = projection.build_realtime_match_state(row, now=NOW)['coverage']['lineups']
    assert result['state'] == 'NOT_ESTABLISHED'


def test_consistent_descriptor_and_rows_remain_available():
    row = match(lineups={'state':'AVAILABLE', 'available':True, 'count':1, 'data':[{'team':'QA'}]})
    result = projection.build_realtime_match_state(row, now=NOW)['coverage']['lineups']
    assert result == {'state':'AVAILABLE', 'available':True, 'observed':True, 'count':1}
