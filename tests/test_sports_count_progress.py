"""Actual SQLite progress opportunities on owned ordinary tables, not fake clocks."""
from contextlib import closing
import hashlib
import json
import sqlite3
import time

import pytest

from engines import api_exploitation_engine as engine
from engines.cron_request_budget import CronRequestBudget


@pytest.mark.parametrize("interrupt", [False, True, "deadline"])
def test_plain_table_history_count_obeys_original_sqlite_progress_control(tmp_path, monkeypatch, interrupt):
    path = tmp_path / "owned-count.sqlite"
    engine.ensure_api_exploitation_schema(str(path))
    with closing(sqlite3.connect(path)) as c, c:
        c.execute("CREATE TABLE api_football_live_events(id TEXT)")
        c.execute("CREATE TABLE player_profiles(player_id TEXT)")
        c.execute("INSERT INTO api_football_fixture_index(id) VALUES('owned-fixture')")
        c.executemany("INSERT INTO player_profiles VALUES(?)", [(None,), ("",), (" ",), ("own",)])
        c.executemany("INSERT INTO api_football_match_stats_history(id) VALUES(?)",
                      ((f"owned-{i}",) for i in range(30000)))
        c.execute("INSERT INTO api_exploitation_runs(started_at,finished_at,status,payload_json) VALUES(?,?,?,?)",
                  ("2026-10-01T00:00:00+00:00", "2026-10-01T00:00:01+00:00", "OK",
                   json.dumps({"account": {"ok": True, "http_status": 200}, "capabilities": {}})))
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    native_connect = sqlite3.connect
    calls = []
    counter = {"stats_callbacks": 0}

    class ObservedConnection(sqlite3.Connection):
        counting_stats = False

        def execute(self, sql, *args, **kwargs):
            # Identify the supported store; do not assert a chosen SQL spelling
            # or replace the real query, its rows, transaction or VM execution.
            self.counting_stats = sql.startswith(
                "SELECT COUNT(*) AS total FROM api_football_match_stats_history")
            try:
                return super().execute(sql, *args, **kwargs)
            finally:
                self.counting_stats = False

        def set_progress_handler(self, callback, n):
            if callback is None:
                return super().set_progress_handler(None, n)
            def observe():
                if self.counting_stats:
                    counter["stats_callbacks"] += 1
                    # SQLite's native interruption is an injected fault, not a
                    # simulated clock, extra budget or production timing claim.
                    if interrupt == "deadline" and counter["stats_callbacks"] == 1:
                        # Real descheduling inside this owned SQLite callback.
                        # The unchanged caller clock must observe elapsed time.
                        time.sleep(.30)
                    if interrupt is True and counter["stats_callbacks"] >= 2:
                        return 1
                return callback()
            return super().set_progress_handler(observe, n)

    def connect(*args, **kwargs):
        calls.append((args, kwargs))
        return native_connect(*args, **kwargs, factory=ObservedConnection)

    monkeypatch.setattr(engine.sqlite3, "connect", connect)
    with CronRequestBudget(seconds=.5 if interrupt == "deadline" else 5) as budget:
        result = engine.api_exploitation_summary(str(path), budget)
    assert len(calls) == 1 and calls[0][1]["uri"] is True
    assert calls[0][0][0].endswith("?mode=ro")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert result["latest_account"] == {"ok": True, "http_status": 200}
    assert result["sports_read_state"]["account_is_current"] is False
    assert result["persisted_totals"]["fixtures"] == 1
    assert result["persisted_totals"]["players"] == 2
    assert budget.deferred is (interrupt == "deadline")
    if interrupt:
        assert counter["stats_callbacks"] == (1 if interrupt == "deadline" else 2)
        assert result["ok"] is False
        assert result["sports_read_state"]["query_interrupted"] is True
        assert "stats" not in result["persisted_totals"]
        assert "stats" not in {row["capability"] for row in result["continuity"]}
        assert "stats" in result["sports_read_state"]["unknown_capabilities"]
        assert result["sports_read_state"]["state"] != "COMPLETE"
    else:
        assert counter["stats_callbacks"] > 20
        assert result["ok"] is True
        assert result["persisted_totals"]["stats"] == 30000
        assert result["sports_read_state"]["state"] == "COMPLETE"
        assert result["sports_read_state"]["unknown_capabilities"] == []
