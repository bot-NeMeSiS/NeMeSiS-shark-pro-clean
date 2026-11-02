"""Impossible calendar dates must remain unresolved without aborting consumers."""
from datetime import datetime
import sqlite3

import pytest

from engines import madrid_time_engine as clock
from engines.spanish_localization_engine import madrid_values_from_datetime


@pytest.mark.parametrize("parser", [clock.parse_match_datetime, clock.parse_madrid_local_datetime])
@pytest.mark.parametrize("value", [
    "2026-02-30", "2026-02-29", "2026-13-01", "2026-00-01",
    "2026-01-00", "0000-12-01", "1900-02-29", "２０２６-０２-３０",
])
def test_impossible_bare_dates_are_unresolved_like_invalid_datetime_strings(parser, value):
    assert parser(value + "T00:00:00") is None
    assert parser(value) is None


@pytest.mark.parametrize("value,madrid", [
    ("2024-02-29", "2024-02-29T00:00:00+01:00"),
    ("2000-02-29", "2000-02-29T00:00:00+01:00"),
    ("2026-07-15", "2026-07-15T00:00:00+02:00"),
    ("2026-03-29", "2026-03-29T00:00:00+01:00"),
    ("2026-10-25", "2026-10-25T00:00:00+02:00"),
])
def test_valid_bare_dates_keep_manual_madrid_and_api_utc_contracts(value, madrid):
    assert clock.parse_madrid_local_datetime(value).isoformat() == madrid
    assert clock.parse_match_datetime(value).isoformat() == value + "T00:00:00+00:00"


def test_naive_datetimes_still_have_distinct_manual_and_provider_meanings():
    value = datetime(2026, 7, 15, 21, 30)
    assert clock.parse_madrid_local_datetime(value).isoformat() == "2026-07-15T21:30:00+02:00"
    assert clock.parse_match_datetime(value).isoformat() == "2026-07-15T21:30:00+00:00"


def test_existing_valid_fallback_resolves_an_invalid_primary_without_double_shift():
    result = madrid_values_from_datetime("2026-02-30", "2026-07-16", "00:30")
    assert (result["match_date"], result["kickoff_time"], result["kickoff_iso"]) == (
        "2026-07-16", "00:30", "2026-07-16T00:30:00+02:00"
    )


def test_invalid_primary_without_valid_fallback_does_not_invent_an_instant():
    result = madrid_values_from_datetime("2026-02-30")
    assert result["match_date"] == result["kickoff_time"] == result["safe_datetime"] == ""
    assert result["kickoff_iso"] == "2026-02-30"
    item = {"id": "owned-invalid", "kickoff_iso": "2026-02-30", "status": "NS"}
    assert clock.normalize_kickoff_for_display(item)["display_datetime"] == "Hora pendiente"
    assert clock.format_telegram_match_time_madrid(item)["iso_madrid"] == ""
    assert item == {"id": "owned-invalid", "kickoff_iso": "2026-02-30", "status": "NS"}


def test_an_invalid_fallback_is_not_promoted_to_a_canonical_instant():
    result = madrid_values_from_datetime("2026-02-30", "2026-13-01", "25:99")
    assert result["safe_datetime"] == ""
    assert result["kickoff_iso"] == "2026-02-30"
    assert (result["match_date"], result["kickoff_time"]) == ("2026-13-01", "25:99")


def test_actual_calendar_label_uses_its_existing_unresolved_branch(app_module):
    with app_module.app.test_request_context("/calendario"):
        assert app_module.ui_calendar_date("2026-02-30") == app_module.ui_text("Fecha pendiente")
        assert app_module.ui_calendar_date("2024-02-29", detail=True) != app_module.ui_text("Fecha pendiente")


def _connection(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE matches(
        id TEXT PRIMARY KEY, kickoff_iso TEXT, match_date TEXT, kickoff_time TEXT,
        match_time TEXT, updated_at TEXT, source TEXT, provider_updated_at TEXT, raw_json TEXT
    )""")
    conn.execute("CREATE TABLE automation_state(key TEXT PRIMARY KEY,value_json TEXT,updated_at TEXT)")
    return conn


def _insert(conn, key, iso, day, hour, alias, order):
    conn.execute("INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?)", (
        key, iso, day, hour, alias, order, "owned-provider", "2026-07-15T23:00:00Z",
        '{"owned":"preserved"}',
    ))


def _rows(conn):
    return [tuple(row) for row in conn.execute("SELECT * FROM matches ORDER BY id")]


def test_real_startup_continues_after_invalid_date_and_remains_caller_transactional(
    app_module, tmp_path
):
    path = tmp_path / "OWNED_INVALID_DATE.sqlite"
    conn = _connection(path)
    _insert(conn, "invalid", "2026-02-30", "", "", "", "2026-07-17")
    _insert(conn, "convert", "2026-07-15T23:30:00Z", "2026-07-15", "23:30", "23:30", "2026-07-16")
    conn.commit()
    before = _rows(conn)
    try:
        assert app_module.normalize_existing_match_times_to_madrid(conn) == 1
        after = {row["id"]: dict(row) for row in conn.execute("SELECT * FROM matches")}
        assert tuple(after["invalid"].values()) == before[1]
        assert (after["convert"]["match_date"], after["convert"]["kickoff_time"],
                after["convert"]["match_time"], after["convert"]["kickoff_iso"]) == (
            "2026-07-16", "01:30", "01:30", "2026-07-16T01:30:00+02:00"
        )
        for field in ("source", "provider_updated_at", "raw_json"):
            assert after["convert"][field] == dict(zip(after["convert"], before[0]))[field]
        assert after["convert"]["updated_at"] != before[0][5]
        assert datetime.fromisoformat(after["convert"]["updated_at"]).tzinfo is not None
        receipt = conn.execute("SELECT value_json FROM automation_state").fetchone()
        import json
        assert json.loads(receipt[0])["changed"] == 1
        assert conn.in_transaction is True
        with sqlite3.connect(path) as other:
            assert other.execute("SELECT match_date FROM matches WHERE id='convert'").fetchone()[0] == "2026-07-15"
        conn.rollback()
        assert _rows(conn) == before
        assert conn.execute("SELECT count(*) FROM automation_state").fetchone()[0] == 0
    finally:
        conn.close()


def test_real_startup_keeps_the_existing_limit_and_alias_no_change_contract(app_module, tmp_path):
    conn = _connection(tmp_path / "OWNED_COHORT_DATE.sqlite")
    _insert(conn, "recent", "2026-07-16T00:30:00+02:00", "2026-07-16", "00:30", "12:00", "2026-07-17")
    _insert(conn, "older", "2026-07-15T23:30:00Z", "2026-07-15", "23:30", "23:30", "2026-07-15")
    conn.commit()
    before = _rows(conn)
    try:
        assert app_module.normalize_existing_match_times_to_madrid(conn, limit=1) == 0
        assert _rows(conn) == before
        assert conn.execute("SELECT count(*) FROM automation_state").fetchone()[0] == 0
        assert app_module.normalize_existing_match_times_to_madrid(conn, limit=2) == 1
        conn.commit()
        normalized = _rows(conn)
        assert app_module.normalize_existing_match_times_to_madrid(conn, limit=2) == 0
        assert _rows(conn) == normalized
        assert conn.execute("SELECT match_time FROM matches WHERE id='recent'").fetchone()[0] == "12:00"
    finally:
        conn.close()

