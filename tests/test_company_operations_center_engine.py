import sqlite3

from engines.company_operations_center_engine import _latest_operational_record


def test_latest_operational_record_selects_real_columns() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        'CREATE TABLE "cron_runs" ("status" TEXT, "finished_at" TEXT)'
    )
    connection.executemany(
        'INSERT INTO "cron_runs" ("status", "finished_at") VALUES (?, ?)',
        [
            ("FAILED", "2026-07-26T08:00:00+02:00"),
            ("SUCCESS", "2026-07-26T09:00:00+02:00"),
        ],
    )

    record = _latest_operational_record(connection, ["cron_runs"])

    assert record == {
        "table": "cron_runs",
        "last_at": "2026-07-26T09:00:00+02:00",
        "status": "SUCCESS",
    }
    connection.close()
