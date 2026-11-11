"""Read-only filesystem identity and capacity planning for recovery #327.

No capture, restore, directory creation or cleanup is performed here. A plan is
not reserved capacity, data authorization, or a reusable filesystem capability.
The eventual operator must revalidate identity/capacity at the write boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat

MIB = 1024 * 1024
MIN_RESERVE = 128 * MIB


class WorkspacePlanError(ValueError):
    """Closed planning diagnostic; never print user data or configuration."""


def _integer(value, *, positive=False):
    if type(value) is not int or value < (1 if positive else 0):
        raise WorkspacePlanError("INVALID_CAPACITY_OBSERVATION")
    return value


@dataclass(frozen=True)
class VolumeObservation:
    device: int
    free_bytes: int

    def __post_init__(self):
        _integer(self.device, positive=True)
        _integer(self.free_bytes)


@dataclass(frozen=True)
class WorkspaceRootIdentity:
    path: Path
    device: int
    inode: int


def _absolute(path):
    if (not isinstance(path, Path) or not path.is_absolute() or ".." in path.parts
            or str(path).startswith(("//", "\\\\"))):
        raise WorkspacePlanError("UNSAFE_WORKSPACE_ROOT")
    return path


def observe_workspace_root(path: Path, *, protected_paths=()) -> WorkspaceRootIdentity:
    """Read an existing directory without resolving away aliases.

    Every ancestor is checked; symlinks/reparse points and overlap with an
    archive/source tree are rejected. This observation grants no write access.
    """
    path = _absolute(path)
    for current in (*reversed(path.parents), path):
        info = current.lstat()
        if (stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400):
            raise WorkspacePlanError("WORKSPACE_ALIAS_OR_NON_DIRECTORY")
    info = path.lstat()
    for protected in protected_paths:
        protected = _absolute(protected)
        if path.is_relative_to(protected) or protected.is_relative_to(path):
            raise WorkspacePlanError("WORKSPACE_OVERLAPS_PROTECTED_TREE")
        # An already-existing bind/alias cannot hide equal filesystem identity.
        if protected.exists():
            other = protected.lstat()
            if (info.st_dev, info.st_ino) == (other.st_dev, other.st_ino):
                raise WorkspacePlanError("WORKSPACE_ALIASES_PROTECTED_ROOT")
    return WorkspaceRootIdentity(path, info.st_dev, info.st_ino)


def revalidate_workspace_root(identity: WorkspaceRootIdentity, *, protected_paths=()):
    if type(identity) is not WorkspaceRootIdentity:
        raise WorkspacePlanError("TYPED_WORKSPACE_IDENTITY_REQUIRED")
    current = observe_workspace_root(identity.path, protected_paths=protected_paths)
    if current != identity:
        raise WorkspacePlanError("WORKSPACE_ROOT_CHANGED")
    return current


def capacity_plan(*, snapshot_bytes: int, archive: VolumeObservation,
                  workspace: VolumeObservation, app_probe_mode=None,
                  state_archive_bytes=0, restored_state_bytes=0) -> dict:
    """Separate filesystem budgets without summing unrelated free space.

    Published archive/state stay durable. ONE disposable restore, App scratch
    and normal-boot journal share the selected workspace. Time budgets and
    integrity/hash/manifest requirements are unchanged by this calculation.
    """
    size = _integer(snapshot_bytes, positive=True)
    state_archive_bytes = _integer(state_archive_bytes)
    restored_state_bytes = _integer(restored_state_bytes)
    if type(archive) is not VolumeObservation or type(workspace) is not VolumeObservation:
        raise WorkspacePlanError("TYPED_VOLUME_OBSERVATION_REQUIRED")
    if app_probe_mode not in (None, "read_only", "normal_boot"):
        raise WorkspacePlanError("INVALID_APP_PROBE_MODE")
    reserve = max(MIN_RESERVE, size // 5)
    durable_payload = size + state_archive_bytes
    temporary = size + reserve + restored_state_bytes
    if app_probe_mode is not None:
        temporary += MIN_RESERVE
        if app_probe_mode == "normal_boot":
            temporary += size
    same = archive.device == workspace.device
    if same:
        # One pool, one reserve: never credit the same free bytes twice.
        required = {archive.device: durable_payload + temporary}
        free = {archive.device: min(archive.free_bytes, workspace.free_bytes)}
    else:
        required = {archive.device: durable_payload + reserve,
                    workspace.device: temporary}
        free = {archive.device: archive.free_bytes,
                workspace.device: workspace.free_bytes}
    ready = all(free[device] >= amount for device, amount in required.items())
    return {"ok": ready, "code": "READY" if ready else "INSUFFICIENT_SPACE",
            "same_filesystem": same, "reserve_bytes": reserve,
            "durable_payload_bytes": durable_payload,
            "restore_workspace_required_bytes": temporary,
            "required_by_device": required, "free_by_device": free,
            "capacity_reserved": False, "full_application_recovery_certified": False}
