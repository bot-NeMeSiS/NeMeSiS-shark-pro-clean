"""Bound provider identity reads without losing transactional observation truth."""
import sqlite3


def test_batch_avoids_one_history_scan_per_fixture(app_module):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("CREATE TABLE matches(id TEXT PRIMARY KEY,external_id TEXT,source TEXT,raw_json TEXT);"
                       "CREATE INDEX source_external ON matches(source,external_id);")
    conn.executemany("INSERT INTO matches VALUES(?,?,?,?)", [
        (f"legacy-{i}", str(i), "TheSportsDB API", "x" * 2048) for i in range(180)
    ])
    batch = [{"id": f"new-{i}", "external_id": str(i)} for i in range(180)]
    old_plan = conn.execute("EXPLAIN QUERY PLAN SELECT * FROM matches WHERE external_id=? "
                            "AND source LIKE 'TheSportsDB%'", ("1",)).fetchall()
    assert any("SCAN" in row[3] for row in old_plan)
    calls = []
    conn.set_trace_callback(calls.append)
    cur = conn.cursor()
    ids = app_module._sportsdb_provider_ids_for_batch(cur, batch)
    for i, item in enumerate(batch):
        found = app_module._sportsdb_existing_provider_rows(cur, item, provider_ids=ids)
        assert [row["id"] for row in found] == [f"legacy-{i}"]
    history_reads = [sql for sql in calls if "external_id IN (" in sql]
    assert len(history_reads) == 1
    assert not any("WHERE external_id=" in sql for sql in calls)
    plan = conn.execute("EXPLAIN QUERY PLAN SELECT * FROM matches WHERE id IN (?) AND external_id=? "
                        "AND source LIKE 'TheSportsDB%'", ("legacy-1", "1")).fetchall()
    assert all("SCAN" not in row[3] for row in plan)
    conn.close()


def test_cached_ids_read_current_transaction_and_reject_changed_identity(app_module):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE matches(id TEXT PRIMARY KEY,external_id TEXT,source TEXT,score TEXT)")
    conn.execute("INSERT INTO matches VALUES('legacy','42','TheSportsDB API','1-0')")
    cur = conn.cursor()
    ids = app_module._sportsdb_provider_ids_for_batch(cur, [{"external_id": "42"}])
    conn.execute("UPDATE matches SET score='2-0' WHERE id='legacy'")
    rows = app_module._sportsdb_existing_provider_rows(cur, {"id":"new","external_id":"42"}, provider_ids=ids)
    assert rows[0]["score"] == "2-0"
    conn.execute("UPDATE matches SET external_id='43' WHERE id='legacy'")
    assert app_module._sportsdb_existing_provider_rows(cur, {"id":"new","external_id":"42"}, provider_ids=ids) == []
    conn.close()


def test_same_event_in_batch_keeps_newer_observation(app_module, monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "batch.sqlite"))
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", None)
    app_module.init_db()
    item = app_module.sportsdb_event_to_match({
        "idEvent":"42", "strSport":"Soccer", "strHomeTeam":"Valencia CF",
        "strAwayTeam":"Real Betis", "strLeague":"La Liga", "dateEvent":app_module.today_iso(),
        "strTime":"20:00:00", "strStatus":"Match Finished", "intHomeScore":"2", "intAwayScore":"0",
    }, provider_observed_at="2026-10-07T22:00:00+02:00")
    newer = dict(item, id="newer")
    older = dict(item, id="older", last_synced_at="2026-10-07T21:00:00+02:00", home_score="1", score="1-0")
    result = app_module.upsert_sportsdb_matches([newer, older])
    assert result["skipped"] == 1
    with sqlite3.connect(app_module.DB_PATH) as conn:
        rows = conn.execute("SELECT id,home_score FROM matches WHERE external_id='42'").fetchall()
    assert rows == [("newer", "2")]
