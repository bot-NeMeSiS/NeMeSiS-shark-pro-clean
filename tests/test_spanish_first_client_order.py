"""Owner-directed display order; synthetic snapshots, not an audience measurement."""
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from engines import client_competition_order as ordering
from engines.client_live_surface import live_surface
from engines.home_matchday import build_matchday

NOW = datetime(2026, 10, 11, 12, tzinfo=ZoneInfo('Europe/Madrid'))
COMPETITIONS = [
    ('laliga','LaLiga','Spain',1,10),
    ('segunda-division','Segunda Division','Spain',2,25),
    ('copa-del-rey','Copa del Rey','Spain',3,25),
    ('supercopa-espana','Supercopa de Espana','Spain',4,25),
    ('uefa-champions-league','UEFA Champions League','Europe',5,10),
    ('premier-league','Premier League','England',6,10),
    ('serie-a','Serie A','Italy',7,10),
    ('bundesliga','Bundesliga','Germany',8,10),
    ('ligue-1','Ligue 1','France',9,10),
    ('primera-rfef','Primera RFEF','Spain',70,70),
    ('unknown','Premier League','Ghana',95,95),
]


def fixture(index, state='UPCOMING', suffix=''):
    key,name,country,display,legacy = COMPETITIONS[index]
    kickoff = NOW + timedelta(hours=2 if state == 'UPCOMING' else -1)
    return dict(id=key+suffix,competition_key=key,competition_name=name,country=country,
        home_team='QA Local',away_team='QA Rival',source='SIMULATED_QA',sport='Soccer',
        kickoff_iso=kickoff.isoformat(),match_date=kickoff.date().isoformat(),
        kickoff_time=kickoff.strftime('%H:%M'),test_rank=legacy,
        status='1H' if state == 'LIVE' else 'HT' if state == 'HALFTIME' else 'NS',
        status_info={'key':state,'is_live':state in {'LIVE','HALFTIME'},'is_upcoming':state=='UPCOMING'},
        home_score=1 if state != 'UPCOMING' else None,away_score=0 if state != 'UPCOMING' else None,
        live_updated_at=NOW.isoformat(),updated_at=NOW.isoformat(),
        sports_relevance={'competition_rank':display})


def agenda(rows, limit=None):
    return build_matchday(rows,now=NOW,status_for=lambda row:row['status_info'],
        kickoff_for=lambda row:datetime.fromisoformat(row['kickoff_iso']),
        priority_for=lambda row:{'rank':row['test_rank']},limit=limit)


@pytest.mark.parametrize('index',range(len(COMPETITIONS)))
def test_explicit_spanish_then_international_rank(index):
    row=fixture(index)
    assert ordering.competition_display_rank(row,row['test_rank']) == COMPETITIONS[index][3]


@pytest.mark.parametrize('country',['Spain','España','Espana'])
def test_spanish_country_names_keep_same_rank(country):
    row=fixture(1);row['country']=country
    assert ordering.competition_display_rank(row,95)==2


@pytest.mark.parametrize('updates',[
    {'competition_name':'Premier League','competition_key':'premier-league','country':'Ghana'},
    {'country':'Ghana','safe_country':'Spain'},
    {'competition_name':'LaLiga regional juvenil','competition_key':'other'},
    {'competition_name':'LaLiga','competition_key':'laliga','sport':'Basketball'},
    {'competition_name':'Segunda Division','competition_key':'segunda-division','country':'Uruguay'},
    {'source':'TheSportsDB','competition_id':'4328','competition_name':'LaLiga','country':'Spain'},
])
def test_unrelated_or_conflicting_competitions_are_not_promoted(updates):
    row=fixture(0);row.update(updates)
    assert ordering.competition_display_rank(row,95)==95


def test_numeric_ids_require_provider_and_do_not_guess_from_team_name():
    row={'competition_id':'4335','home_team':'Real Madrid','away_team':'Barcelona'}
    assert ordering.competition_display_rank(row,95)==95
    assert ordering.competition_display_rank({**row,'source':'TheSportsDB'},95)==1
    assert ordering.competition_display_rank({**row,'source':'API-Football'},95)==95


@pytest.mark.parametrize('state,lane',[('UPCOMING','today'),('LIVE','live')])
def test_home_spain_first_with_secondary_leagues_kept_collapsed(state,lane):
    rows=[fixture(index,state) for index in reversed(range(len(COMPETITIONS)))]
    before=deepcopy(rows); result=agenda(rows)
    groups=result[lane]['groups']
    assert [group['matches'][0]['id'] for group in groups]==[
        'laliga', 'segunda-division', 'copa-del-rey', 'supercopa-espana',
        'uefa-champions-league', 'premier-league', 'primera-rfef',
        'bundesliga', 'ligue-1', 'unknown', 'serie-a',
    ]
    assert sum(group['home_primary'] for group in groups)==6
    assert all(not group['home_primary'] for group in groups[6:])
    assert [group['presentation_group_key'] for group in groups[:6]] == [
        'country:espana', 'country:espana', 'country:espana', 'country:espana',
        'international', 'country:inglaterra',
    ]
    assert [group['presentation_group_key'] for group in groups[6:]] == [
        'country:espana', 'country:alemania', 'country:francia',
        'country:ghana', 'country:italia',
    ]
    assert result[lane]['shown']==len(rows) and rows==before


def test_bounded_home_reserves_other_major_leagues_even_with_many_spanish_matches():
    rows=[fixture(0,suffix=str(i)) for i in range(40)]+[fixture(i) for i in range(1,9)]
    result=agenda(rows,limit=9)
    groups=result['today']['groups']
    assert len(groups)==9
    assert [group['key'] for group in groups]==[
        'laliga', 'segunda-division', 'copa-del-rey', 'supercopa-espana',
        'uefa-champions-league', 'premier-league', 'bundesliga', 'ligue-1', 'serie-a',
    ]
    assert all(group['shown']==1 for group in groups)
    assert result['today']['total']==48 and result['today']['shown']==9


def test_madrid_days_and_hours_remain_primary_boundaries():
    spanish=fixture(0); spanish['kickoff_iso']=(NOW+timedelta(days=2)).isoformat()
    other=fixture(5); other['kickoff_iso']=(NOW+timedelta(days=1)).isoformat()
    result=agenda([spanish,other])
    assert [group['matches'][0]['id'] for group in result['upcoming']['groups']]==['premier-league','laliga']
    late=fixture(0,suffix='late');early=fixture(0,suffix='early')
    early['kickoff_iso']=(NOW+timedelta(hours=1)).isoformat()
    assert [row['id'] for row in agenda([late,early])['today']['groups'][0]['matches']]==['laligaearly','laligalate']


@pytest.mark.parametrize('lane,state',[('live','LIVE'),('break','HALFTIME'),('with_pick','LIVE')])
def test_live_orders_only_accepted_rows_without_mutation(lane,state):
    rows=[fixture(index,state) for index in reversed(range(9))]
    future=fixture(0,suffix='future')
    stale=fixture(0,'LIVE',suffix='stale');stale['live_updated_at']=(NOW-timedelta(minutes=10)).isoformat();stale['updated_at']=stale['live_updated_at']
    source={'live_experience':{'lane':lane,'matches':[future,stale]+rows+rows[:1]}}
    before=deepcopy(source)
    result=live_surface(source,now=NOW)
    assert [row['id'] for row in result['matches']]==[item[0] for item in COMPETITIONS[:9]]
    assert source==before and result['external_calls']==0


def test_global_keeps_existing_priority(monkeypatch):
    monkeypatch.setattr(ordering,'_POLICY',{'profile':'GLOBAL'})
    assert ordering.competition_display_rank(fixture(0),42)==42
    assert not ordering.spanish_first_enabled()


def test_ordering_does_not_read_db_or_network_after_import(monkeypatch):
    import sqlite3,urllib.request
    def deny(*a,**kw):raise AssertionError('Ordering must be in-memory only')
    monkeypatch.setattr(Path,'read_text',deny)
    monkeypatch.setattr(sqlite3,'connect',deny)
    monkeypatch.setattr(urllib.request,'urlopen',deny)
    assert ordering.competition_display_rank(fixture(0))==1
    assert agenda([fixture(0)])['today']['shown']==1


@pytest.mark.parametrize('sort_key',['importance','time'])
def test_real_calendar_groups_spanish_first_with_dates_and_picks_preserved(app_module,sort_key):
    # CI integration: real application config, relevance, identity and grouping.
    rows=[fixture(index) for index in reversed(range(9))]
    rows[0]['has_pick']=True
    before=deepcopy(rows)
    prepared=app_module.sort_matches_by_sports_relevance(rows,'calendar')
    grouped=app_module._calendar_group(prepared,sort_key=sort_key)
    assert [group['matches'][0]['id'] for group in grouped[0]['leagues']]==[item[0] for item in COMPETITIONS[:9]]
    assert rows==before
    assert app_module.sports_competition_priority(rows[0])['rank']==10
    assert app_module.sports_competition_priority(rows[0],audience=True)['weight']==app_module.sports_competition_priority(rows[0])['weight']


@pytest.mark.parametrize('invalid',[None,True,'1',float('nan'),float('inf'),-1,10**400])
def test_invalid_fallback_does_not_break_rendering(invalid):
    assert ordering.competition_display_rank({},invalid)==95
