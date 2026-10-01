"""Publication boundary regression: evidence-only rows must never become picks.

Only synthetic dictionaries are used. Database reads, writes, logs and network
are replaced before calling the real publisher. These tests reproduce a missing
check in the current scheduler helper; they must pass before this PR is merged.
"""
import math

import pytest


@pytest.fixture
def isolated_publisher(app_module, monkeypatch):
    calls = []
    monkeypatch.setattr(app_module, 'one', lambda *_a, **_k: {})
    monkeypatch.setattr(app_module, 'telegram_log', lambda *_a, **_k: None)

    def record(payload, **_kwargs):
        calls.append(payload)
        return {'id': 'SYNTHETIC-NOT-PERSISTED'}

    monkeypatch.setattr(app_module, 'create_or_update_pick', record)
    import requests
    def forbidden(*_args, **_kwargs):
        raise AssertionError('A publication-boundary test must never call a provider')
    monkeypatch.setattr(requests.sessions.Session, 'request', forbidden)
    return app_module.ensure_auto_pick_from_recommendation, calls


def candidate(**changes):
    # Deliberately high cosmetic score: it must not override the actual decision.
    return {'match_id': 'synthetic-fixture', 'selection': 'Local QA',
            'odds_value': 1.9, 'score': 99, 'risk': 'BAJO',
            'can_publish': True, 'decision': 'BET', **changes}


@pytest.mark.parametrize('decision,permission', [
    ('WAIT', False), ('NO_BET', False), ('BET', False),
    ('WAIT', True), ('NO_BET', True), ('BET', 'true'), ('BET', 1),
])
def test_non_publishable_decision_cannot_reach_storage(isolated_publisher, decision, permission):
    publish, writes = isolated_publisher
    result = publish(candidate(decision=decision, can_publish=permission))
    assert writes == [], 'The scheduler ignored the explicit publication boundary'
    assert result.get('created') is False


def test_missing_permission_is_not_permission(isolated_publisher):
    publish, writes = isolated_publisher
    row = candidate()
    row.pop('can_publish')
    result = publish(row)
    assert writes == []
    assert result.get('created') is False


@pytest.mark.parametrize('price', [math.nan, math.inf, -math.inf, True, 1.0, 0.0])
def test_non_finite_or_invalid_price_cannot_reach_storage(isolated_publisher, price):
    publish, writes = isolated_publisher
    result = publish(candidate(odds_value=price))
    assert writes == [], 'An invalid observation was treated as an executable quote'
    assert result.get('created') is False


@pytest.mark.parametrize('changes,reason', [
    ({'decision':'WAIT', 'can_publish':False}, 'analisis_no_publicable'),
    ({'decision':'NO_BET'}, 'analisis_no_publicable'),
    ({'can_publish':'true'}, 'analisis_no_publicable'),
    ({'odds_value':math.nan}, 'sin_cuota_valida'),
    ({'odds_value':math.inf}, 'sin_cuota_valida'),
    ({'odds_value':True}, 'sin_cuota_valida'),
])
def test_scheduler_reports_the_actual_blocker(app_module, monkeypatch, changes, reason):
    monkeypatch.setattr(app_module, 'v565_recommendation_pool', lambda **_kw: [candidate(**changes)])
    monkeypatch.setattr(app_module, 'telegram_log', lambda *_a, **_k: None)
    def forbidden(*_a, **_k):
        raise AssertionError('Rejected candidate reached the publisher')
    monkeypatch.setattr(app_module, 'ensure_auto_pick_from_recommendation', forbidden)
    result = app_module.refresh_auto_picks_basic()
    assert result['saved'] == 0
    assert result['auto_candidates'] == 0
    assert result['discarded'][0]['reason'] == reason


def test_admin_does_not_present_missing_model_as_a_low_score(app_module, monkeypatch):
    monkeypatch.setattr(app_module, 'get_upcoming_matches', lambda *_a, **_k: [{'id':'synthetic'}])
    monkeypatch.setattr(app_module, 'get_matches', lambda *_a, **_k: [])
    monkeypatch.setattr(app_module, 'rows', lambda *_a, **_k: [])
    monkeypatch.setattr(app_module, 'get_picks', lambda *_a, **_k: [])
    monkeypatch.setattr(app_module, 'v565_recommendation_pool', lambda **_kw: [candidate(decision='WAIT',can_publish=False)])
    report = app_module.v565_data_picks_health()
    assert any('validar el modelo' in line for line in report['actions'])
    assert not any('convertir las mejores' in line for line in report['actions'])
