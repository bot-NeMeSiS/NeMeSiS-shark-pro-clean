"""No fake always-on workers: only last locally persisted master tick is reported."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import sqlite3

from engines.company_workforce_receipts_engine import master_cron_receipt


NOW = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)


def make_db(tmp_path, payload):
    path = tmp_path / "cron-receipt.sqlite"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE automation_state("
                     "key TEXT PRIMARY KEY,value_json TEXT,updated_at TEXT)")
        if payload is not None:
            conn.execute("INSERT INTO automation_state VALUES(?,?,?)",
                         ("telegram_tick_last_detail", payload, NOW.isoformat()))
    return path


def test_persisted_recent_receipt_is_readonly_not_all_worker_certification(tmp_path):
    value = {"finished_at": (NOW - timedelta(minutes=8)).isoformat(),
             "compact": {"private_user": "CANARY_NOT_IN_RESULT"}}
    path = make_db(tmp_path, json.dumps(value))
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    state = master_cron_receipt(path, now=NOW)
    assert state["state"] == "RECENT_RECEIPT"
    assert state["age_minutes"] == 8
    assert state["last_observed_madrid"].endswith("+01:00")
    assert state["workers_certified_24x7"] is False
    assert state["database_writes"] == state["external_calls"] == 0
    assert "CANARY_NOT_IN_RESULT" not in str(state)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_missing_and_invalid_payloads_never_claim_success(tmp_path):
    absent = tmp_path / "absent.sqlite"
    assert master_cron_receipt(absent, now=NOW)["state"] == "NO_EVIDENCE"
    assert not absent.exists()
    none = make_db(tmp_path, None)
    assert master_cron_receipt(none, now=NOW)["state"] == "NO_EVIDENCE"


def test_stale_future_unknown_and_corrupt_receipts(tmp_path):
    path = make_db(tmp_path, json.dumps({"finished_at": (NOW - timedelta(minutes=20)).isoformat()}))
    assert master_cron_receipt(path, now=NOW)["state"] == "STALE_RECEIPT"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE automation_state SET value_json=?",
                     (json.dumps({"finished_at": (NOW + timedelta(hours=2)).isoformat()}),))
    assert master_cron_receipt(path, now=NOW)["state"] == "CLOCK_UNVERIFIED"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE automation_state SET value_json=?", ("not-json",))
    assert master_cron_receipt(path, now=NOW)["state"] == "READ_UNAVAILABLE"


def read_and_verify_connection_closed(path, *, fail_query=False):
    """Observe the real SQLite resource after a successful or failed read."""
    connect = sqlite3.connect
    opened = []

    class TrackedConnection(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if fail_query and sql.startswith("SELECT value_json"):
                raise sqlite3.OperationalError("Synthetic read failure")
            return super().execute(sql, parameters)

    def track_connect(*args, **kwargs):
        conn = connect(*args, factory=TrackedConnection, **kwargs)
        opened.append(conn)
        return conn

    try:
        with patch("engines.company_workforce_receipts_engine.sqlite3.connect", side_effect=track_connect):
            state = master_cron_receipt(path, now=NOW)
        assert len(opened) == 1
        try:
            opened[0].execute("SELECT 1")
        except sqlite3.ProgrammingError as exc:
            assert "closed" in str(exc).lower()
        else:
            raise AssertionError("Receipt read left its SQLite connection usable")
        return state
    finally:
        # Also release resources when exercising the unfixed negative control.
        for conn in opened:
            conn.close()


def test_receipt_connection_is_closed_after_success(tmp_path):
    path = make_db(tmp_path, json.dumps({"finished_at": NOW.isoformat()}))
    before = path.read_bytes()
    state = read_and_verify_connection_closed(path)
    assert state["state"] == "RECENT_RECEIPT"
    assert state["workers_certified_24x7"] is False
    assert path.read_bytes() == before


def test_receipt_connection_is_closed_after_sqlite_failure(tmp_path):
    path = make_db(tmp_path, json.dumps({"finished_at": NOW.isoformat()}))
    before = path.read_bytes()
    state = read_and_verify_connection_closed(path, fail_query=True)
    assert state["state"] == "READ_UNAVAILABLE"
    assert state["database_writes"] == state["external_calls"] == 0
    assert path.read_bytes() == before


def test_receipt_connection_is_closed_after_missing_receipt(tmp_path):
    path = make_db(tmp_path, None)
    before = path.read_bytes()
    state = read_and_verify_connection_closed(path)
    assert state["state"] == "NO_EVIDENCE"
    assert path.read_bytes() == before
