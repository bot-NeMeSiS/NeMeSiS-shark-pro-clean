"""Settlement and history must reflect published picks and recorded amounts."""
import sqlite3

import pytest

from engines import pick_grading_engine as grading


@pytest.fixture
def grading_db(tmp_path):
    path=str(tmp_path/"grading-truth.sqlite")
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE matches(id TEXT PRIMARY KEY,status TEXT,score TEXT,
                home_score INTEGER,away_score INTEGER,match_date TEXT,kickoff_time TEXT,updated_at TEXT);
            CREATE TABLE picks(id TEXT PRIMARY KEY,match_id TEXT,match_date TEXT,
                competition_name TEXT,home_team TEXT,away_team TEXT,pick_type TEXT,
                market TEXT,selection TEXT,odds REAL,confidence INTEGER,stake_units REAL,
                status TEXT,result_status TEXT,updated_at TEXT,created_at TEXT);
            INSERT INTO matches(id,status,score,home_score,away_score,match_date,kickoff_time,updated_at)
            VALUES('qa-match','FT','2-0',2,0,'2026-09-27','19:00','2026-09-27T18:00:00+00:00');
        """)
    grading.ensure_pick_grading_schema(path)
    return path


def add_pick(path,identifier,status="published",stake=1,result="pending"):
    with sqlite3.connect(path) as conn:
        conn.execute("""INSERT INTO picks(id,match_id,home_team,away_team,pick_type,selection,
                     odds,confidence,stake_units,status,result_status,updated_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (identifier,"qa-match","QA Home","QA Away","1x2","1",2,70,stake,status,result,"2026-09-27"))


def test_grading_does_not_publish_drafts_or_archived_picks(grading_db):
    for status in ("draft","archived","review","published"):
        add_pick(grading_db,status,status)
    report=grading.run_pick_grading(grading_db,apply=True)
    assert report["picks_checked"]==1
    with sqlite3.connect(grading_db) as conn:
        assert dict(conn.execute("SELECT id,status FROM picks"))=={
            "draft":"draft","archived":"archived","review":"review","published":"won"}
        assert conn.execute("SELECT pick_id FROM pick_grading_results").fetchall()==[("published",)]


def test_grading_respects_recorded_manual_settlement(grading_db):
    add_pick(grading_db,"qa-manual",result="void")
    grading.run_pick_grading(grading_db,apply=True)
    with sqlite3.connect(grading_db) as conn:
        assert conn.execute("SELECT result_status FROM picks").fetchone()[0]=="void"


@pytest.mark.parametrize("stake", [None,"",0,-1,"invalid",float("nan"),float("inf")])
def test_missing_or_invalid_stake_never_creates_financial_result(stake):
    grade=grading.grade_pick({"result_status":"won","odds":2.5,"stake_units":stake})
    assert grade["stake"] is None
    assert grade["profit"] is None


@pytest.mark.parametrize("odds", [None,"",0,1,-1,"invalid",float("nan"),float("inf")])
def test_missing_or_invalid_odds_never_creates_financial_result(odds):
    grade=grading.grade_pick({"result_status":"lost","odds":odds,"stake_units":2})
    assert grade["odds"] is None
    assert grade["profit"] is None


def test_missing_stake_stays_out_of_real_history(grading_db):
    add_pick(grading_db,"qa-no-stake",stake=None)
    grading.run_pick_grading(grading_db,apply=True)
    summary=grading.pick_grading_summary(grading_db)
    assert summary["evaluable_total"]==0
    assert summary["non_evaluable"]==1
    assert summary["recent_results"]==[]


@pytest.mark.parametrize("score,home,away", [("n/a-n/a",None,None),("-1-0",None,None),
    ("1.5-0",None,None),("2-0","not available",0),("2-0",float("nan"),0)])
def test_invalid_scores_cannot_be_settled_as_zero(score,home,away):
    grade=grading.grade_pick({"match_status":"FT","score":score,"home_score":home,
        "away_score":away,"pick_type":"1x2","selection":"X","odds":2,"stake_units":1})
    assert grade["result_status"]=="pending"
    assert grade["auto_validated"]==0


def test_valid_recorded_amounts_keep_expected_profit():
    for result,expected in (("won",3.0),("lost",-2.0),("void",0.0)):
        grade=grading.grade_pick({"result_status":result,"odds":2.5,"stake_units":2})
        assert grade["stake"]==2
        assert grade["odds"]==2.5
        assert grade["profit"]==expected


@pytest.mark.parametrize("latest,profit,closed", [("lost",-1,1),("pending",None,0)])
def test_history_counts_only_latest_evaluation_without_deleting_audit(grading_db,latest,profit,closed):
    add_pick(grading_db,"same-pick")
    with sqlite3.connect(grading_db) as conn:
        conn.executemany("""INSERT INTO pick_grading_results
            (id,pick_id,result_status,odds,stake,profit,graded_at) VALUES(?,?,?,?,?,?,?)""",
            [("old","same-pick","won",2,1,1,"2026-08-01T12:00:00+00:00"),
             ("new","same-pick",latest,2,1,profit,"2026-09-01T12:00:00+00:00")])
        before=conn.execute("SELECT * FROM pick_grading_results ORDER BY id").fetchall()
    summary=grading.pick_grading_summary(grading_db)
    assert summary["graded_total"]==1
    assert summary["evaluable_total"]==closed
    assert summary["won"]==0
    assert summary["lost"]==closed
    assert summary["pending_review"]==1-closed
    assert summary["profit"]==(profit or 0)
    assert [row["id"] for row in summary["recent_results"]]==(["new"] if closed else [])
    with sqlite3.connect(grading_db) as conn:
        assert conn.execute("SELECT * FROM pick_grading_results ORDER BY id").fetchall()==before


def test_latest_evaluation_tie_uses_last_stored_row(grading_db):
    add_pick(grading_db,"same-pick")
    with sqlite3.connect(grading_db) as conn:
        for identifier,result in (("z-old","won"),("a-new","lost")):
            conn.execute("""INSERT INTO pick_grading_results
                (id,pick_id,result_status,odds,stake,profit,graded_at) VALUES(?,?,?,?,?,?,?)""",
                (identifier,"same-pick",result,2,1,1 if result=="won" else -1,"2026-09-01"))
    summary=grading.pick_grading_summary(grading_db)
    assert summary["won"]==0 and summary["lost"]==1
    assert summary["stake_total"]==1


def test_client_history_scopes_paid_tiers_and_filters_before_recent_limit(grading_db):
    add_pick(grading_db,"old-free-won",result="won")
    for index in range(12):
        add_pick(grading_db,f"new-pro-lost-{index}",result="lost")
    add_pick(grading_db,"new-elite-won",result="won")
    with sqlite3.connect(grading_db) as conn:
        conn.execute("ALTER TABLE picks ADD COLUMN membership_required TEXT")
        conn.execute("UPDATE picks SET membership_required='FREE',created_at='2020-01-01' WHERE id='old-free-won'")
        conn.execute("UPDATE picks SET membership_required='PRO',created_at='2026-02-01' WHERE id LIKE 'new-pro-lost-%'")
        conn.execute("UPDATE picks SET membership_required='ELITE',created_at='2026-03-01' WHERE id='new-elite-won'")
        conn.executemany("""INSERT INTO pick_grading_results
            (id,pick_id,result_status,odds,stake,profit,graded_at) VALUES(?,?,?,?,?,?,?)""",
            [("grade-old-free-won","old-free-won","won",2,1,1,"2020-01-01")]
            + [(f"grade-pro-{index}",f"new-pro-lost-{index}","lost",2,1,-1,f"2026-02-{index+1:02d}") for index in range(12)]
            + [("grade-new-elite-won","new-elite-won","won",2,1,1,"2026-03-01")])

    summary=grading.pick_grading_summary(
        grading_db,visible_membership="PRO",result_filter="won",recent_limit=10,
    )
    assert summary["won"]==1
    assert summary["lost"]==12
    assert [row["pick_id"] for row in summary["recent_results"]]==["old-free-won"]
    assert summary["recent_runs"]==[]


def test_free_history_engine_fails_closed(grading_db):
    add_pick(grading_db,"legacy-free-won",result="won")
    with sqlite3.connect(grading_db) as conn:
        conn.execute("ALTER TABLE picks ADD COLUMN membership_required TEXT")
        conn.execute("UPDATE picks SET membership_required='FREE' WHERE id='legacy-free-won'")
        conn.execute("""INSERT INTO pick_grading_results
            (id,pick_id,result_status,odds,stake,profit,graded_at) VALUES(?,?,?,?,?,?,?)""",
            ("grade-free","legacy-free-won","won",2,1,1,"2026-01-01"))
    summary=grading.pick_grading_summary(grading_db,visible_membership="FREE")
    assert summary["graded_total"]==0
    assert summary["recent_results"]==[]
    assert summary["recent_runs"]==[]


def test_track_record_months_and_pending_use_same_latest_evaluations(app_module,monkeypatch,grading_db):
    monkeypatch.setattr(app_module,"DB_PATH",grading_db)
    add_pick(grading_db,"one")
    add_pick(grading_db,"two")
    with sqlite3.connect(grading_db) as conn:
        conn.execute("""UPDATE picks SET match_date='2026-09-27 18:00',
                       competition_name='QA League', market='Total goles',
                       selection='Over 2.5' WHERE id='two'""")
        conn.execute("UPDATE matches SET match_date='2026-09-27',kickoff_time='19:00' WHERE id='qa-match'")
        conn.executemany("""INSERT INTO pick_grading_results
            (id,pick_id,result_status,odds,stake,profit,reason,graded_at) VALUES(?,?,?,?,?,?,?,?)""",
            [("a","one","pending",2,1,None,"obsolete pending","2026-08-01"),
             ("b","one","won",2,1,1,"decided","2026-08-02"),
             ("c","one","lost",2,1,-1,"decided","2026-09-01"),
             ("d","two","pending",2,1,None,"Evidence is not conclusive yet.","2026-09-01")])
    record=app_module.v742_track_record_context()
    assert record["by_month"]==[{"label":"2026-09","total":1,"profit":-1.0}]
    assert record["roi"]==-100.0
    assert record["winrate"]==0.0
    assert [r["pick_id"] for r in record["pending_results"]]==["two"]
    pending = record["pending_results"][0]
    assert pending["home_team"] == "QA Home"
    assert pending["away_team"] == "QA Away"
    assert pending["competition_name"] == "QA League"
    assert pending["market"] == "Total goles"
    assert pending["selection"] == "Over 2.5"
    assert pending["event_datetime"] == "2026-09-27 19:00"
    assert pending["match_status"] == "FT"
    assert pending["score"] == "2-0"
    assert pending["reason"] == "Evidence is not conclusive yet."


def test_admin_pending_context_tolerates_legacy_schema_without_optional_columns(app_module,monkeypatch,tmp_path):
    path=str(tmp_path/"legacy-pending.sqlite")
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE picks(id TEXT PRIMARY KEY,status TEXT);
            CREATE TABLE matches(home_team TEXT);
            CREATE TABLE pick_grading_results(
                id TEXT PRIMARY KEY,pick_id TEXT,match_id TEXT,result_status TEXT,
                odds REAL,stake REAL,profit REAL,grading_score INTEGER,
                auto_validated INTEGER,confidence_after INTEGER,graded_at TEXT
            );
            INSERT INTO picks(id,status) VALUES('legacy-pick','published');
            INSERT INTO pick_grading_results(id,pick_id,result_status,odds,stake,profit,
                grading_score,auto_validated,confidence_after,graded_at)
                VALUES('legacy-grade','legacy-pick','pending',2,1,0,30,0,40,'2026-09-27');
        """)
    monkeypatch.setattr(app_module,"DB_PATH",path)
    monkeypatch.setattr(app_module,"is_admin_session",lambda:True)
    record=app_module.v742_track_record_context()
    assert [row["pick_id"] for row in record["pending_results"]]==["legacy-pick"]
    pending=record["pending_results"][0]
    assert pending["home_team"]==pending["away_team"]==""
    assert pending["market"]==pending["selection"]==""
    assert pending["reason"]==pending["event_datetime"]==""


def test_admin_pending_context_preserves_full_pick_match_time(app_module,monkeypatch,tmp_path):
    path=str(tmp_path/"legacy-pick-datetime.sqlite")
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE picks(id TEXT PRIMARY KEY,status TEXT,match_date TEXT,match_time TEXT);
            CREATE TABLE pick_grading_results(
                id TEXT PRIMARY KEY,pick_id TEXT,match_id TEXT,result_status TEXT,
                odds REAL,stake REAL,profit REAL,grading_score INTEGER,
                auto_validated INTEGER,confidence_after INTEGER,reason TEXT,graded_at TEXT
            );
            INSERT INTO picks(id,status,match_date,match_time)
                VALUES('legacy-datetime-pick','published','2026-10-25','2026-10-25 19:00');
            INSERT INTO pick_grading_results(id,pick_id,result_status,reason,graded_at)
                VALUES('legacy-datetime-grade','legacy-datetime-pick','pending','review','2026-10-22');
        """)
    monkeypatch.setattr(app_module,"DB_PATH",path)
    monkeypatch.setattr(app_module,"is_admin_session",lambda:True)
    pending=app_module.v742_track_record_context()["pending_results"][0]
    assert pending["event_datetime"]=="2026-10-25 19:00"
    assert "19:00" in pending["event_datetime_label"]
    assert pending["event_datetime_label"].endswith("Madrid")


@pytest.mark.parametrize("market,selection", [
    ("Córners totales", "Over 8.5"),
    ("Total goles primera parte", "Over 0.5"),
    ("Total local", "QA Home over 1.5"),
    ("Hándicap asiático", "QA Home -1.5"),
    ("Resultado exacto", "2-0"),
    ("Goleador", "QA Player marca"),
])
def test_unsupported_markets_never_use_full_time_team_score(market,selection):
    grade=grading.grade_pick({
        "match_status":"FT","score":"3-1","home_score":3,"away_score":1,
        "pick_type":market,"selection":selection,"odds":2.0,"stake_units":1,
        "home_team":"QA Home","away_team":"QA Away",
    })
    assert grade["result_status"]=="pending"
    assert grade["auto_validated"]==0
    assert "no soportado" in grade["reason"].lower() or "necesita" in grade["reason"].lower() or "no derivable" in grade["reason"].lower()


@pytest.mark.parametrize("selection,expected", [("Over 2.0","void"),("Under 2.0","void"),("Over 2.25","pending"),("Under 2.75","pending")])
def test_goal_lines_do_not_turn_push_or_quarter_lines_into_losses(selection,expected):
    grade=grading.grade_pick({
        "match_status":"FT","score":"1-1","home_score":1,"away_score":1,
        "pick_type":"Total goles","selection":selection,"odds":1.9,"stake_units":1,
    })
    assert grade["result_status"]==expected
    assert grade["auto_validated"]==(1 if expected=="void" else 0)


def test_history_excludes_orphan_and_draft_evaluations_from_real_metrics(grading_db):
    add_pick(grading_db,"eligible",status="published")
    add_pick(grading_db,"draft-evaluation",status="draft")
    with sqlite3.connect(grading_db) as conn:
        conn.executemany("""INSERT INTO pick_grading_results
            (id,pick_id,result_status,odds,stake,profit,graded_at,auto_validated)
            VALUES(?,?,?,?,?,?,?,?)""",[
            ("g-eligible","eligible","won",2,1,1,"2026-09-01",1),
            ("g-draft","draft-evaluation","won",2,1,1,"2026-09-01",1),
            ("g-orphan","missing-pick","lost",2,1,-1,"2026-09-01",1),
        ])
    summary=grading.pick_grading_summary(grading_db)
    assert summary["graded_total"]==1
    assert summary["evaluable_total"]==1
    assert summary["won"]==1 and summary["lost"]==0
    assert summary["stake_total"]==1
    assert summary["profit"]==1
    assert [row["pick_id"] for row in summary["recent_results"]]==["eligible"]


@pytest.mark.parametrize("status", [
    "pending", "halftime", "penalties", "unfinished", "not finished",
    "NS", "1H", "HT", "2H", "ET", "BT", "P", "LIVE", "SUSP", "INT", "PST", "CANC",
])
def test_nonterminal_or_ambiguous_match_status_never_settles_pick(status):
    grade = grading.grade_pick({
        "match_status": status,
        "score": "2-1",
        "home_score": 2,
        "away_score": 1,
        "pick_type": "1x2",
        "selection": "1",
        "odds": 2.0,
        "stake_units": 1,
    })
    assert grading.normalize_status(status) == "pending"
    assert grade["result_status"] == "pending"
    assert grade["auto_validated"] == 0
    assert grade["profit"] is None


@pytest.mark.parametrize("status", [
    "FT", "Match Finished", "Finished", "Finalizado",
])
def test_explicit_terminal_match_status_can_settle_pick(status):
    grade = grading.grade_pick({
        "match_status": status,
        "score": "2-1",
        "home_score": 2,
        "away_score": 1,
        "pick_type": "1x2",
        "selection": "1",
        "odds": 2.0,
        "stake_units": 1,
    })
    assert grading.normalize_status(status) == "finished"
    assert grade["result_status"] == "won"
    assert grade["auto_validated"] == 1
    assert grade["profit"] == 1.0


@pytest.mark.parametrize("status", [
    "AET", "PEN", "Finished after extra time", "Match Finished After Penalty",
    "Match Finished After Penalties", "Finalizado tras prórroga",
])
def test_terminal_extra_time_or_penalty_score_does_not_settle_regulation_market(status):
    assert grading.normalize_status(status) == "finished"
    grade = grading.grade_pick({
        "match_status": status,
        "score": "2-1",
        "pick_type": "1x2",
        "selection": "1",
        "odds": 2.0,
        "stake_units": 1,
    })
    assert grade["result_status"] == "pending"
    assert grade["auto_validated"] == 0
    assert grade["profit"] is None


@pytest.mark.parametrize("market,selection", [
    ("1H 1X2", "1"),
    ("BTTS", "No disponible"),
    ("1X2", "QA Home or QA Away"),
    ("1X2", "QA Home no pierde"),
    ("BTTS", "Yes or no"),
])
def test_ambiguous_period_or_selection_never_settles(market, selection):
    grade = grading.grade_pick({
        "match_status": "FT",
        "score": "2-0",
        "pick_type": market,
        "selection": selection,
        "home_team": "QA Home",
        "away_team": "QA Away",
        "odds": 2.0,
        "stake_units": 1,
    })
    assert grade["result_status"] == "pending"
    assert grade["auto_validated"] == 0
    assert grade["profit"] is None


@pytest.mark.parametrize("market,selection,score,expected", [
    ("over_under_25", "Under 2.5", "2-0", "won"),
    ("Más/Menos 2.5 goles", "Menos de 2.5 goles", "2-0", "won"),
    ("Goles", "Más de 1.5 goles", "2-0", "won"),
    ("BTTS", "No", "2-0", "won"),
    ("BTTS", "Sí", "2-0", "lost"),
    ("1X2", "Local gana", "2-0", "won"),
    ("Doble oportunidad", "Local o visitante (sin empate)", "1-1", "lost"),
    ("DNB", "Local empate no apuesta", "1-1", "void"),
])
def test_supported_market_and_selection_are_settled_only_from_exact_choices(market, selection, score, expected):
    grade = grading.grade_pick({
        "match_status": "FT",
        "score": score,
        "pick_type": "single",
        "market": market,
        "selection": selection,
        "home_team": "QA Home",
        "away_team": "QA Away",
        "odds": 2.0,
        "stake_units": 1,
    })
    assert grade["result_status"] == expected


def test_apply_keeps_published_pick_pending_until_match_status_is_terminal(grading_db):
    add_pick(grading_db, "live-match-pick")
    with sqlite3.connect(grading_db) as conn:
        conn.execute(
            "UPDATE matches SET status='halftime', score='2-1', home_score=2, away_score=1 WHERE id='qa-match'"
        )

    report = grading.run_pick_grading(grading_db, apply=True)

    assert report["pending"] == 1
    assert report["auto_validated"] == 0
    assert report["profit"] == 0.0
    with sqlite3.connect(grading_db) as conn:
        pick = conn.execute("SELECT status, result_status FROM picks WHERE id='live-match-pick'").fetchone()
        result = conn.execute(
            "SELECT result_status, auto_validated, profit FROM pick_grading_results WHERE pick_id='live-match-pick'"
        ).fetchone()
    assert pick == ("published", "pending")
    assert result == ("pending", 0, None)
