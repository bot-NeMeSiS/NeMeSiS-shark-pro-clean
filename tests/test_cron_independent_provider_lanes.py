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
    monkeypatch.setenv('AUTOMATION_SECRET', 'isolated-lane-test')
    monkeypatch.setattr(app_module, 'seed_core', lambda: None)
    monkeypatch.setattr(app_module, 'run_sports_sync_cycle', lambda **k: pytest.fail('inline Sports'))
    monkeypatch.setattr(app_module, 'sync_odds_events', lambda **k: pytest.fail('inline Odds'))
    monkeypatch.setattr(app_module, 'telegram_scheduler_tick', lambda **k: {'ok': True, 'status': 'QUEUE_EMPTY'})
    result = client.post('/api/automation/telegram/tick', headers={
        'X-Automation-Secret': 'isolated-lane-test', 'X-NeMeSiS-Cron-Runner': 'render-cron'})
    assert result.status_code == 200
    assert result.get_json()['ok'] is True
    assert 'sports_pipeline' not in result.get_json()


@pytest.mark.parametrize('path', ['/api/automation/sports/sync', '/api/automation/odds/sync'])
def test_provider_routes_require_header_and_post(client, app_module, monkeypatch, path):
    monkeypatch.setenv('AUTOMATION_SECRET', 'isolated-lane-test')
    monkeypatch.setattr(app_module, 'bounded_sports_sync', lambda **k: pytest.fail('unauthorized'))
    monkeypatch.setattr(app_module, 'bounded_odds_sync', lambda **k: pytest.fail('unauthorized'))
    assert client.get(path).status_code == 405
    assert client.post(path).status_code == 403
    assert client.post(path+'?secret=isolated-lane-test').status_code == 403


def test_sports_wrapper_explicitly_excludes_odds(app_module, monkeypatch):
    seen = {}
    def sports(**kwargs):
        seen.update(kwargs)
        return {'ok': True, 'status': 'OK'}
    monkeypatch.setattr(app_module, 'run_sports_sync_cycle', sports)
    assert app_module.bounded_sports_sync()['ok']
    assert seen['include_odds'] is False


@pytest.mark.parametrize('stage,expected_errors', [
    ({'ok':False,'status':'CACHE_PROVIDER_FAILURE_FREE_PLAN_RESTRICTED','error':'cached_provider_failure'}, []),
    ({'ok':True,'status':'PROVIDER_FAILURE_BACKOFF_ACCESS_RESTRICTED','errors':['provider_failure_backoff']}, []),
    ({'ok':False,'status':'ERROR','errors':['TIME_BUDGET']}, []),
    ({'ok':False,'status':'INVALID_RESPONSE','error':'invalid'}, ['fixtures_INVALID_RESPONSE']),
    ({'ok':False,'status':'ERROR','error':'TimeoutError'}, ['fixtures_ERROR']),
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


@pytest.mark.parametrize('payload,expected', [
    ({'ok':True,'status':'OK'}, 'PASS'),
    ({'ok':True,'status':'PARTIAL','controlled_deferrals':['TIME_BUDGET']}, 'PARTIAL'),
    ({'ok':True,'status':'PARTIAL','errors_count':1}, 'FAIL'),
    ({'ok':False,'status':'PIPELINE_ERROR'}, 'FAIL'),
])
def test_provider_lane_distinguishes_deferral_and_failure(monkeypatch, payload, expected):
    monkeypatch.setattr(master.urllib.request, 'urlopen', lambda *a, **k: Response(payload))
    assert master.odds_tick('https://example.invalid','test')['odds_status'] == expected


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
