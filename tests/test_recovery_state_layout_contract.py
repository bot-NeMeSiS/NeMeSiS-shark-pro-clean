"""Pure contract checks for the opt-in co-located state layout."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from engines import recovery_non_sqlite_state as state
from tools import recovery_state_adapter as adapter


LAYOUT = state.LAYOUT_CE_COLOCATED_SENTINEL_AUTOPILOT_V1
OPERATION = "LAYOUT_TEST"
PROPOSAL = "a" * 64
SQLITE_SHA = "b" * 64


def _identity(kind: str, size: int = 0, ino: int = 1) -> dict:
    mode = (stat.S_IFDIR | 0o700) if kind == "directory" else (stat.S_IFREG | 0o600)
    return {
        "st_dev": 1, "st_ino": ino, "st_mode": mode, "st_nlink": 1,
        "st_uid": 1, "st_gid": 1, "st_size": size,
        "st_mtime_ns": 1, "st_ctime_ns": 1,
    }


def _layout_manifest():
    roles = ["ce", "legacy_runtime"]
    roots = [{"scope": role, "identity": _identity("directory", ino=i)}
             for i, role in enumerate(roles, start=1)]
    entries, payloads = [], {}
    for index, (role, relative) in enumerate(state._LAYOUT_REQUIRED_ENTRIES[LAYOUT]):
        raw = f"opaque-{index}".encode("ascii")
        digest = hashlib.sha256(raw).hexdigest()
        member = f"payload/{index:06d}"
        entries.append({
            "scope": role, "relative": relative,
            "identity": _identity("file", size=len(raw), ino=index + 10),
            "kind": "file", "member": member, "bytes": len(raw),
            "sha256": digest, "classification": "OPAQUE_PRESERVED",
        })
        payloads[member] = (len(raw), digest)
    sqlite_receipt = {
        "artifact_id": OPERATION, "sha256": SQLITE_SHA,
        "published_and_validated": True,
    }
    manifest = {
        "schema": "OPAQUE_STATE_BUNDLE_V2",
        "authorization_ref": "LAYOUT_TEST_AUTH",
        "sqlite": sqlite_receipt,
        "limits": asdict(state.Limits()),
        "roots": roots,
        "entries": entries,
        "bracket_equal": True,
        "continuous_cross_store_consistency_certified": False,
        "layout_binding": {
            "layout_id": LAYOUT,
            "operation_id": OPERATION,
            "proposal_sha256": PROPOSAL,
            "scope_roles": roles,
            "required_entries": [
                {"scope": role, "relative": relative}
                for role, relative in state._LAYOUT_REQUIRED_ENTRIES[LAYOUT]
            ],
        },
    }
    raw_manifest = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return raw_manifest, payloads, manifest


def _legacy_manifest():
    raw = b"opaque-legacy"
    digest = hashlib.sha256(raw).hexdigest()
    member = "payload/000000"
    manifest = {
        "schema": "OPAQUE_STATE_BUNDLE_V1",
        "authorization_ref": "LAYOUT_TEST_AUTH",
        "sqlite": {"artifact_id": OPERATION, "sha256": SQLITE_SHA,
                   "published_and_validated": True},
        "limits": asdict(state.Limits()),
        "roots": [{"scope": "ce", "identity": _identity("directory")}],
        "entries": [{
            "scope": "ce", "relative": "product_memory.json",
            "identity": _identity("file", size=len(raw)), "kind": "file",
            "member": member, "bytes": len(raw), "sha256": digest,
            "classification": "OPAQUE_PRESERVED",
        }],
        "bracket_equal": True,
        "continuous_cross_store_consistency_certified": False,
    }
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return encoded, {member: (len(raw), digest)}


def _archive_for_layout():
    raw_manifest, payloads, manifest = _layout_manifest()
    values = [(member, f"opaque-{index}".encode("ascii"))
              for index, member in enumerate(sorted(payloads))]
    values.append(("manifest.json", raw_manifest))
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, raw in values:
            header = tarfile.TarInfo(name)
            header.type = tarfile.REGTYPE
            header.mode = 0o600
            header.size = len(raw)
            header.mtime = 0
            header.uid = header.gid = 0
            header.uname = header.gname = ""
            archive.addfile(header, io.BytesIO(raw))
    end = sum(512 + ((len(raw) + 511) // 512) * 512 for _, raw in values) + 1024
    return stream.getvalue()[:end], raw_manifest, manifest


def _plan(scopes, layout_id):
    roles = tuple((scope.role, str(scope.source)) for scope in sorted(scopes, key=lambda item: item.role))
    root = scopes[0].source.parent
    authorization = state.Authorization(
        "LAYOUT_TEST_AUTH", roles, True, (str(root / "database.db"),)
    )
    return adapter.StateRecoveryPlan(
        OPERATION, PROPOSAL, tuple(scopes), authorization, root / "private-state",
        layout_id=layout_id,
    )


class RecoveryStateLayoutContractTests(unittest.TestCase):
    def test_v1_manifest_remains_compatible_without_layout_expectations(self):
        raw, payloads = _legacy_manifest()
        manifest = state._manifest(raw, payloads, state.Limits())
        self.assertEqual(manifest["schema"], "OPAQUE_STATE_BUNDLE_V1")
        self.assertIsNone(manifest.get("layout_binding"))
        self.assertIsNone(state._validate_expected_layout_binding(manifest))

    def test_v2_manifest_accepts_only_the_closed_layout_and_required_files(self):
        raw, payloads, _ = _layout_manifest()
        manifest = state._manifest(raw, payloads, state.Limits())
        binding = state._validate_expected_layout_binding(
            manifest, expected_layout_id=LAYOUT, expected_operation_id=OPERATION,
            expected_proposal_sha256=PROPOSAL,
            expected_scope_roles=("ce", "legacy_runtime"),
        )
        self.assertEqual(binding["layout_id"], LAYOUT)
        self.assertEqual(binding["scope_roles"], ["ce", "legacy_runtime"])

    def test_unknown_layout_and_arbitrary_binding_fields_fail_closed(self):
        raw, payloads, manifest = _layout_manifest()
        manifest["layout_binding"]["layout_id"] = "UNRECOGNIZED_LAYOUT"
        with self.assertRaises(state.StateError):
            state._manifest(json.dumps(manifest).encode("ascii"), payloads, state.Limits())

        raw, payloads, manifest = _layout_manifest()
        manifest["layout_binding"]["extra"] = "not-admitted"
        with self.assertRaises(state.StateError):
            state._manifest(json.dumps(manifest).encode("ascii"), payloads, state.Limits())

    def test_missing_scope_role_or_required_file_fails_closed(self):
        _, payloads, manifest = _layout_manifest()
        manifest["layout_binding"]["scope_roles"] = ["ce"]
        with self.assertRaises(state.StateError):
            state._manifest(json.dumps(manifest).encode("ascii"), payloads, state.Limits())

        _, payloads, manifest = _layout_manifest()
        missing = ("ce", "sentinel_issues_memory.json")
        entry = next(item for item in manifest["entries"]
                     if (item["scope"], item["relative"]) == missing)
        manifest["entries"].remove(entry)
        payloads.pop(entry["member"])
        with self.assertRaises(state.StateError):
            state._manifest(json.dumps(manifest).encode("ascii"), payloads, state.Limits())

    def test_manifest_binds_operation_sqlite_proposal_and_expected_roles(self):
        raw, payloads, manifest = _layout_manifest()
        manifest["layout_binding"]["operation_id"] = "OTHER_OPERATION"
        with self.assertRaises(state.StateError):
            state._manifest(json.dumps(manifest).encode("ascii"), payloads, state.Limits())

        raw, payloads, manifest = _layout_manifest()
        manifest["sqlite"]["published_and_validated"] = False
        with self.assertRaises(state.StateError):
            state._manifest(json.dumps(manifest).encode("ascii"), payloads, state.Limits())

        raw, payloads, _ = _layout_manifest()
        valid = state._manifest(raw, payloads, state.Limits())
        with self.assertRaises(state.StateError):
            state._validate_expected_layout_binding(
                valid, expected_layout_id=LAYOUT, expected_operation_id=OPERATION,
                expected_proposal_sha256="c" * 64,
                expected_scope_roles=("ce", "legacy_runtime"),
            )
        with self.assertRaises(state.StateError):
            state._validate_expected_layout_binding(
                valid, expected_layout_id=LAYOUT, expected_operation_id=OPERATION,
                expected_proposal_sha256=PROPOSAL, expected_scope_roles=("ce",),
            )
        with self.assertRaises(state.StateError):
            state._validate_expected_layout_binding(valid)

    def test_archive_parser_binds_layout_to_expected_bundle_receipts(self):
        archive, raw_manifest, manifest = _archive_for_layout()
        expected_archive_sha256 = hashlib.sha256(archive).hexdigest()
        expected_manifest_sha256 = hashlib.sha256(raw_manifest).hexdigest()
        expected_sqlite = state.SqliteReceipt(OPERATION, SQLITE_SHA, True)
        base = {
            "expected_archive_sha256": expected_archive_sha256,
            "expected_manifest_sha256": expected_manifest_sha256,
            "expected_sqlite": expected_sqlite,
            "deadline": time.monotonic() + 30,
            "limits": state.Limits(),
            "expected_layout_id": LAYOUT,
            "expected_proposal_sha256": PROPOSAL,
            "expected_scope_roles": ("ce", "legacy_runtime"),
        }
        parsed = state.parse_bundle(io.BytesIO(archive), **base)
        self.assertEqual(parsed["layout_binding"], manifest["layout_binding"])
        for change in (
            {"expected_layout_id": "OTHER_LAYOUT"},
            {"expected_proposal_sha256": "c" * 64},
            {"expected_scope_roles": ("ce",)},
        ):
            with self.subTest(change=change), self.assertRaises(state.StateError):
                state.parse_bundle(io.BytesIO(archive), **{**base, **change})
        with self.assertRaises(state.StateError):
            state.parse_bundle(
                io.BytesIO(archive), **{**base, "expected_sqlite": state.SqliteReceipt("OTHER_OPERATION", SQLITE_SHA, True)}
            )

    def test_typed_plan_requires_exact_layout_and_both_roles(self):
        root = Path(tempfile.gettempdir()) / "recovery-layout-contract-plan"
        ce = state.Scope("ce", root / "ce")
        legacy = state.Scope("legacy_runtime", root / "runtime")
        with self.assertRaises(adapter.HandoffError):
            _plan((ce, legacy), "UNKNOWN_LAYOUT")
        with self.assertRaises(adapter.HandoffError):
            _plan((ce,), LAYOUT)
        plan = _plan((legacy, ce), LAYOUT)
        self.assertEqual(plan.layout_id, LAYOUT)

    @unittest.skipUnless(os.name == "posix", "native state writer requires POSIX descriptor primitives")
    def test_missing_required_entry_fails_before_sqlite_snapshot_callback(self):
        scopes = (
            state.Scope("ce", Path("/owned/ce")),
            state.Scope("legacy_runtime", Path("/owned/runtime")),
        )
        authorization = state.Authorization(
            "LAYOUT_TEST_AUTH",
            tuple((scope.role, str(scope.source)) for scope in scopes),
            True,
            ("/owned/database.db",),
        )
        callback = Mock()
        fake_scan = {
            "roots": [], "entries": [], "entries_count": 0, "bytes": 0,
        }
        with tempfile.TemporaryDirectory(prefix="state_layout_contract_") as temporary:
            publication = Path(temporary) / "private"
            publication.mkdir(mode=0o700)
            with patch.object(state, "_native"), patch.object(state, "_scan", return_value=fake_scan):
                result = state.capture_state(
                    scopes=scopes, authorization=authorization, publication=publication,
                    deadline=time.monotonic() + 30,
                    sqlite_snapshot_callback=callback,
                    layout_binding=state.StateLayoutBinding(LAYOUT, OPERATION, PROPOSAL),
                )
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "LAYOUT_REQUIRED_ENTRY_MISSING")
        self.assertFalse(result["sqlite_callback_invoked"])
        callback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
