"""Real local HTTP and app JS; synthetic session results, no provider access.

Covers the new manual-result page, not production playback or account access.
"""
import argparse
import json
import logging
import os
from pathlib import Path
import secrets
import socket
import sys
import tempfile
import threading
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', default='reports/postmatch_delivery_browser')
args = parser.parse_args()
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
output = Path(args.output).resolve()
output.mkdir(parents=True, exist_ok=True)
original_connect = socket.socket.connect
network_attempts = []
def guard(self, address):
    if isinstance(address, tuple) and address[0] not in {'127.0.0.1','localhost','::1'}:
        network_attempts.append(True)
        raise AssertionError('Provider transport forbidden in isolated browser QA')
    return original_connect(self, address)
socket.socket.connect = guard
with tempfile.TemporaryDirectory(prefix='nemesis-delivery-browser-') as tmp:
    os.environ.update(DB_PATH=str(Path(tmp)/'app.sqlite'), SECRET_KEY=secrets.token_hex(32),
        AUTOMATION_SECRET=secrets.token_hex(32), BACKGROUND_JOBS_ENABLED='false',
        AUTO_SEND_TELEGRAM_PICKS='false', AUTO_GENERATE_PICKS='false',
        SCHEDULER_ENABLED='0', ENABLE_AUTO_SYNC='0', AUTO_SYNC_ON_STARTUP='0')
    for key in ('THE_ODDS_API_KEY','ODDS_API_KEY','THESPORTSDB_KEY','THESPORTSDB_API_KEY',
                'API_FOOTBALL_KEY','API_FOOTBALL_API_KEY','OPENAI_API_KEY','TELEGRAM_BOT_TOKEN','STRIPE_SECRET_KEY'):
        os.environ.pop(key, None)
    import app
    import blueprints.postmatch_recovery as recovery_routes
    app.app.config.update(TESTING=True)
    app.init_db()
    executions = []
    def forbidden_tick(*a, **kw):
        executions.append(True)
        raise AssertionError('Result GET must not run a worker')
    recovery_routes.tick = forbidden_tick
    from tools.run_v929_click_navigation_qa import _signed_sessions
    sessions = _signed_sessions(app.app)
    signer = app.app.session_interface.get_signing_serializer(app.app)
    from werkzeug.serving import make_server
    from playwright.sync_api import sync_playwright
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    server = make_server('127.0.0.1', 0, app.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    records = []
    samples = {
        'partial': {'ok':True,'result':'PARTIAL','processed':2,'external_calls':3,'jobs':[
            {'job_id':1,'kind':'highlights','state':'REVIEW_REQUIRED','reason':'RIGHTS_REVIEW',
             'diagnostics':{'sportsdb_event_id':'101','video_lookup':'LEAGUE_DAY_LINK','highlight_rows':1}},
            {'job_id':2,'kind':'statistics','state':'RETRY','reason':'NO_STATISTICS','due_at':1790966400,
             'diagnostics':{'statistics_received':0,'statistics_recognized':0,'statistics_accepted':0,
                            'key_mode':'CONFIGURED_KEY_NOT_PLAN_VERIFIED'}}]},
        'failure': {'ok':False,'result':'STORAGE_UNAVAILABLE','processed':0,'external_calls':0,'jobs':[]},
        'empty': None,
    }
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.getenv('NEMESIS_QA_CHROMIUM') or pw.chromium.executable_path,
                                         headless=True, args=['--no-sandbox'])
            for name, sample in samples.items():
                for width in (320,390,1440):
                    session = signer.loads(sessions['admin'])
                    if sample is not None:
                        session['postmatch_last_result'] = sample
                    context = browser.new_context(viewport={'width':width,'height':900},
                        service_workers='block',locale='es-ES')
                    context.add_cookies([{'name':sessions['cookie_name'],'value':signer.dumps(session),'url':base}])
                    def route_request(route):
                        if urlsplit(route.request.url).netloc != urlsplit(base).netloc or route.request.method != 'GET':
                            route.abort()
                        else:
                            route.continue_()
                    context.route('**/*', route_request)
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda e:errors.append(str(e)[:250]))
                    response = page.goto(base+'/admin/highlights-review/workers/result',wait_until='load')
                    assert response.status == (503 if name=='failure' else 200)
                    page.wait_for_timeout(500)
                    assert page.locator('[data-postmatch-run-result]').count()==1
                    if name=='partial':
                        assert page.locator('[data-postmatch-result-job]').count()==2
                        assert page.get_by_text('Lote procesado con pendientes',exact=True).is_visible()
                        page.locator('[data-postmatch-result-job] summary').first.click()
                    else:
                        assert page.locator('[data-postmatch-result-job]').count()==0
                    assert page.get_by_role('link',name='Volver a trabajadores pospartido',exact=True).is_visible()
                    overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 2')
                    assert not overflow and not errors, (name,width,errors)
                    page.screenshot(path=str(output/f'{name}-{width}.png'),full_page=True)
                    page.reload(wait_until='load')
                    assert not executions
                    records.append({'case':name,'width':width,'status':response.status,
                        'overflow':overflow,'page_errors':errors,'refresh_worker_calls':len(executions)})
                    context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    assert len(records)==9 and not network_attempts and not executions
    (output/'checks.json').write_text(json.dumps({'mode':'full_http','checks':records,
        'data':'synthetic isolated result sessions','real_provider_calls':0,
        'production_verified':False},ensure_ascii=False,indent=2))
    print('DELIVERY_BROWSER_OK',len(records))
