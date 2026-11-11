"""Typed single-use native SQLite-set producer; no CLI/job or data authority.

All members use the SAME absolute phase-A deadline. Partial captures remain
private and preserved. Individual snapshots and opaque-state bracketing do not
certify continuous cross-store quiescence or application recovery.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import os
from pathlib import Path
import re
import time

from engines import recovery_non_sqlite_state as state
from tools.recovery_sqlite_prepare import SqliteSnapshotProducer, MAX_SNAPSHOT_BYTES

MAX_DATABASES = 8
MAX_PHASE_SECONDS = 300.0


class SqliteSetError(ValueError):
    """Closed mechanism codes; no source paths, payloads or original errors."""


@dataclass(frozen=True)
class SqliteSource:
    source_id: str
    source: Path
    maximum_bytes: int

    def __post_init__(self):
        if (type(self.source_id) is not str
                or not re.fullmatch(r"principal|aux_[a-z0-9_]{1,40}", self.source_id)
                or type(self.maximum_bytes) is not int
                or not 0 < self.maximum_bytes <= MAX_SNAPSHOT_BYTES):
            raise SqliteSetError("INVALID_SQLITE_SET_SOURCE")
        state._path(self.source)

    @property
    def restore_relative(self):
        return ("restoration-test.db" if self.source_id == "principal"
                else "sqlite/" + self.source_id + ".db")


@dataclass(frozen=True)
class SqliteSetPlan:
    operation_id: str
    proposal_sha256: str
    sources: tuple[SqliteSource, ...]
    publication: Path
    snapshot_timeout: float = 15.0

    def __post_init__(self):
        if (type(self.operation_id) is not str or not state.REF.fullmatch(self.operation_id)
                or type(self.proposal_sha256) is not str or not state.HEX.fullmatch(self.proposal_sha256)
                or type(self.sources) is not tuple or not 2 <= len(self.sources) <= MAX_DATABASES
                or any(type(s) is not SqliteSource for s in self.sources)
                or self.sources[0].source_id != "principal"
                or tuple(s.source_id for s in self.sources[1:])
                   != tuple(sorted(s.source_id for s in self.sources[1:]))
                or len({s.source_id for s in self.sources}) != len(self.sources)
                or len({os.path.normcase(str(s.source)) for s in self.sources}) != len(self.sources)
                or sum(s.maximum_bytes for s in self.sources) > MAX_SNAPSHOT_BYTES
                or type(self.snapshot_timeout) not in (int, float)
                or not math.isfinite(self.snapshot_timeout)
                or not 0 < self.snapshot_timeout <= MAX_PHASE_SECONDS):
            raise SqliteSetError("INVALID_SQLITE_SET_PLAN")
        state._path(self.publication)
        for source in self.sources:
            SqliteSource.__post_init__(source)
            if (source.source == self.publication
                    or source.source.is_relative_to(self.publication)
                    or self.publication.is_relative_to(source.source)):
                raise SqliteSetError("SQLITE_SET_PUBLICATION_OVERLAP")


class SqliteSetProducer:
    """Trusted-code opt-in only. Caller closes after state handoff consumes FDs."""

    def __init__(self, plan: SqliteSetPlan):
        if type(plan) is not SqliteSetPlan:
            raise SqliteSetError("TYPED_SQLITE_SET_PLAN_REQUIRED")
        SqliteSetPlan.__post_init__(plan)
        self.plan = plan
        self._members = tuple((s, SqliteSnapshotProducer(
            source=s.source, publication=plan.publication,
            operation_id=plan.operation_id, proposal_sha256=plan.proposal_sha256,
            snapshot_timeout=plan.snapshot_timeout, snapshot_byte_limit=s.maximum_bytes))
            for s in plan.sources)
        self._prepared = None
        self._deadline = None
        self._attempted = self._validated = self._closed = False
        self._complete = False

    @property
    def result(self):
        return {
            "schema": "OWNED_SQLITE_SET_PRODUCER_V1",
            "prepare_completed": self._prepared is not None,
            "validated_set": self._complete,
            "all_members_published": bool(self._validated and all(
                p.result.get("ok") is True for _, p in self._members)),
            "recapture_attempted": False,
            "continuous_cross_store_consistency_certified": False,
            "full_application_recovery_certified": False,
            "members": tuple((s.source_id, p.result) for s, p in self._members),
        }

    def _check(self, deadline, *, first=False):
        if (type(deadline) not in (int, float) or not math.isfinite(deadline)
                or deadline <= time.monotonic()):
            raise SqliteSetError("SQLITE_SET_DEADLINE_EXPIRED")
        if first and deadline - time.monotonic() > MAX_PHASE_SECONDS:
            raise SqliteSetError("SQLITE_SET_PHASE_BUDGET_EXCEEDED")
        if self._deadline is not None and deadline != self._deadline:
            raise SqliteSetError("SQLITE_SET_DEADLINE_CHANGED")

    def _source_origins(self):
        state._native()
        origins = []
        for source in self.plan.sources:
            parent = state._directory(source.source.parent)
            try:
                info = os.stat(source.source.name, dir_fd=parent, follow_symlinks=False)
                state._regular(info)
                origins.append(state._capture_identity(info)[:6])
            finally:
                os.close(parent)
        if len({origin[:2] for origin in origins}) != len(origins):
            raise SqliteSetError("SQLITE_SET_SOURCE_ALIAS")
        return tuple(origins)

    def prepare(self, absolute_deadline):
        if self._closed or self._attempted:
            raise SqliteSetError("SECOND_SQLITE_SET_CAPTURE_DENIED")
        self._attempted = True
        self._check(absolute_deadline, first=True)
        self._deadline = absolute_deadline
        origins = self._source_origins()
        captures = []
        for (source, producer), origin in zip(self._members, origins):
            self._check(absolute_deadline)
            capture = producer.prepare(absolute_deadline)
            if state._capture_identity(producer._source_info)[:6] != origin:
                raise SqliteSetError("SQLITE_SET_SOURCE_CHANGED")
            captures.append((source.source_id, capture))
        self._check(absolute_deadline)
        self._prepared = state.PreparedSqliteSetCapture(
            self.plan.operation_id, self.plan.proposal_sha256, tuple(captures))
        return self._prepared

    def validate(self, prepared, absolute_deadline):
        if self._closed or self._validated:
            raise SqliteSetError("SECOND_SQLITE_SET_VALIDATION_DENIED")
        self._validated = True
        self._check(absolute_deadline)
        if (prepared is not self._prepared or type(prepared) is not state.PreparedSqliteSetCapture
                or prepared.operation_id != self.plan.operation_id
                or prepared.proposal_sha256 != self.plan.proposal_sha256
                or tuple(label for label, _ in prepared.members)
                   != tuple(s.source_id for s in self.plan.sources)):
            raise SqliteSetError("FOREIGN_PREPARED_SQLITE_SET")
        validated = []
        for (source, producer), (label, capture) in zip(self._members, prepared.members):
            self._check(absolute_deadline)
            value = producer.validate(capture, absolute_deadline)
            if value.prepared is not capture or label != source.source_id:
                raise SqliteSetError("FOREIGN_SQLITE_SET_MEMBER")
            validated.append((label, value))
        self._check(absolute_deadline)
        self._complete = True
        return state.ValidatedSqliteSetCapture(prepared, tuple(validated))

    def close(self):
        self._closed = True
        failed = False
        for _, producer in self._members:
            try:
                producer.close()
            except BaseException:
                failed = True
        if failed:
            raise SqliteSetError("SQLITE_SET_CLOSE_NOT_VERIFIED")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
