"""Native restores of a complete sealed SQLite set, under ONE B deadline.

No workspace admission, App activation, CLI, job or data permission is supplied
here. Caller must own an admitted private disposable workspace. Failed files
are preserved; no retry, cleanup or new live-source snapshot is performed.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import os
import stat
from pathlib import Path
import subprocess
import sys
import time

from engines import recovery_non_sqlite_state as state
from engines import recovery_sqlite_set_contract as contract
from tools.recovery_sqlite_prepare import _CaptureWorker
from tools.recovery_sqlite_set_state import BoundSqliteSetStateBundle


class SqliteSetRestoreError(ValueError):
    """Closed restore codes without private paths or original exceptions."""


def _workspace_origin(info):
    # Child mkdir changes directory nlink/mtime/ctime. Bind stable namespace,
    # owner and privacy instead; regular SQLite files still require nlink==1.
    if (not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077
            or info.st_uid != os.geteuid()):
        raise SqliteSetRestoreError("PRIVATE_RESTORE_WORKSPACE_REQUIRED")
    return tuple(int(getattr(info, key)) for key in
                 ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid"))


@dataclass(frozen=True)
class RestoredMember:
    source_id: str
    capture_id: str
    relative: str
    fd: int
    identity: tuple[int, ...]
    worker_receipt: dict


@dataclass(frozen=True)
class RestoredSet:
    bundle: BoundSqliteSetStateBundle
    workspace: Path
    workspace_origin: tuple[int, ...]
    deadline: float
    members: tuple[RestoredMember, ...]

    def verify_before_app(self, deadline):
        if deadline != self.deadline:
            raise SqliteSetRestoreError("RESTORE_SET_DEADLINE_CHANGED")
        state._check_time(deadline)
        if type(self.bundle) is not BoundSqliteSetStateBundle:
            raise SqliteSetRestoreError("TYPED_BOUND_SQLITE_SET_REQUIRED")
        BoundSqliteSetStateBundle.__post_init__(self.bundle)
        contract.to_record(self.bundle.sqlite)
        if (type(self.members) is not tuple
                or any(type(m) is not RestoredMember for m in self.members)
                or tuple(m.source_id for m in self.members)
                   != tuple(m.source_id for m in self.bundle.sqlite.members)):
            raise SqliteSetRestoreError("INCOMPLETE_RESTORED_SQLITE_SET")
        root = state._directory(self.workspace)
        try:
            if _workspace_origin(os.fstat(root)) != self.workspace_origin:
                raise SqliteSetRestoreError("RESTORE_WORKSPACE_CHANGED")
            for restored, expected in zip(self.members, self.bundle.sqlite.members):
                state._check_time(deadline)
                relative = ("restoration-test.db" if expected.source_id == "principal"
                            else "sqlite/" + expected.source_id + ".db")
                if restored.relative != relative or restored.capture_id != expected.capture_id:
                    raise SqliteSetRestoreError("FOREIGN_RESTORED_SQLITE_MEMBER")
                parent = root
                extra = None
                try:
                    if expected.source_id != "principal":
                        extra = os.open("sqlite", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
                        parent = extra
                    name = relative.split("/")[-1]
                    info = os.stat(name, dir_fd=parent, follow_symlinks=False)
                    state._regular(info)
                    if (state._capture_identity(info) != restored.identity
                            or state._capture_identity(os.fstat(restored.fd)) != restored.identity
                            or info.st_size != expected.size_bytes or info.st_mode & 0o077
                            or info.st_uid != os.geteuid()
                            or state._hash_fd(restored.fd, deadline, expected.maximum_bytes) != expected.sha256):
                        raise SqliteSetRestoreError("RESTORED_SQLITE_MEMBER_CHANGED")
                    _receipt(restored.worker_receipt, self.bundle, expected, deadline,
                             destination_identity=restored.identity)
                    state._same(info, os.stat(name, dir_fd=parent, follow_symlinks=False))
                    state._same(info, os.fstat(restored.fd))
                finally:
                    if extra is not None:
                        os.close(extra)
            state._check_time(deadline)
        finally:
            os.close(root)


def _receipt(value, bundle, member, deadline, *, destination_identity, pid=None, source_identity=None):
    keys = {"schema", "ok", "operation_id", "proposal_sha256", "capture_id", "source_id",
            "deadline", "maximum_bytes", "size_bytes", "sha256", "worker_pid", "source_identity",
            "destination_identity", "integrity_attested_before_sql", "integrity_check_ok",
            "sealed_snapshot_copy_calls", "live_source_capture_calls"}
    if (type(value) is not dict or set(value) != keys
            or value["schema"] != "G3_RESTORE_MEMBER_RECEIPT_V1" or value["ok"] is not True
            or value["operation_id"] != bundle.plan.sqlite.operation_id
            or value["proposal_sha256"] != bundle.plan.sqlite.proposal_sha256
            or value["capture_id"] != member.capture_id or value["source_id"] != member.source_id
            or type(value["deadline"]) not in (int, float) or value["deadline"] != deadline
            or type(value["maximum_bytes"]) is not int or value["maximum_bytes"] != member.maximum_bytes
            or type(value["size_bytes"]) is not int or value["size_bytes"] != member.size_bytes
            or value["sha256"] != member.sha256
            or type(value["worker_pid"]) is not int or value["worker_pid"] <= 0
            or (pid is not None and value["worker_pid"] != pid)
            or type(value["source_identity"]) is not list or len(value["source_identity"]) != 9
            or any(type(v) is not int or v < 0 for v in value["source_identity"])
            or (source_identity is not None and value["source_identity"] != list(source_identity))
            or type(value["destination_identity"]) is not list
            or value["destination_identity"] != list(destination_identity)
            or value["integrity_attested_before_sql"] is not True
            or value["integrity_check_ok"] is not True
            or type(value["sealed_snapshot_copy_calls"]) is not int or value["sealed_snapshot_copy_calls"] != 1
            or type(value["live_source_capture_calls"]) is not int or value["live_source_capture_calls"] != 0):
        raise SqliteSetRestoreError("NATIVE_RESTORE_MEMBER_NOT_VERIFIED")


def _close_fds(descriptors):
    failed = False
    for fd in descriptors:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                failed = True
    if failed:
        raise SqliteSetRestoreError("RESTORE_SET_CLOSE_NOT_VERIFIED")


@contextmanager
def restore_all_members(*, bundle, workspace, deadline):
    """Yield retained native bindings only after every member is verified."""
    if type(bundle) is not BoundSqliteSetStateBundle:
        raise SqliteSetRestoreError("TYPED_BOUND_SQLITE_SET_REQUIRED")
    BoundSqliteSetStateBundle.__post_init__(bundle)
    state._check_time(deadline)
    if deadline - time.monotonic() > 300:
        raise SqliteSetRestoreError("RESTORE_SET_PHASE_BUDGET_EXCEEDED")
    state._path(workspace)
    for protected in (bundle.plan.sqlite.publication, bundle.plan.state.publication,
                      *(s.source for s in bundle.plan.sqlite.sources),
                      *(s.source for s in bundle.plan.state.scopes)):
        if (workspace == protected or workspace.is_relative_to(protected)
                or protected.is_relative_to(workspace)):
            raise SqliteSetRestoreError("RESTORE_SET_WORKSPACE_OVERLAP")
    state._native()
    if sys.platform != "linux" or not workspace.name.startswith(".isolated_restore_327_"):
        raise SqliteSetRestoreError("NATIVE_OWNED_RESTORE_WORKSPACE_REQUIRED")
    root = publication = auxiliary = None
    retained = []
    try:
        root = state._directory(workspace)
        info = os.fstat(root)
        if info.st_mode & 0o077 or info.st_uid != os.geteuid():
            raise SqliteSetRestoreError("PRIVATE_RESTORE_WORKSPACE_REQUIRED")
        origin = _workspace_origin(info)
        publication = state._directory(bundle.plan.sqlite.publication)
        # Exclusive child creation: never merge or replace a previous restore.
        os.mkdir("sqlite", 0o700, dir_fd=root)
        auxiliary = os.open("sqlite", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
        for member in bundle.sqlite.members:
            state._check_time(deadline)
            parent = root if member.source_id == "principal" else auxiliary
            name = "restoration-test.db" if member.source_id == "principal" else member.source_id + ".db"
            relative = name if parent == root else "sqlite/" + name
            source = output = None
            owner = None
            try:
                source = os.open(member.backup_file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=publication)
                source_identity = state._capture_identity(os.fstat(source))
                output = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                payload = {"schema": "G3_RESTORE_MEMBER_WORKER_V1",
                    "operation_id": bundle.plan.sqlite.operation_id,
                    "proposal_sha256": bundle.plan.sqlite.proposal_sha256,
                    "source_id": member.source_id, "capture_id": member.capture_id,
                    "deadline": deadline, "maximum_bytes": member.maximum_bytes,
                    "size_bytes": member.size_bytes, "sha256": member.sha256,
                    "backup_name": member.backup_file, "backup_parent_fd": publication,
                    "backup_fd": source, "destination_parent_fd": parent, "destination_fd": output}
                process = subprocess.Popen([sys.executable, "-I", "-S", "-u",
                    str(Path(__file__).with_name("recovery_sqlite_capture_worker.py")),
                    "--g3-restore-member-worker"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, close_fds=True, pass_fds=(publication, source, parent, output),
                    env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"})
                owner = _CaptureWorker(process, {}, deadline)
                receipt = owner.exchange(payload)
                owner.finish()
                destination_identity = state._capture_identity(os.fstat(output))
                _receipt(receipt, bundle, member, deadline, destination_identity=destination_identity,
                         pid=process.pid, source_identity=source_identity)
                if state._capture_identity(os.fstat(source)) != source_identity:
                    raise SqliteSetRestoreError("SEALED_SQLITE_SOURCE_CHANGED")
                retained.append(RestoredMember(member.source_id, member.capture_id, relative,
                                               output, destination_identity, receipt))
                output = None
            finally:
                try:
                    if owner is not None:
                        owner.close()
                finally:
                    _close_fds((source, output))
        restored = RestoredSet(bundle, workspace, origin, deadline, tuple(retained))
        restored.verify_before_app(deadline)
        yield restored
    finally:
        _close_fds(tuple(member.fd for member in retained) + (auxiliary, publication, root))
