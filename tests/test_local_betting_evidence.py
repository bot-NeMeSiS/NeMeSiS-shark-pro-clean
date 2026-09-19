import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest


def match(**extra):
    future = datetime.now(ZoneInfo('Europe/Madrid')) + timedelta(days=1)
    return dict(id='qa-betting', home_team='Local QA', away_team='Visitante QA',
                competition_name='Liga QA', kickoff_iso=future.isoformat(),
                match_date=future.date().isoformat(), status='NS', priority=100, **extra)


def test_calendar_priority_does_not_invent_confidence_stake_or_selection(app_module):
    result = app_module.v565_recommendation_for_match(match())
    assert result['confidence'] is None
    assert result['score'] is None
    assert result['risk'] is None
    assert result['odds_value'] is None
    assert result['decision'] == 'WAIT'
    assert result['can_publish'] is False
    assert set(result['evidence']) == {'facts','context','analysis','betting'}


def test_quote_is_an_observation_not_a_recommendation(app_module):
    stamp = datetime.now(ZoneInfo('Europe/Madrid')).isoformat()
    result = app_module.v565_recommendation_for_match(match(
        odds_h2h_json=json.dumps({'home':1.90,'draw':3.2,'away':4.1}),
        bookmaker='QA bookmaker', odds_source='SIMULATED_QA', odds_updated_at=stamp))
    assert result['decision'] == 'WAIT'
    assert result['confidence'] is None and result['odds_value'] is None
    quotes = result['evidence']['betting']['observations']
    assert [q['selection'] for q in quotes] == ['Local QA','Empate','Visitante QA']
    assert quotes[0]['odds'] == 1.90
    assert quotes[0]['source'] == 'SIMULATED_QA'
    assert quotes[0]['bookmaker'] == 'QA bookmaker'
    assert quotes[0]['observed_at'] == stamp
    assert result['evidence']['betting']['validity'] == 'NOT_VERIFIED'


@pytest.mark.parametrize('payload', [
    {'outcomes':[{'name':'Unrelated club', 'price':2.0}]},
    {'home':'NaN', 'draw':'Infinity', 'away':-2},
    [],
])
def test_unidentified_or_invalid_prices_do_not_become_team_odds(app_module,payload):
    odds = app_module.v565_extract_odds(match(odds_h2h_json=json.dumps(payload)))
    assert odds['available'] is False


def test_finished_and_stale_states_cannot_be_pre_match_recommendations(app_module):
    for status in ('FT', 'PEN', 'SUSP', 'LIVE'):
        row = match()
        row.update(status=status, updated_at='2000-01-01T00:00:00+01:00', home_score=0, away_score=0)
        result = app_module.v565_recommendation_for_match(row)
        assert result['decision'] == 'NO_BET'
        assert not result['can_publish']
        assert result['evidence']['facts']['status'] == app_module.canonical_match_status(row)


@pytest.mark.parametrize('path', ['/api/betting/convert-to-pick', '/api/v565/convert-recommendation'])
def test_wait_cannot_be_published_and_get_does_not_write(app_module, monkeypatch, path):
    client = app_module.app.test_client()
    client.get('/local-safe/login/admin?token=' + os.environ['NEMESIS_LOCAL_ACCESS_TOKEN'])
    def forbidden(*args, **kwargs):
        raise AssertionError('A watchlist row must not create/publish a pick')
    monkeypatch.setattr(app_module, 'create_or_update_pick', forbidden)
    assert client.get(path).status_code == 405
    assert client.post(path, json={'id':'local-match-2','match_id':'local-match-2'}).status_code == 403
    with client.session_transaction() as session:
        csrf = session['csrf_token']
    response = client.post(path, json={'id':'local-match-2','match_id':'local-match-2','publish':True},
                           headers={'X-CSRF-Token':csrf})
    assert response.status_code == 409
    assert response.json['published'] is False


@pytest.mark.parametrize('language,label', [('es','Esperar'),('en','Wait'),('fr','Attendre')])
def test_real_client_review_and_shark_lines_have_no_fabricated_confidence(app_module, language, label):
    client = app_module.app.test_client()
    client.get('/local-safe/login/client?token=' + os.environ['NEMESIS_LOCAL_ACCESS_TOKEN'])
    with client.session_transaction() as session:
        session['ui_locale'] = language
    response = client.get('/recommendations')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'data-betting-decision="WAIT"' in body and label in body
    assert 'None%' not in body and '/100' not in body
    assert 'data-v933-template="betting-review"' in body
    assert '<section class="band compact-band">' not in body
    assert '<div class="metric">' not in body
    with app_module.app.test_request_context('/shark'):
        lines = app_module._shark_recommendation_lines()
        assert lines and all('/100' not in line for line in lines)
