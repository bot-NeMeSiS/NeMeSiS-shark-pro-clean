"""Archive digest binding against WAL, separate from live-WAL semantics."""
from contextlib import closing
from pathlib import Path
import hashlib
import json
import os
import runpy
import sqlite3
import time

import pytest
from engines import data_vault_engine as vault

ROOT = Path(__file__).resolve().parents[1]
OP = runpy.run_path(str(ROOT / "tools/backup_operator_recovery_327.py"))
VERIFY = OP["verify_and_restore_isolated"]
GLOBALS = VERIFY.__globals__


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(folder):
    return {p.name: sha(p) for p in folder.iterdir() if p.is_file()}


def sealed_bytes_unchanged(folder, selected, before):
    after = files(folder)
    cache_names = {selected.name + "-wal", selected.name + "-shm"}
    for name, digest in before.items():
        if name not in cache_names:
            assert after.get(name) == digest
    assert set(after) - set(before) <= cache_names
    wal = selected.with_name(selected.name + "-wal")
    if wal.exists():
        assert wal.stat().st_size == 0


@pytest.fixture
def legacy_wal(tmp_path):
    """Native SQLite copy models the self-contained WAL format before this fix."""
    source = tmp_path / "source.db"
    folder = tmp_path / "archives"
    folder.mkdir()
    selected = folder / "database_20000101_000000_legacy.db"
    with closing(sqlite3.connect(source)) as live:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT)")
        live.execute("INSERT INTO users VALUES(1,'SEALED_ORIGINAL')")
        live.commit()
        with closing(sqlite3.connect(selected)) as destination:
            live.backup(destination)
        assert selected.read_bytes()[18:20] == b"\x02\x02"
        manifest = {"valid": True, "size_bytes": selected.stat().st_size,
                    "sha256": sha(selected), "version": "SYNTHETIC_LEGACY",
                    "created_at": "2000-01-01T00:00:00+00:00"}
        selected.with_suffix(".json").write_text(json.dumps(manifest), encoding="utf-8")
        with vault.backup_directory_lock(folder):
            pass
        yield source, folder, selected, manifest


def mutate_wal(writer):
    writer.execute("PRAGMA wal_autocheckpoint=0")
    writer.execute("UPDATE users SET name='UNSEALED_CHANGED' WHERE id=1")
    writer.commit()


def test_legacy_standalone_wal_archive_preserves_sealed_bytes(legacy_wal):
    source, folder, selected, manifest = legacy_wal
    before = files(folder)
    assert vault.validate_backup(ROOT, selected.name, directory=folder)["ok"]
    bounded = vault.validate_backup(ROOT, selected.name, directory=folder, deadline=time.monotonic()+10)
    assert bounded["ok"] and bounded["results"][0]["actual"] == manifest["sha256"]
    with closing(vault.connect_archive_readonly(selected)) as conn:
        assert conn.execute("SELECT name FROM users").fetchone()[0] == "SEALED_ORIGINAL"
    result = VERIFY(folder, selected.name, 10)
    assert result["ok"] and result["code"] == "RESTORE_VERIFIED"
    sealed_bytes_unchanged(folder, selected, before)
    assert not list(folder.glob(".isolated_restore_327_*"))


def test_unsealed_wal_is_rejected_by_legacy_named_and_operator_readers(legacy_wal):
    _, folder, selected, manifest = legacy_wal
    with closing(sqlite3.connect(selected)) as writer:
        mutate_wal(writer)
        assert sha(selected) == manifest["sha256"], "WAL can change data without changing the sealed db"
        before = files(folder)
        assert vault.validate_backup(ROOT, selected.name, directory=folder)["ok"] is False
        bounded = vault.validate_backup(ROOT, selected.name, directory=folder, deadline=time.monotonic()+10)
        assert bounded["ok"] is False and bounded["error"] == "backup_archive_not_standalone"
        result = VERIFY(folder, selected.name, 10)
        assert result["ok"] is False and result["code"] == "HASH_OR_INTEGRITY_FAILED"
        assert files(folder) == before
        assert not list(folder.glob(".isolated_restore_327_*"))


def test_unsealed_archive_is_rejected_before_any_target_restore_write(legacy_wal, tmp_path, monkeypatch):
    _, folder, selected, manifest = legacy_wal
    target = tmp_path / "target.db"
    with closing(sqlite3.connect(target)) as conn:
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT)")
        conn.execute("INSERT INTO users VALUES(1,'TARGET_UNCHANGED')")
        conn.commit()
    target_hash = sha(target)
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid archive must be rejected before a safety backup or target restore")
    monkeypatch.setattr(vault, "create_sqlite_backup", forbidden)
    with closing(sqlite3.connect(selected)) as writer:
        mutate_wal(writer)
        before = files(folder)
        result = vault.restore_sqlite_backup(target, tmp_path, selected.name, "SYNTHETIC", directory=folder)
        assert result["ok"] is False and result["error"] == "backup_validation_failed"
        assert sha(target) == target_hash and files(folder) == before
        assert not list(folder.glob(".restore-*"))


def test_archive_connection_cannot_consume_wal_added_after_open(legacy_wal):
    _, folder, selected, manifest = legacy_wal
    with closing(vault.connect_archive_readonly(selected)) as reader:
        with closing(sqlite3.connect(selected)) as writer:
            mutate_wal(writer)
            assert sha(selected) == manifest["sha256"]
            assert writer.execute("SELECT name FROM users").fetchone()[0] == "UNSEALED_CHANGED"
            assert reader.execute("SELECT name FROM users").fetchone()[0] == "SEALED_ORIGINAL"
            with pytest.raises(sqlite3.OperationalError, match="readonly"):
                reader.execute("UPDATE users SET name='MUST_NOT_WRITE'")


@pytest.mark.parametrize("bounded", [False, True])
def test_wal_added_during_hash_cannot_be_certified(legacy_wal, monkeypatch, bounded):
    _, folder, selected, manifest = legacy_wal
    real = vault.sha256_file
    with closing(sqlite3.connect(selected)) as writer:
        def hashing(path, **kwargs):
            digest = real(path, **kwargs)
            mutate_wal(writer)
            return digest
        monkeypatch.setattr(vault, "sha256_file", hashing)
        options = {"deadline": time.monotonic()+10} if bounded else {}
        result = vault.validate_backup(ROOT, selected.name, directory=folder, **options)
        assert result["ok"] is False
        assert sha(selected) == manifest["sha256"]
        assert writer.execute("SELECT name FROM users").fetchone()[0] == "UNSEALED_CHANGED"


def test_wal_added_during_isolated_copy_is_not_consumed_or_certified(legacy_wal, monkeypatch):
    _, folder, selected, manifest = legacy_wal
    real = GLOBALS["connect_archive_readonly"]
    copied = []
    with closing(sqlite3.connect(selected)) as writer:
        class Observe:
            def __init__(self, conn):
                self.conn = conn
            def __getattr__(self, name):
                return getattr(self.conn, name)
            def close(self):
                self.conn.close()
            def backup(self, target, **kwargs):
                mutate_wal(writer)
                self.conn.backup(target, **kwargs)
                copied.append(target.execute("SELECT name FROM users").fetchone()[0])
        def changing(path):
            reader = real(path)
            return Observe(reader)
        monkeypatch.setitem(GLOBALS, "connect_archive_readonly", changing)
        result = VERIFY(folder, selected.name, 10)
        assert copied == ["SEALED_ORIGINAL"]
        assert result["ok"] is False and result["code"] != "RESTORE_VERIFIED"
        assert sha(selected) == manifest["sha256"]
        assert selected.with_name(selected.name+"-wal").is_file()
        assert not list(folder.glob(".isolated_restore_327_*"))


@pytest.mark.parametrize("source_mode", ["DELETE", "WAL"])
def test_new_snapshot_is_standalone_and_captures_live_commits(tmp_path, source_mode):
    source = tmp_path / "live.db"
    folder = tmp_path / "published"
    with closing(sqlite3.connect(source)) as live:
        live.execute("PRAGMA journal_mode="+source_mode)
        live.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT)")
        live.execute("INSERT INTO users VALUES(1,'CURRENT_COMMITTED')")
        live.commit()
        before = sha(source)
        with closing(vault.connect_readonly(source)) as reader:
            assert reader.execute("SELECT name FROM users").fetchone()[0] == "CURRENT_COMMITTED"
        made = vault.create_sqlite_backup(source, tmp_path, "SYNTHETIC", directory=folder,
                                         max_files=0, preserve_existing_backups=True)
        assert made["ok"] and made["backup_created"], made
        selected = Path(made["path"])
        assert selected.read_bytes()[18:20] == b"\x01\x01"
        assert sha(selected) == made["sha256"]
        assert live.execute("PRAGMA journal_mode").fetchone()[0].upper() == source_mode
        assert sha(source) == before
        before_archive = files(folder)
        with closing(vault.connect_archive_readonly(selected)) as reader:
            assert reader.execute("SELECT name FROM users").fetchone()[0] == "CURRENT_COMMITTED"
        assert files(folder) == before_archive


@pytest.mark.parametrize("suffix", ["-wal", "-journal"])
@pytest.mark.parametrize("kind", ["nonempty", "directory", "hardlink"])
def test_unsafe_archive_auxiliary_state_is_not_read_or_removed(legacy_wal, suffix, kind):
    _, folder, selected, _ = legacy_wal
    sidecar = selected.with_name(selected.name+suffix)
    if kind == "nonempty":
        sidecar.write_bytes(b"SYNTHETIC_UNSEALED_STATE")
    elif kind == "directory":
        sidecar.mkdir()
    else:
        original = folder / "owned-empty-file"
        original.write_bytes(b"")
        try:
            sidecar.hardlink_to(original)
        except OSError as exc:
            pytest.skip("Owned filesystem hardlinks unavailable: "+type(exc).__name__)
    before = files(folder)
    result = vault.validate_backup(ROOT, selected.name, directory=folder, deadline=time.monotonic()+10)
    assert result["ok"] is False and result["error"] == "backup_archive_not_standalone"
    assert sidecar.exists() and files(folder) == before


def test_empty_wal_and_unconsumed_shm_do_not_invalidate_sealed_bytes(legacy_wal):
    _, folder, selected, manifest = legacy_wal
    selected.with_name(selected.name+"-wal").write_bytes(b"")
    selected.with_name(selected.name+"-shm").write_bytes(b"")
    before = files(folder)
    result = VERIFY(folder, selected.name, 10)
    assert result["ok"] and result["sha256"] == manifest["sha256"]
    sealed_bytes_unchanged(folder, selected, before)


@pytest.mark.parametrize("safety_fails", [False, True])
def test_legacy_wal_archive_restore_uses_staged_sealed_bytes(legacy_wal, tmp_path, monkeypatch, safety_fails):
    _, folder, selected, _ = legacy_wal
    target = tmp_path / "target.db"
    unknown = folder / ".restore-unknown.partial-wal"
    unknown.write_bytes(b"SYNTHETIC_UNRELATED_KEEP")
    if safety_fails:
        monkeypatch.setattr(vault, "create_sqlite_backup", lambda *a, **k: {"ok": False, "backup_created": False})
    with closing(sqlite3.connect(target)) as live:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT)")
        live.execute("INSERT INTO users VALUES(1,'TARGET_OLD')")
        live.commit()
        result = vault.restore_sqlite_backup(target, tmp_path, selected.name, "SYNTHETIC", directory=folder)
        assert result["ok"] is not safety_fails, result
        if safety_fails:
            assert result["error"] == "safety_backup_failed"
        with closing(vault.connect_readonly(target)) as reader:
            expected = "TARGET_OLD" if safety_fails else "SEALED_ORIGINAL"
            assert reader.execute("SELECT name FROM users").fetchone()[0] == expected
    assert unknown.read_bytes() == b"SYNTHETIC_UNRELATED_KEEP"
    assert set(folder.glob(".restore-*")) == {unknown}


@pytest.mark.parametrize("name", ["archive # literal.db", "archive %23.db", "fútbol mañana.db"])
def test_archive_uri_keeps_literal_path_and_readonly_contract(legacy_wal, tmp_path, name):
    _, _, selected, _ = legacy_wal
    path = tmp_path / name
    with closing(sqlite3.connect(path)) as own:
        own.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT)")
        own.execute("INSERT INTO users VALUES(1,'SEALED_ORIGINAL')")
        own.commit()
    before = sha(path)
    names = set(tmp_path.iterdir())
    with closing(vault.connect_archive_readonly(path)) as conn:
        assert conn.execute("SELECT name FROM users").fetchone()[0] == "SEALED_ORIGINAL"
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("UPDATE users SET name='MUST_NOT_WRITE'")
    assert sha(path) == before and set(tmp_path.iterdir()) == names


def test_archive_read_transaction_blocks_checkpoint_of_unsealed_wal(legacy_wal):
    _, folder, selected, manifest = legacy_wal
    with closing(vault.connect_archive_readonly(selected)) as reader:
        assert reader.in_transaction
        with closing(sqlite3.connect(selected)) as writer:
            writer.execute("PRAGMA busy_timeout=1")
            mutate_wal(writer)
            outcome = writer.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            assert outcome[0] == 1
            assert sha(selected) == manifest["sha256"]
            assert reader.execute("SELECT name FROM users").fetchone()[0] == "SEALED_ORIGINAL"


def test_malformed_shared_index_is_rejected_without_rebuilding_it(legacy_wal):
    _, folder, selected, _ = legacy_wal
    shm = selected.with_name(selected.name+"-shm")
    shm.write_bytes(b"SYNTHETIC_NOT_A_SQLITE_SHARED_INDEX")
    before = files(folder)
    result = VERIFY(folder, selected.name, 10)
    assert result["ok"] is False
    assert files(folder) == before
