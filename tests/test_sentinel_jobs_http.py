import uuid

import pytest


@pytest.fixture(scope="module")
def runtime():
    from tools.local_desktop.run_sentinel_local import prepare
    module, store, blocked = prepare(db_name="sentinel_http_" + uuid.uuid4().hex + ".sqlite", allow_browser=True)
    module.app.config["TESTING"] = True
    yield module, store, blocked
    assert blocked == []


def login(module, owner=None, role="ADMIN"):
    client = module.app.test_client()
    with client.session_transaction() as session:
        session["user_role"] = role
        session["user_id"] = owner or "sentinel-test-" + uuid.uuid4().hex
        session["csrf_token"] = "qa-csrf-token"
    return client


def post(client, **overrides):
    data = {"action":"product_surface_review", "parameters":{"scope":"client_templates"}, "request_key":uuid.uuid4().hex}
    data.update(overrides)
    with client.session_transaction() as session:
        token = session.get("csrf_token")
    return client.post("/api/admin/sentinel/jobs", json=data, headers={"X-CSRF-Token":token})


def test_real_handlers_and_result(runtime):
    from engines.sentinel_jobs import run_one
    module, store, _ = runtime
    client = login(module)
    response = post(client)
    assert response.status_code == 202
    job_id = response.json["job"]["id"]
    assert client.get("/api/admin/sentinel/jobs/"+job_id).json["job"]["state"] == "QUEUED"
    for _ in range(10):
        if not run_one(store, module.BASE_DIR):
            break
    result = client.get("/api/admin/sentinel/jobs/"+job_id)
    assert result.status_code == 200
    assert result.json["job"]["state"] == "COMPLETED", result.json
    assert result.json["job"]["attempt"] == 1
    assert post(client).json["job"]["id"] == job_id
    assert client.get("/api/admin/sentinel/jobs").headers["Cache-Control"] == "no-store"
    other = login(module)
    assert other.get("/api/admin/sentinel/jobs/"+job_id).status_code == 404


@pytest.mark.parametrize("role", [None, "FREE", "PRO", "ELITE"])
def test_no_client_or_visitor_access(runtime, role):
    module, _, _ = runtime
    client = module.app.test_client() if role is None else login(module, role=role)
    assert client.get("/api/admin/sentinel/jobs").status_code == 403
    assert client.get("/api/admin/sentinel/jobs/unknown").status_code == 403
    if role:
        assert post(client).status_code == 403
    assert client.get("/admin/sentinel-issues").status_code in (302, 403)


def test_bad_csrf_and_closed_parameters(runtime):
    module, _, _ = runtime
    client = login(module)
    assert client.post("/api/admin/sentinel/jobs", json={}, headers={"X-CSRF-Token":"incorrect"}).status_code == 403
    assert post(client, parameters={"scope":"../private"}).status_code == 400
    assert post(client, action="shell").status_code == 400
    assert post(client, url="https://example.com").status_code == 400
    with client.session_transaction() as session:
        token = session["csrf_token"]
    assert client.post("/api/admin/sentinel/jobs", json=[], headers={"X-CSRF-Token":token}).status_code == 400


def test_get_has_no_operational_writes_and_legacy_gets_do_not_scan(runtime, monkeypatch):
    module, store, _ = runtime
    client = login(module)
    with store.connection() as con:
        before = con.execute("SELECT count(*) FROM sentinel_jobs").fetchone()[0]
    assert client.get("/admin/sentinel-issues").status_code == 200
    assert client.get("/api/admin/sentinel/jobs").status_code == 200
    def forbidden(*args, **kwargs):
        pytest.fail("Action GET must not scan or read an issue with the action name")
    monkeypatch.setattr(module, "_v892_sentinel_issues_summary", forbidden)
    monkeypatch.setattr(module, "get_sentinel_issue", forbidden)
    for action in ("scan", "sync-autopilot", "sync-visual-worker"):
        for method in ("GET", "HEAD"):
            response = client.open("/api/admin/sentinel/issues/"+action, method=method)
            # LOCAL SAFE blocks sync actions before Flask dispatch. Scan reaches
            # the router, which must reject the action rather than read an ID.
            assert response.status_code == (405 if action == "scan" else 403)
            if action == "scan":
                assert response.headers["Allow"] == "POST"
            elif method == "GET":
                assert response.json["status"] == "LOCAL_SAFE_BLOCKED"
    with store.connection() as con:
        assert con.execute("SELECT count(*) FROM sentinel_jobs").fetchone()[0] == before


def test_issue_reader_still_reads_ids_and_checks_admin(runtime, monkeypatch):
    module, _, _ = runtime
    calls = []
    def read(issue_id, root):
        calls.append(issue_id)
        return {"id": issue_id, "status": "OPEN"} if issue_id == "qa-issue" else None
    monkeypatch.setattr(module, "get_sentinel_issue", read)
    client = login(module)
    assert client.get("/api/admin/sentinel/issues/qa-issue").json["issue"]["id"] == "qa-issue"
    assert client.get("/api/admin/sentinel/issues/qa-missing").status_code == 404
    before = list(calls)
    for role in (None, "FREE", "PRO", "ELITE"):
        client = module.app.test_client() if role is None else login(module, role=role)
        for issue_id in ("qa-issue", "scan", "sync-autopilot", "sync-visual-worker"):
            assert client.get("/api/admin/sentinel/issues/"+issue_id).status_code == 403
    assert calls == before


def test_no_executor_means_unavailable_not_queued(runtime):
    module, store, _ = runtime
    client = login(module)
    with store.connection(write=True) as con:
        con.execute("UPDATE sentinel_executor SET seen=0")
    try:
        assert post(client).status_code == 503
        assert client.get("/api/admin/sentinel/jobs").json["executor_connected"] is False
    finally:
        store.recover_and_heartbeat()


def test_disabled_outside_local_safe(runtime, monkeypatch):
    module, _, _ = runtime
    client = login(module)
    monkeypatch.setitem(module.app.config, "SENTINEL_JOBS_ENABLED", False)
    assert client.get("/api/admin/sentinel/jobs").status_code == 503
