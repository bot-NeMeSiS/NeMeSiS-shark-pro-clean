"""Owned per-member SQLite budget checks; never real-data recovery evidence."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

import pytest
from tools import recovery_sqlite_prepare as producer

_NATIVE = (os.name == "posix" and Path("/proc/self/fd").is_dir()
           and os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW"))
native = pytest.mark.skipif(not _NATIVE, reason="native confined SQLite worker required")


def _producer(tmp_path, **options):
    return producer.SqliteSnapshotProducer(
        source=tmp_path / "owned.db", publication=tmp_path / "publication",
        operation_id="OWNED_MEMBER_BUDGET", proposal_sha256="a" * 64, **options)


@pytest.mark.parametrize("limit", [None, True, False, 0, -1, 1.0,
                                   producer.MAX_SNAPSHOT_BYTES + 1])
def test_member_budget_cannot_expand_existing_ceiling(tmp_path, limit):
    with pytest.raises(producer.PreparedSnapshotError,
                       match="INVALID_SQLITE_SNAPSHOT_BYTE_LIMIT"):
        _producer(tmp_path, snapshot_byte_limit=limit)


def test_default_member_budget_preserves_existing_ceiling(tmp_path):
    owned = _producer(tmp_path)
    assert owned.snapshot_byte_limit == producer.MAX_SNAPSHOT_BYTES
    assert owned.result["sqlite_capture_attempted"] is False
    owned.close()


def _owned_database(tmp_path):
    publication = tmp_path / "publication"
    publication.mkdir(mode=0o700)
    publication.chmod(0o700)
    source = tmp_path / "owned.db"
    with closing(sqlite3.connect(source)) as db:
        db.execute("CREATE TABLE auxiliary_owned (id INTEGER PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO auxiliary_owned(value) VALUES (?)", ("preserved-owned-value",))
        db.commit()
    return source, publication


@native
@pytest.mark.parametrize("bounded", [False, True])
def test_exact_capture_and_validation_keep_member_budget(tmp_path, bounded):
    source, publication = _owned_database(tmp_path)
    limit = 1024 * 1024 if bounded else producer.MAX_SNAPSHOT_BYTES
    owned = _producer(tmp_path, snapshot_byte_limit=limit)
    before = source.read_bytes()
    deadline = time.monotonic() + 15
    try:
        prepared = owned.prepare(deadline)
        validated = owned.validate(prepared, deadline)
        assert validated.prepared is prepared
        assert owned.result["ok"] is True
        assert owned.result["backup_created"] is True
        snapshot = publication / validated.backup_file
        assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == validated.receipt.sha256
        manifest = json.loads(snapshot.with_suffix(".json").read_bytes())
        assert manifest["schema"] == ("PREPARED_SQLITE_CAPTURE_V2" if bounded
                                      else "PREPARED_SQLITE_CAPTURE_V1")
        with closing(sqlite3.connect(snapshot.as_uri() + "?mode=ro", uri=True)) as db:
            assert db.execute("SELECT value FROM auxiliary_owned").fetchall() == [
                ("preserved-owned-value",)]
        for name in ("worker_prepared_receipt", "worker_validation_receipt"):
            record = owned.result[name]
            assert record["schema"] == ("G3_CAPTURE_WORKER_RECEIPT_V2" if bounded
                                       else "G3_CAPTURE_WORKER_RECEIPT_V1")
            if bounded:
                assert record["snapshot_byte_limit"] == limit
            else:
                assert "snapshot_byte_limit" not in record
        if bounded:
            assert manifest["snapshot_byte_limit"] == limit
        else:
            assert "snapshot_byte_limit" not in manifest
        assert source.read_bytes() == before
    finally:
        owned.close()


@native
def test_member_estimate_over_quota_preserves_source_and_denies_recapture(tmp_path):
    source, publication = _owned_database(tmp_path)
    before = source.read_bytes()
    owned = _producer(tmp_path, snapshot_byte_limit=1)
    try:
        with pytest.raises(producer.PreparedSnapshotError):
            owned.prepare(time.monotonic() + 15)
        assert owned.result["prepare_completed"] is False
        assert owned.result["backup_created"] is False
        assert not list(publication.glob("database_*"))
        assert source.read_bytes() == before
        assert list(publication.glob(".*/snapshot.partial")), "retain failed owned capture"
        with pytest.raises(producer.PreparedSnapshotError, match="SECOND_SQLITE_CAPTURE_DENIED"):
            owned.prepare(time.monotonic() + 15)
    finally:
        owned.close()


@native
def test_validation_cannot_downgrade_bounded_capture_receipt(tmp_path):
    _owned_database(tmp_path)
    owned = _producer(tmp_path, snapshot_byte_limit=1024 * 1024)
    deadline = time.monotonic() + 15
    try:
        prepared = owned.prepare(deadline)
        original = owned._worker.prepared_response
        original["schema"] = "G3_CAPTURE_WORKER_RECEIPT_V1"
        original.pop("snapshot_byte_limit")
        with pytest.raises(producer.PreparedSnapshotError):
            owned.validate(prepared, deadline)
        assert owned.result["backup_created"] is False
        assert not list(owned.publication.glob("database_*"))
        assert list(owned.publication.glob(".*/snapshot.partial"))
        with pytest.raises(producer.PreparedSnapshotError,
                           match="FOREIGN_OR_STALE_PREPARED_SQLITE_CAPTURE"):
            owned.validate(prepared, deadline)
    finally:
        owned.close()
