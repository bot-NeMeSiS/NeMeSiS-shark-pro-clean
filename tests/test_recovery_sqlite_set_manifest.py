"""Pure V4 codec/complete-set admission tests, not a recovery certificate."""
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import io
import json
from pathlib import Path
import tarfile
import time
from unittest.mock import Mock

import pytest

from engines import recovery_non_sqlite_state as state
from engines import recovery_sqlite_set_contract as contract
from tests.test_recovery_state_layout_contract import (
    _layout_manifest, LAYOUT, OPERATION, PROPOSAL)


def _receipt():
    return contract.SqliteSetReceipt(OPERATION, (
        contract.SqliteSetMemberReceipt("principal", "1" * 32,
            "database_" + "1" * 32 + ".db", "a" * 64, 8192, 1024 * 1024),
        contract.SqliteSetMemberReceipt("aux_app", "2" * 32,
            "database_" + "2" * 32 + ".db", "b" * 64, 16384, 1024 * 1024)), True)


def _value():
    _, payloads, value = _layout_manifest()
    value["schema"] = "OPAQUE_STATE_BUNDLE_V4"
    value["sqlite"] = contract.to_record(_receipt())
    return value, payloads


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _archive(value):
    manifest = _bytes(value)
    pieces = [("payload/%06d" % index, ("opaque-%d" % index).encode("ascii"))
              for index in range(len(value["entries"]))]
    pieces.append(("manifest.json", manifest))
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, raw in pieces:
            info = tarfile.TarInfo(name)
            info.mode, info.size, info.mtime = 0o600, len(raw), 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(raw))
    length = sum(512 + ((len(raw) + 511) // 512) * 512 for _, raw in pieces) + 1024
    return stream.getvalue()[:length], manifest


def _read(value, expected=None):
    archive, manifest = _archive(value)
    return state.parse_bundle(io.BytesIO(archive),
        expected_archive_sha256=hashlib.sha256(archive).hexdigest(),
        expected_manifest_sha256=hashlib.sha256(manifest).hexdigest(),
        expected_sqlite=_receipt() if expected is None else expected,
        deadline=time.monotonic() + 10, expected_layout_id=LAYOUT,
        expected_proposal_sha256=PROPOSAL, expected_scope_roles=("ce", "legacy_runtime"))


def test_v4_roundtrip_requires_the_same_complete_declared_set():
    value, _ = _value()
    parsed = _read(value)
    assert parsed["schema"] == "OPAQUE_STATE_BUNDLE_V4"
    assert parsed["sqlite"] == contract.to_record(_receipt())
    assert parsed["continuous_cross_store_consistency_certified"] is False


@pytest.mark.parametrize("field,new_value", [
    ("sha256", "c" * 64), ("backup_file", "database_" + "3" * 32 + ".db"),
    ("capture_id", "3" * 32), ("size_bytes", "0000010000"),
    ("maximum_bytes", "0002097152")])
def test_rehashed_archive_cannot_replace_one_member_of_expected_set(field, new_value):
    value, _ = _value()
    value["sqlite"]["members"][1][field] = new_value
    with pytest.raises(state.StateError, match="FOREIGN_SQLITE_RECEIPT"):
        _read(value)


@pytest.mark.parametrize("attack", ["omit_auxiliary", "duplicate_capture", "duplicate_file",
                                   "swap_hashes", "extra_member", "new_operation"])
def test_complete_set_cannot_inherit_another_members_identity(attack):
    value, _ = _value()
    members = value["sqlite"]["members"]
    if attack == "omit_auxiliary":
        members.pop()
    elif attack == "duplicate_capture":
        members[1]["capture_id"] = members[0]["capture_id"]
    elif attack == "duplicate_file":
        members[1]["backup_file"] = members[0]["backup_file"]
    elif attack == "swap_hashes":
        members[0]["sha256"], members[1]["sha256"] = members[1]["sha256"], members[0]["sha256"]
    elif attack == "extra_member":
        member = deepcopy(members[1])
        member.update(source_id="aux_b", capture_id="3" * 32,
                      backup_file="database_" + "3" * 32 + ".db")
        members.append(member)
    else:
        value["sqlite"]["artifact_id"] = "OTHER_OPERATION"
        value["layout_binding"]["operation_id"] = "OTHER_OPERATION"
    with pytest.raises(state.StateError):
        _read(value)


@pytest.mark.parametrize("field,bad", [
    ("size_bytes", 8192), ("size_bytes", "8192"), ("size_bytes", True),
    ("size_bytes", "0000000000"), ("size_bytes", "0001048577"),
    ("maximum_bytes", "4294967297"), ("source_id", "../aux_app"),
    ("backup_file", "../database_" + "2" * 32 + ".db")])
def test_wire_member_fields_are_closed_and_canonical(field, bad):
    value = contract.to_record(_receipt())
    value["members"][1][field] = bad
    with pytest.raises(contract.SqliteSetContractError):
        contract.from_record(value)


def test_schema_and_expected_receipt_cannot_be_downgraded_to_one_database():
    value, _ = _value()
    with pytest.raises(state.StateError, match="INVALID_MANIFEST"):
        _read(value, state.SqliteReceipt(OPERATION, "a" * 64, True))
    value["schema"] = "OPAQUE_STATE_BUNDLE_V2"
    with pytest.raises(state.StateError, match="INVALID_MANIFEST"):
        _read(value)


def test_old_single_database_v2_remains_readable():
    _, _, value = _layout_manifest()
    expected = state.SqliteReceipt(**value["sqlite"])
    assert _read(value, expected)["sqlite"] == value["sqlite"]


@pytest.mark.parametrize("size", [1, 8192, 1024 * 1024])
def test_sizing_mask_has_exact_wire_width_but_is_not_a_receipt(size):
    receipt = _receipt()
    members = tuple(replace(m, size_bytes=size) for m in receipt.members)
    actual = contract.to_record(replace(receipt, members=members))
    mask = contract.sizing_record(OPERATION, tuple(
        (m.source_id, m.maximum_bytes) for m in receipt.members))
    assert len(_bytes(actual)) == len(_bytes(mask))
    with pytest.raises(contract.SqliteSetContractError):
        contract.from_record(mask)


def test_writer_checks_pre_capture_size_for_v4():
    value, _ = _value()
    stream = io.BytesIO()
    writer = state._Writer(stream, time.monotonic() + 10)
    with pytest.raises(state.StateError, match="SOURCE_CHANGED"):
        writer.manifest(value, state._policy(), expected_length=len(_bytes(value)) + 1)
    assert stream.getvalue() == b""


def test_oversized_full_manifest_never_calls_snapshot():
    value, _ = _value()
    value["sqlite"] = contract.sizing_record(OPERATION, tuple(
        (m.source_id, m.maximum_bytes) for m in _receipt().members))
    # Valid filesystem-component widths can still exceed the manifest budget
    # after ASCII escaping. This is a metadata mask, not payload or a real scan.
    value["entries"] = [{"relative": "/".join(
        ["é" * 120] * 5 + ["é" * 116 + f"{i:04d}"])} for i in range(250)]
    callback = Mock()
    with pytest.raises(state.StateError, match="MANIFEST_BUDGET"):
        state._snapshot_after_profile_manifest_preflight(
            value, state._policy(), time.monotonic() + 10, callback, Mock())
    callback.assert_not_called()


def test_sqlite_members_share_the_original_aggregate_entry_budget():
    value, payloads = _value()
    value["limits"] = asdict(state.Limits(entries=4))
    with pytest.raises(state.StateError, match="ENTRY_BUDGET"):
        state._manifest(_bytes(value), payloads, state.Limits(entries=4),
                        time.monotonic() + 10, sqlite_set=True)
    value["limits"] = asdict(state.Limits(entries=5))
    assert state._manifest(_bytes(value), payloads, state.Limits(entries=5),
                           time.monotonic() + 10, sqlite_set=True)["schema"] == value["schema"]


@pytest.mark.parametrize("attack", ["missing_protected", "extra_protected", "duplicate_path"])
def test_callback_declaration_must_match_every_protected_sqlite_path(tmp_path, attack):
    principal, aux = tmp_path / "main.db", tmp_path / "app.db"
    sources = (("principal", principal, 1024 * 1024), ("aux_app", aux, 1024 * 1024))
    protected = (str(principal), str(aux))
    if attack == "missing_protected":
        protected = protected[:1]
    elif attack == "extra_protected":
        protected += (str(tmp_path / "unclassified.db"),)
    else:
        sources = (sources[0], ("aux_app", principal, 1024 * 1024))
        protected = (str(principal), str(principal))
    prepare = Mock()
    callbacks = state.PreparedSqliteSetCallbacks(sources, prepare, Mock())
    authority = state.Authorization("OWNED_SET_AUTH", (), True, protected)
    with pytest.raises(state.StateError, match="INVALID_SQLITE_SET_DECLARATION"):
        state._sqlite_set_sources(callbacks, authority)
    prepare.assert_not_called()


def test_callback_complete_declaration_is_admitted_without_io(tmp_path):
    sources = (("principal", tmp_path / "main.db", 1024),
               ("aux_app", tmp_path / "app.db", 1024))
    callbacks = state.PreparedSqliteSetCallbacks(sources, Mock(), Mock())
    authority = state.Authorization("OWNED_SET_AUTH", (), True, tuple(str(p) for _, p, _ in sources))
    assert state._sqlite_set_sources(callbacks, authority) == sources

# Native cases deliberately keep the full FD/namespace boundary. Windows skips
# them; no availability guard is patched to manufacture a native certificate.
import os
import sqlite3
from contextlib import closing
from tools import recovery_sqlite_set as producer_set

_NATIVE = (os.name == "posix" and Path("/proc/self/fd").is_dir()
           and os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW"))
native = pytest.mark.skipif(not _NATIVE, reason="native complete set/state handoff required")


def _native_owned(tmp_path):
    ce, runtime, publication = (tmp_path / "ce", tmp_path / "runtime", tmp_path / "publication")
    for directory in (ce, runtime, publication):
        directory.mkdir(mode=0o700)
        directory.chmod(0o700)
    (ce / "product_memory.json").write_bytes(b'{"owned":"before"}')
    (ce / "sentinel_issues_memory.json").write_bytes(b'{"owned_issues":[]}')
    (runtime / "sentinel_autopilot_memory.json").write_bytes(b'{"owned_actions":[]}')
    sources = (
        producer_set.SqliteSource("principal", tmp_path / "main.db", 1024 * 1024),
        producer_set.SqliteSource("aux_app", tmp_path / "app.db", 1024 * 1024))
    for source in sources:
        with closing(sqlite3.connect(source.source)) as db:
            db.execute("CREATE TABLE owned_rows (source_id TEXT)")
            db.execute("INSERT INTO owned_rows VALUES (?)", (source.source_id,))
            db.commit()
    plan = producer_set.SqliteSetPlan(
        OPERATION, PROPOSAL, sources, publication, snapshot_timeout=30.0)
    scopes = (state.Scope("ce", ce), state.Scope("legacy_runtime", runtime))
    authority = state.Authorization("OWNED_SET_NATIVE_AUTH",
        tuple((s.role, str(s.source)) for s in scopes), True,
        tuple(str(s.source) for s in sources))
    return plan, scopes, authority


def _capture(plan, scopes, authority, producer, *, prepare=None, validate=None, limits=None, profile=None):
    callbacks = state.PreparedSqliteSetCallbacks(
        tuple((s.source_id, s.source, s.maximum_bytes) for s in plan.sources),
        producer.prepare if prepare is None else prepare,
        producer.validate if validate is None else validate)
    return state.capture_state(scopes=scopes, authorization=authority, publication=plan.publication,
        deadline=time.monotonic() + 30, limits=state.Limits() if limits is None else limits,
        layout_binding=state.StateLayoutBinding(LAYOUT, OPERATION, PROPOSAL),
        profile_id=profile, sqlite_set_callbacks=callbacks)


@native
def test_actual_set_captures_all_sqlite_before_complete_state_publication(tmp_path):
    plan, scopes, authority = _native_owned(tmp_path)
    before = tuple(s.source.read_bytes() for s in plan.sources)
    with producer_set.SqliteSetProducer(plan) as producer:
        result = _capture(plan, scopes, authority, producer)
        assert result["ok"] is True, result
        assert result["same_prepared_sqlite_set_verified"] is True
        assert all(p._absolute_deadline == producer._deadline
                   and p._deadline == producer._deadline for _, p in producer._members)
        assert result["opaque_bracket_closed"] is True
        assert set(result["sqlite_backup_files"]) == {"principal", "aux_app"}
        expected = contract.from_record(result["sqlite_receipt"])
        with (plan.publication / result["bundle_file"]).open("rb") as stream:
            parsed = state.parse_bundle(stream,
                expected_archive_sha256=result["archive_sha256"],
                expected_manifest_sha256=result["manifest_sha256"], expected_sqlite=expected,
                deadline=time.monotonic() + 10, expected_layout_id=LAYOUT,
                expected_proposal_sha256=PROPOSAL, expected_scope_roles=("ce", "legacy_runtime"))
        assert parsed["schema"] == "OPAQUE_STATE_BUNDLE_V4"
        assert parsed["sqlite"] == result["sqlite_receipt"]
        workspace = tmp_path / ".isolated_restore_327_missing_set_binding"
        denied = state.restore_state(
            bundle=plan.publication / result["bundle_file"],
            expected_archive_sha256=result["archive_sha256"],
            expected_manifest_sha256=result["manifest_sha256"], expected_sqlite=expected,
            workspace=workspace, expected_database_identity={}, deadline=time.monotonic() + 10)
        assert denied["code"] == "SQLITE_SET_RESTORE_NOT_VERIFIED"
        assert denied["state_ready_before_app"] is False
        assert not workspace.exists()
        assert result["full_application_recovery_certified"] is False
        assert result["continuous_cross_store_consistency_certified"] is False
    assert tuple(s.source.read_bytes() for s in plan.sources) == before


@native
def test_state_mutation_aborts_before_any_member_validation(tmp_path):
    plan, scopes, authority = _native_owned(tmp_path)
    with producer_set.SqliteSetProducer(plan) as producer:
        def mutate(deadline):
            prepared = producer.prepare(deadline)
            (scopes[0].source / "product_memory.json").write_bytes(b'{"owned":"changed"}')
            return prepared
        result = _capture(plan, scopes, authority, producer, prepare=mutate)
        assert result["ok"] is False
        assert result["code"] == "STATE_CHANGED_ACROSS_SQLITE_INTERVAL"
        assert producer._validated is False
        assert all(p.result["prepare_completed"] for _, p in producer._members)
        assert not list(plan.publication.glob("database_*.db"))
        assert not list(plan.publication.glob("state-*.tar"))
        assert len(list(plan.publication.glob(".*/snapshot.partial"))) == 2


@native
@pytest.mark.parametrize("attack", ["omit_validated_auxiliary", "swap_validated_capabilities"])
def test_complete_receipt_requires_each_original_native_capability(tmp_path, attack):
    plan, scopes, authority = _native_owned(tmp_path)
    with producer_set.SqliteSetProducer(plan) as producer:
        def substitute(prepared, deadline):
            validated = producer.validate(prepared, deadline)
            if attack == "omit_validated_auxiliary":
                return replace(validated, members=validated.members[:1])
            return replace(validated, members=(
                (validated.members[0][0], validated.members[1][1]),
                (validated.members[1][0], validated.members[0][1])))
        result = _capture(plan, scopes, authority, producer, validate=substitute)
        assert result["ok"] is False
        assert result["sqlite_receipt"] is None
        assert result["state_published"] is False
        assert result["code"] in {"FOREIGN_PREPARED_SQLITE_SET", "FOREIGN_PREPARED_SQLITE_CAPTURE"}
        assert len(list(plan.publication.glob("database_*.db"))) == 2, "preserve verified members"
        assert not list(plan.publication.glob("state-*.tar"))


@native
def test_aggregate_entry_limit_stops_before_first_sqlite_capture(tmp_path):
    plan, scopes, authority = _native_owned(tmp_path)
    with producer_set.SqliteSetProducer(plan) as producer:
        result = _capture(plan, scopes, authority, producer, limits=state.Limits(entries=4))
        assert result["code"] == "ENTRY_BUDGET"
        assert result["sqlite_callback_invoked"] is False
        assert producer._attempted is False


@native
def test_set_cannot_opt_in_to_larger_state_profile(tmp_path):
    plan, scopes, authority = _native_owned(tmp_path)
    with producer_set.SqliteSetProducer(plan) as producer:
        result = _capture(plan, scopes, authority, producer, profile=state.CE_RUNTIME_STATE_V1)
        assert result["code"] == "INVALID_SQLITE_SET_MODE"
        assert result["sqlite_callback_invoked"] is False
        assert producer._attempted is False
