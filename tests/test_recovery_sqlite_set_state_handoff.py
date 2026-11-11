"""Owned set disposition and cleanup; no real data operations."""
from types import SimpleNamespace
import pytest
from tools import recovery_sqlite_set as sets
from tools import recovery_sqlite_set_state as bridge


def handoff(flags, invoked=True):
    members = tuple((name, dict(zip(("sqlite_capture_attempted", "prepare_completed", "backup_created", "ok"), values)))
                    for name, values in zip(("principal", "aux_app"), flags))
    return bridge.SqliteSetCaptureHandoff({"members": members},
        {"ok": False, "sqlite_callback_invoked": invoked}, None)


@pytest.mark.parametrize("flags,invoked,expected,counts", [
    (((False,False,False,False),)*2, False, "NOT_INVOKED", (0,0,0,0)),
    (((False,False,False,False),)*2, True, "CALLBACK_INVOKED_SQLITE_NOT_ATTESTED_PRESERVE_AND_DO_NOT_RETRY", (0,0,0,0)),
    (((True,False,False,False),(False,False,False,False)), True, "ATTEMPTED_UNKNOWN_PRESERVE_AND_DO_NOT_RETRY", (1,0,0,0)),
    (((True,True,False,False),)*2, True, "CAPTURES_UNVALIDATED_PRESERVE_AND_DO_NOT_RETRY", (2,2,0,0)),
    (((True,True,True,True),(True,True,False,False)), True, "PARTIALLY_PUBLISHED_PRESERVE_AND_DO_NOT_RETRY", (2,2,1,1)),
    (((True,True,True,True),)*2, True, "MEMBERS_PUBLISHED_STATE_UNVERIFIED_PRESERVE", (2,2,2,2)),
])
def test_partial_disposition_requires_actual_member_facts(flags, invoked, expected, counts):
    value = handoff(flags, invoked)
    value.sqlite_result["private_path"] = "PRIVATE_MUST_NOT_ESCAPE"
    result = bridge.public_set_disposition(value)
    assert result["sqlite_set_disposition"] == expected
    assert tuple(result[k] for k in ("attempted_sqlite_members", "prepared_sqlite_members",
        "published_sqlite_members", "verified_sqlite_members")) == counts
    assert "PRIVATE_MUST_NOT_ESCAPE" not in repr(result)
    assert result["full_application_recovery_certified"] is False
    assert result["continuous_cross_store_consistency_certified"] is False
    assert result["recapture_attempted"] is False


@pytest.mark.parametrize("field", ["ok", "sqlite_capture_attempted", "prepare_completed", "backup_created"])
@pytest.mark.parametrize("bad", [None, 0, 1, "true"])
def test_missing_or_coerced_facts_cannot_certify_no_attempt(field, bad):
    value = handoff(((False,False,False,False),)*2)
    value.sqlite_result["members"][0][1][field] = bad
    with pytest.raises(bridge.SqliteSetHandoffError):
        bridge.public_set_disposition(value)


@pytest.mark.parametrize("flags,invoked", [
    (((False,False,True,False),)*2, True),
    (((False,True,False,False),)*2, True),
    (((True,True,False,True),)*2, True),
    (((True,False,False,False),)*2, False),
])
def test_contradictory_receipt_facts_are_rejected(flags, invoked):
    with pytest.raises(bridge.SqliteSetHandoffError):
        handoff(flags, invoked)


def test_close_releases_every_member_after_first_failure():
    calls = []
    def close_first():
        calls.append("principal")
        raise OSError("PRIVATE_ERROR")
    def close_second():
        calls.append("aux_app")
    owned = object.__new__(sets.SqliteSetProducer)
    owned._members = ((None, SimpleNamespace(close=close_first)),
                      (None, SimpleNamespace(close=close_second)))
    with pytest.raises(sets.SqliteSetError, match="^SQLITE_SET_CLOSE_NOT_VERIFIED$"):
        owned.close()
    assert calls == ["principal", "aux_app"]
    assert owned._closed is True
    with pytest.raises(sets.SqliteSetError, match="SECOND_SQLITE_SET_CAPTURE_DENIED"):
        owned.prepare(1)


@pytest.mark.parametrize("field,bad", [("maximum_bytes", -1), ("source_id", "aux/escape")])
def test_native_producer_rechecks_nested_source_before_construction(tmp_path, field, bad):
    from tests.test_recovery_sqlite_set import _plan
    plan = _plan(tmp_path)
    object.__setattr__(plan.sources[1], field, bad)
    with pytest.raises(sets.SqliteSetError):
        sets.SqliteSetProducer(plan)


def complete_plan(tmp_path):
    from tests.test_recovery_sqlite_set_manifest import _native_owned, LAYOUT
    from tools.recovery_state_adapter import StateRecoveryPlan
    sql, scopes, authority = _native_owned(tmp_path)
    state_dir = sql.publication / "state"
    state_dir.mkdir(mode=0o700)
    state_dir.chmod(0o700)
    opaque = StateRecoveryPlan(sql.operation_id, sql.proposal_sha256,
        scopes, authority, state_dir, layout_id=LAYOUT)
    return bridge.StateSqliteSetPlan(opaque, sql)


@pytest.mark.parametrize("change", ["operation", "proposal", "publication", "missing_source", "entry_limit"])
def test_combined_plan_denies_incomplete_binding(tmp_path, change):
    from dataclasses import replace
    from engines import recovery_non_sqlite_state as state
    good = complete_plan(tmp_path)
    opaque = good.state
    if change == "operation":
        opaque = replace(opaque, operation_id="FOREIGN_OPERATION")
    elif change == "proposal":
        opaque = replace(opaque, proposal_sha256="c"*64)
    elif change == "publication":
        opaque = replace(opaque, publication=tmp_path / "foreign_state")
    elif change == "missing_source":
        opaque = replace(opaque, authorization=replace(opaque.authorization,
            protected_sqlite_paths=opaque.authorization.protected_sqlite_paths[:1]))
    else:
        opaque = replace(opaque, limits=state.Limits(entries=4))
    with pytest.raises(bridge.SqliteSetHandoffError):
        bridge.StateSqliteSetPlan(opaque, good.sqlite)


from tests.test_recovery_sqlite_set_manifest import native
import time


@native
def test_actual_bridge_binds_all_members_and_state(tmp_path):
    plan = complete_plan(tmp_path)
    before = tuple(s.source.read_bytes() for s in plan.sqlite.sources)
    result = bridge.capture_set_with_state(plan=plan, deadline=time.monotonic()+30)
    assert result.ok is True, result.state_result
    public = bridge.public_set_disposition(result)
    assert public["verified_sqlite_members"] == 2
    assert public["sqlite_set_disposition"] == "SET_AND_OPAQUE_BYTES_VERIFIED_NOT_FULL_RECOVERY"
    assert result.bundle.archive.is_file()
    assert tuple(s.source.read_bytes() for s in plan.sqlite.sources) == before


@native
def test_actual_bridge_preserves_partial_publication(tmp_path, monkeypatch):
    plan = complete_plan(tmp_path)
    original = sets.SqliteSetProducer.validate
    def fail_auxiliary(self, prepared, deadline):
        def fail(*args):
            raise sets.SqliteSetError("OWNED_AUXILIARY_FAULT")
        monkeypatch.setattr(self._members[1][1], "validate", fail)
        return original(self, prepared, deadline)
    monkeypatch.setattr(sets.SqliteSetProducer, "validate", fail_auxiliary)
    result = bridge.capture_set_with_state(plan=plan, deadline=time.monotonic()+30)
    assert result.ok is False
    assert result.bundle is None
    public = bridge.public_set_disposition(result)
    assert public["prepared_sqlite_members"] == 2
    assert public["published_sqlite_members"] == 1
    assert public["sqlite_set_disposition"] == "PARTIALLY_PUBLISHED_PRESERVE_AND_DO_NOT_RETRY"
    assert len(list(plan.sqlite.publication.glob("database_*.db"))) == 1
    assert list(plan.sqlite.publication.glob(".*/snapshot.partial"))
    assert not list(plan.state.publication.glob("state-*.tar"))
