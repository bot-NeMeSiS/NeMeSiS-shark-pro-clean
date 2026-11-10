"""Explicit one-use legacy-marker transition; never part of a scheduled job.

Approval and owner cessation are externally reviewed preconditions, not facts
proved by an advisory lock or by the reference strings accepted here.
"""
from __future__ import annotations

import ctypes
from datetime import datetime
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

try:
    import fcntl
except ImportError:
    fcntl = None

MARKER = "scheduler.lock"
FIELDS = {"sha", "instance", "root_device", "root_inode", "device", "inode", "mtime_ns", "digest"}


class TransitionError(ValueError):
    """Only closed diagnostic codes may be returned by the CLI."""


def validate_expected(value):
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise TransitionError("INVALID_EXPECTATION_FIELDS")
    for key in ("root_device", "root_inode", "device", "inode", "mtime_ns"):
        if type(value[key]) is not int or value[key] <= 0:
            raise TransitionError("INVALID_EXPECTATION_IDENTITY")
    if not isinstance(value["sha"], str) or not re.fullmatch(r"[0-9a-f]{40}", value["sha"]):
        raise TransitionError("INVALID_EXPECTATION_SHA")
    if not isinstance(value["digest"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["digest"]):
        raise TransitionError("INVALID_EXPECTATION_DIGEST")
    if not isinstance(value["instance"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", value["instance"]):
        raise TransitionError("INVALID_EXPECTATION_INSTANCE")
    return dict(value)


def _context(expected, context):
    if (context.get("sha") != expected["sha"] or context.get("instance") != expected["instance"]):
        raise TransitionError("RUNTIME_CONTEXT_CHANGED")


def _references(cessation, authorization):
    for value in (cessation, authorization):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,160}", value):
            raise TransitionError("EXTERNAL_REVIEW_AND_AUTHORIZATION_REQUIRED")


def _supported():
    if sys.platform != "linux" or fcntl is None:
        raise TransitionError("LINUX_CONFINED_OPERATION_REQUIRED")


def _open_root(root, expected):
    _supported()
    root = Path(root)
    if not root.is_absolute() or ".." in root.parts or str(root).startswith("//"):
        raise TransitionError("UNSAFE_STORAGE_ROOT")
    fd = os.open(root.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for part in root.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = child
        s = os.fstat(fd)
        if (s.st_dev, s.st_ino) != (expected["root_device"], expected["root_inode"]):
            raise TransitionError("STORAGE_ROOT_CHANGED")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _open_marker(parent, name):
    return os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)


def _root_still_named(root, expected):
    fd = _open_root(root, expected)
    os.close(fd)


def _checked(fd, parent, name, expected):
    s = os.fstat(fd)
    named = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if (not stat.S_ISREG(s.st_mode) or s.st_nlink != 1 or not stat.S_ISREG(named.st_mode)
            or (s.st_dev, s.st_ino) != (named.st_dev, named.st_ino)):
        raise TransitionError("UNVERIFIED_MARKER_IDENTITY")
    if (s.st_dev, s.st_ino, s.st_mtime_ns) != (expected["device"], expected["inode"], expected["mtime_ns"]):
        raise TransitionError("MARKER_CHANGED")
    if not 0 < s.st_size <= 4096:
        raise TransitionError("INVALID_MARKER_SIZE")
    os.lseek(fd, 0, os.SEEK_SET)
    raw = os.read(fd, 4097)
    after = os.fstat(fd)
    if (s.st_size, s.st_mtime_ns, s.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise TransitionError("MARKER_CHANGED_DURING_READ")
    if hashlib.sha256(raw).hexdigest() != expected["digest"]:
        raise TransitionError("MARKER_DIGEST_CHANGED")
    try:
        marker = json.loads(raw)
        valid = (isinstance(marker, dict) and set(marker) == {"job_id", "pid", "locked_at_madrid"}
                 and isinstance(marker["job_id"], str) and 0 < len(marker["job_id"]) <= 160
                 and type(marker["pid"]) is int and marker["pid"] > 0
                 and isinstance(marker["locked_at_madrid"], str)
                 and datetime.fromisoformat(marker["locked_at_madrid"]).utcoffset() is not None)
    except (ValueError, TypeError, KeyError, UnicodeError):
        valid = False
    if not valid:
        raise TransitionError("NOT_A_SUPPORTED_LEGACY_MARKER")
    return {"pid": marker["pid"], "locked_at_madrid": marker["locked_at_madrid"],
            "bytes": len(raw), "digest": expected["digest"], "inode": s.st_ino, "device": s.st_dev}


def _archive_name(expected):
    return "scheduler.%d.%s.legacy.json" % (expected["inode"], expected["digest"])


def inspect(root, expected, *, context):
    """Read metadata/one bounded legacy marker; no flock or filesystem writes."""
    expected = validate_expected(expected)
    _context(expected, context)
    parent = _open_root(root, expected)
    fd = None
    try:
        fd = _open_marker(parent, MARKER)
        marker = _checked(fd, parent, MARKER, expected)
        return {"operation": "READ_ONLY_PLAN", "expected": expected, "marker": marker,
                "preserved_destination": _archive_name(expected),
                "owner_cessation": "REQUIRES_EXTERNAL_REVIEW_NOT_INFERRED_FROM_PID_AGE_OR_FLOCK",
                "authorization": "REQUIRES_NEW_SPECIFIC_HUMAN_DECISION",
                "next_execution": "EXISTING_NATURAL_SCHEDULE_ONLY",
                "rollback": "ONLY_IF_ACTIVE_MARKER_ABSENT; NEVER_REPLACE_A_NEW_OWNER",
                "business_execution_certified": False, "production_certified": False}
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def _rename_function():
    _supported()
    library = ctypes.CDLL(None, use_errno=True)
    function = getattr(library, "renameat2", None)
    if function is None:
        raise TransitionError("ATOMIC_NO_REPLACE_RENAME_UNAVAILABLE")
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    return function


def _rename(function, parent, source, destination, root):
    # renameat2 has no stdlib equivalent for RENAME_NOREPLACE. Preserve the
    # standard Python rename audit boundary before the native operation. Both
    # syscall names remain anchored to the already verified directory FD.
    sys.audit("os.rename", str(Path(root) / source), str(Path(root) / destination), parent, parent)
    if function(parent, source.encode("ascii"), parent, destination.encode("ascii"), 1):
        code = ctypes.get_errno()
        if code == errno.EEXIST:
            raise TransitionError("DESTINATION_ALREADY_EXISTS_NO_REPLACE")
        raise TransitionError("ATOMIC_RENAME_FAILED")


def transition(root, expected, *, context, cessation_reference, authorization_reference, rollback=False):
    """Execute only after external human review of this exact plan and scope.

    Reference strings are audit bindings, NOT authentication or proof of owner
    cessation. The operator must verify those preconditions before calling.
    """
    expected = validate_expected(expected)
    _context(expected, context)
    _references(cessation_reference, authorization_reference)
    rename = _rename_function()
    parent = _open_root(root, expected)
    fd = None
    renamed = False
    try:
        source = _archive_name(expected) if rollback else MARKER
        fd = _open_marker(parent, source)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise TransitionError("MARKER_BUSY") from None
        marker = _checked(fd, parent, source, expected)
        _context(expected, context)
        _checked(fd, parent, source, expected)
        _root_still_named(root, expected)
        os.fsync(fd)
        destination = MARKER if rollback else _archive_name(expected)
        _rename(rename, parent, source, destination, root)
        renamed = True
        # The original bytes/inode survive the atomic rename. Never overwrite,
        # rewrite, unlink, replace a new marker, run a job, or retry automatically.
        os.fsync(parent)
        _root_still_named(root, expected)
        _checked(fd, parent, destination, expected)
        return {"operation": "ROLLBACK_TO_LEGACY_BLOCKED" if rollback else "LEGACY_MARKER_PRESERVED",
                "marker": marker, "preserved_destination": destination,
                "cessation_reference": cessation_reference, "authorization_reference": authorization_reference,
                "next_execution": "EXISTING_NATURAL_SCHEDULE_ONLY", "automatic_retry": False,
                "business_execution_certified": False, "production_certified": False}
    except (OSError, TransitionError) as exc:
        if renamed:
            raise TransitionError("RENAMED_BUT_POSTCHECK_INCOMPLETE_PRESERVE_AND_REVIEW") from exc
        raise
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)
