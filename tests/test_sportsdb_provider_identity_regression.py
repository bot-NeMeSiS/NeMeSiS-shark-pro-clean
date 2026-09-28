"""Regression audit recovered from historical SportsDB identity reconciliation work.

Tests only. No provider calls and no production-code changes.
"""
from datetime import datetime, timedelta
import sqlite3
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")


def _prepare(app_module, tmp_path, monkeypatch, name):
    db_path = tmp_path / name
    monkeypatch.setattr(app_module, "DB_PATH", str(db_path), raising=False)
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", None, raising=False)
    monkeypatch.setattr(app_module, "_SEEDING_DB_PATH", None, raising=False)
    app_module.init_db()
    return db_path


def _incoming(app_module, external_id, today, observed_at, *, status="Match Finished", home="2", away="1"):
    return app_module.sportsdb_event_to_match(
        {
            "idEvent": external_id,
            "strSport": "Soccer",
            "strHomeTeam": "Tartu Kalev",
            "strAwayTeam": "Jõhvi Phoenix",
            "strLeague": "Estonian Esiliiga B",
            "dateEvent": today,
            "strTime": "20:00:00",
            "strStatus": status,
            "intHomeScore": home,
            "intAwayScore": away,
        },
        provider_observed_at=observed_at,
    )


def test_sportsdb_provider_identity_reconciles_legacy_internal_id_atomically(app_module, tmp_path, monkeypatch):
    db_path = _prepare(app_module, tmp_path, monkeypatch, "identity.sqlite")
    today = datetime.now(MADRID).date().isoformat()
    legacy_id = "legacy-live-2440438"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO matches(
               id,external_id,match_date,kickoff_time,competition_name,
               home_team,away_team,status,minute,score,home_score,away_score,
               source,last_synced_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (legacy_id,"2440438",today,"20:00","Estonian Esiliiga B",
             "Tartu Kalev","Jõhvi Phoenix","LIVE","67","1-0","1","0",
             "TheSportsDB API","",""),
        )
        conn.execute(
            """INSERT INTO live_matches(
               id,match_id,status,minute,home_score,away_score,payload_json,source,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?)""",
            ("live-"+legacy_id,legacy_id,"LIVE","67","1","0","{}","TheSportsDB API",""),
        )

    observed_at = datetime.now(MADRID).isoformat()
    incoming = _incoming(app_module,"2440438",today,observed_at)
    assert incoming is not None and incoming["id"] != legacy_id
    result = app_module.upsert_sportsdb_matches([incoming])

    assert result["inserted"] == 0
    assert result["updated"] == 1
    assert result["provider_identity_rows_reconciled"] == 1
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute("SELECT * FROM matches WHERE external_id=?",("2440438",))]
        live_rows = conn.execute("SELECT COUNT(*) FROM live_matches WHERE match_id=?",(legacy_id,)).fetchone()[0]
    assert len(rows) == 1
    assert rows[0]["id"] == legacy_id
    assert rows[0]["last_synced_at"] == observed_at
    assert rows[0]["score"] == "2-1"
    assert app_module.v935_match_status_truth(rows[0])["is_finished"] is True
    assert live_rows == 0


def test_sportsdb_provider_identity_updates_all_legacy_duplicates_before_cleanup(app_module, tmp_path, monkeypatch):
    db_path = _prepare(app_module, tmp_path, monkeypatch, "duplicates.sqlite")
    today = datetime.now(MADRID).date().isoformat()
    with sqlite3.connect(db_path) as conn:
        for legacy_id in ("legacy-a-2429209","legacy-b-2429209"):
            conn.execute(
                """INSERT INTO matches(
                   id,external_id,match_date,kickoff_time,competition_name,
                   home_team,away_team,status,score,home_score,away_score,
                   source,last_synced_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (legacy_id,"2429209",today,"18:00","Estonian Esiliiga",
                 "Maardu Linnameeskond","Flora Tallinn U21","LIVE","0-0","0","0",
                 "TheSportsDB API","",""),
            )

    observed_at = datetime.now(MADRID).isoformat()
    incoming = app_module.sportsdb_event_to_match(
        {
            "idEvent":"2429209","strSport":"Soccer","strHomeTeam":"Maardu Linnameeskond",
            "strAwayTeam":"Flora Tallinn U21","strLeague":"Estonian Esiliiga",
            "dateEvent":today,"strTime":"18:00:00","strStatus":"Match Finished",
            "intHomeScore":"1","intAwayScore":"3",
        },
        provider_observed_at=observed_at,
    )
    result = app_module.upsert_sportsdb_matches([incoming])
    assert result["provider_identity_rows_reconciled"] == 2
    assert result["duplicates_removed"] >= 1
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows=[dict(r) for r in conn.execute("SELECT * FROM matches WHERE external_id=?",("2429209",))]
    assert len(rows) == 1
    assert rows[0]["last_synced_at"] == observed_at
    assert rows[0]["score"] == "1-3"


def test_sportsdb_provider_identity_rejects_older_snapshot_for_same_external_id(app_module, tmp_path, monkeypatch):
    db_path = _prepare(app_module, tmp_path, monkeypatch, "out-of-order.sqlite")
    today = datetime.now(MADRID).date().isoformat()
    newer_at = datetime.now(MADRID)
    older_at = newer_at - timedelta(minutes=5)
    legacy_id = "legacy-final-2440424"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO matches(
               id,external_id,match_date,kickoff_time,competition_name,
               home_team,away_team,status,score,home_score,away_score,
               source,last_synced_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (legacy_id,"2440424",today,"17:00","Estonian Esiliiga B",
             "Levadia U19 Tallinn","Tartu U21 Tammeka","FINALIZADO","2-0","2","0",
             "TheSportsDB API",newer_at.isoformat(),newer_at.isoformat()),
        )

    incoming = app_module.sportsdb_event_to_match(
        {
            "idEvent":"2440424","strSport":"Soccer","strHomeTeam":"Levadia U19 Tallinn",
            "strAwayTeam":"Tartu U21 Tammeka","strLeague":"Estonian Esiliiga B",
            "dateEvent":today,"strTime":"17:00:00","strStatus":"LIVE","strProgress":"2H",
            "intHomeScore":"1","intAwayScore":"0",
        },
        provider_observed_at=older_at.isoformat(),
    )
    result = app_module.upsert_sportsdb_matches([incoming])
    assert result["skipped"] == 1
    assert result["updated"] == 0
    with sqlite3.connect(db_path) as conn:
        conn.row_factory=sqlite3.Row
        row=dict(conn.execute("SELECT * FROM matches WHERE id=?",(legacy_id,)).fetchone())
    assert row["status"] == "FINALIZADO"
    assert row["score"] == "2-0"
    assert row["last_synced_at"] == newer_at.isoformat()
