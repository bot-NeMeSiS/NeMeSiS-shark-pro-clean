"""Owned native App/state integration, authored for authentic-checkout POSIX CI.

This test runs the stock normal_boot child and checks three fixed owners in the
explicit co-located CE/runtime fixture against bytes restored in the same
workspace, under the existing audit/SQLite boundary and absolute deadline. It
does not establish continuous cross-store quiescence, real-data permission,
production layout, or full recovery.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from engines import data_vault_engine as vault
from engines import recovery_non_sqlite_state as state
from tools import backup_operator_recovery_327 as operator
from tools import recovery_app_probe as app_probe
from tools import recovery_state_adapter as adapter

ROOT = Path(__file__).resolve().parents[1]

def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


@unittest.skipUnless(os.name == "posix", "Native POSIX state confinement; not certified on Windows")
class NativeRestoredStateAppConsumptionTests(unittest.TestCase):
    def test_real_normal_boot_then_three_colocated_owner_reads_in_same_restore(self):
        # This test belongs in the authentic checkout, not an artificial source
        # tree. prepare_source below copies exactly the current admitted source.
        self.assertEqual(operator.ROOT, ROOT)
        self.assertEqual(Path(app_probe.__file__), ROOT / "tools/recovery_app_probe.py")
        self.assertTrue((ROOT / "app.py").is_file())
        with tempfile.TemporaryDirectory(prefix="owned_state_app_") as temporary:
            root = Path(temporary).absolute()
            root.chmod(0o700)
            database = root / "owned.sqlite3"
            backups = root / "backups"
            ce = root / "ce"
            runtime = root / "runtime"
            for path in (backups, ce, runtime):
                path.mkdir(mode=0o700)
            publication = backups / "private-state"
            publication.mkdir(mode=0o700)
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
                connection.executemany("INSERT INTO sample(value) VALUES (?)", [("owned-one",), ("owned-two",)])
            before_database = hashlib.sha256(database.read_bytes()).hexdigest()
            ce_issue = "OWNED-CE-SENTINEL-ISSUE"
            autopilot_issue = "OWNED-RUNTIME-AUTOPILOT-ISSUE"
            dormant_issue = "OWNED-DORMANT-RUNTIME-SENTINEL"
            recommendations = {"owned-restored-recommendation": {"title": "Owned CE fixture", "status": "OBSERVED"}}
            ce_bytes = _json_bytes({"recommendations": recommendations, "events": [], "snapshots": []})
            ce_sentinel_bytes = _json_bytes({"issues": [{"id": ce_issue, "title": "Owned co-located Sentinel fixture",
                                                       "status": "OPEN_REAL", "severity": "low"}], "events": []})
            autopilot_bytes = _json_bytes({"issues": [{"id": autopilot_issue, "title": "Owned autopilot fixture",
                                                      "status": "OPEN_REAL", "severity": "low"}]})
            dormant_runtime_sentinel_bytes = _json_bytes({"issues": [{"id": dormant_issue,
                                                                     "title": "Dormant duplicate root",
                                                                     "status": "OPEN_REAL", "severity": "low"}],
                                                         "events": []})
            decoy_recommendations = _json_bytes({"recommendations": {"owned-wrong-ce-root": {"title": "Wrong CE root"}}})
            ce_file = ce / "product_memory.json"
            ce_sentinel_file = ce / "sentinel_issues_memory.json"
            autopilot_file = runtime / "sentinel_autopilot_memory.json"
            dormant_runtime_sentinel_file = runtime / "sentinel_issues_memory.json"
            ce_file.write_bytes(ce_bytes)
            ce_sentinel_file.write_bytes(ce_sentinel_bytes)
            autopilot_file.write_bytes(autopilot_bytes)
            dormant_runtime_sentinel_file.write_bytes(dormant_runtime_sentinel_bytes)
            runtime_ce_decoys = runtime / "continuous_evolution_os"
            runtime_ce_decoys.mkdir(mode=0o700)
            product_decoy = runtime_ce_decoys / "product_memory.json"
            product_decoy.write_bytes(decoy_recommendations)
            originals = {path: path.read_bytes() for path in (
                ce_file, ce_sentinel_file, autopilot_file, dormant_runtime_sentinel_file, product_decoy)}
            scopes = tuple(sorted((state.Scope("ce", ce), state.Scope("legacy_runtime", runtime)),
                                  key=lambda scope: scope.role))
            authorization = state.Authorization("OWNED_APP_NATIVE_ONLY",
                tuple((scope.role, str(scope.source)) for scope in scopes), True, (str(database),))
            plan = adapter.StateRecoveryPlan("OWNED_APP_NATIVE_ONLY",
                hashlib.sha256(b"owned CI fixture; not real data-operation approval").hexdigest(),
                scopes, authorization, publication, layout_id=app_probe.COLOCATED_LAYOUT_ID)
            capture_deadline = time.monotonic() + 60.0
            snapshot_deadlines = []

            def create_snapshot(*, absolute_deadline):
                snapshot_deadlines.append(absolute_deadline)
                return vault.create_sqlite_backup(
                    database, ROOT, "OWNED_TEST", backup_type="owned_app",
                    created_by="owned_native_fixture", directory=backups, max_files=0,
                    preserve_existing_backups=True, snapshot_timeout=15.0,
                    absolute_deadline=absolute_deadline)

            handoff = adapter.capture_with_state(plan=plan, source=database,
                                                create_snapshot=create_snapshot, deadline=capture_deadline)
            self.assertTrue(handoff.ok, json.dumps(handoff.state_result))
            self.assertEqual(snapshot_deadlines, [capture_deadline], "one native capture callback; no retry")
            self.assertTrue(handoff.sqlite_result["ok"])
            backup_name = handoff.sqlite_result["backup_file"]
            archive = backups / backup_name
            archive_before = hashlib.sha256(archive.read_bytes()).hexdigest()
            bundle_before = hashlib.sha256(handoff.bundle.archive.read_bytes()).hexdigest()
            launches = []
            restore_deadlines = []
            native_popen = subprocess.Popen
            native_restore_state = state.restore_state
            native_archive_connect = operator.connect_archive_readonly

            def observe_native_restore(**kwargs):
                restore_deadlines.append(kwargs["deadline"])
                return native_restore_state(**kwargs)

            def launch_real_observed_child(command, **kwargs):
                # Observe the launch but invoke the exact stock child command unchanged.
                self.assertEqual(command, [sys.executable, "-I", "-B", str(Path(app_probe.__file__)), "--child"])
                self.assertEqual(kwargs["env"]["PATH"], str(Path(sys.executable).parent))
                self.assertEqual(set(kwargs["env"]) - {"SYSTEMROOT", "WINDIR"},
                                 {"PATH", "TMP", "TEMP", "TMPDIR", "PYTHONDONTWRITEBYTECODE",
                                  "PYTHONNOUSERSITE", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS",
                                  "CONTINUOUS_EVOLUTION_SAFE_MODE", "CONTINUOUS_EVOLUTION_STORAGE_ROOT"})
                self.assertEqual(kwargs["env"]["CONTINUOUS_EVOLUTION_SAFE_MODE"], "1")
                self.assertEqual(kwargs["env"]["CONTINUOUS_EVOLUTION_STORAGE_ROOT"],
                                 str(kwargs["cwd"].parent / "source" / "data" / "continuous_evolution_os"))
                self.assertEqual(kwargs["cwd"].name, "scratch")
                workspace = kwargs["cwd"].parent
                self.assertTrue(workspace.name.startswith(".isolated_restore_327_"))
                self.assertTrue((workspace / "restoration-test.db").is_file())
                launches.append(workspace)
                self.assertEqual(len(restore_deadlines), 1, "state restored before the stock child")
                return native_popen(command, **kwargs)

            with patch.object(state, "restore_state", side_effect=observe_native_restore), \
                 patch.object(operator, "connect_archive_readonly", wraps=native_archive_connect) as archive_connections, \
                 patch.object(app_probe.subprocess, "Popen", side_effect=launch_real_observed_child):
                result = operator.verify_and_restore_isolated(
                    backups, backup_name, 60, app_probe_mode="normal_boot", state_bundle=handoff.bundle)
            self.assertTrue(result["ok"], json.dumps(result))
            self.assertEqual(result["code"], "SQLITE_RESTORE_AND_GUEST_APP_SMOKE_VERIFIED")
            self.assertTrue(result["sqlite_restore_verified"])
            self.assertTrue(result["schema_match"])  # SQLite pre-boot phase, not post-migration equality.
            self.assertEqual(archive_connections.call_count, 1, "one archive connection for the native restore")
            self.assertEqual(len(launches), 1, "one actual child, not a fake success/second restore")
            self.assertEqual(len(restore_deadlines), 1)
            child = result["app_probe"]["child"]
            self.assertEqual(result["app_probe"]["child_exit"], 0)
            self.assertTrue(child["ok"])
            self.assertTrue(child["initialized"])
            self.assertFalse(child["initialization_error_present"])
            self.assertEqual(len(child["routes"]), len(app_probe.DEFAULT_ROUTES))
            self.assertTrue(all(row["ok"] and row["completed_read_fetches"] > 0 for row in child["routes"]))
            self.assertFalse(child["boundary_denials"])
            self.assertTrue(result["app_probe"]["state_restore"]["state_ready_before_app"])
            self.assertEqual(result["app_probe"]["state_restore"]["code"], "STATE_BYTES_VERIFIED_BEFORE_APP")
            self.assertEqual(result["app_probe"]["state_scope_roles"], ["ce", "legacy_runtime"])
            expected_consumers = [
                {"consumer_id": "ce_product_memory", "scope_role": "ce",
                 "relative_path": "data/continuous_evolution_os/product_memory.json",
                 "owner": "engines.product_review_system_engine.load_product_memory"},
                {"consumer_id": "ce_sentinel_issues", "scope_role": "ce",
                 "relative_path": "data/continuous_evolution_os/sentinel_issues_memory.json",
                 "owner": "engines.sentinel_issues_engine.load_sentinel_issues_memory"},
                {"consumer_id": "runtime_sentinel_autopilot", "scope_role": "legacy_runtime",
                 "relative_path": "data/runtime/sentinel_autopilot_memory.json",
                 "owner": "engines.sentinel_issues_engine._issues_from_autopilot_memory"},
            ]
            self.assertTrue(result["app_probe"]["bundle_all_files_restored_verified"])
            self.assertTrue(result["app_probe"]["canonical_consumer_consumption_verified"])
            self.assertEqual(result["app_probe"]["canonical_consumer_paths"], expected_consumers)
            proof = child["restored_state_consumption"]
            self.assertEqual(proof["schema"], "NEMESIS_CANONICAL_CONSUMER_OBSERVATION_V4")
            self.assertEqual(proof["layout_id"], app_probe.COLOCATED_LAYOUT_ID)
            self.assertEqual(proof["scope_roles"], ["ce", "legacy_runtime"])
            self.assertEqual(proof["observed_roles"], ["ce", "legacy_runtime"])
            self.assertEqual(proof["observed_consumer_ids"],
                             ["ce_product_memory", "ce_sentinel_issues", "runtime_sentinel_autopilot"])
            self.assertEqual(proof["canonical_consumer_paths"], expected_consumers)
            self.assertEqual(proof["mode"], "normal_boot")
            self.assertEqual(proof["layout_model"], app_probe.COLOCATED_LAYOUT_MODEL)
            self.assertEqual(proof["observation_scope"], "THREE_FIXED_CANONICAL_CONSUMERS_ONLY")
            self.assertFalse(proof["universal_scope_consumption_verified"])
            self.assertFalse(proof["production_layout_attested"])
            self.assertFalse(proof["full_application_recovery_certified"])
            for key in ("verified", "canonical_consumer_consumption_verified", "successful_full_file_reads",
                        "getters_read_only", "same_restored_workspace", "same_sqlite_boundary",
                        "same_deadline", "canonical_value_projections_match_restored_bytes",
                        "decoy_open_not_attempted_during_getters", "getters_wrote_nothing",
                        "bundle_all_files_restored_verified"):
                self.assertIs(proof[key], True, key)
            self.assertTrue(child["canonical_consumer_consumption_verified"])
            self.assertFalse(child["production_layout_attested"])
            self.assertFalse(child["full_application_recovery_certified"])
            self.assertTrue(result["app_probe"]["external_state_restoration_verified"])
            binding = result["app_probe"]["state_consumption_binding"]
            self.assertTrue(binding["verified"])
            self.assertTrue(binding["bundle_all_files_restored_verified"])
            self.assertTrue(binding["canonical_consumer_consumption_verified"])
            self.assertTrue(binding["state_ready_before_app"])
            self.assertEqual(binding["layout_id"], app_probe.COLOCATED_LAYOUT_ID)
            self.assertEqual(binding["canonical_consumer_paths"], expected_consumers)
            self.assertEqual(binding["canonical_consumer_ids"],
                             ["ce_product_memory", "ce_sentinel_issues", "runtime_sentinel_autopilot"])
            self.assertEqual(binding["consumer_mode"], "normal_boot")
            self.assertEqual(binding["layout_model"], app_probe.COLOCATED_LAYOUT_MODEL)
            self.assertEqual(binding["proposal_sha256"], handoff.bundle.proposal_sha256)
            self.assertTrue(binding["same_restored_workspace"])
            self.assertTrue(binding["same_sqlite_boundary"])
            self.assertTrue(binding["same_deadline"])
            self.assertEqual(binding["canonical_consumer_scope"], "THREE_FIXED_CANONICAL_CONSUMERS_ONLY")
            self.assertFalse(binding["universal_scope_consumption_verified"])
            self.assertFalse(binding["production_layout_attested"])
            self.assertFalse(binding["full_application_recovery_certified"])
            proof_wire = json.dumps(proof, sort_keys=True)
            for fixture_value in (ce_issue, autopilot_issue, dormant_issue, "owned-restored-recommendation"):
                self.assertNotIn(fixture_value, proof_wire)
            self.assertNotIn("legacy_sha256", proof)
            self.assertNotIn("ce_projection_sha256", proof)
            self.assertEqual(binding["backup_name"], backup_name)
            self.assertEqual(binding["sqlite_sha256"], handoff.bundle.sqlite.sha256)
            self.assertEqual(binding["state_archive_sha256"], handoff.bundle.archive_sha256)
            self.assertEqual(binding["state_manifest_sha256"], handoff.bundle.manifest_sha256)
            self.assertEqual(binding["bundle_scope_roles"], ["ce", "legacy_runtime"])
            for scope in (result, result["app_probe"], child):
                self.assertFalse(scope["full_application_recovery_certified"])
            self.assertFalse(child["authenticated_client_verified"])
            self.assertFalse(child["external_services_verified"])
            self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(), before_database)
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), archive_before)
            self.assertEqual(hashlib.sha256(handoff.bundle.archive.read_bytes()).hexdigest(), bundle_before)
            for path, original in originals.items():
                self.assertEqual(path.read_bytes(), original)
            self.assertEqual(len(list(backups.glob("database_*.db"))), 1)
            self.assertFalse(list(backups.glob(".isolated_restore_327_*")))
            self.assertTrue(all(not workspace.exists() for workspace in launches))


if __name__ == "__main__":
    unittest.main()
