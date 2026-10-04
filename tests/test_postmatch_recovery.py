"""Offline post-match fault matrix; synthetic events never leave temporary databases."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import time
import json
from pathlib import Path
import sqlite3
import urllib.error

import pytest

from engines.postmatch_store import Store, StaleLease, BudgetStopped, identity, is_final
from engines.postmatch_sources import OfficialSources, SourceError, validate_rows, match_event
from engines.postmatch_recovery import tick, finish, save_statistics, read_for_match, attach_detail


@pytest.mark.parametrize('reason', ['DAILY_BUDGET', 'TICK_BUDGET', 'SOURCE_COOLDOWN'])
def test_controlled_deferral_does_not_exhaust_error_attempts(store, reason):
    store.discover(NOW)
    with store.connection(True) as conn:
        first = conn.execute('SELECT min(id) FROM postmatch_jobs').fetchone()[0]
        conn.execute('DELETE FROM postmatch_jobs WHERE id<>?', (first,))
        conn.execute('UPDATE postmatch_jobs SET attempts=4')
    for _ in range(6):
        job = store.claim(NOW)
        result = finish(store, job, {'reasons':[reason], 'external_calls':0}, NOW)
        assert result['state'] == 'RETRY'
        with store.connection(True) as conn:
            assert conn.execute('SELECT attempts FROM postmatch_jobs').fetchone()[0] == 4
            conn.execute('UPDATE postmatch_jobs SET due_at=?', (NOW,))


@pytest.mark.parametrize('local_time', ['2026-10-24T23:30:00+02:00', '2026-10-25T02:30:00+01:00'])
def test_daily_budget_waits_until_next_madrid_day_including_dst(store, local_time):
    from zoneinfo import ZoneInfo
    from datetime import timedelta
    now = datetime.fromisoformat(local_time).timestamp()
    store.discover(NOW)
    with store.connection(True) as conn:
        first = conn.execute('SELECT min(id) FROM postmatch_jobs').fetchone()[0]
        conn.execute('DELETE FROM postmatch_jobs WHERE id<>?', (first,))
    job = store.claim(now)
    result = finish(store, job, {'reasons':['DAILY_BUDGET'], 'external_calls':0}, now)
    due = datetime.fromtimestamp(result['due_at'], ZoneInfo('Europe/Madrid'))
    today = datetime.fromtimestamp(now, ZoneInfo('Europe/Madrid')).date()
    assert due.date() == today + timedelta(days=1)
    assert (due.hour, due.minute, due.second) == (0, 0, 5)
    assert store.claim(result['due_at'] - 1) is None
    assert store.claim(result['due_at']) is not None


def test_real_network_errors_still_exhaust_attempts(store):
    store.discover(NOW)
    with store.connection(True) as conn:
        conn.execute('UPDATE postmatch_jobs SET attempts=4')
    job = store.claim(NOW)
    result = finish(store, job, {'reasons':['NETWORK'], 'external_calls':1}, NOW)
    assert result['state'] == 'FAILED'

NOW = datetime(2026, 9, 30, 22, tzinfo=timezone.utc).timestamp()
MATCH = {'id':'pm-test', 'external_id':'sportsdb-101', 'source':'TheSportsDB',
         'home_team':'Equipo Uno', 'away_team':'Equipo Dos', 'league_id':'4328',
         'competition_name':'English Premier League', 'league_name':'English Premier League',
         'match_date':'2026-09-30', 'kickoff_time':'18:00', 'status':'FT',
         'score':'2-1', 'home_score':2, 'away_score':1}
EVENT = {'idEvent':'101','strHomeTeam':'Equipo Uno','strAwayTeam':'Equipo Dos',
         'strLeague':'English Premier League','idLeague':'4328','dateEvent':'2026-09-30',
         'strTimestamp':'2026-09-30T16:00:00+00:00','strStatus':'Match Finished',
         'intHomeScore':'2','intAwayScore':'1','strVideo':'https://www.youtube.com/watch?v=testVideo01',
         'strEvent':'Equipo Uno vs Equipo Dos'}
STATS = [('Total Shots','12','8'),('Shots on Goal','5','3'),('Ball Possession','55','45'),
         ('Corner Kicks','3','0'),('Fouls','8','10'),('Yellow Cards','0','1'),('Red Cards','0','0')]


@pytest.fixture
def store(tmp_path):
    path = tmp_path/'test.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE matches (' + ','.join(key + (' INTEGER' if key.endswith('_score') else ' TEXT') for key in MATCH) + ')')
        conn.execute('INSERT INTO matches VALUES(' + ','.join('?' for _ in MATCH) + ')', tuple(MATCH.values()))
    result = Store(path)
    result.configure(enabled=True, sources=['thesportsdb'], daily_limit=60, actor='test-admin', confirmed=True)
    return result


def transport(request, timeout):
    if 'lookupeventstats.php' in request.full_url:
        return {'eventstats':[{'idEvent':'101','strStat':label,'intHome':home,'intAway':away} for label,home,away in STATS]}
    if 'lookupevent.php' in request.full_url or 'eventsday.php' in request.full_url:
        return {'events':[dict(EVENT)]}
    raise AssertionError('Unexpected network endpoint')


def factory(store, job, config, **kwargs):
    return OfficialSources(store, job, config, transport=transport, **kwargs)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv('THESPORTSDB_KEY','local-test-secret-never-log')
    for name in ('API_FOOTBALL_KEY','API_FOOTBALL_API_KEY','API_SPORTS_KEY','APISPORTS_KEY'):
        monkeypatch.delenv(name, raising=False)
    def deny(*args, **kwargs):
        raise AssertionError('No real network in unit tests')
    monkeypatch.setattr('urllib.request.urlopen', deny)


def test_disabled_is_read_only_and_does_not_create_database(tmp_path):
    path = tmp_path/'absent.sqlite'
    result = tick(path)
    assert result['result'] == 'SKIPPED_DISABLED'
    assert not path.exists()


def test_requires_explicit_source_permission(store):
    with pytest.raises(ValueError):
        store.configure(enabled=True,sources=['thesportsdb'],daily_limit=60,actor='admin',confirmed=False)
    with pytest.raises(ValueError):
        store.configure(enabled=True,sources=['arbitrary_website'],daily_limit=60,actor='admin',confirmed=True)


def test_real_workers_recover_stats_and_queue_video_review(store):
    result = tick(store.path, clock=lambda:NOW, source_factory=factory)
    assert result['processed'] == 2
    assert result['external_calls'] == 2  # one event lookup shared by both jobs, plus statistics
    assert {row['state'] for row in result['jobs']} == {'COMPLETE','REVIEW_REQUIRED'}
    assert result['result'] == 'COMPLETE' and result['content_pending']  # Technical completion does not approve rights.
    snap = read_for_match(store.path, MATCH)
    assert len(snap['items']) == 7
    zero = next(row for row in snap['items'] if row['key']=='red_cards')
    assert zero['home'] == zero['away'] == '0'
    assert zero['source'] == 'thesportsdb'
    with store.connection() as conn:
        media = dict(conn.execute('SELECT * FROM sportsdb_match_highlights').fetchone())
        assert media['match_id'] == MATCH['id']
        assert media['rights_status'] not in {'PROVIDER_ALLOWED','LICENSED','OWNED'}
        assert conn.execute('SELECT score FROM matches').fetchone()[0] == '2-1'
    assert tick(store.path, clock=lambda:NOW+10, source_factory=factory)['result'] == 'IDLE'
    assert len(Store(store.path).snapshot()['jobs']) == 2  # persistence, no dedupe reset


@pytest.mark.parametrize('status,score',[('NS',''),('2H','2-1'),('PST','2-1'),('CANC',''),('FT','')])
def test_does_not_infer_final_from_clock_or_score(store,status,score):
    with store.connection(True) as conn:
        conn.execute('UPDATE matches SET status=?,score=?,home_score=NULL,away_score=NULL',(status,score))
    assert store.discover(NOW) == 0


def test_dry_run_does_not_enqueue_or_call_providers(store):
    result = tick(store.path,dry_run=True,clock=lambda:NOW,source_factory=lambda *a,**k:pytest.fail('must not run'))
    assert result['external_calls'] == result['database_writes'] == 0
    assert store.snapshot()['jobs'] == []


def test_atomic_claim_across_workers(store):
    store.discover(NOW)
    with ThreadPoolExecutor(max_workers=2) as pool:
        claimed = list(pool.map(lambda _: Store(store.path).claim(NOW),range(2)))
    assert sum(bool(job) for job in claimed) == 1


def test_fencing_expired_lease_cannot_publish(store):
    store.discover(NOW)
    old = store.claim(NOW)
    new = store.claim(NOW+91)
    assert old['id']==new['id'] and old['lease_token'] != new['lease_token']
    with pytest.raises(StaleLease):
        finish(store,old,{'event':EVENT},NOW+92)
    with store.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM sportsdb_match_highlights').fetchone()[0]==0


def test_pause_during_io_blocks_publication(store):
    store.discover(NOW);job=store.claim(NOW)
    store.configure(enabled=False,sources=['thesportsdb'],daily_limit=60,actor='admin')
    with pytest.raises(StaleLease):finish(store,job,{'event':EVENT},NOW+1)


def test_identity_change_during_io_cancels_old_write(store):
    store.discover(NOW);job=store.claim(NOW)
    with store.connection(True) as conn:conn.execute("UPDATE matches SET away_team='Otro equipo'")
    result=finish(store,job,{'event':EVENT},NOW+1)
    assert result['state']=='CANCELLED'
    with store.connection() as conn:assert conn.execute('SELECT COUNT(*) FROM sportsdb_match_highlights').fetchone()[0]==0


def test_budget_shared_by_workers_and_crash_does_not_refund(store):
    store.discover(NOW);job=store.claim(NOW)
    store.reserve('thesportsdb',job,NOW,1)
    with pytest.raises(BudgetStopped,match='DAILY_BUDGET'):store.reserve('thesportsdb',job,NOW,1)
    with store.connection() as conn:assert conn.execute('SELECT SUM(used) FROM postmatch_source_budget').fetchone()[0]==1


def test_production_budget_cannot_exceed_sixty_with_legacy_larger_configuration(store):
    store.configure(enabled=True,sources=['thesportsdb'],daily_limit=200,actor='qa',confirmed=True)
    store.discover(NOW);job=store.claim(NOW)
    for _ in range(60):
        store.reserve('thesportsdb',job,NOW,200)
    with pytest.raises(BudgetStopped,match='DAILY_BUDGET'):
        store.reserve('thesportsdb',job,NOW,200)
    with store.connection() as conn:
        assert conn.execute('SELECT SUM(used) FROM postmatch_source_budget').fetchone()[0] == 60


def test_circuit_breaker_stops_failed_source(store):
    store.discover(NOW);job=store.claim(NOW)
    for _ in range(3):store.circuit('thesportsdb',True,'NETWORK',NOW)
    with pytest.raises(BudgetStopped,match='SOURCE_COOLDOWN'):store.reserve('thesportsdb',job,NOW+1,60)
    assert store.snapshot()['circuits'][0]['blocked_until'] == NOW + 300


@pytest.mark.parametrize('bad',[-1,'NaN','inf',True,'abc',201,1.5])
def test_bad_count_rejected(bad):
    with pytest.raises(SourceError):validate_rows([{'label':'Total Shots','home':bad,'away':1}])


def test_null_not_zero_and_percent_rules():
    row=validate_rows([{'label':'Corner Kicks','home':None,'away':0}])[0]
    assert row['home'] is None and row['away']=='0'
    with pytest.raises(SourceError):validate_rows([{'label':'Ball Possession','home':'66%','away':'66%'}])
    with pytest.raises(SourceError):validate_rows([{'label':'Total Shots','home':2,'away':5},{'label':'Shots on Goal','home':3,'away':1}])


@pytest.mark.parametrize('change',[{'dateEvent':'2026-09-29','strTimestamp':'2026-09-29T16:00:00Z'},
                                   {'strAwayTeam':'Tercer Equipo'}, {'idLeague':'4400'}])
def test_wrong_event_never_matched(change):
    assert not match_event(MATCH,{**EVENT,**change})


def test_date_utc_to_madrid_midnight():
    assert match_event({**MATCH,'match_date':'2026-10-01'}, {**EVENT,'strTimestamp':'2026-09-30T23:30:00Z'})


def test_empty_200_retry_is_not_complete(store):
    def empty(*args,**kwargs):return {'events':None}
    def sf(s,j,c,**kw):return OfficialSources(s,j,c,transport=empty,**kw)
    result=tick(store.path,clock=lambda:NOW,source_factory=sf)
    assert result['result']=='COMPLETE' and result['content_pending']
    assert all(row['state']=='RETRY' for row in result['jobs'])


def test_no_video_no_statistics_are_technical_pass_and_do_not_exhaust_retries(store):
    def empty_content(request,timeout):
        if 'lookupeventstats.php' in request.full_url:return {'eventstats':[]}
        if 'eventshighlights.php' in request.full_url:return {'events':[]}
        return {'events':[{**EVENT,'strVideo':''}]}
    def sf(s,j,c,**kw):return OfficialSources(s,j,c,transport=empty_content,**kw)
    result=tick(store.path,clock=lambda:NOW,source_factory=sf)
    assert result['result']=='COMPLETE' and result['technical_status']=='PASS' and result['content_pending']
    assert {row['reason'] for row in result['jobs']}=={'NO_VIDEO','NO_STATISTICS'}
    with store.connection() as conn:
        assert all(row['state']=='RETRY' and row['attempts']==0 and row['due_at']==NOW+21600
                   for row in conn.execute('SELECT * FROM postmatch_jobs'))


def test_http_200_provider_error_is_not_success_and_secrets_hidden(store):
    def error(*args,**kwargs):return {'errors':{'subscription':'key local-test-secret-never-log forbidden'}}
    def sf(s,j,c,**kw):return OfficialSources(s,j,c,transport=error,**kw)
    result=tick(store.path,clock=lambda:NOW,source_factory=sf)
    assert result['result']=='FAIL' and result['ok'] is False
    assert 'local-test-secret' not in json.dumps(result)
    assert 'local-test-secret' not in json.dumps(store.snapshot())


def test_redirect_rejected():
    from engines.postmatch_sources import NoRedirect
    with pytest.raises(SourceError,match='REDIRECT_BLOCKED'):NoRedirect().redirect_request(None,None,302,'',{},'https://127.0.0.1/')


def test_conflicting_statistics_preserve_selected_and_audit(store):
    job={'id':1,'match_id':MATCH['id'],'identity':identity(MATCH)}
    def obs(value):return [{'source':'thesportsdb','reference':'thesportsdb:event:101','scope':'REGULATION',
                           'observed_at':NOW, 'items':validate_rows([{'label':'Corner Kicks','home':value,'away':0}])}]
    with store.connection(True) as conn:
        assert save_statistics(conn,job,obs(3),NOW)=='PARTIAL_COVERAGE'
        assert save_statistics(conn,job,obs(4),NOW+1)=='CONFLICT'
        assert conn.execute('SELECT COUNT(*) FROM postmatch_observations').fetchone()[0]==2
        assert conn.execute("SELECT COUNT(*) FROM postmatch_audit WHERE action='STAT_CONFLICT'").fetchone()[0]==1
    assert read_for_match(store.path,MATCH)['items'][0]['home']=='3'


def test_recovered_data_does_not_overwrite_original_cached_stats(store):
    tick(store.path,clock=lambda:NOW,source_factory=factory)
    detail={'match':MATCH,'cached_statistics':{'available':True,'items':[{'key':'corner_kicks','label':'Corner Kicks','home':'4','away':'2'}],'source':'original'}}
    attach_detail(store.path,detail)
    assert detail['cached_statistics']['items'][0]['home']=='4'
    assert len([r for r in detail['cached_statistics']['items'] if 'corner' in r['key']])==1


def test_highlight_url_change_revokes_approval(store):
    from engines.sportsdb_highlights_engine import _upsert_highlight, classify_stored_highlight
    with store.connection(True) as conn:
        saved=_upsert_highlight(conn,EVENT)
        conn.execute("UPDATE sportsdb_match_highlights SET rights_status='PROVIDER_ALLOWED',commercial_use_status='ALLOWED',"
                     "attribution='Test source',rights_verified_at='2026-09-30T20:00:00Z',official_source_verified=1")
        _upsert_highlight(conn,{**EVENT,'strVideo':'https://www.youtube.com/watch?v=DIFFERENT01'})
        row=dict(conn.execute('SELECT * FROM sportsdb_match_highlights').fetchone())
    assert row['rights_status']=='REVIEW_REQUIRED'
    assert not classify_stored_highlight(row)['show_block']


def test_unchanged_highlight_keeps_review(store):
    from engines.sportsdb_highlights_engine import _upsert_highlight
    with store.connection(True) as conn:
        _upsert_highlight(conn,EVENT)
        conn.execute("UPDATE sportsdb_match_highlights SET rights_status='BLOCKED'")
        _upsert_highlight(conn,EVENT)
        assert conn.execute('SELECT rights_status FROM sportsdb_match_highlights').fetchone()[0]=='BLOCKED'


def test_source_partial_stats_does_not_claim_full_coverage(store):
    def partial(req,timeout):
        payload=transport(req,timeout)
        if 'eventstats' in payload:payload['eventstats']=payload['eventstats'][:2]
        return payload
    def sf(s,j,c,**kw):return OfficialSources(s,j,c,transport=partial,**kw)
    result=tick(store.path,clock=lambda:NOW,source_factory=sf)
    stats=next(r for r in result['jobs'] if r['kind']=='statistics')
    assert stats['state']=='RETRY' and stats['reason']=='PARTIAL_COVERAGE'


def test_readers_missing_catalogue_do_not_write(tmp_path):
    path=tmp_path/'none.sqlite'
    assert read_for_match(path,MATCH)['state']=='READ_UNAVAILABLE'
    assert not path.exists()


def test_cron_auth_admin_csrf_and_paused_no_network(store,monkeypatch):
    from flask import Flask
    from blueprints.postmatch_recovery import create_postmatch_blueprint
    app=Flask(__name__);app.secret_key='offline-test'
    app.register_blueprint(create_postmatch_blueprint(store.path,lambda:False))
    c=app.test_client();monkeypatch.setenv('AUTOMATION_SECRET','offline-only')
    assert c.post('/api/automation/postmatch/tick').status_code==403
    assert c.post('/api/automation/postmatch/tick?secret=offline-only').status_code==403
    assert c.post('/admin/highlights-review/workers/run').status_code==403
    assert c.get('/api/admin/postmatch/status').status_code==403
    store.configure(enabled=False,sources=['thesportsdb'],daily_limit=60,actor='admin')
    r=c.post('/api/automation/postmatch/tick',headers={'X-Automation-Secret':'offline-only'})
    assert r.status_code==200 and r.json['result']=='SKIPPED_DISABLED'
    assert r.headers['Cache-Control']=='private, no-store'
    app2=Flask('admin-test');app2.secret_key='offline'
    app2.register_blueprint(create_postmatch_blueprint(store.path,lambda:True))
    assert app2.test_client().post('/admin/highlights-review/workers/settings',data={'enabled':'1'}).status_code==403


def test_actual_flask_cron_accepts_header_not_query(client, app_module, monkeypatch):
    monkeypatch.setenv('AUTOMATION_SECRET', 'postmatch-test-secret')
    result = client.post('/api/automation/postmatch/tick', json={}, headers={'X-Automation-Secret':'postmatch-test-secret'})
    assert result.status_code == 200, result.get_data(as_text=True)
    assert result.json['result'] == 'SKIPPED_DISABLED'
    assert client.post('/api/automation/postmatch/tick?secret=postmatch-test-secret', json={}).status_code == 403
    assert client.get('/api/automation/postmatch/tick').status_code == 405


@pytest.mark.parametrize('domain_result,ok,expected', [('COMPLETE',True,'PASS'),('PARTIAL',True,'PARTIAL'),
    ('STORAGE_UNAVAILABLE',False,'FAIL'),('NO_FAKE_GREEN',True,'FAIL')])
def test_master_reports_postmatch_result_not_http_only(monkeypatch,domain_result,ok,expected):
    from tools import render_cron_master_tick as master
    class Response:
        status = 200
        def read(self,n):
            return json.dumps({'ok':ok,'result':domain_result,
                'jobs':[{'state':'RETRY','reason':'DAILY_BUDGET'}]}).encode()
        def __enter__(self): return self
        def __exit__(self,*a): pass
    calls=[]
    def open_(req,timeout):
        calls.append(req); return Response()
    monkeypatch.setattr(master.urllib.request,'urlopen',open_)
    result=master.postmatch_tick('https://app.example.invalid','test-secret')
    assert result['postmatch_status']==expected
    assert 'test-secret' not in json.dumps(result)
    assert 'test-secret' not in calls[0].full_url
    assert calls[0].headers['X-automation-secret']=='test-secret'


def test_translated_competition_keeps_canonical_observations(store):
    tick(store.path,clock=lambda:NOW,source_factory=factory)
    display = {**MATCH,'competition_name':'Premier League','league_name':'Premier League'}
    assert len(read_for_match(store.path, display)['items']) == 7
    with store.connection(True) as conn:
        conn.execute("UPDATE matches SET match_date='2026-10-15'")
    assert read_for_match(store.path, display)['items'] == []


def test_manual_review_conflict_and_stale_form(store):
    from engines.postmatch_recovery import select_observation,selection_revision,selected_values
    tick(store.path,clock=lambda:NOW,source_factory=factory)
    with store.connection(True) as conn:
        original=selected_values(conn,MATCH['id'],identity(MATCH))
        observation=dict(conn.execute('SELECT * FROM postmatch_observations').fetchone())
        items=json.loads(observation['values_json'])
        for item in items:
            if item['key']=='corners': item['home']='8'
        conn.execute('INSERT INTO postmatch_observations(match_id,identity,source,reference,scope,values_json,observed_at,digest) VALUES(?,?,?,?,?,?,?,?)',
            (MATCH['id'],identity(MATCH),'thesportsdb','test:correction','REGULATION',json.dumps(items),NOW+100,'manual-review-fixture'))
        oid=conn.execute('SELECT max(id) FROM postmatch_observations').fetchone()[0]
    revision=selection_revision(original)
    select_observation(store.path,oid,actor='qa-reviewer',expected_identity=identity(MATCH),expected_revision=revision)
    assert next(row for row in read_for_match(store.path,MATCH)['items'] if row['key']=='corners')['home']=='8'
    with pytest.raises(ValueError,match='selección ha cambiado'):
        select_observation(store.path,observation['id'],actor='qa-reviewer',expected_identity=identity(MATCH),expected_revision=revision)
    with store.connection() as conn:
        assert conn.execute('SELECT count(*) FROM postmatch_manual_locks').fetchone()[0]==7
        assert conn.execute("SELECT count(*) FROM postmatch_audit WHERE action='ADMIN_SELECT_STATISTICS'").fetchone()[0]==1
    # Automatic replay of old data must not undo the explicit correction.
    statjob=next(j for j in store.snapshot()['jobs'] if j['kind']=='statistics')
    store.requeue(statjob['id'],'qa-reviewer')
    tick(store.path,clock=lambda:time.time()+1,source_factory=factory)
    assert next(row for row in read_for_match(store.path,MATCH)['items'] if row['key']=='corners')['home']=='8'


def test_corrupted_config_is_not_reported_as_healthy_paused(store):
    with store.connection(True) as conn:
        conn.execute("UPDATE postmatch_settings SET payload='broken-json'")
    result=tick(store.path)
    assert result['ok'] is False and result['result']=='STORAGE_UNAVAILABLE'


def test_source_event_without_final_does_not_attach_live_clip(store):
    store.discover(NOW);job=store.claim(NOW)
    def live_event(req, timeout): return {'events':[{**EVENT,'strStatus':'2H'}]}
    source=OfficialSources(store,job,store.config(),deadline=NOW+20,clock=lambda:NOW,transport=live_event)
    result=source.highlights(MATCH)
    assert not result.get('event')
    assert 'SOURCE_NOT_FINAL' in result['reasons']


def test_approved_media_review_finishes_waiting_job_without_provider_io(store):
    tick(store.path,clock=lambda:NOW,source_factory=factory)
    with store.connection(True) as conn:
        conn.execute("UPDATE sportsdb_match_highlights SET rights_status='LICENSED',commercial_use_status='ALLOWED',attribution='synthetic review',rights_verified_at='2026-09-30T22:00:00Z'")
    result=tick(store.path,clock=lambda:NOW+10,source_factory=lambda *a,**k:pytest.fail('No provider call after review'))
    assert result['external_calls']==0
    assert all(j['state']=='COMPLETE' for j in store.snapshot()['jobs'])


def test_thumbnail_change_does_not_inherit_image_rights(store):
    from engines.sportsdb_highlights_engine import _upsert_highlight
    with store.connection(True) as conn:
        saved=_upsert_highlight(conn,EVENT)
        conn.execute("UPDATE sportsdb_match_highlights SET thumbnail_rights_status='LICENSED',thumbnail_commercial_use_status='ALLOWED' WHERE id=?",(saved['id'],))
        _upsert_highlight(conn,{**EVENT,'strThumb':'https://example.org/changed-image.jpg'})
        row=conn.execute('SELECT thumbnail_rights_status,thumbnail_commercial_use_status FROM sportsdb_match_highlights').fetchone()
        assert tuple(row)==('UNKNOWN_RIGHTS','UNKNOWN')
