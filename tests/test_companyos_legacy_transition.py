"""Operator transitions use disposable markers; never live storage or jobs."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

import pytest

from engines import companyos_legacy_transition as transition
from engines import companyos_scheduler_lock as scheduler_lock

CONTEXT = {"sha": "a" * 40, "instance": "synthetic-instance"}
POSIX = pytest.mark.skipif(sys.platform != "linux", reason="real Linux confined rename/flock required")


def _fixture(root):
    path = root / "scheduler.lock"
    path.write_text(json.dumps({"job_id": "synthetic-legacy", "pid": 58,
                               "locked_at_madrid": "2026-11-05T01:01:32+01:00"}))
    return path, _expected(root, path)


def _expected(root, path):
    r, s = root.stat(), path.lstat()
    return {**CONTEXT, "root_device": r.st_dev, "root_inode": r.st_ino,
            "device": s.st_dev, "inode": s.st_ino, "mtime_ns": s.st_mtime_ns,
            "digest": hashlib.sha256(path.read_bytes()).hexdigest()}


def _execute(root, expected, **options):
    return transition.transition(root, expected, context=CONTEXT,
                                 cessation_reference="synthetic-reviewed-cessation",
                                 authorization_reference="synthetic-authorization", **options)


@pytest.mark.parametrize("key,value", [("sha", "short"), ("digest", "bad"), ("instance", "../escape"),
                                        ("device", True), ("inode", 0), ("mtime_ns", -1),
                                        ("root_device", None), ("root_inode", False)])
def test_invalid_identity_cannot_reach_filesystem(key, value, monkeypatch):
    spec = {**CONTEXT, "root_device": 1, "root_inode": 2, "device": 1,
            "inode": 3, "mtime_ns": 4, "digest": "b" * 64}
    spec[key] = value
    monkeypatch.setattr(transition, "_open_root", lambda *a: pytest.fail("opened storage"))
    with pytest.raises(transition.TransitionError):
        transition.inspect(Path("unused"), spec, context=CONTEXT)


@pytest.mark.parametrize("references", [(None, "approval"), ("cessation", None), ("", "approval"),
                                           ("cessation", ""), ("cessation", "contains spaces")])
def test_execution_requires_both_external_references_before_storage(references, monkeypatch):
    spec = {**CONTEXT, "root_device": 1, "root_inode": 2, "device": 1,
            "inode": 3, "mtime_ns": 4, "digest": "b" * 64}
    monkeypatch.setattr(transition, "_open_root", lambda *a: pytest.fail("opened storage"))
    with pytest.raises(transition.TransitionError, match="EXTERNAL_REVIEW"):
        transition.transition(Path("unused"), spec, context=CONTEXT,
                              cessation_reference=references[0], authorization_reference=references[1])


@POSIX
def test_default_plan_is_read_only_and_does_not_acquire_flock(tmp_path):
    path, expected = _fixture(tmp_path)
    before = path.read_bytes(), path.stat().st_ctime_ns, list(tmp_path.iterdir())
    fd = os.open(path, os.O_RDONLY)
    try:
        transition.fcntl.flock(fd, transition.fcntl.LOCK_EX | transition.fcntl.LOCK_NB)
        result = transition.inspect(tmp_path, expected, context=CONTEXT)
        assert result["operation"] == "READ_ONLY_PLAN"
        assert result["owner_cessation"].startswith("REQUIRES_EXTERNAL_REVIEW")
        assert result["production_certified"] is False
        assert "job_id" not in result["marker"]
    finally:
        os.close(fd)
    assert (path.read_bytes(), path.stat().st_ctime_ns, list(tmp_path.iterdir())) == before


@POSIX
def test_transition_preserves_exact_inode_and_bytes_then_natural_protocol_can_acquire(tmp_path):
    path, expected = _fixture(tmp_path)
    raw = path.read_bytes()
    result = _execute(tmp_path, expected)
    archive = tmp_path / result["preserved_destination"]
    assert result["operation"] == "LEGACY_MARKER_PRESERVED"
    assert not path.exists()
    assert archive.read_bytes() == raw and archive.stat().st_ino == expected["inode"]
    assert archive.stat().st_mtime_ns == expected["mtime_ns"]
    assert result["business_execution_certified"] is False
    assert result["next_execution"] == "EXISTING_NATURAL_SCHEDULE_ONLY"
    # A synthetic invocation demonstrates compatibility, never a production job.
    try:
        assert scheduler_lock.acquire(path, "synthetic-next", "2026-11-10T22:00:00+01:00")[0]
        assert scheduler_lock.owned(path, "synthetic-next")
        assert archive.read_bytes() == raw
    finally:
        scheduler_lock.release(path, "synthetic-next")


@POSIX
def test_busy_current_descriptor_prevents_any_mutation(tmp_path):
    path, expected = _fixture(tmp_path)
    fd = os.open(path, os.O_RDONLY)
    try:
        transition.fcntl.flock(fd, transition.fcntl.LOCK_EX | transition.fcntl.LOCK_NB)
        with pytest.raises(transition.TransitionError, match="MARKER_BUSY"):
            _execute(tmp_path, expected)
    finally:
        os.close(fd)
    assert path.stat().st_ino == expected["inode"]
    assert list(tmp_path.iterdir()) == [path]


@POSIX
@pytest.mark.parametrize("kind", ["digest", "inode", "root", "context", "hardlink", "symlink", "protocol", "malformed"])
def test_changed_or_unverified_identity_is_preserved(tmp_path, kind):
    path, expected = _fixture(tmp_path)
    if kind == "digest": expected["digest"] = "0" * 64
    elif kind == "inode": expected["inode"] += 1
    elif kind == "root": expected["root_inode"] += 1
    elif kind == "context": expected["sha"] = "c" * 40
    elif kind == "hardlink": os.link(path, tmp_path / "other")
    elif kind == "symlink":
        path.rename(tmp_path / "original")
        path.symlink_to(tmp_path / "original")
    elif kind == "protocol":
        path.write_text(json.dumps({"lock_protocol": scheduler_lock.PROTOCOL, "job_id": "current",
                                    "pid": os.getpid(), "locked_at_madrid": "2026-11-10T22:00:00+01:00"}))
        expected = _expected(tmp_path, path)
    elif kind == "malformed":
        path.write_bytes(b"{")
        expected = _expected(tmp_path, path)
    before = path.read_bytes()
    with pytest.raises((transition.TransitionError, OSError)):
        _execute(tmp_path, expected)
    assert path.read_bytes() == before
    assert not (tmp_path / transition._archive_name(expected)).exists()


@POSIX
def test_destination_collision_never_overwrites_either_marker(tmp_path):
    path, expected = _fixture(tmp_path)
    destination = tmp_path / transition._archive_name(expected)
    destination.write_bytes(b"preserve-existing")
    with pytest.raises(transition.TransitionError, match="DESTINATION_ALREADY_EXISTS"):
        _execute(tmp_path, expected)
    assert path.stat().st_ino == expected["inode"]
    assert destination.read_bytes() == b"preserve-existing"


@POSIX
def test_rollback_before_next_owner_preserves_original_and_reblocks_legacy(tmp_path):
    path, expected = _fixture(tmp_path)
    raw = path.read_bytes()
    _execute(tmp_path, expected)
    result = _execute(tmp_path, expected, rollback=True)
    assert result["operation"] == "ROLLBACK_TO_LEGACY_BLOCKED"
    assert path.read_bytes() == raw and path.stat().st_ino == expected["inode"]
    with pytest.raises(scheduler_lock.LegacyLock):
        scheduler_lock.acquire(path, "synthetic-next", "2026-11-10T22:00:00+01:00")


@POSIX
def test_rollback_cannot_replace_new_owner_or_its_marker(tmp_path):
    path, expected = _fixture(tmp_path)
    result = _execute(tmp_path, expected)
    archive = tmp_path / result["preserved_destination"]
    raw = archive.read_bytes()
    try:
        assert scheduler_lock.acquire(path, "new-owner", "2026-11-10T22:00:00+01:00")[0]
        current = path.read_bytes()
        with pytest.raises(transition.TransitionError, match="DESTINATION_ALREADY_EXISTS"):
            _execute(tmp_path, expected, rollback=True)
        assert scheduler_lock.owned(path, "new-owner")
        assert path.read_bytes() == current and archive.read_bytes() == raw
    finally:
        scheduler_lock.release(path, "new-owner")


@POSIX
def test_post_rename_failure_preserves_archive_and_requires_review_not_retry(tmp_path, monkeypatch):
    path, expected = _fixture(tmp_path)
    raw = path.read_bytes()
    original_fsync = os.fsync
    def fail_parent_sync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("synthetic directory sync failure")
        original_fsync(fd)
    monkeypatch.setattr(transition.os, "fsync", fail_parent_sync)
    with pytest.raises(transition.TransitionError, match="RENAMED_BUT_POSTCHECK_INCOMPLETE"):
        _execute(tmp_path, expected)
    archive = tmp_path / transition._archive_name(expected)
    assert archive.read_bytes() == raw and not path.exists()


@POSIX
def test_symlink_ancestor_cannot_redirect_operation(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    path, expected = _fixture(real)
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    with pytest.raises(OSError):
        _execute(alias, expected)
    assert path.exists() and not (real / transition._archive_name(expected)).exists()


@POSIX
def test_native_rename_respects_python_audit_denial_before_mutation(tmp_path):
    path, expected = _fixture(tmp_path)
    raw = path.read_bytes()
    destination = tmp_path / transition._archive_name(expected)
    events = []
    def deny_exact_synthetic_rename(event, args):
        if event == "os.rename" and args[:2] == (str(path), str(destination)):
            events.append(event)
            raise PermissionError("synthetic policy denial")
    sys.addaudithook(deny_exact_synthetic_rename)
    with pytest.raises(PermissionError, match="synthetic policy denial"):
        _execute(tmp_path, expected)
    assert events == ["os.rename"]
    assert path.read_bytes() == raw and not destination.exists()
