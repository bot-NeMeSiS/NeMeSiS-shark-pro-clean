import json
from copy import deepcopy
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import pytest
from engines.match_odds_presentation import cached_match_odds

NOW=datetime(2026,10,5,0,0,tzinfo=ZoneInfo('Europe/Madrid'))

def record(age=5):
    return {'id':'persisted-odds-qa','home_team':'Local','away_team':'Visitante',
            'kickoff_iso':(NOW+timedelta(hours=12)).isoformat(),'status':'NS',
            'odds_h2h_json':json.dumps({'home':2.5,'draw':3.1,'away':2.9,
             'source':'The Odds API','bookmaker':'Casa registrada',
             'last_update':(NOW-timedelta(minutes=age)).isoformat()})}

def test_prices_are_visible_without_a_pick_and_do_not_mutate_input():
    match=record();before=deepcopy(match)
    view=cached_match_odds(match,now=NOW)
    assert view['available'] and view['current']
    assert [p['price'] for p in view['items']]==[2.5,3.1,2.9]
    assert match==before

def test_old_prices_remain_dated_history_never_current():
    view=cached_match_odds(record(360),now=NOW)
    assert view['available'] and not view['current']
    assert 'no se consideran vigentes' in view['message']
    assert view['observed_at'] and view['bookmaker']

@pytest.mark.parametrize('missing',['last_update','bookmaker','source'])
def test_missing_provenance_does_not_publish_prices(missing):
    match=record();payload=json.loads(match['odds_h2h_json']);payload.pop(missing)
    match['odds_h2h_json']=json.dumps(payload)
    assert not cached_match_odds(match,now=NOW)['available']

@pytest.mark.parametrize('price',[True,float('nan'),float('inf'),0,1,-2,'invalid'])
def test_invalid_prices_never_reach_client(price):
    match=record();payload=json.loads(match['odds_h2h_json']);payload.update(home=price,draw=price,away=price)
    match['odds_h2h_json']=json.dumps(payload)
    assert not cached_match_odds(match,now=NOW)['available']

def test_future_clock_and_finished_prices_are_not_current():
    assert not cached_match_odds(record(-5),now=NOW)['available']
    match=record();match.update(status='FT',home_score=1,away_score=0)
    view=cached_match_odds(match,now=NOW)
    assert view['available'] and not view['current']
