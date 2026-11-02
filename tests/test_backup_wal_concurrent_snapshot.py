"""Concurrent backup regressions use owned SQLite fixtures and no external data."""
from contextlib import closing
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from engines import data_vault_engine as vault


class ConcurrentBackupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.temporary)
        self.source = self.root / "synthetic.sqlite"
        self.archives = self.root / "backups"
        self.enterContext(patch.dict(os.environ, {"DATA_BACKUP_DIR": str(self.archives)}))

    def exercise(self, mode, *, writes=None, fail=None, timeout=15.0, pause=0.0):
        writer = sqlite3.connect(self.source)
        self.addCleanup(writer.close)
        writer.execute("PRAGMA journal_mode=" + mode)
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)")
        writer.execute("INSERT INTO users VALUES(1,'generation-0')")
        writer.execute("CREATE TABLE epoch(value INTEGER)")
        writer.execute("INSERT INTO epoch VALUES(0)")
        writer.execute("CREATE TABLE payload(id INTEGER PRIMARY KEY, value BLOB)")
        writer.executemany("INSERT INTO payload VALUES(?,zeroblob(4096))",
                           ((i,) for i in range(2048)))
        writer.commit()
        writer.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
        pages = writer.execute("PRAGMA page_count").fetchone()[0]
        state = {"callbacks": 0, "commits": 0, "remaining": [], "pins": [],
                 "at_integrity": None, "wal_bytes_peak": 0, "closed_pins": []}
        native = vault.connect_readonly
        sources = []

        class ObservedSource:
            def __init__(inner, conn):
                inner.conn = conn

            def __getattr__(inner, name):
                return getattr(inner.conn, name)

            def close(inner):
                state["closed_pins"].append(inner.conn.in_transaction)
                inner.conn.close()

            def backup(inner, destination, **kwargs):
                sources.append(inner)
                original_progress = kwargs["progress"]

                def progress(status, remaining, total):
                    state["callbacks"] += 1
                    state["remaining"].append(remaining)
                    state["pins"].append(inner.conn.in_transaction)
                    # Bound this fixture by actual native copy steps, not a fake clock.
                    if state["callbacks"] > math.ceil(pages / 256) + 2:
                        raise RuntimeError("synthetic_copy_restarted_under_writes")
                    original_progress(status, remaining, total)
                    if pause:
                        time.sleep(pause)
                    if fail is not None:
                        raise fail
                    if status == sqlite3.SQLITE_OK and (writes is None or state["commits"] < writes):
                        state["commits"] += 1
                        generation = state["commits"]
                        writer.execute("UPDATE epoch SET value=?", (generation,))
                        writer.execute("UPDATE users SET name=?", (f"generation-{generation}",))
                        writer.commit()
                        wal = Path(str(self.source) + "-wal")
                        if wal.exists():
                            state["wal_bytes_peak"] = max(state["wal_bytes_peak"], wal.stat().st_size)

                return inner.conn.backup(destination, **{**kwargs, "progress": progress})

        def opener(path):
            conn = native(path)
            return ObservedSource(conn) if Path(path).resolve() == self.source.resolve() else conn

        original_stage = vault._emit_backup_stage

        def stage(name, status, **kwargs):
            if name == "INTEGRITY" and status == "started":
                state["at_integrity"] = sources[-1].conn.in_transaction
                state["checkpoint_at_integrity"] = writer.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            return original_stage(name, status, **kwargs)

        with patch.object(vault, "connect_readonly", opener), patch.object(vault, "_emit_backup_stage", stage):
            result = vault.create_sqlite_backup(self.source, self.root, "SYNTHETIC_WAL_QA",
                                               max_files=0, snapshot_timeout=timeout)
        state["live_epoch"] = writer.execute("SELECT value FROM epoch").fetchone()[0]
        state["mode_after"] = writer.execute("PRAGMA journal_mode").fetchone()[0]
        state["checkpoint_after"] = writer.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        return result, state

    def assert_sealed(self, result, state, epoch):
        self.assertTrue(result["ok"], result)
        snapshot = Path(result["path"])
        manifest = json.loads(snapshot.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), manifest["sha256"])
        with closing(sqlite3.connect(snapshot)) as copied:
            self.assertEqual(copied.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
            self.assertEqual(copied.execute("PRAGMA journal_mode").fetchone()[0], "delete")
            self.assertEqual(copied.execute("SELECT value FROM epoch").fetchone()[0], epoch)
            self.assertEqual(copied.execute("SELECT name FROM users").fetchone()[0], f"generation-{epoch}")
            self.assertEqual(copied.execute("SELECT COUNT(*) FROM payload").fetchone()[0], 2048)
        self.assertEqual(result["records_summary"]["users"], 1)
        self.assertFalse(state["at_integrity"])
        self.assertFalse(any(state["closed_pins"]))
        self.assertEqual(list(self.archives.glob(".backup-work-*")), [])

    def test_wal_copy_completes_coherently_despite_commits_between_every_step(self):
        result, state = self.exercise("WAL")
        self.assert_sealed(result, state, 0)
        self.assertGreater(state["commits"], 2)
        self.assertGreater(state["live_epoch"], 0)
        self.assertEqual(state["mode_after"], "wal")
        self.assertTrue(all(a > b for a, b in zip(state["remaining"], state["remaining"][1:])))
        self.assertEqual(state["checkpoint_at_integrity"], (0, 0, 0))
        self.assertGreater(state["wal_bytes_peak"], 0)
        self.assertLess(state["wal_bytes_peak"], 1024 * 1024)

    def test_delete_sources_keep_incremental_writes_and_no_long_read_transaction(self):
        result, state = self.exercise("DELETE", writes=2)
        self.assert_sealed(result, state, 2)
        self.assertFalse(any(state["pins"]))
        self.assertEqual(state["commits"], 2)
        self.assertEqual(state["mode_after"], "delete")

    def test_copy_error_releases_wal_and_never_publishes_partial_file(self):
        error = sqlite3.OperationalError("synthetic_native_copy_failure")
        result, state = self.exercise("WAL", fail=error)
        self.assertFalse(result["ok"])
        self.assertFalse(result["backup_created"])
        self.assertEqual(result["failure_stage"], "SNAPSHOT")
        self.assertEqual(result["error"], str(error))
        self.assertFalse(any(state["closed_pins"]))
        self.assertEqual(state["checkpoint_after"], (0, 0, 0))
        self.assertEqual(list(self.archives.glob("database_*")), [])
        self.assertEqual(list(self.archives.glob(".backup-work-*")), [])

    def test_real_deadline_releases_wal_without_publishing(self):
        result, state = self.exercise("WAL", timeout=0.02, pause=0.03)
        self.assertFalse(result["ok"])
        self.assertFalse(result["backup_created"])
        self.assertEqual(result["error"], "backup_snapshot_timeout")
        self.assertEqual(result["failure_stage"], "SNAPSHOT")
        self.assertTrue(any(state["pins"]))
        self.assertFalse(any(state["closed_pins"]))
        self.assertEqual(state["checkpoint_after"], (0, 0, 0))
        self.assertEqual(list(self.archives.glob("database_*")), [])
        self.assertEqual(list(self.archives.glob(".backup-work-*")), [])


class SnapshotPreparationTests(unittest.TestCase):
    """Fault injection targets connection boundaries, never substitutes backup data."""
    class Source:
        def __init__(self, modes=("wal", "wal"), prepare_error=None, copy_error=None, rollback_error=None):
            self.modes = iter(modes)
            self.prepare_error = prepare_error
            self.copy_error = copy_error
            self.rollback_error = rollback_error
            self.events = []

        def execute(self, sql):
            self.events.append(sql)
            if sql.startswith("SELECT") and self.prepare_error:
                raise self.prepare_error
            value = next(self.modes) if sql == "PRAGMA journal_mode" else 1

            class Cursor:
                def fetchone(inner):
                    self.events.append("consume")
                    return (value,)

                def fetchall(inner):
                    self.events.append("consume")
                    return [(value,)]

                def close(inner):
                    self.events.append("cursor_close")
            return Cursor()

        def rollback(self):
            self.events.append("rollback")
            if self.rollback_error:
                raise self.rollback_error

        def backup(self, destination, **kwargs):
            self.events.append("backup")
            if self.copy_error:
                raise self.copy_error

    def run_copy(self, source):
        vault._backup_with_wal_snapshot(source, object(), progress=lambda *_: None)

    def test_wal_rollback_follows_copy_and_materialized_read(self):
        source = self.Source()
        self.run_copy(source)
        events = source.events
        self.assertLess(events.index("BEGIN"), next(i for i, e in enumerate(events) if e.startswith("SELECT")))
        self.assertLess(events.index("consume", events.index("BEGIN")), events.index("backup"))
        self.assertEqual(events[-2:], ["backup", "rollback"])

    def test_delete_does_not_begin_or_rollback(self):
        source = self.Source(modes=("delete",))
        self.run_copy(source)
        self.assertNotIn("BEGIN", source.events)
        self.assertNotIn("rollback", source.events)
        self.assertEqual(source.events.count("backup"), 1)

    def test_mode_change_releases_before_copy(self):
        source = self.Source(modes=("wal", "delete"))
        self.run_copy(source)
        self.assertEqual(source.events[-2:], ["rollback", "backup"])

    def test_preparation_busy_and_locked_fall_back_after_release(self):
        for code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED, sqlite3.SQLITE_BUSY | (2 << 8)):
            with self.subTest(code=code):
                error = sqlite3.OperationalError("synthetic_preparation_lock")
                error.sqlite_errorcode = code
                source = self.Source(prepare_error=error)
                self.run_copy(source)
                self.assertEqual(source.events[-2:], ["rollback", "backup"])

    def test_unclassified_preparation_error_is_not_fallback(self):
        error = sqlite3.OperationalError("synthetic_without_code")
        source = self.Source(prepare_error=error)
        with self.assertRaises(sqlite3.OperationalError) as raised:
            self.run_copy(source)
        self.assertIs(raised.exception, error)
        self.assertNotIn("backup", source.events)
        self.assertEqual(source.events[-1], "rollback")

    def test_base_exception_releases_prepared_read(self):
        class StopCopy(BaseException):
            pass
        error = StopCopy()
        source = self.Source(prepare_error=error)
        with self.assertRaises(StopCopy) as raised:
            self.run_copy(source)
        self.assertIs(raised.exception, error)
        self.assertNotIn("backup", source.events)
        self.assertEqual(source.events[-1], "rollback")

    def test_copy_busy_is_not_retried(self):
        error = sqlite3.OperationalError("synthetic_copy_busy")
        error.sqlite_errorcode = sqlite3.SQLITE_BUSY
        source = self.Source(copy_error=error)
        with self.assertRaises(sqlite3.OperationalError) as raised:
            self.run_copy(source)
        self.assertIs(raised.exception, error)
        self.assertEqual(source.events.count("backup"), 1)
        self.assertEqual(source.events[-1], "rollback")

    def test_original_copy_error_survives_rollback_failure(self):
        error = sqlite3.OperationalError("synthetic_disk_full")
        source = self.Source(copy_error=error, rollback_error=sqlite3.OperationalError("rollback_error"))
        with self.assertRaises(sqlite3.OperationalError) as raised:
            self.run_copy(source)
        self.assertIs(raised.exception, error)

    def test_successful_copy_with_failed_release_is_not_accepted(self):
        error = sqlite3.OperationalError("synthetic_failed_release")
        source = self.Source(rollback_error=error)
        with self.assertRaises(sqlite3.OperationalError) as raised:
            self.run_copy(source)
        self.assertIs(raised.exception, error)

    def test_secondary_base_exception_cannot_replace_copy_failure(self):
        error = sqlite3.OperationalError("synthetic_primary_copy_failure")
        source = self.Source(copy_error=error, rollback_error=KeyboardInterrupt("synthetic_secondary_interrupt"))
        with self.assertRaises(sqlite3.OperationalError) as raised:
            self.run_copy(source)
        self.assertIs(raised.exception, error)

    def test_preparation_release_failure_never_enters_fallback(self):
        busy = sqlite3.OperationalError("synthetic_prepare_busy")
        busy.sqlite_errorcode = sqlite3.SQLITE_BUSY
        source = self.Source(prepare_error=busy, rollback_error=sqlite3.OperationalError("synthetic_release_failure"))
        with self.assertRaises(sqlite3.OperationalError):
            self.run_copy(source)
        self.assertNotIn("backup", source.events)
