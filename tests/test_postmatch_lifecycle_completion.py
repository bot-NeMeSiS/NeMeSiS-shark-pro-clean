"""Isolated production dispatch, durable cache and final archive fault matrix."""
import json
import sqlite3
import urllib.error
import pytest
from test_postmatch_recovery import store, offline, NOW, MATCH, EVENT, transport
from engines.postmatch_sources import OfficialSources, SourceError
from engines.postmatch_store import Store
from engines.postmatch_recovery import tick, read_for_match, attach_detail, finish, media_handoff
from engines.postmatch_archive import normalize

LINEUP={'idEvent':'101','idPlayer':'456','strPlayer':'Jugador real de prueba',
        'idTeam':'10','strTeam':MATCH['home_team'],'strHome':'Yes','strSubstitute':'No',
        'strPosition':'Goalkeeper','intSquadNumber':'1'}
TIMELINE={'idEvent':'101','idTimeline':'789','strTimeline':'Goal','strTimelineDetail':'Normal Goal',
          'strHome':'Yes','strTeam':MATCH['home_team'],'intTime':'30','strPlayer':'Jugador de prueba'}


def install(monkeypatch, *, empty=False):
    calls=[]
    def fetch(request,timeout):
        calls.append(request.full_url.split('/')[-1].split('?')[0])
        if 'lookuplineup.php' in request.full_url:return {'lineup':[] if empty else [LINEUP]}
        if 'lookuptimeline.php' in request.full_url:return {'timeline':[] if empty else [TIMELINE]}
        if empty and 'lookupeventstats.php' in request.full_url:return {'eventstats':[]}
        return transport(request,timeout)
    monkeypatch.setattr(OfficialSources,'_http',staticmethod(fetch))
    return calls


def test_production_recovers_archive_after_statistics_without_duplicate_video_calls(store,monkeypatch):
    calls=install(monkeypatch)
    result=tick(store.path,clock=lambda:NOW)
    assert [job['kind'] for job in result['jobs']]==['statistics','archive']
    assert result['technical_status']=='PASS' and result['external_calls']==4
    assert result['content_pending'] and result['pending_jobs']==1
    assert calls.count('lookupevent.php')==1 and 'eventshighlights.php' not in calls
    detail={'match':MATCH}
    attach_detail(store.path,detail)
    assert detail['lineups'][0]['player_id']=='sportsdb-456'
    assert detail['timeline'][0]['id']=='sportsdb-timeline-789'
    assert len(read_for_match(store.path,MATCH)['sections'])==2
    next_result=tick(store.path,clock=lambda:NOW+10)
    assert next_result['external_calls']==0 and next_result['jobs'][0]['reason']=='MEDIA_PENDING'
    assert len(calls)==4
    with store.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM sportsdb_match_highlights').fetchone()[0]==0
        assert conn.execute('SELECT score FROM matches').fetchone()[0]=='2-1'


def test_archive_cache_survives_restart_and_identical_receipts_are_idempotent(store,monkeypatch):
    calls=install(monkeypatch)
    tick(store.path,clock=lambda:NOW)
    jid=next(j['id'] for j in Store(store.path).snapshot()['jobs'] if j['kind']=='archive')
    Store(store.path).requeue(jid,'offline-test')
    with store.connection(True) as conn:conn.execute('UPDATE postmatch_jobs SET due_at=? WHERE id=?',(NOW+60,jid))
    result=tick(store.path,clock=lambda:NOW+60)
    assert result['external_calls']==0 and len(calls)==4
    with store.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM postmatch_sections').fetchone()[0]==2
        assert conn.execute('SELECT SUM(used) FROM postmatch_source_budget').fetchone()[0]==4


def test_empty_success_is_pass_with_scheduled_content_pending(store,monkeypatch):
    install(monkeypatch,empty=True)
    result=tick(store.path,clock=lambda:NOW)
    assert result['technical_status']=='PASS' and result['content_pending']
    assert {j['reason'] for j in result['jobs']}=={'NO_STATISTICS','NO_POSTMATCH_DETAILS'}
    with store.connection() as conn:
        jobs=conn.execute("SELECT attempts,checks,due_at FROM postmatch_jobs WHERE state='RETRY'").fetchall()
        assert all(j['attempts']==0 and j['checks']==1 and j['due_at']>NOW for j in jobs)


def test_budget_deferrals_preserve_all_three_kinds_across_restarts(store,monkeypatch):
    install(monkeypatch)
    with store.connection(True) as conn:
        conn.execute("INSERT INTO postmatch_source_budget VALUES('thesportsdb','2026-10-01',60)")
    result=tick(store.path,clock=lambda:NOW)
    assert result['external_calls']==0 and result['technical_status']=='PARTIAL'
    snapshot=Store(store.path).snapshot()
    assert {j['kind'] for j in snapshot['jobs']}=={'statistics','archive','highlights'}
    assert all(j['attempts']==0 for j in snapshot['jobs'])
    assert all(j['state']!='FAILED' for j in snapshot['jobs'])


@pytest.mark.parametrize('reason',['MISSING_PROVIDER_ID','SOURCE_DISABLED','NO_APPROVED_SOURCE','PARTIAL_COVERAGE'])
def test_dependencies_never_exhaust_error_attempts(store,reason):
    store.discover(NOW)
    with store.connection(True) as conn:
        conn.execute('UPDATE postmatch_jobs SET attempts=4')
    for _ in range(7):
        job=store.claim(NOW)
        result=finish(store,job,{'reasons':[reason],'external_calls':0},NOW)
        assert result['state']=='RETRY'
        with store.connection(True) as conn:
            conn.execute('UPDATE postmatch_jobs SET due_at=?',(NOW,))
    assert all(j['attempts']==4 for j in store.snapshot()['jobs'])


@pytest.mark.parametrize('change',[{'idEvent':'999'},{'strTeam':'Wrong team'},{'idPlayer':''}])
def test_lineup_identity_and_required_evidence_are_strict(change):
    with pytest.raises(SourceError):
        normalize([{**LINEUP,**change}],'lineups','thesportsdb',EVENT,MATCH,'101')


def test_archive_does_not_replace_primary_sections_or_leak_into_changed_identity(store,monkeypatch):
    install(monkeypatch);tick(store.path,clock=lambda:NOW)
    primary={'match':MATCH,'lineups':[{'player_id':'primary'}],'timeline':[{'id':'primary'}]}
    attach_detail(store.path,primary)
    assert primary['lineups']==[{'player_id':'primary'}] and primary['timeline']==[{'id':'primary'}]
    assert read_for_match(store.path,{**MATCH,'home_team':'Another'})['sections']=={}
    with store.connection(True) as conn:conn.execute("UPDATE matches SET status='AET'")
    assert read_for_match(store.path,{**MATCH,'status':'AET'})['sections']=={}


def test_corrupt_cache_is_storage_failure_not_empty_success(store,monkeypatch):
    install(monkeypatch);tick(store.path,clock=lambda:NOW)
    jid=next(j['id'] for j in store.snapshot()['jobs'] if j['kind']=='archive')
    store.requeue(jid,'offline-test')
    with store.connection(True) as conn:conn.execute('UPDATE postmatch_jobs SET due_at=? WHERE id=?',(NOW+60,jid))
    with store.connection(True) as conn:conn.execute("UPDATE postmatch_request_cache SET payload_json='not json'")
    result=tick(store.path,clock=lambda:NOW+60)
    assert result['technical_status']=='FAIL' and result['external_calls']==0
    assert any(j['reason']=='STORAGE_UNAVAILABLE' for j in result['jobs'])


def test_disk_reserve_defers_archive_before_buying_calls(store,monkeypatch):
    calls=install(monkeypatch)
    monkeypatch.setattr('engines.postmatch_archive._disk_free_bytes',lambda conn:0)
    result=tick(store.path,clock=lambda:NOW)
    archive=next(j for j in result['jobs'] if j['kind']=='archive')
    assert archive['reason']=='ARCHIVE_BUDGET' and archive['external_calls']==0
    assert result['technical_status']=='PARTIAL' and len(calls)==2


def test_exact_final_provider_memory_avoids_identity_lookup(store,monkeypatch):
    calls=install(monkeypatch)
    with store.connection(True) as conn:
        conn.execute('ALTER TABLE matches ADD COLUMN raw_json TEXT')
        conn.execute('UPDATE matches SET raw_json=?',(json.dumps(EVENT),))
    result=tick(store.path,clock=lambda:NOW)
    assert result['external_calls']==3 and 'lookupevent.php' not in calls


def test_corrected_period_requeues_archive_without_restarting_completed_current_scope(store,monkeypatch):
    install(monkeypatch);tick(store.path,clock=lambda:NOW)
    with store.connection(True) as conn:conn.execute("UPDATE matches SET status='AET'")
    store.discover(NOW,include_archive=True)
    archive=next(j for j in store.snapshot()['jobs'] if j['kind']=='archive')
    assert archive['state']=='PENDING'
    with store.connection(True) as conn:
        for section in ('events','lineups'):
            conn.execute('INSERT INTO postmatch_sections(match_id,identity,section,source,reference,scope,payload_json,observed_at,digest) '
                         "SELECT match_id,identity,section,source,reference,'INCLUDING_EXTRA_TIME',payload_json,observed_at,digest||'aet' "
                         'FROM postmatch_sections WHERE section=?',(section,))
        conn.execute("UPDATE postmatch_jobs SET state='COMPLETE' WHERE kind='archive'")
    store.discover(NOW,include_archive=True)
    assert next(j for j in store.snapshot()['jobs'] if j['kind']=='archive')['state']=='COMPLETE'


def test_inventory_cursor_survives_restart_and_reaches_deep_history(store):
    old={**MATCH,'id':'deep-old','match_date':'2020-01-01'}
    with store.connection(True) as conn:
        conn.execute('INSERT INTO matches VALUES('+','.join('?' for _ in old)+')',tuple(old.values()))
    store.discover(NOW,include_archive=True,inventory_batch=1)
    assert store.snapshot()['inventory_cursor']['row_cursor']==1
    Store(store.path).discover(NOW,include_archive=True,inventory_batch=1)
    assert store.snapshot()['inventory_cursor']['row_cursor']==2
    assert len([j for j in store.snapshot()['jobs'] if j['match_id']=='deep-old'])==3
    Store(store.path).discover(NOW,include_archive=True,inventory_batch=1)
    assert len(store.snapshot()['jobs'])==6


def test_recent_archive_precedes_deep_statistics_and_uses_editorial_tie_break(store):
    old={**MATCH,'id':'old-history','match_date':'2020-01-01'}
    important={**MATCH,'id':'important-recent'}
    with store.connection(True) as conn:
        for match in (old,important):
            conn.execute('INSERT INTO matches VALUES('+','.join('?' for _ in match)+')',tuple(match.values()))
    store.discover(NOW,include_archive=True,priority=lambda m:10 if m['id']=='important-recent' else 0)
    job=store.claim(NOW,prefer_critical=True)
    assert job['kind']=='statistics' and job['match_id']=='important-recent'
    with store.connection(True) as conn:
        conn.execute("UPDATE postmatch_jobs SET state='COMPLETE',lease_until=0 WHERE kind='statistics' AND match_id<>'old-history'")
    job=store.claim(NOW,prefer_critical=True)
    assert job['kind']=='archive' and job['match_id']=='important-recent'


def test_future_pending_is_visible_when_an_idle_tick_is_pass(store):
    store.discover(NOW,include_archive=True)
    with store.connection(True) as conn:conn.execute('UPDATE postmatch_jobs SET due_at=?',(NOW+3600,))
    result=tick(store.path,clock=lambda:NOW)
    assert result['technical_status']=='PASS' and result['result']=='IDLE'
    assert result['content_pending'] and result['pending_jobs']==3


def test_provider_auth_error_is_not_hidden_by_a_later_cooldown_or_empty_response(store,monkeypatch):
    def fetch(request,timeout):
        if 'lookuptimeline.php' in request.full_url:
            raise urllib.error.HTTPError(request.full_url,401,'blocked',{},None)
        if 'lookuplineup.php' in request.full_url:return {'lineup':[]}
        return transport(request,timeout)
    monkeypatch.setattr(OfficialSources,'_http',staticmethod(fetch))
    result=tick(store.path,clock=lambda:NOW)
    assert result['technical_status']=='FAIL'
    archive=next(j for j in result['jobs'] if j['kind']=='archive')
    assert archive['reason']=='ACCESS_DENIED' and archive['technical_errors']==['ACCESS_DENIED']


def test_crash_after_provider_cache_keeps_original_receipt_time_on_recovery(store,monkeypatch):
    calls=install(monkeypatch)
    store.discover(NOW,include_archive=True)
    with store.connection(True) as conn:conn.execute("UPDATE postmatch_jobs SET state='CANCELLED' WHERE kind='statistics'")
    job=store.claim(NOW,prefer_critical=True)
    source=OfficialSources(store,job,store.config(),deadline=NOW+20,clock=lambda:NOW)
    assert source.archive(MATCH)['external_calls']==3  # Simulate a crash before finish commits receipts.
    result=tick(store.path,clock=lambda:NOW+91)
    assert result['external_calls']==0 and len(calls)==3
    with store.connection() as conn:
        assert {r[0] for r in conn.execute('SELECT observed_at FROM postmatch_sections')}=={NOW}


def test_api_football_archive_is_exact_and_cached_network_off_recovery_does_not_buy_calls(store,monkeypatch):
    store.configure(enabled=True,sources=['api_football'],daily_limit=60,actor='offline-test',confirmed=True)
    monkeypatch.setenv('API_FOOTBALL_KEY','offline-only')
    monkeypatch.setenv('ENABLE_API_FOOTBALL_PROVIDER','true')
    monkeypatch.setenv('ENABLE_API_SPORTS_NETWORK_CALLS','true')
    with store.connection(True) as conn:
        conn.execute('CREATE TABLE api_football_live_snapshots(match_id TEXT,fixture_id TEXT)')
        conn.execute('INSERT INTO api_football_live_snapshots VALUES(?,?)',(MATCH['id'],'505'))
    fixture={'fixture':{'id':505,'date':'2026-09-30T16:00:00Z','status':{'short':'FT'}},
             'teams':{'home':{'id':10,'name':MATCH['home_team']},'away':{'id':20,'name':MATCH['away_team']}},
             'league':{'name':MATCH['competition_name']}}
    calls=[]
    def fetch(request,timeout):
        calls.append(request.full_url)
        if 'fixtures/statistics' in request.full_url:return {'response':[]}
        if 'fixtures/events' in request.full_url:return {'response':[{'team':{'id':10},'time':{'elapsed':0},
                 'type':'Goal','detail':'Normal Goal','player':{'name':'Test'}}]}
        if 'fixtures/lineups' in request.full_url:return {'response':[{'team':{'id':10},'formation':'4-4-2',
             'startXI':[{'player':{'id':99,'name':'Test','pos':'G','number':1}}],'substitutes':[]}]}
        return {'response':[fixture]}
    monkeypatch.setattr(OfficialSources,'_http',staticmethod(fetch))
    result=tick(store.path,clock=lambda:NOW)
    assert result['external_calls']==4 and result['technical_status']=='PASS'
    recorded=read_for_match(store.path,MATCH)['sections']
    assert recorded['events']['items'][0]['minute']=='0'
    assert recorded['lineups']['items'][0]['player_id']=='api-football-99'
    jid=next(j['id'] for j in store.snapshot()['jobs'] if j['kind']=='archive')
    store.requeue(jid,'offline-test')
    with store.connection(True) as conn:conn.execute('UPDATE postmatch_jobs SET due_at=? WHERE id=?',(NOW+60,jid))
    monkeypatch.setenv('ENABLE_API_SPORTS_NETWORK_CALLS','false')
    assert tick(store.path,clock=lambda:NOW+60)['external_calls']==0 and len(calls)==4


def test_cache_drops_secret_fields_without_changing_event_evidence(store,monkeypatch):
    calls=install(monkeypatch)
    def fetch(request,timeout):return {'events':[{**EVENT,'api_key':'PRIVATE'}],'headers':{'Authorization':'PRIVATE'}}
    monkeypatch.setattr(OfficialSources,'_http',staticmethod(fetch))
    store.discover(NOW);job=store.claim(NOW)
    source=OfficialSources(store,job,store.config(),deadline=NOW+20,clock=lambda:NOW)
    assert source.sportsdb_event(MATCH)['idEvent']=='101'
    with store.connection() as conn:
        assert 'PRIVATE' not in conn.execute('SELECT payload_json FROM postmatch_request_cache').fetchone()[0]
