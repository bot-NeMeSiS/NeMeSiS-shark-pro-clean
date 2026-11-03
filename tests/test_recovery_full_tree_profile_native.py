"""Owned full-tree profile integration case; intended for native POSIX CI only.

The test creates its own opaque state trees and SQLite fixtures. It does not load
the application, touch production state, or certify full application recovery.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time

import pytest

from engines import recovery_non_sqlite_state as state


PROFILE = "CE_RUNTIME_STATE_V1"
LAYOUT = "CE_COLOCATED_SENTINEL_AND_RUNTIME_AUTOPILOT_V1"
OPERATION_ID = "OWNED_PROFILE_TEST_1"
PROPOSAL_SHA256 = hashlib.sha256(
    b"owned full-state profile test proposal; not an authorization grant"
).hexdigest()
EXPECTED_CHILD_ENTRIES = 19664
EXPECTED_FILES = 19648
EXPECTED_CHILD_DIRECTORIES = 16
EXPECTED_STATE_BYTES = 55054268


def _private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    path.chmod(0o700)
    return path


def _json_bytes_with_size(value: object, size: int) -> bytes:
    prefix = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")
    if len(prefix) > size:
        raise AssertionError("owned fixture prefix exceeds assigned file size")
    return prefix + b" " * (size - len(prefix))


def _write_json_file(path: Path, value: object, size: int) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    path.write_bytes(_json_bytes_with_size(value, size))


def _make_directory_chain(root: Path, components: tuple[str, ...]) -> Path:
    current = root
    for component in components:
        current = current / component
        current.mkdir(mode=0o700, exist_ok=True)
        current.chmod(0o700)
    return current


def _populate_ce(root: Path) -> tuple[int, int]:
    _private_directory(root)
    _write_json_file(root / "product_memory.json", {"recommendations": {}}, 334568)
    _write_json_file(root / "sentinel_issues_memory.json", {"issues": [], "events": []}, 149557)

    directories = [
        _make_directory_chain(root, (f"segment-ce-{index:02d}",))
        for index in range(7)
    ]

    other_sizes = [2116] * 14781 + [2115] * (19409 - 14781)
    for index, size in enumerate(other_sizes):
        parent = directories[index] if index < len(directories) else root
        name = (
            f"owned-ce-nested-{index:05d}.json"
            if index < len(directories)
            else f"owned-ce-root-{index:05d}.json"
        )
        _write_json_file(parent / name, {"owned_fixture": f"ce-{index}"}, size)

    return 19411, 7


def _populate_runtime(root: Path) -> tuple[int, int]:
    _private_directory(root)
    _write_json_file(root / "sentinel_autopilot_memory.json", {"issues": []}, 392697)

    directories = [
        _make_directory_chain(root, ("segment-runtime-00",)),
        _make_directory_chain(
            root, ("segment-runtime-01", "segment-runtime-02", "segment-runtime-03")
        ),
        *(
            _make_directory_chain(root, (f"segment-runtime-{index:02d}",))
            for index in range(4, 9)
        ),
    ]

    other_sizes = [55562] * 234 + [55561] * 2
    for index, size in enumerate(other_sizes):
        parent = directories[index] if index < len(directories) else root
        name = (
            f"owned-runtime-nested-{index:03d}.json"
            if index < len(directories)
            else f"owned-runtime-root-{index:03d}.json"
        )
        _write_json_file(parent / name, {"owned_fixture": f"runtime-{index}"}, size)

    return 237, 9


def _create_owned_database(path: Path, marker: str) -> None:
    connection = sqlite3.connect(str(path))
    try:
        connection.execute(
            "CREATE TABLE owned_fixture (fixture_id INTEGER PRIMARY KEY, marker TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO owned_fixture(marker) VALUES (?)",
            ((f"{marker}-row-1",), (f"{marker}-row-2",)),
        )
        connection.commit()
    finally:
        connection.close()
    path.chmod(0o600)


@pytest.mark.skipif(os.name != "posix", reason="requires the engine's native POSIX fd protections")
def test_explicit_profile_captures_and_restores_full_owned_tree(tmp_path: Path, capsys) -> None:
    owned_root = _private_directory(tmp_path / "owned-full-tree-profile")
    ce_root = owned_root / "owned-ce-root"
    runtime_root = owned_root / "owned-runtime-root"
    publication = _private_directory(owned_root / "owned-state-publication")
    ce_files, ce_dirs = _populate_ce(ce_root)
    runtime_files, runtime_dirs = _populate_runtime(runtime_root)
    assert ce_files + runtime_files == EXPECTED_FILES
    assert ce_dirs + runtime_dirs == EXPECTED_CHILD_DIRECTORIES
    assert EXPECTED_FILES + EXPECTED_CHILD_DIRECTORIES == EXPECTED_CHILD_ENTRIES
    assert (
        334568 + 149557
        + 2116 * 14781 + 2115 * (19409 - 14781)
        + 392697
        + 55562 * 234 + 55561 * 2
    ) == EXPECTED_STATE_BYTES

    source_database = owned_root / "owned-source.sqlite3"
    snapshot_path = publication / "owned-sqlite-snapshot.sqlite3"
    snapshot_partial = publication / "owned-sqlite-snapshot.partial"
    _create_owned_database(source_database, "source")
    restoration_workspace = owned_root / ".isolated_restore_327_owned"
    _private_directory(restoration_workspace)
    (restoration_workspace / "source").mkdir(mode=0o700)
    restoration_database = restoration_workspace / "restoration-test.db"

    scopes = (
        state.Scope("ce", ce_root),
        state.Scope("legacy_runtime", runtime_root),
    )
    authorization = state.Authorization(
        "OWNED_PROFILE_NATIVE",
        tuple((scope.role, str(scope.source)) for scope in scopes),
        True,
        (str(source_database), str(snapshot_path), str(restoration_database)),
    )
    layout_binding = state.StateLayoutBinding(
        LAYOUT,
        OPERATION_ID,
        PROPOSAL_SHA256,
    )

    sqlite_integrity_ok = False
    sqlite_snapshot_sha256 = None

    def snapshot_callback(deadline: float) -> state.SqliteReceipt:
        nonlocal sqlite_integrity_ok, sqlite_snapshot_sha256
        if time.monotonic() >= deadline:
            raise TimeoutError("owned fixture deadline expired")
        source = sqlite3.connect(str(source_database))
        destination = sqlite3.connect(str(snapshot_partial))
        try:
            source.backup(destination)
            integrity = destination.execute("PRAGMA integrity_check").fetchone()
            sqlite_integrity_ok = integrity == ("ok",)
            destination.commit()
        finally:
            destination.close()
            source.close()
        if not sqlite_integrity_ok:
            raise AssertionError("owned SQLite snapshot integrity check failed")
        snapshot_partial.chmod(0o600)
        os.link(snapshot_partial, snapshot_path)
        snapshot_partial.unlink()
        sqlite_snapshot_sha256 = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
        return state.SqliteReceipt(
            OPERATION_ID,
            sqlite_snapshot_sha256,
            True,
        )

    deadline = time.monotonic() + 300.0
    captured = state.capture_state(
        scopes=scopes,
        authorization=authorization,
        publication=publication,
        deadline=deadline,
        sqlite_snapshot_callback=snapshot_callback,
        layout_binding=layout_binding,
        profile_id=PROFILE,
    )
    assert captured["ok"] is True
    assert captured["state_published"] is True
    assert captured["profile_id"] == PROFILE
    assert captured["layout_id"] == LAYOUT
    assert captured["scope_roles"] == ["ce", "legacy_runtime"]
    assert captured["entries"] == EXPECTED_CHILD_ENTRIES
    assert captured["state_bytes"] == EXPECTED_STATE_BYTES
    assert captured["continuous_cross_store_consistency_certified"] is False
    assert captured["full_application_recovery_certified"] is False
    assert captured["sqlite_receipt"]["artifact_id"] == OPERATION_ID
    assert captured["sqlite_receipt"]["sha256"] == sqlite_snapshot_sha256
    assert sqlite_integrity_ok is True
    assert isinstance(sqlite_snapshot_sha256, str) and len(sqlite_snapshot_sha256) == 64

    archive_path = publication / captured["bundle_file"]
    receipt = state.SqliteReceipt(**captured["sqlite_receipt"])
    # The isolated DB presented to restore_state is the exact published snapshot,
    # pre-created by this test harness; the engine itself must not restore SQLite.
    shutil.copyfile(snapshot_path, restoration_database)
    restoration_database.chmod(0o600)
    restored_sqlite_sha256 = hashlib.sha256(restoration_database.read_bytes()).hexdigest()
    assert restored_sqlite_sha256 == receipt.sha256
    connection = sqlite3.connect(str(restoration_database))
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute(
            "SELECT marker FROM owned_fixture ORDER BY fixture_id"
        ).fetchall() == [("source-row-1",), ("source-row-2",)]
    finally:
        connection.close()
    restoration_database_identity = state._identity(restoration_database.stat())
    with archive_path.open("rb") as stream:
        with pytest.raises(state.StateError) as caught:
            state.parse_bundle(
                stream,
                expected_archive_sha256=captured["archive_sha256"],
                expected_manifest_sha256=captured["manifest_sha256"],
                expected_sqlite=receipt,
                deadline=time.monotonic() + 120.0,
                expected_layout_id=LAYOUT,
                expected_proposal_sha256=PROPOSAL_SHA256,
                expected_scope_roles=("ce", "legacy_runtime"),
            )
    # Under the unchanged 400-member default, the 401st member fails before bytes cap.
    assert str(caught.value) == "UNSAFE_TAR_NAME"

    wrong_workspace = owned_root / ".isolated_restore_327_owned"
    restore = state.restore_state(
        bundle=archive_path,
        expected_archive_sha256=captured["archive_sha256"],
        expected_manifest_sha256=captured["manifest_sha256"],
        expected_sqlite=receipt,
        workspace=wrong_workspace,
        expected_database_identity=restoration_database_identity,
        deadline=time.monotonic() + 300.0,
        expected_layout_id=LAYOUT,
        expected_proposal_sha256=PROPOSAL_SHA256,
        expected_scope_roles=("ce", "legacy_runtime"),
        expected_profile_id=PROFILE,
    )
    assert restore["ok"] is True
    assert restore["state_ready_before_app"] is True
    assert restore["entries"] == EXPECTED_CHILD_ENTRIES
    assert restore["state_bytes"] == EXPECTED_STATE_BYTES
    assert restore["app_started"] is False
    assert restore["sqlite_restore_created"] is False
    assert restore["live_restore_allowed"] is False
    assert restore["full_application_recovery_certified"] is False
    assert state._identity(restoration_database.stat()) == restoration_database_identity
    assert hashlib.sha256(restoration_database.read_bytes()).hexdigest() == receipt.sha256
    connection = sqlite3.connect(str(restoration_database))
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute(
            "SELECT marker FROM owned_fixture ORDER BY fixture_id"
        ).fetchall() == [("source-row-1",), ("source-row-2",)]
    finally:
        connection.close()

    restored_data = wrong_workspace / "source" / "data"
    product = json.loads((restored_data / "continuous_evolution_os" / "product_memory.json").read_text())
    sentinel = json.loads(
        (restored_data / "continuous_evolution_os" / "sentinel_issues_memory.json").read_text()
    )
    autopilot = json.loads(
        (restored_data / "runtime" / "sentinel_autopilot_memory.json").read_text()
    )
    assert product == {"recommendations": {}}
    assert sentinel == {"issues": [], "events": []}
    assert autopilot == {"issues": []}

    proof = {
        "schema": "OWNED_FULL_STATE_NATIVE_PROOF_V1",
        "profile_id": PROFILE,
        "child_entries": EXPECTED_CHILD_ENTRIES,
        "files": EXPECTED_FILES,
        "child_directories": EXPECTED_CHILD_DIRECTORIES,
        "regular_bytes": EXPECTED_STATE_BYTES,
        "sqlite_integrity_ok": sqlite_integrity_ok,
        "sqlite_snapshot_sha256": sqlite_snapshot_sha256,
        "owned_sqlite_restore_from_receipt_verified": True,
        "engine_sqlite_restore_created": False,
        "state_byte_restore_verified": True,
        "app_started": False,
        "production_data_touched": False,
        "full_application_recovery_certified": False,
    }
    with capsys.disabled():
        print(json.dumps(proof, sort_keys=True))
