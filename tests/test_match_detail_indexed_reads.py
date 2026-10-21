"""Match Center reads must stay bounded as unrelated cached fixtures grow.

All records are synthetic and live in a temporary database. Instruction counts
test query complexity without depending on the speed of the machine running CI.
"""
from __future__ import annotations

from contextlib import closing
import sqlite3

import pytest

from engines.api_exploitation_engine import ensure_api_exploitation_schema


FIXTURE = "900001"
LATEST = "2026-10-21T11:00:00Z"
OLDER = "2026-10-21T12:30:00+02:00"  # Lexically later, chronologically earlier.
VM_BUDGET = 20_000


@pytest.fixture(scope="module")
def populated_cache(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("indexed-match-cache") / "cache.db")
    ensure_api_exploitation_schema(path)  # Includes the production UNIQUE indexes.
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute(
            """INSERT INTO api_football_fixture_index
               (id,fixture_id,internal_match_id,home_team_id,away_team_id,last_seen_at)
               VALUES (?,?,?,?,?,?)""",
            ("index-target", FIXTURE, "af-" + FIXTURE, "10", "20", LATEST),
        )
        lineup_sql = """INSERT INTO api_football_lineups_deep
            (id,fixture_id,team_id,player_id,player_name,position,is_starting,captured_at)
            VALUES (?,?,?,?,?,?,?,?)"""
        stats_sql = """INSERT INTO api_football_match_stats_history
            (id,fixture_id,team_id,team_name,stat_name,stat_value,captured_at)
            VALUES (?,?,?,?,?,?,?)"""
        conn.executemany(lineup_sql, (
            (f"lineup-{i}", str(100_000 + i), "10", str(i), "Other player", "MID", 1, OLDER)
            for i in range(30_000)
        ))
        conn.executemany(stats_sql, (
            (f"stat-{i}", str(100_000 + i), "10", "Other team", "Ball Possession", "99%", LATEST)
            for i in range(30_000)
        ))
        conn.executemany(lineup_sql, [
            ("lineup-home", FIXTURE, "10", "101", "Home player", "MID", 1, OLDER),
            ("lineup-away", FIXTURE, "20", "201", "Away player", "DEF", 1, LATEST),
            ("lineup-null", None, "10", "301", "Unidentified", "MID", 1, LATEST),
            ("lineup-empty", "", "20", "401", "Unidentified", "DEF", 1, LATEST),
        ])
        conn.executemany(stats_sql, [
            ("old-home", FIXTURE, "10", "Provider alias", "Ball Possession", "47%", OLDER),
            ("old-away", FIXTURE, "20", "Provider alias", "Ball Possession", "53%", OLDER),
            ("new-home", FIXTURE, "10", "Provider alias", "Ball Possession", "56%", LATEST),
            ("new-away", FIXTURE, "20", "Provider alias", "Ball Possession", "44%", LATEST),
            ("empty-value", FIXTURE, "10", "Provider alias", "Shots", "", "2026-10-22T12:00:00Z"),
            ("invalid-clock", FIXTURE, "10", "Provider alias", "Shots", "99", "invalid-time"),
            ("stat-null", None, "10", "Home QA", "Ball Possession", "99%", LATEST),
            ("stat-empty", "", "20", "Away QA", "Ball Possession", "99%", LATEST),
        ])
    return path


def _match():
    return {"id": "af-" + FIXTURE, "source": "api_football", "external_id": FIXTURE,
            "home_team": "Home QA", "away_team": "Away QA"}


def _measured_read(app_module, callback):
    ticks = []
    with app_module.app.test_request_context("/match/af-" + FIXTURE):
        conn = app_module.request_read_db()
        conn.set_progress_handler(lambda: ticks.append(None) or 0, 1000)
        try:
            result = callback()
        finally:
            conn.set_progress_handler(None, 0)
    return result, len(ticks) * 1000


def test_lineups_read_only_the_requested_fixture_with_bounded_work(
    app_module, monkeypatch, populated_cache,
):
    monkeypatch.setattr(app_module, "DB_PATH", populated_cache)
    lineups, instructions = _measured_read(
        app_module, lambda: app_module._cached_lineups_for_match(_match()),
    )
    assert {row["player_id"] for row in lineups} == {"101", "201"}
    assert {row["fixture_id"] for row in lineups} == {FIXTURE}
    assert instructions <= VM_BUDGET, f"Lineups scanned unrelated fixtures: {instructions} SQLite VM instructions"


def test_statistics_preserve_identity_and_capture_time_with_bounded_work(
    app_module, monkeypatch, populated_cache,
):
    monkeypatch.setattr(app_module, "DB_PATH", populated_cache)
    statistics, instructions = _measured_read(
        app_module, lambda: app_module._cached_match_statistics(_match()),
    )
    assert statistics["updated_at"] == LATEST
    assert statistics["external_calls"] == 0
    assert statistics["items"] == [{
        "key": "ball_possession", "label": "Ball Possession",
        "home": "56%", "away": "44%", "leader": "even",
    }]
    unrelated = {**_match(), "id": "sportsdb-unrelated", "source": "thesportsdb"}
    foreign, _ = _measured_read(
        app_module, lambda: app_module._cached_match_statistics(unrelated),
    )
    assert foreign["available"] is False
    assert foreign["items"] == []
    assert instructions <= VM_BUDGET, f"Statistics scanned unrelated fixtures: {instructions} SQLite VM instructions"
