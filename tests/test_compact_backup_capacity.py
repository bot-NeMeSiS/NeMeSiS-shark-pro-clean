"""Low-capacity backup and isolated restore; disposable databases only."""
import json
import itertools
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from engines import data_vault_engine as vault


def source_with_free_pages(tmp_path):
    source = tmp_path / "source.db"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO users(rowid,id,name) VALUES(42,'owner','Keep me')")
        conn.execute("CREATE TABLE scratch(id INTEGER PRIMARY KEY, payload BLOB)")
        conn.executemany("INSERT INTO scratch(payload) VALUES(zeroblob(4096))", [()] * 256)
        conn.execute("DELETE FROM scratch")
    return source


def test_compact_copy_fits_without_changing_source_or_previous_backup(tmp_path, monkeypatch):
    source = source_with_free_pages(tmp_path)
    folder = tmp_path / "backups"
    first = vault.create_sqlite_backup(source, tmp_path, "SIMULATED_QA", directory=folder)
    original = source.read_bytes()
    previous = Path(first["path"]).read_bytes()
    allocated = source.stat().st_size
    # There is enough space for useful pages plus the same safety margin,
    # but not for the original allocation plus that margin.
    free = 64 * 1024 * 1024 + allocated // 2
    monkeypatch.setattr(vault.shutil, "disk_usage", lambda _: SimpleNamespace(free=free, total=2**31))
    second = vault.create_sqlite_backup(source, tmp_path, "SIMULATED_QA", directory=folder)
    assert second["ok"] and second["backup_created"]
    assert second["storage"]["method"] == "vacuum_into"
    assert source.read_bytes() == original
    assert Path(first["path"]).read_bytes() == previous
    assert Path(second["path"]).stat().st_size < allocated // 2
    assert vault.validate_backup(tmp_path, second["backup_file"], directory=folder)["ok"]
    manifest = json.loads(Path(second["path"]).with_suffix(".json").read_text())
    assert manifest["records_summary"]["users"] == 1
    with sqlite3.connect(second["path"]) as conn:
        assert conn.execute("SELECT rowid,id,name FROM users").fetchall() == [(42, "owner", "Keep me")]
    # Restore only into a separate disposable target, with the ordinary API.
    monkeypatch.undo()
    target = tmp_path / "restore.db"
    with sqlite3.connect(target) as conn:
        conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY,name TEXT)")
    result = vault.restore_sqlite_backup(target, tmp_path, second["backup_file"], "SIMULATED_QA", directory=folder)
    assert result["ok"]
    with sqlite3.connect(target) as conn:
        assert conn.execute("SELECT rowid,id,name FROM users").fetchall() == [(42, "owner", "Keep me")]
    assert source.read_bytes() == original


def test_compact_copy_rejects_insufficient_margin(tmp_path, monkeypatch):
    source = source_with_free_pages(tmp_path)
    original = source.read_bytes()
    folder = tmp_path / "backups"
    monkeypatch.setattr(vault.shutil, "disk_usage", lambda _: SimpleNamespace(free=1024, total=2**31))
    result = vault.create_sqlite_backup(source, tmp_path, "SIMULATED_QA", directory=folder)
    assert not result["ok"] and not result["backup_created"]
    assert result["error"] == "backup_storage_insufficient"
    assert source.read_bytes() == original
    assert {p.name for p in folder.iterdir()} == {".backup.lock"}


def test_compact_copy_timeout_never_publishes(tmp_path, monkeypatch):
    source = source_with_free_pages(tmp_path)
    original = source.read_bytes()
    folder = tmp_path / "backups"
    free = 64 * 1024 * 1024 + source.stat().st_size // 2
    monkeypatch.setattr(vault.shutil, "disk_usage", lambda _: SimpleNamespace(free=free, total=2**31))
    clock = itertools.count()
    monkeypatch.setattr(vault.time, "monotonic", lambda: next(clock))
    result = vault.create_sqlite_backup(source, tmp_path, "SIMULATED_QA", directory=folder, snapshot_timeout=0.000001)
    assert not result["ok"] and not result["backup_created"]
    assert source.read_bytes() == original
    assert {p.name for p in folder.iterdir()} == {".backup.lock"}


def test_compact_copy_includes_committed_wal_and_schema(tmp_path, monkeypatch):
    source = source_with_free_pages(tmp_path)
    writer = sqlite3.connect(source)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE INDEX users_name ON users(name)")
        writer.execute("INSERT INTO users(rowid,id,name) VALUES(73,'wal','Committed')")
        writer.commit()
        original = source.read_bytes()
        wal = Path(str(source) + "-wal").read_bytes()
        free = 64 * 1024 * 1024 + source.stat().st_size // 2
        monkeypatch.setattr(vault.shutil, "disk_usage", lambda _: SimpleNamespace(free=free, total=2**31))
        result = vault.create_sqlite_backup(source, tmp_path, "SIMULATED_QA", directory=tmp_path / "backups")
        assert result["ok"]
        assert source.read_bytes() == original
        assert Path(str(source) + "-wal").read_bytes() == wal
        with sqlite3.connect(result["path"]) as copy:
            assert copy.execute("SELECT rowid,id,name FROM users ORDER BY rowid").fetchall() == [(42,'owner','Keep me'),(73,'wal','Committed')]
            assert copy.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='users_name'").fetchone()
    finally:
        writer.close()
