"""Delivery tests use real adapters with synthetic transports and temporary stores.

Schema checked against official examples on 2026-10-01:
/documentation, /api/v1/json/123/eventshighlights.php?d=2024-07-07
and /api/v1/json/123/lookupeventstats.php?id=1032723 . No production I/O.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import urllib.parse

import pytest
from engines.postmatch_sources import OfficialSources
from engines.postmatch_store import Store
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
    # Adapter requests use NOW; daily-budget reads must observe that same day.
    class FixtureDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls.fromtimestamp(NOW, tz)
    monkeypatch.setattr('engines.postmatch_store.datetime', FixtureDateTime)
    monkeypatch.setenv('THESPORTSDB_KEY','local-secret-never-expose')
    def reject(*args, **kwargs): raise AssertionError('Real transport forbidden')
    monkeypatch.setattr('urllib.request.urlopen',reject)
    monkeypatch.setattr('urllib.request.OpenerDirector.open',reject)


@pytest.fixture
def store(tmp_path):
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


def test_actual_http_result_uses_full_application_template_without_running_worker(client,app_module,monkeypatch):
    import blueprints.postmatch_recovery as bp
    monkeypatch.setattr(bp,'tick',lambda *a,**k:pytest.fail('GET must not execute a worker'))
    with client.session_transaction() as sess:
        sess.clear();sess.update(user_role='ADMIN',csrf_token='test-result-csrf',postmatch_last_result={
            'ok':True,'result':'PARTIAL','processed':1,'external_calls':1,
            'jobs':[{'job_id':1,'kind':'statistics','state':'RETRY','reason':'NO_STATISTICS'}]})
    response=client.get('/admin/highlights-review/workers/result')
    assert response.status_code==200, response.text[:1000]
    assert 'data-postmatch-run-result' in response.text
    assert 'Lote procesado con pendientes' in response.text
    assert 'no-store' in response.headers['Cache-Control']
