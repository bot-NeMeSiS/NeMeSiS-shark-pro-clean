"""Dense-day admission must retain useful candidates without certifying LIVE."""
from datetime import datetime, timedelta, timezone
import json
import re
import sqlite3

import pytest


@pytest.mark.parametrize('hour,minute', [(0,0),(0,1),(0,19),(0,20),(12,30),(23,59)])
def test_actual_app_test_fixture_stays_on_current_day_at_midnight(hour, minute):
    # Load only the stdlib fixture helper; do not import App or replace its clock.
    import ast
    from pathlib import Path
    from zoneinfo import ZoneInfo
    source = Path(__file__).with_name('v991_api_prepare_only_cases.py').read_text(encoding='utf-8')
    node = next(n for n in ast.parse(source).body
                if isinstance(n, ast.FunctionDef) and n.name=='current_day_live_kickoff')
    namespace = {'timedelta':timedelta}
    exec(compile(ast.Module(body=[node],type_ignores=[]), '<fixture-helper>', 'exec'),namespace)
    now = datetime(2026,10,26,hour,minute,17,tzinfo=ZoneInfo('Europe/Madrid'))
    kickoff = namespace['current_day_live_kickoff'](now)
    assert kickoff.date()==now.date() and kickoff<=now
    assert kickoff==max((now-timedelta(minutes=20)).replace(second=0,microsecond=0),
                        now.replace(hour=0,minute=0,second=0,microsecond=0))


def _database(tmp_path, rows, *, status_column=True):
    path = tmp_path / "dense-calendar.sqlite3"
    status = ", status TEXT" if status_column else ""
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE matches (id TEXT PRIMARY KEY, match_date TEXT, "
            "kickoff_iso TEXT, updated_at TEXT, last_synced_at TEXT" + status + ")"
        )
        names = "id,match_date,kickoff_iso,updated_at,last_synced_at"
        if status_column:
            names += ",status"
        connection.executemany(
            "INSERT INTO matches (" + names + ") VALUES (" +
            ",".join("?" for _ in names.split(",")) + ")", rows
        )
    return path


def _row(key, day, status, *, kickoff="01:00", observation=None):
    observed = observation or f"{day}T00:01:00+00:00"
    return (key, day, f"{day}T{kickoff}:00+00:00", observed, observed, status)


def test_dense_today_admits_live_and_upcoming_before_early_finished_rows(
    app_module, tmp_path, monkeypatch
):
    today = app_module.today_iso()
    rows = [_row(f"finished-{i:04}", today, "FT") for i in range(1004)]
    rows += [
        _row("fresh-live", today, "2H", kickoff="21:00"),
        _row("half-time", today, "HT", kickoff="21:01"),
        _row("next-today", today, "NS", kickoff="23:30"),
        _row("next-translated", today, "PROGRAMADO", kickoff="23:35"),
    ]
    database = _database(tmp_path, rows)
    before = database.read_bytes()
    monkeypatch.setattr(app_module, "DB_PATH", str(database))

    selected, metadata = app_module._v931_read_table_rows("matches", 800)

    assert metadata["status"] == "ok", metadata
    assert len(selected) == 800
    assert {row["id"] for row in selected[:2]} == {"fresh-live", "half-time"}
    assert [row["id"] for row in selected[2:4]] == ["next-today", "next-translated"]
    assert sum(row["status"] == "FT" for row in selected) == 796
    # Admission only: no invented provider clock, lease or native LIVE proof.
    expected = {row[0]: dict(zip(
        ("id", "match_date", "kickoff_iso", "updated_at", "last_synced_at", "status"), row
    )) for row in rows}
    assert all(row == expected[row["id"]] for row in selected)
    assert database.read_bytes() == before


def test_recent_live_candidate_is_not_starved_by_older_live_labels(
    app_module, tmp_path, monkeypatch
):
    today = app_module.today_iso()
    now = datetime.now(timezone.utc)
    stale = (now - timedelta(hours=3)).isoformat()
    fresh = now.isoformat()
    rows = [_row(f"stale-{i:04}", today, "LIVE", observation=stale) for i in range(900)]
    rows += [_row("fresh-later-kickoff", today, "1H", kickoff="23:00", observation=fresh)]
    database = _database(tmp_path, rows)
    monkeypatch.setattr(app_module, "DB_PATH", str(database))

    selected, metadata = app_module._v931_read_table_rows("matches", 800)

    assert metadata["status"] == "ok", metadata
    assert len(selected) == 800
    assert selected[0]["id"] == "fresh-later-kickoff"
    assert selected[0]["last_synced_at"] == fresh


@pytest.mark.parametrize("live_status", ["1H", "2H", "HT", "ET", "BT", "P", "LIVE", "EN_DIRECTO"])
def test_admission_status_does_not_confuse_live_penalties_with_final_pen(
    app_module, tmp_path, monkeypatch, live_status
):
    today = app_module.today_iso()
    database = _database(tmp_path, [
        _row("final-pen", today, "PEN"),
        _row("postponed", today, "PST"),
        _row("candidate", today, live_status, kickoff="23:00"),
        _row("scheduled", today, "NS", kickoff="23:30"),
    ])
    monkeypatch.setattr(app_module, "DB_PATH", str(database))
    selected, metadata = app_module._v931_read_table_rows("matches", 2)
    assert metadata["status"] == "ok", metadata
    assert [row["id"] for row in selected] == ["candidate", "scheduled"]


def test_status_priority_does_not_move_future_or_historical_labels_before_today(
    app_module, tmp_path, monkeypatch
):
    today = app_module.today_iso()
    tomorrow = app_module.today_iso(1)
    yesterday = app_module.today_iso(-1)
    database = _database(tmp_path, [
        _row("today-result", today, "FT"),
        _row("tomorrow-label", tomorrow, "LIVE"),
        _row("yesterday-label", yesterday, "LIVE"),
    ])
    monkeypatch.setattr(app_module, "DB_PATH", str(database))
    selected, metadata = app_module._v931_read_table_rows("matches", 3)
    assert metadata["status"] == "ok", metadata
    assert [row["id"] for row in selected] == ["today-result", "tomorrow-label", "yesterday-label"]


def test_legacy_schema_without_status_retains_date_and_kickoff_order(
    app_module, tmp_path, monkeypatch
):
    today = app_module.today_iso()
    rows = [row[:-1] for row in [
        _row("late", today, "NS", kickoff="22:00"),
        _row("early", today, "FT", kickoff="01:00"),
    ]]
    database = _database(tmp_path, rows, status_column=False)
    monkeypatch.setattr(app_module, "DB_PATH", str(database))
    selected, metadata = app_module._v931_read_table_rows("matches", 800)
    assert metadata["status"] == "ok", metadata
    assert [row["id"] for row in selected] == ["early", "late"]


@pytest.mark.parametrize('only_stale', [False, True])
def test_dense_day_real_http_retains_fresh_live_and_rejects_stale_candidate(
    app_module, tmp_path, monkeypatch, only_stale
):
    """Use the real SQLite reader, cache builder, normalizer and registered GET."""
    database = tmp_path / "dense-real-http.sqlite3"
    monkeypatch.setattr(app_module, "DB_PATH", str(database))
    app_module.seed_core()
    now = datetime.now(app_module.TZ)
    # Keep this dense-today fixture on its actual Madrid day when CI runs
    # just after midnight; the SQL/date and native kickoff must agree.
    start = max(
        now - timedelta(minutes=20),
        now.replace(hour=0, minute=0, second=0, microsecond=0),
    )
    today = now.date().isoformat()
    common = {
        "match_date": today, "source": "api_football_live", "sport_key": "soccer",
        "competition_key": "laliga", "competition_id": "140",
        "competition_name": "LaLiga", "league_name": "LaLiga", "country": "Spain",
        "season": str(now.year), "home_team": "Synthetic Home", "away_team": "Synthetic Away",
        "home_team_id": "99201", "away_team_id": "99202", "minute": 20,
        "home_score": 1, "away_score": 0, "updated_at": now.isoformat(),
        "last_synced_at": now.isoformat(),
    }
    live = dict(common, id="af-992001", external_id="992001", status="1H",
                kickoff_iso=start.isoformat(), kickoff_time=start.strftime("%H:%M"),
                match_time=start.strftime("%H:%M"))
    live["raw_json"] = json.dumps({
        "fixture": {"id": 992001, "date": start.isoformat(), "status": {"short": "1H", "elapsed": 20}},
        "league": {"id": 140, "name": "LaLiga", "country": "Spain", "season": now.year},
        "teams": {"home": {"id": 99201, "name": live["home_team"]},
                  "away": {"id": 99202, "name": live["away_team"]}},
        "goals": {"home": 1, "away": 0},
    })
    old = (now - timedelta(hours=3)).isoformat()
    stale = dict(live, id="af-992002", external_id="992002", updated_at=old,
                 last_synced_at=old, raw_json="")
    if only_stale:
        live.update(updated_at=old, last_synced_at=old)
    finished = [dict(common, id=f"finished-{i:04}", status="FT", minute=90,
                     kickoff_iso=f"{today}T00:01:00+00:00", kickoff_time="00:01",
                     match_time="00:01") for i in range(1004)]
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM matches")
        connection.execute("DELETE FROM picks")
        connection.execute("DELETE FROM competitions WHERE key='laliga'")
        connection.execute(
            "INSERT INTO competitions (key,name,country,source,external_id) VALUES (?,?,?,?,?)",
            ("laliga", "LaLiga", "Spain", "API_FOOTBALL", "140"),
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(matches)")}
        for row in finished + [live, stale]:
            values = {key: value for key, value in row.items() if key in columns}
            connection.execute(
                "INSERT INTO matches (" + ",".join(values) + ") VALUES (" +
                ",".join("?" for _ in values) + ")", tuple(values.values())
            )
        connection.commit()
        before = connection.execute("SELECT * FROM matches ORDER BY id").fetchall()
    response = app_module.app.test_client().get(
        "/api/realtime/sports",
        query_string={"scope": "matches", "consumer": "directo-v2", "f": "live"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["counts"]["live"] == (0 if only_stale else 1)
    # The transport retains the whole admitted cohort; only descriptor.view is
    # filtered to LIVE. Finished observations must not disappear to pass QA.
    frames = {row["id"]: row for row in payload["matches"]}
    expected_frames = 798 if only_stale else 799
    assert len(payload["matches"]) == len(frames) == expected_frames
    assert stale["id"] not in frames
    assert len(set(frames) & {row["id"] for row in finished}) == 798
    if only_stale:
        assert live["id"] not in frames
        assert payload['counts']['stale_live'] == 2
        assert payload['realtime_live_status'] == 'stale'
        assert all(row['realtime_state']['is_live'] is False for row in frames.values())
        page = app_module.app.test_client().get('/live')
        assert page.status_code == 200
        html = page.get_data(as_text=True)
        assert 'data-directo-delayed="true"' in html
        notice = re.search(r'<p\b[^>]*\bdata-directo-notice\b[^>]*>', html)
        assert notice and not re.search(r'\bhidden\b', notice.group())
    else:
        assert live["id"] in frames
        assert frames[live["id"]]["realtime_state"]["score_home"] == 1
        assert frames[live["id"]]["realtime_state"]["is_live"] is True
    descriptor = payload["fixture_identity"]
    assert descriptor["state"] == "ESTABLISHED_FOR_EMITTED_COHORT"
    assert descriptor["coverage"]["emitted_observations"] == expected_frames
    assert descriptor["view"]["groups_before_limit"] == (0 if only_stale else 1)
    assert [row["id"] for row in descriptor["view"]["members"]] == ([] if only_stale else [live["id"]])
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT * FROM matches ORDER BY id").fetchall() == before
        assert connection.execute("SELECT COUNT(*) FROM picks").fetchone()[0] == 0
