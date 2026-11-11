"""Owned synthetic SQLite/filesystem cases; never use server data."""
from contextlib import closing
import hashlib
import os
from pathlib import Path
import sqlite3
import sys
import time

import pytest

from engines.data_vault_engine import create_sqlite_backup
from tools import backup_operator_recovery_327 as operator
from tools.recovery_workspace import admit_restore_root, restore_workspace
from tools.recovery_workspace_plan import WorkspacePlanError


@pytest.fixture
def archive_case(tmp_path):
    source, archives, scratch = tmp_path/"source.db", tmp_path/"archives", tmp_path/"scratch"
    scratch.mkdir(mode=0o700)
    with closing(sqlite3.connect(source)) as connection, connection:
        connection.execute("CREATE TABLE owned_values(id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO owned_values(value) VALUES(?)", ("synthetic-only",))
    created = create_sqlite_backup(source, tmp_path, "OWNED_SYNTHETIC",
                                  directory=archives, max_files=0,
                                  preserve_existing_backups=True, snapshot_timeout=60)
    assert created.get("ok") is True and created.get("backup_created") is True, created
    selected = archives/created["backup_file"]
    before = (selected.read_bytes(), selected.with_suffix(".json").read_bytes(), source.read_bytes())
    return source, archives, scratch, created["backup_file"], before


def assert_durable_unchanged(case):
    source, archives, scratch, name, before = case
    assert ((archives/name).read_bytes(), (archives/name).with_suffix(".json").read_bytes(),
            source.read_bytes()) == before


def test_non_linux_explicit_root_refuses_without_fallback(archive_case):
    if sys.platform == "linux":
        pytest.skip("This refusal is specific to non-Linux hosts")
    _, archives, scratch, name, _ = archive_case
    result = operator.verify_and_restore_isolated(archives, name, 60,
                                                 restore_workspace_root=scratch)
    assert result["ok"] is False
    assert result["diagnostic"] == "EXPLICIT_RESTORE_WORKSPACE_REQUIRES_LINUX"
    assert not list(archives.glob(".isolated_restore_327_*"))
    assert list(scratch.iterdir()) == []
    assert_durable_unchanged(archive_case)


@pytest.mark.skipif(sys.platform != "linux", reason="Actual Linux descriptor/procfs semantics required")
class TestLinuxWorkspace:
    def test_real_restore_is_under_selected_root_and_cleans_only_owned_tree(self, archive_case, monkeypatch):
        _, archives, scratch, name, _ = archive_case
        keep = scratch/"keep"
        keep.write_bytes(b"pre-existing owned data")
        native_connect = sqlite3.connect
        observed = []

        def connect(database, *args, **kwargs):
            if str(database).endswith("restoration-test.db"):
                observed.append(Path(database))
            return native_connect(database, *args, **kwargs)

        monkeypatch.setattr(operator.sqlite3, "connect", connect)
        result = operator.verify_and_restore_isolated(archives, name, 60,
                                                     restore_workspace_root=scratch)
        assert result["ok"] is True and result["code"] == "RESTORE_VERIFIED", result
        assert len(observed) == 1
        assert observed[0].parent.parent == scratch
        assert observed[0].parent.name.startswith(".isolated_restore_327_")
        assert list(scratch.iterdir()) == [keep]
        assert keep.read_bytes() == b"pre-existing owned data"
        assert_durable_unchanged(archive_case)

    def test_alias_root_never_restores_or_creates_workspace(self, archive_case):
        _, archives, scratch, name, _ = archive_case
        alias = scratch.parent/"scratch-alias"
        alias.symlink_to(scratch, target_is_directory=True)
        result = operator.verify_and_restore_isolated(archives, name, 60,
                                                     restore_workspace_root=alias)
        assert result["ok"] is False and result["diagnostic"] == "WORKSPACE_ALIAS_OR_NON_DIRECTORY"
        assert list(scratch.iterdir()) == []
        assert_durable_unchanged(archive_case)

    def test_archive_root_cannot_be_disguised_as_disposable_root(self, archive_case):
        _, archives, _, name, _ = archive_case
        result = operator.verify_and_restore_isolated(archives, name, 60,
                                                     restore_workspace_root=archives)
        assert result["ok"] is False
        assert result["diagnostic"] == "WORKSPACE_OVERLAPS_PROTECTED_TREE"
        assert_durable_unchanged(archive_case)

    def test_root_replaced_before_creation_is_rejected(self, tmp_path):
        scratch = tmp_path/"scratch"
        scratch.mkdir(mode=0o700)
        identity = admit_restore_root(scratch)
        scratch.rename(tmp_path/"old-scratch")
        scratch.mkdir(mode=0o700)
        with pytest.raises(WorkspacePlanError, match="WORKSPACE_ROOT_CHANGED"):
            with restore_workspace(tmp_path, identity=identity, check_time=lambda: None):
                pytest.fail("Changed root must not be used")
        assert list(scratch.iterdir()) == []

    def test_root_replacement_preserves_original_workspace_and_foreign_tree(self, tmp_path):
        scratch = tmp_path/"scratch"
        scratch.mkdir(mode=0o700)
        identity = admit_restore_root(scratch)
        moved = tmp_path/"preserved-root"
        observed = {}
        with pytest.raises(WorkspacePlanError, match="WORKSPACE_ROOT_CHANGED"):
            with restore_workspace(tmp_path, identity=identity, check_time=lambda: None,
                                   observation=observed) as workspace:
                owned_name = workspace.name
                (workspace/"owned").write_bytes(b"preserve after fault")
                scratch.rename(moved)
                scratch.mkdir(mode=0o700)
                (scratch/"foreign").write_bytes(b"do not delete")
        assert (moved/owned_name/"owned").read_bytes() == b"preserve after fault"
        assert (scratch/"foreign").read_bytes() == b"do not delete"
        assert observed["created"] is True and observed["cleanup_verified"] is False
        assert observed["disposable_name"] == owned_name
        assert observed["root_inode"] == identity.inode

    def test_replaced_child_is_never_recursively_deleted(self, tmp_path):
        scratch = tmp_path/"scratch"
        scratch.mkdir(mode=0o700)
        identity = admit_restore_root(scratch)
        with pytest.raises(WorkspacePlanError, match="WORKSPACE_ENTRY_CHANGED_PRESERVE"):
            with restore_workspace(tmp_path, identity=identity, check_time=lambda: None) as workspace:
                original = scratch/"preserved-child"
                workspace.rename(original)
                workspace.mkdir(mode=0o700)
                (workspace/"foreign").write_bytes(b"preserve foreign")
                (original/"owned").write_bytes(b"preserve owned")
        assert (workspace/"foreign").read_bytes() == b"preserve foreign"
        assert (original/"owned").read_bytes() == b"preserve owned"

    def test_unexpected_symlink_is_preserved_and_never_followed(self, tmp_path):
        scratch = tmp_path/"scratch"
        scratch.mkdir(mode=0o700)
        outside = tmp_path/"outside"
        outside.write_bytes(b"untouched")
        identity = admit_restore_root(scratch)
        with pytest.raises(WorkspacePlanError, match="UNEXPECTED_WORKSPACE_ENTRY_PRESERVE"):
            with restore_workspace(tmp_path, identity=identity, check_time=lambda: None) as workspace:
                (workspace/"alias").symlink_to(outside)
        assert outside.read_bytes() == b"untouched"
        assert (workspace/"alias").is_symlink()

    def test_original_standard_audit_veto_happens_before_creation(self, tmp_path):
        scratch = tmp_path/"scratch"
        scratch.mkdir(mode=0o700)
        identity = admit_restore_root(scratch)
        active = {"enabled": True}

        def audit(event, args):
            if (active["enabled"] and event == "os.mkdir"
                    and str(args[0]).startswith("/proc/self/fd/")
                    and ".isolated_restore_327_" in str(args[0])):
                raise PermissionError("owned synthetic audit veto")

        sys.addaudithook(audit)
        try:
            with pytest.raises(PermissionError, match="owned synthetic audit veto"):
                with restore_workspace(tmp_path, identity=identity, check_time=lambda: None):
                    pytest.fail("Audit veto must prevent the actual mkdir")
        finally:
            active["enabled"] = False
        assert list(scratch.iterdir()) == []

    def test_cleanup_propagates_the_callers_deadline_refusal_without_retry(self, tmp_path):
        scratch = tmp_path/"scratch"
        scratch.mkdir(mode=0o700)
        identity = admit_restore_root(scratch)
        refusal = {"active": False, "calls_after_refusal": 0}

        def check_time():
            # Inject the caller's existing deadline refusal, not a fake wall
            # clock or a timing/performance claim. The helper may not replace it
            # with another budget or retry cleanup after it rejects.
            if refusal["active"]:
                refusal["calls_after_refusal"] += 1
                raise TimeoutError("same original deadline")

        with pytest.raises(TimeoutError, match="same original deadline"):
            with restore_workspace(tmp_path, identity=identity, check_time=check_time) as workspace:
                (workspace/"owned").write_bytes(b"preserve on exhausted deadline")
                refusal["active"] = True
        assert refusal["calls_after_refusal"] == 1
        assert (workspace/"owned").read_bytes() == b"preserve on exhausted deadline"

    def test_parent_swapped_at_mkdir_uses_pinned_old_root_and_stops(self, tmp_path, monkeypatch):
        scratch = tmp_path/"scratch"
        scratch.mkdir(mode=0o700)
        identity = admit_restore_root(scratch)
        moved = tmp_path/"preserved-parent"
        native_mkdir = os.mkdir
        changed = {"done": False}

        def mkdir(path, *args, **kwargs):
            if not changed["done"] and str(path).startswith("/proc/self/fd/"):
                changed["done"] = True
                scratch.rename(moved)
                native_mkdir(scratch, mode=0o700)
                (scratch/"foreign").write_bytes(b"do not touch replacement")
            return native_mkdir(path, *args, **kwargs)

        monkeypatch.setattr(os, "mkdir", mkdir)
        with pytest.raises(WorkspacePlanError, match="WORKSPACE_ROOT_CHANGED"):
            with restore_workspace(tmp_path, identity=identity, check_time=lambda: None):
                pytest.fail("Changed named root must stop before restore data")
        assert (scratch/"foreign").read_bytes() == b"do not touch replacement"
        preserved = list(moved.glob(".isolated_restore_327_*"))
        assert len(preserved) == 1 and list(preserved[0].iterdir()) == []

    def test_writable_nonsticky_parent_is_not_silently_fixed(self, tmp_path):
        scratch = tmp_path/"scratch"
        scratch.mkdir(mode=0o700)
        scratch.chmod(0o777)
        try:
            with pytest.raises(WorkspacePlanError, match="UNTRUSTED_WORKSPACE_PARENT"):
                admit_restore_root(scratch)
            assert scratch.stat().st_mode & 0o777 == 0o777
        finally:
            scratch.chmod(0o700)

    def test_hardlinked_entry_is_retained_without_touching_other_name(self, tmp_path):
        scratch = tmp_path/"scratch"
        scratch.mkdir(mode=0o700)
        outside = tmp_path/"owned-outside"
        outside.write_bytes(b"preserve linked inode")
        identity = admit_restore_root(scratch)
        with pytest.raises(WorkspacePlanError, match="UNEXPECTED_WORKSPACE_ENTRY_PRESERVE"):
            with restore_workspace(tmp_path, identity=identity, check_time=lambda: None) as workspace:
                os.link(outside, workspace/"hardlink")
        assert outside.read_bytes() == b"preserve linked inode"
        assert (workspace/"hardlink").stat().st_ino == outside.stat().st_ino

    def test_workspace_space_failure_keeps_published_archive(self, archive_case, monkeypatch):
        _, archives, scratch, name, _ = archive_case
        original_usage = operator.shutil.disk_usage

        def usage(path):
            if Path(path) == scratch:
                return type(original_usage(path))(1000, 999, 1)
            return original_usage(path)

        monkeypatch.setattr(operator.shutil, "disk_usage", usage)
        result = operator.verify_and_restore_isolated(archives, name, 60,
                                                     restore_workspace_root=scratch)
        assert result["ok"] is False
        assert result["code"] == "INSUFFICIENT_ISOLATED_RESTORE_SPACE"
        assert list(scratch.iterdir()) == []
        assert_durable_unchanged(archive_case)



def _args(case, *, execute):
    from types import SimpleNamespace
    source, archives, scratch, _, _ = case
    return SimpleNamespace(db=str(source), backup_dir=str(archives), timeout=60,
                           execute=execute, verify_existing=None, app_probe_mode="normal_boot",
                           restore_workspace_root=scratch)


def test_non_linux_execute_refuses_before_any_capture(archive_case, monkeypatch, capsys):
    if sys.platform == "linux":
        pytest.skip("Non-Linux explicit-root refusal only")
    captures = []
    monkeypatch.setattr(operator, "create_sqlite_backup", lambda *a, **kw: captures.append(kw))
    result = operator.run(_args(archive_case, execute=True))
    import json
    report = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert result == 2 and report["backup_created"] is False
    assert report["diagnostic"] == "EXPLICIT_RESTORE_WORKSPACE_REQUIRES_LINUX"
    assert captures == []
    assert_durable_unchanged(archive_case)


@pytest.mark.skipif(sys.platform != "linux", reason="Actual Linux preflight root binding required")
class TestLinuxWorkspacePreflight:
    def test_readonly_preflight_creates_no_archive_or_workspace(self, archive_case, monkeypatch, capsys):
        import json
        source, archives, scratch, _, _ = archive_case
        usage_type = type(operator.shutil.disk_usage(scratch))
        monkeypatch.setattr(operator.shutil, "disk_usage",
                            lambda path: usage_type(20_000_000_000, 1, 19_999_999_999))
        captures = []
        monkeypatch.setattr(operator, "create_sqlite_backup", lambda *a, **kw: captures.append(kw))
        assert operator.run(_args(archive_case, execute=False)) == 0
        report = json.loads(capsys.readouterr().out.splitlines()[-1])
        assert report["code"] == "READY" and report["backup_created"] is False
        assert report["capacity_reserved"] is False
        assert report["full_application_recovery_certified"] is False
        assert report["restore_workspace_identity"]["inode"] == scratch.stat().st_ino
        assert captures == [] and list(scratch.iterdir()) == []
        assert_durable_unchanged(archive_case)

    def test_same_pool_normal_boot_headroom_is_checked_before_capture(self, archive_case, monkeypatch):
        source, archives, scratch, _, _ = archive_case
        usage_type = type(operator.shutil.disk_usage(scratch))
        monkeypatch.setattr(operator.shutil, "disk_usage",
                            lambda path: usage_type(300*1024**2, 44*1024**2, 256*1024**2))
        result = operator.preflight(source, archives, restore_workspace_root=scratch,
                                    app_probe_mode="normal_boot")
        assert result["ok"] is False
        assert result["same_filesystem"] is True
        assert result["required_bytes"] > 256*1024**2
        assert list(scratch.iterdir()) == []
        assert_durable_unchanged(archive_case)

    def test_root_changes_after_preflight_before_capture(self, archive_case, monkeypatch, capsys):
        import json
        _, _, scratch, _, _ = archive_case
        original = operator.preflight
        calls = []
        def changed(*args, **kwargs):
            report = original(*args, **kwargs)
            calls.append(report)
            if len(calls) == 1:
                assert report["ok"] is True, report
                scratch.rename(scratch.with_name("preserved-preflight-root"))
                scratch.mkdir(mode=0o700)
            return report
        captures = []
        monkeypatch.setattr(operator, "preflight", changed)
        monkeypatch.setattr(operator, "create_sqlite_backup", lambda *a, **kw: captures.append(kw))
        assert operator.run(_args(archive_case, execute=True)) == 2
        report = json.loads(capsys.readouterr().out.splitlines()[-1])
        assert report["backup_created"] is False and report["diagnostic"] == "WORKSPACE_ROOT_CHANGED"
        assert captures == [] and list(scratch.iterdir()) == []
        assert_durable_unchanged(archive_case)

    def test_root_change_after_publication_keeps_actual_new_archive(self, archive_case, monkeypatch, capsys):
        import json
        _, archives, scratch, _, _ = archive_case
        before = set(archives.glob("database_*.db"))
        original = operator.create_sqlite_backup
        def changed(*args, **kwargs):
            result = original(*args, **kwargs)
            assert result["ok"] is True and result["backup_created"] is True, result
            scratch.rename(scratch.with_name("preserved-after-publication"))
            scratch.mkdir(mode=0o700)
            return result
        monkeypatch.setattr(operator, "create_sqlite_backup", changed)
        assert operator.run(_args(archive_case, execute=True)) == 3
        report = json.loads(capsys.readouterr().out.splitlines()[-1])
        assert report["backup_created"] is True and report["isolated_restore_ok"] is False
        assert report["code"] == "ISOLATED_RESTORE_WORKSPACE_NOT_VERIFIED"
        new = set(archives.glob("database_*.db"))-before
        assert len(new) == 1
        assert new.pop().with_suffix(".json").is_file()
        assert list(scratch.iterdir()) == []
        assert_durable_unchanged(archive_case)

    def test_typed_state_capacity_preserves_archive_and_extraction_in_one_pool(self, archive_case):
        from engines import recovery_non_sqlite_state as state
        from tools import recovery_state_adapter as adapter
        source, archives, scratch, _, _ = archive_case
        ce, legacy = source.parent/"ce", source.parent/"legacy"
        ce.mkdir(mode=0o700)
        legacy.mkdir(mode=0o700)
        scopes = (state.Scope("ce", ce), state.Scope("legacy_runtime", legacy))
        authorization = state.Authorization("SYNTHETIC_ONLY",
            tuple((scope.role, str(scope.source)) for scope in scopes), True, (str(source),))
        plan = adapter.StateRecoveryPlan("OWNED_OPERATION", "c"*64, scopes,
                                         authorization, archives/"state-private")
        base = operator.preflight(source, archives, restore_workspace_root=scratch,
                                  app_probe_mode="normal_boot")
        result = adapter.operator_preflight(
            plan=plan, source=source, directory=archives, app_probe_mode="normal_boot",
            verify_existing=None, storage=base, restore_workspace_root=scratch)
        policy = state._policy(plan.profile_id, plan.limits)
        assert result["required_bytes"]-base["required_bytes"] == policy.archive_bytes+policy.bytes
        assert result["state_overhead_bytes"] == policy.archive_bytes+policy.bytes
        assert result["capacity_reserved"] is False
        assert result["full_application_recovery_certified"] is False
        assert list(scratch.iterdir()) == []
        assert_durable_unchanged(archive_case)

    def test_actual_second_device_metadata_is_not_pooled(self, archive_case):
        from tools.recovery_workspace import workspace_capacity_preflight
        source, archives, scratch, _, _ = archive_case
        other = Path("/dev/shm")
        if not other.is_dir() or other.stat().st_dev == archives.stat().st_dev:
            pytest.skip("No existing independent shared-memory filesystem")
        result = workspace_capacity_preflight(
            source=source, directory=archives, restore_root=other,
            snapshot_bytes=operator.estimate_bytes(source), app_probe_mode="normal_boot")
        assert result["same_filesystem"] is False
        assert set(result["required_by_device"]) == {archives.stat().st_dev, other.stat().st_dev}
        assert len(result["free_by_device"]) == 2
        # Metadata only. Never create files or grant writes on /dev/shm.
        assert list(scratch.iterdir()) == []
        assert_durable_unchanged(archive_case)
