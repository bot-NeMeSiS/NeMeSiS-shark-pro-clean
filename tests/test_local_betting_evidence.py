import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from flask import render_template_string, session


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
        odds_h2h_json=json.dumps({
            'source':'The Odds API', 'last_update':stamp,
            'bookmaker':'QA bookmaker',
            'outcomes':[
                {'name':'Local QA','price':1.90},
                {'name':'Draw','price':3.2},
                {'name':'Visitante QA','price':4.1},
            ],
        }),
        bookmaker='QA bookmaker', odds_source='The Odds API', odds_updated_at=stamp))
    assert result['decision'] == 'WAIT'
    assert result['confidence'] is None and result['odds_value'] is None
    quotes = result['evidence']['betting']['observations']
    assert [q['selection'] for q in quotes] == ['Local QA','Empate','Visitante QA']
    assert quotes[0]['odds'] == 1.90
    assert quotes[0]['source'] == 'The Odds API'
    assert quotes[0]['bookmaker'] == 'QA bookmaker'
    assert quotes[0]['observed_at'] == stamp
    assert result['evidence']['betting']['validity'] == 'NOT_VERIFIED'
    assert result['market_forecast']['available'] is True
    assert result['market_forecast']['source'] == 'The Odds API'
    assert sum(item['probability_pct'] for item in result['market_forecast']['outcomes']) == 100.0
    assert result['can_publish'] is False


def test_customer_market_card_renders_probabilities_separately_from_shark_pick(app_module):
    stamp = datetime.now(ZoneInfo('Europe/Madrid')).isoformat()
    row = match()
    row['home_team'] = 'Granada CF'
    row['odds_h2h_json'] = json.dumps({
            'source':'The Odds API', 'last_update':stamp,
            'bookmaker':'QA bookmaker',
            'outcomes':[
                {'name':'Granada C.F.','price':2.0},
                {'name':'Draw','price':4.0},
                {'name':'Visitante QA','price':4.0},
            ],
        })
    row.update(bookmaker='QA bookmaker', odds_source='The Odds API', odds_updated_at=stamp)
    result = app_module.v565_recommendation_for_match(row)

    with app_module.app.test_request_context('/recommendations'):
        session['ui_locale'] = 'en'
        body = render_template_string(
            '{% from "components/betting_evidence.html" import betting_evidence with context %}'
            '{{ betting_evidence(result) }}', result=result,
        )

    assert 'data-market-forecast="current"' in body
    assert '50.0%' in body and body.count('25.0%') >= 2
    assert 'Market-implied estimate, not a SHARK forecast' in body
    assert 'Under review; there is no SHARK-approved pick for this match.' in body
    assert 'data-betting-decision="WAIT"' in body
    assert result['evidence']['betting']['observations'][0]['selection'] == 'Granada CF'
    assert result['evidence']['betting']['observations'][0]['odds'] == 2.0


def test_opportunities_pool_collapses_provider_aliases_without_mixing_quotes(app_module, monkeypatch):
    future = datetime.now(ZoneInfo('Europe/Madrid')) + timedelta(days=1)
    stamp = datetime.now(ZoneInfo('Europe/Madrid')).isoformat()
    api_row = match()
    api_row.update({
        'id': 'api-football-duplicate',
        'home_team': 'Tottenham',
        'away_team': 'Coventry',
        'competition_name': 'LaLiga EA Sports',
        'kickoff_iso': future.isoformat(),
        'source': 'API-Football',
        'external_id': 'fixture-1001',
        'home_logo': 'https://example.test/home.png',
        'away_logo': 'https://example.test/away.png',
        'odds_h2h_json': json.dumps({
            'source': 'The Odds API', 'last_update': stamp, 'bookmaker': 'Current QA',
            'outcomes': [
                {'name': 'Tottenham', 'price': 2.0},
                {'name': 'Draw', 'price': 4.0},
                {'name': 'Coventry', 'price': 4.0},
            ],
        }),
        'bookmaker': 'Current QA', 'odds_source': 'The Odds API', 'odds_updated_at': stamp,
    })
    alias_row = match()
    alias_row.update({
        'id': 'sportsdb-duplicate',
        'home_team': 'Tottenham Hotspur',
        'away_team': 'Coventry City',
        'competition_name': 'La Liga',
        'kickoff_iso': future.isoformat(),
        'source': 'TheSportsDB',
        'odds_h2h_json': json.dumps({
            'source': 'Unverified QA source', 'last_update': stamp, 'bookmaker': 'Other QA',
            'outcomes': [
                {'name': 'Tottenham Hotspur', 'price': 99.0},
                {'name': 'Draw', 'price': 99.0},
                {'name': 'Coventry City', 'price': 99.0},
            ],
        }),
        'bookmaker': 'Other QA',
    })
    monkeypatch.setattr(app_module, 'get_upcoming_matches', lambda *_args, **_kwargs: [alias_row, api_row])

    results = app_module.v565_recommendation_pool()

    assert len(results) == 1
    assert results[0]['match_id'] == 'api-football-duplicate'
    assert results[0]['evidence']['betting']['observations'][0]['source'] == 'The Odds API'
    assert results[0]['evidence']['betting']['observations'][0]['odds'] == 2.0


@pytest.mark.parametrize('difference', ['competition', 'kickoff'])
def test_opportunities_pool_keeps_distinct_fixtures_separate(app_module, monkeypatch, difference):
    first = match()
    second = match()
    first.update(id='fixture-one', home_team='Club A', away_team='Club B')
    second.update(id='fixture-two', home_team='Club A', away_team='Club B')
    if difference == 'competition':
        first['competition_name'] = 'La Liga'
        second['competition_name'] = 'FA Cup'
    else:
        kickoff = datetime.fromisoformat(first['kickoff_iso'])
        second['kickoff_iso'] = (kickoff + timedelta(minutes=1)).isoformat()
        second['match_date'] = (kickoff + timedelta(minutes=1)).date().isoformat()
        second['kickoff_time'] = (kickoff + timedelta(minutes=1)).strftime('%H:%M')
    monkeypatch.setattr(app_module, 'get_upcoming_matches', lambda *_args, **_kwargs: [first, second])

    results = app_module.v565_recommendation_pool()

    assert len(results) == 2


def test_market_page_uses_a_lightweight_read_only_context(app_module, monkeypatch):
    stamp = datetime.now(ZoneInfo('Europe/Madrid')).isoformat()
    future = datetime.now(ZoneInfo('Europe/Madrid')) + timedelta(days=1)
    row = {
        'id': 'market-route-qa', 'home_team': 'Local QA', 'away_team': 'Visitante QA',
        'competition_name': 'Liga QA', 'match_date': future.date().isoformat(),
        'kickoff_iso': future.isoformat(), 'status': 'NS',
        'odds_h2h_json': json.dumps({
            'source': 'The Odds API', 'bookmaker': 'QA bookmaker', 'last_update': stamp,
            'outcomes': [
                {'name': 'Local QA', 'price': 2.0},
                {'name': 'Draw', 'price': 4.0},
                {'name': 'Visitante QA', 'price': 4.0},
            ],
        }),
    }
    candidate = app_module.v565_recommendation_for_match(row)
    monkeypatch.setattr(app_module, 'current_session_user', lambda: None)
    monkeypatch.setattr(app_module, 'membership_allows', lambda *_args, **_kwargs: True)
    monkeypatch.setattr(app_module, 'v565_recommendation_pool', lambda **_kwargs: [candidate])
    monkeypatch.setattr(app_module, 'v565_data_picks_health', lambda review_candidates: {
        'upcoming_matches': 1,
        'fresh_market_forecasts': sum(item['market_forecast']['available'] for item in review_candidates),
        'recommendations': 0,
    })
    monkeypatch.setattr(app_module, 'dashboard_data', lambda: (_ for _ in ()).throw(
        AssertionError('The market page must not build the full operations dashboard')))

    response = app_module.app.test_client().get('/oportunidades')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'data-market-forecast="current"' in body
    assert 'market-forecast.css?v=20261018-1' in body
    assert 'Partidos con mercado 1X2 actual verificable' in body
    assert 'En observación; no hay una apuesta SHARK aprobada para este partido.' in body


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


def test_fresh_live_signal_for_tomorrow_cannot_be_a_waiting_recommendation(app_module):
    row = match()
    row.update(status='LIVE', updated_at=datetime.now(ZoneInfo('Europe/Madrid')).isoformat())
    result = app_module.v565_recommendation_for_match(row)
    assert result['evidence']['facts']['status']['status_conflict']
    assert result['decision'] == 'NO_BET'
    assert result['can_publish'] is False


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
