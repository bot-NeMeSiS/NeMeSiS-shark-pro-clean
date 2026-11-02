"""Tiny owned fixtures. No App, SQLite, providers or production state."""
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

from engines import recovery_non_sqlite_state as m

RUNTIME = Path(os.environ.get("OWNED_STATE_TEST_ROOT", tempfile.gettempdir()))
SQLITE = m.SqliteReceipt("OWNED_SQLITE_RECEIPT", hashlib.sha256(b"owned-placeholder").hexdigest(), True)


def identity(kind, size=0):
    return {"st_dev": 1, "st_ino": 1, "st_mode": (stat.S_IFDIR | 0o700) if kind == "directory" else (stat.S_IFREG | 0o600),
            "st_nlink": 2 if kind == "directory" else 1, "st_uid": 0, "st_gid": 0,
            "st_size": size, "st_mtime_ns": 1, "st_ctime_ns": 1}


def manifest(data=b"opaque owned state", relative="unclassified.bin"):
    return {"schema": "OPAQUE_STATE_BUNDLE_V1", "authorization_ref": "OWNED_FIXTURE_ONLY",
            "sqlite": m.asdict(SQLITE), "limits": m.asdict(m.Limits()),
            "roots": [{"scope": "ce", "identity": identity("directory")}],
            "entries": [{"scope": "ce", "relative": relative, "identity": identity("file", len(data)),
                         "kind": "file", "member": "payload/000000", "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest(), "classification": "OPAQUE_PRESERVED"}],
            "bracket_equal": True, "continuous_cross_store_consistency_certified": False}


def tar_member(name, data=b"", *, kind=tarfile.REGTYPE, length=None):
    item = tarfile.TarInfo(name)
    item.type, item.mode, item.size = kind, 0o600, len(data) if length is None else length
    return item.tobuf(format=tarfile.USTAR_FORMAT) + data + b"\0" * (-len(data) % 512)


def archive(data=b"opaque owned state", value=None, *, prefix=None, raw_manifest=None):
    value = manifest(data) if value is None else value
    raw = m._canonical(value) if raw_manifest is None else raw_manifest
    body = (tar_member("payload/000000", data) if prefix is None else prefix)
    whole = body + tar_member("manifest.json", raw) + b"\0" * 1024
    return whole, hashlib.sha256(whole).hexdigest(), hashlib.sha256(raw).hexdigest()


class Owned(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="owned_state_", dir=RUNTIME)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).absolute()

    def parse(self, bundle, sha=None, mh=None, sqlite=SQLITE, **kwargs):
        raw, default_sha, default_mh = bundle
        return m.parse_bundle(io.BytesIO(raw), expected_archive_sha256=sha or default_sha,
                              expected_manifest_sha256=mh or default_mh,
                              expected_sqlite=sqlite, deadline=time.monotonic()+5, **kwargs)


class PortableContractTests(Owned):
    def test_opaque_payload_is_preserved_without_interpretation(self):
        data = b'{"instruction":"NEVER_EXECUTE"}\x00\xff'
        output = self.root / "copied.bin"
        def sink(name, length):
            self.assertEqual(name, "payload/000000")
            self.assertEqual(length, len(data))
            return output.open("xb")
        result = self.parse(archive(data), payload_sink=sink)
        self.assertEqual(output.read_bytes(), data)
        self.assertEqual(result["entries"][0]["classification"], "OPAQUE_PRESERVED")
        self.assertFalse(result["continuous_cross_store_consistency_certified"])

    def test_tampered_payload_cannot_pass(self):
        raw, sha, mh = archive()
        changed = raw[:512] + bytes([raw[512] ^ 1]) + raw[513:]
        with self.assertRaises(m.StateError):
            self.parse((changed, sha, mh))

    def test_foreign_sqlite_receipt_is_rejected(self):
        other = m.SqliteReceipt("FOREIGN", "b"*64, True)
        with self.assertRaisesRegex(m.StateError, "FOREIGN_SQLITE_RECEIPT"):
            self.parse(archive(), sqlite=other)

    def test_traversal_tar_member_is_rejected_before_sink(self):
        body = tar_member("../outside", b"x")
        with self.assertRaisesRegex(m.StateError, "UNSAFE_TAR_NAME"):
            self.parse(archive(prefix=body), payload_sink=lambda *_: self.fail("sink invoked"))

    def test_link_tar_member_is_rejected(self):
        with self.assertRaisesRegex(m.StateError, "UNSAFE_TAR_TYPE"):
            self.parse(archive(prefix=tar_member("payload/000000", kind=tarfile.SYMTYPE)))

    def test_pax_extension_is_rejected_before_decoding(self):
        with self.assertRaisesRegex(m.StateError, "UNSAFE_TAR_TYPE"):
            self.parse(archive(prefix=tar_member("pax", b"x", kind=tarfile.XHDTYPE)))

    def test_oversized_header_rejected_without_payload_allocation(self):
        with self.assertRaisesRegex(m.StateError, "BYTE_BUDGET"):
            self.parse(archive(prefix=tar_member("payload/000000", length=m.MAX_BYTES+1)))

    def test_duplicate_payload_name_is_rejected(self):
        body = tar_member("payload/000000", b"x") * 2
        with self.assertRaisesRegex(m.StateError, "UNSAFE_TAR_NAME"):
            self.parse(archive(prefix=body))

    def test_manifest_traversal_is_rejected(self):
        with self.assertRaisesRegex(m.StateError, "UNSAFE_MEMBER_PATH"):
            self.parse(archive(value=manifest(relative="../outside")))

    def test_secret_named_manifest_entry_is_not_restorable(self):
        with self.assertRaisesRegex(m.StateError, "SECRET_CUSTODY_REQUIRED"):
            self.parse(archive(value=manifest(relative="private-token.json")))

    def test_missing_parent_directory_is_rejected(self):
        with self.assertRaisesRegex(m.StateError, "INCOMPLETE_MANIFEST_NAMESPACE"):
            self.parse(archive(value=manifest(relative="nested/file.bin")))

    def test_manifest_identity_is_required(self):
        value = manifest()
        value["entries"][0]["identity"] = {}
        with self.assertRaisesRegex(m.StateError, "INVALID_MANIFEST_IDENTITY"):
            self.parse(archive(value=value))

    def test_duplicate_manifest_json_key_is_rejected(self):
        raw = m._canonical(manifest())
        raw = b'{"schema":"duplicate",' + raw[1:]
        with self.assertRaises(m.StateError):
            self.parse(archive(raw_manifest=raw))

    def test_concatenated_or_trailing_archives_are_rejected(self):
        raw, sha, mh = archive()
        with self.assertRaisesRegex(m.StateError, "TRAILING_ARCHIVE"):
            self.parse((raw+b"x", sha, mh))

    def test_bad_checksum_is_rejected(self):
        raw, sha, mh = archive()
        bad = bytes([raw[0] ^ 1]) + raw[1:]
        with self.assertRaisesRegex(m.StateError, "INVALID_TAR_HEADER"):
            self.parse((bad, sha, mh))

    def test_limits_cannot_be_expanded_or_boolean(self):
        for kwargs in ({"entries":401}, {"depth":7}, {"bytes":m.MAX_BYTES+1},
                       {"seconds":5.01}, {"entries":True}, {"seconds":float("inf")}):
            with self.subTest(kwargs=kwargs), self.assertRaises(m.StateError):
                m.Limits(**kwargs)

    def test_authority_must_bind_exact_roots_and_unknowns(self):
        scopes = [m.Scope("ce", self.root / "ce")]
        bad = m.Authorization("OWNED_ONLY", (("ce", str(self.root / "other")),), True,
                              (str(self.root / "live.db"),))
        with self.assertRaisesRegex(m.StateError, "SPECIFIC_DATA_AUTHORITY_REQUIRED"):
            m._scopes(scopes, bad)

    def test_secret_named_root_cannot_gain_authority_by_explicit_binding(self):
        root = self.root/"private-secrets"
        scope = m.Scope("ce",root)
        auth = m.Authorization("OWNED_ONLY",(("ce",str(root)),),True,(str(self.root/"live.db"),))
        with self.assertRaisesRegex(m.StateError,"SECRET_CUSTODY_REQUIRED"):
            m._scopes([scope],auth)

    def test_dynamic_exception_text_cannot_escape_closed_receipt_codes(self):
        error = m.StateError("OWNED_CANARY_SHOULD_NOT_BE_LOGGED")
        self.assertEqual(str(error),"UNCLASSIFIED_STATE_ERROR")

    @unittest.skipIf(os.name == "posix", "Windows fail-closed branch")
    def test_windows_capture_stops_before_scan_or_callback(self):
        called = []
        result = m.capture_state(scopes=[], authorization=None, publication=self.root,
                                 deadline=time.monotonic()+1,
                                 sqlite_snapshot_callback=lambda: called.append(True))
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "STRONG_FD_PRIMITIVES_UNSUPPORTED")
        self.assertEqual(called, [])
        self.assertFalse(result["state_published"])

    @unittest.skipIf(os.name == "posix", "Windows fail-closed branch")
    def test_windows_restore_stops_before_workspace_or_database_access(self):
        result = m.restore_state(bundle=self.root/"absent.tar", expected_archive_sha256="a"*64,
                                 expected_manifest_sha256="a"*64, expected_sqlite=SQLITE,
                                 workspace=self.root/"absent", expected_database_identity={},
                                 deadline=time.monotonic()+1)
        self.assertEqual(result["code"], "STRONG_FD_PRIMITIVES_UNSUPPORTED")
        self.assertFalse(result["state_ready_before_app"])


@unittest.skipUnless(os.name == "posix", "Native POSIX confinement remains pending on Windows")
class PosixStateTests(Owned):
    def setUp(self):
        super().setUp()
        self.ce, self.legacy, self.pub = self.root/"ce", self.root/"legacy", self.root/"private"
        for path in (self.ce, self.legacy, self.pub):
            path.mkdir(mode=0o700)
        (self.ce/"nested").mkdir(mode=0o700)
        (self.ce/"nested/unknown.bin").write_bytes(b"owned opaque\x00\xff")
        (self.legacy/"unclassified state.json").write_bytes(b'{"instruction":"DO_NOT_EXECUTE"}')
        self.scopes = [m.Scope("ce", self.ce), m.Scope("legacy_runtime", self.legacy)]
        self.auth = m.Authorization("OWNED_FIXTURE_CAPTURE_AND_RESTORE",
            tuple((s.role,str(s.source)) for s in sorted(self.scopes,key=lambda s:s.role)),
            True, (str(self.root/"live.db"),))
        self.calls = 0

    def callback(self, deadline):
        self.assertGreater(deadline, time.monotonic())
        self.calls += 1
        return SQLITE

    def capture(self, callback=None, **kwargs):
        return m.capture_state(scopes=self.scopes, authorization=self.auth, publication=self.pub,
                               deadline=time.monotonic()+10,
                               sqlite_snapshot_callback=callback or self.callback, **kwargs)

    def workspace(self):
        path = self.root / ".isolated_restore_327_owned"
        path.mkdir(mode=0o700)
        (path/"source").mkdir(mode=0o700)
        # This is an owned non-SQLite marker: no claim to perform a SQLite restore.
        (path/"restoration-test.db").write_bytes(b"owned restored identity marker")
        return path

    def restore(self, result, workspace):
        return m.restore_state(bundle=self.pub/result["bundle_file"],
            expected_archive_sha256=result["archive_sha256"],
            expected_manifest_sha256=result["manifest_sha256"],
            expected_sqlite=SQLITE, workspace=workspace,
            expected_database_identity=m._identity((workspace/"restoration-test.db").stat()),
            deadline=time.monotonic()+10)

    def test_round_trip_two_roots_keeps_unknowns_and_empty_dirs(self):
        (self.ce/"empty").mkdir()
        result = self.capture()
        self.assertTrue(result["ok"], result)
        self.assertEqual(self.calls, 1)
        self.assertEqual((self.pub/result["bundle_file"]).stat().st_mode & 0o777, 0o600)
        work = self.workspace()
        restored = self.restore(result, work)
        self.assertTrue(restored["ok"], restored)
        self.assertFalse(restored["sqlite_restore_created"])
        self.assertEqual((work/"source/data/continuous_evolution_os/nested/unknown.bin").read_bytes(),
                         (self.ce/"nested/unknown.bin").read_bytes())
        self.assertTrue((work/"source/data/continuous_evolution_os/empty").is_dir())
        self.assertEqual((work/"source/data/runtime/unclassified state.json").read_bytes(),
                         (self.legacy/"unclassified state.json").read_bytes())

    def test_change_during_sqlite_callback_keeps_receipt_without_state_publish(self):
        def changed(deadline):
            self.calls += 1
            (self.ce/"nested/unknown.bin").write_bytes(b"changed owned payload")
            return SQLITE
        result = self.capture(changed)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "STATE_CHANGED_ACROSS_SQLITE_INTERVAL")
        self.assertTrue(result["sqlite_receipt"]["published_and_validated"])
        self.assertFalse(result["state_published"])
        self.assertEqual(self.calls, 1)

    def test_namespace_addition_during_callback_is_rejected(self):
        def changed(deadline):
            (self.ce/"new.opaque").write_bytes(b"owned")
            return SQLITE
        self.assertFalse(self.capture(changed)["ok"])

    def test_callback_exception_is_unknown_without_retry(self):
        def failed(deadline):
            self.calls += 1
            raise RuntimeError("do not disclose this owned diagnostic")
        result = self.capture(failed)
        self.assertEqual(self.calls, 1)
        self.assertEqual(result["sqlite_disposition"], "UNKNOWN_PRESERVE_AND_DO_NOT_RETRY")
        self.assertNotIn("do not disclose", json.dumps(result))

    def test_entry_limit_stops_before_sqlite_callback(self):
        result = self.capture(limits=m.Limits(entries=1))
        self.assertEqual(result["code"], "ENTRY_BUDGET")
        self.assertEqual(self.calls, 0)

    def test_byte_limit_stops_before_sqlite_callback(self):
        result = self.capture(limits=m.Limits(bytes=1))
        self.assertEqual(result["code"], "BYTE_BUDGET")
        self.assertEqual(self.calls, 0)

    def test_secret_name_stops_whole_scope_without_exclusion_success(self):
        (self.ce/"private-token.json").write_bytes(b"owned canary secret")
        result = self.capture()
        self.assertEqual(result["code"], "SECRET_CUSTODY_REQUIRED")
        self.assertEqual(self.calls, 0)

    def test_hardlinked_source_is_rejected(self):
        os.link(self.ce/"nested/unknown.bin", self.ce/"another")
        self.assertEqual(self.capture()["code"], "UNSAFE_STATE_FILE")
        self.assertEqual(self.calls, 0)

    def test_fifo_is_rejected_without_opening_or_callback(self):
        os.mkfifo(self.ce/"pipe")
        self.assertEqual(self.capture()["code"], "UNSAFE_STATE_FILE")
        self.assertEqual(self.calls, 0)

    def test_source_symlink_is_rejected(self):
        (self.ce/"alias").symlink_to(self.legacy/"unclassified state.json")
        self.assertEqual(self.capture()["code"], "STATE_LINK")
        self.assertEqual(self.calls, 0)

    def test_known_sqlite_and_sidecar_collision_is_rejected(self):
        protected = self.root/"live.db"
        self.auth = m.Authorization(self.auth.evidence_ref, self.auth.exact_roots, True,
                                  (str(self.ce/"declared.db"),))
        (self.ce/"declared.db-wal").write_bytes(b"owned protected marker")
        self.assertEqual(self.capture()["code"], "SQLITE_SCOPE_COLLISION")
        self.assertEqual(self.calls, 0)

    def test_existing_restore_data_is_never_merged_or_overwritten(self):
        result = self.capture()
        self.assertTrue(result["ok"], result)
        work = self.workspace()
        (work/"source/data").mkdir()
        (work/"source/data/keep").write_bytes(b"must remain")
        restored = self.restore(result, work)
        self.assertFalse(restored["ok"])
        self.assertEqual((work/"source/data/keep").read_bytes(), b"must remain")

    def test_wrong_bundle_hash_stops_before_state_directory_creation(self):
        result = self.capture()
        result["archive_sha256"] = "0"*64
        work = self.workspace()
        restored = self.restore(result, work)
        self.assertFalse(restored["ok"])
        self.assertFalse((work/"source/data").exists())

    def test_foreign_database_identity_stops_before_restoration(self):
        result = self.capture()
        work = self.workspace()
        restored = m.restore_state(bundle=self.pub/result["bundle_file"],
            expected_archive_sha256=result["archive_sha256"],
            expected_manifest_sha256=result["manifest_sha256"], expected_sqlite=SQLITE,
            workspace=work, expected_database_identity={}, deadline=time.monotonic()+5)
        self.assertEqual(restored["code"], "RESTORED_DATABASE_IDENTITY_MISMATCH")
        self.assertFalse((work/"source/data").exists())
