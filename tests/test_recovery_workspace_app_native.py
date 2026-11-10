"""Actual Linux SAME restore/guest App case in the existing standard CI suite.

Synthetic provenance only; the fixed native App probe retains its original
process guard, no external credentials/network and one shared phaseB deadline.
The outer LOCAL_SAFE loop covers descriptor lifecycle separately without adding
a new child-process grant to that supervisor.
"""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import sys

import pytest

from engines.data_vault_engine import create_sqlite_backup
from tools import backup_operator_recovery_327 as operator


@pytest.mark.skipif(sys.platform != "linux", reason="Actual Linux isolated App and procfs required")
def test_same_owned_restore_runs_real_normal_boot_in_explicit_workspace(tmp_path):
    source, archives, scratch = tmp_path/"source.db", tmp_path/"archives", tmp_path/"scratch"
    scratch.mkdir(mode=0o700)
    with closing(sqlite3.connect(source)) as connection, connection:
        connection.execute("CREATE TABLE owned_case(id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO owned_case(value) VALUES(?)", ("synthetic-only",))
    created = create_sqlite_backup(source, tmp_path, "OWNED_SYNTHETIC", directory=archives,
                                  max_files=0, preserve_existing_backups=True, snapshot_timeout=60)
    assert created["ok"] is True and created["backup_created"] is True, created
    selected = archives/created["backup_file"]
    before = hashlib.sha256(selected.read_bytes()).hexdigest()
    manifest = selected.with_suffix(".json").read_bytes()
    live = source.read_bytes()
    result = operator.verify_and_restore_isolated(
        archives, created["backup_file"], 60, app_probe_mode="normal_boot",
        restore_workspace_root=scratch)
    assert result["ok"] is True and result["code"] == "SQLITE_RESTORE_AND_GUEST_APP_SMOKE_VERIFIED", result
    assert result["full_application_recovery_certified"] is False
    assert result["restore_workspace"]["device"] == scratch.stat().st_dev
    assert result["restore_workspace"]["root_inode"] == scratch.stat().st_ino
    assert result["restore_workspace"]["same_restoration_for_app"] is True
    assert result["restore_workspace"]["cleanup_verified"] is True
    app = result["app_probe"]
    assert app["ok"] is True and app["child"]["initialized"] is True
    assert app["child"]["initialization_error_present"] is False
    assert len(app["child"]["routes"]) == 6
    assert all(route["ok"] and route["completed_read_fetches"] > 0 for route in app["child"]["routes"])
    assert not app["child"]["boundary_denials"]
    assert app["child"]["authenticated_client_verified"] is False
    assert hashlib.sha256(selected.read_bytes()).hexdigest() == before
    assert selected.with_suffix(".json").read_bytes() == manifest
    assert source.read_bytes() == live
    assert list(scratch.iterdir()) == []
    assert not list(archives.glob(".isolated_restore_327_*"))



def test_default_backend_still_verifies_actual_owned_sqlite(tmp_path):
    # Legacy default restoration uses the original TemporaryDirectory cleanup;
    # retain its regression check in the existing standard suite alongside
    # test_backup_operator_recovery_327, not the new descriptor-boundary loop.
    source, archives = tmp_path/"source.db", tmp_path/"archives"
    with closing(sqlite3.connect(source)) as connection, connection:
        connection.execute("CREATE TABLE owned_default(id INTEGER)")
        connection.execute("INSERT INTO owned_default VALUES(1)")
    created = create_sqlite_backup(source, tmp_path, "OWNED_SYNTHETIC", directory=archives,
                                  max_files=0, preserve_existing_backups=True, snapshot_timeout=60)
    assert created["ok"] is True and created["backup_created"] is True
    selected = archives/created["backup_file"]
    before = selected.read_bytes(), selected.with_suffix(".json").read_bytes(), source.read_bytes()
    result = operator.verify_and_restore_isolated(archives, created["backup_file"], 60)
    assert result["ok"] is True and result["code"] == "RESTORE_VERIFIED", result
    assert (selected.read_bytes(), selected.with_suffix(".json").read_bytes(), source.read_bytes()) == before
    assert not list(archives.glob(".isolated_restore_327_*"))
