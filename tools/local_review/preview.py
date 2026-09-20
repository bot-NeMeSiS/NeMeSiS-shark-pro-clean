"""Local-only desktop launcher; no installs, services, secrets or remote calls."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import webbrowser

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'data/local_dev'
METADATA = LOCAL / 'sentinel-preview.json'
STOP = LOCAL / 'preview-stop.json'
PROTOCOL = 'nemesis-local-preview-v1'


@contextmanager
def local_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def read_metadata():
    try:
        value = json.loads(METADATA.read_text(encoding='utf-8'))
        if (value.get('protocol') == PROTOCOL and value.get('root') == str(ROOT)
                and type(value.get('port')) is int and 1024 <= value['port'] <= 65535
                and value.get('instance_id')):
            return value
    except (OSError, ValueError, TypeError):
        pass
    return None


def stop_requested(instance_id, path=STOP):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        return isinstance(value, dict) and value.get('instance_id') == instance_id
    except (OSError, ValueError):
        return False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def is_running(meta):
    if not meta:
        return False
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(f"http://127.0.0.1:{meta['port']}/local-safe/preview-identity", timeout=1) as response:
            actual = json.loads(response.read(4096))
        return actual.get('instance_id') == meta['instance_id'] and actual.get('protocol') == PROTOCOL
    except (OSError, ValueError):
        return False


def select_port(preferred=54910):
    for port in range(preferred, min(preferred + 20, 65536)):
        with socket.socket() as probe:
            if os.name == 'nt':
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                probe.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError('No hay puerto local libre; no se ha detenido ninguna otra aplicacion.')


def safe_environment():
    # Only OS essentials are inherited; API keys, DB URLs and .env never enter the child.
    allowed = {'SYSTEMROOT','WINDIR','PATH','COMSPEC','TEMP','TMP','USERPROFILE',
               'APPDATA','LOCALAPPDATA','HOMEDRIVE','HOMEPATH','PATHEXT','SYSTEMDRIVE',
               'PROGRAMFILES','PROGRAMFILES(X86)','PROCESSOR_ARCHITECTURE','NUMBER_OF_PROCESSORS'}
    env = {k:v for k,v in os.environ.items() if k.upper() in allowed}
    deps = Path.home() / '.codex/visualizations/2026/05/27/019e69a5-0d06-7af3-98c9-b9e23032ef02/design02-20260913/qa-deps'
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1',
               PYTHONPATH=os.pathsep.join([str(ROOT)] + ([str(deps)] if deps.is_dir() else [])),
               NEMESIS_LOCAL_EXTERNAL_AUTHORIZED='0')
    return env


def show(meta, open_browser):
    base = f"http://127.0.0.1:{meta['port']}"
    print('NeMeSiS PREVIEW LOCAL. No es Render ni produccion.')
    print('CLIENTE: ' + base + '/app')
    print('SENTINEL: ' + base + '/admin/sentinel-issues (Panel local > Admin)')
    print('RECOMENDACIONES: ' + base + '/recommendations')
    print('Para parar: doble clic en stop_nemesis_preview.bat')
    if open_browser:
        # Construct the fixed local entry; never open arbitrary metadata URLs.
        token = urllib.parse.urlsplit(meta['url']).query
        webbrowser.open(base + '/local-safe/login/client?' + token)


def start(open_browser=True):
    LOCAL.mkdir(parents=True, exist_ok=True)
    with local_lock(LOCAL/'preview-start.lock'):
        meta = read_metadata()
        if is_running(meta):
            print('La preview ya esta encendida; se reutiliza la misma instancia.')
            show(meta, open_browser)
            return
        # The server owns a separate lifetime lock, including its startup window.
        try:
            with local_lock(LOCAL/'preview-server.lock'):
                pass
        except OSError as exc:
            raise RuntimeError('La preview esta arrancando o deteniendose. Espera unos segundos y vuelve a abrirla.') from exc
        env = safe_environment()
        check = subprocess.run([sys.executable,'-B','-c','import flask, werkzeug'],
                               env=env, cwd=ROOT, capture_output=True, timeout=15)
        if check.returncode:
            raise RuntimeError('El Python seleccionado no tiene las dependencias preparadas. No se ha instalado nada.')
        port = select_port()
        if port != 54910:
            print(f'El puerto 54910 esta ocupado. Se usara {port}; no se detiene otra aplicacion.')
        command = [sys.executable,'-B',str(ROOT/'tools/local_desktop/run_sentinel_local.py'),'--port',str(port)]
        options = {'creationflags':subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session':True}
        log_path = LOCAL/'preview-launch.log'
        with log_path.open('ab') as log:
            process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=log, **options)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            meta = read_metadata()
            if is_running(meta):
                show(meta, open_browser)
                return
            if process.poll() is not None:
                break
            time.sleep(.25)
        raise RuntimeError('No se pudo confirmar el arranque. Consulta ' + str(log_path) + '. No se inicia otra copia automaticamente.')


def stop():
    meta = read_metadata()
    if not is_running(meta):
        print('No hay una preview gestionada accesible. No se ha detenido otro proceso.')
        return
    temporary = STOP.with_suffix('.pending')
    temporary.write_text(json.dumps({'instance_id':meta['instance_id']}), encoding='utf-8')
    temporary.replace(STOP)
    print('Parada solicitada. Se espera al trabajo local en curso; no se fuerza su cierre.')
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if not is_running(meta):
            print('Preview detenida. El candidato y la evidencia local se conservan.')
            return
        time.sleep(.25)
    raise RuntimeError('La instancia aun no confirma la parada. No se ha forzado ni cancelado el trabajo.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start','stop'))
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    try:
        start(not args.no_browser) if args.action == 'start' else stop()
        return 0
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print('NeMeSiS local: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
