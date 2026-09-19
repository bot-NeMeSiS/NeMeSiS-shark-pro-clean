import concurrent.futures
import json
from pathlib import Path
import sqlite3
import time

import pytest

from engines.sentinel_jobs import Store, Rejected, revision, run_one

ROOT = Path(__file__).resolve().parents[1]


def payload(key="first_request_0001"):
    return {"action":"product_surface_review", "parameters":{"scope":"client_templates"}, "request_key":key}


def submit_process(path, owner, key):
    return Store(path).submit(owner, payload(key), "same-revision")[0]["id"]


def claim_process(path):
    return Store(path).claim()


@pytest.fixture
def store(tmp_path):
    obj = Store(tmp_path / "jobs.sqlite")
    obj.initialize()
    return obj


def test_replay_and_tabs_recover_one_job(store):
    first, reused = store.submit("admin-a", payload(), "source")
    assert not reused
    assert store.submit("admin-a", payload(), "changed-source")[0]["id"] == first["id"]
    assert store.submit("admin-a", payload("second_tab_000001"), "source")[0]["id"] == first["id"]
    assert len(Store(store.path).list("admin-a")) == 1
    assert Store(store.path).get("admin-b", first["id"]) is None


@pytest.mark.parametrize("change", [
    {"action":"shell"}, {"parameters":{"scope":"../.env"}},
    {"parameters":{"scope":"client_templates", "url":"https://example.com"}},
    {"request_key":123}, {"request_key":"short"}, {"command":"print(1)"},
])
def test_closed_registry_rejects_untrusted_input(store, change):
    original, _ = store.submit("admin", payload(), "source")
    with pytest.raises(Rejected):
        store.submit("admin", dict(payload(), **change), "source")
    assert store.get("admin", original["id"])["state"] == "QUEUED"
    assert store.claim()["attempt"] == 1


def test_process_concurrency_and_owner_scope(store):
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit_process, str(store.path), "a", f"tab_request_{i:05d}") for i in range(6)]
        ids = [f.result(timeout=20) for f in futures]
        assert len(set(ids)) == 1
        other = pool.submit(submit_process, str(store.path), "b", "tab_request_00000").result(timeout=20)
        assert other != ids[0]
        claimed = [f.result(timeout=20) for f in [pool.submit(claim_process, str(store.path)) for _ in range(4)]]
    jobs = [j for j in claimed if j]
    assert len(jobs) == 2
    assert len({j["id"] for j in jobs}) == 2
    assert all(j["attempt"] == 1 for j in jobs)


def test_interrupt_is_terminal_and_fences_late_result(store):
    job, _ = store.submit("a", payload(), "source")
    claimed = store.claim()
    with store.connection(write=True) as con:
        con.execute("UPDATE sentinel_jobs SET lease_until=?", (time.time()-1,))
    restarted = Store(store.path)
    restarted.recover_and_heartbeat()
    assert restarted.get("a", job["id"])["state"] == "INTERRUPTED"
    assert restarted.claim() is None
    assert not restarted.finish(claimed, {"ok":True})
    assert restarted.submit("a", payload(), "source")[0]["state"] == "INTERRUPTED"


def test_read_does_not_create_database(tmp_path):
    missing = Store(tmp_path / "missing.sqlite")
    assert not missing.available()
    with pytest.raises(sqlite3.OperationalError):
        missing.list("a")
    assert not missing.path.exists()


def test_real_worker_and_restart(store):
    job, _ = store.submit("a", payload(), revision(ROOT))
    assert run_one(store, ROOT)
    result = Store(store.path).get("a", job["id"])
    assert result["state"] == "COMPLETED", result
    assert result["result"]["database_status"] == "NOT_ACCESSED"
    assert result["result"]["metrics"]["client_surfaces_present"] == 8
    assert len(result["result"]["scope"]) == 8
    assert result["attempt"] == 1
    assert not run_one(store, ROOT)


def test_error_is_not_success_and_not_retried(store, monkeypatch):
    import automation_workforce.common as common
    job, _ = store.submit("a", payload(), revision(ROOT))
    monkeypatch.setattr(common, "run_command", lambda *a, **k: {"ok":False, "error":"secret-must-not-persist"})
    run_one(store, ROOT)
    result = store.get("a", job["id"])
    assert result["state"] == "FAILED" and result["result"] is None
    assert "secret" not in json.dumps(result)
    assert not run_one(store, ROOT)


def test_revision_change_never_certifies_new_bytes(store):
    job, _ = store.submit("a", payload(), "previous-revision")
    run_one(store, ROOT)
    assert store.get("a", job["id"])["error"] == "source_revision_changed"
