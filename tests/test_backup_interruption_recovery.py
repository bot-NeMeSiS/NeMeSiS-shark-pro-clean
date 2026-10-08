"""Crash/concurrency recovery using only disposable files and child processes."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from engines import backup_staging as staging
from engines import data_vault_engine as vault


def make_source(tmp_path):
    source = tmp_path / "live.db"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO users VALUES(1, 'preserve')")
    return source


def test_killed_backup_releases_lock_and_next_attempt_recovers_only_its_workspace(tmp_path):
    source = make_source(tmp_path)
    folder = tmp_path / "backups"
    first = vault.create_sqlite_backup(source, tmp_path, "QA", directory=folder)
    assert first["ok"]
    preserved = Path(first["path"]).read_bytes()
    original = source.read_bytes()
    ready = tmp_path / "child-ready"
    # Block after the SQLite copy has closed, while the OS directory lock is held.
    code = """
import sys, time
from pathlib import Path
from engines import data_vault_engine as vault
def pause(*args, **kwargs):
    Path(sys.argv[3]).write_text('ready')
    while True: time.sleep(0.05)
vault.sha256_file = pause
vault.create_sqlite_backup(sys.argv[1], '.', 'QA', directory=sys.argv[2])
"""
    process = subprocess.Popen([sys.executable, "-c", code, str(source), str(folder), str(ready)],
                               cwd=Path(__file__).resolve().parents[1],
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 15
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready.exists(), "child never reached the isolated backup checkpoint"
        interrupted = list(folder.glob(".backup-work-*"))
        assert len(interrupted) == 1
        concurrent = vault.create_sqlite_backup(source, tmp_path, "QA", directory=folder)
        assert concurrent == {"ok": True, "backup_created": False, "status": "SKIPPED_ALREADY_RUNNING"}
        assert interrupted[0].exists()
        assert len(vault.list_backups(tmp_path, directory=folder)) == 1
        process.kill()
        process.wait(timeout=10)
        assert interrupted[0].exists()  # No Python finally ran after termination.
        recovered = vault.create_sqlite_backup(source, tmp_path, "QA", directory=folder)
        assert recovered["ok"] and recovered["backup_created"]
        recovery = recovered["storage"]["temporary_recovery"]
        assert recovery["recovered_count"] == 1 and recovery["recovered_bytes"] >= len(original)
        assert not list(folder.glob(".backup-work-*"))
        assert Path(first["path"]).read_bytes() == preserved
        assert source.read_bytes() == original
        assert vault.validate_backup(tmp_path, directory=folder)["ok"]
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        process.stderr.close()


def test_recovery_precedes_capacity_and_preserves_legacy_files_and_quarantine(tmp_path, monkeypatch):
    source = make_source(tmp_path)
    folder = tmp_path / "backups"
    folder.mkdir()
    abandoned = staging.new_workspace(folder)
    (abandoned / "snapshot.partial").write_bytes(b"interrupted copy")
    legacy = folder / ".backup-legacy.partial"
    legacy.write_bytes(b"unmanaged: retain for review")
    quarantine = folder / "quarantine-20261008"
    quarantine.mkdir()
    archive = quarantine / "abandoned-backups.tar.gz"
    archive.write_bytes(b"preserve archive")
    original_capacity = vault.ensure_backup_capacity
    def check_capacity(*args, **kwargs):
        assert not abandoned.exists()
        return original_capacity(*args, **kwargs)
    monkeypatch.setattr(vault, "ensure_backup_capacity", check_capacity)
    result = vault.create_sqlite_backup(source, tmp_path, "QA", directory=folder)
    assert result["ok"]
    assert legacy.read_bytes() == b"unmanaged: retain for review"
    assert archive.read_bytes() == b"preserve archive"


def test_concurrent_thread_cannot_recover_an_active_workspace(tmp_path):
    source = make_source(tmp_path)
    folder = tmp_path / "backups"
    folder.mkdir()
    with staging.backup_directory_lock(folder):
        active = staging.new_workspace(folder)
        (active / "snapshot.partial").write_bytes(b"still being written")
        with ThreadPoolExecutor(max_workers=1) as executor:
            blocked = executor.submit(vault.create_sqlite_backup, source, tmp_path, "QA", directory=folder).result(timeout=10)
        assert blocked["status"] == "SKIPPED_ALREADY_RUNNING" and not blocked["backup_created"]
        assert (active / "snapshot.partial").read_bytes() == b"still being written"
    result = vault.create_sqlite_backup(source, tmp_path, "QA", directory=folder)
    assert result["ok"] and result["storage"]["temporary_recovery"]["recovered_count"] == 1


@pytest.mark.parametrize("unsafe", ["unmarked", "wrong_marker", "extra_file", "subdirectory", "source"])
def test_recovery_leaves_unrecognized_or_protected_workspaces_untouched(tmp_path, unsafe):
    folder = tmp_path / "backups"
    folder.mkdir()
    source = make_source(tmp_path)
    workspace = staging.new_workspace(folder)
    (workspace / "snapshot.partial").write_bytes(b"keep")
    if unsafe == "unmarked":
        (workspace / ".owner").unlink()
    elif unsafe == "wrong_marker":
        (workspace / ".owner").write_bytes(b"unrecognized")
    elif unsafe == "extra_file":
        (workspace / "user-document").write_bytes(b"keep too")
    elif unsafe == "subdirectory":
        (workspace / "nested").mkdir()
    else:
        source = workspace / "snapshot.partial"
    with staging.backup_directory_lock(folder):
        result = staging.recover_abandoned_workspaces(folder, source)
    assert result["skipped_count"] == 1 and result["recovered_count"] == 0
    assert (workspace / "snapshot.partial").read_bytes() == b"keep"


def test_recovery_rejects_hardlinks_to_source(tmp_path):
    folder = tmp_path / "backups"
    folder.mkdir()
    source = make_source(tmp_path)
    original = source.read_bytes()
    workspace = staging.new_workspace(folder)
    os.link(source, workspace / "snapshot.partial")
    with staging.backup_directory_lock(folder):
        result = staging.recover_abandoned_workspaces(folder, source)
    assert result["skipped_count"] == 1
    assert source.read_bytes() == original
    assert (workspace / "snapshot.partial").exists()


def test_recovery_never_follows_a_workspace_symlink(tmp_path):
    folder = tmp_path / "backups"
    folder.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / ".owner").write_bytes(staging.OWNER)
    (outside / "snapshot.partial").write_bytes(b"keep")
    link = folder / (".backup-work-" + "a" * 32)
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks require host permission")
    with staging.backup_directory_lock(folder):
        result = staging.recover_abandoned_workspaces(folder, make_source(tmp_path))
    assert result["skipped_count"] == 1 and link.is_symlink()
    assert (outside / "snapshot.partial").read_bytes() == b"keep"


def test_failure_cleans_sqlite_sidecars_as_well_as_snapshot(tmp_path, monkeypatch):
    source = make_source(tmp_path)
    folder = tmp_path / "backups"
    def fail_hash(path, **kwargs):
        for suffix in ("-wal", "-shm", "-journal"):
            Path(str(path) + suffix).write_bytes(b"disposable sidecar")
        raise OSError("QA_HASH_FAILURE")
    monkeypatch.setattr(vault, "sha256_file", fail_hash)
    result = vault.create_sqlite_backup(source, tmp_path, "QA", directory=folder)
    assert not result["ok"] and not result["backup_created"]
    assert result["error"] == "QA_HASH_FAILURE"
    assert result["failure_stage"] == "HASH"
    assert sorted(p.name for p in folder.iterdir()) == [staging.LOCK_NAME]


def test_restore_does_not_accept_a_skipped_safety_backup(tmp_path, monkeypatch):
    source = make_source(tmp_path)
    folder = tmp_path / "backups"
    saved = vault.create_sqlite_backup(source, tmp_path, "QA", directory=folder)
    with sqlite3.connect(source) as conn:
        conn.execute("UPDATE users SET name='current data'")
    original = source.read_bytes()
    monkeypatch.setattr(vault, "create_sqlite_backup", lambda *a, **k:
                        {"ok": True, "backup_created": False, "status": "SKIPPED_ALREADY_RUNNING"})
    result = vault.restore_sqlite_backup(source, tmp_path, saved["backup_file"], "QA", directory=folder)
    assert not result["ok"] and result["error"] == "safety_backup_failed"
    assert source.read_bytes() == original


def test_failed_recovery_stops_before_allocating_another_snapshot(tmp_path, monkeypatch):
    source = make_source(tmp_path)
    original = source.read_bytes()
    folder = tmp_path / "backups"
    folder.mkdir()
    workspace = staging.new_workspace(folder)
    partial = workspace / "snapshot.partial"
    partial.write_bytes(b"interrupted copy")
    real_unlink = Path.unlink
    def deny_partial(path, *args, **kwargs):
        if path == partial:
            raise PermissionError("QA_DENIED")
        return real_unlink(path, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", deny_partial)
    monkeypatch.setattr(vault, "ensure_backup_capacity", lambda *a, **k: pytest.fail("must stop before capacity"))
    result = vault.create_sqlite_backup(source, tmp_path, "QA", directory=folder)
    assert not result["ok"] and not result["backup_created"]
    assert result["failure_stage"] == "RECOVERY"
    assert result["storage"]["temporary_recovery"]["failed_count"] == 1
    assert list(folder.glob(".backup-work-*")) == [workspace]
    assert partial.read_bytes() == b"interrupted copy" and source.read_bytes() == original


def test_cleanup_failure_reports_completed_copy_truthfully_and_next_attempt_recovers(tmp_path, monkeypatch):
    source = make_source(tmp_path)
    folder = tmp_path / "backups"
    with monkeypatch.context() as patch:
        patch.setattr(vault, "remove_workspace", lambda *a: {"removed": False})
        result = vault.create_sqlite_backup(source, tmp_path, "QA", directory=folder)
    assert not result["ok"] and result["backup_created"]
    assert result["failure_stage"] == "CLEANUP"
    assert result["storage"]["temporary_cleanup_ok"] is False
    assert vault.validate_backup(tmp_path, result["backup_file"], directory=folder)["ok"]
    retry = vault.create_sqlite_backup(source, tmp_path, "QA", directory=folder)
    assert retry["ok"] and retry["storage"]["temporary_recovery"]["recovered_count"] == 1
    assert not list(folder.glob(".backup-work-*"))
