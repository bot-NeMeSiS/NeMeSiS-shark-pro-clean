"""Owned synthetic planning only: no production data/capture/restore."""
from pathlib import Path

import pytest

from tools.recovery_workspace_plan import (
    MIB, VolumeObservation, WorkspacePlanError, capacity_plan,
    observe_workspace_root, revalidate_workspace_root,
)


def test_spare_ephemeral_bytes_cannot_cover_missing_durable_capacity():
    result = capacity_plan(snapshot_bytes=100*MIB,
                           archive=VolumeObservation(1, 100*MIB),
                           workspace=VolumeObservation(2, 10_000*MIB),
                           app_probe_mode="normal_boot")
    assert result["ok"] is False
    assert result["required_by_device"][1] > result["free_by_device"][1]


def test_spare_durable_bytes_cannot_cover_missing_restore_capacity():
    result = capacity_plan(snapshot_bytes=100*MIB,
                           archive=VolumeObservation(1, 10_000*MIB),
                           workspace=VolumeObservation(2, 200*MIB),
                           app_probe_mode="normal_boot")
    assert result["ok"] is False
    assert result["required_by_device"][2] > result["free_by_device"][2]


def test_shared_device_cannot_count_same_free_space_twice():
    # Each separate pool would fit228MiB; one300MiB pool cannot hold both
    # durable100MiB and restored100MiB plus the shared128MiB reserve.
    result = capacity_plan(snapshot_bytes=100*MIB,
                           archive=VolumeObservation(7, 300*MIB),
                           workspace=VolumeObservation(7, 300*MIB))
    assert result["ok"] is False
    assert list(result["required_by_device"]) == [7]


def test_shared_device_uses_lower_observed_free_without_double_reserve():
    result = capacity_plan(snapshot_bytes=100*MIB,
                           archive=VolumeObservation(7, 500*MIB),
                           workspace=VolumeObservation(7, 328*MIB))
    assert result["ok"] is True
    assert result["required_by_device"] == {7: 328*MIB}
    assert result["capacity_reserved"] is False
    assert result["full_application_recovery_certified"] is False


def test_normal_boot_and_state_all_stay_inside_original_workspace_budget():
    kwargs = dict(snapshot_bytes=100*MIB,
                  archive=VolumeObservation(1, 10_000*MIB),
                  workspace=VolumeObservation(2, 10_000*MIB))
    basic = capacity_plan(**kwargs)
    readonly = capacity_plan(**kwargs, app_probe_mode="read_only")
    normal = capacity_plan(**kwargs, app_probe_mode="normal_boot",
                           state_archive_bytes=30*MIB, restored_state_bytes=40*MIB)
    assert readonly["restore_workspace_required_bytes"] - basic["restore_workspace_required_bytes"] == 128*MIB
    assert normal["restore_workspace_required_bytes"] - readonly["restore_workspace_required_bytes"] == 140*MIB
    assert normal["durable_payload_bytes"] == 130*MIB


@pytest.mark.parametrize("bad", [True, False, -1, 1.5, "1", None])
def test_invalid_capacity_observations_never_become_permission(bad):
    with pytest.raises(WorkspacePlanError):
        capacity_plan(snapshot_bytes=bad, archive=VolumeObservation(1, 0),
                      workspace=VolumeObservation(2, 0))


def test_workspace_observation_does_not_create_or_remove_files(tmp_path):
    archive, scratch = tmp_path/"archive", tmp_path/"scratch"
    archive.mkdir()
    scratch.mkdir()
    marker = scratch/"preserve.txt"
    marker.write_bytes(b"owned existing data")
    identity = observe_workspace_root(scratch, protected_paths=(archive,))
    assert revalidate_workspace_root(identity, protected_paths=(archive,)) == identity
    assert list(scratch.iterdir()) == [marker]
    assert marker.read_bytes() == b"owned existing data"


def test_overlap_parent_or_child_never_admitted(tmp_path):
    archive = tmp_path/"archive"
    archive.mkdir()
    child = archive/"child"
    child.mkdir()
    for root in (archive, child, tmp_path):
        with pytest.raises(WorkspacePlanError):
            observe_workspace_root(root, protected_paths=(archive,))


def test_root_replacement_invalidates_observation(tmp_path):
    scratch = tmp_path/"scratch"
    scratch.mkdir()
    identity = observe_workspace_root(scratch)
    scratch.rename(tmp_path/"preserved-scratch")
    scratch.mkdir()
    with pytest.raises(WorkspacePlanError, match="WORKSPACE_ROOT_CHANGED"):
        revalidate_workspace_root(identity)


def test_ancestor_alias_cannot_be_resolved_away(tmp_path):
    actual = tmp_path/"actual"
    actual.mkdir()
    (actual/"scratch").mkdir()
    alias = tmp_path/"alias"
    try:
        alias.symlink_to(actual, target_is_directory=True)
    except OSError:
        pytest.skip("Owned directory symlink unavailable on this platform")
    with pytest.raises(WorkspacePlanError, match="WORKSPACE_ALIAS_OR_NON_DIRECTORY"):
        observe_workspace_root(alias/"scratch")
