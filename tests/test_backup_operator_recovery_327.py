"""Synthetic-only tests for the operator recovery tool; never touch /data."""
from __future__ import annotations

import json
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
        with sqlite3.connect(self.source) as conn:
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
        with sqlite3.connect(self.source) as conn:
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


if __name__ == "__main__":
    unittest.main()
