"""A bounded, diverse Home agenda built only from synthetic existing snapshots."""
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from engines.home_matchday import build_matchday

NOW = datetime(2026, 10, 9, 12, tzinfo=ZoneInfo('Europe/Madrid'))
LEAGUES = [('laliga','LaLiga','Spain'), ('premier-league','Premier League','England'),
           ('serie-a','Serie A','Italy'), ('bundesliga','Bundesliga','Germany'),
           ('ligue-1','Ligue 1','France'), ('uefa-champions-league','UEFA Champions League','Europe')]


def match(identity, league=LEAGUES[0], *, now=NOW, hours=2, state='upcoming', **extra):
    kickoff = now + timedelta(hours=hours)
    return dict(id=identity, home_team='Local '+identity, away_team='Visitante '+identity,
        competition_key=league[0], competition_name=league[1], country=league[2],
        source='SIMULATED_QA', kickoff_iso=kickoff.isoformat(), match_date=kickoff.date().isoformat(),
        kickoff_time=kickoff.strftime('%H:%M'), test_state=state,
        status='1H' if state=='live' else 'FT' if state=='finished' else 'NS',
        live_updated_at=now.isoformat(), updated_at=now.isoformat(), **extra)


def build(rows, **kwargs):
    return build_matchday(rows, now=NOW,
        status_for=lambda m: {'is_'+m['test_state']: True, 'is_stale':m.get('is_stale',False),
                             'status_conflict':m.get('status_conflict',False)},
        kickoff_for=lambda m: datetime.fromisoformat(m['kickoff_iso']),
        priority_for=lambda m: {'rank':10 if m['competition_key'] in {l[0] for l in LEAGUES} else 70}, **kwargs)


def items(result,lane):
    return [m for g in result[lane]['groups'] for m in g['matches']]


def test_spanish_volume_does_not_displace_other_major_leagues():
    rows=[match('es'+str(i)) for i in range(30)] + [match(l[0],l) for l in LEAGUES[1:]]
    original=deepcopy(rows)
    result=build(rows)
    assert {m['competition_key'] for m in items(result,'today')}=={l[0] for l in LEAGUES}
    assert result['today']['total']==35 and result['today']['shown']==12 and result['today']['has_more']
    assert rows==original
    items(result,'today')[0]['home_team']='changed locally'
    assert rows==original


def test_state_lanes_are_exclusive_and_keep_confirmed_results_separate():
    rows=[match('live',hours=-.5,state='live'), match('today'),match('next',hours=24),
          match('final',hours=-3,state='finished',home_score=0,away_score=0),
          match('stale',hours=-1,state='live',is_stale=True),
          match('conflict',hours=-1,state='live',status_conflict=True),
          match('past-unplayed',hours=-1), match('archive',hours=-72,state='finished')]
    result=build(rows+rows[:2])
    assert {lane:[m['id'] for m in items(result,lane)] for lane in ('live','today','upcoming','results')}=={
        'live':['live'],'today':['today'],'upcoming':['next'],'results':['final']}
    assert items(result,'results')[0]['home_score']==0


def test_upcoming_dates_and_result_dates_are_ordered_truthfully():
    rows=[match('later',hours=48),match('soon',hours=24),
          match('older',hours=-30,state='finished'),match('recent',hours=-2,state='finished')]
    result=build(rows)
    assert [m['id'] for m in items(result,'upcoming')]==['soon','later']
    assert [m['id'] for m in items(result,'results')]==['recent','older']


def test_unknown_and_lower_tiers_do_not_displace_known_major_competitions():
    rows=[match('local'+str(i),('local','Local','Spain')) for i in range(50)]
    rows += [match(l[0],l) for l in LEAGUES]
    result=build(rows,limit=6)
    assert {m['id'] for m in items(result,'today')}=={l[0] for l in LEAGUES}


def test_grouping_keeps_same_named_competitions_in_different_countries_separate():
    result=build([match('eng',('premier-league','Premier League','England')),
                  match('gha',('ghana-premier','Premier League','Ghana'))])
    assert len(result['today']['groups'])==2
    assert {g['country'] for g in result['today']['groups']}=={'England','Ghana'}


def test_home_uses_existing_canonical_global_competition_policy(app_module):
    for league in LEAGUES:
        assert app_module.sports_competition_priority(match(league[0],league))['tier']=='S'
    unknown=match('ghana',('unknown','Premier League','Ghana'))
    assert app_module.sports_competition_priority(unknown)['tier']!='S'


def test_home_context_is_read_only_scoped_and_does_not_change_shared_snapshot(app_module,monkeypatch):
    now=datetime.now(ZoneInfo('Europe/Madrid'))
    rows=[match('saved',now=now),match('other',now=now,is_favorite=True)]
    summary={'all_valid_matches':rows,'sports_home':{'important_today':rows[:1]}}
    original=deepcopy(summary)
    calls=[]
    def forbidden(*a,**kw): calls.append(1);raise AssertionError('unexpected IO')
    for name in ('rows','db','get_favorites','dashboard_data','get_public_home_sports_summary'):
        monkeypatch.setattr(app_module,name,forbidden)
    a=app_module.home_matchday_context(summary,favorites={'match':{'saved'}})
    b=app_module.home_matchday_context(summary,favorites={'match':{'other'}})
    selected=lambda result: {m['id'] for lane in ('today','upcoming') for m in items(result,lane) if m['is_favorite']}
    assert selected(a)=={'saved'} and selected(b)=={'other'}
    assert not calls and summary==original


@pytest.mark.parametrize('language',['es','en','fr'])
def test_all_home_lanes_are_visible_without_disclosures(app_module,language):
    from test_design02_r7_home_composition import render_home
    from test_design02_calendar_presentation import Structure
    rows=[match('live',hours=-.5,state='live'),match('today'),match('next',hours=24),match('done',hours=-4,state='finished')]
    dom=Structure(render_home(app_module,{'home_matchday':build(rows)},language))
    cards=[n for n in dom.nodes if 'data-v934-match-id' in n['attrs']]
    assert [n['attrs']['data-v934-match-id'] for n in cards]==['live','today','next','done']
    assert all(not any(p['tag']=='details' or 'hidden' in p['attrs'] for p in n['parents']) for n in cards)
    assert not any('data-personal-home' in n['attrs'] for n in dom.nodes)
    assert not any(n['attrs'].get('href')=='#personal-home-title' for n in dom.nodes)


def test_home_route_does_not_build_following_or_change_favorites(app_module,monkeypatch):
    monkeypatch.setattr(app_module,'current_session_user',lambda:{'id':'qa','membership':'FREE'})
    monkeypatch.setattr(app_module,'v932_safe_dashboard_data',lambda *a,**kw: ({'picks':[]},{'all_valid_matches':[]}))
    monkeypatch.setattr(app_module,'personal_home_agenda',lambda *a: pytest.fail('unused following read'))
    monkeypatch.setattr(app_module,'favorite_sets',lambda:{'all':[]})
    monkeypatch.setattr(app_module,'render_template',lambda template,**kw:kw)
    with app_module.app.test_request_context('/app'):
        result=app_module.v757_client_app_center_page()
    assert result['data']['home_matchday']['today']['shown']==0
    assert 'personal_home' not in result['data']
