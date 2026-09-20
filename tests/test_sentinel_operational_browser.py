"""Real Flask/SQLite/Chromium closure, with explicit negative fault injection."""
import json
import os
from pathlib import Path
import threading
import uuid

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def test_operational_lifecycle_and_http_guards(monkeypatch):
    from tools.local_desktop.run_sentinel_local import prepare
    from engines.sentinel_jobs import Store, revision, run_one
    import automation_workforce.common as common

    module, store, blocked = prepare(db_name="sentinel_close_" + uuid.uuid4().hex + ".sqlite", allow_browser=True)
    root = Path(module.BASE_DIR)
    output = root / "data/local_dev/sentinel-operational-close"
    output.mkdir(exist_ok=True)
    owner = "qa-owner-" + uuid.uuid4().hex
    token = uuid.uuid4().hex
    payload = {"action": "product_surface_review", "parameters": {"scope": "client_templates"}, "request_key": uuid.uuid4().hex}
    # A prior, invalidated source revision is a real terminal job, not a fake result.
    old, _ = store.submit(owner, payload, "earlier-qa-source")
    run_one(store, root)
    assert store.get(owner, old["id"])["state"] == "FAILED"
    server = make_server("127.0.0.1", 0, module.app, threaded=True)
    web = threading.Thread(target=server.serve_forever, daemon=True)
    web.start()
    base = f"http://127.0.0.1:{server.server_port}"
    report = {"environment": "LOCAL_ONLY", "transport": "REAL_FLASK_HTTP", "database": str(store.path.relative_to(root)), "checks": {}, "errors": []}
    release = threading.Event()
    running = threading.Event()
    worker_errors = []
    worker = None

    def context(browser, role, identity):
        ctx = browser.new_context(viewport={"width": 1366, "height": 900}, timezone_id="Asia/Tokyo", service_workers="block")
        ctx.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base + "/") else route.abort())
        if role:
            value = module.app.session_interface.get_signing_serializer(module.app).dumps({"user_role": role, "user_id": identity, "csrf_token": token})
            ctx.add_cookies([{"name": module.app.config.get("SESSION_COOKIE_NAME", "session"), "value": value, "url": base, "httpOnly": True, "sameSite": "Lax"}])
        return ctx

    def submit(ctx, body=None, csrf=token):
        return ctx.request.post(base + "/api/admin/sentinel/jobs", data=body or dict(payload, request_key=uuid.uuid4().hex), headers={"X-CSRF-Token": csrf})

    def execute():
        try:
            run_one(store, root)
        except Exception as exc:
            worker_errors.append(type(exc).__name__)

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=os.environ["NEMESIS_QA_CHROMIUM"])
            admin = context(browser, "ADMIN", owner)
            page = admin.new_page()
            page.on("pageerror", lambda exc: report["errors"].append(str(exc)))
            before = len(store.list(owner))
            page.goto(base + "/admin/sentinel-issues", wait_until="domcontentloaded")
            page.wait_for_function("!document.querySelector('[data-request-review]').disabled")
            assert len(store.list(owner)) == before
            report["checks"]["get_does_not_submit"] = True
            # Two physical clicks before the supervisor runs; UI and server both deduplicate.
            button = page.locator("[data-request-review]")
            box = button.bounding_box()
            with page.expect_response(lambda r: r.url.endswith('/api/admin/sentinel/jobs') and r.request.method == 'POST') as accepted:
                page.mouse.dblclick(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2, delay=30)
            job_id = accepted.value.json()["job"]["id"]
            report["job_id"] = job_id
            assert store.get(owner, job_id)["state"] == "QUEUED"
            simultaneous = page.evaluate("""async ({token}) => Promise.all(Array.from({length:8}, () => fetch('/api/admin/sentinel/jobs', {
                method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':token},
                body:JSON.stringify({action:'product_surface_review',parameters:{scope:'client_templates'},request_key:crypto.randomUUID()})
            }).then(async r => ({status:r.status, data:await r.json()}))))""", {"token": token})
            assert all(item['status'] == 200 and item['data']['job']['id'] == job_id for item in simultaneous)
            assert len(store.list(owner)) == before + 1
            report["checks"]["double_click_and_8_concurrent_requests_one_job"] = True
            original_claim = store.claim

            def observed_claim():
                claimed = original_claim()
                if claimed:
                    running.set()
                    if not release.wait(15):
                        raise RuntimeError("QA observation barrier expired")
                return claimed

            monkeypatch.setattr(store, "claim", observed_claim)
            worker = threading.Thread(target=execute, daemon=True)
            worker.start()
            assert running.wait(5)
            assert Store(store.path).claim() is None
            page.wait_for_function("document.querySelector('[data-job-detail]').textContent.includes('En ejecución')")
            assert store.get(owner, job_id)["state"] == "RUNNING"
            report["states"] = ["QUEUED", "RUNNING"]
            page.locator('[data-sentinel-jobs]').screenshot(path=str(output / 'running.png'))
            release.set()
            worker.join(15)
            assert not worker.is_alive() and not worker_errors
            monkeypatch.setattr(store, "claim", original_claim)
            page.wait_for_function("document.querySelector('[data-job-detail]').textContent.includes('Revisión terminada')")
            result = store.get(owner, job_id)
            assert result["state"] == "COMPLETED" and result["attempt"] == 1
            assert result["result"]["database_status"] == "NOT_ACCESSED"
            assert len(result["result"]["scope"]) == 8
            report["states"].append("COMPLETED")
            report["revision"] = result["revision"]
            assert len(page.locator('[data-job-lifecycle] li').all()) == 3
            page.reload(wait_until="domcontentloaded")
            page.wait_for_function("id => document.querySelector('[data-job-detail]').textContent.includes(id)", arg=job_id)
            second = admin.new_page()
            second.goto(page.url, wait_until="domcontentloaded")
            second.wait_for_function("id => document.querySelector('[data-job-detail]').textContent.includes(id)", arg=job_id)
            assert store.get(owner, job_id) == result
            report["checks"]["reload_and_second_tab_same_result"] = True
            page.locator(f'[data-job-id="{old["id"]}"]').click()
            page.wait_for_function("id => document.querySelector('[data-job-detail]').textContent.includes(id)", arg=old["id"])
            page.reload(wait_until="domcontentloaded")
            page.wait_for_function("id => document.querySelector('[data-job-detail]').textContent.includes(id)", arg=old["id"])
            assert 'Revisión fallida' in page.locator('[data-job-detail]').inner_text()
            report["checks"]["selected_historical_job_survives_reload"] = True
            page.goto(base + '/admin/sentinel-issues?job=' + ('f' * 32), wait_until='domcontentloaded')
            page.wait_for_function("document.querySelector('[data-job-detail]').textContent.includes('no disponible para esta sesión')")
            assert job_id not in page.locator('[data-job-detail]').inner_text()
            report["checks"]["unavailable_selection_never_substituted"] = True
            for role in (None, 'FREE', 'PRO', 'ELITE'):
                denied = context(browser, role, 'qa-client')
                assert denied.request.get(base + '/api/admin/sentinel/jobs').status == 403
                assert denied.request.get(base + '/api/admin/sentinel/jobs/' + job_id).status == 403
                assert submit(denied).status == 403
                denied.close()
            other = context(browser, 'ADMIN', 'qa-other-' + uuid.uuid4().hex)
            assert other.request.get(base + '/api/admin/sentinel/jobs/' + job_id).status == 404
            assert submit(admin, csrf='invalid').status == 403
            assert submit(admin, dict(payload, action='shell')).status == 400
            assert submit(admin, dict(payload, parameters={'scope': '../private'})).status == 400
            assert submit(admin, dict(payload, url='https://example.invalid')).status == 400
            assert store.get(owner, job_id) == result
            report['checks']['auth_csrf_foreign_id_closed_parameters'] = True
            # The fixed child really runs; only its result handoff fails intentionally.
            original_command = common.run_command
            child_ran = []

            def fail_after_child(*args, **kwargs):
                actual = original_command(*args, **kwargs)
                child_ran.append(actual.get('ok'))
                raise RuntimeError('QA_SENSITIVE_CANARY_DO_NOT_PERSIST')

            failed_id = submit(other).json()['job']['id']
            monkeypatch.setattr(common, 'run_command', fail_after_child)
            run_one(store, root)
            monkeypatch.setattr(common, 'run_command', original_command)
            failed = other.request.get(base + '/api/admin/sentinel/jobs/' + failed_id).json()['job']
            assert child_ran == [True]
            assert failed['state'] == 'FAILED' and failed['result'] is None
            assert failed['error'] == 'executor_result_unavailable'
            assert 'CANARY' not in json.dumps(failed)
            assert not run_one(store, root)
            failed_page = other.new_page()
            failed_page.goto(base + '/admin/sentinel-issues?job=' + failed_id, wait_until='domcontentloaded')
            failed_page.wait_for_function("document.querySelector('[data-job-detail]').textContent.includes('No se pudo verificar la evidencia')")
            assert 'CANARY' not in failed_page.locator('body').inner_text()
            failed_page.locator('[data-sentinel-jobs]').screenshot(path=str(output / 'failed.png'))
            report['checks']['real_child_negative_handoff_failed_sanitized_no_retry'] = True
            report['failure_injection'] = 'QA_ONLY_RESULT_HANDOFF_AFTER_REAL_WORKER'
            report['failed_job_id'] = failed_id
            page.goto(base + '/admin/sentinel-issues?job=' + job_id, wait_until='domcontentloaded')
            page.wait_for_function("document.querySelector('[data-job-detail]').textContent.includes('Revisión terminada')")
            search = page.locator('[data-v892-search]')
            search.fill('conservar foco')
            page.wait_for_timeout(3300)
            assert search.input_value() == 'conservar foco'
            assert search.evaluate('e => document.activeElement === e')
            search.fill('')
            for width in (1366, 390, 430):
                page.set_viewport_size({'width': width, 'height': 900 if width == 1366 else 932})
                page.locator('[data-sentinel-jobs]').scroll_into_view_if_needed()
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                assert not page.locator('[data-sentinel-jobs]').evaluate('e => e.scrollWidth > e.clientWidth + 1')
                page.screenshot(path=str(output / f'sentinel-{width}.png'))
            report['checks']['focus_and_1366_390_430'] = True
            assert not report['errors'] and blocked == []
            assert Store(store.path).get(owner, job_id) == result
            report['checks']['reopened_registry_preserves_result'] = True
            browser.close()
    finally:
        release.set()
        if worker:
            worker.join(15)
        server.shutdown()
        web.join(5)
        server.server_close()
        (output / 'result.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
