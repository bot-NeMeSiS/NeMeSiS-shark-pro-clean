"""Native transient SQLite-open substitutions in fresh owned Linux processes.

This is a test-only delta over frozen G3 candidate-v2. The bootstrap wraps only
its own sqlite3.connect; the production worker gains no injection hook, CLI mode
or environment switch. Test authoring/AST checks do not execute this bootstrap.
All databases are small synthetic fixtures created under pytest's tmp_path.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pytest


_NATIVE_LINUX = (
    sys.platform == "linux"
    and bool(getattr(os, "O_NOFOLLOW", 0))
    and bool(getattr(os, "O_DIRECTORY", 0))
    and Path("/proc/self/fd").is_dir()
    and all(function in os.supports_dir_fd for function in (os.open, os.stat, os.rename))
)


_OWNED_BOOTSTRAP = r'''
import fcntl
import hashlib
import json
import os
import runpy
import sqlite3
import sys

raw = sys.stdin.buffer.read(8193)
if len(raw) > 8192:
    raise RuntimeError("OWNED_TEST_INPUT_BUDGET")
payload = json.loads(raw)
namespace = runpy.run_path(payload["worker_file"], run_name="g3_owned_connection_test")
open_connection = namespace["_open_connection"]
worker_globals = open_connection.__globals__
fd_table = namespace["_fd_table"]

parent = os.open(payload["directory"], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
readonly = payload["role"] in ("source", "integrity")
access = os.O_RDONLY if readonly else os.O_RDWR
authorized_fd = os.open("authorized.db", access | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
authorized_before = os.fstat(authorized_fd)
decoy_before = os.stat("decoy.db", dir_fd=parent, follow_symlinks=False)
statements = []
connect_calls = []
copy_calls = []
integrity_hash_calls = []
opened_origins = []
opened_access_modes = []
connections = []
restored_before_return = []
original_connect = sqlite3.connect
original_copy = worker_globals["_copy_once"]
original_hash = worker_globals["_hash"]

def counted_copy(*args, **kwargs):
    copy_calls.append(1)
    return original_copy(*args, **kwargs)

def counted_hash(*args, **kwargs):
    integrity_hash_calls.append(1)
    return original_hash(*args, **kwargs)

worker_globals["_copy_once"] = counted_copy
worker_globals["_hash"] = counted_hash

def transient_connect(uri, **kwargs):
    if connect_calls:
        raise RuntimeError("OWNED_SECOND_CONNECTION_DENIED")
    connect_calls.append(1)
    before = fd_table()
    os.rename("authorized.db", "authorized.saved", src_dir_fd=parent, dst_dir_fd=parent)
    os.rename("decoy.db", "authorized.db", src_dir_fd=parent, dst_dir_fd=parent)
    connection = None
    try:
        # The real SQLite unix VFS opens B while the authorized basename points
        # at B. This fresh process has never opened or closed a SQLite database.
        connection = original_connect(uri, **kwargs)
        connections.append(connection)
        connection.set_trace_callback(statements.append)
        after = fd_table()
        added = sorted(set(after) - set(before))
        for descriptor in added:
            info = os.fstat(descriptor)
            opened_origins.append([info.st_dev, info.st_ino])
            opened_access_modes.append(fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_ACCMODE)
    finally:
        # Restore BOTH names before returning the actual connection to B. A
        # pathname-only before/after check would now observe authorized A.
        os.rename("authorized.db", "decoy.db", src_dir_fd=parent, dst_dir_fd=parent)
        os.rename("authorized.saved", "authorized.db", src_dir_fd=parent, dst_dir_fd=parent)
    named = os.stat("authorized.db", dir_fd=parent, follow_symlinks=False)
    restored_before_return.append(
        (named.st_dev, named.st_ino) == (authorized_before.st_dev, authorized_before.st_ino))
    return connection

sqlite3.connect = transient_connect
code = "UNEXPECTED_CONNECTION_ACCEPTED"
try:
    connection, _actual_fd = open_connection(
        parent, "authorized.db", authorized_fd,
        readonly=readonly, deadline=payload["deadline"])
    # Acceptance itself is a test failure. No fallback, second connection,
    # backup or integrity operation is attempted after an unsafe acceptance.
    connection.close()
except namespace["WorkerError"] as exc:
    code = str(exc)
finally:
    sqlite3.connect = original_connect
    for connection in connections:
        connection.close()
    authorized_after = os.stat("authorized.db", dir_fd=parent, follow_symlinks=False)
    decoy_after = os.stat("decoy.db", dir_fd=parent, follow_symlinks=False)
    os.close(authorized_fd)
    os.close(parent)

result = {
    "schema": "OWNED_G3_TRANSIENT_SQLITE_OPEN_TEST_V1",
    "role": payload["role"],
    "readonly": readonly,
    "code": code,
    "real_connect_calls": len(connect_calls),
    "opened_origins": opened_origins,
    "opened_access_modes": opened_access_modes,
    "authorized_origin_before": [authorized_before.st_dev, authorized_before.st_ino],
    "authorized_origin_after": [authorized_after.st_dev, authorized_after.st_ino],
    "decoy_origin_before": [decoy_before.st_dev, decoy_before.st_ino],
    "decoy_origin_after": [decoy_after.st_dev, decoy_after.st_ino],
    "authorized_name_restored_before_connect_returned": restored_before_return,
    "statements": statements,
    "integrity_statements": sum("INTEGRITY_CHECK" in statement.upper() for statement in statements),
    "source_backup_calls": len(copy_calls),
    "integrity_hash_calls": len(integrity_hash_calls),
    "recapture_attempted": len(connect_calls) > 1 or len(copy_calls) > 1,
}
sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
'''


def _database(path, value):
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("CREATE TABLE owned_data (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO owned_data(value) VALUES (?)", (value,))
        connection.commit()
    path.chmod(0o600)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.skipif(not _NATIVE_LINUX, reason="native Linux unix-VFS and /proc descriptor attestation required")
@pytest.mark.parametrize("role,readonly", [("source", True), ("destination", False), ("integrity", True)])
def test_real_connect_transient_substitution_is_rejected_before_sql_copy_or_integrity(tmp_path, role, readonly):
    owned = tmp_path / "owned_connection_swap"
    owned.mkdir(mode=0o700)
    owned.chmod(0o700)
    authorized, decoy = owned / "authorized.db", owned / "decoy.db"
    if role == "destination":
        # Match the producer's exclusive, initially empty snapshot destination.
        authorized.write_bytes(b"")
        authorized.chmod(0o600)
    elif role == "integrity":
        # Corrupt captured A versus healthy B exposes integrity(B)+hash(A).
        authorized.write_bytes(b"owned-corrupt-captured-sqlite-A\n")
        authorized.chmod(0o600)
    else:
        _database(authorized, "authorized-A-owned-only")
    _database(decoy, "different-B-owned-only")
    original_a, original_b = _sha256(authorized), _sha256(decoy)
    assert original_a != original_b
    authorized_inode = (authorized.stat().st_dev, authorized.stat().st_ino)
    decoy_inode = (decoy.stat().st_dev, decoy.stat().st_ino)
    assert authorized_inode != decoy_inode
    worker_file = Path(__file__).resolve().parents[1] / "tools" / "recovery_sqlite_capture_worker.py"
    assert worker_file.is_file()
    deadline = time.monotonic() + 20.0
    payload = {
        "worker_file": str(worker_file), "directory": str(owned),
        "role": role, "deadline": deadline,
    }
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-u", "-c", _OWNED_BOOTSTRAP],
        input=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25.0,
        env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}, check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    assert len(completed.stdout) <= 16384
    report = json.loads(completed.stdout)
    assert report["schema"] == "OWNED_G3_TRANSIENT_SQLITE_OPEN_TEST_V1"
    assert report["role"] == role
    assert report["readonly"] is readonly
    assert report["code"] == "SQLITE_CONNECTION_FD_ATTESTATION_FAILED"
    assert report["real_connect_calls"] == 1
    assert report["opened_origins"] == [list(decoy_inode)]
    assert report["opened_access_modes"] == [os.O_RDONLY if readonly else os.O_RDWR]
    assert report["authorized_origin_before"] == report["authorized_origin_after"] == list(authorized_inode)
    assert report["decoy_origin_before"] == report["decoy_origin_after"] == list(decoy_inode)
    assert report["authorized_name_restored_before_connect_returned"] == [True]
    assert report["statements"] == []
    assert report["integrity_statements"] == 0
    assert report["source_backup_calls"] == 0
    assert report["integrity_hash_calls"] == 0
    assert report["recapture_attempted"] is False
    assert _sha256(authorized) == original_a
    assert _sha256(decoy) == original_b
    assert (authorized.stat().st_dev, authorized.stat().st_ino) == authorized_inode
    assert (decoy.stat().st_dev, decoy.stat().st_ino) == decoy_inode
    assert not (owned / "authorized.saved").exists()
    assert sorted(path.name for path in owned.iterdir()) == ["authorized.db", "decoy.db"]
