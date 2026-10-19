"""Real SQLite collection contracts with synthetic provider responses only."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import io
import json
import sqlite3
import urllib.request

import pytest

from engines import api_football_statistics_engine as stats
from engines import api_football_live_tracker_engine as live
from engines import api_exploitation_engine as deep
from engines.cron_request_budget import CronRequestBudget, CronTimeBudget

NOW = datetime(2026, 10, 17, 19, 0, tzinfo=timezone.utc)
ENV = {"API_FOOTBALL_KEY": "synthetic-key", "API_FOOTBALL_DAILY_CALL_BUDGET": "120"}


@pytest.fixture
def store(tmp_path, monkeypatch):
    db = str(tmp_path / "statistics.sqlite")
    live.ensure_live_tracker_schema(db)
    clock = [NOW]
    monkeypatch.setattr(stats, "_now", lambda: clock[0])
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: pytest.fail("unexpected real network"))
    return db, clock


def seed(db, fid, *, status="1H", kickoff=None, observed=None):
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("""INSERT OR REPLACE INTO api_football_live_snapshots
            (fixture_id,match_id,status_short,kickoff_iso,match_date,home_team_id,away_team_id,
             home_team,away_team,last_synced_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (str(fid), "af-" + str(fid), status, (kickoff or NOW - timedelta(minutes=30)).isoformat(),
             (kickoff or NOW).date().isoformat(), "10", "20", "Norte", "Sur", (observed or NOW).isoformat()))


def values(value=0, other=None):
    return [
        {"team": {"id": 10, "name": "Norte"}, "statistics": [{"type": "Shots on Goal", "value": value}, {"type": "Corner Kicks", "value": other}]},
        {"team": {"id": 20, "name": "Sur"}, "statistics": [{"type": "Shots on Goal", "value": value}, {"type": "Corner Kicks", "value": 0}]},
    ]


def answer(ids, payload=None):
    return {"ok": True, "response": [{"fixture": {"id": int(fid)}, "statistics": values() if payload is None else payload} for fid in ids]}


def rows(db, query, params=()):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute(query, params).fetchall()


def transport(monkeypatch, calls, payload=None):
    def fetch(path, params, timeout=18):
        calls.append((path, params, timeout))
        return answer(reversed(params["ids"].split("-")), payload)
    monkeypatch.setattr(stats, "_api_get", fetch)


def test_batch_rotates_and_preserves_zero_null_receipts_and_fixture_clock(store, monkeypatch):
    db, clock = store
    for fid in (101, 102, 103):
        seed(db, fid)
    calls = []
    transport(monkeypatch, calls)
    env = {**ENV, "API_FOOTBALL_STATISTICS_BATCH_SIZE": "2"}
    before = rows(db, "SELECT fixture_id,last_synced_at FROM api_football_live_snapshots ORDER BY fixture_id")
    first = stats.refresh_api_football_statistics_if_due(db, env=env)
    second = stats.refresh_api_football_statistics_if_due(db, env=env)
    third = stats.refresh_api_football_statistics_if_due(db, env=env)
    assert first["refreshed_fixtures"] == 2 and second["refreshed_fixtures"] == 1
    assert third["external_calls"] == 0 and third["status"] == "NO_DUE_STATISTICS"
    assert len(calls) == 2 and all(item[0] == "fixtures" for item in calls)
    assert set(first["selected_fixture_ids"]).isdisjoint(second["selected_fixture_ids"])
    assert rows(db, "SELECT fixture_id,last_synced_at FROM api_football_live_snapshots ORDER BY fixture_id") == before
    assert rows(db, "SELECT COUNT(*) FROM match_record_observations WHERE section='statistics'") == [(3,)]
    assert rows(db, "SELECT stat_value,numeric_value FROM api_football_live_stats WHERE fixture_id='101' AND team_id='10' AND stat_name='Shots on Goal'") == [("0", 0.0)]
    assert rows(db, "SELECT stat_value,numeric_value FROM api_football_live_stats WHERE fixture_id='101' AND team_id='10' AND stat_name='Corner Kicks'") == [("", None)]
    assert rows(db, "SELECT SUM(estimated_calls),SUM(actual_calls) FROM api_usage_guard") == [(2, 2)]


def test_live_final_and_negative_ttls(store, monkeypatch):
    db, clock = store
    seed(db, 101)
    seed(db, 102, status="FT", kickoff=NOW - timedelta(hours=3))
    calls = []
    transport(monkeypatch, calls)
    result = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    due = {item["fixture_id"]: stats._date(item["next_due_at"]) for item in result["items"]}
    assert due["101"] == NOW + timedelta(minutes=5)
    assert due["102"] == NOW + timedelta(hours=6)
    clock[0] += timedelta(minutes=5)
    result = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    assert result["selected_fixture_ids"] == ["101"]
    clock[0] += timedelta(minutes=5)
    transport(monkeypatch, calls, payload=[])
    result = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    assert result["items"][0]["status"] == "NO_DATA"
    assert stats._date(result["items"][0]["next_due_at"]) == clock[0] + timedelta(minutes=30)


@pytest.mark.parametrize("payload", [[], [{"team": {"id": 10, "name": "Norte"}, "statistics": [{"type": "Shots on Goal", "value": None}]}]])
def test_empty_or_null_reply_preserves_last_usable_snapshot(store, monkeypatch, payload):
    db, clock = store
    seed(db, 101)
    calls = []
    transport(monkeypatch, calls)
    stats.refresh_api_football_statistics_if_due(db, env=ENV)
    snapshot = rows(db, "SELECT * FROM api_football_live_stats ORDER BY id")
    history = rows(db, "SELECT * FROM api_football_match_stats_history ORDER BY id")
    clock[0] += timedelta(minutes=6)
    transport(monkeypatch, calls, payload=payload)
    result = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    assert result["status"] == "NO_DATA" and result["data_contributed"] is False
    assert rows(db, "SELECT * FROM api_football_live_stats ORDER BY id") == snapshot
    assert rows(db, "SELECT * FROM api_football_match_stats_history ORDER BY id") == history
    assert rows(db, "SELECT COUNT(*) FROM match_record_observations") == [(2,)]


def test_batch_omissions_extra_ids_and_duplicate_or_wrong_team_never_cross_associate(store, monkeypatch):
    db, clock = store
    for fid in (101, 102, 103, 104):
        seed(db, fid)
    payload = answer([104, 101, 999])
    payload["response"].append(answer([104])["response"][0])
    wrong = answer([103])["response"][0]
    wrong["statistics"][0]["team"]["id"] = 999
    payload["response"].append(wrong)
    monkeypatch.setattr(stats, "_api_get", lambda *a, **k: payload)
    result = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    observed = {item["fixture_id"]: item["status"] for item in result["items"]}
    assert observed["101"] == "AVAILABLE"
    assert observed["102"] == "NO_DATA"
    assert observed["103"] == observed["104"] == "PROVIDER_FAILURE_INVALID_RESPONSE"
    assert result["ok"] is False and result["refreshed_fixtures"] == 1
    assert rows(db, "SELECT DISTINCT fixture_id FROM api_football_live_stats") == [("101",)]
    assert rows(db, "SELECT DISTINCT fixture_id FROM match_record_observations") == [("101",)]


def test_partial_new_receipt_replaces_current_set_without_losing_history(store, monkeypatch):
    db, clock = store
    seed(db, 101)
    transport(monkeypatch, [])
    stats.refresh_api_football_statistics_if_due(db, env=ENV)
    clock[0] += timedelta(minutes=6)
    payload = [{"team": {"id": 10, "name": "Norte"}, "statistics": [{"type": "Shots on Goal", "value": 3}]}]
    transport(monkeypatch, [], payload=payload)
    result = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    assert result["refreshed_fixtures"] == 1
    assert rows(db, "SELECT team_id,stat_name,stat_value FROM api_football_live_stats") == [("10", "Shots on Goal", "3")]
    assert rows(db, "SELECT COUNT(*) FROM api_football_match_stats_history") == [(5,)]


def test_shared_daily_guard_and_denied_reservation_make_no_request(store, monkeypatch):
    db, clock = store
    seed(db, 101)
    with closing(sqlite3.connect(db)) as conn, conn:
        stats._ensure_schema(conn)
        conn.execute("""INSERT INTO api_usage_guard(provider,window_key,estimated_calls,status)
            VALUES ('api_football',?,1,'ALLOWED')""", (NOW.astimezone(stats.usage_guard.TZ).date().isoformat(),))
    monkeypatch.setattr(stats, "_api_get", lambda *a, **k: pytest.fail("daily quota exceeded"))
    result = stats.refresh_api_football_statistics_if_due(db, env={**ENV, "API_FOOTBALL_DAILY_CALL_BUDGET": "1"})
    assert result["status"] == "DAILY_BUDGET" and result["external_calls"] == 0
    assert result["budget_scope"] == "LOCAL_APPLICATION_GUARD"
    assert result["reason_code"] == "LOCAL_APPLICATION_BUDGET_EXHAUSTED"
    assert result["budget_limit"] == result["budget_used"] == 1
    assert result["budget_remaining"] == 0 and result["required_calls"] == 1
    assert result["provider_quota_consulted"] is False
    assert rows(db, "SELECT COUNT(*) FROM api_football_statistics_refresh_state") == [(0,)]


def test_claim_is_durable_and_no_sqlite_write_lock_spans_transport(store, monkeypatch):
    db, clock = store
    seed(db, 101)
    def fetch(path, params, timeout=4):
        with closing(sqlite3.connect(db, timeout=.01)) as other:
            other.execute("BEGIN IMMEDIATE")
            other.rollback()
        nested = stats.refresh_api_football_statistics_if_due(db, env=ENV)
        assert nested["external_calls"] == 0 and nested["status"] == "NO_DUE_STATISTICS"
        return answer([101])
    monkeypatch.setattr(stats, "_api_get", fetch)
    result = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    assert result["refreshed_fixtures"] == 1
    assert rows(db, "SELECT COUNT(*) FROM api_usage_guard") == [(1,)]


def test_auth_failure_cools_down_without_healthy_claim_or_secret_leak(store, monkeypatch):
    db, clock = store
    seed(db, 101)
    calls = []
    def fetch(*args, **kwargs):
        calls.append(1)
        return {"ok": False, "response": [], "error": "HTTP Error 403 private-token"}
    monkeypatch.setattr(stats, "_api_get", fetch)
    first = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    second = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    assert len(calls) == 1
    assert first["ok"] is False and first["failure_category"] == "AUTH_OR_ACCESS"
    assert second["ok"] is False and second["status"] == "PROVIDER_FAILURE_BACKOFF_AUTH_OR_ACCESS"
    assert second["provider_observation_current"] is False and second["external_calls"] == 0
    assert "private-token" not in json.dumps([first, second])
    assert rows(db, "SELECT COUNT(*) FROM api_football_match_stats_history") == [(0,)]


def test_coverage_failure_is_local_and_next_fixture_can_progress(store, monkeypatch):
    db, clock = store
    seed(db, 101)
    seed(db, 102)
    replies = [{"ok": False, "errors": {"coverage": "not available for this fixture"}}, answer([102])]
    monkeypatch.setattr(stats, "_api_get", lambda *a, **k: replies.pop(0))
    first = stats.refresh_api_football_statistics_if_due(db, limit=1, env=ENV)
    second = stats.refresh_api_football_statistics_if_due(db, limit=1, env=ENV)
    assert first["failure_category"] == "COVERAGE_UNAVAILABLE"
    assert second["selected_fixture_ids"] == ["102"] and second["refreshed_fixtures"] == 1


def test_deadline_does_not_call_or_stamp_provider_success(store, monkeypatch):
    db, clock = store
    seed(db, 101)
    monkeypatch.setattr(stats, "_api_get", lambda *a, **k: pytest.fail("deadline exhausted"))
    with CronRequestBudget(seconds=0):
        result = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    assert result["status"] == "TIME_BUDGET" and result["external_calls"] == 0
    assert rows(db, "SELECT COUNT(*) FROM sqlite_master WHERE name='api_football_statistics_refresh_state'") == [(0,)]
    def interrupted(*a, **k):
        raise CronTimeBudget(external_calls=1)
    monkeypatch.setattr(stats, "_api_get", interrupted)
    result = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    assert result["status"] == "TIME_BUDGET" and result["external_calls"] == 1
    assert result["provider_observation_current"] is False
    assert rows(db, "SELECT last_success_at,provider_observed_at FROM api_football_statistics_refresh_state") == [(None, None)]


@pytest.mark.parametrize("setting", ["ENABLE_API_FOOTBALL_PROVIDER", "ENABLE_API_FOOTBALL_STATISTICS_SYNC", "ENABLE_API_SPORTS_NETWORK_CALLS"])
def test_disabled_collection_never_touches_storage_or_http(tmp_path, monkeypatch, setting):
    db = tmp_path / "not-created.sqlite"
    monkeypatch.setattr(stats, "_api_get", lambda *a, **k: pytest.fail("disabled network"))
    result = stats.refresh_api_football_statistics_if_due(str(db), env={**ENV, setting: "false"})
    assert result["status"] == "DISABLED" and not db.exists()


def test_only_recent_proven_api_football_fixtures_are_eligible(store, monkeypatch):
    db, clock = store
    seed(db, 101, status="NS", kickoff=NOW + timedelta(hours=1))
    seed(db, 102, status="FT", kickoff=NOW - timedelta(days=5))
    seed(db, 103, status="1H", kickoff=NOW - timedelta(days=2))
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE matches(external_id TEXT,source TEXT,status TEXT,kickoff_iso TEXT,updated_at TEXT)")
        conn.execute("INSERT INTO matches VALUES ('999','thesportsdb','1H',?,?)", ((NOW - timedelta(minutes=20)).isoformat(), NOW.isoformat()))
    monkeypatch.setattr(stats, "_api_get", lambda *a, **k: pytest.fail("unproved fixture"))
    assert stats.refresh_api_football_statistics_if_due(db, env=ENV)["status"] == "SKIPPED_NO_API_FOOTBALL_FIXTURE"


def test_large_future_calendar_cannot_hide_recent_finished_candidate(store, monkeypatch):
    db, clock = store
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE matches(external_id TEXT,source TEXT,status TEXT,kickoff_iso TEXT,updated_at TEXT)")
        conn.execute("INSERT INTO matches VALUES ('101','api_football','FT',?,?)", ((NOW - timedelta(hours=3)).isoformat(), (NOW - timedelta(minutes=1)).isoformat()))
        conn.executemany("INSERT INTO matches VALUES (?,'api_football','NS',?,?)", [
            (str(1000 + index), (NOW + timedelta(days=1)).isoformat(), NOW.isoformat()) for index in range(601)])
    calls = []
    transport(monkeypatch, calls)
    result = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    assert result["selected_fixture_ids"] == ["101"] and result["refreshed_fixtures"] == 1
    assert len(calls) == 1


def test_candidate_filter_does_not_resurrect_older_live_after_newer_postponement(store, monkeypatch):
    db, clock = store
    seed(db, 101, observed=NOW - timedelta(minutes=10))
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE matches(external_id TEXT,source TEXT,status TEXT,kickoff_iso TEXT,updated_at TEXT)")
        conn.execute("INSERT INTO matches VALUES ('101','api_football','PST',?,?)", ((NOW - timedelta(minutes=30)).isoformat(), NOW.isoformat()))
    monkeypatch.setattr(stats, "_api_get", lambda *a, **k: pytest.fail("postponed match"))
    assert stats.refresh_api_football_statistics_if_due(db, env=ENV)["status"] == "SKIPPED_NO_API_FOOTBALL_FIXTURE"


@pytest.mark.parametrize("status", ["halftime", "HALFTIME", "descanso", "extra_time", "penalties"])
def test_canonical_live_status_without_status_short_remains_eligible(store, monkeypatch, status):
    db, clock = store
    seed(db, 101, observed=NOW - timedelta(minutes=10))
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE matches(external_id TEXT,source TEXT,status TEXT,kickoff_iso TEXT,updated_at TEXT)")
        conn.execute("INSERT INTO matches VALUES ('101','api_football',?,?,?)", (status, (NOW - timedelta(minutes=30)).isoformat(), NOW.isoformat()))
    transport(monkeypatch, [])
    result = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    assert result["selected_fixture_ids"] == ["101"] and result["refreshed_fixtures"] == 1
    assert stats._date(result["items"][0]["next_due_at"]) == NOW + timedelta(minutes=5)


def test_halftime_only_in_matches_and_madrid_midnight_offset_are_eligible(store, monkeypatch):
    db, clock = store
    clock[0] = datetime(2026, 10, 17, 22, 45, tzinfo=timezone.utc)
    kickoff = datetime(2026, 10, 18, 0, 10, tzinfo=timezone(timedelta(hours=2)))
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE matches(external_id TEXT,source TEXT,status TEXT,kickoff_iso TEXT,updated_at TEXT)")
        conn.execute("INSERT INTO matches VALUES ('101','api_football','halftime',?,?)", (kickoff.isoformat(), clock[0].isoformat()))
    transport(monkeypatch, [])
    result = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    assert result["selected_fixture_ids"] == ["101"] and result["refreshed_fixtures"] == 1


@pytest.mark.parametrize("flags", [{"NEMESIS_OFFLINE_MODE": "true"}, {"NEMESIS_LOCAL_SAFE_MODE": "1", "NEMESIS_LOCAL_MODE": "OFFLINE_SAFE"}])
def test_offline_flags_do_not_open_db_or_request_provider(tmp_path, monkeypatch, flags):
    db = tmp_path / "offline-unopened.sqlite"
    monkeypatch.setattr(stats, "_api_get", lambda *a, **k: pytest.fail("offline provider"))
    result = stats.refresh_api_football_statistics_if_due(str(db), env={**ENV, **flags})
    assert result["status"] == "OFFLINE_SAFE" and result["external_calls"] == 0
    assert result["provider_observation_current"] is False and not db.exists()


def test_transport_explicit_zero_calls_does_not_manufacture_receipt(store, monkeypatch):
    db, clock = store
    seed(db, 101)
    monkeypatch.setattr(stats, "_api_get", lambda *a, **k: {"ok": False, "status": "OFFLINE_SAFE", "external_calls": 0})
    result = stats.refresh_api_football_statistics_if_due(db, env=ENV)
    assert result["external_calls"] == 0 and result["status"] == "OFFLINE_SAFE"
    assert result["provider_observation_current"] is False
    assert rows(db, "SELECT last_success_at,provider_observed_at FROM api_football_statistics_refresh_state") == [(None, None)]


def test_read_state_is_readonly_and_exposes_stale_or_identity_unavailable(store, monkeypatch):
    db, clock = store
    seed(db, 101)
    transport(monkeypatch, [])
    stats.refresh_api_football_statistics_if_due(db, env=ENV)
    before = rows(db, "SELECT * FROM api_football_statistics_refresh_state")
    state = stats.statistics_refresh_state_for_match(db, {"id": "af-101"})
    assert state["status"] == "AVAILABLE" and state["external_calls"] == 0
    clock[0] += timedelta(minutes=6)
    assert stats.statistics_refresh_state_for_match(db, {"id": "af-101"})["status"] == "STALE"
    assert stats.statistics_refresh_state_for_match(db, {"source": "thesportsdb", "external_id": "101"})["status"] == "IDENTITY_UNAVAILABLE"
    assert rows(db, "SELECT * FROM api_football_statistics_refresh_state") == before


def test_read_state_accepts_only_explicit_internal_mapping_and_sanitizes_stored_metadata(store, monkeypatch):
    db, clock = store
    seed(db, 101)
    transport(monkeypatch, [])
    stats.refresh_api_football_statistics_if_due(db, env=ENV)
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE api_football_fixture_index(fixture_id TEXT,internal_match_id TEXT)")
        conn.execute("INSERT INTO api_football_fixture_index VALUES ('101','canonical-merged')")
        conn.execute("UPDATE api_football_statistics_refresh_state SET status='private-canary',failure_category='private-canary',provider_observed_at='private-canary'")
    result = stats.statistics_refresh_state_for_match(db, {"id": "canonical-merged", "source": "thesportsdb", "external_id": "999"})
    assert result["fixture_id"] == "101" and result["status"] == "UNKNOWN"
    assert "private-canary" not in json.dumps(result)
    unrelated = stats.statistics_refresh_state_for_match(db, {"id": "different", "source": "thesportsdb", "external_id": "101"})
    assert unrelated["status"] == "IDENTITY_UNAVAILABLE"


def test_global_access_failure_preserves_fixture_last_success_clock(store, monkeypatch):
    db, clock = store
    seed(db, 101)
    transport(monkeypatch, [])
    stats.refresh_api_football_statistics_if_due(db, env=ENV)
    last_success = stats.statistics_refresh_state_for_match(db, {"id": "af-101"})["last_success_at"]
    clock[0] += timedelta(minutes=6)
    monkeypatch.setattr(stats, "_api_get", lambda *a, **k: {"ok": False, "error": "403 forbidden", "response": []})
    stats.refresh_api_football_statistics_if_due(db, env=ENV)
    state = stats.statistics_refresh_state_for_match(db, {"id": "af-101"})
    assert state["status"] == "PROVIDER_FAILURE_AUTH_OR_ACCESS" and state["has_previous_data"] is True
    assert state["last_success_at"] == last_success
    assert state["provider_observed_at"] != last_success


def test_individual_transport_is_explicit_and_capped(store, monkeypatch):
    db, clock = store
    for fid in range(101, 105):
        seed(db, fid)
    calls = []
    def fetch(path, params, timeout=18):
        calls.append((path, params))
        return {"ok": True, "response": values()}
    monkeypatch.setattr(stats, "_api_get", fetch)
    result = stats.refresh_api_football_statistics_if_due(db, env={**ENV, "API_FOOTBALL_STATISTICS_TRANSPORT": "individual"})
    assert result["external_calls"] == result["refreshed_fixtures"] == 2
    assert all(path == "fixtures/statistics" for path, params in calls)
    assert rows(db, "SELECT estimated_calls,actual_calls FROM api_usage_guard") == [(2, 2)]


@pytest.mark.parametrize("alias", ["API_FOOTBALL_KEY", "API_FOOTBALL_API_KEY", "API_SPORTS_KEY", "APISPORTS_KEY"])
def test_provider_key_aliases_use_same_authenticated_transport(monkeypatch, alias, tmp_path):
    for key in ("API_FOOTBALL_KEY", "API_FOOTBALL_API_KEY", "API_SPORTS_KEY", "APISPORTS_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(alias, "synthetic-alias-key")
    seen = []
    def fetch(req, **kwargs):
        seen.append(req.get_header("X-apisports-key"))
        response = io.BytesIO(b'{"response":[],"errors":[]}')
        response.headers = {}
        return response
    monkeypatch.setattr(urllib.request, "urlopen", fetch)
    assert live.api_key_configured() is True and deep._api_football_key() == live._api_key()
    configured = stats.refresh_api_football_statistics_if_due(str(tmp_path / "alias.sqlite"), env={alias: "synthetic-alias-key"})
    assert configured["configured"] is True and configured["enabled"] is True and configured["external_calls"] == 0
    assert live._api_get("fixtures", {"ids": "101"})["ok"]
    assert deep._api_get("fixtures/statistics", {"fixture": "101"})["ok"]
    assert seen == ["synthetic-alias-key", "synthetic-alias-key"]
