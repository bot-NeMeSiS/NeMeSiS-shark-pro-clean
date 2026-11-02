"""Small handoff unit contracts; never runs App or opens a SQLite database.

Doubles here model ONLY the new adapter boundaries. Native POSIX state tests
use an ordinary marker file, not SQLite, and make no SQLite/App claim.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from engines import data_vault_engine as vault
from engines import recovery_non_sqlite_state as state
from tools import recovery_app_probe as probe
from tools import backup_operator_recovery_327 as operator
from tools import recovery_state_adapter as handoff

H = "a" * 64
M = "b" * 64
P = "c" * 64
NAME = "database_OWNED_1.db"
RUN_ROOT = Path(os.environ.get("OWNED_HANDOFF_TEST_ROOT", tempfile.gettempdir()))


def plan_for(base):
    scopes = (state.Scope("ce", base / "ce"), state.Scope("legacy_runtime", base / "legacy"))
    authorization = state.Authorization("OWNED_FIXTURE_ONLY",
        tuple((s.role, str(s.source)) for s in scopes), True, (str(base / "live.db"),))
    return handoff.StateRecoveryPlan("OWNED_OPERATION", P, scopes, authorization,
                                     base / "backups" / "state-private")


def native_result(receipt, *, ok=True):
    return {"ok": ok, "code": "BRACKETED_STATE_PRESERVED_NOT_FULL_RECOVERY" if ok else "STATE_CHANGED_ACROSS_SQLITE_INTERVAL",
            "state_published": ok, "bundle_file": "state-" + "1" * 32 + ".tar",
            "archive_sha256": H, "manifest_sha256": M, "sqlite_callback_invoked": True,
            "sqlite_receipt": state._sqlite(receipt)}


def bundle_for(base):
    return handoff.BoundStateBundle("OWNED_OPERATION", P, base / "state.tar", H, M,
                                    state.SqliteReceipt("OWNED_OPERATION", H, True), NAME,
                                    ("ce", "legacy_runtime"), state.Limits())


class DeadlineContracts(unittest.TestCase):
    def test_default_still_fifteen_seconds(self):
        self.assertEqual(inspect.signature(vault.create_sqlite_backup).parameters["snapshot_timeout"].default, 15.0)
        self.assertIsNone(inspect.signature(vault.create_sqlite_backup).parameters["absolute_deadline"].default)
        self.assertEqual(vault._bounded_backup_deadline(15, now=100), 115)

    def test_later_absolute_never_enlarges_local_timeout(self):
        self.assertEqual(vault._bounded_backup_deadline(15, 900, now=100), 115)

    def test_earlier_absolute_does_not_restart_after_setup(self):
        self.assertEqual(vault._bounded_backup_deadline(300, 400, now=250), 400)
        self.assertEqual(vault._bounded_backup_deadline(300, 400, now=399), 400)

    def test_expired_absolute_stays_expired_not_floor_extended(self):
        self.assertEqual(vault._bounded_backup_deadline(.001, 99, now=100), 99)
        result = vault.create_sqlite_backup(Path("/unopened-owned-marker"), Path("/unopened-owned-root"),
                                             "OWNED", absolute_deadline=1)
        self.assertFalse(result["ok"])
        self.assertFalse(result["backup_created"])
        self.assertEqual(result["error"], "backup_snapshot_timeout")

    def test_nonfinite_boolean_or_nonpositive_absolute_denied(self):
        for value in (True, False, float("nan"), float("inf"), -1, 0, "400"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    vault._bounded_backup_deadline(15, value, now=100)

    def test_existing_local_floor_is_preserved(self):
        self.assertAlmostEqual(vault._bounded_backup_deadline(.001, now=100), 100.01)


class HandoffContracts(unittest.TestCase):
    def setUp(self):
        self.base = RUN_ROOT.absolute() / "unopened"
        self.plan = plan_for(self.base)
        self.deadline = time.monotonic() + 30
        self.capture = Mock(return_value={"ok": True, "backup_created": True, "backup_file": NAME, "sha256": H})

    def test_one_capture_uses_identical_absolute_and_typed_receipt(self):
        observed = []
        def native(**kw):
            observed.append(kw)
            receipt = kw["sqlite_snapshot_callback"](kw["deadline"])
            self.assertEqual(type(receipt), state.SqliteReceipt)
            return native_result(receipt)
        with patch.object(state, "capture_state", native):
            result = handoff.capture_with_state(plan=self.plan, source=self.base / "live.db",
                                                create_snapshot=self.capture, deadline=self.deadline)
        self.assertTrue(result.ok)
        self.capture.assert_called_once_with(absolute_deadline=self.deadline)
        self.assertEqual(observed[0]["deadline"], self.deadline)
        self.assertEqual(result.bundle.sqlite.sha256, H)
        self.assertEqual(result.bundle.proposal_sha256, P)
        self.assertEqual(result.bundle.scope_roles, ("ce", "legacy_runtime"))

    def test_post_sqlite_state_failure_keeps_copy_evidence_without_retry(self):
        def native(**kw):
            receipt = kw["sqlite_snapshot_callback"](kw["deadline"])
            return native_result(receipt, ok=False)
        with patch.object(state, "capture_state", native):
            result = handoff.capture_with_state(plan=self.plan, source=self.base / "live.db",
                                                create_snapshot=self.capture, deadline=self.deadline)
        self.assertFalse(result.ok)
        self.assertIsNone(result.bundle)
        self.assertTrue(result.sqlite_result["backup_created"])
        self.capture.assert_called_once()
        self.assertEqual(handoff.public_sqlite_disposition(result)["backup_name"], NAME)

    def test_second_callback_never_calls_engine_twice(self):
        def native(**kw):
            receipt = kw["sqlite_snapshot_callback"](kw["deadline"])
            with self.assertRaisesRegex(handoff.HandoffError, "SECOND_SQLITE_CAPTURE_DENIED"):
                kw["sqlite_snapshot_callback"](kw["deadline"])
            return native_result(receipt, ok=False)
        with patch.object(state, "capture_state", native):
            result = handoff.capture_with_state(plan=self.plan, source=self.base / "live.db",
                                                create_snapshot=self.capture, deadline=self.deadline)
        self.assertFalse(result.ok)
        self.capture.assert_called_once()

    def test_foreign_deadline_rejected_before_engine(self):
        def native(**kw):
            with self.assertRaisesRegex(handoff.HandoffError, "FOREIGN_SQLITE_CAPTURE_DEADLINE"):
                kw["sqlite_snapshot_callback"](kw["deadline"] + 300)
            return {"ok": False, "sqlite_callback_invoked": False}
        with patch.object(state, "capture_state", native):
            result = handoff.capture_with_state(plan=self.plan, source=self.base / "live.db",
                                                create_snapshot=self.capture, deadline=self.deadline)
        self.assertFalse(result.ok)
        self.capture.assert_not_called()

    def test_engine_failure_after_publication_is_preserved(self):
        self.capture.return_value = {"ok": False, "backup_created": True, "backup_file": NAME}
        def native(**kw):
            with self.assertRaisesRegex(handoff.HandoffError, "SQLITE_CAPTURE_NOT_SEALED_AND_VALIDATED"):
                kw["sqlite_snapshot_callback"](kw["deadline"])
            return {"ok": False, "sqlite_callback_invoked": True}
        with patch.object(state, "capture_state", native):
            result = handoff.capture_with_state(plan=self.plan, source=self.base / "live.db",
                                                create_snapshot=self.capture, deadline=self.deadline)
        self.assertFalse(result.ok)
        self.assertIsNone(result.bundle)
        self.assertTrue(handoff.public_sqlite_disposition(result)["backup_created"])
        self.assertEqual(handoff.public_sqlite_disposition(result)["backup_name"], NAME)

    def test_callback_exception_disposition_unknown_not_false(self):
        self.capture.side_effect = RuntimeError("owned failure, not an SQL call")
        def native(**kw):
            kw["sqlite_snapshot_callback"](kw["deadline"])
        with patch.object(state, "capture_state", native):
            result = handoff.capture_with_state(plan=self.plan, source=self.base / "live.db",
                                                create_snapshot=self.capture, deadline=self.deadline)
        self.assertFalse(result.ok)
        self.assertIsNone(handoff.public_sqlite_disposition(result)["backup_created"])
        self.capture.assert_called_once()

    def test_unprotected_actual_sqlite_refused_before_native_capture(self):
        with patch.object(state, "capture_state") as native:
            with self.assertRaisesRegex(handoff.HandoffError, "ACTUAL_SQLITE_SOURCE_NOT_PROTECTED"):
                handoff.capture_with_state(plan=self.plan, source=self.base / "other.db",
                                           create_snapshot=self.capture, deadline=self.deadline)
        native.assert_not_called()
        self.capture.assert_not_called()

    def test_a_dict_is_not_a_data_authority_or_typed_bundle(self):
        with self.assertRaisesRegex(handoff.HandoffError, "TYPED_STATE_PLAN_REQUIRED"):
            handoff.capture_with_state(plan={"authorized": True}, source=self.base / "live.db",
                                       create_snapshot=self.capture, deadline=self.deadline)
        with self.assertRaisesRegex(handoff.HandoffError, "TYPED_STATE_BUNDLE_REQUIRED"):
            handoff.bind_verified_sqlite({}, backup_name=NAME, sqlite_sha256=H, deadline=self.deadline)

    def test_foreign_sqlite_name_or_digest_refused_before_restore(self):
        bundle = bundle_for(self.base)
        for name, digest in (("database_OTHER.db", H), (NAME, M)):
            with self.subTest(name=name, digest=digest):
                with self.assertRaisesRegex(handoff.HandoffError, "FOREIGN_VERIFIED_SQLITE_ARCHIVE"):
                    handoff.bind_verified_sqlite(bundle, backup_name=name, sqlite_sha256=digest, deadline=self.deadline)
        handoff.bind_verified_sqlite(bundle, backup_name=NAME, sqlite_sha256=H, deadline=self.deadline)

    def test_plan_keeps_limits_and_denies_namespace_overlap(self):
        with self.assertRaises(handoff.HandoffError):
            replace(self.plan, publication=self.plan.scopes[0].source / "out")
        with self.assertRaises(state.StateError):
            replace(self.plan, authorization=replace(self.plan.authorization, unknown_regular_files_authorized=False))
        for kwargs in ({"entries":401}, {"bytes":16*1024*1024+1}, {"depth":7}, {"seconds":5.01}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(state.StateError):
                    state.Limits(**kwargs)

    def test_state_capacity_gate_only_increases_required_not_limits(self):
        check = handoff.operator_preflight(plan=self.plan, source=self.base / "live.db",
                   directory=self.base / "backups", app_probe_mode="normal_boot", verify_existing=None,
                   storage={"ok":True, "snapshot_bytes":5, "required_bytes":100, "free_bytes":101})
        self.assertFalse(check["ok"])
        self.assertEqual(check["required_bytes"], 100 + 128*1024*1024 + 5 + state.MAX_ARCHIVE + self.plan.limits.bytes)
        self.assertEqual(self.plan.limits, state.Limits())
        for mode, existing, directory in ((None,None,self.base/"backups"),
                                         ("normal_boot",NAME,self.base/"backups"),
                                         ("normal_boot",None,self.base/"other")):
            with self.subTest(mode=mode, existing=existing, directory=directory):
                with self.assertRaises(handoff.HandoffError):
                    handoff.operator_preflight(plan=self.plan, source=self.base/"live.db",
                      directory=directory, app_probe_mode=mode, verify_existing=existing, storage={})


    def test_whole_mode_capacity_boundary_and_pure_validation(self):
        kwargs = dict(plan=self.plan, source=self.base/"live.db", directory=self.base/"backups",
                      app_probe_mode="normal_boot", verify_existing=None)
        self.assertIsNone(handoff.validate_operator_plan(**kwargs))
        expected=11
        needed=100 + 128*1024*1024 + expected + state.MAX_ARCHIVE + self.plan.limits.bytes
        for free, admitted in ((needed-1,False),(needed,True)):
            with self.subTest(free=free):
                result=handoff.operator_preflight(**kwargs,storage={
                    "ok":True,"snapshot_bytes":expected,"required_bytes":100,"free_bytes":free})
                self.assertEqual(result["ok"],admitted)
                self.assertEqual(result["required_bytes"],needed)
        ro=handoff.operator_preflight(**{**kwargs,"app_probe_mode":"read_only"},storage={
                "ok":True,"snapshot_bytes":expected,"required_bytes":100,"free_bytes":needed})
        self.assertEqual(ro["required_bytes"],needed-expected)
        self.assertFalse(handoff.operator_preflight(**kwargs,storage={
                "ok":True,"required_bytes":100,"free_bytes":needed})["ok"])

    def test_public_receipt_does_not_emit_paths_or_raw_exception(self):
        result = handoff.CaptureHandoff({"backup_created":True,"backup_file":"/private/file","sha256":"raw"},
                 {"ok":False, "code":"/private/failure", "bundle_file":"private.tar","error":"secret"},None)
        public = handoff.public_state_receipt(result)
        self.assertEqual(public["code"],"STATE_CAPTURE_NOT_VERIFIED")
        self.assertNotIn("bundle_file",public)
        self.assertNotIn("error",public)
        self.assertNotIn("backup_name",handoff.public_sqlite_disposition(result))
        self.assertFalse(public["full_application_recovery_certified"])


class OperatorWiringContracts(unittest.TestCase):
    def test_default_operator_has_no_state_capture_no_new_deadline_keyword(self):
        with tempfile.TemporaryDirectory(dir=RUN_ROOT,prefix="p") as tmp:
            base=Path(tmp); (base/"VERSION.txt").write_text("OWNED")
            args=SimpleNamespace(db=str(base/"live.db"),backup_dir=str(base/"backups"),verify_existing=None,
                                 timeout=300,execute=True,app_probe_mode=None)
            with patch.object(operator,"ROOT",base), patch.object(operator,"preflight",return_value={
                 "ok":True,"snapshot_bytes":1,"required_bytes":1,"free_bytes":10**9}), \
                 patch.object(operator,"create_sqlite_backup",return_value={"ok":True,"backup_created":True,"backup_file":NAME,"sha256":H}) as create, \
                 patch.object(operator,"verify_and_restore_isolated",return_value={"ok":True,"code":"OWNED_STUB"}) as restore, \
                 patch.object(operator,"emit"):
                self.assertEqual(operator.run(args),0)
            create.assert_called_once()
            self.assertNotIn("absolute_deadline",create.call_args.kwargs)
            self.assertEqual(create.call_args.kwargs["snapshot_timeout"],300)
            self.assertTrue(create.call_args.kwargs["preserve_existing_backups"])
            self.assertEqual(create.call_args.kwargs["max_files"],0)
            restore.assert_called_once_with(base/"backups",NAME,300,app_probe_mode=None)

    def test_optin_operator_binds_once_and_passes_same_bundle(self):
        with tempfile.TemporaryDirectory(dir=RUN_ROOT,prefix="p") as tmp:
            base=Path(tmp); (base/"VERSION.txt").write_text("OWNED"); plan=plan_for(base)
            args=SimpleNamespace(db=str(base/"live.db"),backup_dir=str(base/"backups"),verify_existing=None,
                                 timeout=300,execute=True,app_probe_mode="normal_boot")
            def native(**kw):
                receipt=kw["sqlite_snapshot_callback"](kw["deadline"])
                return native_result(receipt)
            with patch.object(operator,"ROOT",base), patch.object(operator,"preflight",return_value={
                 "ok":True,"snapshot_bytes":1,"required_bytes":1,"free_bytes":10**9}), \
                 patch.object(operator,"create_sqlite_backup",return_value={"ok":True,"backup_created":True,"backup_file":NAME,"sha256":H}) as create, \
                 patch.object(operator,"verify_and_restore_isolated",return_value={"ok":True,"code":"OWNED_STUB"}) as restore, \
                 patch.object(state,"capture_state",native), patch.object(operator,"emit"), patch.object(time,"monotonic",return_value=100):
                self.assertEqual(operator.run(args,state_plan=plan),0)
            create.assert_called_once()
            self.assertEqual(create.call_args.kwargs["absolute_deadline"],400)
            self.assertEqual(create.call_args.kwargs["snapshot_timeout"],300)
            restore.assert_called_once()
            bundle=restore.call_args.kwargs["state_bundle"]
            self.assertIs(type(bundle),handoff.BoundStateBundle)
            self.assertEqual(bundle.backup_name,NAME)
            self.assertEqual(bundle.sqlite.sha256,H)

    def test_failed_state_does_not_start_restore_or_repeat_snapshot(self):
        with tempfile.TemporaryDirectory(dir=RUN_ROOT,prefix="p") as tmp:
            base=Path(tmp); (base/"VERSION.txt").write_text("OWNED"); plan=plan_for(base)
            args=SimpleNamespace(db=str(base/"live.db"),backup_dir=str(base/"backups"),verify_existing=None,
                                 timeout=300,execute=True,app_probe_mode="normal_boot")
            def native(**kw):
                receipt=kw["sqlite_snapshot_callback"](kw["deadline"])
                return native_result(receipt,ok=False)
            with patch.object(operator,"ROOT",base), patch.object(operator,"preflight",return_value={
                 "ok":True,"snapshot_bytes":1,"required_bytes":1,"free_bytes":10**9}), \
                 patch.object(operator,"create_sqlite_backup",return_value={"ok":True,"backup_created":True,"backup_file":NAME,"sha256":H}) as create, \
                 patch.object(operator,"verify_and_restore_isolated") as restore, \
                 patch.object(state,"capture_state",native), patch.object(operator,"emit") as emit:
                self.assertEqual(operator.run(args,state_plan=plan),2)
            create.assert_called_once(); restore.assert_not_called()
            self.assertTrue(emit.call_args.args[0]["backup_created"])
            self.assertEqual(emit.call_args.args[0]["backup_name"],NAME)

    def test_bundle_without_app_mode_refused_before_sqlite_read(self):
        with patch.object(operator,"validate_backup") as validate:
            result=operator.verify_and_restore_isolated(self_path := RUN_ROOT,NAME,300,state_bundle=bundle_for(self_path))
        self.assertEqual(result["code"],"STATE_REQUIRES_EXPLICIT_APP_PROBE")
        validate.assert_not_called()


class ProbeHookContracts(unittest.TestCase):
    def test_failed_state_prevents_child_after_real_owned_source_preparation(self):
        with tempfile.TemporaryDirectory(dir=RUN_ROOT,prefix="p") as tmp:
            base=Path(tmp); project=base/"p"; project.mkdir(); (project/"app.py").write_text("# owned marker NEVER executed\n")
            workspace=base/".isolated_restore_327_x"; workspace.mkdir()
            db=workspace/"restoration-test.db"; db.write_bytes(b"OWNED NON SQLITE MARKER")
            bundle=bundle_for(base)
            with patch.object(state,"restore_state",return_value={"ok":False,"state_ready_before_app":False,"code":"OWNED_FAILURE"}) as restore, \
                 patch.object(probe.subprocess,"Popen") as child:
                result=probe.run_app_probe(project_root=project,restored_database=db,workspace=workspace,
                                           deadline=time.monotonic()+30,mode="normal_boot",state_bundle=bundle)
            self.assertFalse(result["ok"])
            self.assertEqual(result["code"],"STATE_NOT_READY_BEFORE_APP")
            self.assertTrue((workspace/"source"/"app.py").is_file())
            restore.assert_called_once(); child.assert_not_called()
            self.assertEqual(restore.call_args.kwargs["expected_database_identity"], state._identity(db.stat()))
            self.assertFalse((workspace/"source"/"data").exists())

    def test_restore_handoff_keeps_exact_workspace_db_identity_and_deadline(self):
        with tempfile.TemporaryDirectory(dir=RUN_ROOT,prefix="p") as tmp:
            base=Path(tmp); workspace=base/".isolated_restore_327_x"; workspace.mkdir()
            db=workspace/"restoration-test.db"; db.write_bytes(b"OWNED NON SQLITE MARKER")
            deadline=time.monotonic()+30; info=db.stat()
            with patch.object(state,"restore_state",return_value={"ok":True,"state_ready_before_app":True}) as restore:
                result=handoff.restore_before_app(bundle_for(base),source=workspace/"source",restored_database=db,
                                                  workspace=workspace,database_info=info,deadline=deadline)
            self.assertTrue(result["state_ready_before_app"])
            self.assertEqual(restore.call_args.kwargs["workspace"],workspace)
            self.assertEqual(restore.call_args.kwargs["deadline"],deadline)
            self.assertEqual(restore.call_args.kwargs["expected_database_identity"],state._identity(info))
            with patch.object(state,"restore_state") as restore:
                with self.assertRaises(handoff.HandoffError):
                    handoff.restore_before_app(bundle_for(base),source=workspace/"other",restored_database=db,
                                               workspace=workspace,database_info=info,deadline=deadline)
                restore.assert_not_called()


@unittest.skipUnless(os.name=="posix","Native POSIX state FD path; NOT certified on Windows")
class NativeStateAdapterContracts(unittest.TestCase):
    def test_native_state_to_same_owned_workspace_without_sqlite_or_app(self):
        with tempfile.TemporaryDirectory(dir=RUN_ROOT,prefix="p") as tmp:
            base=Path(tmp); plan=plan_for(base)
            for scope in plan.scopes:
                scope.source.mkdir(); (scope.source/"owned.json").write_bytes(b"OPAQUE OWNED BYTES")
            plan.publication.mkdir(parents=True,mode=0o700); plan.publication.chmod(0o700)
            capture=Mock(return_value={"ok":True,"backup_created":True,"backup_file":NAME,"sha256":H})
            deadline=time.monotonic()+30
            captured=handoff.capture_with_state(plan=plan,source=base/"live.db",create_snapshot=capture,deadline=deadline)
            self.assertTrue(captured.ok,captured.state_result); capture.assert_called_once()
            workspace=base/".isolated_restore_327_x"; workspace.mkdir()
            (workspace/"source").mkdir(); db=workspace/"restoration-test.db"; db.write_bytes(b"NOT SQLITE")
            result=handoff.restore_before_app(captured.bundle,source=workspace/"source",restored_database=db,
                                              workspace=workspace,database_info=db.stat(),deadline=deadline)
            self.assertTrue(result["ok"],result)
            self.assertEqual((workspace/"source/data/continuous_evolution_os/owned.json").read_bytes(),b"OPAQUE OWNED BYTES")
            self.assertEqual((workspace/"source/data/runtime/owned.json").read_bytes(),b"OPAQUE OWNED BYTES")
            self.assertEqual(db.read_bytes(),b"NOT SQLITE")
            again=handoff.restore_before_app(captured.bundle,source=workspace/"source",restored_database=db,
                                             workspace=workspace,database_info=db.stat(),deadline=deadline)
            self.assertFalse(again["ok"])  # Exclusive data root; never merge/overwrite.


if __name__=="__main__":
    unittest.main()
