"""Process-owned POSIX scheduler locks; legacy markers are never reclaimed.

The inode stays in place after release. JSON records the last owner, while the
open descriptor and advisory OS lock establish current ownership. This protocol
does not migrate an older exclusive-create lock or certify storage semantics.
"""
from __future__ import annotations

import errno
import json
import os
from pathlib import Path
import stat
import threading

try:
    import fcntl
except ImportError:  # Windows keeps the conservative exclusive-create policy.
    fcntl = None

PROTOCOL = "nemesis-companyos-flock-v1"
_owners: dict[str, tuple[int, int, str]] = {}
_guard = threading.RLock()


class LegacyLock(Exception):
    def __init__(self, payload):
        self.payload = payload if isinstance(payload, dict) else {}


def supported() -> bool:
    return fcntl is not None and os.name == "posix"


def _key(path: Path) -> str:
    return os.path.abspath(path)


def _same_inode(path: Path, fd: int) -> bool:
    actual, named = os.fstat(fd), path.lstat()
    return (stat.S_ISREG(actual.st_mode) and actual.st_nlink == 1
            and stat.S_ISREG(named.st_mode)
            and (actual.st_dev, actual.st_ino) == (named.st_dev, named.st_ino))


def _read(fd: int) -> dict:
    os.lseek(fd, 0, os.SEEK_SET)
    raw = os.read(fd, 4097)
    if len(raw) > 4096:
        raise ValueError("scheduler_lock_marker_too_large")
    value = json.loads(raw)
    return value if isinstance(value, dict) else {}


def acquire(path: Path, job_id: str, now_iso: str) -> tuple[bool, dict]:
    """Nonblocking acquisition. A legacy/malformed marker is read, never changed."""
    with _guard:
        return _acquire(path, job_id, now_iso)


def _acquire(path: Path, job_id: str, now_iso: str) -> tuple[bool, dict]:
    fd = None
    retained = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
        try:
            fd = os.open(path, flags | os.O_CREAT | os.O_EXCL, 0o600)
            created = True
        except FileExistsError:
            fd = os.open(path, flags)
            created = False
        if not _same_inode(path, fd):
            return False, {"state": "LOCK_UNVERIFIED"}
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EAGAIN, errno.EACCES):
                return False, {"locked": True}
            raise
        if not _same_inode(path, fd):
            return False, {"state": "LOCK_UNVERIFIED"}
        if not created:
            try:
                existing = _read(fd)
            except (ValueError, UnicodeError):
                raise LegacyLock({}) from None
            if (existing.get("lock_protocol") != PROTOCOL
                    or not isinstance(existing.get("job_id"), str) or not existing["job_id"]
                    or type(existing.get("pid")) is not int or existing["pid"] <= 0
                    or not isinstance(existing.get("locked_at_madrid"), str)):
                raise LegacyLock(existing)
        payload = {"lock_protocol": PROTOCOL, "job_id": job_id,
                   "locked_at_madrid": now_iso, "pid": os.getpid()}
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf8")
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        pending = memoryview(raw)
        while pending:
            written = os.write(fd, pending)
            if written <= 0:
                raise OSError("scheduler_lock_short_write")
            pending = pending[written:]
        os.fsync(fd)
        if not _same_inode(path, fd):
            return False, {"state": "LOCK_UNVERIFIED"}
        with _guard:
            _owners[_key(path)] = (fd, os.getpid(), job_id)
        retained = True
        return True, payload
    except OSError:
        return False, {"state": "LOCK_UNVERIFIED"}
    finally:
        if fd is not None and not retained:
            os.close(fd)


def owned(path: Path, job_id: str) -> bool:
    with _guard:
        owner = _owners.get(_key(path))
        if owner is None or owner[1:] != (os.getpid(), job_id):
            return False
        fd = owner[0]
        try:
            marker = _read(fd)
            return (_same_inode(path, fd) and marker.get("lock_protocol") == PROTOCOL
                    and marker.get("job_id") == job_id and marker.get("pid") == os.getpid())
        except (OSError, ValueError, UnicodeError):
            return False


def release(path: Path, job_id: str) -> None:
    with _guard:
        key = _key(path)
        owner = _owners.get(key)
        if owner is not None and owner[1:] == (os.getpid(), job_id):
            del _owners[key]
            # Closing releases our descriptor; never unlink or unlock an inode
            # another process could still be using through an inherited handle.
            os.close(owner[0])


def _after_fork() -> None:
    global _guard
    # A child must not keep the parent's open-file-description lock alive, or
    # release it with LOCK_UN. Closing its duplicate preserves the parent's lock.
    for fd, _pid, _job_id in _owners.values():
        os.close(fd)
    _owners.clear()
    _guard = threading.RLock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(before=lambda: _guard.acquire(),
                        after_in_parent=lambda: _guard.release(),
                        after_in_child=_after_fork)
