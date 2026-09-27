"""Backup publication and retention in disposable storage only."""
import json
import os
from pathlib import Path
import sqlite3

import pytest

from engines import data_vault_engine as vault


@pytest.fixture
def backup_source(tmp_path,monkeypatch):
    path=tmp_path/"source.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY,name TEXT)")
        conn.execute("INSERT INTO users VALUES('qa-user','QA')")
    monkeypatch.setenv("DATA_BACKUP_DIR",str(tmp_path/"backups"))
    monkeypatch.setenv("DATA_BACKUP_MAX_FILES","30")
    return path,tmp_path


def test_backup_is_not_published_until_manifest_and_database_are_complete(backup_source,monkeypatch):
    source,root=backup_source
    original=vault.sha256_file
    observed=[]
    def digest(path):
        observed.extend(vault.list_backups(root))
        return original(path)
    monkeypatch.setattr(vault,"sha256_file",digest)
    result=vault.create_sqlite_backup(source,root,"SIMULATED_QA")
    assert result["ok"] is True,result
    assert observed==[]
    assert vault.validate_backup(root)["ok"] is True


def test_two_backups_in_same_second_never_replace_each_other(backup_source,monkeypatch):
    source,root=backup_source
    monkeypatch.setattr(vault,"now_stamp",lambda:"20260927_120000")
    first=vault.create_sqlite_backup(source,root,"SIMULATED_QA")
    assert first["ok"] is True,first
    original=Path(first["path"]).read_bytes()
    with sqlite3.connect(source) as conn:
        conn.execute("INSERT INTO users VALUES('qa-two','QA 2')")
    second=vault.create_sqlite_backup(source,root,"SIMULATED_QA")
    assert first["ok"] and second["ok"]
    assert first["path"]!=second["path"]
    assert Path(first["path"]).read_bytes()==original
    assert len(vault.list_backups(root))==2


def test_failed_manifest_does_not_publish_partial_backup_or_prune(backup_source,monkeypatch):
    source,root=backup_source
    original=Path.write_text
    def fail_manifest(path,*args,**kwargs):
        if "json" in path.name:
            raise OSError("SIMULATED_QA_MANIFEST_FAILURE")
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,"write_text",fail_manifest)
    monkeypatch.setattr(vault,"apply_backup_retention",lambda *_:pytest.fail("failed backup cannot prune"))
    result=vault.create_sqlite_backup(source,root,"SIMULATED_QA")
    assert result["ok"] is False
    assert result["backup_created"] is False
    assert vault.list_backups(root)==[]
    assert list(vault.backup_dir(root).iterdir())==[]


def test_manifest_counts_describe_snapshot_not_later_source(backup_source,monkeypatch):
    source,root=backup_source
    original=vault.sha256_file
    def digest(path):
        with sqlite3.connect(source) as conn:
            conn.execute("INSERT OR IGNORE INTO users VALUES('qa-later','QA Later')")
        return original(path)
    monkeypatch.setattr(vault,"sha256_file",digest)
    result=vault.create_sqlite_backup(source,root,"SIMULATED_QA")
    assert result["ok"] is True
    with sqlite3.connect(result["path"]) as conn:
        count=conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    assert result["records_summary"]["users"]==count==1


def test_orphan_and_corrupt_database_are_not_valid_backups(backup_source):
    _,root=backup_source
    folder=vault.backup_dir(root);folder.mkdir()
    path=folder/"database_orphan.db";path.write_bytes(b"not a sqlite backup")
    assert vault.list_backups(root)[0]["valid"] is False
    assert vault.validate_backup(root)["ok"] is False
    path.with_suffix(".json").write_text(json.dumps({"valid":True,"sha256":vault.sha256_file(path)}))
    assert vault.validate_backup(root)["ok"] is False


def test_retention_preserves_last_valid_backup_when_newer_file_is_incomplete(backup_source,monkeypatch):
    source,root=backup_source
    valid=vault.create_sqlite_backup(source,root,"SIMULATED_QA")
    orphan=vault.backup_dir(root)/"database_new_incomplete.db";orphan.write_bytes(b"partial")
    future=Path(valid["path"]).stat().st_mtime+60
    os.utime(orphan,(future,future))
    monkeypatch.setenv("DATA_BACKUP_MAX_FILES","1")
    vault.apply_backup_retention(root)
    assert Path(valid["path"]).exists()
    assert vault.validate_backup(root,valid["backup_file"])["ok"] is True


def test_retention_does_not_trust_a_corrupt_newer_manifest(backup_source,monkeypatch):
    source,root=backup_source
    valid=vault.create_sqlite_backup(source,root,"SIMULATED_QA")
    corrupt=vault.backup_dir(root)/"database_new_corrupt.db";corrupt.write_bytes(b"corrupt")
    corrupt.with_suffix(".json").write_text(json.dumps({"valid":True,"sha256":vault.sha256_file(corrupt)}))
    future=Path(valid["path"]).stat().st_mtime+60
    os.utime(corrupt,(future,future))
    monkeypatch.setenv("DATA_BACKUP_MAX_FILES","1")
    vault.apply_backup_retention(root)
    assert Path(valid["path"]).exists()


def test_failed_database_publication_removes_its_manifest(backup_source,monkeypatch):
    source,root=backup_source
    original=os.replace
    def fail_database(src,dst):
        if Path(dst).suffix==".db":
            raise OSError("SIMULATED_QA_RENAME_FAILURE")
        return original(src,dst)
    monkeypatch.setattr(os,"replace",fail_database)
    result=vault.create_sqlite_backup(source,root,"SIMULATED_QA")
    assert not result["ok"] and not result["backup_created"]
    assert list(vault.backup_dir(root).iterdir())==[]


def test_retention_failure_is_reported_without_losing_completed_backup(backup_source,monkeypatch):
    source,root=backup_source
    first=vault.create_sqlite_backup(source,root,"SIMULATED_QA")
    monkeypatch.setenv("DATA_BACKUP_MAX_FILES","1")
    original=Path.unlink
    def fail_old(path,*args,**kwargs):
        if path==Path(first["path"]):
            raise PermissionError("SIMULATED_QA_RETENTION_FAILURE")
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,"unlink",fail_old)
    second=vault.create_sqlite_backup(source,root,"SIMULATED_QA")
    assert second["backup_created"] is True
    assert second["ok"] is False
    assert second["retention"]["ok"] is False
    assert second["retention"]["kept"]==2
    assert Path(first["path"]).exists() and Path(second["path"]).exists()


def test_legacy_admin_backup_uses_verified_unique_copies_in_its_configured_directory(backup_source, app_module, monkeypatch):
    source, root = backup_source
    folder = root / "legacy-backups"
    monkeypatch.setenv("BACKUP_DIR", str(folder))
    monkeypatch.setattr(app_module, "DB_PATH", str(source))
    first = app_module.create_database_backup("admin_manual")
    second = app_module.create_database_backup("daily_autonomous_system")
    assert first["ok"] and second["ok"]
    assert first["path"] != second["path"]
    assert Path(first["path"]).parent == folder
    assert first["reason"] == "admin_manual"
    assert first["size"] > 0 and first["removed"] == []
    manifest = json.loads(Path(first["path"]).with_suffix(".json").read_text())
    assert manifest["valid"] and manifest["sha256"] == vault.sha256_file(first["path"])
    assert {item["name"] for item in app_module.list_backups()} == {first["name"], second["name"]}
    assert not vault.backup_dir(root).exists()


def test_legacy_backup_manifest_failure_does_not_publish_or_prune(backup_source, app_module, monkeypatch):
    source, root = backup_source
    folder = root / "legacy-backups"
    monkeypatch.setenv("BACKUP_DIR", str(folder))
    monkeypatch.setattr(app_module, "DB_PATH", str(source))
    original = Path.write_text
    def fail_manifest(path, *args, **kwargs):
        if "json" in path.name:
            raise OSError("SIMULATED_QA_MANIFEST_FAILURE")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "write_text", fail_manifest)
    result = app_module.create_database_backup("admin_manual")
    assert result["ok"] is False and not result["backup_created"]
    assert list(folder.iterdir()) == []


def test_legacy_backup_listing_is_readonly(backup_source, app_module, monkeypatch):
    _, root = backup_source
    folder = root / "not-created-by-a-read"
    monkeypatch.setenv("BACKUP_DIR", str(folder))
    assert app_module.list_backups() == []
    assert not folder.exists()


def test_legacy_backup_reports_post_publication_failure_without_losing_copy(backup_source, app_module, monkeypatch):
    source, root = backup_source
    monkeypatch.setenv("BACKUP_DIR", str(root / "legacy-backups"))
    monkeypatch.setattr(app_module, "DB_PATH", str(source))
    def fail_retention(*args, **kwargs):
        raise OSError("SIMULATED_QA_RETENTION_FAILURE")
    monkeypatch.setattr(vault, "apply_backup_retention", fail_retention)
    result = app_module.create_database_backup("admin_manual")
    assert not result["ok"] and result["backup_created"]
    assert Path(result["path"]).is_file()
    assert result["name"] and result["size"] > 0
    assert result["error"] == "SIMULATED_QA_RETENTION_FAILURE"


def test_backup_includes_committed_wal_data_but_not_uncommitted_transaction(backup_source):
    source, root = backup_source
    writer = sqlite3.connect(source)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("INSERT INTO users VALUES('qa-committed','Committed')")
        writer.commit()
        writer.execute("INSERT INTO users VALUES('qa-uncommitted','Uncommitted')")
        result = vault.create_sqlite_backup(source, root, "SIMULATED_QA")
        assert result["ok"], result
        with sqlite3.connect(result["path"]) as copied:
            assert {row[0] for row in copied.execute("SELECT id FROM users")} == {"qa-user", "qa-committed"}
        assert result["records_summary"]["users"] == 2
        assert vault.validate_backup(root, result["backup_file"])["ok"]
    finally:
        writer.rollback()
        writer.close()
