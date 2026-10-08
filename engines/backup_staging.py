"""Private backup workspaces, recovered only while holding the directory lock."""
from __future__ import annotations

import errno
import os
import re
import stat
import uuid
from contextlib import contextmanager
from pathlib import Path

LOCK_NAME = ".backup.lock"
OWNER = b"nemesis-sqlite-backup-staging-v1\n"
WORKSPACE_NAME = re.compile(r"\.backup-work-[0-9a-f]{32}\Z")
WORKSPACE_FILES = {".owner", "snapshot.partial", "snapshot.partial-wal",
                   "snapshot.partial-shm", "snapshot.partial-journal", "manifest.json.partial"}


class BackupInProgress(Exception):
    """Another process or thread owns this backup directory."""


@contextmanager
def backup_directory_lock(directory: Path):
    # Keep this inode permanently: unlinking a lock file lets another caller
    # create a different inode and bypass a lock still held by the first caller.
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    path = directory / LOCK_NAME
    if path.is_symlink():
        raise OSError("backup_lock_unsafe")
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise OSError("backup_lock_unsafe")
        if os.name == "nt":
            import msvcrt
            if info.st_size == 0:
                os.write(fd, b"\0")
            os.lseek(fd, 0, os.SEEK_SET)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise BackupInProgress from exc
                raise
        else:
            import fcntl
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise BackupInProgress from exc
        yield
    finally:
        # Closing releases the OS lock, including after a worker is killed.
        os.close(fd)


def new_workspace(directory: Path) -> Path:
    workspace = directory / (".backup-work-" + uuid.uuid4().hex)
    workspace.mkdir(mode=0o700)
    try:
        with (workspace / ".owner").open("xb") as marker:
            marker.write(OWNER)
            marker.flush()
            os.fsync(marker.fileno())
    except OSError:
        (workspace / ".owner").unlink(missing_ok=True)
        workspace.rmdir()
        raise
    return workspace


def remove_workspace(workspace: Path, directory: Path, source: Path) -> dict:
    """Remove only our marked, flat temporary workspace; never follow links.

    The caller must own backup_directory_lock for the entire operation. Age
    alone cannot prove that a file is abandoned; the OS lock supplies that proof.
    Legacy .backup-*.partial files and quarantine archives are deliberately excluded.
    """
    result = {"removed": False, "bytes": 0, "skipped": False, "failed": False}
    try:
        if (not WORKSPACE_NAME.fullmatch(workspace.name) or workspace.is_symlink()
                or not workspace.is_dir() or workspace.parent.resolve() != directory.resolve()
                or source.resolve().is_relative_to(workspace.resolve())):
            return {**result, "skipped": True}
        children = list(workspace.iterdir())
        if not children or any(
            p.name not in WORKSPACE_FILES or p.is_symlink()
            or not stat.S_ISREG(p.lstat().st_mode) or p.lstat().st_nlink != 1
            for p in children
        ):
            return {**result, "skipped": True}
        marker = workspace / ".owner"
        if not marker.is_file() or marker.stat().st_size != len(OWNER):
            return {**result, "skipped": True}
        if marker.read_bytes() != OWNER:
            return {**result, "skipped": True}
        size = sum(p.stat().st_size for p in children)
        # Marker last: an interrupted cleanup remains identifiable on retry.
        for child in children:
            if child.name != ".owner":
                child.unlink()
        marker.unlink()
        workspace.rmdir()
        return {**result, "removed": True, "bytes": size}
    except OSError:
        return {**result, "failed": True}


def recover_abandoned_workspaces(directory: Path, source: Path) -> dict:
    """Called after acquiring the same lock used by every workspace creator."""
    result = {"recovered_count": 0, "recovered_bytes": 0,
              "skipped_count": 0, "failed_count": 0}
    for workspace in directory.glob(".backup-work-*"):
        item = remove_workspace(workspace, directory, source)
        result["recovered_count"] += int(item["removed"])
        result["recovered_bytes"] += item["bytes"]
        result["skipped_count"] += int(item["skipped"])
        result["failed_count"] += int(item["failed"])
    return result
