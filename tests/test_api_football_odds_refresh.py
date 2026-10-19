"""Synthetic API-Football odds refresh tests; no provider credentials or HTTP calls."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import sqlite3

import pytest

from engines import api_football_odds_engine as odds
from engines.v935_launch_trust_engine import get_odds_freshness


NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)
ENV = {
    "API_FOOTBALL_KEY": "synthetic-key",
    "API_FOOTBALL_DAILY_CALL_BUDGET": "120",
    "API_FOOTBALL_ODDS_DAILY_CALL_BUDGET": "60",
    "API_FOOTBALL_ODDS_FIXTURES_PER_TICK": "2",
    "NEMESIS_LOCAL_MODE": "INTEGRATION_TEST",
    "NEMESIS_OFFLINE_MODE": "false",
    "NEMESIS_LOCAL_EXTERNAL_AUTHORIZED": "true",
    "NEMESIS_LOCAL_SAFE_MODE": "false",
}


@pytest.fixture
def store(tmp_path, monkeypatch):
    path = str(tmp_path / "api-football-odds.sqlite")
    kickoff = NOW + timedelta(days=2)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("""CREATE TABLE matches(
            id TEXT PRIMARY KEY, external_id TEXT, source TEXT, match_date TEXT NOT NULL,
            kickoff_iso TEXT, kickoff_time TEXT, match_time TEXT, status TEXT,
            home_team TEXT, away_team TEXT, league_name TEXT, competition_name TEXT,
            bookmaker TEXT, odds_h2h_json TEXT, odds_updated_at TEXT)""")
        conn.execute("""CREATE TABLE odds_snapshots(
            id TEXT PRIMARY KEY, match_id TEXT, external_id TEXT, source TEXT, sport_key TEXT,
            league_name TEXT, bookmaker TEXT, market TEXT, home_team TEXT, away_team TEXT,
            home_price TEXT, draw_price TEXT, away_price TEXT, commence_time TEXT,
            payload_json TEXT, created_at TEXT)""")
        conn.execute("""INSERT INTO matches(id,external_id,source,match_date,kickoff_iso,status,
            home_team,away_team,league_name) VALUES(?,?,?,?,?,?,?,?,?)""",
            ("af-501", "501", "API-Football", kickoff.date().isoformat(),
             kickoff.isoformat(), "NS", "Granada", "Málaga", "LaLiga QA"))
    monkeypatch.setattr(odds, "_now", lambda: NOW)
    return path


def payload(fixture_id=501, *, update=None, bookmakers=None):
    return {
        "ok": True,
        "response": [{
            "fixture": {"id": fixture_id},
            "update": update or (NOW - timedelta(minutes=5)).isoformat(),
            "bookmakers": bookmakers if bookmakers is not None else [{
                "id": 8, "name": "Casa verificada", "bets": [{
                    "id": 1, "name": "Match Winner", "values": [
                        {"value": "Home", "odd": "2.10"},
                        {"value": "Draw", "odd": "3.25"},
                        {"value": "Away", "odd": "3.80"},
                    ],
                }],
            }],
        }],
    }


def query(path, sql, params=()):
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute(sql, params).fetchall()


def test_persists_only_verified_1x2_and_reuses_provider_cooldown(store):
    calls = []

    def transport(endpoint, params, timeout=0):
        calls.append((endpoint, params, timeout))
        return payload()

    first = odds.refresh_api_football_odds_if_due(store, env=ENV, transport=transport)
    assert first["status"] == "OK"
    assert first["external_calls"] == 1
    assert first["provider_observation_current"] is True
    assert first["provider_quota_consulted"] is False
    assert first["snapshots_inserted"] == 1
    assert calls == [("odds", {"fixture": "501"}, 4)]
    assert query(store, "SELECT source,market,home_price,draw_price,away_price FROM odds_snapshots") == [
        ("API-Football", "1x2", "2.1", "3.25", "3.8")
    ]
    stored = json.loads(query(store, "SELECT odds_h2h_json FROM matches WHERE id='af-501'")[0][0])
    assert stored["source"] == "API-Football"
    assert stored["last_update"] == (NOW - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")

    second = odds.refresh_api_football_odds_if_due(store, env=ENV, transport=transport)
    assert second["external_calls"] == 0
    assert second["status"] == "NO_DUE_ODDS"
    assert len(calls) == 1


def test_no_data_or_unsupported_markets_never_create_prices(store):
    calls = []

    def transport(*args, **kwargs):
        calls.append(args)
        return {**payload(bookmakers=[{"id": 8, "name": "Casa", "bets": [{
            "name": "Over/Under", "values": [{"value": "Over 2.5", "odd": "1.90"}],
        }]}])}

    result = odds.refresh_api_football_odds_if_due(store, env=ENV, transport=transport)
    assert result["status"] == "NO_DATA"
    assert result["external_calls"] == 1
    assert result["snapshots_inserted"] == 0
    assert query(store, "SELECT COUNT(*) FROM odds_snapshots") == [(0,)]
    assert query(store, "SELECT COALESCE(odds_h2h_json,'') FROM matches WHERE id='af-501'") == [("",)]


def test_access_failure_sets_global_backoff_without_repeating_request(store):
    calls = []

    def transport(*args, **kwargs):
        calls.append(args)
        return {"ok": False, "response": [], "errors": {"access": "Your account is suspended"}}

    first = odds.refresh_api_football_odds_if_due(store, env=ENV, transport=transport)
    assert first["provider_observation_current"] is True
    assert first["failure_categories"] == ["ACCOUNT_SUSPENDED"]
    assert first["external_calls"] == 1
    second = odds.refresh_api_football_odds_if_due(store, env=ENV, transport=transport)
    assert second["status"] == "PROVIDER_FAILURE_BACKOFF"
    assert second["external_calls"] == 0
    assert second["provider_observation_current"] is False
    assert len(calls) == 1


def test_local_budget_and_offline_mode_stop_before_transport(store):
    called = []
    transport = lambda *args, **kwargs: called.append(args) or payload()
    capped = odds.refresh_api_football_odds_if_due(
        store, env={**ENV, "API_FOOTBALL_ODDS_DAILY_CALL_BUDGET": "0"}, transport=transport,
    )
    assert capped["status"] == "DAILY_BUDGET"
    assert capped["external_calls"] == 0
    offline = odds.refresh_api_football_odds_if_due(
        store, env={**ENV, "NEMESIS_OFFLINE_MODE": "true"}, transport=transport,
    )
    assert offline["status"] == "OFFLINE_SAFE"
    assert offline["external_calls"] == 0
    assert called == []


def test_only_api_football_fixtures_are_candidates(store):
    with closing(sqlite3.connect(store)) as conn, conn:
        conn.execute("UPDATE matches SET source='TheSportsDB'")
    called = []
    result = odds.refresh_api_football_odds_if_due(
        store, env=ENV, transport=lambda *args, **kwargs: called.append(args),
    )
    assert result["status"] == "SKIPPED_NO_API_FOOTBALL_FIXTURE"
    assert result["external_calls"] == 0
    assert called == []


def test_api_football_quote_freshness_matches_slow_provider_cadence(monkeypatch):
    monkeypatch.setenv("API_FOOTBALL_ODDS_FRESH_SECONDS", "10800")
    now = NOW
    api_quote = get_odds_freshness((now - timedelta(hours=2, minutes=30)).isoformat(), now,
                                   odds=2.1, source="API-Football", match_lifecycle="UPCOMING")
    other_quote = get_odds_freshness((now - timedelta(minutes=20)).isoformat(), now,
                                     odds=2.1, source="The Odds API", match_lifecycle="UPCOMING")
    expired_api_quote = get_odds_freshness((now - timedelta(hours=3, minutes=1)).isoformat(), now,
                                           odds=2.1, source="API-Football", match_lifecycle="UPCOMING")
    assert api_quote["status"] == "FRESH"
    assert api_quote["label"] == "Cuota reciente de API-Football"
    assert other_quote["status"] == "RECORDED"
    assert expired_api_quote["status"] == "STALE"


def test_the_odds_api_is_never_called_without_explicit_funding(monkeypatch):
    import app as app_module

    monkeypatch.setenv("THE_ODDS_API_FUNDED", "false")
    monkeypatch.setenv("THE_ODDS_API_KEY", "synthetic-only")
    monkeypatch.setenv("ENABLE_ODDS_API", "true")
    monkeypatch.setattr(app_module, "seed_core", lambda: pytest.fail("unfunded path must not initialize data"))
    result = app_module.sync_odds_events(limit=5)
    assert result["status"] == "UNFUNDED_NOT_CONFIGURED"
    assert result["funded"] is False
    assert result["external_calls"] == 0


def test_provider_wrapper_respects_zero_limit_and_reports_unfunded_optional_source(monkeypatch):
    import app as app_module

    refreshes = []
    optional_calls = []
    monkeypatch.setattr(app_module, "refresh_api_football_odds_if_due",
                        lambda *args, **kwargs: refreshes.append(kwargs.get("limit")) or {
                            "ok": True, "status": "DISABLED", "external_calls": 0, "processed": 0,
                            "fixtures_count": 0, "snapshots_inserted": 0,
                        })
    monkeypatch.setattr(app_module, "sync_odds_events",
                        lambda *args, **kwargs: optional_calls.append(1) or {"ok": True})
    monkeypatch.setenv("THE_ODDS_API_FUNDED", "false")
    monkeypatch.setenv("THE_ODDS_API_KEY", "synthetic-only")
    monkeypatch.setenv("ENABLE_ODDS_API", "true")

    result = app_module.sync_provider_odds(limit=0)
    assert refreshes == [0]
    assert optional_calls == []
    assert result["external_calls"] == 0
    assert result["the_odds_api"]["status"] == "UNFUNDED_NOT_CONFIGURED"
