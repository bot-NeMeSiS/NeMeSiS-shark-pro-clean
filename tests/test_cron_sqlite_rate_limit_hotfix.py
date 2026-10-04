"""Regression coverage for the October 4 SQLite/Gunicorn Cron incident."""

import sqlite3
from pathlib import Path

import pytest

from tools import render_cron_master_tick as master


def _build_queue_db(path, sent_status, day):
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """CREATE TABLE telegram_queue(
                id TEXT PRIMARY KEY,
                chat_id TEXT,
                message_type TEXT,
                status TEXT,
                sent_at TEXT
            )"""
        )
        conn.executemany(
            "INSERT INTO telegram_queue(id,chat_id,message_type,status,sent_at) VALUES(?,?,?,?,?)",
            [
                ("1", "chat-a", "daily_matches", sent_status, f"{day}T09:30:00+02:00"),
                ("2", "chat-a", "auto_pick", sent_status, f"{day}T10:00:00+02:00"),
                ("3", "chat-b", "daily_matches", sent_status, f"{day}T10:15:00+02:00"),
                ("4", "chat-a", "daily_matches", "pending", f"{day}T10:30:00+02:00"),
                ("5", "chat-a", "daily_matches", sent_status, "2026-09-01T10:00:00+02:00"),
            ],
        )
        conn.commit()
    finally:
        conn.close()


def test_telegram_daily_limit_count_uses_persistent_read_only_path(app_module, tmp_path, monkeypatch):
    app = app_module
    path = tmp_path / "queue.sqlite"
    day = app.today_iso()
    _build_queue_db(path, app.QUEUE_SENT, day)
    monkeypatch.setattr(app, "DB_PATH", str(path))

    assert app.telegram_sent_today("chat-a") == 2
    assert app.telegram_sent_today("chat-b") == 1
    assert app.telegram_sent_today() == 3
    assert app.telegram_sent_today("chat-a", "auto_pick") == 1


def test_telegram_rate_limit_read_fails_closed_without_waiting_for_global_sqlite_timeout(app_module, tmp_path, monkeypatch):
    app = app_module
    path = tmp_path / "queue.sqlite"
    path.write_bytes(b"sqlite-placeholder")
    monkeypatch.setattr(app, "DB_PATH", str(path))
    seen = {}

    def locked_connect(*args, **kwargs):
        seen["timeout"] = kwargs.get("timeout")
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(app.sqlite3, "connect", locked_connect)
    monkeypatch.setenv("TELEGRAM_RATE_LIMIT_READ_TIMEOUT_MS", "1200")

    assert app.telegram_sent_today("chat-a") == app.TELEGRAM_QUEUE_RATE_LIMIT_FAILSAFE_COUNT
    assert app.telegram_sent_last_hour("chat-a") == app.TELEGRAM_QUEUE_RATE_LIMIT_FAILSAFE_COUNT
    assert 0 < seen["timeout"] <= 3.0


def test_telegram_rate_limit_queries_have_supporting_indexes():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "idx_telegram_queue_sent_at ON telegram_queue(status, sent_at)" in source
    assert "idx_telegram_queue_chat_sent_at ON telegram_queue(chat_id, status, sent_at)" in source
    assert "TELEGRAM_RATE_LIMIT_READ_TIMEOUT_MS" in source
    assert "TELEGRAM_QUEUE_RATE_LIMIT_FAILSAFE_COUNT" in source


@pytest.mark.parametrize(
    ("status", "expected"),
    [("PASS", 0), ("PARTIAL", 0), ("FAIL", 2), ("UNKNOWN", 0)],
)
def test_render_cron_exit_code_only_fails_technical_fail(status, expected):
    assert master.exit_code_for_overall(status) == expected
