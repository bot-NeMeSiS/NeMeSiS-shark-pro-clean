"""Explicit two-phase SQLite producer for a producer-owned captured snapshot.

No App, job, CLI or environment variable selects this mechanism. Preparation
attests the actual source/destination unix-VFS descriptors in a clean stdlib
worker, then copies once and seals private standalone bytes. Integrity, metadata, hashes and
no-replace publication run only when the bracket owner calls validate().
A failed attempt retains captured SQLite bytes and never takes another snapshot.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import stat
import time
import selectors
import subprocess
import sys
import uuid

from engines import recovery_non_sqlite_state as state

MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024 * 1024
MAX_MANIFEST_BYTES = 128 * 1024
MAX_TABLES = 6000
MIN_FREE_MARGIN = 64 * 1024 * 1024



class PreparedSnapshotError(ValueError):
    """Closed producer codes; never source paths, SQL or original exceptions."""


def _check(deadline):
    state._check_time(deadline)



SOURCE_BINDING = "ISOLATED_WORKER_CONNECTION_FD_V1"
_WORKER_SCHEMA = "G3_CAPTURE_WORKER_RECEIPT_V1"
_MAX_WORKER_RESPONSE = MAX_MANIFEST_BYTES + 16384


class _CaptureWorker:
    def __init__(self, process, binding, deadline):
        self.process, self.binding, self.deadline = process, binding, deadline
        self.validation_worker = None

    def exchange(self, payload):
        _check(self.deadline)
        raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
        if len(raw) > 8192 or self.process.poll() is not None:
            raise PreparedSnapshotError("SQLITE_CAPTURE_WORKER_NOT_AVAILABLE")
        self.process.stdin.write(raw)
        self.process.stdin.flush()
        data = bytearray()
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            while b"\n" not in data:
                _check(self.deadline)
                ready = selector.select(max(0.0, self.deadline - time.monotonic()))
                if not ready:
                    raise PreparedSnapshotError("SQLITE_CAPTURE_WORKER_DEADLINE")
                block = os.read(self.process.stdout.fileno(), min(65536, _MAX_WORKER_RESPONSE + 1 - len(data)))
                if not block or len(data) + len(block) > _MAX_WORKER_RESPONSE:
                    raise PreparedSnapshotError("INVALID_SQLITE_CAPTURE_WORKER_RESPONSE")
                data.extend(block)
        if not data.endswith(b"\n") or data.count(b"\n") != 1:
            raise PreparedSnapshotError("INVALID_SQLITE_CAPTURE_WORKER_RESPONSE")
        def pairs(items):
            out = {}
            for key, value in items:
                if key in out:
                    raise PreparedSnapshotError("INVALID_SQLITE_CAPTURE_WORKER_RESPONSE")
                out[key] = value
            return out
        value = json.loads(data, object_pairs_hook=pairs)
        if type(value) is not dict or value.get("ok") is not True:
            raise PreparedSnapshotError("SQLITE_CAPTURE_WORKER_NOT_VERIFIED")
        _check(self.deadline)
        return value

    def finish(self):
        _check(self.deadline)
        code = self.process.wait(timeout=max(0.0, self.deadline - time.monotonic()))
        if code != 0 or self.process.stdout.read(1):
            raise PreparedSnapshotError("SQLITE_CAPTURE_WORKER_NOT_VERIFIED")
        _check(self.deadline)

    def close(self):
        if self.validation_worker is not None:
            self.validation_worker.close()
        if self.process.poll() is None:
            # Only this owned stdlib worker exists; it never spawns descendants.
            self.process.kill()
        self.process.wait(timeout=1.0)
        for handle in (self.process.stdin, self.process.stdout):
            if handle is not None:
                handle.close()


def _run_capture_worker(*, source_parent_fd, expected_source_origin, snapshot_parent_fd, snapshot_fd,
                        source_name, operation_id, proposal_sha256, capture_id, deadline,
                        snapshot_byte_limit=MAX_SNAPSHOT_BYTES):
    _check(deadline)
    worker_path = Path(__file__).with_name("recovery_sqlite_capture_worker.py")
    if sys.platform != "linux" or not Path("/proc/self/fd").is_dir():
        raise PreparedSnapshotError("SOURCE_CONNECTION_BINDING_UNAVAILABLE")
    from engines.data_vault_engine import CRITICAL_TABLES
    binding = {"operation_id": operation_id, "proposal_sha256": proposal_sha256,
               "capture_id": capture_id, "deadline": deadline}
    process = subprocess.Popen(
        [sys.executable, "-I", "-S", "-u", str(worker_path), "--g3-capture-worker"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        close_fds=True, pass_fds=(source_parent_fd, snapshot_parent_fd, snapshot_fd),
        env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
    )
    bounded = snapshot_byte_limit != MAX_SNAPSHOT_BYTES
    if bounded:
        binding["snapshot_byte_limit"] = snapshot_byte_limit
    owner = _CaptureWorker(process, binding, deadline)
    try:
        response = owner.exchange({
            "schema": "G3_CAPTURE_WORKER_V2" if bounded else "G3_CAPTURE_WORKER_V1", **binding,
            "source_parent_fd": source_parent_fd, "expected_source_origin": list(expected_source_origin),
            "source_name": source_name, "snapshot_parent_fd": snapshot_parent_fd,
            "snapshot_fd": snapshot_fd, "critical_tables": list(CRITICAL_TABLES),
        })
        owner.finish()
        owner.prepared_response = response
        owner.critical_tables = list(CRITICAL_TABLES)
        return owner, response
    except BaseException:
        owner.close()
        raise


def _validate_capture_worker(owner):
    _check(owner.deadline)
    worker_path = Path(__file__).with_name("recovery_sqlite_capture_worker.py")
    process = subprocess.Popen(
        [sys.executable, "-I", "-S", "-u", str(worker_path), "--g3-validate-worker"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        close_fds=True, pass_fds=(owner.snapshot_parent_fd, owner.snapshot_fd),
        env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
    )
    validator = _CaptureWorker(process, owner.binding, owner.deadline)
    owner.validation_worker = validator
    try:
        response = validator.exchange({"schema": ("G3_VALIDATE_WORKER_V2"
            if "snapshot_byte_limit" in owner.binding else "G3_VALIDATE_WORKER_V1"),
            "prepared_receipt": owner.prepared_response,
            "snapshot_parent_fd": owner.snapshot_parent_fd, "snapshot_fd": owner.snapshot_fd,
            "critical_tables": owner.critical_tables})
        validator.finish()
        return response
    except BaseException:
        validator.close()
        raise


def _worker_receipt(value, owner, *, phase, source_info, capture_info):
    common_keys = {"schema", "ok", "phase", "worker_pid", "operation_id", "proposal_sha256",
                   "capture_id", "deadline", "source_binding", "source_origin",
                   "snapshot_identity", "sqlite_backup_calls", "source_attested_before_sql",
                   "destination_attested_before_sql", "source_connection_retained_through_backup",
                   "source_connections_closed", "snapshot_writers_closed", "authorized_source_fd_opened_in_worker",
                   "hostile_wal_namespace_certified"}
    bounded = "snapshot_byte_limit" in owner.binding
    if bounded:
        common_keys.add("snapshot_byte_limit")
    extra = ({"integrity_attested_before_sql", "sha256", "tables_included", "records_summary"}
             if phase == "VALIDATED" else set())
    if (type(value) is not dict or set(value) != common_keys | extra
            or value["schema"] != ("G3_CAPTURE_WORKER_RECEIPT_V2" if bounded else _WORKER_SCHEMA) or value["ok"] is not True
            or value["phase"] != phase or type(value["worker_pid"]) is not int
            or value["worker_pid"] != (owner.validation_worker.process.pid if phase == "VALIDATED" else owner.process.pid)
            or any(type(value[k]) is not type(v) or value[k] != v for k, v in owner.binding.items())
            or value["source_binding"] != SOURCE_BINDING
            or type(value["source_origin"]) is not list or len(value["source_origin"]) != 6
            or any(type(v) is not int for v in value["source_origin"])
            or type(value["snapshot_identity"]) is not list or len(value["snapshot_identity"]) != 9
            or any(type(v) is not int for v in value["snapshot_identity"])
            or value["source_origin"] != list(state._capture_identity(source_info)[:6])
            or value["snapshot_identity"] != list(state._capture_identity(capture_info))
            or type(value["sqlite_backup_calls"]) is not int or value["sqlite_backup_calls"] != 1
            or any(value[k] is not True for k in ("source_attested_before_sql",
                "destination_attested_before_sql", "source_connection_retained_through_backup",
                "source_connections_closed", "snapshot_writers_closed", "authorized_source_fd_opened_in_worker"))
            or value["hostile_wal_namespace_certified"] is not False):
        raise PreparedSnapshotError("INVALID_SQLITE_CAPTURE_WORKER_RECEIPT")
    if phase == "VALIDATED":
        if (value["integrity_attested_before_sql"] is not True
                or type(value["sha256"]) is not str or not state.HEX.fullmatch(value["sha256"])
                or type(value["tables_included"]) is not list or len(value["tables_included"]) > MAX_TABLES
                or any(type(v) is not str for v in value["tables_included"])
                or type(value["records_summary"]) is not dict
                or any(type(v) is not int or v < 0 for v in value["records_summary"].values())):
            raise PreparedSnapshotError("INVALID_SQLITE_CAPTURE_WORKER_RECEIPT")
    return value


class SqliteSnapshotProducer:
    """Single-use owner of the capture FD and its exact pathname binding.

    Caller must close() after the engine finishes (or use a context manager).
    close() releases handles only; it never removes captured or published bytes.
    """
    def __init__(self, *, source: Path, publication: Path, operation_id: str,
                 proposal_sha256: str, snapshot_timeout=15.0, snapshot_method="sqlite_backup",
                 snapshot_byte_limit=MAX_SNAPSHOT_BYTES):
        if type(snapshot_method) is not str or snapshot_method != "sqlite_backup":
            raise PreparedSnapshotError("UNSUPPORTED_PREPARED_SQLITE_METHOD")
        if (type(snapshot_byte_limit) is not int
                or not 0 < snapshot_byte_limit <= MAX_SNAPSHOT_BYTES):
            raise PreparedSnapshotError("INVALID_SQLITE_SNAPSHOT_BYTE_LIMIT")
        state._path(source)
        state._path(publication)
        if (type(operation_id) is not str or not state.REF.fullmatch(operation_id)
                or type(proposal_sha256) is not str or not state.HEX.fullmatch(proposal_sha256)
                or type(snapshot_timeout) not in (int, float)
                or not math.isfinite(snapshot_timeout) or snapshot_timeout <= 0
                or source == publication or source.is_relative_to(publication)
                or publication.is_relative_to(source)):
            raise PreparedSnapshotError("INVALID_PREPARED_SQLITE_PRODUCER")
        self.source, self.publication = source, publication
        self.operation_id, self.proposal_sha256 = operation_id, proposal_sha256
        self.snapshot_timeout = snapshot_timeout
        self.snapshot_byte_limit = snapshot_byte_limit
        self.producer_id = uuid.uuid4().hex
        self._capture = None
        self._attempted = self._validated = self._closed = False
        self._pfd = self._wfd = self._fd = None
        self._worker = None
        self._workspace = self._backup_name = None
        self._absolute_deadline = self._deadline = None
        self._result = {"ok": False, "backup_created": False, "prepare_completed": False,
                        "sqlite_capture_attempted": False,
                        "sqlite_disposition": "NOT_INVOKED",
                        "recapture_attempted": False, "source_binding": None,
                        "production_source_connection_bound": False}

    @property
    def result(self):
        return dict(self._result)

    def _open_publication(self):
        self._pfd = state._directory(self.publication)
        info = os.fstat(self._pfd)
        if info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise PreparedSnapshotError("PRIVATE_SQLITE_PUBLICATION_REQUIRED")
        self._publication_identity = (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid)

    def _namespace(self):
        check_fd = state._directory(self.publication)
        try:
            info = os.fstat(check_fd)
            if ((info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid)
                    != self._publication_identity):
                raise PreparedSnapshotError("SQLITE_PUBLICATION_NAMESPACE_CHANGED")
        finally:
            os.close(check_fd)
        info = os.stat(self._workspace, dir_fd=self._pfd, follow_symlinks=False)
        actual = os.fstat(self._wfd)
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_mode & 0o077 or (info.st_dev, info.st_ino) != (actual.st_dev, actual.st_ino)):
            raise PreparedSnapshotError("PREPARED_SQLITE_NAMESPACE_CHANGED")

    def _same_capture(self, *, expected=None, name="snapshot.partial", parent=None):
        self._namespace()
        parent = self._wfd if parent is None else parent
        opened = os.fstat(self._fd)
        state._regular(opened)
        named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        state._same(opened, named)
        if expected is not None and state._capture_identity(opened) != expected:
            raise PreparedSnapshotError("PREPARED_SQLITE_CAPTURE_CHANGED")
        if opened.st_mode & 0o077 or opened.st_uid != os.geteuid() or not 0 < opened.st_size <= self.snapshot_byte_limit:
            raise PreparedSnapshotError("INVALID_PREPARED_SQLITE_FILE")
        return opened


    def prepare(self, absolute_deadline):
        if self._closed or self._attempted:
            raise PreparedSnapshotError("SECOND_SQLITE_CAPTURE_DENIED")
        self._attempted = True
        self._absolute_deadline = absolute_deadline
        _check(absolute_deadline)
        self._deadline = min(absolute_deadline, time.monotonic() + self.snapshot_timeout)
        try:
            state._native()
            self._open_publication()
            self._workspace = ".prepared-sqlite-" + uuid.uuid4().hex
            os.mkdir(self._workspace, 0o700, dir_fd=self._pfd)
            self._wfd = os.open(self._workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=self._pfd)
            self._fd = os.open("snapshot.partial", os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                               0o600, dir_fd=self._wfd)
            initial = os.fstat(self._fd)
            source_parent = state._directory(self.source.parent)
            try:
                # Metadata observation only: caller never opens/closes a main
                # source DB FD, preserving locks of any caller SQLite connection.
                self._source_info = os.stat(self.source.name, dir_fd=source_parent, follow_symlinks=False)
                state._regular(self._source_info)
                self._result.update(sqlite_capture_attempted=True,
                    sqlite_disposition="CAPTURE_ATTEMPT_PRESERVE_AND_DO_NOT_RETRY")
                capture_id = uuid.uuid4().hex
                self._worker, response = _run_capture_worker(
                    source_parent_fd=source_parent,
                    expected_source_origin=state._capture_identity(self._source_info)[:6],
                    snapshot_parent_fd=self._wfd, snapshot_fd=self._fd,
                    source_name=self.source.name, operation_id=self.operation_id,
                    proposal_sha256=self.proposal_sha256, capture_id=capture_id,
                    deadline=self._deadline,
                    **({"snapshot_byte_limit": self.snapshot_byte_limit}
                       if self.snapshot_byte_limit != MAX_SNAPSHOT_BYTES else {}))
                captured = self._same_capture()
                _worker_receipt(response, self._worker, phase="PREPARED",
                                source_info=self._source_info, capture_info=captured)
                if (captured.st_dev, captured.st_ino) != (initial.st_dev, initial.st_ino):
                    raise PreparedSnapshotError("PREPARED_SQLITE_CAPTURE_CHANGED")
                readonly_fd = os.open("snapshot.partial", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                      dir_fd=self._wfd)
                try:
                    state._same(captured, os.fstat(readonly_fd))
                except BaseException:
                    os.close(readonly_fd)
                    raise
                # Worker has closed destination connection and its writer before
                # PREPARED. Parent closes its duplicate writer only now.
                os.close(self._fd)
                self._fd = readonly_fd
                self._worker.snapshot_parent_fd = self._wfd
                self._worker.snapshot_fd = self._fd
                _check(self._deadline)
                self._capture = state.PreparedSqliteCapture(
                    self.operation_id, self.proposal_sha256, self.producer_id, capture_id,
                    self._fd, state._capture_identity(captured))
                self._result.update(prepare_completed=True,
                    source_binding=SOURCE_BINDING, production_source_connection_bound=True,
                    worker_prepared_receipt=response,
                    sqlite_disposition="CAPTURED_UNVALIDATED_PRESERVED_DO_NOT_RETRY")
                return self._capture
            finally:
                # Only a directory FD belongs to the caller process here.
                os.close(source_parent)
        except BaseException:
            self._result["ok"] = False
            self._result.setdefault("code", "SQLITE_PREPARATION_NOT_VERIFIED")
            raise


    def validate(self, prepared, absolute_deadline):
        if self._closed or self._validated:
            raise PreparedSnapshotError("FOREIGN_OR_STALE_PREPARED_SQLITE_CAPTURE")
        # Every validation attempt is terminal, including a foreign capability.
        self._validated = True
        if (self._capture is None
                or prepared is not self._capture or type(prepared) is not state.PreparedSqliteCapture
                or prepared.operation_id != self.operation_id
                or prepared.proposal_sha256 != self.proposal_sha256
                or prepared.producer_id != self.producer_id
                or prepared.snapshot_fd != self._fd
                or type(absolute_deadline) not in (int, float)
                or absolute_deadline != self._absolute_deadline):
            raise PreparedSnapshotError("FOREIGN_OR_STALE_PREPARED_SQLITE_CAPTURE")
        try:
            _check(self._deadline)
            before = self._same_capture(expected=prepared.snapshot_identity)
            response = _validate_capture_worker(self._worker)
            _worker_receipt(response, self._worker, phase="VALIDATED",
                            source_info=self._source_info, capture_info=before)
            self._result["worker_validation_receipt"] = response
            tables, counts = response["tables_included"], response["records_summary"]
            self._same_capture(expected=prepared.snapshot_identity)
            digest = state._hash_fd(self._fd, self._deadline, MAX_SNAPSHOT_BYTES)
            if digest != response["sha256"]:
                raise PreparedSnapshotError("PREPARED_SQLITE_HASH_MISMATCH")
            self._same_capture(expected=prepared.snapshot_identity)
            self._worker.close()
            self._worker = None
            _check(self._deadline)
            name = "database_" + uuid.uuid4().hex + ".db"
            manifest_name = name[:-3] + ".json"
            manifest = {"schema": ("PREPARED_SQLITE_CAPTURE_V2"
                        if "snapshot_byte_limit" in response else "PREPARED_SQLITE_CAPTURE_V1"), "valid": True,
                        "sha256": digest, "size_bytes": before.st_size,
                        "operation_id": self.operation_id, "proposal_sha256": self.proposal_sha256,
                        "source_binding": SOURCE_BINDING, "production_source_connection_bound": True,
                        "source_origin": list(state._capture_identity(self._source_info)[:6]),
                        "source_authorized_in_worker": True,
                        "capture_worker_pid": self._result["worker_prepared_receipt"]["worker_pid"],
                        "validation_worker_pid": response["worker_pid"],
                        "hostile_wal_namespace_certified": False,
                        "capture_id": prepared.capture_id, "snapshot_method": "sqlite_backup",
                        "tables_included": tables, "records_summary": counts}
            if "snapshot_byte_limit" in response:
                manifest["snapshot_byte_limit"] = response["snapshot_byte_limit"]
            raw = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            if len(raw) > MAX_MANIFEST_BYTES:
                raise PreparedSnapshotError("SQLITE_METADATA_BUDGET")
            manifest_fd = os.open("manifest.partial", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                  0o600, dir_fd=self._wfd)
            try:
                with os.fdopen(manifest_fd, "wb") as handle:
                    handle.write(raw)
                    handle.flush()
                    os.fsync(handle.fileno())
                    manifest_info = os.fstat(handle.fileno())
            except BaseException:
                # Only owned metadata; captured snapshot remains preserved.
                raise
            self._same_capture(expected=prepared.snapshot_identity)
            _check(self._deadline)
            # Both publications refuse replacement. Readers discover the DB last.
            os.link("manifest.partial", manifest_name, src_dir_fd=self._wfd, dst_dir_fd=self._pfd,
                    follow_symlinks=False)
            linked_manifest = os.stat(manifest_name, dir_fd=self._pfd, follow_symlinks=False)
            if (linked_manifest.st_nlink != 2
                    or state._capture_identity(linked_manifest)[:3] != state._capture_identity(manifest_info)[:3]
                    or state._capture_identity(linked_manifest)[4:8] != state._capture_identity(manifest_info)[4:8]
                    or state._capture_identity(linked_manifest) != state._capture_identity(
                        os.stat("manifest.partial", dir_fd=self._wfd, follow_symlinks=False))):
                raise PreparedSnapshotError("SQLITE_MANIFEST_PUBLICATION_CHANGED")
            os.unlink("manifest.partial", dir_fd=self._wfd)
            published_manifest = os.stat(manifest_name, dir_fd=self._pfd, follow_symlinks=False)
            state._regular(published_manifest)
            if state._capture_identity(published_manifest)[:-1] != state._capture_identity(manifest_info)[:-1]:
                raise PreparedSnapshotError("SQLITE_MANIFEST_PUBLICATION_CHANGED")
            self._same_capture(expected=prepared.snapshot_identity)
            _check(self._deadline)
            os.link("snapshot.partial", name, src_dir_fd=self._wfd, dst_dir_fd=self._pfd,
                    follow_symlinks=False)
            self._backup_name = name
            self._result.update(backup_created=True, backup_file=name, sha256=digest,
                                manifest=manifest_name,
                                sqlite_disposition="PUBLISHED_PRESERVE_AND_DO_NOT_RETRY")
            linked = os.fstat(self._fd)
            named = os.stat(name, dir_fd=self._pfd, follow_symlinks=False)
            # Model EXACT link transition: same inode/content/owner and 1->2 links.
            if (state._capture_identity(linked)[:3] != prepared.snapshot_identity[:3]
                    or state._capture_identity(linked)[4:8] != prepared.snapshot_identity[4:8]
                    or linked.st_nlink != 2 or linked.st_ctime_ns < before.st_ctime_ns
                    or state._capture_identity(linked) != state._capture_identity(named)
                    or state._capture_identity(linked) != state._capture_identity(
                        os.stat("snapshot.partial", dir_fd=self._wfd, follow_symlinks=False))):
                raise PreparedSnapshotError("SQLITE_PUBLICATION_IDENTITY_CHANGED")
            os.unlink("snapshot.partial", dir_fd=self._wfd)
            published = self._same_capture(name=name, parent=self._pfd)
            if (state._capture_identity(published)[:-1] != prepared.snapshot_identity[:-1]
                    or published.st_ctime_ns < linked.st_ctime_ns):
                raise PreparedSnapshotError("SQLITE_PUBLICATION_IDENTITY_CHANGED")
            # Verify the SAME retained capture after its namespace transition.
            if state._hash_fd(self._fd, self._deadline, MAX_SNAPSHOT_BYTES) != digest:
                raise PreparedSnapshotError("SQLITE_PUBLICATION_HASH_CHANGED")
            self._same_capture(expected=state._capture_identity(published), name=name, parent=self._pfd)
            manifest_check = os.open(manifest_name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                     dir_fd=self._pfd)
            try:
                state._same(published_manifest, os.fstat(manifest_check))
                with os.fdopen(os.dup(manifest_check), "rb") as handle:
                    _check(self._deadline)
                    if handle.read(MAX_MANIFEST_BYTES + 1) != raw:
                        raise PreparedSnapshotError("SQLITE_MANIFEST_PUBLICATION_CHANGED")
                state._same(published_manifest, os.fstat(manifest_check))
                state._same(published_manifest, os.stat(manifest_name, dir_fd=self._pfd, follow_symlinks=False))
            finally:
                os.close(manifest_check)
            os.fsync(self._wfd)
            os.fsync(self._pfd)
            _check(self._deadline)
            self._result.update(ok=True, code="SAME_CAPTURE_VALIDATED_AND_PUBLISHED",
                sqlite_disposition="VALIDATED_PUBLISHED_PRESERVE_DO_NOT_RETRY")
            return state.ValidatedSqliteCapture(
                prepared, state.SqliteReceipt(self.operation_id, digest, True),
                state._capture_identity(published), self.publication, self._pfd, name)
        except BaseException:
            self._result.update(ok=False, code="SQLITE_VALIDATION_NOT_VERIFIED")
            raise

    def close(self):
        if not self._closed:
            self._closed = True
            if self._worker is not None:
                try:
                    self._worker.close()
                except (OSError, subprocess.TimeoutExpired):
                    self._result["owned_worker_cleanup_failed"] = True
                finally:
                    self._worker = None
            for key in ("_fd", "_wfd", "_pfd"):
                fd = getattr(self, key)
                if fd is not None:
                    os.close(fd)
                    setattr(self, key, None)

    def __enter__(self):
        if self._closed:
            raise PreparedSnapshotError("PREPARED_SQLITE_PRODUCER_CLOSED")
        return self

    def __exit__(self, *_exc):
        self.close()
