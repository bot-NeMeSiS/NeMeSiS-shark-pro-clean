"""Native, owned-fixture integration tests for the optional opaque-state overlay.

Artifact only: copy into the sealed checkout's tests/ directory before CI.
This file has deliberately not been executed on the Windows workstation.
The POSIX case uses a tiny SQLite fixture and opaque owned bytes only. Its
child-process seam returns an explicit NOT RUN response after asserting that
both restored opaque roots were present before launch; it does not import App,
exercise a Flask getter, or certify that App consumes restored state.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from engines import data_vault_engine as vault
from engines import recovery_non_sqlite_state as state
from tools import backup_operator_recovery_327 as operator
from tools import recovery_app_probe as app_probe
from tools import recovery_state_adapter as adapter


class _OwnedFixture:
    """A private temp tree, a tiny local DB, and non-secret opaque byte markers."""

    def __init__(self, root: Path):
        self.root = root.absolute()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.database = self.root / "owned-source.sqlite3"
        self.backups = self.root / "owned-backups"
        self.publication = self.root / "owned-state-publication"
        self.ce = self.root / "owned-ce"
        self.legacy = self.root / "owned-legacy-runtime"
        self.project = self.root / "owned-probe-project"
        for path in (self.backups, self.publication, self.ce, self.legacy, self.project):
            path.mkdir(mode=0o700)
            if os.name == "posix":
                path.chmod(0o700)

        self.project.joinpath("app.py").write_text(
            "# OWNED SOURCE MARKER ONLY; THIS APP IS NEVER IMPORTED BY THIS TEST.\n",
            encoding="utf-8",
        )
        self.ce_bytes = b"owned CE state\x00\xff\nopaque"
        self.legacy_bytes = b"owned legacy runtime\x00\x80opaque"
        self.ce_file = self.ce / "owned-interface-state.bin"
        self.legacy_file = self.legacy / "owned-runtime-state.bin"
        self.ce_file.write_bytes(self.ce_bytes)
        self.legacy_file.write_bytes(self.legacy_bytes)

        connection = sqlite3.connect(str(self.database))
        try:
            connection.execute("CREATE TABLE owned_fixture (fixture_id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
            connection.executemany(
                "INSERT INTO owned_fixture(value) VALUES (?)",
                (("owned-row-1",), ("owned-row-2",)),
            )
            connection.commit()
        finally:
            connection.close()

        self.scopes = tuple(sorted((state.Scope("ce", self.ce),
                                    state.Scope("legacy_runtime", self.legacy)),
                                   key=lambda scope: scope.role))
        self.authorization = state.Authorization(
            "OWNED_NATIVE_ONLY",
            tuple((scope.role, str(scope.source)) for scope in self.scopes),
            True,
            (str(self.database),),
        )
        self.plan = adapter.StateRecoveryPlan(
            "OWNED_NATIVE_ONLY",
            hashlib.sha256(b"owned test proposal; not an authorization grant").hexdigest(),
            self.scopes,
            self.authorization,
            self.publication,
        )

    def capture_once(self, *, mutate_after_snapshot: bool = False):
        """Run native state bracketing and one real SQLite backup on owned paths."""
        deadline = time.monotonic() + 60.0
        scan_deadlines = []
        sqlite_deadlines = []
        recovery_calls = []
        real_scan = state._scan
        real_recover = vault.recover_abandoned_workspaces

        def tracked_scan(scopes, limits, deadline_arg, writer=None, protected=()):
            scan_deadlines.append(deadline_arg)
            return real_scan(scopes, limits, deadline_arg, writer, protected)

        def tracked_recovery(*args, **kwargs):
            recovery_calls.append(True)
            return real_recover(*args, **kwargs)

        def create_snapshot(*, absolute_deadline):
            sqlite_deadlines.append(absolute_deadline)
            result = vault.create_sqlite_backup(
                self.database,
                self.project,
                "OWNED_TEST",
                backup_type="owned_native",
                created_by="owned_test_fixture",
                directory=self.backups,
                max_files=0,
                snapshot_timeout=15.0,
                preserve_existing_backups=True,
                absolute_deadline=absolute_deadline,
            )
            if mutate_after_snapshot:
                self.ce_file.write_bytes(b"changed owned CE bytes after the one SQLite snapshot")
            return result

        with patch.object(state, "_scan", side_effect=tracked_scan), \
             patch.object(vault, "recover_abandoned_workspaces", side_effect=tracked_recovery):
            result = adapter.capture_with_state(
                plan=self.plan,
                source=self.database,
                create_snapshot=create_snapshot,
                deadline=deadline,
            )

        return result, deadline, scan_deadlines, sqlite_deadlines, recovery_calls


@unittest.skipUnless(os.name == "posix", "Native POSIX FD integration; Windows fail-closed case is separate")
class NativeOwnedStateIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="owned_non_sqlite_native_")
        self.addCleanup(self.temp.cleanup)
        self.fx = _OwnedFixture(Path(self.temp.name))

    def test_one_real_snapshot_and_one_isolated_restore_put_both_opaque_roots_before_child(self):
        handoff, capture_deadline, scan_deadlines, sqlite_deadlines, recovery_calls = self.fx.capture_once()
        self.assertTrue(handoff.ok, handoff.state_result)
        self.assertIsNotNone(handoff.bundle)
        self.assertEqual(len(sqlite_deadlines), 1, "the owned SQLite snapshot callback is single-use")
        self.assertEqual(sqlite_deadlines, [capture_deadline])
        self.assertEqual(scan_deadlines, [capture_deadline, capture_deadline],
                         "the before/after state scans share one absolute monotonic deadline")
        self.assertEqual(len(recovery_calls), 1, "one real backup call performs one owned-workspace recovery pass")
        sqlite_result = handoff.sqlite_result
        self.assertTrue(sqlite_result["ok"])
        self.assertTrue(sqlite_result["backup_created"])
        backup_path = self.fx.backups / sqlite_result["backup_file"]
        self.assertTrue(backup_path.is_file())
        self.assertTrue((self.fx.backups / sqlite_result["manifest"]).is_file())

        # Negative binding guards run before any isolated SQLite restore.
        with self.assertRaisesRegex(adapter.HandoffError, "FOREIGN_VERIFIED_SQLITE_ARCHIVE"):
            adapter.bind_verified_sqlite(
                handoff.bundle,
                backup_name="database_FOREIGN_OWNED.db",
                sqlite_sha256=handoff.bundle.sqlite.sha256,
                deadline=time.monotonic() + 10,
            )
        with self.assertRaisesRegex(adapter.HandoffError, "FOREIGN_VERIFIED_SQLITE_ARCHIVE"):
            adapter.bind_verified_sqlite(
                handoff.bundle,
                backup_name=handoff.bundle.backup_name,
                sqlite_sha256="0" * 64,
                deadline=time.monotonic() + 10,
            )

        # The restore adapter rejects workspace/path substitution before its
        # native state restore is called and before any child is eligible.
        path_workspace = self.fx.root / ".isolated_restore_327_path_guard"
        path_workspace.mkdir(mode=0o700)
        (path_workspace / "source").mkdir(mode=0o700)
        db_marker = path_workspace / "restoration-test.db"
        db_marker.write_bytes(b"OWNED NON-SQLITE DATABASE IDENTITY MARKER")
        with patch.object(state, "restore_state", wraps=state.restore_state) as native_restore:
            with self.assertRaisesRegex(adapter.HandoffError, "STATE_RESTORE_WORKSPACE_BINDING_FAILED"):
                adapter.restore_before_app(
                    handoff.bundle,
                    source=path_workspace / "foreign-source",
                    restored_database=db_marker,
                    workspace=path_workspace,
                    database_info=db_marker.stat(),
                    deadline=time.monotonic() + 10,
                )
            native_restore.assert_not_called()
        self.assertFalse((path_workspace / "source" / "data").exists())

        # Exercise the existing SQLite verifier/restore exactly once using the
        # actual owned backup and real opaque-state restore. Only its final
        # child process is replaced; the replacement asserts ordering and then
        # explicitly reports NOT RUN so no App code or getters execute.
        events = []
        native_restore_results = []
        real_state_restore = state.restore_state

        def tracked_state_restore(**kwargs):
            events.append("opaque_restore_started")
            restored_state = real_state_restore(**kwargs)
            native_restore_results.append(restored_state)
            events.append("opaque_restore_finished")
            return restored_state

        class NotRunAppChild:
            def __init__(child_self, command, **kwargs):
                events.append("app_child_not_run_boundary")
                workspace = Path(kwargs["cwd"]).parent
                ce_path = workspace / "source" / "data" / "continuous_evolution_os" / self.fx.ce_file.name
                legacy_path = workspace / "source" / "data" / "runtime" / self.fx.legacy_file.name
                self.assertEqual(ce_path.read_bytes(), self.fx.ce_bytes)
                self.assertEqual(legacy_path.read_bytes(), self.fx.legacy_bytes)
                self.assertTrue((workspace / "restoration-test.db").is_file())
                child_self.returncode = 0

            def __enter__(child_self):
                return child_self

            def __exit__(child_self, exc_type, exc_value, traceback):
                return False

            def communicate(child_self, input=None, timeout=None):
                payload = json.loads(input.decode("utf-8"))
                # Deliberately not a successful or simulated App result.
                result = {
                    "schema": "NEMESIS_APP_PROBE_CHILD_V1",
                    "ok": False,
                    "code": "OWNED_CHILD_NOT_EXECUTED",
                    "nonce": payload["nonce"],
                    "mode": payload["mode"],
                    "routes": [],
                }
                return json.dumps(result).encode("utf-8"), b""

            def kill(child_self):
                raise AssertionError("the non-executed child stub must not be killed")

        with patch.object(operator, "ROOT", self.fx.project), \
             patch.object(state, "restore_state", side_effect=tracked_state_restore), \
             patch.object(app_probe.subprocess, "Popen", new=NotRunAppChild):
            verified = operator.verify_and_restore_isolated(
                self.fx.backups,
                handoff.bundle.backup_name,
                60,
                app_probe_mode="read_only",
                state_bundle=handoff.bundle,
            )

        self.assertEqual(len(native_restore_results), 1, "one native opaque-state recovery before child boundary")
        self.assertTrue(native_restore_results[0]["ok"], native_restore_results[0])
        self.assertTrue(native_restore_results[0]["state_ready_before_app"])
        self.assertFalse(native_restore_results[0]["app_started"])
        self.assertLess(events.index("opaque_restore_finished"), events.index("app_child_not_run_boundary"))
        self.assertEqual(verified["code"], "SQLITE_RESTORED_APP_NOT_VERIFIED")
        self.assertTrue(verified["sqlite_restore_verified"])
        self.assertFalse(verified["full_application_recovery_certified"])
        self.assertFalse(verified["app_probe"]["ok"])
        self.assertEqual(verified["app_probe"]["child"]["code"], "OWNED_CHILD_NOT_EXECUTED")

    def test_foreign_receipt_hash_and_archive_path_fail_before_state_materialization_or_child(self):
        handoff, _deadline, _scans, _sqlite_deadlines, _recoveries = self.fx.capture_once()
        self.assertTrue(handoff.ok, handoff.state_result)
        bundle = handoff.bundle
        no_child_calls = []

        foreign_receipt = replace(bundle.sqlite, artifact_id="FOREIGN_OWNED_OPERATION")
        foreign_bundle = replace(bundle, operation_id="FOREIGN_OWNED_OPERATION", sqlite=foreign_receipt)
        bad_hash_bundle = replace(bundle, archive_sha256="0" * 64)
        foreign_path = self.fx.root / "foreign-state-archive.tar"
        foreign_path.write_bytes(b"owned foreign archive marker; not executable")
        foreign_path.chmod(0o600)
        foreign_path_bundle = replace(bundle, archive=foreign_path)

        for label, candidate in (("receipt", foreign_bundle), ("archive hash", bad_hash_bundle),
                                 ("archive path", foreign_path_bundle)):
            with self.subTest(label=label):
                workspace = self.fx.root / (".isolated_restore_327_invalid_" + label.replace(" ", "_"))
                workspace.mkdir(mode=0o700)
                marker = workspace / "restoration-test.db"
                marker.write_bytes(b"OWNED NON-SQLITE DATABASE IDENTITY MARKER")
                with patch.object(app_probe.subprocess, "Popen") as child:
                    result = app_probe.run_app_probe(
                        project_root=self.fx.project,
                        restored_database=marker,
                        workspace=workspace,
                        deadline=time.monotonic() + 20,
                        mode="read_only",
                        state_bundle=candidate,
                    )
                self.assertFalse(result["ok"])
                self.assertEqual(result["code"], "STATE_NOT_READY_BEFORE_APP")
                self.assertFalse((workspace / "source" / "data").exists(),
                                 "foreign state must fail before opaque bytes are materialized")
                child.assert_not_called()
                no_child_calls.append(label)
        self.assertEqual(no_child_calls, ["receipt", "archive hash", "archive path"])

    def test_post_capture_state_change_keeps_the_one_published_sqlite_copy_without_retry(self):
        handoff, capture_deadline, scans, sqlite_deadlines, recovery_calls = self.fx.capture_once(
            mutate_after_snapshot=True,
        )
        self.assertFalse(handoff.ok)
        self.assertEqual(handoff.state_result["code"], "STATE_CHANGED_ACROSS_SQLITE_INTERVAL")
        self.assertIsNone(handoff.bundle)
        self.assertEqual(sqlite_deadlines, [capture_deadline])
        self.assertEqual(scans, [capture_deadline, capture_deadline])
        self.assertEqual(len(recovery_calls), 1)
        disposition = adapter.public_sqlite_disposition(handoff)
        self.assertTrue(disposition["backup_created"])
        self.assertEqual(disposition["sqlite_disposition"], "PRESERVE_DO_NOT_RETRY")
        self.assertTrue((self.fx.backups / handoff.sqlite_result["backup_file"]).is_file())
        self.assertTrue((self.fx.backups / handoff.sqlite_result["manifest"]).is_file())


@unittest.skipUnless(os.name == "nt", "Windows-only fail-closed assertion; no SQLite fixture is created")
class WindowsFailClosedBeforeSqlTests(unittest.TestCase):
    def test_capture_rejects_before_the_sqlite_snapshot_callback(self):
        with tempfile.TemporaryDirectory(prefix="owned_windows_fail_closed_") as temp:
            root = Path(temp).absolute()
            ce, legacy, publication, source = (root / name for name in
                                                ("ce", "legacy", "private-publication", "owned-source.sqlite3"))
            scopes = tuple(sorted((state.Scope("ce", ce), state.Scope("legacy_runtime", legacy)),
                                  key=lambda scope: scope.role))
            authorization = state.Authorization(
                "OWNED_WINDOWS_ONLY",
                tuple((scope.role, str(scope.source)) for scope in scopes),
                True,
                (str(source),),
            )
            plan = adapter.StateRecoveryPlan(
                "OWNED_WINDOWS_ONLY",
                hashlib.sha256(b"Windows fail-closed fixture").hexdigest(),
                scopes,
                authorization,
                publication,
            )
            snapshot_calls = []
            result = adapter.capture_with_state(
                plan=plan,
                source=source,
                create_snapshot=lambda **kwargs: snapshot_calls.append(kwargs),
                deadline=time.monotonic() + 10,
            )
        self.assertFalse(result.ok)
        self.assertEqual(result.state_result["code"], "STRONG_FD_PRIMITIVES_UNSUPPORTED")
        self.assertFalse(result.state_result["sqlite_callback_invoked"])
        self.assertIsNone(result.sqlite_result)
        self.assertEqual(snapshot_calls, [], "fail closed before any SQLite callback/SQL access")
        self.assertEqual(adapter.public_sqlite_disposition(result)["sqlite_disposition"], "NOT_INVOKED")
