"""Owned multi-SQLite capability tests; no real capture or recovery claim."""
from contextlib import closing
from dataclasses import FrozenInstanceError, replace
import os
from pathlib import Path
import sqlite3
import time

import pytest
from tools import recovery_sqlite_set as sets
from tools.recovery_sqlite_prepare import MAX_SNAPSHOT_BYTES

_NATIVE = (os.name == "posix" and Path("/proc/self/fd").is_dir()
           and os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW"))
native = pytest.mark.skipif(not _NATIVE, reason="native confined SQLite workers required")


def _plan(tmp_path, *, sources=None, **options):
    if sources is None:
        sources = (
            sets.SqliteSource("principal", tmp_path / "main.db", 1024 * 1024),
            sets.SqliteSource("aux_app", tmp_path / "app.db", 1024 * 1024))
    return sets.SqliteSetPlan(
        "OWNED_SET_CAPTURE", "b" * 64, sources, tmp_path / "publication", **options)


@pytest.mark.parametrize("quota", [None, True, False, 0, -1, 1.0, MAX_SNAPSHOT_BYTES + 1])
def test_invalid_member_quota_is_denied_before_io(tmp_path, quota):
    with pytest.raises(sets.SqliteSetError, match="INVALID_SQLITE_SET_SOURCE"):
        sets.SqliteSource("principal", tmp_path / "main.db", quota)


def test_aggregate_quotas_cannot_multiply_original_ceiling(tmp_path):
    sources = (
        sets.SqliteSource("principal", tmp_path / "main.db", MAX_SNAPSHOT_BYTES),
        sets.SqliteSource("aux_app", tmp_path / "app.db", 1))
    with pytest.raises(sets.SqliteSetError, match="INVALID_SQLITE_SET_PLAN"):
        _plan(tmp_path, sources=sources)


@pytest.mark.parametrize("case", ["no_primary", "duplicate_id", "duplicate_path",
                                  "unsorted_auxiliary", "too_many"])
def test_set_requires_complete_unambiguous_canonical_members(tmp_path, case):
    main = sets.SqliteSource("principal", tmp_path / "main.db", 1024)
    aux = sets.SqliteSource("aux_app", tmp_path / "app.db", 1024)
    sources = {
        "no_primary": (aux, main),
        "duplicate_id": (main, sets.SqliteSource("principal", tmp_path / "other.db", 1024)),
        "duplicate_path": (main, sets.SqliteSource("aux_app", main.source, 1024)),
        "unsorted_auxiliary": (main, sets.SqliteSource("aux_z", tmp_path / "z.db", 1024), aux),
        "too_many": (main,) + tuple(sets.SqliteSource("aux_" + str(n), tmp_path / (str(n)+".db"), 1024)
                                    for n in range(sets.MAX_DATABASES)),
    }[case]
    with pytest.raises(sets.SqliteSetError, match="INVALID_SQLITE_SET_PLAN"):
        _plan(tmp_path, sources=sources)


@pytest.mark.parametrize("timeout", [True, 0, -1, float("inf"), sets.MAX_PHASE_SECONDS + 1])
def test_set_cannot_add_another_phase_budget(tmp_path, timeout):
    with pytest.raises(sets.SqliteSetError, match="INVALID_SQLITE_SET_PLAN"):
        _plan(tmp_path, snapshot_timeout=timeout)


def test_expired_aggregate_deadline_never_observes_a_source(tmp_path, monkeypatch):
    owned = sets.SqliteSetProducer(_plan(tmp_path))
    def forbidden():
        pytest.fail("expired set reached source metadata")
    monkeypatch.setattr(owned, "_source_origins", forbidden)
    try:
        with pytest.raises(sets.SqliteSetError, match="SQLITE_SET_DEADLINE_EXPIRED"):
            owned.prepare(time.monotonic() - 1)
        with pytest.raises(sets.SqliteSetError, match="SECOND_SQLITE_SET_CAPTURE_DENIED"):
            owned.prepare(time.monotonic() + 15)
    finally:
        owned.close()


def test_plan_is_immutable_and_declares_isolated_restore_names(tmp_path):
    plan = _plan(tmp_path)
    with pytest.raises(FrozenInstanceError):
        plan.sources = ()
    assert [s.restore_relative for s in plan.sources] == [
        "restoration-test.db", "sqlite/aux_app.db"]
    with sets.SqliteSetProducer(plan) as owned:
        assert owned.result["validated_set"] is False
        assert owned.result["full_application_recovery_certified"] is False


def _owned(tmp_path, *, auxiliary_quota=1024 * 1024):
    publication = tmp_path / "publication"
    publication.mkdir(mode=0o700)
    publication.chmod(0o700)
    for name, value in (("main.db", "owned-main"), ("app.db", "owned-auxiliary")):
        with closing(sqlite3.connect(tmp_path / name)) as db:
            db.execute("CREATE TABLE owned_content(value TEXT)")
            db.execute("INSERT INTO owned_content VALUES (?)", (value,))
            db.commit()
    return _plan(tmp_path, sources=(
        sets.SqliteSource("principal", tmp_path / "main.db", 1024 * 1024),
        sets.SqliteSource("aux_app", tmp_path / "app.db", auxiliary_quota)))


@native
def test_two_native_sources_keep_distinct_same_capture_capabilities(tmp_path):
    plan = _owned(tmp_path)
    originals = {s.source_id: s.source.read_bytes() for s in plan.sources}
    deadline = time.monotonic() + 15
    with sets.SqliteSetProducer(plan) as owned:
        prepared = owned.prepare(deadline)
        assert [k for k, _ in prepared.members] == ["principal", "aux_app"]
        assert len({c.snapshot_identity[:2] for _, c in prepared.members}) == 2
        validated = owned.validate(prepared, deadline)
        assert validated.prepared is prepared
        for (label, captured), (validated_label, value) in zip(prepared.members, validated.members):
            assert label == validated_label
            assert value.prepared is captured
            with closing(sqlite3.connect((plan.publication / value.backup_file).as_uri() + "?mode=ro",
                                         uri=True)) as db:
                expected = "owned-main" if label == "principal" else "owned-auxiliary"
                assert db.execute("SELECT value FROM owned_content").fetchall() == [(expected,)]
        assert owned.result["validated_set"] is True
        assert owned.result["all_members_published"] is True
        assert owned.result["continuous_cross_store_consistency_certified"] is False
        assert owned.result["full_application_recovery_certified"] is False
    assert {s.source_id: s.source.read_bytes() for s in plan.sources} == originals


@native
def test_auxiliary_failure_preserves_first_capture_without_retry(tmp_path):
    plan = _owned(tmp_path, auxiliary_quota=1)
    with sets.SqliteSetProducer(plan) as owned:
        with pytest.raises(ValueError):
            owned.prepare(time.monotonic() + 15)
        results = dict(owned.result["members"])
        assert results["principal"]["prepare_completed"] is True
        assert results["principal"]["backup_created"] is False
        assert results["aux_app"]["prepare_completed"] is False
        assert owned.result["validated_set"] is False
        assert not list(plan.publication.glob("database_*"))
        assert len(list(plan.publication.glob(".*/snapshot.partial"))) == 2
        with pytest.raises(sets.SqliteSetError, match="SECOND_SQLITE_SET_CAPTURE_DENIED"):
            owned.prepare(time.monotonic() + 15)


@native
@pytest.mark.parametrize("attack", ["new_capability_wrapper", "new_deadline"])
def test_set_validation_binds_original_capability_and_deadline(tmp_path, attack):
    plan = _owned(tmp_path)
    deadline = time.monotonic() + 15
    with sets.SqliteSetProducer(plan) as owned:
        prepared = owned.prepare(deadline)
        with pytest.raises(sets.SqliteSetError):
            owned.validate(replace(prepared) if attack == "new_capability_wrapper" else prepared,
                           deadline + 1 if attack == "new_deadline" else deadline)
        assert all(not p._validated for _, p in owned._members)
        assert owned.result["validated_set"] is False
        assert not list(plan.publication.glob("database_*"))
        with pytest.raises(sets.SqliteSetError, match="SECOND_SQLITE_SET_VALIDATION_DENIED"):
            owned.validate(prepared, deadline)


@native
def test_late_auxiliary_validation_failure_preserves_published_principal(tmp_path, monkeypatch):
    plan = _owned(tmp_path)
    deadline = time.monotonic() + 15
    with sets.SqliteSetProducer(plan) as owned:
        prepared = owned.prepare(deadline)
        def fail(*args):
            raise sets.SqliteSetError("OWNED_AUXILIARY_FAULT")
        monkeypatch.setattr(owned._members[1][1], "validate", fail)
        with pytest.raises(sets.SqliteSetError, match="OWNED_AUXILIARY_FAULT"):
            owned.validate(prepared, deadline)
        assert dict(owned.result["members"])["principal"]["backup_created"] is True
        assert dict(owned.result["members"])["aux_app"]["backup_created"] is False
        assert owned.result["validated_set"] is False
        assert owned.result["all_members_published"] is False
        assert len(list(plan.publication.glob("database_*.db"))) == 1
        assert list(plan.publication.glob(".*/snapshot.partial"))
    assert len(list(plan.publication.glob("database_*.db"))) == 1
