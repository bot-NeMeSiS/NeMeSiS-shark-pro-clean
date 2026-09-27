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
