"""Delivery tests use real adapters with synthetic transports and temporary stores.

Schema checked against official examples on 2026-10-01:
/documentation, /api/v1/json/123/eventshighlights.php?d=2024-07-07
and /api/v1/json/123/lookupeventstats.php?id=1032723 . No production I/O.
"""
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import urllib.parse

import pytest
from engines.postmatch_sources import OfficialSources
from engines.postmatch_store import Store, StaleLease
from engines.postmatch_recovery import tick, read_for_match
from engines.postmatch_delivery import safe_diagnostics, safe_run_result, present_run_result
from engines import sportsdb_highlights_engine as media

NOW = datetime(2026, 10, 1, 17, tzinfo=timezone.utc).timestamp()
MATCH = {'id':'delivery-test','external_id':'sportsdb-101','source':'TheSportsDB',
    'home_team':'Norte','away_team':'Sur','match_date':'2026-10-01','kickoff_time':'15:00',
    'status':'FT','score':'2-1','home_score':2,'away_score':1,
    'league_id':'4328','league_name':'Liga de prueba','competition_name':'Liga de prueba'}
EVENT = {'idEvent':'101','strEvent':'Norte vs Sur','strHomeTeam':'Norte','strAwayTeam':'Sur',
    'dateEvent':'2026-10-01','strTimestamp':'2026-10-01T13:00:00Z','strStatus':'Match Finished',
    'idLeague':'4328','strLeague':'Liga de prueba','strSport':'Soccer',
    'intHomeScore':'2','intAwayScore':'1','strVideo':''}
# tvhighlights really omits teams/date/status; do not require invented fields.
PROJECTION = {'idEvent':'101','idLeague':'4328','strEvent':'Norte vs Sur',
              'strSport':'Soccer','strVideo':'https://www.youtube.com/watch?v=abcdefghijk'}
STAT = {'idEvent':'101','strStat':'Total Shots','intHome':'7','intAway':'0'}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv('THESPORTSDB_KEY','local-secret-never-expose')
    def reject(*args, **kwargs): raise AssertionError('Real transport forbidden')
    monkeypatch.setattr('urllib.request.urlopen',reject)
    monkeypatch.setattr('urllib.request.OpenerDirector.open',reject)


@pytest.fixture
def store(tmp_path, monkeypatch):
    # Budget writes and snapshot reads must share the synthetic scenario day.
    class ScenarioDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromtimestamp(NOW, tz)
    monkeypatch.setattr('engines.postmatch_store.datetime', ScenarioDateTime)
    path=tmp_path/'delivery.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE matches (' + ','.join(k+(' INTEGER' if k.endswith('_score') else ' TEXT') for k in MATCH)+')')
        conn.execute('INSERT INTO matches VALUES ('+','.join('?' for _ in MATCH)+')',tuple(MATCH.values()))
    store=Store(path)
    store.configure(enabled=True,sources=['thesportsdb'],daily_limit=60,actor='test',confirmed=True)
    return store


def source(store, responses=None, limit=60):
    responses = responses or {}
    calls=[]
    def transport(request,timeout):
        endpoint=urllib.parse.urlsplit(request.full_url).path.rsplit('/',1)[-1]
        calls.append((endpoint,urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)))
        default={'lookupevent.php':{'events':[EVENT]}, 'eventshighlights.php':{'tvhighlights':[PROJECTION]},
                 'lookupeventstats.php':{'eventstats':[STAT]}}
        return deepcopy(responses.get(endpoint,default[endpoint]))
    store.discover(NOW)
    job=store.claim(NOW)
    return OfficialSources(store,job,{**store.config(),'daily_limit':limit},deadline=NOW+20,
                           clock=lambda:NOW,transport=transport),calls


def test_collector_accepts_real_tvhighlights_projection(store,monkeypatch):
    monkeypatch.setattr(media,'_sportsdb_v1',lambda *a:{'tvhighlights':[deepcopy(PROJECTION)]})
    result=media.sync_sportsdb_highlights(store.path,days_back=0)
    assert result['status']=='OK' and result['highlights_found']==1
    with store.connection() as conn:
        row=dict(conn.execute('SELECT * FROM sportsdb_match_highlights').fetchone())
    assert row['match_id']==MATCH['id']
    assert row['rights_status']=='UNKNOWN_RIGHTS'
    assert media.classify_stored_highlight(row)['show_block'] is False


def test_real_schema_no_video_event_recovers_dated_league_projection(store):
    adapter,calls=source(store)
    result=adapter.highlights(MATCH)
    assert result['event']['strVideo']==PROJECTION['strVideo']
    assert result['event']['strHomeTeam']=='Norte' and result['event']['strStatus']=='Match Finished'
    assert calls==[('lookupevent.php',{'id':['101']}),('eventshighlights.php',{'d':['2026-10-01'],'l':['4328'],'s':['Soccer']})]
    assert result['external_calls']==2
    assert adapter.diagnostics['video_lookup']=='LEAGUE_DAY_LINK'
    assert store.snapshot()['budget'][0]['used']==2


def test_event_video_avoids_extra_lookup(store):
    adapter,calls=source(store,{'lookupevent.php':{'events':[{**EVENT,'strVideo':PROJECTION['strVideo']}]}})
    assert adapter.highlights(MATCH)['event']
    assert len(calls)==1


def test_absent_event_is_not_absent_video(store):
    adapter,calls=source(store,{'lookupevent.php':{'events':None}})
    assert adapter.highlights(MATCH)['reasons']==['NO_EVENT']
    assert len(calls)==1


@pytest.mark.parametrize('response_size', [600 * 1024, 2 * 1024 * 1024])
def test_eventsday_accepts_a_bounded_response_above_default_limit(store, monkeypatch, response_size):
    adapter, _ = source(store)
    adapter.transport = adapter._http
    prefix = b'{"events":[]}'
    body = prefix + b' ' * (response_size - len(prefix))
    requested_limits = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, limit):
            requested_limits.append(limit)
            return body[:limit]

    class Opener:
        def open(self, _request, timeout):
            assert timeout > 0
            return Response()

    monkeypatch.setattr(
        'engines.postmatch_sources.urllib.request.build_opener',
        lambda *_args: Opener(),
    )

    result = adapter.request('thesportsdb', 'eventsday.php', {'d': '2026-10-01', 's': 'Soccer'})

    assert result == {'events': []}
    assert requested_limits == [2 * 1024 * 1024 + 1]
    assert 'source_failures' not in safe_diagnostics(adapter.diagnostics)


@pytest.mark.parametrize('row_count', [700, 1500, 1501])
def test_eventsday_dense_catalog_preserves_matching_budget_cache_and_row_limit(store, monkeypatch, row_count):
    unmapped = {**MATCH, 'source': 'Local', 'external_id': ''}
    with store.connection(True) as conn:
        conn.execute('UPDATE matches SET source=?,external_id=? WHERE id=?',
                     (unmapped['source'], unmapped['external_id'], unmapped['id']))
    adapter, _ = source(store)
    adapter.transport = adapter._http
    assert adapter.identities(unmapped) == ('', '')

    events = [{
        **EVENT,
        'idEvent': str(10000 + index),
        'strEvent': f'Home {index} vs Away {index}',
        'strHomeTeam': f'Home {index}',
        'strAwayTeam': f'Away {index}',
        'strHomeTeamBadge': f'https://www.thesportsdb.com/images/media/team/badge/home{index}.png',
        'strAwayTeamBadge': f'https://www.thesportsdb.com/images/media/team/badge/away{index}.png',
        'strDescriptionEN': (
            f'Official fixture {index}: the home and away teams meet in their scheduled competition. '
        ) * 5,
    } for index in range(row_count)]
    # Matching names alone, or names and date alone, must not select a decoy.
    events[0] = {**EVENT, 'idEvent': '90001', 'dateEvent': '2026-09-30',
                 'strTimestamp': '2026-09-30T13:00:00Z'}
    events[1] = {**EVENT, 'idEvent': '90002', 'idLeague': '999', 'strLeague': 'Other league'}
    events[-3] = deepcopy(EVENT)
    body = json.dumps({'events': events}, ensure_ascii=False).encode('utf-8')
    assert 512 * 1024 < len(body) <= 2 * 1024 * 1024
    requests = []
    requested_limits = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, limit):
            requested_limits.append(limit)
            return body[:limit]

    class Opener:
        def open(self, request, timeout):
            assert timeout > 0
            parsed = urllib.parse.urlsplit(request.full_url)
            requests.append((parsed.path.rsplit('/', 1)[-1], urllib.parse.parse_qs(parsed.query)))
            return Response()

    monkeypatch.setattr(
        'engines.postmatch_sources.urllib.request.build_opener',
        lambda *_args: Opener(),
    )

    if row_count > 1500:
        with pytest.raises(ValueError, match='MALFORMED'):
            adapter.sportsdb_event(unmapped)
    else:
        assert adapter.sportsdb_event(unmapped) == EVENT
        assert adapter.sportsdb_event(unmapped) == EVENT
        assert adapter.diagnostics['cache_hits'] == 1
        assert adapter.diagnostics['sportsdb_event_id'] == EVENT['idEvent']
    assert adapter.diagnostics['event_rows'] == row_count
    assert requests == [('eventsday.php', {'d': ['2026-10-01'], 's': ['Soccer']})]
    assert requested_limits == [2 * 1024 * 1024 + 1]
    assert adapter.calls == 1
    assert store.snapshot()['budget'][0]['used'] == 1
    with store.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM postmatch_request_cache').fetchone()[0] == 0


def test_small_operational_request_cache_is_persisted_and_sanitized(store):
    adapter, _ = source(store)
    payload = {
        'events': [{**EVENT, 'api_key': 'PRIVATE',
                    'metadata': {'token': 'PRIVATE', 'home_score': 2}}],
        'unexpected_field': 'PRIVATE',
    }

    store.cache_request('small-catalog', adapter.job, payload, NOW)
    cached = store.cached_request('small-catalog', adapter.job['identity'], NOW)

    assert cached == {'payload': {'events': [{**EVENT, 'metadata': {'home_score': 2}}]},
                      'observed_at': NOW}
    assert 'PRIVATE' not in json.dumps(cached)
    assert store.cached_request('small-catalog', adapter.job['identity'], NOW + 21600) is None
    assert adapter.calls == 0


@pytest.mark.parametrize('invalid', [float('nan'), float('inf'), float('-inf')],
                         ids=['nan', 'positive-infinity', 'negative-infinity'])
def test_operational_request_cache_still_rejects_non_finite_json(store, invalid):
    adapter, _ = source(store)

    with pytest.raises(ValueError):
        store.cache_request('invalid-catalog', adapter.job,
                            {'events': [{**EVENT, 'invalid_statistic': invalid}]}, NOW)

    with store.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM postmatch_request_cache').fetchone()[0] == 0


def test_small_operational_cache_propagates_sql_failure_and_preserves_existing_rows(store):
    adapter, _ = source(store)
    payload = {'events': [EVENT]}
    store.cache_request('existing-catalog', adapter.job, payload, NOW)
    with store.connection(True) as conn:
        conn.execute('''CREATE TRIGGER reject_cache_insert BEFORE INSERT ON postmatch_request_cache
                        BEGIN SELECT RAISE(ABORT, 'synthetic cache write failure'); END''')

    with pytest.raises(sqlite3.IntegrityError, match='synthetic cache write failure'):
        store.cache_request('new-catalog', adapter.job, payload, NOW)

    assert store.cached_request('existing-catalog', adapter.job['identity'], NOW)['payload'] == payload
    assert store.cached_request('new-catalog', adapter.job['identity'], NOW) is None
    with store.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM postmatch_request_cache').fetchone()[0] == 1


def test_small_operational_cache_expired_lease_prevents_storage(store):
    adapter, _ = source(store)
    with store.connection(True) as conn:
        conn.execute('UPDATE postmatch_jobs SET lease_until=? WHERE id=?',
                     (NOW - 1, adapter.job['id']))

    with pytest.raises(StaleLease, match='LEASE_LOST'):
        store.cache_request('expired-catalog', adapter.job, {'events': [EVENT]}, NOW)

    assert store.cached_request('expired-catalog', adapter.job['identity'], NOW) is None
    with store.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM postmatch_request_cache').fetchone()[0] == 0


def test_other_provider_endpoint_keeps_the_default_response_limit(store, monkeypatch):
    adapter, _ = source(store)
    adapter.transport = adapter._http
    prefix = b'{"events":[]}'
    body = prefix + b' ' * (600 * 1024 - len(prefix))

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, limit):
            return body[:limit]

    class Opener:
        def open(self, _request, timeout):
            assert timeout > 0
            return Response()

    monkeypatch.setattr(
        'engines.postmatch_sources.urllib.request.build_opener',
        lambda *_args: Opener(),
    )

    with pytest.raises(ValueError, match='MALFORMED'):
        adapter.request('thesportsdb', 'lookupevent.php', {'id': '101'})

    assert safe_diagnostics(adapter.diagnostics)['source_failures'] == [{
        'provider': 'thesportsdb',
        'endpoint': 'lookupevent.php',
        'stage': 'RESPONSE_SIZE_LIMIT',
        'reason': 'MALFORMED',
    }]

def test_oversized_provider_response_is_reported_as_closed_size_limit(store, monkeypatch):
    adapter, _ = source(store)
    adapter.transport = adapter._http

    class OversizedResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, limit):
            return b'x' * limit

    class Opener:
        def open(self, _request, timeout):
            assert timeout > 0
            return OversizedResponse()

    monkeypatch.setattr(
        'engines.postmatch_sources.urllib.request.build_opener',
        lambda *_args: Opener(),
    )

    with pytest.raises(ValueError, match='MALFORMED'):
        adapter.request('thesportsdb', 'eventsday.php', {'d': '2026-10-01', 's': 'Soccer'})

    assert safe_diagnostics(adapter.diagnostics)['source_failures'] == [{
        'provider': 'thesportsdb',
        'endpoint': 'eventsday.php',
        'stage': 'RESPONSE_SIZE_LIMIT',
        'reason': 'MALFORMED',
    }]
    assert 'xxxxxxxx' not in str(adapter.diagnostics)


@pytest.mark.parametrize('payload',[{}, {'tvhighlights':'bad'},{'tvhighlights':[None]},{'unknown':[]}])
def test_malformed_projection_is_not_reported_no_video(store,payload):
    adapter,_=source(store,{'eventshighlights.php':payload})
    assert adapter.highlights(MATCH)['reasons']==['MALFORMED']


@pytest.mark.parametrize('change',[{'idLeague':'999'},{'strSport':'Basketball'},
    {'strHomeTeam':'Other'},{'strEvent':'Other vs Sur'},{'dateEvent':'2026-09-30'}])
def test_projection_conflicts_never_attach_to_match(store,change):
    adapter,_=source(store,{'eventshighlights.php':{'tvhighlights':[{**PROJECTION,**change}]}})
    assert adapter.highlights(MATCH)['reasons']==['IDENTITY_MISMATCH']


def test_different_event_is_not_reassigned(store):
    adapter,_=source(store,{'eventshighlights.php':{'tvhighlights':[{**PROJECTION,'idEvent':'102'}]}})
    assert adapter.highlights(MATCH)['reasons']==['NO_VIDEO']


def test_multiple_urls_require_review_instead_of_picking_arbitrarily(store):
    adapter,_=source(store,{'eventshighlights.php':{'tvhighlights':[PROJECTION,{**PROJECTION,'strVideo':'https://youtu.be/otherClip01'}]}})
    assert adapter.highlights(MATCH)['reasons']==['AMBIGUOUS_VIDEO']


def test_duplicate_same_url_is_one_candidate(store):
    adapter,_=source(store,{'eventshighlights.php':{'tvhighlights':[PROJECTION,PROJECTION]}})
    assert adapter.highlights(MATCH)['event']


def test_saturated_scope_does_not_claim_video_absence(store):
    adapter,_=source(store,{'eventshighlights.php':{'tvhighlights':[{**PROJECTION,'idEvent':str(i+1000)} for i in range(50)]}})
    assert adapter.highlights(MATCH)['reasons']==['HIGHLIGHT_RESPONSE_LIMIT']


def test_new_lookup_uses_existing_shared_daily_budget(store):
    adapter,calls=source(store,limit=1)
    assert adapter.highlights(MATCH)['reasons']==['DAILY_BUDGET']
    assert len(calls)==1 and store.snapshot()['budget'][0]['used']==1


def test_non_final_does_not_fanout(store):
    adapter,calls=source(store,{'lookupevent.php':{'events':[{**EVENT,'strStatus':'2H'}]}})
    assert adapter.highlights(MATCH)['reasons']==['SOURCE_NOT_FINAL']
    assert len(calls)==1


@pytest.mark.parametrize('payload,expected',[
    ({},'MALFORMED'),({'eventstats':None},'NO_STATISTICS'),({'eventstats':[]},'NO_STATISTICS'),
    ({'eventstats':[{**STAT,'strStat':'Unknown metric'}]},'UNSUPPORTED_STATISTICS'),
    ({'eventstats':[{**STAT,'intHome':None,'intAway':None}]},'EMPTY_STATISTIC_VALUES'),
    ({'eventstats':[{'idEvent':'101','intHome':'3'}]},'MALFORMED'),
    ({'eventstats':[{**STAT,'idEvent':'999'}]},'IDENTITY_MISMATCH'),
])
def test_statistics_distinguish_empty_unrecognized_and_invalid(store,payload,expected):
    adapter,_=source(store,{'lookupeventstats.php':payload})
    result=adapter.statistics(MATCH)
    assert result['observations']==[] and result['reasons']==[expected]


def test_malformed_statistics_exposes_only_closed_provider_endpoint_stage(store):
    adapter,_=source(store,{'lookupeventstats.php':{'eventstats':[{'idEvent':'101','intHome':'3'}]}})
    result=adapter.statistics(MATCH)

    assert result['reasons']==['MALFORMED']
    assert safe_diagnostics(adapter.diagnostics)['source_failures']==[{
        'provider':'thesportsdb','endpoint':'lookupeventstats.php',
        'stage':'STATISTICS_ROW_SHAPE','reason':'MALFORMED',
    }]
    serialized=json.dumps(safe_diagnostics(adapter.diagnostics))
    assert 'local-secret-never-expose' not in serialized and 'intHome' not in serialized


def test_official_statistics_shape_and_zero_values_are_supported(store):
    adapter,_=source(store)
    result=adapter.statistics(MATCH)
    assert result['observations'][0]['items'][0]['away']=='0'
    assert adapter.diagnostics['statistics_received']==adapter.diagnostics['statistics_accepted']==1


def test_demo_key_is_flagged_without_exposing_any_key(store,monkeypatch):
    monkeypatch.setenv('THESPORTSDB_KEY','123')
    adapter,_=source(store)
    adapter.statistics(MATCH)
    assert adapter.diagnostics['key_mode']=='PUBLIC_DEMO_KEY'
    assert '123' not in json.dumps(safe_diagnostics(adapter.diagnostics))


def test_projection_rights_fields_cannot_grant_publication(store):
    adapter,_=source(store,{'eventshighlights.php':{'tvhighlights':[{**PROJECTION,'rights_status':'LICENSED','commercial_use_status':'ALLOWED','strThumb':'https://example.org/secret'}]}})
    result=adapter.highlights(MATCH)
    assert 'rights_status' not in result['event'] and 'strThumb' not in result['event']


def test_sanitizer_drops_secrets_and_unexpected_types():
    bad={'sportsdb_event_id':'101','url':'SECRET','key':'SECRET','token':'SECRET',
         'video_lookup':'SECRET','key_mode':['SECRET'],'statistics_accepted':True,'event_rows':-1}
    assert safe_diagnostics(bad)=={'sportsdb_event_id':'101'}
    result=safe_run_result({'ok':True,'result':'SECRET','external_calls':2,'processed':1,
        'jobs':[{'reason':'SECRET','state':'RETRY','kind':'highlights','match_id':'../../SECRET',
                 'diagnostics':bad,'raw_payload':'SECRET'}]})
    assert 'SECRET' not in json.dumps(result)
    malformed={'source_failures':[{'provider':'api_football','endpoint':'fixtures/statistics',
        'stage':'STATISTICS_RESPONSE_SHAPE','reason':'MALFORMED','payload':'SECRET','key':'SECRET'},
        {'provider':'api_football','endpoint':'https://evil.example/?key=SECRET',
         'stage':'SECRET','reason':'SECRET'}]}
    closed=safe_diagnostics(malformed)
    assert closed['source_failures']==[{'provider':'api_football','endpoint':'fixtures/statistics',
        'stage':'STATISTICS_RESPONSE_SHAPE','reason':'MALFORMED'}]
    assert 'SECRET' not in json.dumps(closed)


def test_tick_persists_diagnostics_and_logs_only_closed_evidence(store,capsys):
    def transport(request,timeout):
        if 'lookupeventstats.php' in request.full_url:return {'eventstats':[STAT]}
        if 'eventshighlights.php' in request.full_url:return {'tvhighlights':[PROJECTION]}
        return {'events':[EVENT]}
    def factory(*a,**kw):return OfficialSources(*a,transport=transport,**kw)
    result=tick(store.path,clock=lambda:NOW,source_factory=factory)
    assert result['external_calls']==3 and result['processed']==2
    assert result['jobs'][0]['reason']=='RIGHTS_REVIEW'
    assert result['jobs'][1]['reason']=='PARTIAL_COVERAGE'
    assert result['jobs'][0]['diagnostics']['video_lookup']=='LEAGUE_DAY_LINK'
    assert read_for_match(store.path,MATCH)['items'][0]['away']=='0'
    with store.connection() as conn:
        records=[json.loads(r[0]) for r in conn.execute("SELECT detail FROM postmatch_audit WHERE action='FINISH'")]
        video=dict(conn.execute('SELECT * FROM sportsdb_match_highlights').fetchone())
    assert records[0]['diagnostics']['sportsdb_event_id']=='101'
    assert not media.classify_stored_highlight(video)['show_block']
    logged=capsys.readouterr().out
    assert 'postmatch_delivery' in logged and '101' in logged
    assert 'local-secret' not in logged and 'https://' not in logged and PROJECTION['strVideo'] not in logged


def test_tick_surfaces_malformed_source_context_without_payload_or_key(store,capsys):
    bad_stats={'eventstats':[{'idEvent':'101','intHome':'3'}]}
    def transport(request,timeout):
        endpoint=urllib.parse.urlsplit(request.full_url).path.rsplit('/',1)[-1]
        return {'lookupevent.php':{'events':[EVENT]},
                'lookupeventstats.php':bad_stats,
                'eventshighlights.php':{'tvhighlights':[PROJECTION]}}[endpoint]
    def factory(*args,**kwargs):
        return OfficialSources(*args,transport=transport,**kwargs)

    result=tick(store.path,clock=lambda:NOW,source_factory=factory)
    malformed=next(job for job in result['jobs'] if job['reason']=='MALFORMED')
    assert malformed['diagnostics']['source_failures']==[{
        'provider':'thesportsdb','endpoint':'lookupeventstats.php',
        'stage':'STATISTICS_ROW_SHAPE','reason':'MALFORMED',
    }]
    logged=capsys.readouterr().out
    assert 'lookupeventstats.php' in logged and 'STATISTICS_ROW_SHAPE' in logged
    assert 'local-secret-never-expose' not in logged and 'intHome' not in logged


def test_present_result_is_read_only_and_resolves_match(store):
    before=store.path.read_bytes()
    out=present_run_result({'ok':True,'result':'PARTIAL','processed':1,'external_calls':1,
        'jobs':[{'job_id':1,'match_id':MATCH['id'],'kind':'statistics','state':'RETRY','reason':'NO_STATISTICS','due_at':NOW+1800}]},store)
    assert out['jobs'][0]['match_label']=='Norte — Sur'
    assert 'consulta no devolvió' in out['jobs'][0]['reason_label']
    assert store.path.read_bytes()==before


def test_http_form_redirects_to_private_get_and_refresh_never_repeats_tick(store,monkeypatch):
    from flask import Flask, session
    from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader
    import blueprints.postmatch_recovery as bp
    app=Flask(__name__);app.secret_key='isolated-session'
    app.jinja_loader=ChoiceLoader([DictLoader({'base.html':'{% block content %}{% endblock %}'}),FileSystemLoader(Path(__file__).parents[1]/'templates')])
    app.register_blueprint(bp.create_postmatch_blueprint(str(store.path),lambda:session.get('admin') is True))
    calls=[]
    def fake_tick(path):
        calls.append(1)
        return {'ok':True,'result':'PARTIAL','processed':1,'external_calls':1,
            'jobs':[{'job_id':1,'match_id':MATCH['id'],'kind':'statistics','state':'RETRY','reason':'NO_STATISTICS'}]}
    monkeypatch.setattr(bp,'tick',fake_tick)
    client=app.test_client()
    assert client.get('/admin/highlights-review/workers/result').status_code==403
    with client.session_transaction() as sess:sess.update(admin=True,csrf_token='csrf-test')
    assert client.post('/admin/highlights-review/workers/run',data={'return_to_panel':'1'}).status_code==403
    response=client.post('/admin/highlights-review/workers/run',data={'csrf_token':'csrf-test','return_to_panel':'1'})
    assert response.status_code==303
    for _ in range(2):
        page=client.get(response.headers['Location'])
        assert page.status_code==200 and 'Norte' in page.text and 'Lote procesado con pendientes' in page.text
        assert 'no-store' in page.headers['Cache-Control']
    assert calls==[1]
    # Existing programmatic JSON contract remains unchanged.
    response=client.post('/admin/highlights-review/workers/run',data={'csrf_token':'csrf-test'})
    assert response.is_json and response.json['result']=='PARTIAL' and len(calls)==2


def test_actual_http_result_uses_full_application_template_without_running_worker(client,app_module,monkeypatch,tmp_path):
    import blueprints.postmatch_recovery as bp
    monkeypatch.setattr(app_module,'DB_PATH',str(tmp_path/'postmatch-admin.sqlite3'))
    monkeypatch.setattr(app_module,'_SEEDED_DB_PATH',None)
    monkeypatch.setattr(app_module,'_SEEDING_DB_PATH',None)
    monkeypatch.setattr(app_module,'APP_INITIALIZED',False)
    app_module.seed_core()
    with closing(app_module.db()) as conn,conn:
        admin_id=app_module.create_admin_record(
            conn,'Postmatch QA','postmatch-qa','postmatch-qa@example.invalid','local-qa-password')
    admin=app_module.get_user_by_id(admin_id)
    monkeypatch.setattr(bp,'tick',lambda *a,**k:pytest.fail('GET must not execute a worker'))
    with app_module.app.test_request_context():
        app_module.set_login_session(admin)
        signed_in=dict(app_module.session)
    with client.session_transaction() as sess:
        sess.clear();sess.update(signed_in)
        sess.update(csrf_token='test-result-csrf',postmatch_last_result={
            'ok':True,'result':'PARTIAL','processed':1,'external_calls':1,
            'jobs':[{'job_id':1,'kind':'statistics','state':'RETRY','reason':'NO_STATISTICS'}]})
    response=client.get('/admin/highlights-review/workers/result')
    assert response.status_code==200, response.text[:1000]
    assert 'data-postmatch-run-result' in response.text
    assert 'Lote procesado con pendientes' in response.text
    assert 'no-store' in response.headers['Cache-Control']
