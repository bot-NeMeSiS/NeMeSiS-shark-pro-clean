import json
import pytest
from engines.cron_request_budget import CronRequestBudget, CronTimeBudget, exhausted, request_timeout
from tools import render_cron_master_tick as master


def test_deadline_caps_transport_and_restores_context():
    now = [10.]
    with CronRequestBudget(seconds=16, clock=lambda: now[0]) as scope:
        assert request_timeout(12) == 4
        now[0] = 25.5
        assert request_timeout(12) == .5
        now[0] = 26
        with pytest.raises(CronTimeBudget):
            request_timeout(12)
        assert scope.deferred and exhausted()
    assert request_timeout(12) == 12


def test_render_telegram_never_calls_sports_or_odds(client, app_module, monkeypatch):
    founders = []
    monkeypatch.setenv('AUTOMATION_SECRET', 'isolated-lane-test')
    monkeypatch.setattr(app_module, 'seed_core', lambda: None)
    monkeypatch.setattr(app_module, 'run_sports_sync_cycle', lambda **k: pytest.fail('inline Sports'))
    monkeypatch.setattr(app_module, 'sync_odds_events', lambda **k: pytest.fail('inline Odds'))
    monkeypatch.setattr(app_module, 'telegram_scheduler_tick', lambda **k: {'ok': True, 'status': 'QUEUE_EMPTY'})
    monkeypatch.setattr(app_module, 'founder_alert_tick', lambda *a: founders.append(1) or {'ok':True,'sent':0})
    result = client.post('/api/automation/telegram/tick', headers={
        'X-Automation-Secret': 'isolated-lane-test', 'X-NeMeSiS-Cron-Runner': 'render-cron'})
    assert result.status_code == 200
    assert result.get_json()['ok'] is True
    assert 'sports_pipeline' not in result.get_json()
    assert founders == [1]


@pytest.mark.parametrize('path', ['/api/automation/sports/sync', '/api/automation/odds/sync'])
def test_provider_routes_require_header_and_post(client, app_module, monkeypatch, path):
    monkeypatch.setenv('AUTOMATION_SECRET', 'isolated-lane-test')
    monkeypatch.setattr(app_module, 'bounded_sports_sync', lambda **k: pytest.fail('unauthorized'))
    monkeypatch.setattr(app_module, 'bounded_odds_sync', lambda **k: pytest.fail('unauthorized'))
    assert client.get(path).status_code == 405
    assert client.post(path).status_code == 403
    assert client.post(path+'?secret=isolated-lane-test').status_code == 403


@pytest.mark.parametrize('path', ['/api/automation/sports/sync', '/api/automation/odds/sync'])
def test_provider_header_passes_real_request_boundary_without_browser_csrf(client, app_module, monkeypatch, path):
    monkeypatch.setenv('AUTOMATION_SECRET', 'isolated-boundary-test')
    calls = []
    def execute(endpoint, *args, **kwargs):
        calls.append(endpoint)
        return app_module.jsonify({'ok':True, 'status':'QA_HEADER_ACCEPTED'})
    monkeypatch.setattr(app_module, 'automation_cron_result', execute)
    response = client.post(path, json={}, headers={
        'X-Automation-Secret':'isolated-boundary-test', 'X-NeMeSiS-Cron-Runner':'render-cron'})
    assert response.status_code == 200, response.get_json()
    assert calls == ['sports_sync' if '/sports/' in path else 'odds_sync']
    calls.clear()
    for headers in ({}, {'X-Automation-Secret':'incorrect'}, {'X-CSRF-Token':'browser-token'}):
        response = client.post(path, json={}, headers=headers)
        assert response.status_code == 403
        assert response.get_json()['query_secret_accepted'] is False
    assert calls == []


def test_odds_boundary_exemption_is_exact(app_module):
    assert app_module.csrf_exempt_path('/api/automation/odds/sync') is True
    assert app_module.csrf_exempt_path('/api/automation/odds/sync/extra') is False


def test_sports_wrapper_explicitly_excludes_odds(app_module, monkeypatch):
    seen = {}
    def sports(**kwargs):
        seen.update(kwargs)
        return {'ok': True, 'status': 'OK'}
    monkeypatch.setattr(app_module, 'run_sports_sync_cycle', sports)
    assert app_module.bounded_sports_sync()['ok']
    assert seen['include_odds'] is False


def test_sports_diagnostic_failure_preserves_execution(app_module, monkeypatch):
    monkeypatch.setattr(app_module, 'run_sports_sync_cycle', lambda **k: {'ok':True,'status':'OK'})
    monkeypatch.setattr(app_module, 'api_exploitation_summary', lambda *a: {})
    monkeypatch.setattr(app_module, '_build_sports_pipeline_diagnostics', lambda *a: (_ for _ in ()).throw(ValueError()))
    result = app_module.bounded_sports_sync()
    assert result['ok'] is True
    assert result['sports_pipeline']['status'] == 'CONTROLLED_ERROR'


@pytest.mark.parametrize('stage,expected_errors', [
    ({'ok':False,'status':'CACHE_PROVIDER_FAILURE_FREE_PLAN_RESTRICTED','error':'cached_provider_failure'}, []),
    ({'ok':True,'status':'PROVIDER_FAILURE_BACKOFF_ACCESS_RESTRICTED','errors':['provider_failure_backoff']}, []),
    ({'ok':False,'status':'ERROR','errors':['TIME_BUDGET']}, []),
    ({'ok':False,'status':'INVALID_RESPONSE','error':'invalid'}, ['fixtures_INVALID_RESPONSE']),
    ({'ok':False,'status':'ERROR','error':'TimeoutError'}, ['fixtures_NETWORK_OR_TIMEOUT']),
])
def test_sports_deferral_never_hides_technical_error(app_module, monkeypatch, stage, expected_errors):
    monkeypatch.setattr(app_module, 'run_sports_sync_cycle', lambda **k: {
        'ok': True, 'status':'PARTIAL', 'fixtures':stage, 'fallback':{'ok':True},
        'errors':['legacy_error']})
    result = app_module.bounded_sports_sync()
    assert result['technical_errors'] == expected_errors
    compact = app_module._cron_compact_payload('sports_sync', result, '', '')
    assert compact['errors_count'] == len(expected_errors)


def test_odds_deadline_stops_fanout_without_fabricating_provider_error(app_module, monkeypatch):
    now = [0.]
    calls = []
    monkeypatch.setattr(app_module, 'odds_competitions', lambda: [{'name':str(i),'odds_key':str(i)} for i in range(20)])
    def fetch(*a, **k):
        calls.append(a)
        now[0] += 4
        return {'ok': True, 'payload': [], 'quota': {}}
    monkeypatch.setattr(app_module, 'odds_api_request', fetch)
    with CronRequestBudget(clock=lambda: now[0]):
        events, errors, quota = app_module.fetch_odds_events()
    assert len(calls) == 4
    assert errors == []
    assert quota['controlled_deferrals'] == ['TIME_BUDGET']


class Response:
    status = 200
    def __init__(self, payload): self.payload = payload
    def read(self, *a): return json.dumps(self.payload).encode()
    def __enter__(self): return self
    def __exit__(self, *a): pass


def test_odds_compact_and_runner_preserve_closed_failure_evidence(app_module, monkeypatch):
    result = {'ok':False, 'status':'PROVIDER_FAILURE_STOPPED_EARLY', 'errors':['provider'], 'external_calls':1,
              'quota':{'http_status':401,'error_type':'HTTPError','requests_remaining':0,'error_code':'OUT_OF_USAGE_CREDITS',
                       'events_received':0,'events_with_bookmakers':0,'bookmakers_received':0,'markets_received':0,'events_with_h2h':0},
              'odds_snapshots':{'inserted':0,'updated':0,'skipped':0,'linked':0}}
    compact = app_module._cron_compact_payload('odds_sync', result, '', '')
    monkeypatch.setattr(master.urllib.request, 'urlopen', lambda *a, **k: Response(compact))
    observed = master.odds_tick('https://example.invalid', 'test')
    assert observed['odds_status'] == 'FAIL'
    assert observed['provider_http'] == 401
    assert observed['provider_error_code'] == 'OUT_OF_USAGE_CREDITS'
    assert observed['provider_error_type'] == 'HTTPError'
    assert observed['provider_requests_remaining'] == 0
    assert observed['provider_observation_current'] is True
    assert observed['odds_events_received'] == 0
    assert observed['odds_events_with_h2h'] == 0
    assert observed['odds_snapshots_inserted'] == 0
    assert observed['odds_snapshots_skipped'] == 0
    result['external_calls'] = 0
    compact = app_module._cron_compact_payload('odds_sync', result, '', '')
    assert compact['provider_observation_current'] is False
    assert compact['provider_error_code'] == ''
    assert compact['last_provider_error_code'] == 'OUT_OF_USAGE_CREDITS'
    result['quota']['error_type'] = 'private-url?apiKey=secret'
    compact = app_module._cron_compact_payload('odds_sync', result, '', '')
    assert compact['provider_error_type'] == ''
    assert compact['last_provider_error_type'] == 'UNKNOWN'
    assert 'private-url?apiKey=secret' not in json.dumps(compact)


def test_odds_backoff_is_explained_without_reusing_old_provider_observations(app_module, monkeypatch):
    result = {
        'ok': True,
        'status': 'PARTIAL',
        'reason': 'provider_failure_cooldown',
        'skipped': True,
        'provider_failure_backoff': True,
        'retry_after': '2026-10-19T18:30:00+02:00',
        'external_calls': 0,
        'quota': {
            'http_status': 200,
            'requests_remaining': 123,
            'credential_tier_selected': 'LEGACY',
            'error_type': 'HTTPError',
            'error_code': 'OUT_OF_USAGE_CREDITS',
        },
    }
    compact = app_module._cron_compact_payload('odds_sync', result, '', '')
    assert compact['reason'] == 'PROVIDER_FAILURE_COOLDOWN'
    assert compact['skipped'] is True and compact['provider_failure_backoff'] is True
    assert compact['provider_observation_current'] is False
    assert compact['retry_after'] == '2026-10-19T18:30:00+02:00'
    assert compact['provider_http'] is None
    assert compact['credential_tier_selected'] == ''
    assert compact['provider_requests_remaining'] is None
    assert compact['provider_error_is_current'] is False
    assert compact['provider_error_code'] == ''
    assert compact['provider_error_type'] == ''
    assert compact['last_provider_error_code'] == 'OUT_OF_USAGE_CREDITS'
    assert compact['last_provider_error_type'] == 'HTTPError'

    monkeypatch.setattr(master.urllib.request, 'urlopen', lambda *a, **k: Response(compact))
    observed = master.odds_tick('https://example.invalid', 'test')
    assert observed['odds_status'] == 'PARTIAL'
    assert observed['odds_skip_reason'] == 'PROVIDER_FAILURE_COOLDOWN'
    assert observed['odds_skipped'] is True
    assert observed['odds_provider_failure_backoff'] is True
    assert observed['odds_retry_after'] == '2026-10-19T18:30:00+02:00'
    assert observed['provider_observation_current'] is False
    assert observed['provider_error_is_current'] is False
    assert observed['provider_error_code'] == ''
    assert observed['provider_error_type'] == ''
    assert observed['last_provider_error_code'] == 'OUT_OF_USAGE_CREDITS'
    assert observed['last_provider_error_type'] == 'HTTPError'
    assert observed['provider_http'] is None
    assert observed['credential_tier_selected'] == ''
    assert observed['provider_requests_remaining'] is None

    result['reason'] = 'private-secret-provider-message'
    result['retry_after'] = 'private-secret-provider-message'
    redacted = app_module._cron_compact_payload('odds_sync', result, '', '')
    assert redacted['reason'] == '' and redacted['retry_after'] == ''
    assert 'private-secret-provider-message' not in json.dumps(redacted)


def test_odds_cached_tick_does_not_relabel_previous_pipeline_counts_as_current(app_module):
    result = {
        'ok': True,
        'status': 'CACHE_REUSED',
        'external_calls': 0,
        'quota': {
            'http_status': 200,
            'requests_remaining': 436,
            'events_received': 16,
            'events_with_h2h': 12,
        },
        'odds_snapshots': {'inserted': 12, 'updated': 0, 'skipped': 4, 'linked': 12},
    }

    compact = app_module._cron_compact_payload('odds_sync', result, '', '')

    assert compact['provider_observation_current'] is False
    assert compact['odds_events_received'] is None
    assert compact['odds_events_with_h2h'] is None
    assert compact['odds_snapshots_inserted'] is None


def test_combined_odds_tick_attributes_http_and_snapshots_to_api_football(app_module, monkeypatch):
    result = {
        'ok': True,
        'status': 'OK',
        'external_calls': 2,
        'processed': 4,
        'snapshots_inserted': 38,
        'provider_results': {
            'api_football': {
                'ok': True,
                'status': 'AVAILABLE',
                'external_calls': 2,
                'provider_http': 200,
                'provider_http_statuses': [200, 200],
                'provider_observation_current': True,
                'processed': 4,
                'fixtures_count': 4,
                'snapshots_inserted': 38,
                'failure_categories': [],
            },
            'the_odds_api': {
                'ok': True,
                'status': 'UNFUNDED_NOT_CONFIGURED',
                'funded': False,
                'external_calls': 0,
                'quota': {'http_status': 200, 'requests_remaining': 900},
                'odds_snapshots': {'inserted': 13, 'updated': 2, 'skipped': 1, 'linked': 13},
            },
        },
    }

    compact = app_module._cron_compact_payload('odds_sync', result, '', '')
    assert compact['provider_observation_provider'] == 'API_FOOTBALL'
    assert compact['provider_observation_current'] is True
    assert compact['provider_http'] == 200
    assert compact['api_football_provider_http'] == 200
    assert compact['api_football_http_statuses'] == [200, 200]
    assert compact['api_football_snapshots_inserted'] == 38
    assert compact['the_odds_api_status'] == 'UNFUNDED_NOT_CONFIGURED'
    assert compact['the_odds_api_external_calls'] == 0
    assert compact['the_odds_api_provider_http'] is None
    assert compact['the_odds_api_funded'] is False
    assert compact['credential_tier_selected'] == ''
    assert compact['provider_requests_remaining'] is None
    assert compact['odds_events_received'] is None
    assert compact['odds_snapshots_inserted'] is None

    monkeypatch.setattr(master.urllib.request, 'urlopen', lambda *a, **k: Response(compact))
    observed = master.odds_tick('https://example.invalid', 'test')
    assert observed['provider_observation_provider'] == 'API_FOOTBALL'
    assert observed['api_football_status'] == 'AVAILABLE'
    assert observed['api_football_external_calls'] == 2
    assert observed['api_football_provider_http'] == 200
    assert observed['api_football_http_statuses'] == [200, 200]
    assert observed['api_football_snapshots_inserted'] == 38
    assert observed['the_odds_api_status'] == 'UNFUNDED_NOT_CONFIGURED'
    assert observed['the_odds_api_external_calls'] == 0
    assert observed['the_odds_api_provider_http'] is None
    assert observed['the_odds_api_funded'] is False
    assert observed['provider_requests_remaining'] is None


@pytest.mark.parametrize('code,expected', [('OUT_OF_USAGE_CREDITS','OUT_OF_USAGE_CREDITS'),
                                         ('INVALID_KEY','INVALID_KEY'), ('private-secret','')])
def test_odds_existing_error_response_keeps_only_documented_code(app_module, monkeypatch, code, expected):
    import io
    import urllib.error
    monkeypatch.setenv('THE_ODDS_API_KEY', 'isolated-test-key')
    calls = []
    def fetch(*args, **kwargs):
        calls.append(1)
        body = json.dumps({'error_code':code, 'message':'private-secret'}).encode()
        raise urllib.error.HTTPError('https://example.invalid', 401, 'unauthorized', {}, io.BytesIO(body))
    monkeypatch.setattr(app_module, 'fetch_json_response', fetch)
    result = app_module.odds_api_request('sports/test/odds')
    assert result['error_code'] == expected
    assert result['http_status'] == 401
    assert result['error'] == 'HTTPError'
    assert len(calls) == 1
    assert 'private-secret' not in json.dumps(result)


@pytest.mark.parametrize('tick', [master.telegram_tick, master.postmatch_tick])
def test_uncertain_http_error_retains_only_correlation_metadata(monkeypatch, tick):
    import urllib.error
    calls = []
    def transport(*args, **kwargs):
        calls.append(args)
        raise urllib.error.HTTPError('https://example.invalid', 502, 'bad gateway', {
            'Server':'cloudflare', 'CF-Ray':'abc01234-LHR', 'Rndr-Id':'private?secret=value',
            'Set-Cookie':'private-cookie'}, None)
    monkeypatch.setattr(master.urllib.request, 'urlopen', transport)
    observed = tick('https://example.invalid', 'test')
    assert len(calls) == 1
    assert observed['response_server'] == 'cloudflare'
    assert observed['edge_request_id'] == 'abc01234-LHR'
    assert 'render_request_id' not in observed
    assert 'private' not in json.dumps(observed)


@pytest.mark.parametrize('payload,expected', [
    ({'ok':True,'status':'OK'}, 'PASS'),
    ({'ok':True,'status':'PARTIAL','controlled_deferrals':['TIME_BUDGET']}, 'PARTIAL'),
    ({'ok':True,'status':'PARTIAL','errors_count':1}, 'FAIL'),
    ({'ok':False,'status':'PIPELINE_ERROR'}, 'FAIL'),
])
def test_provider_lane_distinguishes_deferral_and_failure(monkeypatch, payload, expected):
    monkeypatch.setattr(master.urllib.request, 'urlopen', lambda *a, **k: Response(payload))
    assert master.odds_tick('https://example.invalid','test')['odds_status'] == expected


def test_odds_controlled_deferrals_are_logged_without_untrusted_values(monkeypatch):
    payload = {
        'ok': True,
        'status': 'PARTIAL',
        'controlled_deferrals': ['TIME_BUDGET', 'FREE_BUDGET', 'private-secret'],
        'external_calls': 0,
        'provider_observation_current': False,
    }
    monkeypatch.setattr(master.urllib.request, 'urlopen', lambda *a, **k: Response(payload))
    result = master.odds_tick('https://example.invalid', 'private-secret')
    assert result['odds_status'] == 'PARTIAL'
    assert result['odds_controlled_deferrals'] == ['TIME_BUDGET', 'FREE_BUDGET']
    assert result['external_calls'] == 0
    assert result['provider_http'] is None
    assert 'private-secret' not in json.dumps(result)


def test_master_observes_all_lanes_after_uncertain_odds_post(monkeypatch, capsys):
    calls = []
    def transport(request, timeout):
        calls.append((request.get_method(),request.full_url))
        if request.get_method() == 'GET': return Response({})
        if request.full_url.endswith(master.ODDS_ENDPOINT): raise TimeoutError()
        if 'highlights' in request.full_url: return Response({'highlights_sync':{'ok':True,'status':'OK'}})
        if 'continuous-evolution' in request.full_url: return Response({'ok':True,'result':'SKIPPED_NOT_DUE','safe_mode':'PASS','storage':'PASS'})
        if 'postmatch' in request.full_url: return Response({'ok':True,'result':'SKIPPED_DISABLED'})
        return Response({'ok':True,'status':'OK'})
    monkeypatch.setenv('PUBLIC_BASE_URL','https://example.invalid')
    monkeypatch.setenv('AUTOMATION_SECRET','test')
    monkeypatch.setattr(master.urllib.request,'urlopen',transport)
    monkeypatch.setattr(master,'backup_due',lambda *a:False)
    assert master.main() == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload['odds_status'] == 'FAIL'
    assert payload['sports_status'] == payload['telegram_status'] == 'PASS'
    assert sum(method=='POST' and url.endswith(master.ODDS_ENDPOINT) for method,url in calls) == 1
    for index,(method,url) in enumerate(calls):
        if method=='POST' and any(url.endswith(endpoint) for endpoint in [master.SPORTS_ENDPOINT,master.ODDS_ENDPOINT,master.TELEGRAM_ENDPOINT]):
            assert calls[index-1][0] == 'GET'


def test_sports_failure_summary_preserves_safe_stage_and_no_secret(monkeypatch):
    payload = {'ok': False, 'status': 'PARTIAL', 'errors_count': 3,
               'technical_errors': ['fixtures_ERROR', 'deep_enrichment_PROVIDER_UNAVAILABLE',
                                    'https://provider.invalid/private-key'],
               'controlled_deferrals': ['TIME_BUDGET', 'private-key']}
    monkeypatch.setattr(master.urllib.request, 'urlopen', lambda *a, **k: Response(payload))
    result = master.sports_tick('https://qa.invalid', 'private-key')
    assert result['sports_status'] == 'FAIL'
    assert result['sports_technical_errors'] == [
        {'stage': 'fixtures', 'reason': 'ERROR'},
        {'stage': 'deep_enrichment', 'reason': 'PROVIDER_UNAVAILABLE'},
        {'stage': 'UNKNOWN', 'reason': 'UNCLASSIFIED'}]
    assert result['sports_errors_count'] == 3
    assert result['sports_controlled_deferrals'] == ['TIME_BUDGET']
    assert 'private-key' not in json.dumps(result) and 'provider.invalid' not in json.dumps(result)
