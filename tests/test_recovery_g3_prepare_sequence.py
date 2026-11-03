"""Owned G3 mechanism tests; no live paths, App imports or network operations.

These tests are authored for a later explicitly reviewed test run. Native cases
create only small synthetic SQLite/opaque files under pytest's owned tmp_path.
They prove mechanism properties, never real-data recovery or quiescence.
Native cases exercise the isolated worker's source-connection FD attestation.
All files remain synthetic and owned; this is not a real-data recovery proof.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
from types import SimpleNamespace
import time

import pytest

from engines import recovery_non_sqlite_state as state
from tools import recovery_sqlite_prepare as prepared_sqlite
from tools import recovery_state_adapter as adapter


OPERATION = "OWNED_G3_SEQUENCE"
PROPOSAL = "a" * 64
LAYOUT = state.LAYOUT_CE_COLOCATED_SENTINEL_AUTOPILOT_V1
PROFILE = state.CE_RUNTIME_STATE_V1
_HAS_STRONG_FDS = (
    os.name == "posix"
    and bool(getattr(os, "O_NOFOLLOW", 0))
    and bool(getattr(os, "O_DIRECTORY", 0))
    and all(fn in os.supports_dir_fd for fn in (os.open, os.stat, os.mkdir, os.unlink, os.link))
    and os.scandir in os.supports_fd
)
native_state = pytest.mark.skipif(not _HAS_STRONG_FDS, reason="strong POSIX FD primitives required")
native_sqlite = pytest.mark.skipif(
    not _HAS_STRONG_FDS or not Path("/proc/self/fd").is_dir(),
    reason="owned SQLite producer requires strong POSIX FDs and /proc/self/fd",
)


def _plan(tmp_path, *, profile=PROFILE, layout=LAYOUT):
    ce = tmp_path / "ce"
    runtime = tmp_path / "runtime"
    source = tmp_path / "live" / "owned.db"
    publication = tmp_path / "backups" / "state"
    scopes = (state.Scope("ce", ce), state.Scope("legacy_runtime", runtime))
    authority = state.Authorization(
        "OWNED_G3_AUTHORITY", tuple((scope.role, str(scope.source)) for scope in scopes),
        True, (str(source),),
    )
    return adapter.StateRecoveryPlan(
        OPERATION, PROPOSAL, scopes, authority, publication,
        layout_id=layout, profile_id=profile,
    ), source


@pytest.fixture
def owned(tmp_path):
    plan, source = _plan(tmp_path)
    for folder in (plan.scopes[0].source, plan.scopes[1].source, source.parent,
                   plan.publication.parent, plan.publication):
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        folder.chmod(0o700)
    (plan.scopes[0].source / "product_memory.json").write_bytes(b'{"owned":1}\n')
    (plan.scopes[0].source / "sentinel_issues_memory.json").write_bytes(b'{"issues":[]}\n')
    (plan.scopes[1].source / "sentinel_autopilot_memory.json").write_bytes(b'{"actions":[]}\n')
    # An additional opaque history member ensures the bracket covers every
    # file, not only the three canonical consumer names.
    history = plan.scopes[0].source / "history.bin"
    history.write_bytes(b"owned-history-before-bracket\n")
    with closing(sqlite3.connect(source)) as conn:
        conn.execute("CREATE TABLE owned_rows (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO owned_rows(value) VALUES ('captured-before')")
        conn.execute("CREATE TABLE matches (owned_id INTEGER NOT NULL)")
        conn.execute("INSERT INTO matches(owned_id) VALUES (1)")
        conn.commit()
    return SimpleNamespace(plan=plan, source=source, history=history)


@pytest.fixture
def copy_calls(monkeypatch):
    # Instrument the one isolated capture worker, not a fallback or recapture.
    real_copy = prepared_sqlite._run_capture_worker
    calls = []

    def counted(*args, **kwargs):
        record = {"args": args, "kwargs": kwargs, "response": None}
        calls.append(record)
        response = real_copy(*args, **kwargs)
        record["response"] = response
        return response

    monkeypatch.setattr(prepared_sqlite, "_run_capture_worker", counted)
    return calls


def _producer(owned):
    return prepared_sqlite.SqliteSnapshotProducer(
        source=owned.source, publication=owned.plan.publication.parent,
        operation_id=OPERATION, proposal_sha256=PROPOSAL, snapshot_timeout=60.0,
    )


def _capture(owned, producer, *, prepare=None, validate=None, deadline=None):
    return state.capture_state(
        scopes=owned.plan.scopes, authorization=owned.plan.authorization,
        publication=owned.plan.publication, deadline=deadline or time.monotonic() + 60.0,
        layout_binding=state.StateLayoutBinding(LAYOUT, OPERATION, PROPOSAL),
        profile_id=PROFILE,
        sqlite_prepared_callbacks=state.PreparedSqliteCallbacks(
            prepare or producer.prepare, validate or producer.validate,
        ),
    )


def _captured_path(producer):
    return producer.publication / producer._workspace / "snapshot.partial"


def _rows(path):
    with closing(sqlite3.connect("file:" + path.as_posix() + "?mode=ro", uri=True)) as conn:
        return conn.execute("SELECT value FROM owned_rows ORDER BY id").fetchall()


def _assert_no_state_or_sqlite_publication(owned):
    assert list(owned.plan.publication.glob("state-*.tar")) == []
    assert list(owned.plan.publication.parent.glob("database_*.db")) == []


def _observe_scans(monkeypatch, events):
    real_scan = state._scan

    def observed(*args, **kwargs):
        writer = args[3] if len(args) > 3 else kwargs.get("writer")
        name = "before" if writer is not None else "after"
        result = real_scan(*args, **kwargs)
        events.append(name)
        return result

    monkeypatch.setattr(state, "_scan", observed)


@native_sqlite
def test_validator_runs_only_after_complete_bracket_and_same_capture_is_published(
        owned, monkeypatch, copy_calls, capsys):
    events, capabilities, guarded_work = [], [], []
    _observe_scans(monkeypatch, events)
    deadline = time.monotonic() + 60.0
    with _producer(owned) as producer:
        real_validate = prepared_sqlite._validate_capture_worker
        real_hash = state._hash_fd

        def guarded_worker_validation(owner):
            guarded_work.append(("worker_validate", owner.binding["capture_id"], tuple(events)))
            assert events == ["before", "prepare", "after", "validate"]
            # A fresh validation child performs integrity/count/hash work only
            # after this dispatch. PREPARED is never a final receipt.
            return real_validate(owner)

        def traced_hash(fd, cap, maximum):
            if producer._fd is not None and fd == producer._fd:
                guarded_work.append(("hash", fd, tuple(events)))
                assert "after" in events, "captured snapshot hash preceded bracket closure"
            return real_hash(fd, cap, maximum)

        monkeypatch.setattr(prepared_sqlite, "_validate_capture_worker", guarded_worker_validation)
        monkeypatch.setattr(state, "_hash_fd", traced_hash)

        def prepare(cap):
            assert cap == deadline
            assert events == ["before"]
            events.append("prepare")
            captured = producer.prepare(cap)
            capabilities.append(captured)
            assert producer.result["backup_created"] is False
            assert not hasattr(captured, "published_and_validated")
            with pytest.raises(FrozenInstanceError):
                captured.capture_id = "b" * 32
            return captured

        def validate(captured, cap):
            assert cap == deadline
            assert events == ["before", "prepare", "after"]
            assert captured is capabilities[0]
            assert state._capture_identity(os.fstat(captured.snapshot_fd)) == captured.snapshot_identity
            assert list(owned.plan.publication.glob("state-*.tar")) == []
            events.append("validate")
            final = producer.validate(captured, cap)
            assert final.prepared is captured
            return final

        result = _capture(owned, producer, prepare=prepare, validate=validate, deadline=deadline)
        captured = capabilities[0]
        assert result["ok"] is True
        assert result["entries"] == 4
        assert result["opaque_bracket_closed"] is True
        assert result["same_prepared_sqlite_capture_verified"] is True
        assert result["sqlite_receipt"] == state._sqlite(
            state.SqliteReceipt(OPERATION, producer.result["sha256"], True))
        published = producer.publication / producer.result["backup_file"]
        assert (published.stat().st_dev, published.stat().st_ino) == captured.snapshot_identity[:2]
        assert published.stat().st_nlink == 1
        assert hashlib.sha256(published.read_bytes()).hexdigest() == result["sqlite_receipt"]["sha256"]
        assert _rows(published) == [("captured-before",)]
        assert not _captured_path(producer).exists()
        assert result["continuous_cross_store_consistency_certified"] is False
        assert result["full_application_recovery_certified"] is False
        assert producer.result["production_source_connection_bound"] is True
        assert producer.result["source_binding"] == "ISOLATED_WORKER_CONNECTION_FD_V1"
        prepared_receipt = producer.result["worker_prepared_receipt"]
        validated_receipt = producer.result["worker_validation_receipt"]
        assert prepared_receipt["phase"] == "PREPARED"
        assert validated_receipt["phase"] == "VALIDATED"
        assert validated_receipt["sha256"] == result["sqlite_receipt"]["sha256"]
        assert validated_receipt["records_summary"]["matches"] == 1
        assert validated_receipt["integrity_attested_before_sql"] is True
        copy_owner = copy_calls[0]["response"][0]
        assert prepared_receipt["worker_pid"] == copy_owner.process.pid
        assert validated_receipt["worker_pid"] == copy_owner.validation_worker.process.pid
        assert validated_receipt["worker_pid"] != prepared_receipt["worker_pid"]
        assert copy_owner.process.poll() == 0
        for worker_receipt in (prepared_receipt, validated_receipt):
            assert worker_receipt["capture_id"] == captured.capture_id
            assert worker_receipt["operation_id"] == OPERATION
            assert worker_receipt["proposal_sha256"] == PROPOSAL
            assert worker_receipt["deadline"] == deadline
            assert worker_receipt["source_binding"] == "ISOLATED_WORKER_CONNECTION_FD_V1"
            assert worker_receipt["sqlite_backup_calls"] == 1
            assert worker_receipt["source_attested_before_sql"] is True
            assert worker_receipt["destination_attested_before_sql"] is True
            assert worker_receipt["source_connection_retained_through_backup"] is True
            assert worker_receipt["source_connections_closed"] is True
            assert worker_receipt["snapshot_writers_closed"] is True
            assert worker_receipt["hostile_wal_namespace_certified"] is False
    assert events == ["before", "prepare", "after", "validate"]
    assert sum(kind == "worker_validate" for kind, _work, _order in guarded_work) == 1
    assert any(kind == "hash" for kind, _work, _order in guarded_work)
    assert all("after" in order for _kind, _work, order in guarded_work)
    assert len(copy_calls) == 1
    proof = {
        "schema": "OWNED_G3_SAME_CAPTURE_PROOF_V1",
        "phase_order": events,
        "sqlite_sha256": result["sqlite_receipt"]["sha256"],
        "archive_sha256": result["archive_sha256"],
        "manifest_sha256": result["manifest_sha256"],
        "capture_worker_invocations": len(copy_calls),
        "sqlite_backup_calls": prepared_receipt["sqlite_backup_calls"],
        "opaque_bracket_closed": result["opaque_bracket_closed"],
        "same_prepared_sqlite_capture_verified": result["same_prepared_sqlite_capture_verified"],
        "source_binding": prepared_receipt["source_binding"],
        "source_attested_before_sql": prepared_receipt["source_attested_before_sql"],
        "destination_attested_before_sql": prepared_receipt["destination_attested_before_sql"],
        "source_connection_retained_through_backup": prepared_receipt["source_connection_retained_through_backup"],
        "source_connections_closed": prepared_receipt["source_connections_closed"],
        "snapshot_writers_closed": prepared_receipt["snapshot_writers_closed"],
        "integrity_attested_before_sql": validated_receipt["integrity_attested_before_sql"],
        "fresh_validation_worker": validated_receipt["worker_pid"] != prepared_receipt["worker_pid"],
        "hostile_wal_namespace_certified": prepared_receipt["hostile_wal_namespace_certified"],
        "continuous_cross_store_consistency_certified": result["continuous_cross_store_consistency_certified"],
        "production_data_touched": False,
        "full_application_recovery_certified": result["full_application_recovery_certified"],
    }
    with capsys.disabled():
        print(json.dumps(proof, sort_keys=True, separators=(",", ":")), flush=True)


@native_sqlite
@pytest.mark.parametrize("journal_mode", ["DELETE", "WAL"])
def test_native_producer_validates_original_capture_when_source_changes_later(
        owned, journal_mode, copy_calls):
    deadline = time.monotonic() + 60.0
    # Keep a WAL writer alive when selected, so committed WAL-visible data must
    # be included by the actual snapshot helper.
    with closing(sqlite3.connect(owned.source)) as writer:
        assert writer.execute("PRAGMA journal_mode=" + journal_mode).fetchone()[0].upper() == journal_mode
        writer.execute("INSERT INTO owned_rows(value) VALUES ('wal-visible-or-delete')")
        writer.commit()
        with _producer(owned) as producer:
            captured = producer.prepare(deadline)
            identity = captured.snapshot_identity
            assert _rows(_captured_path(producer)) == [("captured-before",), ("wal-visible-or-delete",)]
            writer.execute("INSERT INTO owned_rows(value) VALUES ('source-after-capture')")
            writer.commit()
            final = producer.validate(captured, deadline)
            published = producer.publication / producer.result["backup_file"]
            assert final.prepared is captured
            assert (published.stat().st_dev, published.stat().st_ino) == identity[:2]
            assert _rows(published) == [("captured-before",), ("wal-visible-or-delete",)]
            assert _rows(owned.source)[-1] == ("source-after-capture",)
            assert final.receipt.sha256 == hashlib.sha256(published.read_bytes()).hexdigest()
            with pytest.raises(prepared_sqlite.PreparedSnapshotError, match="SECOND_SQLITE_CAPTURE_DENIED"):
                producer.prepare(deadline)
            with pytest.raises(prepared_sqlite.PreparedSnapshotError, match="FOREIGN_OR_STALE"):
                producer.validate(captured, deadline)
    assert len(copy_calls) == 1


@native_sqlite
def test_opaque_mutation_during_prepare_preserves_capture_without_validator(
        owned, monkeypatch, copy_calls):
    calls = []
    with _producer(owned) as producer:
        def prepare(cap):
            captured = producer.prepare(cap)
            owned.history.write_bytes(b"changed-during-capture\n")
            return captured

        def validate(*args):
            calls.append(args)
            raise AssertionError("validator must not run on an unequal bracket")

        result = _capture(owned, producer, prepare=prepare, validate=validate)
        preserved = _captured_path(producer)
        assert result["ok"] is False
        assert result["code"] == "STATE_CHANGED_ACROSS_SQLITE_INTERVAL"
        assert result["sqlite_receipt"] is None
        assert calls == []
        assert preserved.is_file()
        assert _rows(preserved) == [("captured-before",)]
        assert producer.result["sqlite_disposition"] == "CAPTURED_UNVALIDATED_PRESERVED_DO_NOT_RETRY"
        _assert_no_state_or_sqlite_publication(owned)
    assert preserved.is_file()
    assert len(copy_calls) == 1


@native_sqlite
def test_validation_latency_and_later_state_mutation_do_not_certify_quiescence(
        owned, monkeypatch, copy_calls):
    clock = [time.monotonic()]
    monkeypatch.setattr(state, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(prepared_sqlite, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    events = []
    _observe_scans(monkeypatch, events)
    original = owned.history.read_bytes()
    deadline = clock[0] + 60.0
    with _producer(owned) as producer:
        def validate(captured, cap):
            assert events == ["before", "after"]
            # Simulate expensive validation after both complete scans. This is
            # beyond a scan's 5-second cap but within the original phase cap.
            clock[0] += 7.0
            owned.history.write_bytes(b"changed-after-bracket\n")
            return producer.validate(captured, cap)

        result = _capture(owned, producer, validate=validate, deadline=deadline)
        assert result["ok"] is True
        assert result["opaque_bracket_closed"] is True
        assert events == ["before", "after"]
        assert result["continuous_cross_store_consistency_certified"] is False
        assert result["full_application_recovery_certified"] is False
        bundle = owned.plan.publication / result["bundle_file"]
        with bundle.open("rb") as stream:
            manifest = state.parse_bundle(
                stream, expected_archive_sha256=result["archive_sha256"],
                expected_manifest_sha256=result["manifest_sha256"],
                expected_sqlite=state.SqliteReceipt(OPERATION, producer.result["sha256"], True),
                deadline=deadline, expected_layout_id=LAYOUT,
                expected_proposal_sha256=PROPOSAL, expected_scope_roles=("ce", "legacy_runtime"),
                expected_profile_id=PROFILE,
            )
        history = next(entry for entry in manifest["entries"] if entry["relative"] == "history.bin")
        assert history["sha256"] == hashlib.sha256(original).hexdigest()
        assert history["sha256"] != hashlib.sha256(owned.history.read_bytes()).hexdigest()
        assert manifest["continuous_cross_store_consistency_certified"] is False
    assert len(copy_calls) == 1


@native_sqlite
def test_deadline_expiry_in_validator_preserves_original_and_never_recaptures(
        owned, monkeypatch, copy_calls):
    clock = [time.monotonic()]
    monkeypatch.setattr(state, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(prepared_sqlite, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    deadline = clock[0] + 60.0
    validated = []
    with _producer(owned) as producer:
        def validate(captured, cap):
            validated.append(captured)
            clock[0] = deadline
            return producer.validate(captured, cap)

        result = _capture(owned, producer, validate=validate, deadline=deadline)
        preserved = _captured_path(producer)
        assert result["ok"] is False
        assert result["opaque_bracket_closed"] is True
        assert result["sqlite_receipt"] is None
        assert len(validated) == 1
        assert producer.result["ok"] is False
        assert producer.result["backup_created"] is False
        assert preserved.is_file()
        _assert_no_state_or_sqlite_publication(owned)
    assert preserved.is_file()
    assert len(copy_calls) == 1


@native_sqlite
def test_integrity_failure_after_bracket_preserves_snapshot_and_blocks_publication(
        owned, monkeypatch, copy_calls):
    events, validation_dispatches = [], []
    _observe_scans(monkeypatch, events)

    def failed_integrity(owner):
        assert events == ["before", "after"]
        validation_dispatches.append(owner)
        raise prepared_sqlite.PreparedSnapshotError("CAPTURE_INTEGRITY_FAILED")

    monkeypatch.setattr(prepared_sqlite, "_validate_capture_worker", failed_integrity)
    with _producer(owned) as producer:
        result = _capture(owned, producer)
        preserved = _captured_path(producer)
        assert result["ok"] is False
        assert result["opaque_bracket_closed"] is True
        assert result["sqlite_validator_invoked"] is True
        assert result["sqlite_receipt"] is None
        assert producer.result["code"] == "SQLITE_VALIDATION_NOT_VERIFIED"
        assert len(validation_dispatches) == 1
        assert _rows(preserved) == [("captured-before",)]
        _assert_no_state_or_sqlite_publication(owned)
    assert preserved.is_file()
    assert len(copy_calls) == 1


@native_sqlite
@pytest.mark.parametrize("change", ["clone", "operation", "proposal", "capture", "producer"])
def test_native_producer_rejects_foreign_or_equal_cloned_capability(owned, change, copy_calls):
    deadline = time.monotonic() + 60.0
    with _producer(owned) as producer:
        captured = producer.prepare(deadline)
        changes = {
            "clone": {}, "operation": {"operation_id": "FOREIGN_OPERATION"},
            "proposal": {"proposal_sha256": "b" * 64},
            "capture": {"capture_id": "b" * 32}, "producer": {"producer_id": "b" * 32},
        }
        foreign = replace(captured, **changes[change])
        assert foreign is not captured
        with pytest.raises(prepared_sqlite.PreparedSnapshotError, match="FOREIGN_OR_STALE"):
            producer.validate(foreign, deadline)
        assert producer.result["backup_created"] is False
        assert _captured_path(producer).is_file()
        _assert_no_state_or_sqlite_publication(owned)
    assert len(copy_calls) == 1


@native_sqlite
def test_engine_rejects_equal_cloned_capability_in_final_receipt(owned, copy_calls):
    with _producer(owned) as producer:
        def validate(captured, _cap):
            digest = state._hash_fd(captured.snapshot_fd, time.monotonic() + 30.0,
                                    prepared_sqlite.MAX_SNAPSHOT_BYTES)
            return state.ValidatedSqliteCapture(
                replace(captured), state.SqliteReceipt(OPERATION, digest, True),
                state._capture_identity(os.fstat(captured.snapshot_fd)),
                producer.publication, producer._pfd, "database_owned.db",
            )

        result = _capture(owned, producer, validate=validate)
        assert result["ok"] is False
        assert result["code"] == "FOREIGN_PREPARED_SQLITE_CAPTURE"
        assert result["sqlite_receipt"] is None
        assert _captured_path(producer).is_file()
        _assert_no_state_or_sqlite_publication(owned)
    assert len(copy_calls) == 1


@native_sqlite
@pytest.mark.parametrize("change", ["bytes", "path", "fd"])
def test_changed_or_substituted_capture_fails_without_publication(owned, change, copy_calls):
    deadline = time.monotonic() + 60.0
    with _producer(owned) as producer:
        captured = producer.prepare(deadline)
        captured_path = _captured_path(producer)
        retained = captured_path
        if change == "bytes":
            with captured_path.open("r+b") as handle:
                handle.seek(128)
                handle.write(b"owned-modification")
                handle.flush()
                os.fsync(handle.fileno())
        elif change == "path":
            retained = captured_path.with_name("captured.saved")
            captured_path.rename(retained)
            captured_path.write_bytes(retained.read_bytes())
            captured_path.chmod(0o600)
        else:
            decoy = producer.publication / "decoy.db"
            decoy.write_bytes(captured_path.read_bytes())
            decoy.chmod(0o600)
            foreign_fd = os.open(decoy, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.dup2(foreign_fd, captured.snapshot_fd)
            finally:
                os.close(foreign_fd)
        with pytest.raises((prepared_sqlite.PreparedSnapshotError, state.StateError)):
            producer.validate(captured, deadline)
        assert retained.is_file()
        assert producer.result["backup_created"] is False
        _assert_no_state_or_sqlite_publication(owned)
    assert retained.is_file()
    assert len(copy_calls) == 1


@native_sqlite
def test_wrong_final_digest_preserves_published_sqlite_but_never_publishes_state(owned, copy_calls):
    with _producer(owned) as producer:
        def validate(captured, cap):
            final = producer.validate(captured, cap)
            return replace(final, receipt=state.SqliteReceipt(OPERATION, "0" * 64, True))

        result = _capture(owned, producer, validate=validate)
        assert result["ok"] is False
        assert result["code"] == "PREPARED_SQLITE_HASH_MISMATCH"
        assert result["sqlite_receipt"] is None
        assert producer.result["backup_created"] is True
        published = producer.publication / producer.result["backup_file"]
        assert _rows(published) == [("captured-before",)]
        assert list(owned.plan.publication.glob("state-*.tar")) == []
    assert published.is_file()
    assert len(copy_calls) == 1


@native_sqlite
@pytest.mark.parametrize("change", ["name", "directory"])
def test_final_publication_substitution_is_rejected_before_state_publication(owned, change, copy_calls):
    preserved = []
    with _producer(owned) as producer:
        def validate(captured, cap):
            final = producer.validate(captured, cap)
            published = final.publication / final.backup_file
            original_bytes = published.read_bytes()
            if change == "name":
                retained = published.with_name("captured.saved.db")
                published.rename(retained)
                # Same bytes/digest, a different inode at the published name.
                published.write_bytes(original_bytes)
                published.chmod(0o600)
            else:
                moved_directory = final.publication.with_name("backups.saved")
                final.publication.rename(moved_directory)
                final.publication.mkdir(mode=0o700)
                owned.plan.publication.mkdir(mode=0o700)
                retained = moved_directory / final.backup_file
            assert (retained.stat().st_dev, retained.stat().st_ino) == captured.snapshot_identity[:2]
            preserved.append((retained, original_bytes, captured.snapshot_identity[:2]))
            return final

        result = _capture(owned, producer, validate=validate)
        assert result["ok"] is False
        assert result["state_published"] is False
        assert result["sqlite_receipt"] is None
        assert producer.result["backup_created"] is True
        assert len(preserved) == 1
        retained, original_bytes, original_inode = preserved[0]
        assert retained.read_bytes() == original_bytes
        assert (retained.stat().st_dev, retained.stat().st_ino) == original_inode
        assert _rows(retained) == [("captured-before",)]
        assert list(owned.plan.publication.parent.parent.rglob("state-*.tar")) == []
    assert retained.is_file()
    assert len(copy_calls) == 1


@native_sqlite
@pytest.mark.parametrize("collision_suffix", [".db", ".json"])
def test_no_replace_publication_preserves_existing_and_captured_artifacts(
        owned, monkeypatch, collision_suffix, copy_calls):
    monkeypatch.setattr(prepared_sqlite, "uuid", SimpleNamespace(
        uuid4=lambda: SimpleNamespace(hex="b" * 32)))
    collision = owned.plan.publication.parent / ("database_" + "b" * 32 + collision_suffix)
    collision.write_bytes(b"existing-owned-artifact-must-survive")
    deadline = time.monotonic() + 60.0
    with _producer(owned) as producer:
        captured = producer.prepare(deadline)
        with pytest.raises(FileExistsError):
            producer.validate(captured, deadline)
        assert collision.read_bytes() == b"existing-owned-artifact-must-survive"
        assert _captured_path(producer).is_file()
        assert _rows(_captured_path(producer)) == [("captured-before",)]
        assert producer.result["backup_created"] is False
        assert list(owned.plan.publication.glob("state-*.tar")) == []
    assert len(copy_calls) == 1


@native_sqlite
def test_explicit_adapter_carries_profile_and_preserves_real_same_capture(owned, copy_calls):
    deadline = time.monotonic() + 60.0
    with _producer(owned) as producer:
        handoff = adapter.capture_prepared_with_state(
            plan=owned.plan, source=owned.source, producer=producer, deadline=deadline)
        assert handoff.ok is True
        assert handoff.bundle.profile_id == PROFILE
        assert handoff.bundle.layout_id == LAYOUT
        assert handoff.bundle.sqlite.sha256 == producer.result["sha256"]
        assert handoff.bundle.backup_name == producer.result["backup_file"]
        public = adapter.public_state_receipt(handoff)
        assert public["profile_id"] == PROFILE
        assert public["same_prepared_sqlite_capture_verified"] is True
        assert public["continuous_cross_store_consistency_certified"] is False
        assert public["full_application_recovery_certified"] is False
        assert producer.result["production_source_connection_bound"] is True
    assert len(copy_calls) == 1


@pytest.mark.parametrize("profile,layout", [(None, None), (None, LAYOUT), (PROFILE, LAYOUT)])
def test_restore_handoff_forwards_exact_profile_without_changing_legacy_defaults(
        tmp_path, monkeypatch, profile, layout):
    plan, _source = _plan(tmp_path, profile=profile, layout=layout)
    receipt = state.SqliteReceipt(OPERATION, "b" * 64, True)
    bundle = adapter.BoundStateBundle(
        OPERATION, PROPOSAL, plan.publication / ("state-" + "a" * 32 + ".tar"),
        "c" * 64, "d" * 64, receipt, "database_owned.db", ("ce", "legacy_runtime"),
        state.Limits(), layout, profile,
    )
    observed = []

    def restore(**kwargs):
        observed.append(kwargs)
        return {"ok": True, "state_ready_before_app": True,
                "layout_id": layout, "scope_roles": ["ce", "legacy_runtime"]}

    monkeypatch.setattr(state, "restore_state", restore)
    workspace = tmp_path / ".isolated_restore_327_owned"
    info = SimpleNamespace(**{name: 1 for name in state._CAPTURE_IDENTITY_FIELDS})
    result = adapter.restore_before_app(
        bundle, source=workspace / "source", restored_database=workspace / "restoration-test.db",
        workspace=workspace, database_info=info, deadline=time.monotonic() + 60.0,
    )
    assert result["ok"] is True
    assert len(observed) == 1
    assert observed[0]["expected_profile_id"] == profile
    assert observed[0]["expected_layout_id"] == layout
    assert observed[0]["expected_sqlite"] is receipt


def test_legacy_adapter_uses_once_only_callback_and_original_absolute_deadline(tmp_path, monkeypatch):
    plan, source = _plan(tmp_path, profile=None, layout=None)
    deadline = time.monotonic() + 60.0
    snapshots, captures = [], []
    sqlite_result = {"ok": True, "backup_created": True, "backup_file": "database_owned.db",
                     "sha256": "b" * 64}

    def snapshot(**kwargs):
        snapshots.append(kwargs)
        return sqlite_result

    def capture(**kwargs):
        captures.append(kwargs)
        final_receipt = kwargs["sqlite_snapshot_callback"](kwargs["deadline"])
        return {"ok": True, "state_published": True,
                "bundle_file": "state-" + "a" * 32 + ".tar",
                "archive_sha256": "c" * 64, "manifest_sha256": "d" * 64,
                "sqlite_receipt": state._sqlite(final_receipt)}

    monkeypatch.setattr(state, "capture_state", capture)
    handoff = adapter.capture_with_state(plan=plan, source=source, create_snapshot=snapshot,
                                         deadline=deadline)
    assert handoff.ok is True
    assert snapshots == [{"absolute_deadline": deadline}]
    assert len(captures) == 1
    assert captures[0]["profile_id"] is None
    assert "sqlite_prepared_callbacks" not in captures[0]
    assert handoff.bundle.profile_id is None


@native_state
@pytest.mark.parametrize("layout,schema", [(None, "OPAQUE_STATE_BUNDLE_V1"),
                                            (LAYOUT, "OPAQUE_STATE_BUNDLE_V2")])
def test_legacy_engine_callback_and_manifest_versions_remain_available(owned, layout, schema):
    calls = []
    deadline = time.monotonic() + 60.0
    receipt = state.SqliteReceipt(OPERATION, "b" * 64, True)

    def callback(cap):
        calls.append(cap)
        return receipt

    result = state.capture_state(
        scopes=owned.plan.scopes, authorization=owned.plan.authorization,
        publication=owned.plan.publication, deadline=deadline,
        sqlite_snapshot_callback=callback,
        layout_binding=None if layout is None else state.StateLayoutBinding(layout, OPERATION, PROPOSAL),
    )
    assert result["ok"] is True
    assert calls == [deadline]
    with (owned.plan.publication / result["bundle_file"]).open("rb") as stream:
        manifest = state.parse_bundle(
            stream, expected_archive_sha256=result["archive_sha256"],
            expected_manifest_sha256=result["manifest_sha256"], expected_sqlite=receipt,
            deadline=deadline, expected_layout_id=layout,
            expected_proposal_sha256=PROPOSAL if layout else None,
            expected_scope_roles=("ce", "legacy_runtime") if layout else None,
        )
    assert manifest["schema"] == schema
    assert manifest["limits"] == {"entries": 400, "depth": 6, "bytes": 16 * 1024 * 1024, "seconds": 5.0}
    assert manifest["continuous_cross_store_consistency_certified"] is False


def test_prepared_adapter_is_opt_in_and_rejects_legacy_plan_before_any_capture(tmp_path):
    plan, source = _plan(tmp_path, profile=None, layout=LAYOUT)
    with pytest.raises(adapter.HandoffError, match="PREPARED_STATE_PROFILE_REQUIRED"):
        adapter.capture_prepared_with_state(plan=plan, source=source, producer=object(),
                                             deadline=time.monotonic() + 60.0)


def test_unsupported_prepared_snapshot_method_is_rejected_before_capture(tmp_path, monkeypatch, copy_calls):
    plan, source = _plan(tmp_path)
    sqlite_opens = []

    def forbidden_open(*args, **kwargs):
        sqlite_opens.append((args, kwargs))
        raise AssertionError("unsupported method must not open SQLite")

    monkeypatch.setattr(prepared_sqlite, "_run_capture_worker", forbidden_open)
    with pytest.raises(prepared_sqlite.PreparedSnapshotError, match="UNSUPPORTED_PREPARED_SQLITE_METHOD"):
        prepared_sqlite.SqliteSnapshotProducer(
            source=source, publication=plan.publication.parent,
            operation_id=OPERATION, proposal_sha256=PROPOSAL,
            snapshot_method="vacuum_into",
        )
    assert sqlite_opens == []
    assert copy_calls == []
    assert not source.exists()
    assert not plan.publication.parent.exists()


def _descriptor_info(inode):
    return SimpleNamespace(st_dev=13, st_ino=inode, st_mode=stat.S_IFREG | 0o600,
                           st_nlink=1, st_uid=1000, st_gid=1000, st_size=4096,
                           st_mtime_ns=11, st_ctime_ns=12)


@pytest.mark.skipif(os.name != "posix", reason="worker module requires Unix resource limits")
def test_worker_attests_the_one_actual_new_descriptor_with_mocked_fd_table(monkeypatch):
    from tools import recovery_sqlite_capture_worker as worker
    descriptors = {20: _descriptor_info(37), 21: _descriptor_info(37)}
    monkeypatch.setattr(worker, "os", SimpleNamespace(
        fstat=lambda fd: descriptors[fd], O_ACCMODE=os.O_ACCMODE))
    monkeypatch.setattr(worker, "fcntl", SimpleNamespace(F_GETFL=3, fcntl=lambda *_args: os.O_RDONLY))
    before = {20: worker._origin(descriptors[20]) + (os.O_RDONLY,)}
    after = {**before, 21: worker._origin(descriptors[21]) + (os.O_RDONLY,)}
    assert worker._attest_new_connection(before, 20, table=after) == 21


@pytest.mark.skipif(os.name != "posix", reason="worker module requires Unix resource limits")
@pytest.mark.parametrize("change", ["restored_name_substitution", "ambiguous_new_descriptors",
                                    "baseline_changed", "no_new_descriptor", "access_mode_mismatch"])
def test_worker_rejects_substitution_and_ambiguous_source_descriptors_without_sql(monkeypatch, change):
    from tools import recovery_sqlite_capture_worker as worker
    expected = _descriptor_info(37)
    foreign = _descriptor_info(999)
    descriptors = {20: expected, 21: expected, 22: expected}
    # The authorized basename already looks restored. The new SQLite FD must
    # still bind to the authorized inode, independent of pathname observations.
    monkeypatch.setattr(worker, "os", SimpleNamespace(
        fstat=lambda fd: descriptors[fd], stat=lambda *_args, **_kwargs: expected,
        O_ACCMODE=os.O_ACCMODE))
    access = {20: os.O_RDONLY, 21: os.O_RDONLY, 22: os.O_RDONLY}
    monkeypatch.setattr(worker, "fcntl", SimpleNamespace(F_GETFL=3, fcntl=lambda fd, _cmd: access[fd]))
    before = {20: worker._origin(expected) + (os.O_RDONLY,)}
    after = {**before, 21: worker._origin(expected) + (os.O_RDONLY,)}
    if change == "restored_name_substitution":
        descriptors[21] = foreign
        after[21] = worker._origin(foreign) + (os.O_RDONLY,)
        assert worker._origin(worker.os.stat("owned.db")) == worker._origin(expected)
    elif change == "ambiguous_new_descriptors":
        after[22] = worker._origin(expected) + (os.O_RDONLY,)
    elif change == "baseline_changed":
        after[20] = worker._origin(foreign) + (os.O_RDONLY,)
    elif change == "access_mode_mismatch":
        access[21] = os.O_RDWR
        after[21] = worker._origin(expected) + (os.O_RDWR,)
    else:
        after = dict(before)
    with pytest.raises(worker.WorkerError, match="SQLITE_CONNECTION_FD_ATTESTATION_FAILED"):
        worker._attest_new_connection(before, 20, table=after)


@pytest.mark.skipif(os.name != "posix", reason="worker module requires Unix resource limits")
@pytest.mark.parametrize("reject", [False, True])
def test_worker_connection_attestation_precedes_the_first_sql_statement(monkeypatch, reject):
    from tools import recovery_sqlite_capture_worker as worker
    events = []

    class Connection:
        def set_progress_handler(self, *_args):
            events.append("progress_handler")

        def execute(self, _sql):
            assert "attested" in events
            events.append("sql")

        def close(self):
            events.append("closed")

    connection = Connection()

    legacy_control = object()

    def connect(database, **kwargs):
        assert database.endswith("?mode=ro&cache=private&vfs=unix")
        assert kwargs == {"uri": True, "timeout": 0.05, "isolation_level": None,
                          "factory": Connection, "cached_statements": 0,
                          "autocommit": legacy_control}
        events.append("connect")
        return connection

    def attest(*_args, **_kwargs):
        events.append("attestation_started")
        if reject:
            raise worker.WorkerError("SQLITE_CONNECTION_FD_ATTESTATION_FAILED")
        events.append("attested")
        return 21

    monkeypatch.setattr(worker, "_time", lambda *_args: None)
    monkeypatch.setattr(worker, "_named_origin", lambda *_args: None)
    monkeypatch.setattr(worker, "_fd_table", lambda: {
        20: (13, 37, stat.S_IFREG | 0o600, 1, 1000, 1000, os.O_RDONLY)})
    monkeypatch.setattr(worker, "_attest_new_connection", attest)
    monkeypatch.setattr(worker, "_same_connection", lambda *_args: None)
    monkeypatch.setattr(worker, "fcntl", SimpleNamespace(
        F_GETFL=3, fcntl=lambda *_args: os.O_RDONLY))
    monkeypatch.setattr(worker, "sqlite3", SimpleNamespace(
        connect=connect, Connection=Connection, LEGACY_TRANSACTION_CONTROL=legacy_control))
    if reject:
        with pytest.raises(worker.WorkerError, match="SQLITE_CONNECTION_FD_ATTESTATION_FAILED"):
            worker._open_connection(10, "source.db", 20, readonly=True, deadline=123.0)
        assert events == ["connect", "attestation_started", "closed"]
    else:
        opened, actual = worker._open_connection(10, "source.db", 20, readonly=True, deadline=123.0)
        assert opened is connection and actual == 21
        assert events == ["connect", "attestation_started", "attested", "progress_handler", "sql"]


def test_profile_caps_and_legacy_limits_remain_closed(tmp_path):
    plan, _source = _plan(tmp_path)
    assert plan.profile_id == PROFILE
    policy = state._policy(PROFILE, state.Limits())
    assert (policy.entries, policy.depth, policy.bytes, policy.seconds, policy.manifest_bytes) == (
        32768, 6, 96 * 1024 * 1024, 5.0, 32 * 1024 * 1024,
    )
    assert state.Limits() == state.Limits(400, 6, 16 * 1024 * 1024, 5.0)
    with pytest.raises(state.StateError, match="INVALID_LIMIT"):
        state.Limits(entries=401)
    with pytest.raises(state.StateError, match="INVALID_BUDGET_PROFILE"):
        _plan(tmp_path, profile="UNREVIEWED_PROFILE")


@native_sqlite
def test_parent_prepare_preserves_live_caller_wal_snapshot_without_opening_source(
        owned, monkeypatch, copy_calls, capsys):
    import fcntl
    import json
    import subprocess
    import sys

    writer_script = (
        "import json,sqlite3,sys\n"
        "from contextlib import closing\n"
        "payload=json.loads(sys.stdin.buffer.read(8193))\n"
        "with closing(sqlite3.connect(payload['database'], timeout=5.0)) as connection:\n"
        "    connection.execute('PRAGMA busy_timeout=5000')\n"
        "    connection.execute('INSERT INTO owned_rows(value) VALUES (?)', (payload['value'],))\n"
        "    connection.commit()\n"
        "    sys.stdout.write(json.dumps({'ok':True,'committed_rows':1})+'\\n')\n"
    )
    forbidden_parent_opens, forbidden_parent_closes, writer_commits = [], [], []
    committed_value = "independent-writer-during-prepare"
    with closing(sqlite3.connect(owned.source, timeout=5.0)) as caller:
        assert caller.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
        caller.execute("BEGIN")
        original_rows = caller.execute("SELECT value FROM owned_rows ORDER BY id").fetchall()
        assert original_rows == [("captured-before",)]
        assert caller.in_transaction is True
        source_info = owned.source.stat()
        source_origin = (source_info.st_dev, source_info.st_ino)

        def caller_source_descriptors():
            descriptors = {}
            for name in os.listdir("/proc/self/fd"):
                if not name.isdecimal():
                    continue
                descriptor = int(name)
                try:
                    info = os.fstat(descriptor)
                except OSError:
                    continue
                if (info.st_dev, info.st_ino) == source_origin:
                    descriptors[descriptor] = (
                        info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
                        info.st_uid, info.st_gid,
                        fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_ACCMODE,
                    )
            return descriptors

        original_descriptors = caller_source_descriptors()
        assert original_descriptors
        original_open = prepared_sqlite.os.open
        original_close = prepared_sqlite.os.close

        def guarded_parent_open(path, flags, mode=0o777, *, dir_fd=None):
            try:
                info = os.stat(path, dir_fd=dir_fd, follow_symlinks=False)
            except (OSError, TypeError, ValueError):
                info = None
            if info is not None and (info.st_dev, info.st_ino) == source_origin:
                forbidden_parent_opens.append((flags, dir_fd))
                raise AssertionError("parent producer must never open the live caller's main database inode")
            return original_open(path, flags, mode, dir_fd=dir_fd)

        def guarded_parent_close(descriptor):
            try:
                info = os.fstat(descriptor)
            except OSError:
                info = None
            if info is not None and (info.st_dev, info.st_ino) == source_origin:
                forbidden_parent_closes.append(descriptor)
                raise AssertionError("parent producer must never close the live caller's main database inode")
            return original_close(descriptor)

        monkeypatch.setattr(prepared_sqlite.os, "open", guarded_parent_open)
        monkeypatch.setattr(prepared_sqlite.os, "close", guarded_parent_close)
        # The wrapper implements the same native dir_fd API. Keep the strong
        # primitive gate honest instead of bypassing state._native().
        monkeypatch.setattr(prepared_sqlite.os, "supports_dir_fd",
                            prepared_sqlite.os.supports_dir_fd | {guarded_parent_open})
        real_capture_worker = prepared_sqlite._run_capture_worker

        def commit_then_capture(**kwargs):
            assert caller.in_transaction is True
            assert caller.execute("SELECT value FROM owned_rows ORDER BY id").fetchall() == original_rows
            writer = subprocess.run(
                [sys.executable, "-I", "-S", "-u", "-c", writer_script],
                input=json.dumps({"database": str(owned.source), "value": committed_value}).encode("utf-8"),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10.0,
                env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}, check=False,
            )
            assert writer.returncode == 0, writer.stderr.decode("utf-8", errors="replace")
            assert json.loads(writer.stdout) == {"ok": True, "committed_rows": 1}
            writer_commits.append(1)
            # The writer commits in another process while this parent caller
            # keeps the already-materialized WAL read snapshot.
            assert caller.in_transaction is True
            assert caller.execute("SELECT value FROM owned_rows ORDER BY id").fetchall() == original_rows
            assert caller_source_descriptors() == original_descriptors
            return real_capture_worker(**kwargs)

        monkeypatch.setattr(prepared_sqlite, "_run_capture_worker", commit_then_capture)
        deadline = time.monotonic() + 60.0
        with _producer(owned) as producer:
            captured = producer.prepare(deadline)
            assert forbidden_parent_opens == []
            assert forbidden_parent_closes == []
            assert writer_commits == [1]
            assert len(copy_calls) == 1
            assert caller.in_transaction is True
            assert caller.execute("SELECT value FROM owned_rows ORDER BY id").fetchall() == original_rows
            assert caller_source_descriptors() == original_descriptors
            assert _rows(_captured_path(producer)) == original_rows + [(committed_value,)]
            final = producer.validate(captured, deadline)
            published = producer.publication / producer.result["backup_file"]
            assert final.prepared is captured
            assert _rows(published) == original_rows + [(committed_value,)]
            assert producer.result["production_source_connection_bound"] is True
            assert producer.result["worker_prepared_receipt"]["sqlite_backup_calls"] == 1
            assert forbidden_parent_opens == []
            assert forbidden_parent_closes == []
            assert caller.in_transaction is True
            assert caller.execute("SELECT value FROM owned_rows ORDER BY id").fetchall() == original_rows
            assert caller_source_descriptors() == original_descriptors
        caller.rollback()
        assert caller.in_transaction is False
        assert caller.execute("SELECT value FROM owned_rows ORDER BY id").fetchall() == original_rows + [(committed_value,)]
    assert forbidden_parent_opens == []
    assert forbidden_parent_closes == []
    assert writer_commits == [1]
    assert len(copy_calls) == 1
    proof = {
        "schema": "OWNED_G3_CALLER_WAL_PROOF_V1",
        "parent_source_opens": len(forbidden_parent_opens),
        "parent_source_closes": len(forbidden_parent_closes),
        "independent_writer_commits": len(writer_commits),
        "capture_worker_invocations": len(copy_calls),
        "sqlite_backup_calls": producer.result["worker_prepared_receipt"]["sqlite_backup_calls"],
        "sqlite_sha256": producer.result["sha256"],
        "source_binding": producer.result["source_binding"],
        "production_source_connection_bound": producer.result["production_source_connection_bound"],
        "caller_snapshot_control_assertions_completed": True,
        "production_data_touched": False,
        "full_application_recovery_certified": False,
    }
    with capsys.disabled():
        print(json.dumps(proof, sort_keys=True, separators=(",", ":")), flush=True)
