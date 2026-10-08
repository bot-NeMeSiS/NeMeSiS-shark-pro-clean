"""Offline startup regressions: identical data rules, less repeated work."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from engines.cron_request_budget import CronRequestBudget, request_timeout


@pytest.mark.parametrize("row_factory", [None, sqlite3.Row])
def test_cleanup_keeps_unicode_predicate_and_transaction(app_module, row_factory):
    app = app_module
    conn = sqlite3.connect(":memory:")
    conn.row_factory = row_factory
    conn.execute("CREATE TABLE matches(id TEXT, home_team TEXT, away_team TEXT, source TEXT)")
    fake = sorted(app.FAKE_TEAM_NAMES)[0]
    samples = [
        ("real", "Real Madrid", "FC Barcelona", "sportsdb"),
        ("null", None, None, None),
        ("unicode-real", "Málaga CF", "Córdoba CF", "API legal"),
        ("fake-home", "  " + fake.upper() + "  ", "Real Madrid", "sportsdb"),
        ("fake-away", "Real Madrid", fake, None),
        ("seed", "Real Madrid", "FC Barcelona", " SÉED\t ESTRUCTURAL "),
    ]
    conn.executemany("INSERT INTO matches VALUES (?,?,?,?)", samples)
    conn.commit()
    expected = [r[0] for r in samples if not (
        app.is_fake_team_name(r[1]) or app.is_fake_team_name(r[2])
        or app.normalized_label(r[3]) == "seed estructural")]
    assert app.cleanup_fake_matches(conn.cursor()) == len(samples) - len(expected)
    assert [r[0] for r in conn.execute("SELECT id FROM matches")] == expected
    conn.rollback()
    assert conn.execute("SELECT count(*) FROM matches").fetchone()[0] == len(samples)
    conn.close()


def test_repeated_names_are_normalized_once_per_cleanup(app_module, monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE matches(id TEXT, home_team TEXT, away_team TEXT, source TEXT)")
    conn.executemany("INSERT INTO matches VALUES (?,?,?,?)",
                     ((str(i), "Real Madrid", "FC Barcelona", "sportsdb") for i in range(20000)))
    calls = []
    original = app_module.normalized_label
    monkeypatch.setattr(app_module, "normalized_label", lambda value: calls.append(value) or original(value))
    assert app_module.cleanup_fake_matches(conn.cursor()) == 0
    assert len(calls) == 3
    # Each invocation gets a fresh cache: a changed predicate is not stale.
    monkeypatch.setattr(app_module, "FAKE_TEAM_NAMES", {"real madrid"})
    assert app_module.cleanup_fake_matches(conn.cursor()) == 20000
    assert len(calls) == 4
    conn.close()


def test_seed_scans_catalog_once_and_preserves_real_fixtures(app_module, tmp_path, monkeypatch):
    app = app_module
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "synthetic.sqlite"))
    app.init_db()
    conn = app.db()
    conn.execute("INSERT INTO matches(id,match_date,home_team,away_team,source) VALUES ('real','2026-10-08','Real Madrid','FC Barcelona','sportsdb')")
    conn.commit()
    conn.close()
    calls = []
    original = app.cleanup_fake_matches
    monkeypatch.setattr(app, "cleanup_fake_matches", lambda cur: calls.append(1) or original(cur))
    app._seed_core_unlocked()
    assert calls == [1]
    with sqlite3.connect(app.DB_PATH) as conn:
        assert conn.execute("SELECT count(*) FROM matches WHERE id='real'").fetchone()[0] == 1


def test_concurrent_first_requests_share_initialization(app_module, monkeypatch):
    app = app_module
    monkeypatch.setattr(app, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(app, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(app, "APP_INITIALIZED", False)
    entered, release = Event(), Event()
    calls = []
    def initialize():
        calls.append(1)
        entered.set()
        assert release.wait(3)
    monkeypatch.setattr(app, "_seed_core_unlocked", initialize)
    monkeypatch.setattr(app, "_telegram_sync_env_on_startup", lambda: None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(app.initialize_once)
        try:
            assert entered.wait(3)
            second = pool.submit(app.initialize_once)
        finally:
            release.set()
        assert first.result(timeout=3) and second.result(timeout=3)
    assert calls == [1]


@pytest.mark.parametrize("spent,expected", [(0, 16), (5, 11), (19, 0)])
def test_setup_time_counts_without_affecting_later_requests(app_module, monkeypatch, spent, expected):
    app = app_module
    now = [100.0]
    monkeypatch.setattr(app.time, "monotonic", lambda: now[0])
    observed = []
    def cycle(**kwargs):
        # A large nested default cannot restart the request's deadline.
        with CronRequestBudget(seconds=60) as inner:
            observed.append(inner.remaining())
        return {"ok": True, "status": "OK", "processed": 3}
    monkeypatch.setattr(app, "run_sports_sync_cycle", cycle)
    monkeypatch.setattr(app, "api_exploitation_summary", lambda *a: {})
    monkeypatch.setattr(app, "_build_sports_pipeline_diagnostics", lambda *a: {})
    with app.app.test_request_context("/api/automation/sports/sync", method="POST"):
        app.v935_begin_route_budget_measurement()
        now[0] += spent
        result = app.bounded_sports_sync()
    if expected:
        assert observed == [expected]
        assert result["processed"] == 3
    else:
        assert observed == []
        assert result["status"] == "PARTIAL" and result["skipped"]
        assert result["processed"] == result["external_calls"] == 0
        assert result["controlled_deferrals"] == ["TIME_BUDGET"]
    assert request_timeout(30) == 30
    with app.app.test_request_context("/api/automation/sports/sync", method="POST"):
        app.v935_begin_route_budget_measurement()
        assert app.bounded_sports_sync()["processed"] == 3
    assert observed[-1] == 16


def test_failed_initialization_is_not_a_successful_deferral(app_module, monkeypatch):
    app = app_module
    monkeypatch.setattr(app, "seed_core", lambda: (_ for _ in ()).throw(RuntimeError("synthetic initialization failure")))
    monkeypatch.setattr(app, "automation_safe_set", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(app, "safe_memory_call", lambda *a, **k: {})
    monkeypatch.setattr(app, "bounded_sports_sync", lambda **k: pytest.fail("runner after failed initialization"))
    with app.app.test_request_context("/api/automation/sports/sync", method="POST"):
        response, status = app.automation_cron_result("sports_sync", (), app.bounded_sports_sync)
    assert status == 200
    assert response.get_json()["ok"] is False
    assert response.get_json()["error"] == "cron_execution_error"


def test_cold_authenticated_http_request_defers_then_next_tick_runs(app_module, tmp_path, monkeypatch):
    app = app_module
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "http.sqlite"))
    app.init_db()
    monkeypatch.setenv("AUTOMATION_SECRET", "synthetic-startup-boundary")
    now = [100.0]
    monkeypatch.setattr(app.time, "monotonic", lambda: now[0])
    initialized = []
    def cold_once():
        if not initialized:
            now[0] += 19
            initialized.append(True)
        return True
    monkeypatch.setattr(app, "initialize_once", cold_once)
    monkeypatch.setattr(app, "seed_core", lambda: None)
    monkeypatch.setattr(app, "automation_safe_set", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(app, "safe_memory_call", lambda *a, **k: {})
    monkeypatch.setattr(app, "api_exploitation_summary", lambda *a: {})
    monkeypatch.setattr(app, "_build_sports_pipeline_diagnostics", lambda *a: {})
    calls = []
    monkeypatch.setattr(app, "run_sports_sync_cycle", lambda **k: calls.append(1) or {
        "ok": True, "status": "OK", "processed": 3, "external_calls": 0})
    client = app.app.test_client()
    headers = {"X-Automation-Secret": "synthetic-startup-boundary"}
    cold = client.post("/api/automation/sports/sync", headers=headers)
    assert cold.status_code == 200
    payload = cold.get_json()
    assert payload["status"] == "PARTIAL" and payload["processed"] == 0
    assert payload["controlled_deferrals"] == ["TIME_BUDGET"]
    assert calls == []
    warm = client.post("/api/automation/sports/sync", headers=headers)
    assert warm.status_code == 200 and warm.get_json()["processed"] == 3
    assert calls == [1]


def test_startup_stage_logs_only_safe_label_and_duration_even_on_failure(app_module, capsys):
    app = app_module
    with app.app.test_request_context("/api/automation/sports/sync", method="POST"):
        with pytest.raises(ValueError):
            app._startup_step("startup_schema", lambda: (_ for _ in ()).throw(ValueError("private-value")))
        app._startup_step("unknown-secret-label", lambda: None)
    output = capsys.readouterr().out
    assert "private-value" not in output and "unknown-secret-label" not in output
    log = json.loads(output)
    assert log["stage"] == "startup_schema" and log["duration_ms"] >= 0
