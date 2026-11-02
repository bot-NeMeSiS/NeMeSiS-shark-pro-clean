"""Real SQL work and request-local finalization observations, without providers."""
import json
import sqlite3
from types import SimpleNamespace

import pytest

from engines import api_exploitation_engine as exploitation
from engines import closed_operation_timing as timing


def test_summary_exact_counts_keep_filtered_identities_without_rowwise_count(tmp_path, monkeypatch):
    path = str(tmp_path / "owned-summary.sqlite")
    exploitation.ensure_api_exploitation_schema(path)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE player_profiles(player_id TEXT)")
        conn.executemany("INSERT INTO player_profiles VALUES(?)", [(None,), ("",), ("own-player",), (" ",)])
        conn.executemany("INSERT INTO api_football_match_stats_history(id) VALUES(?)",
                         ((f"own-{i}",) for i in range(30000)))
        conn.execute("INSERT INTO api_football_fixture_index(id,fixture_id) VALUES('own-index','own-fixture')")
    native_connect = exploitation._connect
    work = []

    class ObservedConnection(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            self.set_progress_handler(None, 0)
            if sql.startswith("SELECT COUNT(*) AS total FROM api_football_match_stats_history"):
                counter = [0]
                work.append(counter)
                def observe():
                    counter[0] += 1
                    return 0
                self.set_progress_handler(observe, 1000)
            return super().execute(sql, parameters)

    def observed_connect(db_path):
        conn = sqlite3.connect(db_path, factory=ObservedConnection)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(exploitation, "_connect", observed_connect)
    summary = exploitation.api_exploitation_summary(path)
    assert summary["stats_total"] == 30000
    assert summary["player_profiles_total"] == 2
    assert summary["fixtures_indexed"] == 1
    assert summary["lineups_total"] == 0
    assert {row["capability"]: row["persisted"] for row in summary["continuity"]}["stats"] == 30000
    # The previous tautological WHERE performs >60k VM steps on this same data.
    # This is a deterministic work guard, not a machine-dependent latency claim.
    assert work and max(counter[0] for counter in work) < 10
    with native_connect(path) as conn:
        conn.execute("INSERT INTO api_football_match_stats_history(id) VALUES('own-added')")
    assert exploitation.api_exploitation_summary(path)["stats_total"] == 30001


@pytest.mark.parametrize("failure_point", ["operation_clock", "trace_id", "phase_start", "phase_end"])
@pytest.mark.parametrize("business_fails", [False, True])
def test_observer_failure_preserves_result_or_original_exception(monkeypatch, failure_point, business_fails):
    def unavailable(*args):
        raise OSError("observation unavailable")
    problem = ValueError("private business payload")
    answer = object()

    @timing.operation("sports_sync")
    def run():
        if failure_point == "phase_start":
            monkeypatch.setattr(timing, "time", SimpleNamespace(monotonic=unavailable))
        with timing.phase("sports_sync", "exploitation_summary"):
            if failure_point == "phase_end":
                monkeypatch.setattr(timing, "time", SimpleNamespace(monotonic=unavailable))
            if business_fails:
                raise problem
            return answer

    if failure_point == "operation_clock":
        monkeypatch.setattr(timing, "time", SimpleNamespace(monotonic=unavailable))
    if failure_point == "trace_id":
        monkeypatch.setattr(timing, "secrets", SimpleNamespace(token_hex=unavailable))
    if business_fails:
        with pytest.raises(ValueError) as caught:
            run()
        assert caught.value is problem
    else:
        assert run() is answer
    assert timing.trace_id("sports_sync") is None


@pytest.mark.parametrize("history_fails", [False, True])
def test_real_sports_post_reports_tail_delay_without_changing_result(client, app_module, monkeypatch, capsys, history_fails):
    clock = [0.0]
    monkeypatch.setattr(timing, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setenv("AUTOMATION_SECRET", "owned-sports-finalization-test")
    monkeypatch.setattr(app_module, "sports_sync_window_state", lambda: {"live_refresh_required": False})
    monkeypatch.setattr(app_module, "sync_api_football_match_window", lambda *a, **k: {
        "ok": True, "status": "OK", "fixtures_count": 1, "external_calls": 0})
    monkeypatch.setattr(app_module, "refresh_api_football_statistics_if_due", lambda *a, **k: {
        "ok": True, "status": "SKIPPED_NOT_DUE", "external_calls": 0})
    monkeypatch.setattr(app_module, "_api_football_deep_enrichment_candidates", lambda **k: [])
    monkeypatch.setattr(app_module, "run_api_exploitation_if_due", lambda *a, **k: {
        "ok": True, "status": "SKIPPED_NOT_DUE", "external_calls": 0})
    monkeypatch.setattr(app_module, "run_pick_grading", lambda *a, **k: {"ok": True, "picks_checked": 0})
    calls = []
    def history(*args):
        calls.append("history")
        clock[0] += 2.0
        if history_fails:
            raise RuntimeError("PRIVATE_PROVIDER_ERROR_NEVER_LOG")
        return {}
    monkeypatch.setattr(app_module, "api_exploitation_summary", history)
    response = client.post("/api/automation/sports/sync", headers={
        "X-Automation-Secret": "owned-sports-finalization-test",
        "X-NeMeSiS-Cron-Runner": "render-cron"})
    assert response.status_code == 200
    assert response.get_json()["processed"] == 1
    assert calls == ["history"]
    text = capsys.readouterr().out
    assert "PRIVATE_PROVIDER_ERROR_NEVER_LOG" not in text
    records = []
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(record, dict) and record.get("domain") == "sports_sync":
            records.append(record)
    assert records
    assert {r["phase"] for r in records} == timing.PHASES["sports_sync"]
    assert len({r["trace"] for r in records}) == 1
    assert len(records) == 20
    history_end = [r for r in records if r["phase"] == "exploitation_summary" and r["point"] == "end"]
    assert len(history_end) == 1 and history_end[0]["duration_ms"] == 2000
    assert history_end[0]["error"] == ("ERROR" if history_fails else None)
    assert all(set(r) == {"event", "domain", "trace", "parent", "phase", "point", "duration_ms",
                           "offset_ms", "in_transaction", "error", "dropped_records"} for r in records)
    assert timing.trace_id("sports_sync") is None


def test_new_sports_phases_stay_silent_without_its_operation(capsys):
    with timing.phase("sports_sync", "cron_detail_state"):
        pass
    assert not capsys.readouterr().out
