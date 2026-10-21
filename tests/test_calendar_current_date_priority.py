from datetime import date, datetime, timedelta
import sqlite3

from engines import v935_launch_trust_engine


def test_calendar_snapshot_keeps_today_when_later_fixtures_fill_the_read_limit(
    app_module, tmp_path, monkeypatch
):
    """A large future sync must not push today's fixtures out of the snapshot."""
    # Keep both the fixture date and lifecycle clock deterministic. A fixed
    # 20:00 kickoff must remain upcoming even when CI runs after that time.
    anchor = date.fromisoformat(app_module.today_iso())
    monkeypatch.setattr(
        app_module,
        "today_iso",
        lambda offset=0: (anchor + timedelta(days=offset)).isoformat(),
    )
    lifecycle_now = datetime(
        anchor.year,
        anchor.month,
        anchor.day,
        12,
        0,
        tzinfo=v935_launch_trust_engine.MADRID_TZ,
    )
    monkeypatch.setattr(
        v935_launch_trust_engine,
        "madrid_now",
        lambda now=None: lifecycle_now,
    )
    database = tmp_path / "calendar.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute(
        """CREATE TABLE matches (
            id TEXT PRIMARY KEY,
            match_id TEXT,
            external_id TEXT,
            match_date TEXT,
            kickoff_iso TEXT,
            kickoff_time TEXT,
            match_time TEXT,
            home_team TEXT,
            away_team TEXT,
            competition_name TEXT,
            league_name TEXT,
            country TEXT,
            source TEXT,
            status TEXT,
            home_score INTEGER,
            away_score INTEGER,
            updated_at TEXT
        )"""
    )

    def insert_fixture(match_id, match_date, kickoff_time, updated_at):
        connection.execute(
            """INSERT INTO matches (
                id, match_id, external_id, match_date, kickoff_iso,
                kickoff_time, match_time, home_team, away_team,
                competition_name, league_name, country, source, status,
                home_score, away_score, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                match_id,
                match_id,
                match_id,
                match_date.isoformat(),
                f"{match_date.isoformat()}T{kickoff_time}:00+02:00",
                kickoff_time,
                kickoff_time,
                f"Local {match_id}",
                f"Visitor {match_id}",
                "Competition",
                "Competition",
                "Spain",
                "API_FOOTBALL",
                "NS",
                None,
                None,
                updated_at,
            ),
        )

    insert_fixture(
        "today-match",
        anchor,
        "20:00",
        "2026-10-19T20:00:00+02:00",
    )
    for index in range(900):
        match_date = anchor + timedelta(days=1 + index % 7)
        insert_fixture(
            f"future-{index:04d}",
            match_date,
            "12:00",
            f"2026-10-20T00:{index % 60:02d}:{index % 60:02d}+02:00",
        )
    connection.commit()
    connection.close()
    monkeypatch.setattr(app_module, "DB_PATH", str(database))

    assert app_module._public_sports_cache_key().startswith(
        "v934:sports:public-summary-v2:"
    )
    rows, metadata = app_module._v931_read_table_rows("matches", 800)

    assert metadata["status"] == "ok", metadata
    assert len(rows) == 800
    assert rows[0]["id"] == "today-match"
    assert "today-match" in {row["id"] for row in rows}

    summary = app_module._build_public_home_sports_summary()
    assert summary["valid_matches_today_count"] == 1
    home_agenda = app_module.home_matchday_context(summary, now=lifecycle_now)
    assert home_agenda["today"]["total"] == 1
    assert [
        match["id"]
        for group in home_agenda["today"]["groups"]
        for match in group["matches"]
    ] == ["today-match"]
    with app_module.app.test_request_context("/calendario?lane=today"):
        calendar = app_module.v940_calendar_context(summary, "today", anchor.isoformat())
    assert [match["id"] for match in calendar["matches"]] == ["today-match"]
