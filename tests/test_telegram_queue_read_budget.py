"""Regression coverage for Telegram queue SQLite worker-timeout protection."""

import sqlite3
from pathlib import Path


def test_queue_loader_keeps_status_index_usable():
    root = Path(__file__).resolve().parents[1]
    source = (root / "app.py").read_text(encoding="utf-8")
    start = source.index("def _telegram_queue_pending_rows")
    end = source.index("\n\ndef process_premium_telegram_queue", start)
    block = source[start:end]

    assert "lower(status)" not in block
    assert "status IN (?,?,?,?)" in block
    assert "QUEUE_PENDING.upper()" in block
    assert "QUEUE_FAILED.upper()" in block
    assert "TELEGRAM_QUEUE_READ_TIMEOUT_MS" in block
    assert "set_progress_handler" in block
    assert "idx_telegram_queue_status" in block


def test_queue_loader_reads_due_lower_and_legacy_uppercase_rows(app_module, tmp_path, monkeypatch):
    db_path = tmp_path / "telegram-queue.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """CREATE TABLE telegram_queue(
                id TEXT PRIMARY KEY,
                status TEXT,
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                scheduled_at TEXT,
                priority INTEGER DEFAULT 50,
                created_at TEXT
            )"""
        )
        conn.execute(
            "CREATE INDEX idx_telegram_queue_status ON telegram_queue(status, scheduled_at)"
        )
        rows = [
            ("p-lower", "pending", 0, 3, "", 90, "2026-09-29T18:00:00+02:00"),
            ("p-upper", "PENDING", 0, 3, "", 80, "2026-09-29T18:01:00+02:00"),
            ("f-lower", "failed", 1, 3, "2026-09-29T19:00:00+02:00", 70, "2026-09-29T18:02:00+02:00"),
            ("future", "pending", 0, 3, "2099-01-01T00:00:00+02:00", 99, "2026-09-29T18:03:00+02:00"),
            ("sent", "sent", 0, 3, "", 100, "2026-09-29T18:04:00+02:00"),
        ]
        conn.executemany(
            "INSERT INTO telegram_queue(id,status,attempts,max_attempts,scheduled_at,priority,created_at) VALUES (?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(app_module, "DB_PATH", str(db_path))
    monkeypatch.setenv("TELEGRAM_QUEUE_READ_TIMEOUT_MS", "500")

    loaded = app_module._telegram_queue_pending_rows(
        limit=10,
        current="2026-09-29T20:00:00+02:00",
    )

    assert [item["id"] for item in loaded] == ["p-lower", "p-upper", "f-lower"]


def test_queue_loader_treats_sqlite_busy_as_retryable(app_module, tmp_path, monkeypatch):
    db_path = tmp_path / "telegram-queue.db"
    db_path.write_bytes(b"sqlite-placeholder")
    monkeypatch.setattr(app_module, "DB_PATH", str(db_path))

    def busy_connect(*_args, **_kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(app_module.sqlite3, "connect", busy_connect)

    assert app_module._telegram_queue_pending_rows(limit=5) is None


def test_queue_busy_does_not_fail_the_whole_cron_tick(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "get_telegram_settings", lambda: {"enabled": True})
    monkeypatch.setattr(app_module, "telegram_env_should_enable", lambda: True)
    monkeypatch.setattr(app_module, "telegram_pro_calibration", lambda: {"max_queue_per_tick": 5})
    monkeypatch.setattr(app_module, "_telegram_queue_pending_rows", lambda **_kwargs: None)

    result = app_module.process_premium_telegram_queue(limit=5)

    assert result["ok"] is True
    assert result["status"] == "QUEUE_DB_BUSY_RETRY"
    assert result["failed"] == 0
    assert result["sent"] == 0
    assert result["skipped"] == 1
    assert result["errors"] == []
