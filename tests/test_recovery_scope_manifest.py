"""Owned files only: inventory is not a snapshot or recovery certificate."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import recovery_scope_manifest as scope


POSIX_HASH = os.name == "posix" and bool(getattr(os, "O_NOFOLLOW", 0)) and os.open in os.supports_dir_fd


@unittest.skipUnless(POSIX_HASH, "Native confined inventory requires POSIX; separate tests verify Windows fails closed.")
class RecoveryScopeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.db = self.root / "owned.sqlite"
        # Deliberately not SQLite: the inventory must not connect or read it.
        self.db.write_bytes(b"synthetic database metadata only")
        self.ce = self.root / "ce"
        self.runtime = self.root / "runtime"
        self.ce.mkdir()
        self.runtime.mkdir()

    def write(self, name, content=b"owned state", *, root=None):
        path = (root or self.ce) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def collect(self, **kwargs):
        return scope.collect_manifest(database=self.db, roots={"ce": self.ce, "legacy_runtime": self.runtime},
                                      environment={"SECRET_KEY": "NEVER_DISCLOSE_VALUE"}, **kwargs)

    @staticmethod
    def codes(report):
        return {item["code"] for item in report["issues"]}

    def test_metadata_does_not_read_database_or_mutate_files(self):
        state = self.write("automation_control.json", b'{"paused":true}')
        before = {path: path.read_bytes() for path in (state, self.db)}
        native = scope._open_for_hash
        opened = []

        def observe(path):
            opened.append(path)
            self.assertNotEqual(path, self.db)
            return native(path)

        with patch.object(scope, "_open_for_hash", side_effect=observe):
            report = self.collect()
        self.assertEqual(before, {path: path.read_bytes() for path in before})
        self.assertEqual(opened, [state])
        self.assertEqual(report["database"]["file_bytes"], self.db.stat().st_size)
        self.assertFalse(report["database"]["live_database_or_wal_hashed"])
        self.assertFalse(report["recovery_certified"])
        self.assertFalse(report["backup_created"])
        self.assertFalse(report["restore_created"])
        self.assertEqual(report["content_mode"], "HASH_KNOWN_STATE")
        fact = report["files"][0]
        if POSIX_HASH:
            self.assertEqual(fact["sha256"], hashlib.sha256(before[state]).hexdigest())
            self.assertEqual(report["inventory_status"], "OBSERVED_DECLARED_ROOTS_ONLY")
        else:
            self.assertIn("CONFINED_HASH_UNSUPPORTED", self.codes(report))
            self.assertIsNone(fact["sha256"])
            self.assertEqual(report["inventory_status"], "INCOMPLETE")

    def test_configuration_presence_never_serializes_values(self):
        report = self.collect()
        serialized = json.dumps(report)
        self.assertNotIn("NEVER_DISCLOSE_VALUE", serialized)
        self.assertTrue(report["configuration"]["SECRET_KEY"]["present"])
        self.assertFalse(report["configuration"]["PUBLIC_BASE_URL"]["present"])
        self.assertEqual(report["configuration_custody"], "NOT_ATTESTED")
        self.assertNotIn(str(self.root), serialized)

    def test_secret_unknown_and_private_names_are_not_read_or_disclosed(self):
        for name in (".env", "private-token.json", "id_ed25519", "extra.json", "customer@example.json"):
            self.write(name, b"DO_NOT_READ_OR_HASH")
        with patch.object(scope, "_open_for_hash", side_effect=AssertionError("forbidden content read")):
            report = self.collect()
        serialized = json.dumps(report)
        for value in (".env", "private-token", "id_ed25519", "extra.json", "customer@example", "DO_NOT_READ_OR_HASH"):
            self.assertNotIn(value, serialized)
        self.assertIn("SECRET_CUSTODY_NOT_ATTESTED", self.codes(report))
        self.assertIn("STATE_POLICY_REQUIRED", self.codes(report))
        self.assertIn("PRIVATE_OR_UNCLASSIFIED_NAME", self.codes(report))
        self.assertEqual(report["bytes_hashed"], 0)

    def test_unknown_empty_directory_is_incomplete_and_not_descended(self):
        unknown = self.ce / "unclassified"
        unknown.mkdir()
        self.write("unclassified/nested/automation_control.json")
        with patch.object(scope, "_open_for_hash", side_effect=AssertionError("unknown subtree read")):
            report = self.collect()
        self.assertIn("STATE_POLICY_REQUIRED", self.codes(report))
        self.assertEqual(report["files"], [])
        self.assertEqual(report["entries_inspected"], 1)

    def test_transient_lock_does_not_become_recovered_authority(self):
        self.write("scheduler.lock")
        self.write("automation_control.json.tmp")
        with patch.object(scope, "_open_for_hash", side_effect=AssertionError("transient read")):
            report = self.collect()
        self.assertEqual({f["classification"] for f in report["files"]}, {"TRANSIENT_NOT_RESTORED"})
        self.assertEqual(report["bytes_hashed"], 0)
        self.assertFalse(report["recovery_certified"])

    def test_dynamic_transient_name_is_not_disclosed(self):
        self.write("runs/customer-123/state.tmp")
        report = self.collect()
        self.assertNotIn("customer-123", json.dumps(report))
        self.assertNotIn("relative_path", report["files"][0])
        self.assertEqual(report["bytes_hashed"], 0)

    def test_database_and_journal_collision_with_state_policy_is_excluded(self):
        database = self.write("product_memory.json", b"synthetic live database")
        self.write("product_memory.json-wal", b"synthetic live journal")
        with patch.object(scope, "_open_for_hash", side_effect=AssertionError("live database read")):
            report = scope.collect_manifest(database=database, roots={"ce": self.ce}, environment={})
        self.assertIn("LIVE_DATABASE_SCOPE_OVERLAP", self.codes(report))
        self.assertEqual(report["bytes_hashed"], 0)
        self.assertEqual(report["files"], [])

    def test_hardlinked_state_file_is_rejected_before_content_open(self):
        other = self.write("other-owned-file", b"synthetic")
        os.link(other, self.ce / "product_memory.json")
        with patch.object(scope, "_open_for_hash", side_effect=AssertionError("hardlink read")):
            report = self.collect()
        self.assertIn("UNSAFE_STATE_FILE", self.codes(report))
        self.assertEqual(report["bytes_hashed"], 0)

    def test_entry_budget_does_not_collect_unbounded_directory(self):
        for index in range(8):
            self.write(f"unknown-{index}.json")
        report = self.collect(limits=scope.Limits(files=4))
        self.assertIn("INVENTORY_ENTRY_BUDGET", self.codes(report))
        self.assertEqual(report["entries_inspected"], 5)
        self.assertEqual(report["files"], [])

    def test_hash_byte_budget_prevents_content_read(self):
        self.write("product_memory.json", b"x" * 128)
        with patch.object(scope, "_open_for_hash", side_effect=AssertionError("oversize read")):
            report = self.collect(limits=scope.Limits(hash_bytes=16))
        self.assertIn("INVENTORY_HASH_BUDGET", self.codes(report))
        self.assertEqual(report["bytes_hashed"], 0)

    def test_metadata_only_never_opens_state_content_or_claims_integrity(self):
        state = self.write("native_workforce/state.json", b"DO_NOT_READ_STATE")
        self.write("runs/private-person-123.json", b"DO_NOT_READ_HISTORY")
        self.write("private-token.json", b"DO_NOT_READ_SECRET")
        with patch.object(scope, "_open_for_hash", side_effect=AssertionError("content read")):
            report = self.collect(metadata_only=True)
        self.assertEqual(report["content_mode"], "METADATA_ONLY")
        self.assertEqual(report["bytes_hashed"], 0)
        facts = [f for f in report["files"] if f["classification"] in ("PRIMARY_STATE", "EVIDENCE")]
        self.assertEqual(len(facts), 2)
        self.assertTrue(all(f["hash_state"] == "NOT_REQUESTED_METADATA_ONLY" and f["sha256"] is None for f in facts))
        primary = next(f for f in facts if f["classification"] == "PRIMARY_STATE")
        self.assertEqual(primary["bytes"], state.stat().st_size)
        self.assertFalse(report["recovery_certified"])
        self.assertFalse(report["database"]["sqlite_snapshot_or_integrity_verified"])
        self.assertEqual(report["configuration_custody"], "NOT_ATTESTED")
        self.assertIn("SECRET_CUSTODY_NOT_ATTESTED", self.codes(report))
        for value in ("DO_NOT_READ", "private-person-123", "private-token"):
            self.assertNotIn(value, json.dumps(report))

    def test_metadata_only_large_file_uses_no_hash_budget(self):
        state = self.write("product_memory.json", b"")
        with state.open("wb") as stream:
            stream.truncate(scope.MAX_HASH_BYTES + 1)
        with patch.object(scope, "_open_for_hash", side_effect=AssertionError("large file read")):
            report = self.collect(metadata_only=True, limits=scope.Limits(hash_bytes=1))
        self.assertEqual(report["inventory_status"], "OBSERVED_DECLARED_ROOTS_ONLY")
        self.assertNotIn("INVENTORY_HASH_BUDGET", self.codes(report))
        self.assertEqual(report["files"][0]["bytes"], scope.MAX_HASH_BYTES + 1)
        self.assertIsNone(report["files"][0]["sha256"])
        self.assertEqual(report["bytes_hashed"], 0)

    def test_primary_directory_precedes_history_at_same_entry_limit(self):
        self.write("native_workforce/state.json")
        for index in range(8):
            self.write(f"runs/owned-{index}.json")
        report = self.collect(metadata_only=True, limits=scope.Limits(files=6))
        self.assertEqual(report["inventory_status"], "INCOMPLETE")
        self.assertIn("INVENTORY_ENTRY_BUDGET", self.codes(report))
        self.assertEqual(report["entries_inspected"], 7)
        fact = next(f for f in report["files"] if f.get("relative_path") == "native_workforce/state.json")
        self.assertEqual(fact["hash_state"], "NOT_REQUESTED_METADATA_ONLY")
        self.assertEqual(report["bytes_hashed"], 0)

    def test_legacy_primary_directory_precedes_history_at_same_entry_limit(self):
        self.write("continuous_evolution_os/native_workforce/state.json", root=self.runtime)
        for index in range(8):
            self.write(f"continuous_evolution_os/runs/owned-{index}.json", root=self.runtime)
        report = scope.collect_manifest(database=self.db, roots={"legacy_runtime": self.runtime},
                                        environment={}, metadata_only=True, limits=scope.Limits(files=7))
        self.assertIn("INVENTORY_ENTRY_BUDGET", self.codes(report))
        self.assertEqual(report["entries_inspected"], 8)
        self.assertEqual(report["files"][0]["relative_path"], "continuous_evolution_os/native_workforce/state.json")
        self.assertEqual(report["bytes_hashed"], 0)

    def test_default_hash_mode_prioritizes_nested_primary_without_larger_budget(self):
        state = self.write("native_workforce/state.json", b"primary")
        self.write("runs/owned.json", b"history")
        report = self.collect(limits=scope.Limits(hash_bytes=7))
        primary = next(f for f in report["files"] if f.get("relative_path") == "native_workforce/state.json")
        self.assertEqual(primary["sha256"], hashlib.sha256(state.read_bytes()).hexdigest())
        self.assertEqual(report["content_mode"], "HASH_KNOWN_STATE")
        self.assertEqual(report["bytes_hashed"], 7)
        self.assertIn("INVENTORY_HASH_BUDGET", self.codes(report))
        self.assertEqual(report["inventory_status"], "INCOMPLETE")

    def test_metadata_only_still_excludes_database_journals_unknown_and_links(self):
        database = self.write("product_memory.json", b"synthetic database")
        self.write("product_memory.json-wal", b"synthetic journal")
        other = self.write("unknown.json", b"unclassified")
        os.link(other, self.ce / "automation_control.json")
        (self.ce / "scheduler_state.json").symlink_to(other)
        with patch.object(scope, "_open_for_hash", side_effect=AssertionError("content read")):
            report = scope.collect_manifest(database=database, roots={"ce": self.ce},
                                            environment={}, metadata_only=True)
        self.assertEqual(report["inventory_status"], "INCOMPLETE")
        self.assertIn("LIVE_DATABASE_SCOPE_OVERLAP", self.codes(report))
        self.assertIn("UNSAFE_STATE_FILE", self.codes(report))
        self.assertIn("LINK_STATE_NOT_VERIFIED", self.codes(report))
        self.assertEqual(report["bytes_hashed"], 0)
        self.assertTrue(all(f["sha256"] is None for f in report["files"]))

    def test_metadata_only_cli_can_observe_one_scope_without_claiming_the_other(self):
        self.write("sentinel_issues_memory.json", root=self.runtime)
        for selected in ("ce", "legacy_runtime", "both"):
            with self.subTest(scope=selected):
                output = io.StringIO()
                with contextlib.redirect_stdout(output), patch.object(scope, "_open_for_hash", side_effect=AssertionError("content read")):
                    code = scope.main(["--db", str(self.db), "--ce-root", str(self.ce),
                                       "--runtime-root", str(self.runtime), "--scope", selected, "--metadata-only"])
                report = json.loads(output.getvalue())
                self.assertEqual(code, 0)
                self.assertEqual({r["scope"] for r in report["roots"]}, {"ce", "legacy_runtime"} if selected == "both" else {selected})
                self.assertEqual(report["content_mode"], "METADATA_ONLY")
                self.assertEqual(report["bytes_hashed"], 0)
                self.assertFalse(report["recovery_certified"])

    def test_known_history_depth_is_bounded(self):
        self.write("runs/older/nested/item.json")
        report = self.collect(limits=scope.Limits(depth=1))
        self.assertIn("INVENTORY_DEPTH_BUDGET", self.codes(report))
        self.assertEqual(report["bytes_hashed"], 0)

    def test_elapsed_time_uses_actual_clock_and_fails_closed(self):
        report = self.collect(limits=scope.Limits(seconds=1e-12))
        self.assertIn("INVENTORY_TIME_BUDGET", self.codes(report))
        self.assertEqual(report["inventory_status"], "INCOMPLETE")
        self.assertEqual(report["bytes_hashed"], 0)

    def test_missing_scope_and_database_cannot_certify(self):
        report = scope.collect_manifest(database=self.root / "absent.sqlite", roots={"ce": self.root / "absent-root"}, environment={})
        self.assertEqual(report["database"]["state"], "NOT_VERIFIED")
        self.assertEqual(report["inventory_status"], "INCOMPLETE")
        self.assertFalse(report["recovery_certified"])

    def test_invalid_inputs_have_closed_diagnostics(self):
        for kwargs in ({"files": True}, {"depth": 0}, {"hash_bytes": -1}, {"seconds": float("nan")}, {"seconds": 6}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "INVALID_INVENTORY_LIMIT"):
                scope.Limits(**kwargs)
        with self.assertRaisesRegex(ValueError, "INVALID_SCOPE_ROOTS"):
            scope.collect_manifest(database=self.db, roots={"private-role": self.ce}, environment={})
        with self.assertRaisesRegex(ValueError, "INVALID_SCOPE_PATHS"):
            scope.collect_manifest(database="not a Path", roots={"ce": self.ce}, environment={})
        nul = Path(str(self.root) + "/PRIVATE_VALUE\0")
        report = scope.collect_manifest(database=nul, roots={"ce": self.ce}, environment={})
        self.assertNotIn("PRIVATE_VALUE", json.dumps(report))
        self.assertIn("DATABASE_UNAVAILABLE", self.codes(report))

    def test_cli_stdout_is_metadata_only_and_creates_no_files(self):
        before = set(self.root.rglob("*"))
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.dict(os.environ, {"SECRET_KEY": "PRIVATE_CLI_VALUE"}, clear=True):
            code = scope.main(["--db", str(self.db), "--ce-root", str(self.ce), "--runtime-root", str(self.runtime)])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(output.getvalue())["recovery_certified"])
        self.assertNotIn("PRIVATE_CLI_VALUE", output.getvalue())
        self.assertEqual(before, set(self.root.rglob("*")))

    @unittest.skipUnless(POSIX_HASH, "Anchored POSIX content reads require Linux/Unix; Windows must fail closed.")
    def test_dynamic_history_identity_is_opaque_and_hash_is_real(self):
        path = self.write("runs/owned-person-123.json", b"synthetic history")
        report = self.collect()
        fact = report["files"][0]
        self.assertEqual(fact["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertNotIn("relative_path", fact)
        self.assertNotIn(path.name, json.dumps(report))

    @unittest.skipUnless(POSIX_HASH, "Native symlink containment is certified only where dir_fd/O_NOFOLLOW exist.")
    def test_linked_ancestor_is_not_read(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.write("product_memory.json", b"private synthetic", root=outside)
        (self.ce / "runs").symlink_to(outside, target_is_directory=True)
        report = self.collect()
        self.assertIn("LINK_STATE_NOT_VERIFIED", self.codes(report))
        self.assertEqual(report["bytes_hashed"], 0)

    @unittest.skipUnless(POSIX_HASH, "Native POSIX race regression is exercised in Linux CI.")
    def test_directory_swap_before_sensitive_open_cannot_follow_link(self):
        runs = self.ce / "runs"
        runs.mkdir()
        self.write("runs/owned.json", b"owned")
        outside = self.root / "outside"
        outside.mkdir()
        self.write("owned.json", b"private synthetic", root=outside)
        native = scope._open_for_hash

        def swap(path):
            runs.rename(self.ce / "runs-original")
            runs.symlink_to(outside, target_is_directory=True)
            return native(path)

        with patch.object(scope, "_open_for_hash", side_effect=swap):
            report = self.collect()
        self.assertIn("SCOPE_UNAVAILABLE", self.codes(report))
        self.assertEqual(report["bytes_hashed"], 0)
        self.assertIsNone(report["files"][0]["sha256"])

    def test_directory_swap_before_enumeration_cannot_claim_observation(self):
        outside = self.root / "outside-empty"
        outside.mkdir()
        native = scope._open_directory

        def swap(path):
            self.ce.rename(self.root / "ce-original")
            self.ce.symlink_to(outside, target_is_directory=True)
            return native(path)

        with patch.object(scope, "_open_directory", side_effect=swap):
            report = self.collect()
        self.assertEqual(report["inventory_status"], "INCOMPLETE")
        self.assertEqual(report["entries_inspected"], 0)

    @unittest.skipUnless(POSIX_HASH, "Native POSIX file identity regression is exercised in Linux CI.")
    def test_file_mutation_before_fstat_does_not_publish_hash(self):
        path = self.write("product_memory.json", b"owned")
        native = scope._open_for_hash

        def mutate(value):
            descriptor = native(value)
            path.write_bytes(b"changed synthetic state")
            return descriptor

        with patch.object(scope, "_open_for_hash", side_effect=mutate):
            report = self.collect()
        self.assertIn("STATE_FILE_CHANGED", self.codes(report))
        self.assertIsNone(report["files"][0]["sha256"])


class RecoveryScopePortableBoundaryTests(unittest.TestCase):
    def test_content_mode_rejects_non_boolean_before_path_or_environment_access(self):
        for value in (None, 0, 1, "true", [], {}):
            with self.subTest(value=value), patch.object(scope, "_checked_path", side_effect=AssertionError("path read")):
                with self.assertRaisesRegex(ValueError, "INVALID_CONTENT_MODE"):
                    scope.collect_manifest(database=Path("unused.sqlite"), roots={"ce": Path("unused")},
                                           environment={}, metadata_only=value)

    def test_primary_directory_priority_is_consistent_for_ce_and_legacy(self):
        for relative, priority in (("native_workforce", 0), ("autonomous_product_qa", 0),
                                    ("runs", 1), ("runs/owned", 1), ("autonomous_product_qa/history", 1)):
            with self.subTest(relative=relative):
                self.assertEqual(scope._directory_priority("ce", relative), priority)
                self.assertEqual(scope._directory_priority("legacy_runtime", "continuous_evolution_os/" + relative), priority)
        self.assertEqual(scope._directory_priority("legacy_runtime", "continuous_evolution_os"), 0)
        self.assertEqual(scope._directory_priority("legacy_runtime", "v938_company_operations"), 0)

    def test_legacy_and_explicit_ce_classification_have_the_same_contract(self):
        for relative, category in (("scheduler.lock", "TRANSIENT_NOT_RESTORED"),
                                   ("automation_control.json", "PRIMARY_STATE"),
                                   ("native_workforce/state.json", "PRIMARY_STATE"),
                                   ("runs/owned.json", "EVIDENCE"),
                                   ("runs/owned.tmp", "TRANSIENT_NOT_RESTORED"),
                                   ("unknown.json", "STATE_POLICY_REQUIRED")):
            with self.subTest(relative=relative):
                self.assertEqual(scope._classification("ce", relative), category)
                self.assertEqual(scope._classification("legacy_runtime", "continuous_evolution_os/" + relative), category)

    def test_unsupported_platform_does_not_enumerate_or_read_content(self):
        if POSIX_HASH:
            self.skipTest("The native POSIX suite verifies this platform; this case is for Windows.")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            database = root / "owned.sqlite"
            database.write_bytes(b"synthetic")
            (root / "product_memory.json").write_bytes(b"DO_NOT_READ")
            with patch.object(scope.os, "scandir", side_effect=AssertionError("unconfined enumeration")), patch.object(scope, "_open_for_hash", side_effect=AssertionError("unconfined read")):
                report = scope.collect_manifest(database=database, roots={"ce": root}, environment={"SECRET_KEY": "DO_NOT_DISCLOSE"})
            self.assertEqual(report["inventory_status"], "INCOMPLETE")
            self.assertIn("CONFINED_ENUMERATION_UNSUPPORTED", {i["code"] for i in report["issues"]})
            self.assertEqual(report["entries_inspected"], 0)
            self.assertEqual(report["bytes_hashed"], 0)
            self.assertNotIn("DO_NOT_DISCLOSE", json.dumps(report))
            self.assertFalse(report["recovery_certified"])

    def test_limit_validation_precedes_inventory(self):
        for kwargs in ({"files": True}, {"depth": 0}, {"hash_bytes": -1}, {"seconds": float("inf")}, {"seconds": 6}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "INVALID_INVENTORY_LIMIT"):
                scope.Limits(**kwargs)


if __name__ == "__main__":
    unittest.main()
