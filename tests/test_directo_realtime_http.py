"""Real Flask /live aliases and JSON -> real templates, isolated input store.

The dashboard read boundary is injected with a read-only SIMULATED_QA store.
The actual route, cache, Sports Truth, sorting, counts, permissions and Jinja
rendering are not replaced. No provider, production or user data is used.
"""
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import socket
import sqlite3
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import pytest

from engines.v935_launch_trust_engine import enrich_match_lifecycle, match_status_truth
from engines.v934_realtime_sports_engine import invalidate_realtime_cache


@pytest.fixture
def live_store(app_module, monkeypatch, tmp_path):
    now = datetime.now(ZoneInfo('Europe/Madrid'))
    path = tmp_path / 'directo-input.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE input_records (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    attempts = []
    def forbidden(*args, **kwargs):
        attempts.append('NETWORK'); raise AssertionError('Directo consumer must not contact a provider')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)

    def put(**changes):
        row = dict(id='directo-http-qa', match_id='directo-http-qa',
            home_team='Local QA', away_team='Visitante QA', competition_name='Liga QA',
            match_date=now.date().isoformat(), kickoff_time=(now-timedelta(minutes=65)).strftime('%H:%M'),
            source='persisted-provider-cache', status='LIVE', minute=67, home_score=1, away_score=0,
            last_synced_at=(now-timedelta(seconds=30)).isoformat(),
            client_status_label='Etiqueta heredada que no debe prevalecer')
        row.update(changes)
        with sqlite3.connect(path) as conn:
            conn.execute('DELETE FROM input_records')
            conn.execute('INSERT INTO input_records VALUES (?, ?)', (row['id'], json.dumps(row)))
        invalidate_realtime_cache()
        return row

    def read_summary():
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True) as conn:
            raw = [json.loads(row[0]) for row in conn.execute('SELECT payload FROM input_records')]
        rows = [enrich_match_lifecycle(row) for row in raw]
        live = [row for row in rows if match_status_truth(row)['is_live']]
        finished = [row for row in rows if match_status_truth(row)['is_finished']]
        return dict(all_valid_matches=rows, valid_matches_today=rows, valid_upcoming_matches=[],
            valid_live_events=live, valid_active_picks=[], finished_matches=finished,
            incident_matches=[], incomplete_matches=[], raw_matches_count=len(rows),
            provider_status='observed_test_store', safe_message='SIMULATED_QA', last_sync='')

    def dashboard(*args, **kwargs):
        summary = read_summary()
        return {'upcoming_matches': [], 'sports_metrics': app_module.get_sports_metrics_contract(summary)}, summary

    monkeypatch.setattr(app_module, 'v932_safe_dashboard_data', dashboard)
    monkeypatch.setattr(app_module, 'get_public_home_sports_summary', read_summary)
    put()
    yield app_module.app.test_client(), put, now, attempts
    invalidate_realtime_cache()
    assert attempts == []


@pytest.mark.parametrize('route', ['/live', '/directo', '/live-center', '/en-directo'])
def test_actual_public_route_uses_the_canonical_card(live_store, route):
    client, put, now, attempts = live_store
    response = client.get(route, environ_overrides={'REMOTE_ADDR': '127.0.0.1'})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'data-realtime-consumer="directo-v1"' in html
    assert 'data-canonical-live="true"' in html
    assert 'data-canonical-status="LIVE"' in html
    assert 'data-sports-live-confirmed="1"' in html
    assert '1 - 0' in html and 'Min 67' in html
    assert 'Etiqueta heredada que no debe prevalecer' not in html
    assert '/match/directo-http-qa' in html
    assert 'Observación registrada' in html


def test_http_html_and_json_share_the_same_fixture_truth(live_store):
    client, put, now, attempts = live_store
    html = client.get('/live').get_data(as_text=True)
    response = client.get('/api/realtime/sports?scope=all')
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['ok'] is True
    assert payload['counts']['live'] == len(payload['live']) == 1
    match = payload['live'][0]
    assert match['id'] == 'directo-http-qa'
    state = match['realtime_state']
    assert state['is_live'] is True
    assert state['provider_observed_at'] in html
    assert state['status_canonical'] == 'LIVE'
    assert state['score_home'] == match['home_score'] == 1
    assert state['score_away'] == match['away_score'] == 0
    assert int(state['minute']) == match['minute'] == 67


@pytest.mark.parametrize('changes', [
    {'status':'FT'}, {'strProgress':'FT'}, {'status':'SUSP'},
    {'last_synced_at':'2000-01-01T00:00:00+01:00'},
    {'last_synced_at':None}, {'live_updated_at':'invalid'},
])
def test_next_http_render_never_keeps_finished_stale_or_unconfirmed_live(live_store, changes):
    client, put, now, attempts = live_store
    put(**changes)
    response = client.get('/live')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'data-canonical-live="true"' not in html
    assert 'data-realtime-consumer="directo-v1"' not in html
    assert 'No hay partidos para este estado' in html
    payload = client.get('/api/realtime/sports?scope=all').get_json()
    assert payload['live'] == []
    assert all(not row['is_live'] for row in payload['matches'])


def test_zero_and_partial_score_reach_real_http_template(live_store):
    client, put, now, attempts = live_store
    put(minute=0, home_score=0, away_score=0)
    html = client.get('/live').get_data(as_text=True)
    assert '0 - 0' in html and 'Min 0' in html
    put(home_score=2, away_score=None)
    html = client.get('/live').get_data(as_text=True)
    assert 'Resultado pendiente' in html and '2 - 0' not in html


def test_empty_store_keeps_a_useful_page_and_no_live_count(live_store):
    client, put, now, attempts = live_store
    put(status='NS', kickoff_time='23:59')
    response = client.get('/live')
    assert response.status_code == 200
    assert 'No hay partidos para este estado' in response.get_data(as_text=True)
    assert client.get('/api/realtime/sports?scope=all').get_json()['counts']['live'] == 0


def test_existing_admin_protection_is_not_relaxed(live_store):
    client, _, _, _ = live_store
    response = client.get('/admin/realtime-center', follow_redirects=False)
    assert response.status_code in (302, 303, 401, 403)
    assert 'data-realtime-consumer="directo-v1"' not in response.get_data(as_text=True)


@pytest.mark.parametrize('width,height', [(1366,768), (390,844)])
def test_browser_reads_the_actual_flask_live_response(live_store, tmp_path, width, height):
    # CI's existing smoke environment installs Playwright + Chromium. Missing
    # browser is a failure/NOT_RUN to report, never a silently successful skip.
    from playwright.sync_api import sync_playwright
    import mimetypes
    client, put, now, attempts = live_store
    root = Path(__file__).resolve().parents[1]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width':width, 'height':height})
        page_errors = []; external = []
        page.on('pageerror', lambda error: page_errors.append(str(error)))
        def route(request):
            parsed = urlsplit(request.request.url)
            if parsed.netloc != 'directo-qa.invalid':
                external.append(parsed.netloc); request.abort(); return
            path = parsed.path
            if path.startswith('/static/'):
                asset = (root / path.lstrip('/')).resolve()
                if not asset.is_relative_to(root/'static') or not asset.is_file():
                    request.fulfill(status=404, body='Missing asset'); return
                request.fulfill(status=200, content_type=mimetypes.guess_type(path)[0] or 'application/octet-stream', body=asset.read_bytes()); return
            if path == '/live':
                response = client.get('/live', environ_overrides={'REMOTE_ADDR':'127.0.0.1'})
                request.fulfill(status=response.status_code, content_type='text/html; charset=utf-8', body=response.data); return
            # Do not execute other endpoints or side effects during browser QA.
            request.fulfill(status=404, content_type='application/json', body='{}')
        page.route('**/*', route)
        try:
            for mode, changes in [('fresh', {}), ('stale', {'last_synced_at':'2000-01-01T00:00:00+01:00'}), ('finished', {'status':'FT'})]:
                put(**changes)
                response = page.goto('http://directo-qa.invalid/live', wait_until='networkidle')
                assert response.status == 200
                cards = page.locator('[data-realtime-consumer="directo-v1"]')
                assert cards.count() == (1 if mode == 'fresh' else 0)
                if mode == 'fresh':
                    assert cards.locator('[data-canonical-live="true"]').count() == 1
                    assert cards.locator('[data-v934-score]').inner_text() == '1 - 0'
                    assert cards.locator('[data-v934-minute]').inner_text() == 'Min 67'
                    assert cards.locator('a[href="/match/directo-http-qa"]').count() == 1
                else:
                    assert page.locator('[data-canonical-live="true"]').count() == 0
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
                page.screenshot(path=str(tmp_path/f'directo-{mode}-{width}.png'), full_page=True)
            assert page_errors == []
            assert external == []
        finally:
            browser.close()


@pytest.mark.parametrize('width,height', [(1366,768), (390,844), (430,932)])
def test_open_actual_live_route_updates_without_reload(live_store, width, height):
    """Real Flask-rendered page + actual JS, with local HTTP intercepted in CI.

    The browser clock advances; only SIMULATED_QA observations are changed.
    No provider, cron, commercial send or real database is contacted.
    """
    from playwright.sync_api import sync_playwright, expect
    import mimetypes
    client, put, now, attempts = live_store
    root = Path(__file__).resolve().parents[1]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width':width,'height':height})
        page.clock.install(time=now)
        seen = []; errors = []; external = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        def intercept(route):
            request = route.request; parsed = urlsplit(request.url)
            if parsed.netloc != 'directo-inplace-qa.invalid':
                external.append(request.url); route.abort(); return
            if parsed.path.startswith('/static/'):
                asset = (root/parsed.path.lstrip('/')).resolve()
                if not asset.is_relative_to(root/'static') or not asset.is_file():
                    route.fulfill(status=404,body='');return
                route.fulfill(content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream', body=asset.read_bytes());return
            if parsed.path in {'/live','/api/realtime/sports'} and request.method=='GET':
                seen.append(parsed.path)
                response=client.get(parsed.path+('?' + parsed.query if parsed.query else ''))
                route.fulfill(status=response.status_code, content_type=response.content_type, body=response.data)
                return
            # All other actions/URLs are outside the fixture, never dispatched.
            route.fulfill(status=404,content_type='application/json',body='{}')
        page.route('**/*',intercept)
        try:
            page.goto('http://directo-inplace-qa.invalid/live?f=live&q=Local',wait_until='networkidle')
            card=page.locator('[data-realtime-consumer="directo-v1"]')
            expect(card).to_have_count(1)
            link=card.locator('a[href="/match/directo-http-qa"]');link.focus()
            page.evaluate('window.originalCard=document.querySelector("[data-realtime-consumer]")')
            put(home_score=2, minute=70, last_synced_at=(now+timedelta(seconds=15)).isoformat())
            page.clock.run_for(45000)
            expect(card.locator('[data-v934-score]')).to_have_text('2 - 0')
            expect(card.locator('[data-v934-minute]')).to_have_text('Min 70')
            assert link.evaluate('(node)=>node===document.activeElement')
            assert page.evaluate('originalCard===document.querySelector("[data-realtime-consumer]")')
            assert page.url.endswith('/live?f=live&q=Local')
            put(status='FT', home_score=2, minute=90, last_synced_at=(now+timedelta(seconds=60)).isoformat())
            page.clock.run_for(45000)
            expect(card.locator('[data-canonical-live]')).to_have_attribute('data-canonical-live','false')
            expect(card.locator('[data-v934-status]')).to_contain_text('Finalizado')
            expect(card.locator('[data-v934-minute]')).to_be_hidden()
            assert seen.count('/live')==1
            assert seen.count('/api/realtime/sports')==2
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            assert errors==[] and external==[] and attempts==[]
        finally:
            browser.close()
