"""Real POSIX ownership tests against disposable directories, never production."""
import json
import os
from pathlib import Path
import select

import pytest

from engines import companyos_scheduler_lock as lock
from engines import product_review_system_engine as engine

pytestmark = pytest.mark.skipif(not lock.supported(), reason="requires real POSIX flock")
NOW = "2026-11-10T17:00:00+01:00"


def _receive(fd):
    assert select.select([fd], [], [], 5)[0], "synthetic child did not report"
    return os.read(fd, 64)


def _join(pid):
    waited, status = os.waitpid(pid, 0)
    assert waited == pid and os.waitstatus_to_exitcode(status) == 0


def test_release_keeps_inode_and_next_owner_requires_real_handle(tmp_path):
    path = tmp_path / "scheduler.lock"
    try:
        assert lock.acquire(path, "one", NOW)[0]
        inode, marker = path.stat().st_ino, path.read_bytes()
        assert lock.owned(path, "one")
        lock.release(path, "other")
        assert lock.owned(path, "one")
        assert not lock.acquire(path, "two", NOW)[0]
        lock.release(path, "one")
        assert path.stat().st_ino == inode and path.read_bytes() == marker
        assert not lock.owned(path, "one")
        assert lock.acquire(path, "two", NOW)[0]
        assert path.stat().st_ino == inode and lock.owned(path, "two")
    finally:
        lock.release(path, "one")
        lock.release(path, "two")


@pytest.mark.parametrize("raw,result", [
    (b'{"job_id":"old","locked_at_madrid":"2026-11-10T16:59:00+01:00"}', "SKIPPED_ALREADY_RUNNING"),
    (b'{"job_id":"old","locked_at_madrid":"2026-11-09T16:59:00+01:00"}', "STALE_LOCK"),
    (b'{"job_id":"old"}', "LOCK_UNVERIFIED"),
    (b'{', "LOCK_UNVERIFIED"),
])
def test_legacy_and_malformed_markers_preserved(tmp_path, raw, result):
    path = tmp_path / "scheduler.lock"
    path.write_bytes(raw)
    inode = path.stat().st_ino
    acquired, payload = engine._ce_acquire_lock({"scheduler_lock": path}, "new", NOW)
    assert not acquired
    assert payload.get("state", "SKIPPED_ALREADY_RUNNING") == result
    engine._ce_release_lock({"scheduler_lock": path}, "old")
    assert path.read_bytes() == raw and path.stat().st_ino == inode


def test_forged_same_pid_json_is_not_native_ownership(tmp_path):
    path = tmp_path / "scheduler.lock"
    path.write_text(json.dumps({"lock_protocol": lock.PROTOCOL, "job_id": "forged",
                               "pid": os.getpid(), "locked_at_madrid": NOW}))
    assert not lock.owned(path, "forged")
    assert not engine._nw_lock_owned(tmp_path, "forged")


def test_symlink_and_hardlink_are_not_accepted_or_modified(tmp_path):
    target = tmp_path / "protected"
    target.write_bytes(b"preserve")
    for name, link in (("symbolic", lambda p: p.symlink_to(target)),
                       ("hard", lambda p: os.link(target, p))):
        path = tmp_path / name
        link(path)
        acquired, payload = lock.acquire(path, "new", NOW)
        assert not acquired and payload["state"] == "LOCK_UNVERIFIED"
        assert target.read_bytes() == b"preserve"


def test_abrupt_exit_releases_os_lock_without_deleting_marker(tmp_path):
    path = tmp_path / "scheduler.lock"
    report_r, report_w = os.pipe()
    stop_r, stop_w = os.pipe()
    pid = os.fork()
    if pid == 0:
        try:
            os.close(report_r); os.close(stop_w)
            assert lock.acquire(path, "child", NOW)[0]
            os.write(report_w, b"owned")
            os.read(stop_r, 1)
            os._exit(0)  # Deliberately no release/finally, simulating process death.
        except BaseException:
            os._exit(1)
    os.close(report_w); os.close(stop_r)
    try:
        assert _receive(report_r) == b"owned"
        inode = path.stat().st_ino
        assert not lock.acquire(path, "parent", NOW)[0]
    finally:
        os.write(stop_w, b"x"); os.close(stop_w); os.close(report_r)
        _join(pid)
    try:
        assert lock.acquire(path, "parent", NOW)[0]
        assert path.stat().st_ino == inode and lock.owned(path, "parent")
    finally:
        lock.release(path, "parent")


def test_fork_child_cannot_keep_or_release_parent_ownership(tmp_path):
    path = tmp_path / "scheduler.lock"
    assert lock.acquire(path, "parent", NOW)[0]
    report_r, report_w = os.pipe()
    stop_r, stop_w = os.pipe()
    pid = os.fork()
    if pid == 0:
        try:
            os.close(report_r)
            os.close(stop_w)
            assert not lock.owned(path, "parent")
            lock.release(path, "parent")
            assert not lock.acquire(path, "child", NOW)[0]
            os.write(report_w, b"blocked")
            os.read(stop_r, 1)
            os._exit(0)
        except BaseException:
            os._exit(1)
    os.close(report_w)
    os.close(stop_r)
    try:
        assert _receive(report_r) == b"blocked"
        assert lock.owned(path, "parent")
        lock.release(path, "parent")
        # Child remains alive: an inherited descriptor must not prolong the lock.
        assert lock.acquire(path, "successor", NOW)[0]
    finally:
        os.write(stop_w, b"x"); os.close(stop_w)
        os.close(report_r)
        lock.release(path, "parent")
        lock.release(path, "successor")
        _join(pid)


def test_two_independent_contenders_have_exactly_one_owner(tmp_path):
    path = tmp_path / "scheduler.lock"
    start_r, start_w = os.pipe()
    report_r, report_w = os.pipe()
    stop_r, stop_w = os.pipe()
    children = []
    for name in ("first", "second"):
        pid = os.fork()
        if pid == 0:
            try:
                os.close(start_w); os.close(report_r); os.close(stop_w)
                os.read(start_r, 1)
                acquired, _ = engine._ce_acquire_lock({"scheduler_lock": path}, name, NOW)
                os.write(report_w, b"1" if acquired else b"0")
                if acquired:
                    assert lock.owned(path, name)
                    os.read(stop_r, 1)
                    lock.release(path, name)
                os._exit(0)
            except BaseException:
                os._exit(1)
        children.append(pid)
    os.close(start_r); os.close(report_w); os.close(stop_r)
    try:
        os.write(start_w, b"xx")
        results = b""
        while len(results) < 2:
            results += _receive(report_r)
        assert sorted(results) == sorted(b"10")
    finally:
        os.write(stop_w, b"xx")
        for fd in (start_w, report_r, stop_w):
            os.close(fd)
        for pid in children:
            _join(pid)


def test_matching_json_after_path_replacement_is_not_owned(tmp_path):
    path = tmp_path / "scheduler.lock"
    try:
        assert lock.acquire(path, "owner", NOW)[0]
        marker = path.read_bytes()
        path.rename(tmp_path / "original")
        path.write_bytes(marker)
        assert not lock.owned(path, "owner")
        lock.release(path, "owner")
        assert path.read_bytes() == marker
    finally:
        lock.release(path, "owner")
