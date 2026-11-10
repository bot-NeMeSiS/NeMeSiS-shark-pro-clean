"""Opt-in typed handoff for one bracketed state capture and the SAME restore.

This code reference is not data-operation permission. No CLI switch activates it.
Unknown bytes require the explicit supplied data authority; secrets remain denied.
Bracketing is not continuous cross-store quiescence or full App recovery.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re
import time
from typing import Callable

from engines import recovery_non_sqlite_state as state


class HandoffError(ValueError):
    """Closed codes, never payload, source paths or original exception text."""


def _time(deadline):
    if type(deadline) not in (int, float) or not math.isfinite(deadline) or deadline <= 0:
        raise HandoffError("INVALID_STATE_HANDOFF_DEADLINE")
    if time.monotonic() >= deadline:
        raise HandoffError("STATE_HANDOFF_DEADLINE_EXPIRED")


def _flat_backup_name(name):
    return (type(name) is str and 1 <= len(name) <= 200
            and re.fullmatch(r"database_[A-Za-z0-9_-]+\.db", name) is not None)


@dataclass(frozen=True)
class StateRecoveryPlan:
    operation_id: str
    proposal_sha256: str
    scopes: tuple[state.Scope, ...]
    authorization: state.Authorization
    publication: Path
    limits: state.Limits = state.Limits()
    layout_id: str | None = None
    profile_id: str | None = None

    def __post_init__(self):
        if (type(self.operation_id) is not str or not state.REF.fullmatch(self.operation_id)
                or type(self.proposal_sha256) is not str or not state.HEX.fullmatch(self.proposal_sha256)
                or type(self.scopes) is not tuple or type(self.limits) is not state.Limits):
            raise HandoffError("INVALID_STATE_RECOVERY_PLAN")
        # Pure checks only. Actual native paths/ownership are checked by the
        # sealed FD-based implementation before its callback can run.
        state._scopes(self.scopes, self.authorization)
        if self.layout_id is not None:
            if (type(self.layout_id) is not str
                    or self.layout_id != state.LAYOUT_CE_COLOCATED_SENTINEL_AUTOPILOT_V1
                    or tuple(sorted(scope.role for scope in self.scopes)) != ("ce", "legacy_runtime")):
                raise HandoffError("INVALID_STATE_RECOVERY_LAYOUT")
        state._policy(self.profile_id, self.limits)
        if self.profile_id is not None and self.layout_id != state.LAYOUT_CE_COLOCATED_SENTINEL_AUTOPILOT_V1:
            raise HandoffError("INVALID_STATE_RECOVERY_PROFILE")
        state._path(self.publication)
        for scope in self.scopes:
            if (self.publication == scope.source or self.publication.is_relative_to(scope.source)
                    or scope.source.is_relative_to(self.publication)):
                raise HandoffError("STATE_PUBLICATION_SCOPE_OVERLAP")


@dataclass(frozen=True)
class BoundStateBundle:
    operation_id: str
    proposal_sha256: str
    archive: Path
    archive_sha256: str
    manifest_sha256: str
    sqlite: state.SqliteReceipt
    backup_name: str
    scope_roles: tuple[str, ...]
    limits: state.Limits
    layout_id: str | None = None
    profile_id: str | None = None

    def __post_init__(self):
        if (type(self.operation_id) is not str or not state.REF.fullmatch(self.operation_id)
                or type(self.proposal_sha256) is not str or not state.HEX.fullmatch(self.proposal_sha256)
                or not _flat_backup_name(self.backup_name)
                or type(self.limits) is not state.Limits
                or type(self.scope_roles) is not tuple or not self.scope_roles
                or any(type(role) is not str for role in self.scope_roles)
                or self.scope_roles != tuple(sorted(set(self.scope_roles)))
                or set(self.scope_roles) - state.ROLES):
            raise HandoffError("INVALID_BOUND_STATE_BUNDLE")
        state._policy(self.profile_id, self.limits)
        if self.profile_id is not None and self.layout_id != state.LAYOUT_CE_COLOCATED_SENTINEL_AUTOPILOT_V1:
            raise HandoffError("INVALID_BOUND_STATE_PROFILE")
        state._path(self.archive)
        for value in (self.archive_sha256, self.manifest_sha256):
            if type(value) is not str or not state.HEX.fullmatch(value):
                raise HandoffError("INVALID_BOUND_STATE_DIGEST")
        state._sqlite(self.sqlite)
        if self.sqlite.artifact_id != self.operation_id:
            raise HandoffError("FOREIGN_STATE_OPERATION")
        if self.layout_id is not None:
            if (type(self.layout_id) is not str
                    or self.layout_id != state.LAYOUT_CE_COLOCATED_SENTINEL_AUTOPILOT_V1
                    or self.scope_roles != ("ce", "legacy_runtime")):
                raise HandoffError("INVALID_BOUND_STATE_LAYOUT")


@dataclass(frozen=True)
class CaptureHandoff:
    sqlite_result: dict | None
    state_result: dict
    bundle: BoundStateBundle | None

    @property
    def ok(self):
        return self.bundle is not None and self.state_result.get("ok") is True


def capture_with_state(*, plan: StateRecoveryPlan, source: Path,
                       create_snapshot: Callable[..., dict], deadline: float) -> CaptureHandoff:
    """Trusted operator callback, once; manifest/data never supplies executable code."""
    if type(plan) is not StateRecoveryPlan:
        raise HandoffError("TYPED_STATE_PLAN_REQUIRED")
    _time(deadline)
    state._path(source)
    if str(source) not in plan.authorization.protected_sqlite_paths:
        raise HandoffError("ACTUAL_SQLITE_SOURCE_NOT_PROTECTED")
    if not callable(create_snapshot):
        raise HandoffError("TRUSTED_SNAPSHOT_CALLABLE_REQUIRED")
    sqlite_result = None
    invoked = False

    def capture_once(callback_deadline):
        nonlocal sqlite_result, invoked
        if invoked:
            raise HandoffError("SECOND_SQLITE_CAPTURE_DENIED")
        if type(callback_deadline) not in (int, float) or callback_deadline != deadline:
            raise HandoffError("FOREIGN_SQLITE_CAPTURE_DEADLINE")
        _time(deadline)
        invoked = True
        # The engine itself receives this absolute cap; not just a remaining
        # relative timeout which would restart after its own preparation.
        sqlite_result = create_snapshot(absolute_deadline=deadline)
        if (type(sqlite_result) is not dict or sqlite_result.get("ok") is not True
                or sqlite_result.get("backup_created") is not True
                or not _flat_backup_name(sqlite_result.get("backup_file"))
                or type(sqlite_result.get("sha256")) is not str
                or not state.HEX.fullmatch(sqlite_result["sha256"])):
            raise HandoffError("SQLITE_CAPTURE_NOT_SEALED_AND_VALIDATED")
        return state.SqliteReceipt(plan.operation_id, sqlite_result["sha256"], True)

    try:
        layout_binding = (None if plan.layout_id is None else
                          state.StateLayoutBinding(plan.layout_id, plan.operation_id, plan.proposal_sha256))
        result = state.capture_state(scopes=plan.scopes, authorization=plan.authorization,
                                     publication=plan.publication, deadline=deadline,
                                     sqlite_snapshot_callback=capture_once, limits=plan.limits,
                                     layout_binding=layout_binding, profile_id=plan.profile_id)
    except Exception:
        # A low-level failure after the callback cannot revoke or erase its
        # returned SQLite disposition. Preserve it and never retry.
        result = {"ok": False, "code": "STATE_CAPTURE_FAILED", "sqlite_callback_invoked": invoked,
                  "sqlite_disposition": "UNKNOWN_PRESERVE_AND_DO_NOT_RETRY" if invoked else "NOT_INVOKED"}
    bundle = None
    try:
        if result.get("ok") is True:
            _time(deadline)
            name = result.get("bundle_file")
            if (not invoked or type(sqlite_result) is not dict or type(name) is not str
                    or not re.fullmatch(r"state-[0-9a-f]{32}\.tar", name)
                    or result.get("state_published") is not True):
                raise HandoffError("INVALID_STATE_CAPTURE_HANDOFF")
            expected = state.SqliteReceipt(plan.operation_id, sqlite_result["sha256"], True)
            if result.get("sqlite_receipt") != state._sqlite(expected):
                raise HandoffError("FOREIGN_SQLITE_CAPTURE_RECEIPT")
            bundle = BoundStateBundle(plan.operation_id, plan.proposal_sha256, plan.publication / name,
                                      result["archive_sha256"], result["manifest_sha256"], expected,
                                      sqlite_result["backup_file"],
                                      tuple(sorted(s.role for s in plan.scopes)), plan.limits, plan.layout_id, plan.profile_id)
    except (HandoffError, state.StateError, KeyError, TypeError, ValueError):
        result = {**result, "ok": False, "code": "STATE_HANDOFF_NOT_VERIFIED"}
    # Keep the actual SQLite disposition even if the bracket or publication
    # fails. No second capture and no deletion of a valid SQLite artifact.
    return CaptureHandoff(sqlite_result, result, bundle)




def capture_prepared_with_state(*, plan: StateRecoveryPlan, source: Path,
                                producer, deadline: float) -> CaptureHandoff:
    """Explicit profile-only prepare -> full bracket -> SAME capture validation.

    The native producer is supplied by trusted operator code; this function is
    never selected by legacy capture_with_state, an App caller, a job or CLI.
    The caller owns producer.close() after this function returns.
    """
    from tools.recovery_sqlite_prepare import SqliteSnapshotProducer
    if type(plan) is not StateRecoveryPlan:
        raise HandoffError("TYPED_STATE_PLAN_REQUIRED")
    _time(deadline)
    state._path(source)
    if (plan.profile_id != state.CE_RUNTIME_STATE_V1
            or plan.layout_id != state.LAYOUT_CE_COLOCATED_SENTINEL_AUTOPILOT_V1):
        raise HandoffError("PREPARED_STATE_PROFILE_REQUIRED")
    if str(source) not in plan.authorization.protected_sqlite_paths:
        raise HandoffError("ACTUAL_SQLITE_SOURCE_NOT_PROTECTED")
    if (type(producer) is not SqliteSnapshotProducer or producer.source != source
            or producer.operation_id != plan.operation_id
            or producer.proposal_sha256 != plan.proposal_sha256
            or producer.publication != plan.publication.parent):
        raise HandoffError("FOREIGN_PREPARED_SQLITE_PRODUCER")
    layout = state.StateLayoutBinding(plan.layout_id, plan.operation_id, plan.proposal_sha256)
    result = state.capture_state(
        scopes=plan.scopes, authorization=plan.authorization,
        publication=plan.publication, deadline=deadline, limits=plan.limits,
        layout_binding=layout, profile_id=plan.profile_id,
        sqlite_prepared_callbacks=state.PreparedSqliteCallbacks(producer.prepare, producer.validate))
    sqlite_result = producer.result
    result["sqlite_disposition"] = sqlite_result["sqlite_disposition"]
    result["sqlite_capture_attempted"] = sqlite_result["sqlite_capture_attempted"]
    result["sqlite_prepare_completed"] = sqlite_result["prepare_completed"]
    result["source_connection_binding"] = sqlite_result["source_binding"]
    result["production_source_connection_bound"] = sqlite_result.get("production_source_connection_bound") is True
    bundle = None
    try:
        if result.get("ok") is True:
            _time(deadline)
            name = result.get("bundle_file")
            if (sqlite_result.get("ok") is not True
                    or sqlite_result.get("backup_created") is not True
                    or not _flat_backup_name(sqlite_result.get("backup_file"))
                    or type(name) is not str or not re.fullmatch(r"state-[0-9a-f]{32}\.tar", name)
                    or result.get("state_published") is not True
                    or result.get("opaque_bracket_closed") is not True
                    or result.get("same_prepared_sqlite_capture_verified") is not True
                    or result.get("sqlite_backup_file") != sqlite_result["backup_file"]):
                raise HandoffError("PREPARED_STATE_HANDOFF_NOT_VERIFIED")
            expected = state.SqliteReceipt(plan.operation_id, sqlite_result["sha256"], True)
            if result.get("sqlite_receipt") != state._sqlite(expected):
                raise HandoffError("FOREIGN_SQLITE_CAPTURE_RECEIPT")
            bundle = BoundStateBundle(
                plan.operation_id, plan.proposal_sha256, plan.publication / name,
                result["archive_sha256"], result["manifest_sha256"], expected,
                sqlite_result["backup_file"], tuple(sorted(s.role for s in plan.scopes)),
                plan.limits, plan.layout_id, plan.profile_id)
    except (HandoffError, state.StateError, KeyError, TypeError, ValueError):
        result = {**result, "ok": False, "code": "STATE_HANDOFF_NOT_VERIFIED"}
    return CaptureHandoff(sqlite_result, result, bundle)


def validate_operator_plan(*, plan, source, directory, app_probe_mode, verify_existing):
    """Pure code/data binding check, independent of storage observations."""
    if type(plan) is not StateRecoveryPlan:
        raise HandoffError("TYPED_STATE_PLAN_REQUIRED")
    state._path(source)
    state._path(directory)
    if (plan.publication.parent != directory or app_probe_mode not in ("read_only", "normal_boot")
            or verify_existing is not None):
        raise HandoffError("INVALID_STATE_OPERATOR_BINDING")
    if str(source) not in plan.authorization.protected_sqlite_paths:
        raise HandoffError("ACTUAL_SQLITE_SOURCE_NOT_PROTECTED")


def operator_preflight(*, plan, source, directory, app_probe_mode, verify_existing, storage,
                       restore_workspace_root=None, restore_workspace_identity=None):
    """Whole chosen-mode estimate before capture, not a reservation or quota."""
    validate_operator_plan(plan=plan, source=source, directory=directory,
                           app_probe_mode=app_probe_mode, verify_existing=verify_existing)
    expected = storage.get("snapshot_bytes")
    required = storage.get("required_bytes")
    free = storage.get("free_bytes")
    if (type(expected) is not int or expected <= 0 or type(required) is not int
            or type(free) is not int or required < 0 or free < 0):
        return {**storage, "ok": False, "code": "STATE_STORAGE_NOT_VERIFIED"}
    # Base operator gate = 2E+R. Include the same source/scratch allowance and
    # normal-boot clone journal which B otherwise checks only after capture.
    # State archive and extracted state coexist with that ONE restored DB.
    policy = state._policy(plan.profile_id, plan.limits)
    if restore_workspace_root is not None:
        from tools.recovery_workspace import workspace_capacity_preflight
        checked = workspace_capacity_preflight(
            source=source, directory=directory, restore_root=restore_workspace_root,
            snapshot_bytes=expected, app_probe_mode=app_probe_mode,
            expected_identity=restore_workspace_identity,
            state_archive_bytes=policy.archive_bytes, restored_state_bytes=policy.bytes)
        ready = storage.get("ok") is True and checked["ok"] is True
        return {**checked, "ok": ready, "code": "READY" if ready else "INSUFFICIENT_SPACE",
                "state_overhead_bytes": policy.archive_bytes + policy.bytes,
                "workspace_app_overhead_included": True}
    extra = 128 * 1024 * 1024 + policy.archive_bytes + policy.bytes
    if app_probe_mode == "normal_boot":
        extra += expected
    required += extra
    return {**storage, "required_bytes": required, "state_and_app_overhead_bytes": extra,
            "ok": storage.get("ok") is True and free >= required,
            "code": "READY" if storage.get("ok") is True and free >= required else "INSUFFICIENT_SPACE"}


def bind_verified_sqlite(bundle, *, backup_name, sqlite_sha256, deadline):
    """Must run before the existing ONE isolated restore starts."""
    if type(bundle) is not BoundStateBundle:
        raise HandoffError("TYPED_STATE_BUNDLE_REQUIRED")
    _time(deadline)
    if (bundle.backup_name != backup_name or type(sqlite_sha256) is not str
            or bundle.sqlite.sha256 != sqlite_sha256):
        raise HandoffError("FOREIGN_VERIFIED_SQLITE_ARCHIVE")


def restore_before_app(bundle, *, source: Path, restored_database: Path,
                       workspace: Path, database_info, deadline: float) -> dict:
    """No new SQLite restore; install only in this already-owned App workspace."""
    if type(bundle) is not BoundStateBundle:
        raise HandoffError("TYPED_STATE_BUNDLE_REQUIRED")
    _time(deadline)
    if (source != workspace / "source" or restored_database != workspace / "restoration-test.db"
            or not workspace.name.startswith(".isolated_restore_327_")):
        raise HandoffError("STATE_RESTORE_WORKSPACE_BINDING_FAILED")
    result = state.restore_state(bundle=bundle.archive, expected_archive_sha256=bundle.archive_sha256,
                                 expected_manifest_sha256=bundle.manifest_sha256,
                                 expected_sqlite=bundle.sqlite, workspace=workspace,
                                 expected_database_identity=state._identity(database_info),
                                 deadline=deadline, limits=bundle.limits,
                                 expected_layout_id=bundle.layout_id,
                                 expected_proposal_sha256=(bundle.proposal_sha256 if bundle.layout_id is not None else None),
                                 expected_scope_roles=(bundle.scope_roles if bundle.layout_id is not None else None),
                                 expected_profile_id=bundle.profile_id)
    if result.get("ok") is not True or result.get("state_ready_before_app") is not True:
        return result
    if bundle.layout_id is not None and (
            result.get("layout_id") != bundle.layout_id
            or result.get("scope_roles") != list(bundle.scope_roles)):
        return {**result, "ok": False, "state_ready_before_app": False,
                "code": "LAYOUT_BINDING_MISMATCH"}
    _time(deadline)
    return result


def public_sqlite_disposition(handoff):
    """Known publication evidence only; an interrupted callback is UNKNOWN."""
    value = handoff.sqlite_result
    invoked = handoff.state_result.get("sqlite_callback_invoked") is True
    created = (value.get("backup_created") if type(value) is dict else None)
    result = {"backup_created": created if type(created) is bool else (None if invoked else False),
              "sqlite_disposition": "PRESERVE_DO_NOT_RETRY" if invoked else "NOT_INVOKED"}
    if type(value) is dict:
        # Prepared capture distinguishes a preserved unvalidated artifact from
        # a final publication. Legacy callback dispositions keep their values.
        known = {"NOT_INVOKED", "CAPTURE_ATTEMPT_PRESERVE_AND_DO_NOT_RETRY",
                 "CAPTURED_UNVALIDATED_PRESERVED_DO_NOT_RETRY",
                 "PUBLISHED_PRESERVE_AND_DO_NOT_RETRY",
                 "VALIDATED_PUBLISHED_PRESERVE_DO_NOT_RETRY"}
        if type(value.get("prepare_completed")) is bool:
            result["sqlite_prepare_completed"] = value["prepare_completed"]
            result["sqlite_capture_attempted"] = value.get("sqlite_capture_attempted") is True
            if value.get("sqlite_disposition") in known:
                result["sqlite_disposition"] = value["sqlite_disposition"]
        if _flat_backup_name(value.get("backup_file")):
            result["backup_name"] = value["backup_file"]
        if type(value.get("sha256")) is str and state.HEX.fullmatch(value["sha256"]):
            result["sha256"] = value["sha256"]
    return result


def public_state_receipt(handoff):
    """No original relative paths, archive paths, authorization ref or raw errors."""
    value = handoff.state_result
    allowed = ("schema", "ok", "code", "state_published", "sqlite_callback_invoked",
               "sqlite_disposition", "entries", "state_bytes", "archive_sha256", "manifest_sha256",
               "layout_id", "scope_roles", "profile_id", "sqlite_capture_mode",
               "opaque_bracket_closed", "sqlite_validator_invoked",
               "sqlite_capture_attempted", "sqlite_prepare_completed",
               "source_connection_binding", "production_source_connection_bound",
               "same_prepared_sqlite_capture_verified", "full_application_recovery_certified",
               "continuous_cross_store_consistency_certified")
    result = {key: value[key] for key in allowed if key in value}
    # Codes originating in this fixed module are closed. No data-derived strings.
    if type(result.get("code")) is not str or not re.fullmatch(r"[A-Z0-9_]{1,96}", result["code"]):
        result["code"] = "STATE_CAPTURE_NOT_VERIFIED"
    result["full_application_recovery_certified"] = False
    result["continuous_cross_store_consistency_certified"] = False
    return result
