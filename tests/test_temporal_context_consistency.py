from __future__ import annotations

import copy
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from engines.madrid_time_engine import (
    format_madrid_client_date_label,
    format_madrid_client_datetime_label,
    to_madrid_time,
)
from engines.pick_grading_engine import _enrich_recent_result, pick_grading_summary


MADRID = ZoneInfo("Europe/Madrid")


def test_client_temporal_policy_uses_one_madrid_instant():
    now = datetime(2026, 8, 30, 12, 0, tzinfo=MADRID)
    assert format_madrid_client_datetime_label("2026-08-30T19:00:00Z", now=now) == "Hoy · 21:00"
    assert format_madrid_client_datetime_label("2026-08-31T16:30:00Z", now=now) == "Mañana · 18:30"
    assert format_madrid_client_datetime_label("2026-09-01T18:45:00Z", now=now) == "Mar 1 sep · 20:45"
    assert format_madrid_client_datetime_label("2026-09-12T19:00:00Z", now=now) == "12 sep · 21:00"
    assert format_madrid_client_datetime_label(
        "2026-08-30T19:00:00Z", now=now, detail=True
    ) == "Domingo, 30 de agosto · 21:00"


def test_madrid_midnight_summer_winter_and_dst_edges():
    assert to_madrid_time("2026-08-29T22:30:00Z").isoformat().startswith("2026-08-30T00:30:00+02:00")
    assert to_madrid_time("2026-07-01T19:00:00Z").strftime("%H:%M%z") == "21:00+0200"
    assert to_madrid_time("2026-12-01T19:00:00Z").strftime("%H:%M%z") == "20:00+0100"
    before_fallback = to_madrid_time("2026-10-25T00:30:00Z")
    after_fallback = to_madrid_time("2026-10-25T01:30:00Z")
    assert before_fallback.strftime("%H:%M%z") == "02:30+0200"
    assert after_fallback.strftime("%H:%M%z") == "02:30+0100"


def test_live_and_terminal_temporal_truth_never_invents_minute(app_module):
    base = {
        "id": "temporal-match",
        "kickoff_iso": "2026-08-30T19:00:00Z",
        "home_team": "Real Madrid",
        "away_team": "Barcelona",
        "competition_name": "LaLiga",
        "home_score": "2",
        "away_score": "1",
        "source": "qa",
        "updated_at": app_module.now_iso(),
        "last_synced_at": app_module.now_iso(),
    }
    live = app_module.client_match_display_context({**base, "status": "LIVE", "minute": "67"})
    live_without_minute = app_module.client_match_display_context({**base, "status": "LIVE", "minute": ""})
    finished = app_module.client_match_display_context({**base, "status": "FT", "minute": "90"})
    finished_alias = app_module.client_match_display_context({**base, "status": "FINISHED", "minute": "90"})
    finished_extra_time = app_module.client_match_display_context({**base, "status": "AET", "minute": "120"})
    postponed = app_module.client_match_display_context({**base, "status": "POSTPONED"})
    cancelled = app_module.client_match_display_context({**base, "status": "CANCELLED"})

    assert live["client_temporal_label"] == "En directo · 67'"
    assert live_without_minute["client_temporal_label"] == "En directo"
    assert "0'" not in live_without_minute["client_temporal_label"]
    assert finished["client_temporal_label"] == "Final"
    assert finished_alias["client_temporal_label"] == "Final"
    assert finished_extra_time["client_temporal_label"] == "Final"
    assert finished["status_info"]["is_live"] is False
    assert postponed["client_temporal_label"] == "Aplazado"
    assert cancelled["client_temporal_label"] == "Cancelado"


def test_same_match_uses_same_temporal_contract_across_shared_surfaces(app_module):
    match = {
        "id": "temporal-cross-surface",
        "kickoff_iso": "2026-09-01T18:45:00Z",
        "match_date": "2026-09-01",
        "kickoff_time": "20:45",
        "home_team": "Bayern",
        "away_team": "Stuttgart",
        "competition_name": "Bundesliga",
        "status": "NS",
        "source": "qa",
        "updated_at": app_module.now_iso(),
    }
    favs = {"team": set(), "league": set(), "match": set(), "all": []}
    direct = app_module.client_match_display_context(copy.deepcopy(match))
    annotated = app_module.annotate_match(copy.deepcopy(match), favs=favs, include_timeline=False)
    complete = app_module._v931_prepare_complete_match(
        copy.deepcopy(match),
        {"date": "2026-09-01", "time": "20:45", "competition": "Bundesliga", "source": "qa"},
    )
    pick = app_module._v931_prepare_pick(
        {"id": "pick-temporal", "match_id": match["id"], "status": "published", "selection": "Local", "pick_type": "1X2", "odds": 2.0},
        {match["id"]: copy.deepcopy(match)},
    )

    labels = {
        direct["client_schedule_label"],
        annotated["client_schedule_label"],
        complete["client_schedule_label"],
        pick["client_schedule_label"],
    }
    assert len(labels) == 1
    assert pick["madrid_dt_iso"] == direct["madrid_dt_iso"]
    assert all(
        item["client_temporal_contract"] == "MATCH-TEMPORAL-CONTEXT-V1"
        for item in (direct, annotated, complete, pick)
    )


def test_track_record_separates_event_and_pick_dates(tmp_path):
    db_path = tmp_path / "track.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE matches(
            id TEXT PRIMARY KEY, match_date TEXT, kickoff_time TEXT, kickoff_iso TEXT,
            home_team TEXT, away_team TEXT, competition_name TEXT
        );
        CREATE TABLE picks(
            id TEXT PRIMARY KEY, match_id TEXT, match_date TEXT, created_at TEXT,
            home_team TEXT, away_team TEXT, competition_name TEXT
        );
        CREATE TABLE pick_grading_results(
            id TEXT PRIMARY KEY, pick_id TEXT, match_id TEXT, result_status TEXT,
            odds REAL, stake REAL, profit REAL, grading_score INTEGER,
            auto_validated INTEGER, graded_at TEXT, payload_json TEXT
        );
        CREATE TABLE pick_grading_runs(id TEXT PRIMARY KEY, started_at TEXT);
        """
    )
    conn.execute(
        "INSERT INTO matches VALUES(?,?,?,?,?,?,?)",
        ("m-1", "2026-08-30", "21:00", "2026-08-30T19:00:00Z", "Real Madrid", "Barcelona", "LaLiga"),
    )
    conn.execute(
        "INSERT INTO picks VALUES(?,?,?,?,?,?,?)",
        ("p-1", "m-1", "2026-08-30", "2026-08-30T18:00:00Z", "Real Madrid", "Barcelona", "LaLiga"),
    )
    conn.execute(
        "INSERT INTO pick_grading_results VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        ("g-1", "p-1", "m-1", "won", 2.0, 1.0, 1.0, 90, 1, "2026-08-30T22:00:00Z", "{}"),
    )
    conn.commit()
    conn.close()

    summary = pick_grading_summary(str(db_path))
    row = summary["recent_results"][0]
    assert row["event_datetime_label"].endswith("· 21:00")
    assert row["event_datetime_iso"] == "2026-08-30T21:00:00+02:00"
    assert row["pick_created_at_label"].endswith("· 20:00")
    assert row["temporal_contract"] == "MATCH-TEMPORAL-CONTEXT-V1"


def test_track_record_does_not_invent_missing_event_date():
    row = _enrich_recent_result({"pick_id": "p-missing", "payload_json": "{}"})
    assert row["event_datetime_label"] == ""
    assert format_madrid_client_date_label("") == ""
