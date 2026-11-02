"""Owned native App/state integration, authored for authentic-checkout POSIX CI.

This TEST entrypoint runs the complete existing normal_boot child first. It then
calls two real read-only stores under that child's still-installed audit/SQLite
boundary and the SAME absolute B deadline/native parent timeout. No App flags,
getters, initialization or child results are replaced. It does not establish
that the production CLI receipt itself observes these store reads, continuous
cross-store quiescence, real-data permission, or full recovery.
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

# A test-only entrypoint, not a substitute App or a fabricated child response.
# The production probe module is loaded in full from the authentic checkout.
# _run_child imports the full App from its real bounded source copy.
STORE_OBSERVER_CHILD = r"""
import hashlib, importlib.util, json, os, pathlib, sqlite3, sys, time

probe_path = pathlib.Path(sys.argv[1])
expected = json.loads(sys.argv[2])
spec = importlib.util.spec_from_file_location("owned_real_probe", probe_path)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
raw = sys.stdin.buffer.read(16385)
if len(raw) > 16384:
    raise SystemExit(3)
payload = json.loads(raw)
source = pathlib.Path(payload["source"])
legacy_path = source / "data/runtime/sentinel_issues_memory.json"
ce_path = source / "data/continuous_evolution_os/product_memory.json"
decoy_path = source / "data/runtime/continuous_evolution_os/product_memory.json"
phase = [None]
reads = {"legacy": 0, "ce": 0, "decoy": 0}

def observe_owned_reads(event, args):
    if phase[0] is None or event != "open" or not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    mode, flags = args[1:3]
    writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
        isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
    if writing:
        return
    path = pathlib.Path(os.fsdecode(args[0]))
    if not path.is_absolute():
        path = pathlib.Path.cwd() / path
    if phase[0] == "legacy" and path == legacy_path:
        reads["legacy"] += 1
    if phase[0] == "ce" and path == ce_path:
        reads["ce"] += 1
    if path == decoy_path:
        reads["decoy"] += 1

def require(condition, code):
    if not condition:
        raise probe.ProbeError(code)

sys.addaudithook(observe_owned_reads)
result = None
try:
    result = probe._run_child(payload)
    # Failure of actual initialization/routes is never upgraded or discarded.
    if result.get("ok") is True:
        try:
            probe._deadline(payload["deadline"])
            require(payload["mode"] == "normal_boot", "OWNED_STATE_MODE_MISMATCH")
            require(payload["deadline"] == expected["restore_deadline"], "OWNED_STATE_DEADLINE_RESTARTED")
            require(payload.get("restored_state_layout") == "DISJOINT_CE_LEGACY_V1", "OWNED_STATE_LAYOUT_MISMATCH")
            app = sys.modules["app"]
            require(pathlib.Path(app.__file__) == source / "app.py", "OWNED_APP_SOURCE_MISMATCH")
            require(pathlib.Path.cwd() == source, "OWNED_STATE_CWD_MISMATCH")
            require(os.environ.get("CONTINUOUS_EVOLUTION_STORAGE_ROOT") == str(ce_path.parent),
                    "OWNED_CE_ENV_MISMATCH")
            require(os.environ.get("CONTINUOUS_EVOLUTION_SAFE_MODE") != "1", "OWNED_LEGACY_ROOT_REDIRECTED")
            boundary = getattr(sqlite3.connect, "__self__", None)
            require(boundary is not None and boundary.source == source
                    and boundary.database == pathlib.Path(payload["database"])
                    and boundary.deadline == payload["deadline"]
                    and boundary.mode == "normal_boot", "OWNED_BOUNDARY_BINDING_MISMATCH")
            before_writes = boundary.fs_writes
            before_sql_writes = boundary.sql_writes
            legacy = sys.modules["engines.sentinel_issues_engine"]
            ce = sys.modules["engines.product_review_system_engine"]
            require(pathlib.Path(legacy.__file__) == source / "engines/sentinel_issues_engine.py",
                    "OWNED_LEGACY_SOURCE_MISMATCH")
            require(pathlib.Path(ce.__file__) == source / "engines/product_review_system_engine.py",
                    "OWNED_CE_SOURCE_MISMATCH")
            require(legacy.sentinel_issues_memory_path() == legacy_path, "OWNED_LEGACY_PATH_MISMATCH")
            require(ce._ce_storage() == ce_path.parent, "OWNED_CE_PATH_MISMATCH")

            # Default owner APIs: no root/storage override, fake getter, or now.
            phase[0] = "legacy"
            legacy_memory = legacy.load_sentinel_issues_memory()
            phase[0] = "ce"
            ce_memory = ce.load_product_memory()
            phase[0] = None
            probe._deadline(payload["deadline"])
            require(getattr(sqlite3.connect, "__self__", None) is boundary, "OWNED_BOUNDARY_CHANGED")
            require(not boundary.denials and not result["boundary_denials"], "OWNED_STATE_BOUNDARY_DENIAL")
            require(boundary.fs_writes == before_writes and boundary.sql_writes == before_sql_writes,
                    "OWNED_GETTER_WROTE_STATE")
            require(reads["legacy"] > 0 and reads["ce"] > 0 and reads["decoy"] == 0,
                    "OWNED_GETTER_READS_MISSING")
            require(legacy_memory.get("_storage_revision") == expected["legacy_sha256"],
                    "OWNED_LEGACY_BYTES_MISMATCH")
            require(any(isinstance(issue, dict) and issue.get("id") == expected["legacy_issue"]
                        for issue in legacy_memory.get("issues", [])), "OWNED_LEGACY_VALUE_MISSING")
            projection = json.dumps(ce_memory.get("recommendations"), sort_keys=True,
                                    separators=(",", ":"), ensure_ascii=True).encode("ascii")
            ce_digest = hashlib.sha256(projection).hexdigest()
            require(ce_digest == expected["ce_projection_sha256"], "OWNED_CE_VALUE_MISMATCH")
            # Report only booleans/digests of our own fixture, never state rows.
            result["owned_store_observation"] = {
                "schema": "OWNED_RESTORED_STATE_GETTERS_TEST_V1",
                "legacy_read_observed": True, "ce_read_observed": True,
                "decoy_not_read_by_getters": True, "recognized_state_matches": True,
                "same_sqlite_boundary_binding": True, "same_absolute_deadline_checked": True,
                "getters_wrote_nothing": True,
                "legacy_sha256": legacy_memory["_storage_revision"],
                "ce_projection_sha256": ce_digest,
                "production_cli_observer_coverage": False,
            }
        except BaseException as exc:
            phase[0] = None
            result["ok"] = False
            result["owned_store_observation"] = {
                "schema": "OWNED_RESTORED_STATE_GETTERS_TEST_V1", "ok": False,
                "code": str(exc) if isinstance(exc, probe.ProbeError) else "OWNED_STORE_OBSERVATION_FAILED",
                "error_type": type(exc).__name__,
            }
except BaseException as exc:
    result = {"schema": "NEMESIS_APP_PROBE_CHILD_V1", "ok": False,
              "code": str(exc) if isinstance(exc, probe.ProbeError) else "APP_PROBE_CHILD_FAILED",
              "error_type": type(exc).__name__}
print(json.dumps(result, ensure_ascii=True))
raise SystemExit(0 if result.get("ok") is True else 3)
"""


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


@unittest.skipUnless(os.name == "posix", "Native POSIX state confinement; not certified on Windows")
class NativeRestoredStateAppConsumptionTests(unittest.TestCase):
    def test_real_normal_boot_then_real_legacy_and_ce_reads_in_same_restore(self):
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
            legacy = root / "legacy"
            for path in (backups, ce, legacy):
                path.mkdir(mode=0o700)
            publication = backups / "private-state"
            publication.mkdir(mode=0o700)
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
                connection.executemany("INSERT INTO sample(value) VALUES (?)", [("owned-one",), ("owned-two",)])
            before_database = hashlib.sha256(database.read_bytes()).hexdigest()
            legacy_issue = "OWNED-RESTORED-ISSUE"
            legacy_bytes = _json_bytes({"issues": [{"id": legacy_issue, "title": "Owned recovery fixture",
                                                   "status": "OPEN_REAL", "severity": "low"}], "events": []})
            recommendations = {"owned-restored-recommendation": {"title": "Owned CE fixture", "status": "OBSERVED"}}
            ce_bytes = _json_bytes({"recommendations": recommendations, "events": [], "snapshots": []})
            decoy_bytes = _json_bytes({"recommendations": {"owned-decoy": {"title": "Wrong CE root"}}})
            legacy_file = legacy / "sentinel_issues_memory.json"
            ce_file = ce / "product_memory.json"
            legacy_file.write_bytes(legacy_bytes)
            ce_file.write_bytes(ce_bytes)
            decoy = legacy / "continuous_evolution_os"
            decoy.mkdir(mode=0o700)
            decoy_file = decoy / "product_memory.json"
            decoy_file.write_bytes(decoy_bytes)
            originals = {path: path.read_bytes() for path in (legacy_file, ce_file, decoy_file)}
            expected = {"legacy_issue": legacy_issue,
                        "legacy_sha256": hashlib.sha256(legacy_bytes).hexdigest(),
                        "ce_projection_sha256": hashlib.sha256(_json_bytes(recommendations)).hexdigest()}
            scopes = tuple(sorted((state.Scope("ce", ce), state.Scope("legacy_runtime", legacy)),
                                  key=lambda scope: scope.role))
            authorization = state.Authorization("OWNED_APP_NATIVE_ONLY",
                tuple((scope.role, str(scope.source)) for scope in scopes), True, (str(database),))
            plan = adapter.StateRecoveryPlan("OWNED_APP_NATIVE_ONLY",
                hashlib.sha256(b"owned CI fixture; not real data-operation approval").hexdigest(),
                scopes, authorization, publication)
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
                # Only the TEST entrypoint differs. All environment, cwd, pipes,
                # memory policy and the parent's original timeout are unchanged.
                self.assertEqual(command, [sys.executable, "-I", "-B", str(Path(app_probe.__file__)), "--child"])
                self.assertEqual(kwargs["env"]["PATH"], str(Path(sys.executable).parent))
                self.assertEqual(set(kwargs["env"]) - {"SYSTEMROOT", "WINDIR"},
                                 {"PATH", "TMP", "TEMP", "TMPDIR", "PYTHONDONTWRITEBYTECODE",
                                  "PYTHONNOUSERSITE", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"})
                self.assertEqual(kwargs["cwd"].name, "scratch")
                workspace = kwargs["cwd"].parent
                self.assertTrue(workspace.name.startswith(".isolated_restore_327_"))
                self.assertTrue((workspace / "restoration-test.db").is_file())
                launches.append(workspace)
                self.assertEqual(len(restore_deadlines), 1, "state restored before the actual child")
                return native_popen(
                    [*command[:3], "-c", STORE_OBSERVER_CHILD, str(Path(app_probe.__file__)),
                     json.dumps({**expected, "restore_deadline": restore_deadlines[0]}, ensure_ascii=True)], **kwargs)

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
            self.assertEqual(result["app_probe"]["state_scope_roles"], ["ce", "legacy_runtime"])
            proof = child["owned_store_observation"]
            self.assertEqual(proof["schema"], "OWNED_RESTORED_STATE_GETTERS_TEST_V1")
            for key in ("legacy_read_observed", "ce_read_observed", "decoy_not_read_by_getters",
                        "recognized_state_matches", "same_sqlite_boundary_binding",
                        "same_absolute_deadline_checked", "getters_wrote_nothing"):
                self.assertIs(proof[key], True, key)
            self.assertEqual(proof["legacy_sha256"], expected["legacy_sha256"])
            self.assertEqual(proof["ce_projection_sha256"], expected["ce_projection_sha256"])
            self.assertFalse(proof["production_cli_observer_coverage"])
            for scope in (result, result["app_probe"], child):
                self.assertFalse(scope["full_application_recovery_certified"])
            self.assertFalse(child["external_state_restoration_verified"])
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
