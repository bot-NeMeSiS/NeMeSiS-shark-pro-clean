"""Founder-supplied final result; intermediate observations are replay inputs.

REAL_WORLD_REPLAY_QA, not provider/production certification. No events, scorers,
player IDs, statistics or lineups are fabricated to complete the result.
"""
from datetime import datetime
import json
import os
import re
import sqlite3
import threading

import pytest

from engines import v935_launch_trust_engine as truth
from engines.realtime_state_engine import build_realtime_match_state

MATCH_ID = 'replay-celta-racing-20260919'
CLOCKS = ['2026-09-19T18:50:00+02:00', '2026-09-19T19:06:00+02:00', '2026-09-19T20:30:00+02:00']


def observation(index):
    status, home, minute = [('LIVE', 0, 20), ('LIVE', 1, 36), ('FT', 5, None)][index]
    return dict(id=MATCH_ID, external_id=MATCH_ID, home_team='Celta de Vigo',
        away_team='Racing de Santander', competition_id='4335',
        competition_name='LaLiga EA Sports', country='Spain', round='7',
        match_date='2026-09-19', kickoff_time='18:30', kickoff_iso='2026-09-19T18:30:00+02:00',
        status=status, home_score=home, away_score=0, score=f'{home}-0', minute=minute,
        source='REAL_WORLD_REPLAY_QA', last_synced_at=CLOCKS[index],
        raw_json=json.dumps({'environment':'REAL_WORLD_REPLAY_QA',
            'final_source':'founder-supplied result; not independently certified here',
            'intermediate_source':'illustrative replay observations',
            'lifecycle_observed_at':CLOCKS[index], 'score_observed_at':CLOCKS[index],
            'minute_observed_at':CLOCKS[index], 'events_observed_at':CLOCKS[0],
            'stats_observed_at':CLOCKS[0],
            'coverage':{'events':{'state':'PARTIAL','observed':True},
                        'stats':{'state':'STALE','observed':True},
                        'lineups':{'state':'PROBABLE','observed':True}}}))


@pytest.fixture
def replay(app_module, tmp_path, monkeypatch):
    app = app_module
    path = tmp_path/'replay.sqlite'
    monkeypatch.setattr(app, 'DB_PATH', str(path))
    monkeypatch.setattr(app, '_SEEDED_DB_PATH', None)
    monkeypatch.setattr(app, '_SEEDING_DB_PATH', None)
    app.init_db()
    clock = [datetime.fromisoformat(CLOCKS[1])]
    original_now = truth.madrid_now
    monkeypatch.setattr(truth, 'madrid_now', lambda value=None: original_now(value or clock[0]))
    from engines import realtime_state_engine, v934_realtime_sports_engine
    monkeypatch.setattr(realtime_state_engine, 'madrid_now', truth.madrid_now)
    monkeypatch.setattr(v934_realtime_sports_engine, '_now', truth.madrid_now)
    monkeypatch.setattr(app, 'today_iso', lambda offset=0: '2026-09-19')
    with sqlite3.connect(path) as conn:
        conn.execute("INSERT INTO users(id,name,username,email,password_hash,role,membership,created_at) VALUES(?,?,?,?,?,?,?,?)",
                     ('replay-client','Replay QA','cliente_local','replay@example.invalid','!','FREE','FREE',CLOCKS[0]))
    def read():
        with sqlite3.connect(path) as conn:
            conn.row_factory = sqlite3.Row
            return dict(conn.execute('SELECT * FROM matches WHERE id=?', (MATCH_ID,)).fetchone())
    def put(index):
        result = app.upsert_sportsdb_matches([observation(index)])
        return result
    return app, put, read, clock


def test_final_dominates_older_live_in_the_real_store(replay):
    app, put, read, clock = replay
    put(0)
    assert str(read()['home_score']) == '0'
    put(1)
    assert str(read()['home_score']) == '1'
    put(2)
    final = read()
    for index in (0, 1):
        put(index)
        current = read()
        assert current['status'] == 'FT'
        assert current['home_score'] == final['home_score']
        assert current['minute'] in (None, '')
        assert current['raw_json'] == final['raw_json']
        state = build_realtime_match_state(current, now=datetime.fromisoformat(CLOCKS[2]))
        assert state['is_finished'] and not state['is_live']
        assert state['minute'] is None and state['score_home'] == 5


def test_final_does_not_certify_independent_fields(replay):
    _, put, read, _ = replay
    put(2)
    state = build_realtime_match_state(read(), now=datetime.fromisoformat(CLOCKS[2]))
    assert state['coverage']['events']['state'] == 'PARTIAL'
    assert state['coverage']['stats']['state'] == 'STALE'
    assert state['coverage']['lineups']['state'] == 'NOT_ESTABLISHED'
    assert state['lifecycle_observed_at'] == CLOCKS[2]
    assert state['score_observed_at'] == CLOCKS[2]
    assert state['minute_observed_at'] == CLOCKS[2]
    assert state['events_observed_at'] == state['stats_observed_at'] == CLOCKS[0]


@pytest.mark.parametrize('width', [1366, 390])
def test_real_flask_browser_final_replay_all_surfaces(replay, tmp_path, width):
    from playwright.sync_api import sync_playwright, expect
    from werkzeug.serving import make_server
    app, put, read, clock = replay
    put(1)
    server = make_server('127.0.0.1', 0, app.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    report = {'environment':'REAL_WORLD_REPLAY_QA','transport':'REAL_FLASK_HTTP',
              'width':width,'surfaces':[], 'external':[], 'errors':[], 'certification':'LOCAL_ONLY'}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.environ.get('NEMESIS_QA_CHROMIUM'))
            context = browser.new_context(viewport={'width':width,'height':900},timezone_id='Asia/Tokyo',locale='es')
            def network(route):
                if route.request.url.startswith(base+'/'): route.continue_()
                else: report['external'].append(route.request.url.split('?')[0]); route.abort()
            context.route('**/*', network)
            login = context.request.get(base+'/local-safe/login/client?token='+os.environ['NEMESIS_LOCAL_ACCESS_TOKEN'],max_redirects=0)
            assert login.status == 302
            page = context.new_page()
            page.on('pageerror',lambda error:report['errors'].append(str(error)))
            page.clock.install(time=clock[0])
            page.goto(base+'/live',wait_until='networkidle')
            card = page.locator(f'[data-v934-match-id="{MATCH_ID}"]')
            expect(card).to_have_count(1)
            expect(card.locator('[data-v934-score]')).to_have_text('1 - 0')
            expect(card.locator('[data-v934-minute]')).to_have_text('Min 36')
            page.screenshot(path=str(tmp_path/f't2-live-{width}.png'))
            page.evaluate('window.replayCard=document.querySelector("[data-v934-match-card]")')
            put(2)
            clock[0] = datetime.fromisoformat(CLOCKS[2])
            response = context.request.get(base+'/api/realtime/sports?scope=matches')
            snapshot = response.json()
            (tmp_path/'after-t3.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
            assert any(row.get('id') == MATCH_ID and row.get('home_score') == 5 for row in snapshot['matches'])
            page.clock.run_for(45000)
            expect(card.locator('[data-v934-score]')).to_have_text('5 - 0')
            expect(card).to_have_attribute('data-canonical-live','false')
            expect(card.locator('[data-v934-minute]')).to_be_hidden()
            expect(card.locator('[data-v934-status]')).to_contain_text('Finalizado')
            assert page.evaluate('replayCard===document.querySelector("[data-v934-match-card]")')
            put(1)
            page.clock.run_for(45000)
            expect(card.locator('[data-v934-score]')).to_have_text('5 - 0')
            expect(card).to_have_attribute('data-canonical-live','false')
            page.screenshot(path=str(tmp_path/f't3-final-inplace-{width}.png'))
            report['in_place_and_old_t2_rejected'] = True
            for route in ('/app','/live?f=finished','/calendar','/partidos','/match/'+MATCH_ID):
                response = page.goto(base+route,wait_until='networkidle')
                assert response.status == 200
                if route.startswith('/match/'):
                    expect(page.locator('[data-match-component="ScoreWidget"] strong')).to_have_text('5-0')
                    assert page.locator('[data-match-component="ScoreWidget"] > small:visible').count() == 0
                else:
                    target = page.locator(f'[data-v934-match-id="{MATCH_ID}"]')
                    expect(target.first).to_be_visible()
                    for item in target.all():
                        expect(item.locator('[data-v934-score]')).to_have_text('5 - 0')
                        expect(item).to_have_attribute('data-canonical-live','false')
                        expect(item).to_have_attribute('data-canonical-status',re.compile(r'^(FT|FINISHED)$'))
                        expect(item.locator('[data-v934-status]')).to_have_text(re.compile(r'^Final(?:izado)?$'))
                        expect(item.locator('[data-v934-minute]')).to_be_hidden()
                assert page.locator('[data-canonical-live="true"]').count() == 0
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
                name = route.split('?')[0].strip('/').replace('/','-')
                page.screenshot(path=str(tmp_path/f'final-{name}-{width}.png'))
                report['surfaces'].append({'route':route,'status':'FINAL','score':'5-0','minute':None,'is_live':False})
            assert report['external'] == report['errors'] == []
            browser.close()
    finally:
        server.shutdown(); thread.join(5); server.server_close()
        (tmp_path/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


@pytest.mark.parametrize('clock', [CLOCKS[1], CLOCKS[2], '', 'invalid'])
def test_final_cannot_be_rolled_back_by_older_equal_or_unknown_clock(replay, clock):
    app, put, read, _ = replay
    put(2)
    row = observation(1)
    row['last_synced_at'] = clock
    assert app.upsert_sportsdb_matches([row])['skipped'] == 1
    assert read()['status'] == 'FT' and str(read()['home_score']) == '5'


def test_newer_authoritative_final_correction_is_allowed(replay):
    app, put, read, _ = replay
    put(2)
    row = observation(2)
    row.update(last_synced_at='2026-09-19T20:31:00+02:00')
    assert app.upsert_sportsdb_matches([row])['updated'] == 1
    assert read()['last_synced_at'] == row['last_synced_at']


def test_concurrent_older_observation_cannot_win(replay):
    from concurrent.futures import ThreadPoolExecutor
    app, put, read, _ = replay
    put(0)
    barrier = threading.Barrier(2)
    def deliver(index):
        barrier.wait()
        return put(index)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(deliver, [1,2]))
    assert len(results) == 2
    assert read()['status'] == 'FT' and str(read()['home_score']) == '5'
