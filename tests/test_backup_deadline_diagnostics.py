"""Deadline faults on disposable SQLite copies; no providers or live data."""
import json
from pathlib import Path
import sqlite3

import pytest

from engines import data_vault_engine as vault


@pytest.fixture
def backup_case(tmp_path):
    source = tmp_path / "source.db"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)")
        conn.executemany("INSERT INTO users VALUES (?, ?)",
                         [(i, f"Synthetic {i}") for i in range(2000)])
    original = source.read_bytes()
    folder = tmp_path / "backups"
    previous = vault.create_sqlite_backup(source, tmp_path, "QA", directory=folder)
    assert previous["ok"]
    return source, folder, original, previous


def assert_unpublished(case, result):
    source, folder, original, previous = case
    assert result["ok"] is False and result["backup_created"] is False
    assert source.read_bytes() == original
    assert [p.name for p in folder.glob("database_*.db")] == [previous["backup_file"]]
    assert vault.sha256_file(previous["path"]) == previous["sha256"]
    assert not list(folder.glob(".backup-work-*"))
    assert result["storage"]["temporary_cleanup_ok"] is True


@pytest.mark.parametrize("timing", ["during", "after"])
def test_integrity_deadline_is_reported_and_no_later_phase_runs(backup_case, monkeypatch, timing):
    source, folder, _, _ = backup_case
    clock = [10.0]
    connect = sqlite3.connect

    class Destination(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if sql == "PRAGMA integrity_check" and timing == "during":
                clock[0] = 30.0
            result = super().execute(sql, *args, **kwargs)
            if sql == "PRAGMA integrity_check" and timing == "after":
                clock[0] = 30.0
            return result

    def connection(path, *args, **kwargs):
        if str(path).endswith("snapshot.partial"):
            kwargs["factory"] = Destination
        return connect(path, *args, **kwargs)

    monkeypatch.setattr(vault.sqlite3, "connect", connection)
    monkeypatch.setattr(vault.time, "monotonic", lambda: clock[0])
    result = vault.create_sqlite_backup(source, source.parent, "QA", directory=folder)
    assert_unpublished(backup_case, result)
    assert result["error"] == "backup_snapshot_timeout"
    assert result["failure_stage"] == "INTEGRITY"
    assert set(result["stage_durations_ms"]) == {"SNAPSHOT", "INTEGRITY", "CLEANUP"}


def test_unrelated_sqlite_interrupt_is_not_claimed_as_deadline(backup_case, monkeypatch):
    source, folder, _, _ = backup_case
    connect = sqlite3.connect

    class Destination(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if sql == "PRAGMA integrity_check":
                self.set_progress_handler(lambda: 1, 1)
            return super().execute(sql, *args, **kwargs)

    def connection(path, *args, **kwargs):
        if str(path).endswith("snapshot.partial"):
            kwargs["factory"] = Destination
        return connect(path, *args, **kwargs)

    monkeypatch.setattr(vault.sqlite3, "connect", connection)
    result = vault.create_sqlite_backup(source, source.parent, "QA", directory=folder)
    assert_unpublished(backup_case, result)
    assert result["error"] == "interrupted"
    assert result["failure_stage"] == "INTEGRITY"


def test_snapshot_overrun_does_not_start_integrity(backup_case, monkeypatch):
    source, folder, _, _ = backup_case
    clock = [10.0]
    connect = sqlite3.connect

    class Source(sqlite3.Connection):
        def backup(self, *args, **kwargs):
            result = super().backup(*args, **kwargs)
            clock[0] = 30.0
            return result

    def connection(path, *args, **kwargs):
        if kwargs.get("uri"):
            kwargs["factory"] = Source
        return connect(path, *args, **kwargs)

    monkeypatch.setattr(vault.sqlite3, "connect", connection)
    monkeypatch.setattr(vault.time, "monotonic", lambda: clock[0])
    result = vault.create_sqlite_backup(source, source.parent, "QA", directory=folder)
    assert_unpublished(backup_case, result)
    assert result["error"] == "backup_snapshot_timeout"
    assert result["failure_stage"] == "SNAPSHOT"
    assert set(result["stage_durations_ms"]) == {"SNAPSHOT", "CLEANUP"}


def test_manifest_deadline_prevents_publication_even_without_sql_callback(backup_case, monkeypatch):
    source, folder, _, _ = backup_case
    clock = [10.0]
    write_text = Path.write_text

    def slow_manifest(path, *args, **kwargs):
        result = write_text(path, *args, **kwargs)
        if path.name == "manifest.json.partial":
            clock[0] = 30.0
        return result

    monkeypatch.setattr(Path, "write_text", slow_manifest)
    monkeypatch.setattr(vault.time, "monotonic", lambda: clock[0])
    result = vault.create_sqlite_backup(source, source.parent, "QA", directory=folder)
    assert_unpublished(backup_case, result)
    assert result["error"] == "backup_snapshot_timeout"
    assert result["failure_stage"] == "MANIFEST"
    assert "PUBLICATION" not in result["stage_durations_ms"]


def test_stage_metrics_do_not_replace_integrity_hash_manifest_or_restore(backup_case):
    source, folder, original, previous = backup_case
    result = vault.create_sqlite_backup(source, source.parent, "QA", directory=folder)
    assert result["ok"] and result["backup_created"]
    assert set(result["stage_durations_ms"]) == {
        "SNAPSHOT", "INTEGRITY", "METADATA", "SYNC", "HASH", "MANIFEST",
        "PUBLICATION", "RETENTION", "CLEANUP",
    }
    assert all(type(v) is int and v >= 0 for v in result["stage_durations_ms"].values())
    manifest = json.loads(Path(result["path"]).with_suffix(".json").read_text())
    assert manifest["valid"] and manifest["records_summary"]["users"] == 2000
    assert manifest["sha256"] == vault.sha256_file(result["path"])
    assert vault.validate_backup(source.parent, result["backup_file"], directory=folder)["ok"]
    isolated = source.parent / "isolated.db"
    with sqlite3.connect(isolated) as conn:
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)")
    restored = vault.restore_sqlite_backup(isolated, source.parent, result["backup_file"],
                                           "QA", directory=folder)
    assert restored["ok"]
    with sqlite3.connect(isolated) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2000
    assert source.read_bytes() == original
    assert vault.sha256_file(previous["path"]) == previous["sha256"]
