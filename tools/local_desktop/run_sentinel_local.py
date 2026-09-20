"""Supervised LOCAL SAFE Sentinel preview; no production scheduler is installed."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True


def prepare(port=54910, db_name="sentinel_preview.sqlite", allow_browser=False):
    from tools.local_desktop.run_local_desktop import configure_local_environment, seed_local_database
    os.environ['NEMESIS_LOCAL_EXTERNAL_AUTHORIZED'] = '0'
    configure_local_environment("OFFLINE_SAFE", port, db_name)
    for key in ("BACKGROUND_JOBS_ENABLED", "AUTO_GENERATE_PICKS", "AUTO_SEND_TELEGRAM_PICKS"):
        os.environ[key] = "false"
    os.environ["ADMIN_EMAIL"] = "sentinel@example.invalid"
    os.environ["ADMIN_PASSWORD"] = secrets.token_urlsafe(32)
    local = ROOT / "data/local_dev"
    from tools.run_v944_match_center_browser_qa import install_boundary
    from automation_workforce.common import python_executable
    # The existing boundary permits exactly this supervised, fixed, static worker.
    command = [python_executable(), "-B", str(ROOT / "automation_workforce/product_experience_worker.py"), "--static-only", "--no-write", "--dry-run"]
    audit_command = list(subprocess.list2cmdline(command)) if os.name == "nt" else command
    browser_commands = []
    if allow_browser:
        from playwright._impl._driver import compute_driver_executable
        node, cli = compute_driver_executable()
        driver = [str(node), str(cli), "run-driver"]
        browser_commands.append(list(subprocess.list2cmdline(driver)) if os.name == "nt" else driver)
    # Audit hooks cannot be removed from a running Python process. The standalone
    # LOCAL SAFE supervisor installs the boundary, while pytest validates the same
    # boundary in isolation and must not leak it into unrelated tests.
    blocked = [] if "pytest" in sys.modules else install_boundary(
        local, local, Path(os.environ["DB_PATH"]), audit_command, browser_commands
    )
    import app as module
    module.app.config["SENTINEL_JOBS_ENABLED"] = True
    seed_local_database(module)
    from engines.sentinel_jobs import Store
    job_path = local / ("sentinel_jobs.sqlite" if db_name == "sentinel_preview.sqlite" else Path(db_name).stem + ".jobs.sqlite")
    module.app.config["SENTINEL_JOBS_PATH"] = str(job_path)
    store = Store(job_path)
    store.initialize()
    store.recover_and_heartbeat()
    return module, store, blocked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=54910)
    args = parser.parse_args()
    from tools.local_review.preview import local_lock, LOCAL
    with local_lock(LOCAL/'preview-server.lock'):
        serve(args.port)


def serve(port):
    from werkzeug.serving import make_server
    from engines.sentinel_jobs import run_one
    from tools.local_review.preview import PROTOCOL, METADATA, stop_requested
    module, store, blocked = prepare(port)
    instance_id = secrets.token_hex(24)

    @module.app.get('/local-safe/preview-identity')
    def preview_identity():
        if not module.local_safe_loopback_request() or not module.local_safe_mode_enabled():
            module.abort(404)
        return {'protocol':PROTOCOL, 'instance_id':instance_id}

    @module.app.get('/local-safe/open-sentinel')
    def open_sentinel():
        # Reuse the local QA login checks; never expose this entry in production.
        if not module.local_safe_loopback_request() or not module.local_safe_mode_enabled():
            module.abort(404)
        response = module.local_safe_quick_login('admin')
        if response.status_code == 302 and response.headers.get('Location') == '/admin/control-center':
            return module.redirect('/admin/sentinel-issues')
        return response

    server = make_server("127.0.0.1", port, module.app, threaded=True)
    web = threading.Thread(target=server.serve_forever, name="sentinel-local-http", daemon=True)
    web.start()
    access_url = f"http://127.0.0.1:{port}/local-safe/login/admin?token={os.environ['NEMESIS_LOCAL_ACCESS_TOKEN']}"
    METADATA.write_text(json.dumps({'protocol':PROTOCOL, 'root':str(ROOT), 'instance_id':instance_id,
        "pid":os.getpid(), "url":access_url, "port":port, "environment":"LOCAL_ONLY"}), encoding="utf-8")
    print(f"LOCAL_ONLY Sentinel HTTP ready on 127.0.0.1:{port}", flush=True)
    try:
        while web.is_alive():
            if stop_requested(instance_id):
                break
            run_one(store, ROOT)
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        web.join(timeout=5)
        print(json.dumps({"boundary_events":blocked}), flush=True)


if __name__ == "__main__":
    main()
