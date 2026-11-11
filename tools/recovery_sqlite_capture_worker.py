"""Isolated stdlib-only G3 worker: no App imports, network, extensions or recapture.

Linux /proc FD attestation binds each actual SQLite unix-VFS main descriptor
before any statement. Authorized duplicate descriptors remain open until their
SQLite connection closes: closing one earlier can discard POSIX inode locks.
Normal SQLite WAL semantics are retained; hostile WAL/SHM namespace replacement
is not certified by main-inode attestation.
"""
from __future__ import annotations
from contextlib import closing
import hashlib
import fcntl
import json
import math
import os
import re
import resource
import select
import sqlite3
import stat
import sys
import time
from urllib.parse import quote

MAX_BYTES = 4 * 1024 * 1024 * 1024
MAX_METADATA = 128 * 1024
MAX_TABLES = 6000
CRITICAL_TABLES = ("users", "matches", "picks", "favorites", "api_sync_runs",
                   "match_snapshots", "odds_memory_snapshots", "live_memory_snapshots",
                   "market_forecast_snapshots", "pick_decisions", "pick_discards",
                   "telegram_delivery_memory", "team_identity_cache", "data_memory_errors",
                   "persistent_cache", "pick_grading_results", "pick_grading_runs", "telegram_queue")
SOURCE_BINDING = "ISOLATED_WORKER_CONNECTION_FD_V1"
_BOUND_ORIGINS = {}


class WorkerError(ValueError):
    pass


def _time(deadline):
    if type(deadline) not in (int, float) or not math.isfinite(deadline) or time.monotonic() >= deadline:
        raise WorkerError("WORKER_DEADLINE_EXPIRED")


def _identity(info):
    return tuple(int(getattr(info, k)) for k in
                 ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
                  "st_size", "st_mtime_ns", "st_ctime_ns"))


def _origin(info):
    return _identity(info)[:6]


def _single_thread():
    if sys.platform != "linux" or len(os.listdir("/proc/self/task")) != 1:
        raise WorkerError("SINGLE_THREAD_UNIX_WORKER_REQUIRED")


MAX_OPEN_FDS = 128
_ACTIVE_DEADLINE = None


def _fd_table_once():
    result = {}
    names = os.listdir("/proc/self/fd")
    if len(names) > MAX_OPEN_FDS:
        raise WorkerError("FD_INVENTORY_BUDGET")
    for name in names:
        if _ACTIVE_DEADLINE is not None:
            _time(_ACTIVE_DEADLINE)
        if not name.isdecimal():
            raise WorkerError("FD_ATTESTATION_UNAVAILABLE")
        fd = int(name)
        try:
            result[fd] = _origin(os.fstat(fd)) + (fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE,)
        except OSError as exc:
            # listdir's own descriptor closes before this fstat. No other
            # disappearing descriptor is permitted by the before/after table.
            if exc.errno != 9:
                raise
    return result


def _fd_table():
    _single_thread()
    first, second = _fd_table_once(), _fd_table_once()
    if first != second:
        raise WorkerError("UNSTABLE_FD_INVENTORY")
    return first


def _attest_new_connection(before, authorized_fd, *, table=None):
    """Fresh worker, one private unix VFS connection at a time per database."""
    after = _fd_table() if table is None else table
    expected = _origin(os.fstat(authorized_fd)) + (fcntl.fcntl(authorized_fd, fcntl.F_GETFL) & os.O_ACCMODE,)
    if any(after.get(fd) != identity for fd, identity in before.items()):
        raise WorkerError("SQLITE_CONNECTION_FD_ATTESTATION_FAILED")
    added = set(after) - set(before)
    if len(added) != 1:
        raise WorkerError("SQLITE_CONNECTION_FD_ATTESTATION_FAILED")
    actual_fd = next(iter(added))
    if (after[actual_fd] != expected or not stat.S_ISREG(os.fstat(actual_fd).st_mode)
            or fcntl.fcntl(actual_fd, fcntl.F_GETFL) & os.O_ACCMODE
               != fcntl.fcntl(authorized_fd, fcntl.F_GETFL) & os.O_ACCMODE):
        raise WorkerError("SQLITE_CONNECTION_FD_ATTESTATION_FAILED")
    _BOUND_ORIGINS[actual_fd] = _origin(os.fstat(authorized_fd))
    return actual_fd


def _same_connection(actual_fd, authorized_fd):
    _single_thread()
    actual, authorized = os.fstat(actual_fd), os.fstat(authorized_fd)
    expected = _BOUND_ORIGINS.get(actual_fd)
    if (expected is None or not stat.S_ISREG(actual.st_mode) or actual.st_nlink != 1
            or _origin(actual) != expected or _origin(authorized) != expected
            or fcntl.fcntl(actual_fd, fcntl.F_GETFL) & os.O_ACCMODE
               != fcntl.fcntl(authorized_fd, fcntl.F_GETFL) & os.O_ACCMODE):
        raise WorkerError("SQLITE_CONNECTION_FD_CHANGED")


def _same_file(fd, parent, name, expected=None):
    opened = os.fstat(fd)
    named = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
            or _identity(opened) != _identity(named)
            or (expected is not None and _identity(opened) != expected)):
        raise WorkerError("CAPTURE_FILE_CHANGED")
    return opened


def _named_origin(fd, parent, name):
    opened, named = os.fstat(fd), os.stat(name, dir_fd=parent, follow_symlinks=False)
    if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
            or _origin(opened) != _origin(named)):
        raise WorkerError("SQLITE_AUTHORIZED_NAME_CHANGED")
    return _origin(opened)


def _open_connection(parent, name, authorized_fd, *, readonly, deadline):
    _time(deadline)
    authorized_origin = _named_origin(authorized_fd, parent, name)
    before = _fd_table()
    uri = ("file:" + quote("/proc/self/fd/" + str(parent) + "/" + name, safe="/:")
           + ("?mode=ro" if readonly else "?mode=rw") + "&cache=private&vfs=unix")
    expected_access = os.O_RDONLY if readonly else os.O_RDWR
    if fcntl.fcntl(authorized_fd, fcntl.F_GETFL) & os.O_ACCMODE != expected_access:
        raise WorkerError("SQLITE_CONNECTION_ACCESS_MODE_MISMATCH")
    kwargs = {"uri": True, "timeout": 0.05, "isolation_level": None,
              "factory": sqlite3.Connection, "cached_statements": 0}
    if hasattr(sqlite3, "LEGACY_TRANSACTION_CONTROL"):
        kwargs["autocommit"] = sqlite3.LEGACY_TRANSACTION_CONTROL
    conn = sqlite3.connect(uri, **kwargs)
    try:
        # sqlite3_open eagerly opens main, WAL/SHM only on later access.
        # No PRAGMA, BEGIN or other statement precedes this attestation.
        actual_fd = _attest_new_connection(before, authorized_fd)
        _BOUND_ORIGINS[actual_fd] = authorized_origin
        _same_connection(actual_fd, authorized_fd)
        _named_origin(authorized_fd, parent, name)
        _time(deadline)
        conn.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        conn.execute("PRAGMA busy_timeout=50")
        return conn, actual_fd
    except BaseException:
        conn.close()
        raise


def _copy_once(source, destination, source_actual_fd, authorized_fd, deadline, snapshot_byte_limit=MAX_BYTES):
    # Same established WAL pin/fallback semantics as the actual producer; one
    # backup call only, never a second copy, retry loop or VACUUM fallback.
    pinned = False
    release_before_copy = False
    try:
        _same_connection(source_actual_fd, authorized_fd)
        try:
            wal = str(source.execute("PRAGMA journal_mode").fetchone()[0]).lower() == "wal"
            if wal:
                source.execute("BEGIN")
                pinned = True
                source.execute("SELECT rootpage FROM sqlite_master LIMIT 1").fetchall()
                release_before_copy = str(source.execute("PRAGMA journal_mode").fetchone()[0]).lower() != "wal"
        except sqlite3.OperationalError as exc:
            code = getattr(exc, "sqlite_errorcode", None)
            if type(code) is not int or code & 255 not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                raise
            release_before_copy = pinned
        if release_before_copy:
            source.rollback()
            pinned = False
        _same_connection(source_actual_fd, authorized_fd)

        def progress(_status, _remaining, total):
            _time(deadline)
            _same_connection(source_actual_fd, authorized_fd)
            _same_connection(destination[2], destination[1])
            # SQLite maximum page size gives an unconditional file-size cap;
            # the destination FD is additionally checked after every progress.
            if os.fstat(destination[1]).st_size > snapshot_byte_limit or total < 0:
                raise WorkerError("SQLITE_SNAPSHOT_BYTE_BUDGET")
        source.backup(destination[0], pages=256, progress=progress, sleep=0.05)
        _same_connection(source_actual_fd, authorized_fd)
    finally:
        if pinned:
            source.rollback()


def _standalone(parent, name):
    for suffix in ("-wal", "-journal"):
        try:
            info = os.stat(name + suffix, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != 0:
            raise WorkerError("CAPTURE_NOT_STANDALONE")
    try:
        shm = os.stat(name + "-shm", dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        shm = None
    if shm is not None and (not stat.S_ISREG(shm.st_mode) or shm.st_nlink != 1 or shm.st_size % 32768):
        raise WorkerError("CAPTURE_NOT_STANDALONE")


def _hash(fd, deadline):
    os.lseek(fd, 0, os.SEEK_SET)
    digest, size = hashlib.sha256(), 0
    while True:
        _time(deadline)
        block = os.read(fd, 65536)
        if not block:
            return digest.hexdigest()
        size += len(block)
        if size > MAX_BYTES:
            raise WorkerError("SQLITE_SNAPSHOT_BYTE_BUDGET")
        digest.update(block)


def _limit(kind, value):
    soft, hard = resource.getrlimit(kind)
    values = [value] + [v for v in (soft, hard) if v != resource.RLIM_INFINITY]
    resource.setrlimit(kind, (min(values), hard))


def _configure_limits(deadline, snapshot_byte_limit=MAX_BYTES):
    global _ACTIVE_DEADLINE
    _ACTIVE_DEADLINE = deadline
    _limit(resource.RLIMIT_CORE, 0)
    _limit(resource.RLIMIT_AS, 512 * 1024 * 1024)
    _limit(resource.RLIMIT_FSIZE, snapshot_byte_limit + 64 * 1024 * 1024)
    _limit(resource.RLIMIT_CPU, max(1, math.ceil(deadline - time.monotonic()) + 1))


def _input(deadline=None):
    if deadline is not None:
        _time(deadline)
        ready, _, _ = select.select([sys.stdin.buffer], [], [], max(0.0, deadline - time.monotonic()))
        if not ready:
            raise WorkerError("WORKER_DEADLINE_EXPIRED")
    raw = sys.stdin.buffer.readline(8193)
    if not raw.endswith(b"\n") or len(raw) > 8192:
        raise WorkerError("INVALID_WORKER_PROTOCOL")
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise WorkerError("INVALID_WORKER_PROTOCOL")
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs)


def _emit(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii") + b"\n"
    if len(raw) > MAX_METADATA + 16384:
        raise WorkerError("WORKER_RESPONSE_BUDGET")
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


def _run():
    payload = _input()
    bounded = type(payload) is dict and payload.get("schema") == "G3_CAPTURE_WORKER_V2"
    snapshot_byte_limit = payload.get("snapshot_byte_limit") if bounded else MAX_BYTES
    keys = {"schema", "operation_id", "proposal_sha256", "capture_id", "deadline",
            "source_parent_fd", "expected_source_origin", "source_name", "snapshot_parent_fd", "snapshot_fd",
            "critical_tables"}
    if bounded:
        keys.add("snapshot_byte_limit")
    if (type(payload) is not dict or set(payload) != keys
            or payload["schema"] != ("G3_CAPTURE_WORKER_V2" if bounded else "G3_CAPTURE_WORKER_V1")
            or type(snapshot_byte_limit) is not int or not 0 < snapshot_byte_limit <= MAX_BYTES
            or not re.fullmatch(r"[A-Z0-9_-]{1,96}", payload["operation_id"])
            or not re.fullmatch(r"[0-9a-f]{64}", payload["proposal_sha256"])
            or not re.fullmatch(r"[0-9a-f]{32}", payload["capture_id"])
            or type(payload["source_name"]) is not str or not 1 <= len(os.fsencode(payload["source_name"])) <= 255
            or payload["source_name"] in (".", "..") or any(v in payload["source_name"] for v in ("/", "\\", "\0"))
            or type(payload["expected_source_origin"]) is not list
            or len(payload["expected_source_origin"]) != 6
            or any(type(v) is not int or v < 0 for v in payload["expected_source_origin"])
            or type(payload["critical_tables"]) is not list
            or tuple(payload["critical_tables"]) != CRITICAL_TABLES
            or len(payload["critical_tables"]) > 128
            or any(type(v) is not str or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,95}", v)
                   for v in payload["critical_tables"])):
        raise WorkerError("INVALID_WORKER_PROTOCOL")
    deadline = payload["deadline"]
    _time(deadline)
    _single_thread()
    _configure_limits(deadline, snapshot_byte_limit)
    fds = [payload[k] for k in ("source_parent_fd", "snapshot_parent_fd", "snapshot_fd")]
    if any(type(fd) is not int or fd <= 2 for fd in fds) or len(set(fds)) != 3:
        raise WorkerError("INVALID_WORKER_PROTOCOL")
    sp, dp, df = fds
    destination_parent = os.fstat(dp)
    if (not stat.S_ISDIR(os.fstat(sp).st_mode) or not stat.S_ISDIR(destination_parent.st_mode)
            or destination_parent.st_mode & 0o077 or destination_parent.st_uid != os.geteuid()):
        raise WorkerError("INVALID_WORKER_PROTOCOL")
    # Authorize/open the main source ONLY in this clean worker. Opening and
    # closing a duplicate in a SQLite-using caller could cancel caller locks.
    sf = os.open(payload["source_name"], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=sp)
    source_origin = _origin(os.fstat(sf))
    if list(source_origin) != payload["expected_source_origin"]:
        raise WorkerError("SQLITE_SOURCE_AUTHORIZATION_CHANGED")
    _named_origin(sf, sp, payload["source_name"])
    initial = _same_file(df, dp, "snapshot.partial")
    if initial.st_size != 0 or initial.st_mode & 0o077 or initial.st_uid != os.geteuid():
        raise WorkerError("INVALID_CAPTURE_DESTINATION")
    source = destination = None
    attempted = False
    try:
        source, source_actual = _open_connection(sp, payload["source_name"], sf, readonly=True, deadline=deadline)
        destination, destination_actual = _open_connection(dp, "snapshot.partial", df, readonly=False, deadline=deadline)
        pages = source.execute("PRAGMA page_count").fetchone()[0]
        page_size = source.execute("PRAGMA page_size").fetchone()[0]
        estimate = pages * page_size
        if not 0 < estimate <= snapshot_byte_limit:
            raise WorkerError("SQLITE_SNAPSHOT_BYTE_BUDGET")
        disk = os.fstatvfs(dp)
        if disk.f_bavail * disk.f_frsize < estimate + max(64 * 1024 * 1024, estimate // 10):
            raise WorkerError("SQLITE_SNAPSHOT_STORAGE_INSUFFICIENT")
        attempted = True
        _same_connection(destination_actual, df)
        _copy_once(source, (destination, df, destination_actual), source_actual, sf, deadline, snapshot_byte_limit)
        source.close()
        source = None
        # Keep sf until AFTER source.close(): duplicated-inode close releases
        # POSIX locks process-wide. No live source descriptor closes earlier.
        os.close(sf)
        sf = None
        mode = destination.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
        if str(mode).lower() != "delete":
            raise WorkerError("CAPTURE_NOT_STANDALONE")
        _same_connection(destination_actual, df)
        destination.close()
        destination = None
        _standalone(dp, "snapshot.partial")
        os.fsync(df)
        os.fsync(dp)
        captured = _same_file(df, dp, "snapshot.partial")
        if (captured.st_dev, captured.st_ino) != (initial.st_dev, initial.st_ino):
            raise WorkerError("CAPTURE_FILE_CHANGED")
        readonly_fd = os.open("snapshot.partial", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dp)
        if _identity(os.fstat(readonly_fd)) != _identity(captured):
            os.close(readonly_fd)
            raise WorkerError("CAPTURE_FILE_CHANGED")
        # Destination connection already closed, then close duplicate writer.
        os.close(df)
        df = readonly_fd
        common = {k: payload[k] for k in ("operation_id", "proposal_sha256", "capture_id", "deadline")}
        if bounded:
            common["snapshot_byte_limit"] = snapshot_byte_limit
        common.update(schema="G3_CAPTURE_WORKER_RECEIPT_V2" if bounded else "G3_CAPTURE_WORKER_RECEIPT_V1", worker_pid=os.getpid(),
                      source_binding=SOURCE_BINDING, source_origin=list(source_origin),
                      snapshot_identity=list(_identity(captured)), sqlite_backup_calls=1,
                      source_attested_before_sql=True, destination_attested_before_sql=True,
                      source_connection_retained_through_backup=True,
                      source_connections_closed=True, snapshot_writers_closed=True,
                      authorized_source_fd_opened_in_worker=True,
                      hostile_wal_namespace_certified=False)
        _time(deadline)
        _emit({**common, "ok": True, "phase": "PREPARED"})
        return

    finally:
        if destination is not None:
            destination.close()
        if source is not None:
            source.close()
        if sf is not None:
            os.close(sf)


def _run_validate():
    payload = _input()
    bounded = type(payload) is dict and payload.get("schema") == "G3_VALIDATE_WORKER_V2"
    if (type(payload) is not dict or set(payload) != {"schema", "prepared_receipt", "snapshot_parent_fd", "snapshot_fd", "critical_tables"}
            or payload["schema"] != ("G3_VALIDATE_WORKER_V2" if bounded else "G3_VALIDATE_WORKER_V1")
            or type(payload["prepared_receipt"]) is not dict
            or type(payload["critical_tables"]) is not list or tuple(payload["critical_tables"]) != CRITICAL_TABLES):
        raise WorkerError("INVALID_WORKER_PROTOCOL")
    common = dict(payload["prepared_receipt"])
    snapshot_byte_limit = common.get("snapshot_byte_limit") if bounded else MAX_BYTES
    if type(snapshot_byte_limit) is not int or not 0 < snapshot_byte_limit <= MAX_BYTES:
        raise WorkerError("INVALID_WORKER_PROTOCOL")
    deadline = common.get("deadline")
    _time(deadline)
    _single_thread()
    _configure_limits(deadline, snapshot_byte_limit)
    dp, df = payload["snapshot_parent_fd"], payload["snapshot_fd"]
    if (type(dp) is not int or type(df) is not int or dp <= 2 or df <= 2 or dp == df
            or common.get("ok") is not True or common.get("phase") != "PREPARED"
            or common.get("schema") != ("G3_CAPTURE_WORKER_RECEIPT_V2" if bounded else "G3_CAPTURE_WORKER_RECEIPT_V1")
            or common.get("source_binding") != SOURCE_BINDING
            or type(common.get("snapshot_identity")) is not list or len(common["snapshot_identity"]) != 9):
        raise WorkerError("INVALID_WORKER_PROTOCOL")
    parent = os.fstat(dp)
    if not stat.S_ISDIR(parent.st_mode) or parent.st_mode & 0o077 or parent.st_uid != os.geteuid():
        raise WorkerError("INVALID_CAPTURE_DESTINATION")
    captured = _same_file(df, dp, "snapshot.partial", tuple(common["snapshot_identity"]))
    if not 0 < captured.st_size <= snapshot_byte_limit:
        raise WorkerError("SQLITE_SNAPSHOT_BYTE_BUDGET")
    common["worker_pid"] = os.getpid()
    expected = _identity(captured)
    _same_file(df, dp, "snapshot.partial", expected)
    _standalone(dp, "snapshot.partial")
    integrity, integrity_actual = _open_connection(dp, "snapshot.partial", df, readonly=True, deadline=deadline)
    try:
        _same_file(df, dp, "snapshot.partial", expected)
        integrity.execute("BEGIN")
        if integrity.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise WorkerError("CAPTURE_INTEGRITY_FAILED")
        integrity.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_METADATA)
        tables, names_bytes = [], 0
        with closing(integrity.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")) as cursor:
            for row in cursor:
                _time(deadline)
                names_bytes += len(row[0].encode("utf-8"))
                if len(tables) >= MAX_TABLES or names_bytes > MAX_METADATA // 2:
                    raise WorkerError("SQLITE_METADATA_BUDGET")
                tables.append(row[0])
        counts = {}
        for table in payload["critical_tables"]:
            _time(deadline)
            if table in tables:
                counts[table] = int(integrity.execute('SELECT COUNT(*) FROM "' + table + '"').fetchone()[0])
        _same_connection(integrity_actual, df)
        digest = _hash(df, deadline)
        _same_connection(integrity_actual, df)
        _same_file(df, dp, "snapshot.partial", expected)
    finally:
        # Do not close df while this SQLite connection holds inode locks.
        integrity.close()
    _standalone(dp, "snapshot.partial")
    _same_file(df, dp, "snapshot.partial", expected)
    _time(deadline)
    _emit({**common, "ok": True, "phase": "VALIDATED", "integrity_attested_before_sql": True,
           "sha256": digest, "tables_included": tables, "records_summary": counts})


def _run_restore_member():
    """Restore sealed published bytes, not a new snapshot of any live source."""
    payload = _input()
    keys = {"schema", "operation_id", "proposal_sha256", "capture_id", "source_id",
            "deadline", "maximum_bytes", "size_bytes", "sha256", "backup_name",
            "backup_parent_fd", "backup_fd", "destination_parent_fd", "destination_fd"}
    if (type(payload) is not dict or set(payload) != keys
            or payload["schema"] != "G3_RESTORE_MEMBER_WORKER_V1"
            or type(payload["operation_id"]) is not str
            or re.fullmatch(r"[A-Za-z0-9_-]{1,96}", payload["operation_id"]) is None
            or type(payload["proposal_sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", payload["proposal_sha256"]) is None
            or type(payload["capture_id"]) is not str
            or re.fullmatch(r"[0-9a-f]{32}", payload["capture_id"]) is None
            or type(payload["source_id"]) is not str
            or re.fullmatch(r"principal|aux_[a-z0-9_]{1,40}", payload["source_id"]) is None
            or type(payload["backup_name"]) is not str
            or re.fullmatch(r"database_[0-9a-f]{32}\.db", payload["backup_name"]) is None
            or type(payload["sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", payload["sha256"]) is None
            or type(payload["maximum_bytes"]) is not int
            or not 0 < payload["maximum_bytes"] <= MAX_BYTES
            or type(payload["size_bytes"]) is not int
            or not 0 < payload["size_bytes"] <= payload["maximum_bytes"]):
        raise WorkerError("INVALID_RESTORE_MEMBER_PROTOCOL")
    deadline = payload["deadline"]
    _time(deadline)
    if deadline - time.monotonic() > 300:
        raise WorkerError("INVALID_RESTORE_MEMBER_BUDGET")
    _single_thread()
    _configure_limits(deadline, payload["maximum_bytes"])
    descriptors = tuple(payload[k] for k in ("backup_parent_fd", "backup_fd",
                                            "destination_parent_fd", "destination_fd"))
    if any(type(fd) is not int or fd <= 2 for fd in descriptors) or len(set(descriptors)) != 4:
        raise WorkerError("INVALID_RESTORE_MEMBER_PROTOCOL")
    bp, bf, dp, df = descriptors
    for parent in (bp, dp):
        info = os.fstat(parent)
        if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
            raise WorkerError("PRIVATE_RESTORE_MEMBER_REQUIRED")
    name = ("restoration-test.db" if payload["source_id"] == "principal"
            else payload["source_id"] + ".db")
    source = _same_file(bf, bp, payload["backup_name"])
    target = _same_file(df, dp, name)
    if (source.st_size != payload["size_bytes"] or target.st_size != 0
            or source.st_mode & 0o077 or target.st_mode & 0o077
            or source.st_uid != os.geteuid() or target.st_uid != os.geteuid()
            or _origin(source) == _origin(target)
            or fcntl.fcntl(bf, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDONLY
            or fcntl.fcntl(df, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDWR):
        raise WorkerError("INVALID_RESTORE_MEMBER_FILES")
    expected_source = _identity(source)
    _standalone(bp, payload["backup_name"])
    digest, copied = hashlib.sha256(), 0
    os.lseek(bf, 0, os.SEEK_SET)
    while True:
        _time(deadline)
        block = os.read(bf, 65536)
        if not block:
            break
        copied += len(block)
        if copied > payload["size_bytes"]:
            raise WorkerError("RESTORE_MEMBER_SIZE_CHANGED")
        digest.update(block)
        view = memoryview(block)
        while view:
            _time(deadline)
            wrote = os.write(df, view)
            if wrote <= 0:
                raise WorkerError("RESTORE_MEMBER_WRITE_FAILED")
            view = view[wrote:]
    os.fsync(df)
    if copied != payload["size_bytes"] or digest.hexdigest() != payload["sha256"]:
        raise WorkerError("RESTORE_MEMBER_HASH_MISMATCH")
    _same_file(bf, bp, payload["backup_name"], expected_source)
    copied_identity = _identity(_same_file(df, dp, name))
    if _hash(df, deadline) != payload["sha256"]:
        raise WorkerError("RESTORE_MEMBER_HASH_MISMATCH")
    # Switch the authorized descriptor to read-only BEFORE opening SQLite.
    # Keep every descriptor for this inode until its connection is closed.
    readonly_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dp)
    try:
        _same_file(readonly_fd, dp, name, copied_identity)
        _standalone(dp, name)
        conn, actual = _open_connection(dp, name, readonly_fd, readonly=True, deadline=deadline)
        try:
            conn.execute("BEGIN")
            if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise WorkerError("RESTORE_MEMBER_INTEGRITY_FAILED")
            _same_connection(actual, readonly_fd)
            _same_file(readonly_fd, dp, name, copied_identity)
        finally:
            conn.close()
        _same_file(readonly_fd, dp, name, copied_identity)
    finally:
        os.close(readonly_fd)
    _standalone(dp, name)
    _standalone(bp, payload["backup_name"])
    _same_file(bf, bp, payload["backup_name"], expected_source)
    _same_file(df, dp, name, copied_identity)
    _time(deadline)
    _emit({"schema": "G3_RESTORE_MEMBER_RECEIPT_V1", "ok": True,
           "operation_id": payload["operation_id"], "proposal_sha256": payload["proposal_sha256"],
           "capture_id": payload["capture_id"], "source_id": payload["source_id"],
           "deadline": deadline, "maximum_bytes": payload["maximum_bytes"],
           "size_bytes": copied, "sha256": digest.hexdigest(), "worker_pid": os.getpid(),
           "source_identity": list(expected_source), "destination_identity": list(copied_identity),
           "integrity_attested_before_sql": True, "integrity_check_ok": True,
           "sealed_snapshot_copy_calls": 1, "live_source_capture_calls": 0})


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--g3-capture-worker"]:
            _run()
        elif sys.argv[1:] == ["--g3-validate-worker"]:
            _run_validate()
        elif sys.argv[1:] == ["--g3-restore-member-worker"]:
            _run_restore_member()
        else:
            raise WorkerError("EXPLICIT_WORKER_ENTRY_REQUIRED")
    except BaseException as exc:
        try:
            _emit({"schema": "G3_CAPTURE_WORKER_FAILURE_V1", "ok": False,
                   "code": str(exc) if type(exc) is WorkerError else "SQLITE_CAPTURE_WORKER_FAILED"})
        except BaseException:
            pass
        sys.exit(2)
