"""Directo regression: live-only cards, real Flask aliases, no agenda filler."""
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import pytest
from engines.client_live_surface import live_surface
from test_directo_realtime_http import live_store


def row(status='LIVE'):
    now=datetime.now(ZoneInfo('Europe/Madrid'))
    return {'id':'surface-qa','source':'api-football','status':status,'minute':42,
            'home_team':'Club A','away_team':'Club B','competition_name':'Liga QA',
            'kickoff_iso':(now-timedelta(minutes=45)).isoformat(),
            'last_synced_at':now.isoformat(),'home_score':0,'away_score':0}


@pytest.mark.parametrize('status',['NS','FT','PST','SUSP','CANC','ABD'])
def test_all_is_not_permission_to_insert_nonlive_matches(status):
    item=row(status)
    if status=='NS':item['kickoff_iso']=(datetime.now(ZoneInfo('Europe/Madrid'))+timedelta(hours=2)).isoformat()
    result=live_surface({'live_experience':{'lane':'all','matches':[item]}})
    assert result['matches']==[] and result['lane']=='live'


@pytest.mark.parametrize('status',['LIVE','HT','ET','P'])
def test_active_play_including_break_is_retained(status):
    result=live_surface({'live_experience':{'lane':'live','matches':[row(status)]}})
    assert len(result['matches'])==1


def test_stale_does_not_become_a_featured_live_match():
    item=row();item['last_synced_at']='2020-01-01T00:00:00+01:00'
    assert live_surface({'live_experience':{'matches':[item]}})['matches']==[]


def test_previous_results_bookmark_is_explicitly_historical():
    result=live_surface({'live_experience':{'lane':'finished','matches':[row('FT')]}})
    assert result['historical'] and result['title']!='Ahora mismo' and len(result['matches'])==1


@pytest.mark.parametrize('path',['/live','/directo','/live-center','/en-directo','/live?f=all'])
def test_real_live_routes_never_render_upcoming_fallback(live_store,app_module,monkeypatch,path):
    client,put,now,_=live_store
    upcoming=put(status='NS',kickoff_time='23:59',id='future-in-directo-qa')
    original=app_module.v932_safe_dashboard_data
    def dashboard(*a,**kw):
        data,summary=original(*a,**kw);data['upcoming_matches']=[upcoming];return data,summary
    monkeypatch.setattr(app_module,'v932_safe_dashboard_data',dashboard)
    html=client.get(path).get_data(as_text=True)
    assert 'No hay partidos para este estado' in html
    assert 'data-v934-match-id="future-in-directo-qa"' not in html
    assert '<h2>Próximos encuentros' not in html
    assert 'NEMESIS-DIRECTO-LIVE-ONLY-V1' in html



def test_distinct_identity_and_no_input_mutation():
    from copy import deepcopy
    item=row(); original=deepcopy(item)
    data={'live_experience':{'matches':[item,item,{'status':'LIVE'}]}}
    result=live_surface(data)
    assert len(result['matches'])==1 and item==original
    result['matches'][0]['home_team']='changed in presentation'
    assert item['home_team']==original['home_team']


def test_grouped_source_and_unknown_lane_stay_live_only():
    live=row(); upcoming=row('NS')
    upcoming['id']='future';upcoming['kickoff_iso']=(datetime.now(ZoneInfo('Europe/Madrid'))+timedelta(hours=3)).isoformat()
    data={'live_experience':{'day_groups':[{'leagues':[{'matches':[upcoming,live]}]}]}}
    result=live_surface(data,'unsupported')
    assert [r['id'] for r in result['matches']]==[live['id']] and result['lane']=='live'


def test_break_filter_and_conflicting_status():
    playing=row();playing['id']='play'
    pause=row('HT');pause['id']='break'
    conflict=row();conflict['id']='conflict';conflict['raw_json']='{"fixture":{"status":{"short":"FT"}}}'
    data={'live_experience':{'matches':[playing,pause,conflict]}}
    assert [r['id'] for r in live_surface(data,'break')['matches']]==['break']
