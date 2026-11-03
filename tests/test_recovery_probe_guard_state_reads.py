from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tools.recovery_app_probe import (
    ProbeError,
    _canonical_state_projection_matches,
    _decode_state_consumer_json,
)
from tools.recovery_probe_guard import ProbeBoundary, ProbeBoundaryViolation


class GuardedStateReadObservationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="state_read_guard_")).absolute()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.root.chmod(0o700)
        self.source = self.root / "source"
        self.data = self.source / "data"
        self.target = self.data / "runtime" / "sentinel_issues_memory.json"
        self.target.parent.mkdir(parents=True, mode=0o700)
        self.target.write_bytes(b'{"issues":[{"id":"owned-fixture"}]}')
        self.scratch = self.root / "scratch"
        self.scratch.mkdir(mode=0o700)
        self.database = self.root / "restoration-test.db"
        self.database.write_bytes(b"")
        self.boundary = ProbeBoundary(
            database=self.database,
            source=self.source,
            scratch=self.scratch,
            libraries=(),
            mode="read_only",
            deadline=time.monotonic() + 30.0,
        )

    def _observe(self, reader):
        # The observer itself must install and restore its profile bracket.
        return self.boundary.observe_state_file("legacy_runtime", self.target, reader)

    def test_path_read_bytes_is_a_complete_native_read(self):
        expected = self.target.read_bytes()
        value, _open_attempts, full_reads = self._observe(self.target.read_bytes)
        self.assertEqual(value, expected)
        self.assertGreater(full_reads, 0)

    def test_path_read_text_utf8_crlf_is_a_complete_native_read(self):
        self.target.write_bytes(b"line one\r\nline two\r\n")
        value, _open_attempts, full_reads = self._observe(
            lambda: self.target.read_text(encoding="utf-8"))
        self.assertEqual(value, "line one\nline two\n")
        self.assertGreater(full_reads, 0)

    def test_path_read_text_multibyte_utf8_crlf_is_a_complete_native_read(self):
        raw = "España ⚽\r\nété 東京\r\n".encode("utf-8")
        self.target.write_bytes(raw)
        value, _open_attempts, full_reads = self._observe(
            lambda: self.target.read_text(encoding="utf-8"))
        self.assertEqual(value, "España ⚽\nété 東京\n")
        self.assertGreater(len(raw), len(value))
        self.assertGreater(full_reads, 0)

    def test_partial_read_observation_preserves_native_offsets_and_buffered_bytes(self):
        def native_reader():
            with self.target.open("rb", buffering=64) as stream:
                first = stream.read(1)
                after_partial = (stream.tell(), os.lseek(stream.fileno(), 0, os.SEEK_CUR))
                buffered = stream.peek()
                remaining = stream.read()
                after_remainder = (stream.tell(), os.lseek(stream.fileno(), 0, os.SEEK_CUR))
            return first, buffered, remaining, after_partial, after_remainder

        baseline = native_reader()
        self.assertEqual(baseline[3][0], 1)
        self.assertGreater(baseline[3][1], 1, "fixture must exercise native buffered read-ahead")
        observed, _open_attempts, full_reads = self._observe(native_reader)
        self.assertEqual(observed, baseline)
        self.assertEqual(observed[0] + observed[2], self.target.read_bytes())
        self.assertEqual(full_reads, 0)

    def test_partial_read_followed_by_fallback_is_not_full_consumption(self):
        captured = []
        def reader():
            with self.target.open("rb") as stream:
                captured.append(stream.read(1) + stream.read())
            return {"recommendations": {}}

        value, _open_attempts, full_reads = self._observe(reader)
        self.assertEqual(captured[0], self.target.read_bytes())
        self.assertEqual(value, {"recommendations": {}})
        self.assertEqual(full_reads, 0)

    def test_caught_read_exception_fallback_is_not_consumption(self):
        def reader():
            stream = self.target.open("rb")
            stream.close()
            try:
                stream.read()
            except ValueError:
                return {"recommendations": {}}
            return {"recommendations": {}}

        value, _open_attempts, full_reads = self._observe(reader)
        self.assertEqual(value, {"recommendations": {}})
        self.assertEqual(full_reads, 0)

    def test_read_from_decoy_does_not_bind_to_canonical_path(self):
        decoy = self.data / "runtime" / "continuous_evolution_os" / "product_memory.json"
        decoy.parent.mkdir(parents=True, mode=0o700)
        decoy.write_bytes(b'{"recommendations":{"decoy":true}}')

        value, _open_attempts, full_reads = self._observe(decoy.read_bytes)
        self.assertEqual(value, decoy.read_bytes())
        self.assertEqual(full_reads, 0)

    def test_colocated_consumer_reading_dormant_runtime_sentinel_is_a_decoy_attempt(self):
        canonical = self.data / "continuous_evolution_os" / "sentinel_issues_memory.json"
        canonical.parent.mkdir(parents=True, mode=0o700)
        canonical.write_bytes(b'{"issues":[]}\n')
        enabled = True
        boundary = self.boundary

        def observe_open(event, arguments):
            if enabled and event == "open" and boundary._state_read_role is not None:
                boundary.audit(event, arguments)

        # This audit listener is permanently registered but inert after finally;
        # it forwards only real open events during these owned getter brackets.
        sys.addaudithook(observe_open)
        try:
            before = boundary._state_decoy_open_attempts
            _value, _attempts, full_reads = self._observe(self.target.read_bytes)
            self.assertGreater(full_reads, 0)
            self.assertEqual(boundary._state_decoy_open_attempts, before)
            value, open_attempts, full_reads = boundary.observe_state_file(
                "legacy_runtime", canonical, self.target.read_bytes)
            self.assertEqual(value, self.target.read_bytes())
            self.assertEqual(open_attempts, 0)
            self.assertEqual(full_reads, 0)
            self.assertEqual(boundary._state_decoy_open_attempts, before + 1)
        finally:
            enabled = False

    def test_empty_canonical_file_is_not_a_full_read_proof(self):
        self.target.write_bytes(b"")
        value, _open_attempts, full_reads = self._observe(self.target.read_bytes)
        self.assertEqual(value, b"")
        self.assertEqual(full_reads, 0)

    def test_missing_canonical_file_is_rejected_before_getter(self):
        missing = self.data / "runtime" / "missing.json"
        with self.assertRaises(ProbeBoundaryViolation):
            self.boundary.observe_state_file("legacy_runtime", missing, lambda: b"")

    def test_canonical_file_mutation_during_getter_is_rejected(self):
        def reader():
            self.target.unlink()
            self.target.write_bytes(b'{"issues":[{"id":"changed"}]}')
            return b""

        with self.assertRaises(ProbeBoundaryViolation):
            self._observe(reader)

    def test_previous_profile_is_restored_when_getter_raises(self):
        original_profile = sys.getprofile()

        def previous_profile(_frame, _event, _argument):
            return None

        def raising_reader():
            raise ValueError("fixture")

        sys.setprofile(previous_profile)
        try:
            with self.assertRaises(ValueError):
                self._observe(raising_reader)
            self.assertIs(sys.getprofile(), previous_profile)
            self.assertIsNone(self.boundary._state_read_role)
            self.assertEqual(self.boundary._state_pending_reads, [])
        finally:
            sys.setprofile(original_profile)

    def test_empty_issue_projection_requires_full_read_and_exact_revision(self):
        import hashlib

        revision = hashlib.sha256(b'{"issues":[]}').hexdigest()
        stored = {"issues": []}
        returned = {"_storage_revision": revision, "issues": []}
        self.assertTrue(_canonical_state_projection_matches(
            "legacy_runtime", returned, stored, revision, full_read=True))
        self.assertFalse(_canonical_state_projection_matches(
            "legacy_runtime", returned, stored, revision, full_read=False))
        self.assertFalse(_canonical_state_projection_matches(
            "legacy_runtime", returned, stored, "0" * 64, full_read=True))

    def test_empty_recommendations_require_explicit_equal_projection_and_full_read(self):
        revision = "a" * 64
        stored = {"recommendations": {}}
        returned = {"recommendations": {}}
        self.assertTrue(_canonical_state_projection_matches(
            "ce", returned, stored, revision, full_read=True))
        self.assertFalse(_canonical_state_projection_matches(
            "ce", returned, stored, revision, full_read=False))
        self.assertFalse(_canonical_state_projection_matches(
            "ce", {}, stored, revision, full_read=True))
        self.assertFalse(_canonical_state_projection_matches(
            "ce", returned, {"recommendations": {"different": 1}}, revision, full_read=True))

    def test_malformed_restored_json_is_rejected(self):
        with self.assertRaises(ProbeError):
            _decode_state_consumer_json(b"{not-json")
        with self.assertRaises(ProbeError):
            _decode_state_consumer_json(b"[]")



class ColocatedStateProjectionTests(unittest.TestCase):
    """Canonical source values cannot be replaced by a fallback or another store."""
    @staticmethod
    def _spec(kind):
        from tools.recovery_app_probe import COLOCATED_CONSUMERS
        return next(spec for spec in COLOCATED_CONSUMERS if spec["kind"] == kind)

    def test_product_empty_state_needs_full_read_and_equal_explicit_projection(self):
        from tools.recovery_app_probe import _colocated_projection_matches as matches
        spec=self._spec("product"); revision="a"*64
        stored={"recommendations": {}}
        self.assertTrue(matches(spec, stored, stored, revision, full_read=True))
        self.assertFalse(matches(spec, stored, stored, revision, full_read=False))
        self.assertFalse(matches(spec, {}, stored, revision, full_read=True))
        self.assertFalse(matches(spec, {"recommendations":{"wrong":1}}, stored, revision, full_read=True))

    def test_sentinel_revision_and_active_issue_identity_reject_dormant_store(self):
        from tools.recovery_app_probe import _colocated_projection_matches as matches
        spec=self._spec("sentinel"); revision="b"*64
        stored={"issues":[{"id":"owned-active"}]}
        actual={"_storage_revision":revision,"issues":[{"id":"owned-active","issue_id":"owned-active"}]}
        self.assertTrue(matches(spec, actual, stored, revision, full_read=True))
        self.assertFalse(matches(spec, actual, stored, "c"*64, full_read=True))
        dormant={"_storage_revision":revision,"issues":[{"id":"owned-dormant"}]}
        self.assertFalse(matches(spec, dormant, stored, revision, full_read=True))
        self.assertTrue(matches(spec, {"_storage_revision":revision,"issues":[]}, {"issues":[]}, revision, full_read=True))
        self.assertFalse(matches(spec, actual, stored, revision, full_read=False))

    def test_autopilot_normalized_ids_preserve_source_and_reject_fallback(self):
        from tools.recovery_app_probe import _colocated_projection_matches as matches
        spec=self._spec("autopilot"); revision="d"*64
        stored={"issues":[{"issue_id":"owned-autopilot"}]}
        actual=[{"id":"owned-autopilot"}]
        self.assertTrue(matches(spec, actual, stored, revision, full_read=True))
        self.assertFalse(matches(spec, [{"id":"wrong-root"}], stored, revision, full_read=True))
        self.assertFalse(matches(spec, actual, stored, revision, full_read=False))
        self.assertTrue(matches(spec, [], {"issues":[]}, revision, full_read=True))
        self.assertFalse(matches(spec, [], {"issues":[]}, revision, full_read=False))


if __name__ == "__main__":
    unittest.main()
