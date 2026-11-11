"""Explicit trusted-code handoff for ALL declared SQLite members plus state.

Not a data-operation authorization. No App, job, environment or CLI selects it.
Individual snapshots and opaque bracket equality never certify continuous
cross-store consistency or full application recovery.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

from engines import recovery_non_sqlite_state as state
from engines import recovery_sqlite_set_contract as contract
from tools.recovery_sqlite_set import SqliteSetPlan, SqliteSetProducer
from tools.recovery_state_adapter import StateRecoveryPlan


class SqliteSetHandoffError(ValueError):
    """Closed codes, without source paths or opaque bytes."""


@dataclass(frozen=True)
class StateSqliteSetPlan:
    state: StateRecoveryPlan
    sqlite: SqliteSetPlan

    def __post_init__(self):
        if type(self.state) is not StateRecoveryPlan or type(self.sqlite) is not SqliteSetPlan:
            raise SqliteSetHandoffError("TYPED_COMPLETE_SET_PLAN_REQUIRED")
        # Recheck immutable contracts at the boundary, not another object's status.
        StateRecoveryPlan.__post_init__(self.state)
        SqliteSetPlan.__post_init__(self.sqlite)
        if (self.state.operation_id != self.sqlite.operation_id
                or self.state.proposal_sha256 != self.sqlite.proposal_sha256
                or self.state.publication.parent != self.sqlite.publication
                or self.state.profile_id is not None
                or self.state.layout_id != state.LAYOUT_CE_COLOCATED_SENTINEL_AUTOPILOT_V1
                or tuple(str(s.source) for s in self.sqlite.sources)
                   != self.state.authorization.protected_sqlite_paths
                or self.state.limits.entries < len(self.sqlite.sources)
                   + len(state._LAYOUT_REQUIRED_ENTRIES[self.state.layout_id])):
            raise SqliteSetHandoffError("FOREIGN_OR_INCOMPLETE_SQLITE_SET_PLAN")
        for source in self.sqlite.sources:
            if (source.source == self.state.publication
                    or source.source.is_relative_to(self.state.publication)
                    or self.state.publication.is_relative_to(source.source)):
                raise SqliteSetHandoffError("SQLITE_SET_STATE_PUBLICATION_OVERLAP")


@dataclass(frozen=True)
class BoundSqliteSetStateBundle:
    plan: StateSqliteSetPlan
    archive: Path
    archive_sha256: str
    manifest_sha256: str
    sqlite: contract.SqliteSetReceipt

    def __post_init__(self):
        if type(self.plan) is not StateSqliteSetPlan:
            raise SqliteSetHandoffError("TYPED_COMPLETE_SET_PLAN_REQUIRED")
        StateSqliteSetPlan.__post_init__(self.plan)
        state._path(self.archive)
        if (self.archive.parent != self.plan.state.publication
                or re.fullmatch(r"state-[0-9a-f]{32}\.tar", self.archive.name) is None
                or type(self.archive_sha256) is not str or not state.HEX.fullmatch(self.archive_sha256)
                or type(self.manifest_sha256) is not str or not state.HEX.fullmatch(self.manifest_sha256)):
            raise SqliteSetHandoffError("INVALID_BOUND_SQLITE_SET_ARCHIVE")
        try:
            contract.to_record(self.sqlite)
        except contract.SqliteSetContractError:
            raise SqliteSetHandoffError("SQLITE_SET_RECEIPT_NOT_VERIFIED") from None
        if (self.sqlite.artifact_id != self.plan.sqlite.operation_id
                or tuple((m.source_id, m.maximum_bytes) for m in self.sqlite.members)
                   != tuple((s.source_id, s.maximum_bytes) for s in self.plan.sqlite.sources)):
            raise SqliteSetHandoffError("FOREIGN_SQLITE_SET_RECEIPT")


    @property
    def operation_id(self):
        return self.plan.state.operation_id

    @property
    def proposal_sha256(self):
        return self.plan.state.proposal_sha256

    @property
    def layout_id(self):
        return self.plan.state.layout_id

    @property
    def limits(self):
        return self.plan.state.limits

    @property
    def scope_roles(self):
        return tuple(sorted(s.role for s in self.plan.state.scopes))


@dataclass(frozen=True)
class SqliteSetCaptureHandoff:
    sqlite_result: dict
    state_result: dict
    bundle: BoundSqliteSetStateBundle | None

    def __post_init__(self):
        if type(self.sqlite_result) is not dict or type(self.state_result) is not dict:
            raise SqliteSetHandoffError("TYPED_SQLITE_SET_HANDOFF_REQUIRED")
        members = self.sqlite_result.get("members")
        if (type(members) is not tuple
                or any(type(row) is not tuple or len(row) != 2 or type(row[1]) is not dict
                       for row in members)
                or type(self.state_result.get("ok")) is not bool
                or type(self.state_result.get("sqlite_callback_invoked")) is not bool
                or (self.bundle is not None and type(self.bundle) is not BoundSqliteSetStateBundle)):
            raise SqliteSetHandoffError("SQLITE_SET_HANDOFF_NOT_VERIFIED")
        try:
            contract.member_budgets(tuple((label, 1) for label, _ in members))
        except contract.SqliteSetContractError:
            raise SqliteSetHandoffError("SQLITE_SET_HANDOFF_NOT_VERIFIED") from None
        for _, result in members:
            if (any(type(result.get(k)) is not bool for k in
                    ("ok", "sqlite_capture_attempted", "prepare_completed", "backup_created"))
                    or (result["backup_created"] and not result["prepare_completed"])
                    or (result["prepare_completed"] and not result["sqlite_capture_attempted"])
                    or (result["ok"] and not result["backup_created"])
                    or (result["sqlite_capture_attempted"]
                        and not self.state_result["sqlite_callback_invoked"])):
                raise SqliteSetHandoffError("SQLITE_SET_HANDOFF_NOT_VERIFIED")
        if self.bundle is not None:
            if tuple(label for label, _ in members) != tuple(m.source_id for m in self.bundle.sqlite.members):
                raise SqliteSetHandoffError("FOREIGN_SQLITE_SET_MEMBER")
            observed = dict(members)
            for member in self.bundle.sqlite.members:
                own = observed[member.source_id]
                prepared = own.get("worker_prepared_receipt")
                if (own.get("backup_file") != member.backup_file
                        or own.get("sha256") != member.sha256
                        or type(prepared) is not dict
                        or prepared.get("capture_id") != member.capture_id
                        or prepared.get("snapshot_byte_limit") != member.maximum_bytes):
                    raise SqliteSetHandoffError("FOREIGN_SQLITE_SET_MEMBER")

    @property
    def ok(self):
        self.__post_init__()
        if self.bundle is None:
            return False
        return (self.state_result.get("ok") is True
                and self.state_result.get("state_published") is True
                and self.state_result.get("same_prepared_sqlite_set_verified") is True
                and self.state_result.get("sqlite_receipt") == contract.to_record(self.bundle.sqlite)
                and self.sqlite_result.get("validated_set") is True
                and self.sqlite_result.get("all_members_published") is True)


def capture_set_with_state(*, plan: StateSqliteSetPlan, deadline: float) -> SqliteSetCaptureHandoff:
    """One phase A, one owned producer, SAME capture capabilities throughout."""
    if type(plan) is not StateSqliteSetPlan:
        raise SqliteSetHandoffError("TYPED_COMPLETE_SET_PLAN_REQUIRED")
    StateSqliteSetPlan.__post_init__(plan)
    state._check_time(deadline)
    bundle = None
    with SqliteSetProducer(plan.sqlite) as producer:
        callbacks = state.PreparedSqliteSetCallbacks(
            tuple((s.source_id, s.source, s.maximum_bytes) for s in plan.sqlite.sources),
            producer.prepare, producer.validate)
        result = state.capture_state(
            scopes=plan.state.scopes, authorization=plan.state.authorization,
            publication=plan.state.publication, deadline=deadline, limits=plan.state.limits,
            layout_binding=state.StateLayoutBinding(
                plan.state.layout_id, plan.state.operation_id, plan.state.proposal_sha256),
            sqlite_set_callbacks=callbacks)
        sqlite_result = producer.result
        try:
            if result.get("ok") is True:
                state._check_time(deadline)
                if (result.get("state_published") is not True
                        or result.get("opaque_bracket_closed") is not True
                        or result.get("same_prepared_sqlite_set_verified") is not True
                        or sqlite_result.get("validated_set") is not True
                        or sqlite_result.get("all_members_published") is not True):
                    raise SqliteSetHandoffError("SQLITE_SET_HANDOFF_NOT_VERIFIED")
                receipt = contract.from_record(result.get("sqlite_receipt"))
                observed = dict(sqlite_result["members"])
                for member in receipt.members:
                    own = observed[member.source_id]
                    if (own.get("backup_created") is not True or own.get("ok") is not True
                            or own.get("backup_file") != member.backup_file
                            or own.get("sha256") != member.sha256
                            or own["worker_prepared_receipt"]["capture_id"] != member.capture_id
                            or own["worker_prepared_receipt"].get("snapshot_byte_limit") != member.maximum_bytes
                            or own.get("production_source_connection_bound") is not True):
                        raise SqliteSetHandoffError("FOREIGN_SQLITE_SET_MEMBER")
                bundle = BoundSqliteSetStateBundle(
                    plan, plan.state.publication / result["bundle_file"],
                    result["archive_sha256"], result["manifest_sha256"], receipt)
        except (SqliteSetHandoffError, contract.SqliteSetContractError, state.StateError,
                KeyError, TypeError, ValueError):
            result = {**result, "ok": False, "code": "SQLITE_SET_HANDOFF_NOT_VERIFIED"}
        return SqliteSetCaptureHandoff(sqlite_result, result, bundle)


def public_set_disposition(handoff):
    """Publication/capture facts only; never hidden paths or whole-recovery claims."""
    if type(handoff) is not SqliteSetCaptureHandoff:
        raise SqliteSetHandoffError("TYPED_SQLITE_SET_HANDOFF_REQUIRED")
    handoff.__post_init__()
    members = handoff.sqlite_result.get("members")
    if type(members) is not tuple:
        raise SqliteSetHandoffError("SQLITE_SET_HANDOFF_NOT_VERIFIED")
    attempted = sum(v.get("sqlite_capture_attempted") is True for _, v in members)
    prepared = sum(v.get("prepare_completed") is True for _, v in members)
    published = sum(v.get("backup_created") is True for _, v in members)
    verified = sum(v.get("ok") is True for _, v in members)
    invoked = handoff.state_result["sqlite_callback_invoked"]
    disposition = (
        "SET_AND_OPAQUE_BYTES_VERIFIED_NOT_FULL_RECOVERY" if handoff.ok else
        "MEMBERS_PUBLISHED_STATE_UNVERIFIED_PRESERVE" if members and published == len(members) else
        "PARTIALLY_PUBLISHED_PRESERVE_AND_DO_NOT_RETRY" if published else
        "CAPTURES_UNVALIDATED_PRESERVE_AND_DO_NOT_RETRY" if prepared else
        "ATTEMPTED_UNKNOWN_PRESERVE_AND_DO_NOT_RETRY" if attempted else
        "CALLBACK_INVOKED_SQLITE_NOT_ATTESTED_PRESERVE_AND_DO_NOT_RETRY" if invoked else "NOT_INVOKED")
    return {"expected_sqlite_members": len(members), "attempted_sqlite_members": attempted,
            "prepared_sqlite_members": prepared, "published_sqlite_members": published,
            "verified_sqlite_members": verified, "set_capture_callback_invoked": invoked,
            "sqlite_set_disposition": disposition, "recapture_attempted": False,
            "continuous_cross_store_consistency_certified": False,
            "full_application_recovery_certified": False}
