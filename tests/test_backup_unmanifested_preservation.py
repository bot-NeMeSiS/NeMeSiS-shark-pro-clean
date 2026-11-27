"""Unmanifested candidates are preserved; disposable SQLite/files only."""
from pathlib import Path
from types import SimpleNamespace
import os

import pytest
from engines import data_vault_engine as vault
from test_data_vault_atomic import backup_source


@pytest.mark.parametrize("newer", [False, True])
def test_retention_keeps_unmanifested_candidate_outside_pair_limit(backup_source, newer):
    source, root = backup_source
    verified = vault.create_sqlite_backup(source, root, "SYNTHETIC_QA")
    assert verified["ok"]
    folder = Path(verified["path"]).parent
    candidate = folder / "database_unmanifested.db"
    content = source.read_bytes()
    candidate.write_bytes(content)
    stamp = Path(verified["path"]).stat().st_mtime + (60 if newer else -60)
    os.utime(candidate, (stamp, stamp))
    result = vault.apply_backup_retention(root, max_files=1)
    assert candidate.exists() and candidate.read_bytes() == content
    assert result["removed"] == [] and result["kept"] == 2
    assert candidate.name in result["preserved_unmanifested"]
    assert vault.validate_backup(root, verified["backup_file"])["ok"]
    assert not vault.validate_backup(root, candidate.name)["ok"]


def test_capacity_does_not_reclaim_an_unmanifested_candidate(backup_source, monkeypatch):
    source, root = backup_source
    folder = vault.backup_dir(root)
    folder.mkdir()
    candidate = folder / "database_unmanifested.db"
    content = source.read_bytes()
    candidate.write_bytes(content)
    monkeypatch.setattr(vault, "_sqlite_snapshot_estimate_bytes", lambda _: 1024)
    monkeypatch.setattr(vault.shutil, "disk_usage", lambda _: SimpleNamespace(free=1024, total=2**30))
    result = vault.ensure_backup_capacity(source, root)
    assert candidate.exists() and candidate.read_bytes() == content
    assert result["ok"] is False and result["error"] == "backup_storage_insufficient"
    assert result["removed"] == [] and result["preserved_verified"] == ""
    assert candidate.name in result["preserved_unmanifested"]


def test_pair_delete_rechecks_manifest_before_unlink(backup_source):
    source, root = backup_source
    made = vault.create_sqlite_backup(source, root, "SYNTHETIC_QA")
    assert made["ok"]
    item = vault.list_backups(root)[0]
    data = Path(item["path"]).read_bytes()
    Path(item["path"]).with_suffix(".json").unlink()
    assert vault._delete_backup_item(item) is False
    assert Path(item["path"]).read_bytes() == data


def test_retention_still_limits_known_pairs_without_counting_unknowns(backup_source):
    source, root = backup_source
    first = vault.create_sqlite_backup(source, root, "SYNTHETIC_QA")
    second = vault.create_sqlite_backup(source, root, "SYNTHETIC_QA")
    assert first["ok"] and second["ok"] and first["path"] != second["path"]
    old, latest = Path(first["path"]), Path(second["path"])
    stamp = latest.stat().st_mtime
    os.utime(old, (stamp - 60, stamp - 60))
    unknown = latest.parent / "database_unknown.db"
    unknown.write_bytes(b"retain for review")
    os.utime(unknown, (stamp + 60, stamp + 60))
    result = vault.apply_backup_retention(root, max_files=1)
    assert result["ok"] and result["removed"] == [old.name]
    assert not old.exists() and not old.with_suffix(".json").exists()
    assert latest.exists() and vault.validate_backup(root, latest.name)["ok"]
    assert unknown.read_bytes() == b"retain for review"
    assert result["kept"] == 2 and result["preserved_unmanifested"] == [unknown.name]


def test_retention_rechecks_manifest_after_inventory(backup_source, monkeypatch):
    source, root = backup_source
    first = vault.create_sqlite_backup(source, root, "SYNTHETIC_QA")
    second = vault.create_sqlite_backup(source, root, "SYNTHETIC_QA")
    assert first["ok"] and second["ok"]
    old, latest = Path(first["path"]), Path(second["path"])
    assert old != latest
    stamp = latest.stat().st_mtime
    os.utime(old, (stamp - 60, stamp - 60))
    content = old.read_bytes()
    original = vault.validate_backup
    def validation_then_manifest_disappears(*args, **kwargs):
        result = original(*args, **kwargs)
        old.with_suffix(".json").unlink(missing_ok=True)
        return result
    monkeypatch.setattr(vault, "validate_backup", validation_then_manifest_disappears)
    result = vault.apply_backup_retention(root, max_files=1)
    assert result["ok"] and result["removed"] == []
    assert old.read_bytes() == content and latest.exists()
    assert result["preserved_unmanifested"] == [old.name]
