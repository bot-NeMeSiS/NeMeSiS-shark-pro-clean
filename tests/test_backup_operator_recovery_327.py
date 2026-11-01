"""Synthetic-only tests for the operator recovery tool; never touch /data."""
from __future__ import annotations

from contextlib import closing
import json
import hashlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "backup_operator_recovery_327.py"


class BackupOperatorRecovery327Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nemesis_backup_327_test_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.db"
        self.backups = self.root / "operator_327"
        with closing(sqlite3.connect(self.source)) as conn, conn:
            conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
            conn.executemany(
                "INSERT INTO sample(value) VALUES (?)",
                [(f"data-{i}",) for i in range(200)],
            )

    def cli(self, *extra):
        proc = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--db", str(self.source),
                "--backup-dir", str(self.backups),
                "--timeout", "60",
                *extra,
            ],
            capture_output=True, text=True, check=False, timeout=45,
        )
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        self.assertTrue(lines, proc.stderr)
        return proc, json.loads(lines[-1])

    def test_preflight_only_does_not_create_a_directory(self):
        process, result = self.cli()
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(result["ok"])
        self.assertEqual(result["code"], "READY")
        self.assertFalse(result["backup_created"])
        self.assertFalse(self.backups.exists())

    def test_backup_is_verified_and_restored_to_disposable_path(self):
        process, result = self.cli("--execute")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(result["ok"])
        self.assertTrue(result["backup_created"])
        self.assertTrue(result["isolated_restore_ok"])
        self.assertEqual(result["code"], "RESTORE_VERIFIED")
        self.assertEqual(len(list(self.backups.glob("database_*.db"))), 1)
        self.assertTrue((self.backups / result["backup_name"]).with_suffix(".json").is_file())
        self.assertFalse(list(self.backups.glob(".isolated_restore_327_*")))
        with closing(sqlite3.connect(self.source)) as conn, conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM sample").fetchone()[0], 200)
        second, check = self.cli("--verify-existing", result["backup_name"])
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(check["code"], "RESTORE_VERIFIED")

    def test_existing_archives_are_not_removed(self):
        self.backups.mkdir()
        old = self.backups / "database_20000101_000000_prior.db"
        old.write_bytes(b"historical-copy")
        process, result = self.cli("--execute")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(result["ok"])
        self.assertEqual(old.read_bytes(), b"historical-copy")

    def test_missing_source_refuses_execution_without_writes(self):
        self.source.unlink()
        process, result = self.cli("--execute")
        self.assertEqual(process.returncode, 2, process.stderr)
        self.assertEqual(result["code"], "SOURCE_UNAVAILABLE")
        self.assertFalse(self.backups.exists())

    def test_cannot_verify_arbitrary_path(self):
        self.backups.mkdir()
        process, result = self.cli("--verify-existing", "../outside.db")
        self.assertEqual(process.returncode, 2, process.stderr)
        self.assertEqual(result["code"], "INVALID_BACKUP_NAME")


    def test_recheck_rejects_unsealed_legacy_wal_state(self):
        self.backups.mkdir()
        selected = self.backups / "database_20000101_000000_legacy.db"
        with closing(sqlite3.connect(self.source)) as live:
            live.execute("PRAGMA journal_mode=WAL")
            with closing(sqlite3.connect(selected)) as archive:
                live.backup(archive)
        digest = hashlib.sha256(selected.read_bytes()).hexdigest()
        manifest = selected.with_suffix(".json")
        manifest.write_text(json.dumps({"valid": True, "sha256": digest,
                                       "size_bytes": selected.stat().st_size}), encoding="utf-8")
        manifest_before = manifest.read_bytes()
        with closing(sqlite3.connect(selected)) as writer:
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("UPDATE sample SET value='SYNTHETIC_UNSEALED' WHERE id=1")
            writer.commit()
            self.assertEqual(hashlib.sha256(selected.read_bytes()).hexdigest(), digest)
            process, result = self.cli("--verify-existing", selected.name)
            self.assertEqual(process.returncode, 2, process.stderr)
            self.assertFalse(result["ok"])
            self.assertEqual(result["code"], "HASH_OR_INTEGRITY_FAILED")
            self.assertEqual(hashlib.sha256(selected.read_bytes()).hexdigest(), digest)
            self.assertEqual(manifest.read_bytes(), manifest_before)
            self.assertTrue(selected.with_name(selected.name+"-wal").is_file())
            self.assertFalse(list(self.backups.glob(".isolated_restore_327_*")))

    def test_live_wal_commits_are_captured_without_changing_live_mode(self):
        with closing(sqlite3.connect(self.source)) as live:
            live.execute("PRAGMA journal_mode=WAL")
            live.execute("PRAGMA wal_autocheckpoint=0")
            live.execute("UPDATE sample SET value='SYNTHETIC_COMMITTED' WHERE id=1")
            live.commit()
            source_before = hashlib.sha256(self.source.read_bytes()).hexdigest()
            process, result = self.cli("--execute")
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(result["code"], "RESTORE_VERIFIED")
            selected = self.backups / result["backup_name"]
            self.assertEqual(selected.read_bytes()[18:20], b"\x01\x01")
            with closing(sqlite3.connect(selected)) as archive:
                self.assertEqual(archive.execute("SELECT value FROM sample WHERE id=1").fetchone()[0],
                                 "SYNTHETIC_COMMITTED")
            self.assertEqual(live.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), source_before)


if __name__ == "__main__":
    unittest.main()
