"""Offline persistent coverage, budgets, identity and rights boundaries."""
import json
import sqlite3
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

import pytest
from engines.highlight_coverage import Coverage, run_one, retry_delay
from engines.postmatch_store import identity
from engines.sportsdb_request_budget import SportsDBBudget, SportsDBStopped
from engines import sportsdb_highlights_engine as media
from engines.automation_outcome import postmatch_outcome

NOW = datetime(2026,10,4,10,tzinfo=timezone.utc).timestamp()
MATCH = {'id':'old','external_id':'sportsdb-42','source':'TheSportsDB',
         'home_team':'Home','away_team':'Away','match_date':'2025-01-01','kickoff_time':'18:00',
         'competition_name':'League','league_id':'123','status':'FT','score':'2-1',
         'home_score':2,'away_score':1}
EVENT = {'idEvent':'42','strHomeTeam':'Home','strAwayTeam':'Away','dateEvent':'2025-01-01',
         'strLeague':'League','idLeague':'123','strVideo':'https://www.youtube.com/watch?v=abcdefghijk'}


@pytest.fixture
def coverage(tmp_path):
    path = tmp_path/'coverage.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE matches ('+','.join(k+' TEXT' for k in MATCH)+', PRIMARY KEY(id))')
        conn.execute('INSERT INTO matches VALUES('+','.join('?' for _ in MATCH)+')',tuple(MATCH.values()))
    media.ensure_sportsdb_highlights_schema(path)
    result = Coverage(path,NOW)
    result.prepare()
    return result


def lookup_pipeline(coverage, items=None, fail=None):
    calls=[]
    scope=SportsDBBudget(before_call=lambda:coverage.reserve_media_call(True))
    def lookup(sid):
        calls.append(('v2',sid))
        def fetch():
            if fail:
                raise SportsDBStopped(fail)
            return {'lookup':items or []}
        return scope.call(2,'v2',{'idEvent':sid},fetch)['lookup']
    def v1(endpoint,params):
        calls.append((endpoint,params))
        return {'events':[EVENT]}
    def save(rows):
        with sqlite3.connect(coverage.path) as conn:
            conn.row_factory=sqlite3.Row
            for item in rows:
                media._upsert_highlight(conn,item)
    with scope:
        result=run_one(coverage,scope,lookup,save,v1)
    return result,scope.calls,calls


def test_full_catalogue_denominator_not_video_count(coverage):
    snapshot=coverage.snapshot()
    assert (snapshot['eligible'],snapshot['checked'],snapshot['pending'],snapshot['coverage_percent'])==(1,0,1,0)
    result,calls,_=lookup_pipeline(coverage)
    assert result['state']=='CHECKED_NO_VIDEO' and calls==2
    snapshot=Coverage(coverage.path,NOW).snapshot()
    assert snapshot['checked']==1 and snapshot['pending']==0 and snapshot['coverage_percent']==100
    assert snapshot['states']['CHECKED_NO_VIDEO']==1
    assert Coverage(coverage.path,NOW).claim() is None


def test_cursor_resume_and_future_finalization(coverage):
    with sqlite3.connect(coverage.path) as conn:
        for i in range(1,7):
            row={**MATCH,'id':f'm{i}','external_id':f'sportsdb-{i+100}','status':'NS' if i==1 else 'FT'}
            conn.execute('INSERT INTO matches VALUES('+','.join('?' for _ in row)+')',tuple(row.values()))
    coverage.prepare(batch=2)
    first=coverage.snapshot()['cursor']['row_cursor']
    again=Coverage(coverage.path,NOW);again.prepare(batch=2)
    assert again.snapshot()['cursor']['row_cursor']>first
    with sqlite3.connect(coverage.path) as conn:
        conn.execute("UPDATE matches SET status='FT' WHERE id='m1'")
    again.prepare(batch=2)
    assert again.snapshot()['eligible']==7
    assert again.snapshot()['states']['UNSCANNED']==7
    with sqlite3.connect(coverage.path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM highlight_coverage').fetchone()[0]==7


def test_checked_identity_change_invalidates_coverage_immediately(coverage):
    lookup_pipeline(coverage)
    with sqlite3.connect(coverage.path) as conn:
        conn.execute("UPDATE matches SET away_team='Other' WHERE id='old'")
    assert coverage.snapshot()['checked']==0
    coverage.prepare()
    assert coverage.snapshot()['states']['UNSCANNED']==1


def test_lease_restart_fencing_and_idempotence(coverage):
    job=coverage.claim()
    assert Coverage(coverage.path,NOW+1).claim() is None
    recovery=Coverage(coverage.path,NOW+91)
    replacement=recovery.claim()
    assert replacement and replacement['lease']!=job['lease']
    assert not recovery.finish(job,'CHECKED_NO_VIDEO',checked=True)
    assert recovery.finish(replacement,'CHECKED_NO_VIDEO',checked=True)
    assert not recovery.finish(replacement,'CHECKED_NO_VIDEO',checked=True)


def test_budget_persisted_reserved_before_io_and_concurrent(coverage):
    def reserve(_):
        try:
            Coverage(coverage.path,NOW).reserve_media_call()
            return True
        except SportsDBStopped:
            return False
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes=list(pool.map(reserve,range(20)))
    assert sum(outcomes)==12
    restarted=Coverage(coverage.path,NOW)
    with pytest.raises(SportsDBStopped,match='MEDIA_BUDGET'):
        restarted.reserve_media_call()
    assert restarted.snapshot()['media_budget']['used']==12
    assert Coverage(coverage.path,NOW+21600).snapshot()['media_budget']['used']==0


def test_historical_cannot_drain_recent_or_postmatch_budget(coverage):
    coverage.reserve_media_call(True);coverage.reserve_media_call(True)
    with pytest.raises(SportsDBStopped,match='MEDIA_BUDGET'):
        coverage.reserve_media_call(True)
    for _ in range(10):coverage.reserve_media_call(False)
    assert coverage.snapshot()['media_budget']['used']==12
    with sqlite3.connect(coverage.path) as conn:
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='postmatch_source_budget'").fetchone()


def test_video_linked_without_rights_approval_and_cross_surface_gating(coverage):
    result,calls,_=lookup_pipeline(coverage,[EVENT])
    assert result['state']=='LINKED' and calls==2
    from engines.highlight_read_model import read_highlights_for_match
    from engines.highlight_surfaces import enrich_context
    assert read_highlights_for_match(coverage.path,'old')['highlights']==[]
    context={'matches':[dict(MATCH)],'team_center':{'results':[dict(MATCH)]},'favorites':[dict(MATCH)]}
    enrich_context(coverage.path,context)
    assert not context['matches'][0]['has_highlights']
    with sqlite3.connect(coverage.path) as conn:
        conn.execute("UPDATE sportsdb_match_highlights SET rights_status='LICENSED',commercial_use_status='ALLOWED',"
                     "rights_verified_at='2026-10-04T09:00:00Z',attribution='Official source'")
    enrich_context(coverage.path,context)
    assert all(context[key][0]['has_highlights'] for key in ['matches','favorites'])
    assert context['team_center']['results'][0]['has_highlights']
    enrich_context(coverage.path,context,enabled=False)
    assert not context['matches'][0]['has_highlights']


@pytest.mark.parametrize('failure',['ACCESS_DENIED','RATE_LIMIT','NETWORK','MALFORMED'])
def test_provider_error_never_counts_as_no_video(coverage,failure):
    with pytest.raises(SportsDBStopped):lookup_pipeline(coverage,fail=failure)
    snapshot=coverage.snapshot()
    assert snapshot['checked']==0 and snapshot['states']['PROVIDER_ERROR']==1
    assert snapshot['media_budget']['used']==2


def test_reconciliation_requires_exact_teams_date_competition(coverage):
    with sqlite3.connect(coverage.path) as conn:
        conn.execute("UPDATE matches SET external_id='api-football-1',source='API-Football'")
    coverage.prepare()
    result,_,calls=lookup_pipeline(coverage,[EVENT])
    assert result['state']=='LINKED' and calls[0][0]=='eventsday.php'


def test_duplicate_canonical_matches_are_ambiguous(coverage):
    with sqlite3.connect(coverage.path) as conn:
        other={**MATCH,'id':'other'}
        conn.execute('INSERT INTO matches VALUES('+','.join('?' for _ in other)+')',tuple(other.values()))
    coverage.prepare()
    result,_,_=lookup_pipeline(coverage,[EVENT])
    assert result['state']=='AMBIGUOUS' and coverage.snapshot()['checked']==0
    with sqlite3.connect(coverage.path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sportsdb_match_highlights').fetchone()[0]==0


@pytest.mark.parametrize('reason,expected',[('NO_VIDEO','PASS'),('NO_STATISTICS','PASS'),
    ('RIGHTS_REVIEW','PASS'),('DAILY_BUDGET','PARTIAL'),('PARTIAL_COVERAGE','PARTIAL'),
    ('NETWORK','FAIL'),('ACCESS_DENIED','FAIL'),('STORAGE_UNAVAILABLE','FAIL')])
def test_technical_outcome_separate_from_content(reason,expected):
    assert postmatch_outcome([{'reason':reason,'state':'RETRY'}])==expected


def test_no_video_retries_age_and_cache_identity(coverage):
    assert retry_delay({**MATCH,'match_date':'2026-10-03'},NOW,1)==21600
    assert retry_delay({**MATCH,'match_date':'2026-09-20'},NOW,1)==3*86400
    assert retry_delay(MATCH,NOW,3)==90*86400
    lookup_pipeline(coverage)
    later=Coverage(coverage.path,NOW+31*86400);later.prepare()
    result,calls,requests=lookup_pipeline(later)
    assert result['state']=='CHECKED_NO_VIDEO' and calls==1
    assert requests==[('v2','42')]


def test_read_only_missing_coverage_does_not_create_schema(tmp_path):
    path=tmp_path/'empty.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE matches(id TEXT)')
    assert Coverage(path,NOW).snapshot()['read_state']=='UNSCANNED'
    with sqlite3.connect(path) as conn:
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='highlight_coverage'").fetchone()


def test_existing_editorial_priority_precedes_ordinary_history(coverage):
    with sqlite3.connect(coverage.path) as conn:
        other={**MATCH,'id':'important','competition_name':'Important'}
        conn.execute('INSERT INTO matches VALUES('+','.join('?' for _ in other)+')',tuple(other.values()))
    ranked=Coverage(coverage.path,NOW,priority=lambda match:100 if match['competition_name']=='Important' else 0)
    ranked.prepare()
    assert ranked.claim()['match_id']=='important'


def test_collector_integrates_persistent_backfill_and_negative_cache(coverage,monkeypatch):
    from datetime import date
    monkeypatch.setattr(media,'_api_key',lambda:'offline-only')
    monkeypatch.setattr(media,'_now',lambda:datetime.fromtimestamp(NOW,timezone.utc).isoformat())
    monkeypatch.setattr(media,'_today',lambda:date(2026,10,4))
    calls=[]
    def fetch(endpoint,params):
        calls.append(endpoint)
        return {'events':[EVENT] if endpoint=='lookupevent.php' else []}
    monkeypatch.setattr(media,'_sportsdb_v1',fetch)
    monkeypatch.setattr(media,'_sportsdb_v2',lambda path:{'lookup':[]})
    first=media.sync_sportsdb_highlights(coverage.path,historical_only=True)
    assert first['historical_backfill']['state']=='CHECKED_NO_VIDEO' and first['external_calls']==2
    second=media.sync_sportsdb_highlights(coverage.path,historical_only=True)
    assert second['external_calls']==0
    assert Coverage(coverage.path,NOW).snapshot()['checked']==1
    assert calls==['lookupevent.php']


def test_v2_minimal_payload_uses_verified_event_identity_for_cross_source(coverage):
    with sqlite3.connect(coverage.path) as conn:
        conn.execute("UPDATE matches SET external_id='api-football-1',source='API-Football'")
    coverage.prepare()
    result,_,_=lookup_pipeline(coverage,[{'idEvent':'42','strVideo':EVENT['strVideo']}])
    assert result['state']=='LINKED'


def test_safe_reconciliation_uses_utc_day_for_madrid_midnight():
    from engines.postmatch_sources import sportsdb_query_date
    assert sportsdb_query_date({**MATCH,'match_date':'2026-10-04','kickoff_time':'00:30'})=='2026-10-03'


def test_existing_linked_catalogue_reused_without_provider_or_rights_changes(coverage):
    with sqlite3.connect(coverage.path) as conn:
        conn.row_factory=sqlite3.Row
        media._upsert_highlight(conn,EVENT)
    coverage.prepare()
    snap=coverage.snapshot()
    assert snap['checked']==1 and snap['states']['LINKED']==1
    assert snap['media_budget']['used']==0 and coverage.claim() is None
    assert media.sportsdb_highlights_for_match(coverage.path,'old')['highlights']==[]


def test_verified_persisted_profile_id_is_preferred_and_stale_mapping_rejected(coverage):
    with sqlite3.connect(coverage.path) as conn:
        conn.execute("UPDATE matches SET external_id='api-football-1',source='API-Football'")
        conn.execute('CREATE TABLE sportsdb_event_profiles(match_id TEXT,sportsdb_event_id TEXT,raw_json TEXT)')
        conn.execute('INSERT INTO sportsdb_event_profiles VALUES(?,?,?)',('old','42',json.dumps(EVENT)))
    coverage.prepare()
    job=coverage.claim()
    assert job['event_id']=='42'
    with sqlite3.connect(coverage.path) as conn:
        conn.execute("UPDATE matches SET away_team='Changed'")
    coverage.prepare()
    assert coverage.claim()['event_id']==''


def test_collection_row_id_cannot_override_explicit_canonical_match_id(monkeypatch):
    from engines import highlight_surfaces
    calls=[]
    monkeypatch.setattr(highlight_surfaces,'read_highlights_map',lambda path,ids,**kw:
        calls.append(ids) or {'read_state':'VERIFIED','map':{'canonical':[{'show_block':True}]}})
    item={**MATCH,'id':'collection-row','match_id':'canonical'}
    context={'collection':[item,dict(item)]}
    highlight_surfaces.enrich_context('unused',context)
    assert calls==[['canonical']] and item['has_highlights']


def test_coverage_ratio_uses_one_snapshot_during_concurrent_ingestion(coverage,monkeypatch):
    from engines.highlight_coverage import eligible
    with sqlite3.connect(coverage.path) as conn:
        conn.execute('PRAGMA journal_mode=WAL')
    original=coverage.connect
    changed=[]
    def reader(write=False):
        conn=original(write)
        def check(raw):
            if not changed:
                changed.append(True)
                new={**MATCH,'id':'arrived','external_id':'sportsdb-43'}
                with sqlite3.connect(coverage.path) as writer:
                    writer.execute('INSERT INTO matches VALUES('+','.join('?' for _ in new)+')',tuple(new.values()))
                    writer.execute('INSERT INTO highlight_coverage(match_id,identity,state,checked_at,due_at,updated_at) '
                                   "VALUES(?,?,'LINKED',?,?,?)",('arrived',identity(new),NOW,NOW,NOW))
            return int(eligible(json.loads(raw),NOW))
        conn.create_function('coverage_eligible',1,check)
        return conn
    monkeypatch.setattr(coverage,'connect',reader)
    snapshot=coverage.snapshot()
    assert snapshot['eligible']==1 and snapshot['checked']==0 and snapshot['pending']==1
    assert Coverage(coverage.path,NOW).snapshot()['eligible']==2
