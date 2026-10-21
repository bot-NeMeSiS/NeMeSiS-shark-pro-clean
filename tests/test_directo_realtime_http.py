"""Real Flask /live aliases and JSON -> real templates, isolated input store.

The dashboard read boundary is injected with a read-only SIMULATED_QA store.
The actual route, cache, Sports Truth, sorting, counts, permissions and Jinja
rendering are not replaced. No provider, production or user data is used.
"""
from copy import deepcopy
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import threading
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
    original_connect = socket.socket.connect
    original_create = socket.create_connection
    def forbidden(*args, **kwargs):
        attempts.append('NETWORK'); raise AssertionError('Directo consumer must not contact a provider')
    def local_connect(sock, address, *args, **kwargs):
        if isinstance(address, tuple) and address[0] in ('127.0.0.1', '::1', 'localhost'):
            return original_connect(sock, address, *args, **kwargs)
        return forbidden()
    def local_create(address, *args, **kwargs):
        if isinstance(address, tuple) and address[0] in ('127.0.0.1', '::1', 'localhost'):
            return original_create(address, *args, **kwargs)
        return forbidden()
    monkeypatch.setattr(socket.socket, 'connect', local_connect)
    monkeypatch.setattr(socket, 'create_connection', local_create)

    def put(**changes):
        observed_now = datetime.now(ZoneInfo('Europe/Madrid'))
        row = dict(id='directo-http-qa', match_id='directo-http-qa',
            home_team='Local QA', away_team='Visitante QA', competition_name='Liga QA',
            match_date=(observed_now-timedelta(minutes=65)).date().isoformat(), kickoff_time=(observed_now-timedelta(minutes=65)).strftime('%H:%M'),
            source='persisted-provider-cache', status='LIVE', minute=67, home_score=1, away_score=0,
            last_synced_at=(observed_now-timedelta(seconds=30)).isoformat(),
            client_status_label='Etiqueta heredada que no debe prevalecer')
        row.update(changes)
        if 'kickoff_time' in changes and 'match_date' not in changes:
            row['match_date'] = observed_now.date().isoformat()
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


def test_directo_route_shows_cached_stats_without_provider_calls(live_store, app_module, monkeypatch):
    client, put, now, attempts = live_store
    tracker = {
        'provider': 'api_football',
        'source_label': 'API-Football Pro',
        'statistics_updated_at': '2026-10-17T16:01:00Z',
        'updated_at': '2026-10-17T16:01:00Z',
        'stats': {'available': True},
        'stat_cards': [
            {'key': 'shots_on_goal', 'label': 'Tiros a puerta', 'home': '5', 'away': '2'},
            {'key': 'fouls', 'label': 'Faltas', 'home': '8', 'away': '14'},
            {'key': 'corners', 'label': 'Córners', 'home': '4', 'away': '1'},
            {'key': 'throw_ins', 'label': 'Saques de banda', 'home': '12', 'away': '9'},
            {'key': 'possession', 'label': 'Posesión', 'home': '61%', 'away': '39%',
             'home_captured_at': '2026-10-17T16:00:00Z', 'away_captured_at': '2026-10-17T16:00:00Z'},
            {'key': 'total_shots', 'label': 'Tiros totales', 'home': '12', 'away': '7'},
            {'key': 'saves', 'label': 'Paradas', 'home': '3', 'away': '5'},
            {'key': 'yellow_cards', 'label': 'Tarjetas amarillas', 'home': '1', 'away': '2'},
            {'key': 'offsides', 'label': 'Fueras de juego', 'home': '2', 'away': '0'},
        ],
        'field_state': {
            'possession_available': True,
            'home_possession_pct': 61,
            'away_possession_pct': 39,
            'activity_index_available': True,
            'activity_index_method': 'weighted_provider_statistics',
            'home_activity_index_pct': 64,
            'away_activity_index_pct': 36,
        },
    }
    monkeypatch.setattr(
        app_module,
        'live_tracker_summaries_for_matches',
        lambda _db, matches: {'directo-http-qa': tracker} if matches else {},
    )
    response = client.get('/directo', environ_overrides={'REMOTE_ADDR': '127.0.0.1'})
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    from engines.canonical_assets import canonical_css_href, template_css_href
    root = Path(__file__).resolve().parents[1]
    expected_css = template_css_href((root / 'templates/base.html').read_text(encoding='utf-8'), app_module.APP_VERSION)
    assert expected_css and canonical_css_href(html, app_module.APP_VERSION) == expected_css
    shipped_css = (Path(__file__).resolve().parents[1] / 'static' / 'product-system.css').read_text(encoding='utf-8')
    assert '.v934-live-stats__all-row' in shipped_css
    assert 'v934-live-stats' in html
    assert 'Reparto porcentual de posesión: Local QA 61%, Visitante QA 39%.' in html
    assert 'data-visualization="aggregate-share"' in html
    assert 'data-spatial-map-available="false"' in html
    assert 'no es un mapa de zonas ni la ubicación del balón' in html
    assert 'data-activity-index="weighted-provider-statistics"' in html
    assert 'data-provider-metric="false"' in html
    assert 'Local QA 64%, Visitante QA 36%.' in html
    assert 'no es un dato del proveedor' in html
    assert 'Tiros a puerta' in html and 'Faltas' in html and 'Córners' in html and 'Saques de banda' in html
    assert 'data-live-statistics-more' in html
    assert 'Ver todas las estadísticas disponibles' in html
    stat_rows = dict(re.findall(
        r'<div class="v934-live-stats__all-row" role="row" data-stat-key="([^"]+)">(.*?)</div>',
        html,
        re.DOTALL,
    ))
    assert set(stat_rows) == {'total_shots', 'saves', 'yellow_cards', 'offsides'}
    assert 'Tiros totales' in stat_rows['total_shots'] and '>12</span>' in stat_rows['total_shots'] and '>7</span>' in stat_rows['total_shots']
    assert 'Paradas' in stat_rows['saves'] and '>3</span>' in stat_rows['saves'] and '>5</span>' in stat_rows['saves']
    assert 'Tarjetas amarillas' in stat_rows['yellow_cards'] and '>1</span>' in stat_rows['yellow_cards'] and '>2</span>' in stat_rows['yellow_cards']
    assert 'Fueras de juego' in stat_rows['offsides'] and '>2</span>' in stat_rows['offsides'] and '>0</span>' in stat_rows['offsides']
    assert html.count('Tiros a puerta') == 1
    assert '2026-10-17T16:01:00Z' in html
    assert attempts == []


def test_live_statistics_projection_drops_legacy_placeholders_and_untrusted_side_clock(app_module):
    captured_at = '2026-10-17T16:00:00Z'
    projected = app_module._v970_live_statistics_projection({
        'provider': 'api_football', 'fixture_id': '777', 'available': True,
        'read_only': True, 'external_calls': 0,
        'stat_cards': [
            {'key': 'fouls', 'label': 'Faltas', 'home': 'N/A', 'away': '3',
             'home_captured_at': captured_at, 'away_captured_at': captured_at},
            {'key': 'corners', 'label': 'Córners', 'home': {'bad': 'value'}, 'away': '—'},
        ],
        'field_state': {},
    }, '777')
    assert projected is not None
    assert projected['stat_cards'] == [{
        'key': 'fouls', 'label': 'Faltas', 'home': '—', 'away': '3',
        'home_captured_at': '', 'away_captured_at': captured_at,
    }]


def test_directo_possession_chart_uses_its_own_capture_and_hides_mixed_receipts(app_module):
    capture = '2026-10-17T16:00:00Z'
    tracker = {
        'provider': 'api_football', 'statistics_updated_at': '2026-10-17T16:05:00Z',
        'stats': {'available': True},
        'stat_cards': [
            {'key': 'shots_on_goal', 'label': 'Tiros a puerta', 'home': '5', 'away': '2',
             'home_captured_at': '2026-10-17T16:05:00Z', 'away_captured_at': '2026-10-17T16:05:00Z'},
            {'key': 'possession', 'label': 'Posesión', 'home': '61%', 'away': '39%',
             'home_captured_at': capture, 'away_captured_at': capture},
        ],
        'field_state': {'possession_available': True, 'home_possession_pct': 61, 'away_possession_pct': 39},
    }
    match = {
        'home_team': 'Local QA', 'away_team': 'Visitante QA', 'api_football_live_tracker': tracker,
        'realtime_state': {'contract': 'NEMESIS-REALTIME-STATE-V1', 'sports_truth_contract': 'MATCH-STATUS-TRUTH-V2',
            'is_live': True, 'is_stale': False, 'status_conflict': False, 'status_canonical': 'LIVE', 'minute': 15},
    }
    with app_module.app.test_request_context('/directo'):
        template = app_module.app.jinja_env.from_string(
            "{% from 'components/realtime_live_card.html' import live_card %}{{ live_card(match) }}")
        rendered = template.render(match=match)
    assert f'data-possession-captured-at="{capture}"' in rendered
    assert 'data-stat-updated-at="2026-10-17T16:05:00Z"' in rendered

    tracker['stat_cards'][1]['away_captured_at'] = '2026-10-17T16:01:00Z'
    with app_module.app.test_request_context('/directo'):
        rendered_mixed = template.render(match=match)
    assert 'data-live-stat-possession' not in rendered_mixed
    assert 'data-stat-key="possession"' in rendered_mixed
    assert f'datetime="{capture}"' in rendered_mixed
    assert 'datetime="2026-10-17T16:01:00Z"' in rendered_mixed


def test_matches_poll_includes_compact_cached_stats_and_etag_tracks_them(live_store, app_module, monkeypatch):
    client, put, _now, attempts = live_store
    put(id='af-777', match_id='af-777', external_id='777', fixture_id='777', source='api_football_live_tracker')
    captured_at = datetime.now().astimezone().replace(microsecond=0).isoformat()
    current = {'home': '5'}
    calls = []

    def cached(_db, matches, limit=40):
        calls.append((len(matches), limit))
        return {'777': {
            'provider': 'api_football', 'fixture_id': '777', 'available': True,
            'read_only': True, 'external_calls': 0, 'statistics_updated_at': captured_at,
            'stats': {'available': True, 'teams': [{'raw': {'should_never': 'leak'}}]},
            'stat_cards': [{
                'key': 'shots_on_goal', 'label': 'Tiros a puerta',
                'home': current['home'], 'away': '2',
                'home_captured_at': captured_at, 'away_captured_at': captured_at,
            }],
            'field_state': {'possession_available': False},
        }}

    monkeypatch.setattr(app_module, 'live_tracker_summaries_for_matches', cached)
    first = client.get('/api/realtime/sports?scope=matches')
    first_payload = first.get_json()
    live = first_payload['matches'][0]['live_statistics']
    assert live['fixture_id'] == '777'
    assert live['external_calls'] == 0
    assert live['stat_cards'][0]['home'] == '5'
    assert 'stats' not in live and 'raw' not in str(live)
    first_etag = first.headers['ETag']

    current['home'] = '6'
    second = client.get('/api/realtime/sports?scope=matches')
    assert second.get_json()['matches'][0]['live_statistics']['stat_cards'][0]['home'] == '6'
    assert second.headers['ETag'] != first_etag
    assert calls == [(1, 40), (1, 40)]

    live_scope = client.get('/api/realtime/sports?scope=live').get_json()
    assert 'live_statistics' not in live_scope['live'][0]
    assert attempts == []


def test_directo_route_omits_empty_all_stats_disclosure(live_store, app_module, monkeypatch):
    client, _put, _now, attempts = live_store
    tracker = {
        'stats': {'available': True},
        'stat_cards': [
            {'key': 'shots_on_goal', 'label': 'Tiros a puerta', 'home': '5', 'away': '2'},
            {'key': 'fouls', 'label': 'Faltas', 'home': '8', 'away': '14'},
        ],
        'field_state': {'possession_available': False},
    }
    monkeypatch.setattr(
        app_module,
        'live_tracker_summaries_for_matches',
        lambda _db, matches: {'directo-http-qa': tracker} if matches else {},
    )

    response = client.get('/directo', environ_overrides={'REMOTE_ADDR': '127.0.0.1'})
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Tiros a puerta' in html and 'Faltas' in html
    assert 'data-live-statistics-more' not in html
    assert attempts == []


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


@pytest.mark.parametrize('status,minute,canonical,label', [
    ('HT',45,'HALFTIME','Descanso'),
    ('ET',105,'LIVE','Prórroga'),
    ('P',120,'LIVE','Penaltis'),
    ('PEN',120,'FINISHED','Final tras penaltis'),
    ('AET',120,'FINISHED','Final tras prórroga'),
    ('SUSP',61,'SUSPENDED','Suspendido'),
    ('LIVE','45+3','LIVE','En directo'),
    ('LIVE','90+7','LIVE','En directo'),
])
def test_observed_period_is_shared_by_http_projection_and_match_center(live_store, app_module, monkeypatch, status, minute, canonical, label):
    client,put,now,_=live_store
    row=put(status=status,minute=minute)
    monkeypatch.setattr(app_module,'match_detail',lambda match_id,**kwargs:{'match':deepcopy(row),'related_picks':[]})
    payload=client.get('/api/realtime/sports?scope=all').get_json()
    state=payload['matches'][0]['realtime_state']
    assert state['status_canonical']==canonical
    assert payload['matches'][0]['status_label']==label
    html=client.get('/match/directo-http-qa').get_data(as_text=True)
    assert f'v944-score-widget__phase">{label}</span>' in html
    if isinstance(minute,str):
        assert f'<small>{minute}</small>' in html


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
        browser = pw.chromium.launch(executable_path=os.environ.get('NEMESIS_QA_CHROMIUM'))
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
                    empty_panel = page.locator('.ns16-live-empty')
                    assert empty_panel.is_visible()
                    assert empty_panel.evaluate('(el) => getComputedStyle(el).minHeight') == '0px'
                    empty_height = empty_panel.bounding_box()['height']
                    assert empty_height <= (145 if width > 760 else 190)
                    assert empty_panel.get_by_role('link', name='Abrir calendario').is_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
                page.screenshot(path=str(tmp_path/f'directo-{mode}-{width}.png'), full_page=True)
            assert page_errors == []
            assert external == []
        finally:
            browser.close()


@pytest.mark.parametrize('width,height', [(1366,768), (390,844), (430,932)])
def test_open_actual_live_route_updates_without_reload(live_store, app_module, monkeypatch, width, height):
    """Real Flask-rendered page + actual JS, with local HTTP intercepted in CI.

    The browser clock advances; only SIMULATED_QA observations are changed.
    No provider, cron, commercial send or real database is contacted.
    """
    from playwright.sync_api import sync_playwright, expect
    import mimetypes
    client, put, now, attempts = live_store
    def put_live(**changes):
        return put(fixture_id='777', source='api_football_live_tracker', **changes)

    put_live()
    stats_state = {'available': False, 'home': '5', 'timestamp': (now - timedelta(minutes=11)).isoformat(),
        'label': 'Tiros a puerta', 'activity_available': True}

    def read_cached_stats(_db, matches, limit=40):
        if not stats_state['available'] or not matches:
            return {}
        capture = stats_state['timestamp']
        tracker = {
            'provider': 'api_football', 'fixture_id': '777', 'available': True,
            'read_only': True, 'external_calls': 0,
            'statistics_updated_at': capture,
            'stat_cards': [
                {'key': 'shots_on_goal', 'label': stats_state['label'], 'home': stats_state['home'], 'away': '2',
                 'home_captured_at': capture, 'away_captured_at': capture},
                {'key': 'fouls', 'label': 'Faltas', 'home': '8', 'away': '14',
                 'home_captured_at': capture, 'away_captured_at': capture},
                {'key': 'total_shots', 'label': 'Tiros totales', 'home': '12', 'away': '7',
                 'home_captured_at': capture, 'away_captured_at': capture},
                {'key': 'possession', 'label': 'Posesión', 'home': '61%', 'away': '39%',
                 'home_captured_at': capture, 'away_captured_at': capture},
            ],
            'field_state': {'possession_available': True, 'home_possession_pct': 61, 'away_possession_pct': 39,
                'activity_index_available': stats_state['activity_available'],
                'home_activity_index_pct': 64 if stats_state['activity_available'] else None,
                'away_activity_index_pct': 36 if stats_state['activity_available'] else None},
        }
        return {'777': tracker}

    monkeypatch.setattr(app_module, 'live_tracker_summaries_for_matches', read_cached_stats)
    root = Path(__file__).resolve().parents[1]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get('NEMESIS_QA_CHROMIUM'))
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
            calendar_action = page.locator(
                '.ns16-live-overview > .v933-page-header > .v933-page-actions a[href="/calendario"]'
            )
            expect(calendar_action).to_have_count(1)
            expect(calendar_action).to_be_visible()
            expect(calendar_action).to_contain_text('Calendario')
            link=card.locator('a[href^="/match/"]').first;link.focus()
            page.evaluate('window.originalCard=document.querySelector("[data-realtime-consumer]")')
            stats_state['available'] = True
            put_live(home_score=2, minute=70)
            page.clock.run_for(45000)
            expect(card.locator('[data-v934-score]')).to_have_text('2 - 0')
            expect(card.locator('[data-v934-minute]')).to_have_text('Min 70')
            expect(card.locator('[data-live-statistics]')).to_have_count(1)
            expect(card.locator('[data-stat-key="shots_on_goal"] [data-stat-values]')).to_have_text('5–2')
            expect(card.locator('[data-possession-home-value]')).to_have_text('61%')
            expect(card.locator('[data-stat-home-capture].is-delayed [data-stat-age]').first).to_have_text('Datos retrasados')
            expect(card.locator('[data-live-stat-activity]')).to_be_visible()
            expect(card.locator('[data-live-stat-activity] [data-activity-home-value]')).to_have_text('64%')
            expect(card.locator('[data-live-statistics-more] [role="columnheader"]').nth(0)).to_have_text('Local QA')
            expect(card.locator('[data-live-statistics-more] [role="columnheader"]').nth(2)).to_have_text('Visitante QA')
            assert 'Local QA' in card.locator('[data-live-stat-possession] .v944-possession__pitch').get_attribute('aria-label')
            first_capture = card.locator('[data-stat-key="shots_on_goal"] [data-stat-home-time]')
            assert first_capture.get_attribute('datetime') == stats_state['timestamp']
            assert link.evaluate('(node)=>node===document.activeElement')
            assert page.evaluate('originalCard===document.querySelector("[data-realtime-consumer]")')
            assert page.url.endswith('/live?f=live&q=Local')
            stats_state['home'] = '6'
            stats_state['timestamp'] = (now - timedelta(seconds=30)).isoformat()
            put_live(home_score=2, minute=71)
            page.clock.run_for(45000)
            expect(card.locator('[data-stat-key="shots_on_goal"] [data-stat-values]')).to_have_text('6–2')
            assert card.locator('[data-stat-key="shots_on_goal"] [data-stat-home-time]').get_attribute('datetime') == stats_state['timestamp']
            expect(card.locator('[data-stat-home-capture].is-delayed')).to_have_count(0)
            expect(card.locator('[data-stat-home-capture] [data-stat-age]').first).to_be_hidden()
            stats_state['activity_available'] = False
            put_live(home_score=2, minute=72)
            page.clock.run_for(45000)
            expect(card.locator('[data-live-stat-activity]')).to_be_hidden()
            stats_state['activity_available'] = True
            put_live(home_score=2, minute=73)
            page.clock.run_for(45000)
            expect(card.locator('[data-live-stat-activity]')).to_be_visible()
            expect(card.locator('[data-live-stat-activity] [data-activity-away-value]')).to_have_text('36%')
            # A same-receipt replay with altered values is ignored; hostile labels stay text.
            stats_state['home'] = '99'
            stats_state['label'] = '<img src=x onerror=window.__statXss=1>'
            put_live(home_score=2, minute=74)
            page.clock.run_for(45000)
            expect(card.locator('[data-stat-key="shots_on_goal"] [data-stat-values]')).to_have_text('6–2')
            assert page.locator('[data-stat-key="shots_on_goal"] img').count() == 0
            assert page.evaluate('window.__statXss === undefined')
            # An omitted cache projection leaves the prior value and timestamp intact.
            stats_state['available'] = False
            put_live(home_score=2, minute=75)
            page.clock.run_for(45000)
            expect(card.locator('[data-stat-key="shots_on_goal"] [data-stat-values]')).to_have_text('6–2')
            assert card.locator('[data-stat-key="shots_on_goal"] [data-stat-home-time]').get_attribute('datetime') == stats_state['timestamp']
            put_live(status='FT', home_score=2, minute=90)
            page.clock.run_for(45000)
            expect(card.locator('[data-canonical-live]')).to_have_attribute('data-canonical-live','false')
            expect(card.locator('[data-v934-status]')).to_contain_text('Finalizado')
            expect(card.locator('[data-v934-minute]')).to_be_hidden()
            assert seen.count('/live')==1
            assert seen.count('/api/realtime/sports')==7
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            assert errors==[] and external==[] and attempts==[]
        finally:
            browser.close()


@pytest.mark.parametrize('locale,width', [('es',1366), ('en',390), ('fr',430)])
def test_real_socket_live_match_return_expiry_and_final(live_store, app_module, monkeypatch, locale, width):
    """Real HTTP, templates and JS; only the read-only sports store is QA data."""
    from playwright.sync_api import sync_playwright, expect
    from werkzeug.serving import make_server
    from engines.ui_localization_engine import translate
    client, put, now, attempts = live_store
    row = put()
    # Match Center consumes the same authorized QA record, through its real handler.
    monkeypatch.setattr(app_module, 'match_detail', lambda match_id, **kwargs:
        {'match':deepcopy(row), 'related_picks':[]} if match_id == row['id'] else None)
    server = make_server('127.0.0.1', 0, app_module.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    out = Path(app_module.BASE_DIR) / 'data/local_dev/directo-operational-close'
    out.mkdir(exist_ok=True)
    report = {'environment':'SIMULATED_QA', 'transport':'REAL_FLASK_HTTP_SOCKET', 'locale':locale, 'width':width, 'states':[], 'errors':[], 'external':[]}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.environ['NEMESIS_QA_CHROMIUM'])
            context = browser.new_context(viewport={'width':width,'height':900}, locale=locale, timezone_id='America/New_York', service_workers='block')
            def network(route):
                if route.request.url.startswith(base + '/'):
                    route.continue_()
                else:
                    report['external'].append(route.request.url.split('?')[0]); route.abort()
            context.route('**/*', network)
            page = context.new_page()
            page.clock.install(time=now)
            page.on('pageerror', lambda e: report['errors'].append(str(e)))
            page.goto(base + '/live?f=live', wait_until='networkidle')
            assert page.locator('html').get_attribute('lang') == locale
            card = page.locator('[data-realtime-consumer="directo-v1"]')
            expect(card).to_have_count(1)
            expect(card.locator('[data-v934-score]')).to_have_text('1 - 0')
            report['states'].append('CONFIRMED_LIVE_1_0_MIN_67')
            page.evaluate('window.savedLiveCard=document.querySelector("[data-realtime-consumer]")')
            link=card.locator('a[href="/match/directo-http-qa"]')
            link.focus()
            for observed_status,minute,label in [('LIVE',0,'En directo'),('LIVE','45+3','En directo'),('HT',45,'Descanso'),('ET',105,'Prórroga'),('P',120,'Penaltis'),('LIVE',67,'En directo')]:
                row.update(put(status=observed_status,minute=minute,last_synced_at=datetime.now(ZoneInfo('Europe/Madrid')).isoformat()))
                page.clock.run_for(45000)
                expect(card.locator('[data-v934-status] .v933-status-chip')).to_have_text(translate(label,locale))
                expect(card.locator('[data-v934-minute]')).to_have_text(f'Min {minute}')
                assert page.evaluate('savedLiveCard===document.querySelector("[data-realtime-consumer]")')
                assert link.evaluate('node=>node===document.activeElement')
                assert page.url==base+'/live?f=live'
            report['observed_periods']='ZERO_ADDED_TIME_HT_ET_P_IN_PLACE_NO_IDENTITY_OR_FOCUS_CHANGE'
            page.screenshot(path=str(out / f'live-{locale}-{width}.png'), full_page=True)
            card.locator('a[href="/match/directo-http-qa"]').click()
            page.wait_for_url('**/match/directo-http-qa')
            expect(page.locator('[data-match-component="ScoreWidget"] strong')).to_have_text('1-0')
            assert page.locator('[data-canonical-live="true"]').count() == 1
            if locale != 'es':
                expect(page.get_by_text(translate('Partido en curso',locale),exact=True)).to_be_visible()
                assert 'Partido en curso' not in page.locator('body').inner_text()
            page.screenshot(path=str(out / f'match-{locale}-{width}.png'), full_page=True)
            page.go_back(wait_until='networkidle')
            expect(card.locator('[data-v934-score]')).to_have_text('1 - 0')
            row.update(put(home_score=2,minute=70,last_synced_at=datetime.now(ZoneInfo('Europe/Madrid')).isoformat()))
            page.clock.run_for(45000)
            expect(card.locator('[data-v934-score]')).to_have_text('2 - 0')
            expect(card.locator('[data-v934-minute]')).to_have_text('Min 70')
            expect(card.locator('[data-directo-card-notice]')).to_have_attribute('data-change-kind','SCORE_UPDATE')
            report['states'].append('OBSERVED_SCORE_UPDATE_NOT_GOAL')
            page.screenshot(path=str(out / f'updated-{locale}-{width}.png'), full_page=True)
            # Replay the same observation while only the browser clock advances.
            # No new provider evidence means that LIVE must expire.
            page.clock.run_for(360000)
            expect(card.locator('[data-canonical-live]')).to_have_attribute('data-canonical-live','false')
            expect(card.locator('[data-canonical-status]')).to_have_attribute('data-canonical-status','STALE')
            expect(card.locator('[data-v934-minute]')).to_be_hidden()
            report['states'].append('STALE_NOT_FINAL')
            page.screenshot(path=str(out / f'expired-{locale}-{width}.png'), full_page=True)
            row.update(put(status='FT',home_score=2,away_score=0,minute=90,last_synced_at=datetime.now(ZoneInfo('Europe/Madrid')).isoformat()))
            page.clock.run_for(45000)
            expect(card.locator('[data-canonical-status]')).to_have_attribute('data-canonical-status','FINISHED')
            expect(card.locator('[data-v934-score]')).to_have_text('2 - 0')
            report['states'].append('CONFIRMED_FINAL_2_0')
            page.goto(base + '/live?f=finished', wait_until='networkidle')
            expect(card).to_have_count(1)
            expect(card.locator('[data-v934-status]')).to_contain_text(translate('Finalizado',locale))
            card.locator('a[href="/match/directo-http-qa"]').click()
            page.wait_for_url('**/match/directo-http-qa')
            expect(page.locator('[data-match-component="ScoreWidget"] strong')).to_have_text('2-0')
            assert page.locator('[data-canonical-live="true"]').count() == 0
            missing = page.locator('[data-missing-context]')
            expect(missing).to_have_count(1)
            assert not missing.evaluate('e => e.open')
            missing.locator('summary').click()
            expect(missing.locator('p')).to_be_visible()
            missing.locator('summary').click()
            if locale != 'es':
                source = 'No disponible: faltan señales deportivas suficientes o frescas.'
                assert source not in page.locator('body').inner_text()
                assert translate(source,locale) in page.locator('body').inner_text()
            page.screenshot(path=str(out / f'final-match-{locale}-{width}.png'), full_page=True)
            row.update(put(minute=0,home_score=0,away_score=0,last_synced_at=datetime.now(ZoneInfo('Europe/Madrid')).isoformat()))
            page.reload(wait_until='networkidle')
            expect(page.locator('[data-match-component="ScoreWidget"] strong')).to_have_text('0-0')
            expect(page.locator('[data-match-component="ScoreWidget"] > small')).to_have_text('0')
            report['match_context'] = 'REAL_HTTP_ZERO_MINUTE_AND_COMPACT_MISSING_DATA_AND_LOCALIZED_SHARK'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            assert report['errors'] == [] and report['external'] == [] and attempts == []
            browser.close()
    finally:
        server.shutdown(); thread.join(5); server.server_close()
        (out / f'result-{locale}-{width}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
