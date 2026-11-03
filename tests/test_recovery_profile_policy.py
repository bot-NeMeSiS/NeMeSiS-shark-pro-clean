"""Pure profile tests; no application import, file state, SQLite, or external access."""
from dataclasses import asdict, replace
import hashlib
import io
import json
import stat
import time
import unittest
from unittest.mock import patch

from engines import recovery_non_sqlite_state as state


PROFILE = "CE_RUNTIME_STATE_V1"


class RecoveryProfilePolicyTests(unittest.TestCase):
    def assert_state_code(self, code, callback):
        with self.assertRaises(state.StateError) as caught:
            callback()
        self.assertEqual(str(caught.exception), code)

    def test_legacy_defaults_and_serialization_remain_exact(self):
        limits = state.Limits()
        self.assertEqual(
            (limits.entries, limits.depth, limits.bytes, limits.seconds),
            (400, 6, 16 * 1024 * 1024, 5.0),
        )
        policy = state._policy(None, limits)
        self.assertIsNone(policy.profile_id)
        self.assertEqual(
            (policy.entries, policy.depth, policy.bytes, policy.seconds, policy.manifest_bytes),
            (400, 6, 16 * 1024 * 1024, 5.0, 1024 * 1024),
        )
        self.assertEqual(
            policy.archive_bytes,
            16 * 1024 * 1024 + 1024 * 1024 + 400 * 1024 + 4096,
        )
        self.assertEqual(state._manifest_limits_record(policy, limits), asdict(limits))
        for schema in ("OPAQUE_STATE_BUNDLE_V1", "OPAQUE_STATE_BUNDLE_V2"):
            self.assertEqual(
                state._validate_manifest_limits(
                    schema, state._manifest_limits_record(policy, limits), policy
                ),
                limits,
            )

    def test_existing_private_manifest_limits_call_shape_stays_compatible(self):
        limits = state.Limits()
        directory_identity = {
            "st_dev": 1,
            "st_ino": 2,
            "st_mode": stat.S_IFDIR | 0o700,
            "st_nlink": 1,
            "st_uid": 1,
            "st_gid": 1,
            "st_size": 0,
            "st_mtime_ns": 0,
            "st_ctime_ns": 0,
        }
        legacy = {
            "schema": "OPAQUE_STATE_BUNDLE_V1",
            "authorization_ref": "LAYOUT_TEST_AUTH",
            "sqlite": {
                "artifact_id": "OWNED_LAYOUT_TEST",
                "sha256": "0" * 64,
                "published_and_validated": True,
            },
            "limits": asdict(limits),
            "roots": [{"scope": "ce", "identity": directory_identity}],
            "entries": [],
            "bracket_equal": True,
            "continuous_cross_store_consistency_certified": False,
        }
        raw = json.dumps(
            legacy, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
        # This is the exact third-argument shape used by the unchanged layout contract test.
        manifest = state._manifest(raw, {}, state.Limits())
        self.assertEqual(manifest["schema"], "OPAQUE_STATE_BUNDLE_V1")
        self.assertIsNone(manifest.get("layout_binding"))
        self.assertIsNone(state._validate_expected_layout_binding(manifest))

    def test_profile_selection_is_closed_and_uses_fixed_caps(self):
        limits = state.Limits()
        policy = state._policy(PROFILE, limits)
        self.assertEqual(policy.profile_id, PROFILE)
        self.assertEqual(
            (policy.entries, policy.depth, policy.bytes, policy.seconds, policy.manifest_bytes),
            (32768, 6, 96 * 1024 * 1024, 5.0, 32 * 1024 * 1024),
        )
        self.assertEqual(
            policy.archive_bytes,
            96 * 1024 * 1024 + 32 * 1024 * 1024 + 32768 * 1024 + 4096,
        )
        self.assertEqual(
            state._validate_manifest_limits(
                "OPAQUE_STATE_BUNDLE_V3", state._manifest_limits_record(policy), policy
            ),
            policy,
        )

    def test_unknown_profile_and_custom_limits_cannot_expand_policy(self):
        self.assert_state_code(
            "INVALID_BUDGET_PROFILE",
            lambda: state._policy("CE_RUNTIME_STATE_V2", state.Limits()),
        )
        self.assert_state_code(
            "INVALID_BUDGET_PROFILE",
            lambda: state._policy(PROFILE, state.Limits(entries=399)),
        )
        self.assert_state_code(
            "INVALID_BUDGET_PROFILE",
            lambda: state._policy(PROFILE, state.Limits(bytes=15 * 1024 * 1024)),
        )
        strict = state._policy(None, state.Limits(entries=399))
        self.assertEqual(strict.entries, 399)
        self.assertIsNone(strict.profile_id)

    def test_v3_manifest_requires_exact_profile_caps_and_types(self):
        limits = state.Limits()
        policy = state._policy(PROFILE, limits)
        record = state._manifest_limits_record(policy)
        self.assertIs(
            state._validate_manifest_limits("OPAQUE_STATE_BUNDLE_V3", record, policy),
            policy,
        )
        default_policy = state._policy(None, limits)
        self.assert_state_code(
            "BUDGET_PROFILE_REQUIRED",
            lambda: state._validate_manifest_limits(
                "OPAQUE_STATE_BUNDLE_V3", record, default_policy
            ),
        )
        altered = dict(record)
        altered["bytes"] -= 1
        self.assert_state_code(
            "BUDGET_PROFILE_MISMATCH",
            lambda: state._validate_manifest_limits(
                "OPAQUE_STATE_BUNDLE_V3", altered, policy
            ),
        )
        altered = dict(record)
        altered["seconds"] = 5
        self.assert_state_code(
            "BUDGET_PROFILE_MISMATCH",
            lambda: state._validate_manifest_limits(
                "OPAQUE_STATE_BUNDLE_V3", altered, policy
            ),
        )
        altered = dict(record)
        altered["unexpected"] = 1
        self.assert_state_code(
            "BUDGET_PROFILE_MISMATCH",
            lambda: state._validate_manifest_limits(
                "OPAQUE_STATE_BUNDLE_V3", altered, policy
            ),
        )

    def test_v1_v2_are_not_read_with_the_expanded_profile(self):
        policy = state._policy(PROFILE, state.Limits())
        legacy_record = asdict(state.Limits())
        for schema in ("OPAQUE_STATE_BUNDLE_V1", "OPAQUE_STATE_BUNDLE_V2"):
            self.assert_state_code(
                "BUDGET_PROFILE_MISMATCH",
                lambda schema=schema: state._validate_manifest_limits(
                    schema, legacy_record, policy
                ),
            )

    def test_manifest_rejects_incoherent_internal_policy(self):
        profile = state._policy(PROFILE, state.Limits())
        altered_profile = replace(profile, archive_bytes=profile.archive_bytes - 1)
        self.assert_state_code(
            "INVALID_BUDGET_PROFILE",
            lambda: state._manifest(b"{}", {}, altered_profile, time.monotonic() + 10.0),
        )
        legacy = state._policy(None, state.Limits())
        altered_legacy = replace(legacy, archive_bytes=legacy.archive_bytes - 1)
        self.assert_state_code(
            "INVALID_LIMIT",
            lambda: state._manifest(b"{}", {}, altered_legacy),
        )

    def test_v3_preflight_rejects_array_depth_and_flat_keys_before_json_load(self):
        policy = state._policy(PROFILE, state.Limits())
        excessive_array = b"[" + b"{}, " * policy.entries + b"{}]"
        excessive_depth = b"[" * 7 + b"0" + b"]" * 7
        excessive_flat_keys = (
            b"{"
            + b",".join(
                (b'"key-' + str(index).encode("ascii") + b'":0')
                for index in range(state._PROFILE_MANIFEST_MAX_OBJECT_KEYS + 1)
            )
            + b"}"
        )
        for raw in (excessive_array, excessive_depth, excessive_flat_keys):
            with self.subTest(length=len(raw)):
                with patch.object(
                    state.json,
                    "loads",
                    side_effect=AssertionError("JSON decoder must not run"),
                ):
                    self.assert_state_code(
                        "MANIFEST_COMPLEXITY_BUDGET",
                        lambda raw=raw: state._manifest(
                            raw, {}, policy, time.monotonic() + 30.0
                        ),
                    )

    def test_profile_writer_matches_legacy_canonical_bytes_without_full_buffer(self):
        policy = state._policy(PROFILE, state.Limits())
        value = {
            "schema": "OPAQUE_STATE_BUNDLE_V3",
            "authorization_ref": "OWNED_WRITER_TEST",
            "entries": [{"scope": "ce", "relative": "owned.json", "bytes": 4}],
            "bracket_equal": True,
        }
        expected = state._canonical(value)
        stream = io.BytesIO()
        writer = state._Writer(stream, time.monotonic() + 30.0)
        with patch.object(
            state, "_canonical", side_effect=AssertionError("full V3 canonical buffer forbidden")
        ):
            digest = writer.manifest(value, policy)
        encoded_archive = stream.getvalue()
        self.assertEqual(encoded_archive[512:512 + len(expected)], expected)
        self.assertEqual(digest, hashlib.sha256(expected).hexdigest())
        self.assertEqual(
            len(encoded_archive),
            512 + len(expected) + (-len(expected) % 512) + 1024,
        )

    def test_v3_manifest_budget_aborts_before_callback_or_stream_write(self):
        policy = state._policy(PROFILE, state.Limits())
        value = {"schema": "OPAQUE_STATE_BUNDLE_V3", "entries": []}
        encoded = state._canonical(value)
        tight_policy = replace(policy, manifest_bytes=len(encoded) - 1)
        stream = io.BytesIO()
        writer = state._Writer(stream, time.monotonic() + 30.0)
        callback_calls = []
        before_callback_calls = []
        with patch.object(
            state, "_canonical", side_effect=AssertionError("full V3 canonical buffer forbidden")
        ):
            self.assert_state_code(
                "MANIFEST_BUDGET",
                lambda: writer.manifest(value, tight_policy),
            )
            self.assert_state_code(
                "MANIFEST_BUDGET",
                lambda: state._snapshot_after_profile_manifest_preflight(
                    value,
                    tight_policy,
                    time.monotonic() + 30.0,
                    lambda deadline: callback_calls.append(deadline),
                    lambda: before_callback_calls.append(True),
                ),
            )
        self.assertEqual(stream.getvalue(), b"")
        self.assertEqual(callback_calls, [])
        self.assertEqual(before_callback_calls, [])


if __name__ == "__main__":
    unittest.main()
