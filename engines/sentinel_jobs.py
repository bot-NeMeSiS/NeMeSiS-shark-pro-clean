"""Local-only durable requests for the existing Product Experience Worker."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


ACTION = "product_surface_review"
PARAMETERS = {"scope": "client_templates"}
TEMPLATES = (
    "client_app_center.html", "calendar.html", "live.html", "picks.html",
    "track_record.html", "shark.html", "telegram.html", "membership.html",
)
INPUTS = tuple("templates/" + name for name in TEMPLATES) + (
    "app.py", "templates/components/v933_ui.html",
    "templates/components/v933_navigation.html", "static/v933-product.css",
    "templates/base.html", "static/v934-realtime.js",
    "automation_workforce/v935_worker_common.py",
    "automation_workforce/product_experience_worker.py",
    "engines/sentinel_jobs.py",
)


class Rejected(ValueError):
    def __init__(self, code, status=400):
        super().__init__(code)
        self.status = status


def validate(payload):
    if not isinstance(payload, dict) or set(payload) != {"action", "parameters", "request_key"}:
        raise Rejected("invalid_request")
    if payload["action"] != ACTION or payload["parameters"] != PARAMETERS:
        raise Rejected("action_or_parameters_not_allowed")
    if not isinstance(payload["request_key"], str) or not re.fullmatch(r"[a-zA-Z0-9_-]{16,80}", payload["request_key"]):
        raise Rejected("invalid_request_key")
    return json.dumps({"action": ACTION, "parameters": PARAMETERS}, sort_keys=True)


def revision(root):
    digest = hashlib.sha256()
    for relative in INPUTS:
        path = Path(root) / relative
        digest.update(relative.encode() + b"\0")
        digest.update(path.read_bytes() if path.is_file() else b"MISSING")
        digest.update(b"\0")
    return digest.hexdigest()


class Store:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connection(self, *, write=False):
        # Even writes use mode=rw: schema creation belongs to the local supervisor.
        con = sqlite3.connect(self.path.resolve().as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        try:
            if write:
                con.execute("BEGIN IMMEDIATE")
            else:
                con.execute("PRAGMA query_only=ON")
            yield con
            if write:
                con.commit()
        finally:
            con.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS sentinel_jobs (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, action TEXT NOT NULL,
                    parameters TEXT NOT NULL, revision TEXT NOT NULL, environment TEXT NOT NULL,
                    state TEXT NOT NULL, created REAL NOT NULL, started REAL, finished REAL,
                    attempt INTEGER NOT NULL DEFAULT 0, claim TEXT, lease_until REAL,
                    result TEXT, error TEXT,
                    UNIQUE(owner, action, parameters, revision)
                );
                CREATE TABLE IF NOT EXISTS sentinel_requests (
                    owner TEXT NOT NULL, key TEXT NOT NULL, command TEXT NOT NULL,
                    job_id TEXT NOT NULL REFERENCES sentinel_jobs(id), PRIMARY KEY(owner,key)
                );
                CREATE TABLE IF NOT EXISTS sentinel_executor (id INTEGER PRIMARY KEY CHECK(id=1), seen REAL NOT NULL);
            """)

    @staticmethod
    def public(row):
        data = dict(row)
        for key in ("claim", "owner"):
            data.pop(key, None)
        for key in ("parameters", "result"):
            data[key] = json.loads(data[key]) if data[key] is not None else None
        return data

    def submit(self, owner, payload, source_revision):
        command = validate(payload)
        now = time.time()
        with self.connection(write=True) as con:
            existing = con.execute("SELECT * FROM sentinel_requests WHERE owner=? AND key=?", (owner, payload["request_key"])).fetchone()
            if existing:
                if existing["command"] != command:
                    raise Rejected("idempotency_conflict", 409)
                return self.public(con.execute("SELECT * FROM sentinel_jobs WHERE id=?", (existing["job_id"],)).fetchone()), True
            params = json.dumps(PARAMETERS, sort_keys=True)
            job = con.execute("SELECT * FROM sentinel_jobs WHERE owner=? AND action=? AND parameters=? AND revision=?", (owner, ACTION, params, source_revision)).fetchone()
            reused = job is not None
            if not job:
                job_id = uuid.uuid4().hex
                con.execute("INSERT INTO sentinel_jobs(id,owner,action,parameters,revision,environment,state,created) VALUES(?,?,?,?,?,'LOCAL_ONLY','QUEUED',?)", (job_id, owner, ACTION, params, source_revision, now))
                job = con.execute("SELECT * FROM sentinel_jobs WHERE id=?", (job_id,)).fetchone()
            con.execute("INSERT INTO sentinel_requests VALUES(?,?,?,?)", (owner, payload["request_key"], command, job["id"]))
            return self.public(job), reused

    def list(self, owner):
        with self.connection() as con:
            return [self.public(r) for r in con.execute("SELECT * FROM sentinel_jobs WHERE owner=? ORDER BY created DESC LIMIT 30", (owner,))]

    def get(self, owner, job_id):
        with self.connection() as con:
            row = con.execute("SELECT * FROM sentinel_jobs WHERE owner=? AND id=?", (owner, job_id)).fetchone()
            return self.public(row) if row else None

    def available(self):
        if not self.path.exists():
            return False
        with self.connection() as con:
            row = con.execute("SELECT seen FROM sentinel_executor WHERE id=1").fetchone()
            return bool(row and time.time() - row[0] < 20)

    def recover_and_heartbeat(self):
        now = time.time()
        with self.connection(write=True) as con:
            con.execute("UPDATE sentinel_jobs SET state='INTERRUPTED',finished=?,error='execution_interrupted' WHERE state='RUNNING' AND lease_until<?", (now, now))
            con.execute("INSERT INTO sentinel_executor VALUES(1,?) ON CONFLICT(id) DO UPDATE SET seen=excluded.seen", (now,))

    def claim(self):
        with self.connection(write=True) as con:
            row = con.execute("SELECT * FROM sentinel_jobs WHERE state='QUEUED' ORDER BY created LIMIT 1").fetchone()
            if not row:
                return None
            token = uuid.uuid4().hex
            now = time.time()
            con.execute("UPDATE sentinel_jobs SET state='RUNNING',started=?,attempt=attempt+1,claim=?,lease_until=? WHERE id=? AND state='QUEUED'", (now, token, now + 30, row["id"]))
            return dict(con.execute("SELECT * FROM sentinel_jobs WHERE id=?", (row["id"],)).fetchone())

    def finish(self, job, result=None, error=None):
        with self.connection(write=True) as con:
            return con.execute("UPDATE sentinel_jobs SET state=?,finished=?,result=?,error=? WHERE id=? AND claim=? AND state='RUNNING' AND lease_until>=?", (
                "FAILED" if error else "COMPLETED", time.time(), json.dumps(result) if result is not None else None,
                error, job["id"], job["claim"], time.time(),
            )).rowcount == 1


def run_one(store, root):
    """Called by the supervised LOCAL SAFE loop, never by a web request."""
    from automation_workforce.common import python_executable, run_command

    store.recover_and_heartbeat()
    job = store.claim()
    if not job:
        return False
    try:
        if revision(root) != job["revision"]:
            store.finish(job, error="source_revision_changed")
            return True
        output = run_command([
            python_executable(), "-B", str(Path(root) / "automation_workforce/product_experience_worker.py"),
            "--static-only", "--no-write", "--dry-run",
        ], timeout=10)
        if not output.get("ok"):
            store.finish(job, error="executor_failed_or_timed_out")
        elif revision(root) != job["revision"]:
            store.finish(job, error="source_revision_changed")
        else:
            evidence = json.loads(output["stdout_tail"])
            if evidence.get("role") != "product_experience" or evidence.get("scope") != list(TEMPLATES):
                raise ValueError("invalid_evidence")
            store.finish(job, result=evidence)
    except Exception:
        # Raw exceptions/commands may contain local paths or secrets.
        store.finish(job, error="executor_result_unavailable")
    return True
