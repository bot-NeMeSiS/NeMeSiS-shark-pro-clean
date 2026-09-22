"""Real HTTP queue experiment, synthetic sports task, temporary DB, no provider traffic.

Gunicorn cases execute on CI with the pinned production dependency. Local Werkzeug
cases demonstrate ordering only; neither activates a production worker setting.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import http.client
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import textwrap
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]

APP_SOURCE = '''
import os, socket, time
from pathlib import Path

def denied(*a, **k):
    Path(os.environ['QA_NETWORK_ATTEMPT']).write_text('blocked', encoding='utf-8')
    raise RuntimeError('No outbound network in the synthetic probe')
socket.socket.connect = denied
socket.create_connection = denied
import app as real
real.app.config.update(TESTING=True)
real.init_db()
real.seed_core()
def slow_sports_task(force=False, **kwargs):
    Path(os.environ['QA_ENTERED']).write_text('entered', encoding='utf-8')
    deadline = time.monotonic() + 12
    while not Path(os.environ['QA_RELEASE']).exists():
        if time.monotonic() > deadline:
            raise RuntimeError('synthetic task release timed out')
        time.sleep(.01)
    return {'ok': True, 'status': 'SIMULATED_QA', 'external_calls': 0, 'processed': 0}
real.run_sports_sync_cycle = slow_sports_task
application = real.app
if __name__ == '__main__':
    from werkzeug.serving import make_server
    make_server('127.0.0.1', int(os.environ['QA_PORT']), application,
                threaded=os.environ['QA_THREADED'] == '1').serve_forever()
'''


def _get(port, path, *, token=None):
    # Fixed loopback host. Never accepts a production host or URL.
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
    try:
        headers = {'X-Automation-Secret': token} if token else {}
        start = time.perf_counter()
        conn.request('GET', path, headers=headers)
        response = conn.getresponse()
        body = response.read()
        return {'status': response.status, 'ms': round((time.perf_counter()-start)*1000,2), 'bytes':len(body)}
    finally:
        conn.close()


@pytest.mark.parametrize('backend', ['werkzeug', 'gunicorn'])
@pytest.mark.parametrize('threaded', [False, True], ids=['serial', 'concurrent'])
def test_ordinary_navigation_order_during_synthetic_sports_task(tmp_path, backend, threaded):
    if backend == 'gunicorn' and importlib.util.find_spec('gunicorn') is None:
        if os.getenv('CI'):
            pytest.fail('CI must provide the pinned production Gunicorn dependency')
        pytest.skip('Gunicorn unavailable locally; this experiment must also pass unchanged in CI')
    script = tmp_path / 'queue_probe_app.py'
    script.write_text(textwrap.dedent(APP_SOURCE), encoding='utf-8')
    entered, release, network = (tmp_path / name for name in ('entered','release','network-attempt'))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    token = secrets.token_urlsafe(32)
    env = {key:value for key,value in os.environ.items() if key in {'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','SYSTEMROOT'}}
    env.update(PYTHONPATH=os.pathsep.join([str(tmp_path),str(ROOT)]+[str(p) for p in sys.path if p]),
               DB_PATH=str(tmp_path/'probe.sqlite'), SECRET_KEY=secrets.token_urlsafe(32),
               ADMIN_PASSWORD=secrets.token_urlsafe(32), ADMIN_EMAIL='qa@example.test', AUTOMATION_SECRET=token,
               BACKGROUND_JOBS_ENABLED='false', AUTO_GENERATE_PICKS='false', AUTO_SEND_TELEGRAM_PICKS='false',
               ENABLE_TELEGRAM_AUTO='false', QA_PORT=str(port), QA_THREADED='1' if threaded else '0',
               QA_ENTERED=str(entered), QA_RELEASE=str(release), QA_NETWORK_ATTEMPT=str(network))
    cmd = ([sys.executable, '-m', 'gunicorn', '--workers=1', '--worker-class='+('gthread' if threaded else 'sync'),
            '--threads='+('2' if threaded else '1'), '--timeout=20', '--bind=127.0.0.1:'+str(port),
            '--config=python:queue_probe_settings', 'queue_probe_app:application']
           if backend=='gunicorn' else [sys.executable,str(script)])
    # Explicit empty config avoids accidentally using an unrelated project/server config.
    (tmp_path/'queue_probe_settings.py').write_text('# Synthetic test configuration only\n', encoding='utf-8')
    log_path = tmp_path/'server.log'
    with log_path.open('w', encoding='utf-8') as log:
        process = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+18
            while True:
                if process.poll() is not None:
                    pytest.fail('Isolated server failed: '+log_path.read_text(errors='replace')[-1800:])
                try:
                    if _get(port,'/api/health')['status']==200: break
                except (OSError,http.client.HTTPException):
                    pass
                if time.monotonic()>deadline: pytest.fail('Isolated server startup timed out')
                time.sleep(.05)
            assert _get(port,'/live')['status']==200
            assert _get(port,'/api/automation/sports/sync')['status']==403
            assert not entered.exists()
            with ThreadPoolExecutor(max_workers=2) as pool:
                slow=pool.submit(_get,port,'/api/automation/sports/sync',token=token)
                try:
                    deadline=time.monotonic()+5
                    while not entered.exists():
                        if slow.done(): pytest.fail('Protected task did not enter: '+str(slow.result()))
                        if time.monotonic()>deadline: pytest.fail('Protected task did not start')
                        time.sleep(.01)
                    navigation=pool.submit(_get,port,'/live')
                    if threaded:
                        result=navigation.result(timeout=5)
                        assert result['status']==200 and not slow.done()
                        advanced_before_release=True
                    else:
                        with pytest.raises(FutureTimeout): navigation.result(timeout=.35)
                        assert not slow.done()
                        advanced_before_release=False
                finally:
                    release.touch()
                task=slow.result(timeout=10); result=navigation.result(timeout=10)
                assert task['status']==200 and result['status']==200
            assert not network.exists()
            receipt={'scope':'SIMULATED_QA_HTTP_LOOPBACK','backend':backend,'worker_mode':('gthread-2' if threaded else 'sync-1') if backend=='gunicorn' else ('thread-per-request' if threaded else 'serial'),
                     'navigation_completed_before_task_release':advanced_before_release,'navigation':result,
                     'task':task,'external_calls':0,'production_config_changed':False}
            (tmp_path/'queue-evidence.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
            print('QUEUE_EVIDENCE '+json.dumps(receipt,sort_keys=True))
        finally:
            release.touch()
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=5)
