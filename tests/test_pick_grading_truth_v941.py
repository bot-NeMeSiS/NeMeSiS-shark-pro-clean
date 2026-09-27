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
                home_score INTEGER,away_score INTEGER,updated_at TEXT);
            CREATE TABLE picks(id TEXT PRIMARY KEY,match_id TEXT,match_date TEXT,
                competition_name TEXT,home_team TEXT,away_team TEXT,pick_type TEXT,
                market TEXT,selection TEXT,odds REAL,confidence INTEGER,stake_units REAL,
                status TEXT,result_status TEXT,updated_at TEXT,created_at TEXT);
            INSERT INTO matches VALUES('qa-match','FT','2-0',2,0,'2026-09-27T18:00:00+00:00');
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


def test_track_record_months_and_pending_use_same_latest_evaluations(app_module,monkeypatch,grading_db):
    monkeypatch.setattr(app_module,"DB_PATH",grading_db)
    add_pick(grading_db,"one")
    add_pick(grading_db,"two")
    with sqlite3.connect(grading_db) as conn:
        conn.executemany("""INSERT INTO pick_grading_results
            (id,pick_id,result_status,odds,stake,profit,graded_at) VALUES(?,?,?,?,?,?,?)""",
            [("a","one","pending",2,1,None,"2026-08-01"),
             ("b","one","won",2,1,1,"2026-08-02"),
             ("c","one","lost",2,1,-1,"2026-09-01"),
             ("d","two","pending",2,1,None,"2026-09-01")])
    record=app_module.v742_track_record_context()
    assert record["by_month"]==[{"label":"2026-09","total":1,"profit":-1.0}]
    assert record["roi"]==-100.0
    assert record["winrate"]==0.0
    assert [r["pick_id"] for r in record["pending_results"]]==["two"]


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
