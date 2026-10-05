from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from engines.v935_launch_trust_engine import match_status_truth, classify_match_for_surface
from engines.v934_realtime_sports_engine import normalize_match


@pytest.mark.parametrize('status', ['LIVE', 'HT', '1H', '2H'])
@pytest.mark.parametrize('hours', [1, 24])
def test_fresh_live_signal_cannot_publish_future_fixture(status, hours):
    now = datetime(2026, 10, 4, 21, 0, tzinfo=ZoneInfo('Europe/Madrid'))
    kickoff = now + timedelta(hours=hours)
    match = {'id':'future-live-contract', 'home_team':'Local', 'away_team':'Visitante',
             'competition_name':'Liga', 'source':'persisted-provider-cache',
             'match_date':kickoff.date().isoformat(), 'kickoff_time':kickoff.strftime('%H:%M'),
             'status':status, 'minute':'45', 'home_score':1, 'away_score':0,
             'last_synced_at':now.isoformat()}
    truth = match_status_truth(match, now=now)
    assert truth['lifecycle'] == 'UPCOMING'
    assert truth['is_live'] is False
    assert truth['status_conflict'] is True
    assert truth['conflict_type'] == 'LIVE_FUTURE_KICKOFF'
    assert classify_match_for_surface(match, now=now)['live'] is False
    assert normalize_match(match, now=now)['is_live'] is False
    assert match['status'] == status


def test_future_guard_does_not_replace_finished_score_truth():
    now = datetime(2026, 10, 4, 21, 0, tzinfo=ZoneInfo('Europe/Madrid'))
    truth = match_status_truth({'status':'LIVE', 'strProgress':'FT', 'home_score':2,
                               'away_score':1, 'kickoff_iso':(now+timedelta(days=1)).isoformat()},now=now)
    assert truth['lifecycle'] == 'FINISHED'
    assert truth['conflict_type'] == 'LIVE_TERMINAL'


def test_stale_client_aliases_cannot_keep_old_live_or_upcoming_text(app_module):
    now = datetime.now(ZoneInfo('Europe/Madrid'))
    match = {'id':'stale-client-aliases','home_team':'Local','away_team':'Visitante',
             'status':'LIVE','source':'persisted-provider-cache',
             'kickoff_iso':(now-timedelta(hours=2)).isoformat(),
             'last_synced_at':(now-timedelta(minutes=10)).isoformat()}
    result = app_module.client_match_display_context(match,now_madrid=now)
    assert result['client_status_label'] == 'Datos retrasados'
    assert result['display_status_label'] == 'Datos retrasados'
    assert result['madrid_display'] == 'Datos retrasados'
    assert 'En directo' not in result['display_datetime']
    assert result['status'] == 'LIVE'

def test_stale_annotation_keeps_legacy_depth_out_of_live_and_upcoming(app_module):
    now = datetime.now(ZoneInfo('Europe/Madrid'))
    match = {'id':'stale-depth', 'home_team':'Local', 'away_team':'Visitante',
             'status':'LIVE', 'source':'persisted-provider-cache',
             'kickoff_iso':(now-timedelta(hours=2)).isoformat(),
             'last_synced_at':(now-timedelta(minutes=10)).isoformat()}
    result = app_module.annotate_match(match, favs={'team':set(),'league':set(),'match':set(),'all':[]}, include_timeline=False)
    assert result['live_depth']['state'] == 'STALE'
    assert result['live_depth']['label'] == 'Datos retrasados'
    assert result['live_depth']['badge'] != 'live'
    assert result['live_depth']['minute'] == ''
