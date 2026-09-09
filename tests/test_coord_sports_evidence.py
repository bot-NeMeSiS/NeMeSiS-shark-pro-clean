"""SE-01 regressions; all match data here is SIMULATED_QA."""
import sqlite3
import copy
import hashlib
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest

from engines import shark_historical_intelligence_engine as history
from engines.match_context_engine import build_match_context
from services.sports_service import observe_persisted_match
from engines.sports_domain_model_engine import normalize_match_entity


def sample(status="LIVE", age=600):
    now = datetime.now(timezone.utc)
    return {
        "id": "qa-se-match", "external_id": "qa-se-provider",
        "source": "sportsdb", "home_team": "QA Home", "away_team": "QA Away",
        "competition_id": "4335", "competition_name": "Spanish La Liga",
        "season": "2026-2027", "status": status, "minute": "67",
        "home_score": 0, "away_score": 0,
        "kickoff_iso": (now - timedelta(hours=1)).isoformat(),
        "last_synced_at": (now - timedelta(seconds=age)).isoformat(),
    }


def test_stale_summary_does_not_claim_scheduled_or_current_score():
    context = build_match_context({"match": sample()})
    assert context["lifecycle"]["is_stale"]
    text = context["summaries"]["items"][0]["text"].lower()
    assert "programado" not in text
    assert "no est" in text and "confirmada" in text
    assert "ltimo marcador conocido: 0-0" in text
    assert context["lifecycle"]["minute"] is None


@pytest.mark.parametrize("status,age,live", [
    ("LIVE", 20, True), ("HT", 20, True), ("LIVE", 600, False),
    ("LIVE", -900, False), ("FT", 600, False), ("POSTPONED", 20, False),
])
def test_summary_keeps_canonical_live_truth(status, age, live):
    context = build_match_context({"match": sample(status, age)})
    assert context["lifecycle"]["is_live"] is live
    if not live:
        assert context["lifecycle"]["minute"] is None
    if context["lifecycle"]["is_stale"]:
        assert context["summaries"]["current_type"] == "STALE_SUMMARY"


@pytest.fixture
def historical_db(monkeypatch):
    class MemoryConnection(sqlite3.Connection):
        def close(self):
            pass

    conn = sqlite3.connect(":memory:", factory=MemoryConnection)
    conn.row_factory = sqlite3.Row
    monkeypatch.setattr(history, "_connect", lambda _path: conn)
    history.ensure_historical_intelligence_schema(":memory:")
    conn.execute("""CREATE TABLE football_matches_history (
        id TEXT, external_id TEXT, provider TEXT, status TEXT,
        home_score INTEGER, away_score INTEGER, home_team TEXT, away_team TEXT,
        league_name TEXT, season TEXT, last_seen_at TEXT, kickoff_iso TEXT,
        match_date TEXT, first_seen_at TEXT)""")
    yield conn
    sqlite3.Connection.close(conn)


@pytest.mark.parametrize("home,away,status,winner,total", [
    (None, None, "FT", "pending", None),
    (1, None, "FT", "pending", None),
    (None, 0, "FT", "pending", None),
    (0, 0, "FT", "draw", 0),
    (2, 1, "FT", "home", 3),
    (0, 1, "LIVE", "pending", None),
])
def test_historical_missing_scores_never_become_results(historical_db, home, away, status, winner, total):
    conn = historical_db
    conn.execute("""INSERT INTO football_matches_history
        (id,external_id,provider,status,home_score,away_score,home_team,away_team,league_name,season)
        VALUES ('qa-1','qa-1','sportsdb',?,?,?,'QA Home','QA Away','QA League','2026')""", (status, home, away))
    history._build_match_facts(conn, 10)
    row = dict(conn.execute("SELECT * FROM shark_historical_match_facts").fetchone())
    assert (row["home_score"], row["away_score"]) == (home, away)
    assert (row["winner"], row["total_goals"]) == (winner, total)
    history._rebuild_team_form(conn)
    history._rebuild_league_profiles(conn)
    if winner == "pending":
        assert conn.execute("SELECT COUNT(*) FROM shark_historical_team_form").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM shark_historical_league_profile").fetchone()[0] == 0


def test_correction_to_unknown_removes_only_derived_certainty(historical_db):
    conn = historical_db
    conn.execute("""INSERT INTO football_matches_history
        (id,external_id,provider,status,home_score,away_score,home_team,away_team,league_name,season)
        VALUES ('qa-1','qa-1','sportsdb','FT',0,0,'QA Home','QA Away','QA League','2026')""")
    for home, away in [(0, 0), (2, 1), (None, None), (0, 0)]:
        conn.execute("UPDATE football_matches_history SET home_score=?, away_score=?", (home, away))
        history._build_match_facts(conn, 10)
        history._rebuild_team_form(conn)
        history._rebuild_league_profiles(conn)
        assert conn.execute("SELECT COUNT(*) FROM shark_historical_match_facts").fetchone()[0] == 1
        expected_teams = 0 if home is None else 2
        assert conn.execute("SELECT COUNT(*) FROM shark_historical_team_form").fetchone()[0] == expected_teams
        if home is None:
            assert conn.execute("SELECT COUNT(*) FROM shark_historical_league_profile").fetchone()[0] == 0


def test_stored_or_render_time_does_not_rejuvenate_live():
    row = sample(age=600)
    row["updated_at"] = row["last_synced_at"]
    original = copy.deepcopy(row)
    context = build_match_context({"match": row})
    assert context["lifecycle"]["is_stale"]
    assert row == original


@pytest.mark.parametrize("schema_exists", [False, True])
def test_unavailable_tracker_keeps_store_provenance_and_identity(tmp_path, schema_exists):
    from engines.api_football_live_tracker_engine import live_tracker_for_match
    path = tmp_path / "tracker.sqlite"
    with closing(sqlite3.connect(path)) as conn, conn:
        if schema_exists:
            conn.execute("CREATE TABLE api_football_live_snapshots (match_id TEXT, fixture_id TEXT)")
    row = sample(age=20)
    tracker = live_tracker_for_match(str(path), row["id"])
    assert tracker["available"] is False
    assert tracker["provider"] == "api_football"
    original = copy.deepcopy(tracker)
    expected = normalize_match_entity(row)
    actual = normalize_match_entity(row, live_context=tracker)
    assert actual["source"] == expected["source"]
    assert actual["canonical_match_id"] == expected["canonical_match_id"]
    assert tracker == original
    with_tracker = build_match_context({"match":row}, live_context=tracker)
    without_tracker = build_match_context({"match":row})
    assert with_tracker["evidence"] == without_tracker["evidence"]
    assert with_tracker["transparency"]["summary"] == without_tracker["transparency"]["summary"]


def test_unavailable_tracker_metadata_cannot_refresh_a_stale_match():
    row = sample(age=600)
    tracker = {"available":False, "provider":"api_football", "status":"LIVE",
               "last_synced_at":datetime.now(timezone.utc).isoformat(), "minute":1}
    expected = normalize_match_entity(row)
    actual = normalize_match_entity(row, live_context=tracker)
    assert actual["source"] == expected["source"]
    assert actual["freshness"] == expected["freshness"]
    assert actual["status"] == expected["status"]


def test_available_tracker_provenance_is_not_discarded():
    row = sample(age=20)
    tracker = {"available":True, "provider":"api_football",
               "last_synced_at":row["last_synced_at"], "status":"LIVE"}
    result = normalize_match_entity(row, live_context=tracker)
    assert result["source"] == "api_football"


def test_stale_state_snapshot_is_not_a_confirmed_event_but_real_event_survives():
    from engines.live_engine import fallback_timeline
    row = sample(age=600)
    fallback = fallback_timeline(row)
    context = build_match_context({"match": row, "timeline": fallback})
    assert context["event_summary"]["count"] == 0
    assert context["event_summary"]["excluded_without_evidence"] == 1
    real = {"event_type":"goal", "minute":5, "team":"QA Away", "player":"QA Player",
            "source":"sportsdb", "title":"Gol", "detail":"Gol confirmado"}
    context = build_match_context({"match": row, "timeline": fallback + [real]})
    assert context["event_summary"]["count"] == 1
    assert str(context["event_summary"]["items"][0]["minute"]) == "5"
    assert context["lifecycle"]["minute"] is None


@pytest.mark.parametrize("status,age,expected_live", [
    ("LIVE", 20, True), ("LIVE", 600, False), ("LIVE", -900, False),
    ("HT", 20, True), ("FT", 600, False), ("POSTPONED", 20, False),
])
def test_observer_reads_actual_store_without_initialization(tmp_path, monkeypatch, status, age, expected_live):
    path = tmp_path / "sports.sqlite"
    row = sample(status, age)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE matches (" + ",".join('"'+key+'"' for key in row) + ")")
        conn.execute("INSERT INTO matches VALUES (" + ",".join("?" for _ in row) + ")", tuple(row.values()))
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    real_connect = sqlite3.connect
    attempted_writes = []
    sql = []

    def guarded_connect(*args, **kwargs):
        assert args[0].endswith("?mode=ro")
        connection = real_connect(*args, **kwargs)
        connection.set_trace_callback(sql.append)

        def authorize(action, _arg1, _arg2, _db, _trigger):
            if action not in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}:
                attempted_writes.append(action)
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        connection.set_authorizer(authorize)
        return connection

    monkeypatch.setattr(sqlite3, "connect", guarded_connect)
    now = datetime.now(timezone.utc)
    for _ in range(2):
        observation = observe_persisted_match(path, row["id"], evaluation_time=now)
        assert observation["state"] == "OBSERVED_PROJECTOR"
        assert observation["store"] == row
        assert observation["match_context"]["lifecycle"]["is_live"] is expected_live
        assert observation["html"] == "NOT_OBSERVED"
        assert observation["other_surface_payloads"] == "NOT_OBSERVED"
    assert not attempted_writes
    assert len(sql) == 4
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["sports.sqlite"]


def test_observer_missing_store_schema_and_entity_stay_missing(tmp_path):
    path = tmp_path / "missing.sqlite"
    now = datetime.now(timezone.utc)
    assert observe_persisted_match(path, "qa", evaluation_time=now)["reason"] == "STORE_UNAVAILABLE"
    assert not path.exists()
    with closing(sqlite3.connect(path)) as conn, conn:
        assert observe_persisted_match(path, "qa", evaluation_time=now)["reason"] == "SCHEMA_UNAVAILABLE"
        conn.execute("CREATE TABLE matches (id TEXT)")
        conn.commit()
    assert observe_persisted_match(path, "qa", evaluation_time=now)["reason"] == "MATCH_UNAVAILABLE"


def test_normal_first_access_writes_are_not_hidden_by_observer_claim(app_module, tmp_path, monkeypatch):
    path = tmp_path / "first-access.sqlite"
    monkeypatch.setattr(app_module, "DB_PATH", str(path))
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(app_module, "_SEEDING_DB_PATH", None)
    app_module.seed_core()
    with closing(sqlite3.connect(path)) as conn, conn:
        for table in ("client_profiles", "persistent_cache", "live_sync_state"):
            conn.execute("DELETE FROM " + table)
    writes = []
    real_connect = sqlite3.connect

    def tracked_connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        def authorize(action, table, _column, _db, _trigger):
            if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
                writes.append(table)
            return sqlite3.SQLITE_OK
        conn.set_authorizer(authorize)
        return conn

    monkeypatch.setattr(sqlite3, "connect", tracked_connect)
    for iteration in range(2):
        writes.clear()
        with app_module.app.test_request_context("/app"):
            app_module.default_profile()
            app_module.match_hub("2044-09-09")
        if iteration == 0:
            assert {"client_profiles", "persistent_cache", "live_sync_state"} <= set(writes)
        else:
            assert not writes
