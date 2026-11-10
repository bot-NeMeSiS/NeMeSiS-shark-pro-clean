"""Owned optional Linux restore workspace; no scheduled/application caller.

The parent is pre-existing and metadata-checked. Creation/cleanup use pinned
directory descriptors through Linux procfs and STANDARD audited Python calls,
not native syscalls or a relaxed supervisor. The fixed App probe still receives
normal paths and its original confinement. Ancestors must be OS/current-user
owned and not writable by other users except trusted sticky directories.
This does not isolate arbitrary hostile same-UID Python or a host administrator.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
import shutil
from pathlib import Path
import stat
import sys
import tempfile
import uuid

from tools.recovery_workspace_plan import (
    WorkspacePlanError, WorkspaceRootIdentity, observe_workspace_root,
    revalidate_workspace_root,
)


def admit_restore_root(path, *, protected_paths=()):
    identity = observe_workspace_root(path, protected_paths=protected_paths)
    if sys.platform == "linux":
        trusted = {0, os.geteuid()}
        for current in (*reversed(path.parents), path):
            info = current.lstat()
            if (info.st_uid not in trusted
                    or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX)):
                raise WorkspacePlanError("UNTRUSTED_WORKSPACE_PARENT")
    return identity


def recheck_restore_root(identity, *, protected_paths=()):
    current = revalidate_workspace_root(identity, protected_paths=protected_paths)
    if admit_restore_root(current.path, protected_paths=protected_paths) != identity:
        raise WorkspacePlanError("WORKSPACE_ROOT_CHANGED")
    return current


def _identity(info):
    return info.st_dev, info.st_ino


def _fd_path(fd):
    path = Path("/proc/self/fd") / str(fd)
    # procfs is an internal reference to our own pinned descriptor, never an
    # alias accepted from caller data. Missing/mismatched procfs has no fallback.
    if _identity(path.stat()) != _identity(os.fstat(fd)):
        raise WorkspacePlanError("PINNED_WORKSPACE_REFERENCE_UNAVAILABLE")
    return path


def _remove_owned_contents(fd, check_time, *, depth=0):
    if depth > 64:
        raise WorkspacePlanError("WORKSPACE_CLEANUP_DEPTH_PRESERVE")
    with os.scandir(fd) as entries:
        for entry in entries:
            check_time()
            info = os.stat(entry.name, dir_fd=fd, follow_symlinks=False)
            target = _fd_path(fd) / entry.name
            if stat.S_ISDIR(info.st_mode):
                child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY
                                | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                try:
                    if _identity(os.fstat(child)) != _identity(info):
                        raise WorkspacePlanError("WORKSPACE_ENTRY_CHANGED_PRESERVE")
                    _remove_owned_contents(child, check_time, depth=depth+1)
                    if _identity(os.stat(entry.name, dir_fd=fd, follow_symlinks=False)) != _identity(info):
                        raise WorkspacePlanError("WORKSPACE_ENTRY_CHANGED_PRESERVE")
                    check_time()
                    os.rmdir(target)
                finally:
                    os.close(child)
            elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                check_time()
                os.unlink(target)
            else:
                # Unexpected links/special files are retained, not followed or
                # fed to a broad recursive remover.
                raise WorkspacePlanError("UNEXPECTED_WORKSPACE_ENTRY_PRESERVE")


@contextmanager
def restore_workspace(directory, *, identity=None, check_time, observation=None):
    """Yield ONE workspace. Explicit-root cleanup shares the SAME deadline.

    Defaults retain the existing TemporaryDirectory implementation. An explicit
    root supports Linux only; a failure never falls back to the archive disk.
    Root/entry changes or an expired deadline leave owned scratch for review.
    """
    if identity is None:
        with tempfile.TemporaryDirectory(prefix=".isolated_restore_327_", dir=directory) as temp:
            yield Path(temp)
        return
    if type(identity) is not WorkspaceRootIdentity:
        raise WorkspacePlanError("TYPED_WORKSPACE_IDENTITY_REQUIRED")
    if observation is not None and type(observation) is not dict:
        raise WorkspacePlanError("TYPED_WORKSPACE_OBSERVATION_REQUIRED")
    if sys.platform != "linux":
        raise WorkspacePlanError("EXPLICIT_RESTORE_WORKSPACE_REQUIRES_LINUX")
    check_time()
    recheck_restore_root(identity)
    parent = os.open(identity.path, os.O_RDONLY | os.O_DIRECTORY
                     | os.O_NOFOLLOW | os.O_CLOEXEC)
    child = None
    created = False
    name = ".isolated_restore_327_" + uuid.uuid4().hex
    try:
        if _identity(os.fstat(parent)) != (identity.device, identity.inode):
            raise WorkspacePlanError("WORKSPACE_ROOT_CHANGED")
        parent_path = _fd_path(parent)
        check_time()
        # stdlib audit sees an absolute path resolving inside this owned root;
        # no native mkdirat/audit bypass and no process cwd change is needed.
        os.mkdir(parent_path / name, mode=0o700)
        created = True
        if observation is not None:
            observation.update(created=True, disposable_name=name,
                               root_device=identity.device, root_inode=identity.inode,
                               cleanup_verified=False)
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if observation is not None:
            observation.update(device=info.st_dev, disposable_inode=info.st_ino)
        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                        | os.O_CLOEXEC, dir_fd=parent)
        if (_identity(os.fstat(child)) != _identity(info) or info.st_dev != identity.device
                or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700):
            raise WorkspacePlanError("WORKSPACE_IDENTITY_OR_PRIVACY_NOT_VERIFIED")
        check_time()
        recheck_restore_root(identity)
        temp = identity.path / name
        if _identity(temp.lstat()) != _identity(os.fstat(child)):
            raise WorkspacePlanError("WORKSPACE_ENTRY_CHANGED_PRESERVE")
        yield temp
    finally:
        try:
            if created:
                # Do not remove through a changed named root or replace an
                # entry. On timeout/change/denial preserve scratch; never retry.
                check_time()
                recheck_restore_root(identity)
                if child is None or _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != _identity(os.fstat(child)):
                    raise WorkspacePlanError("WORKSPACE_ENTRY_CHANGED_PRESERVE")
                _remove_owned_contents(child, check_time)
                check_time()
                if _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != _identity(os.fstat(child)):
                    raise WorkspacePlanError("WORKSPACE_ENTRY_CHANGED_PRESERVE")
                os.rmdir(_fd_path(parent) / name)
                if observation is not None:
                    observation["cleanup_verified"] = True
        finally:
            if child is not None:
                os.close(child)
            os.close(parent)



def workspace_capacity_preflight(*, source, directory, restore_root, snapshot_bytes,
                                 app_probe_mode=None, expected_identity=None,
                                 state_archive_bytes=0, restored_state_bytes=0):
    """Read current capacity per device before any capture; reserve no storage."""
    from tools.recovery_workspace_plan import VolumeObservation, capacity_plan
    if sys.platform != "linux":
        raise WorkspacePlanError("EXPLICIT_RESTORE_WORKSPACE_REQUIRES_LINUX")
    identity = admit_restore_root(restore_root, protected_paths=(source, directory))
    if expected_identity is not None and (type(expected_identity) is not WorkspaceRootIdentity
                                          or identity != expected_identity):
        raise WorkspacePlanError("WORKSPACE_ROOT_CHANGED")
    parent = directory
    while not parent.exists():
        if parent.parent == parent:
            raise WorkspacePlanError("ARCHIVE_STORAGE_PARENT_UNAVAILABLE")
        parent = parent.parent
    archive_identity = observe_workspace_root(parent)
    descriptor = os.open(identity.path, os.O_RDONLY | os.O_DIRECTORY
                         | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        if _identity(os.fstat(descriptor)) != (identity.device, identity.inode):
            raise WorkspacePlanError("WORKSPACE_ROOT_CHANGED")
        _fd_path(descriptor)
    finally:
        os.close(descriptor)
    archive = VolumeObservation(archive_identity.device, int(shutil.disk_usage(parent).free))
    workspace = VolumeObservation(identity.device, int(shutil.disk_usage(identity.path).free))
    result = capacity_plan(snapshot_bytes=snapshot_bytes, archive=archive, workspace=workspace,
                           app_probe_mode=app_probe_mode, state_archive_bytes=state_archive_bytes,
                           restored_state_bytes=restored_state_bytes)
    recheck_restore_root(identity, protected_paths=(source, directory))
    return {**result, "stage": "PREFLIGHT", "snapshot_bytes": snapshot_bytes,
            "free_bytes": result["free_by_device"][archive.device],
            "required_bytes": result["required_by_device"][archive.device],
            "restore_workspace_free_bytes": result["free_by_device"][workspace.device],
            "restore_workspace_identity": {"device": identity.device, "inode": identity.inode},
            "explicit_restore_workspace": True}
