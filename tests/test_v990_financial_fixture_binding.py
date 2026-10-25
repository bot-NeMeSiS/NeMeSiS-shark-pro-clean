"""Synthetic financial identity contracts. No App/HTTP/providers/real accounts."""
from copy import deepcopy
from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import json
import sqlite3
import uuid

import pytest
from engines import client_combi_store as store
from engines import combi_advisor_engine as advisor
from engines.combi_draft_review import review_draft
from engines.combi_match_catalogue import choice_id

NOW = datetime(2026, 10, 25, 11, 19, 8, tzinfo=timezone.utc)
BOOK = "SYNTHETIC SAME BOOK"


def match(local, native, *, sports=False, different=False):
    home, away = (("Other Home", "Other Away") if different else
                  ("Granada", "Real Valladolid") if sports else ("Granada CF", "Real Valladolid"))
    kickoff = (NOW + timedelta(days=1, hours=2 if different else 1)).isoformat()
    row = {"id": local, "external_id": native, "sport_key": "soccer", "match_date": kickoff[:10],
           "kickoff_iso": kickoff, "competition_key": "laliga", "competition_id": "4335" if sports else "140",
           "competition_name": "La Liga", "country": "Spain", "source": "TheSportsDB" if sports else "api_football_live",
           "home_team": home, "away_team": away, "home_team_id": "33" if sports else "11",
           "away_team_id": "44" if sports else "22", "status": "NS", "season": "2026",
           "last_synced_at": NOW.isoformat()}
    if sports:
        raw = {"idEvent": native, "idLeague": "4335", "idHomeTeam": "33", "idAwayTeam": "44",
               "strHomeTeam": home, "strAwayTeam": away, "strLeague": "La Liga", "strCountry": "Spain",
               "strSeason": "2026", "strSport": "Soccer", "strTimestamp": kickoff}
    else:
        raw = {"fixture": {"id": int(native), "date": kickoff, "status": {"short": "NS"}},
               "league": {"id": 140, "name": "La Liga", "country": "Spain", "season": 2026},
               "teams": {"home": {"id": 11, "name": home}, "away": {"id": 22, "name": away}}}
    row["raw_json"] = json.dumps(raw)
    return row


@pytest.fixture
def case(tmp_path):
    path = tmp_path / "financial-synthetic.sqlite"
    rows = [match("api-one", "60001"), match("sports-one", "50001", sports=True),
            match("api-other", "60002", different=True)]
    picks, quotes = [], []
    for number, row in enumerate(rows):
        picks.append({"id": "p" + str(number), "match_id": row["id"], "home_team": row["home_team"], "away_team": row["away_team"],
                      "status": "published", "market": "1x2", "selection": "2" if number == 1 else "1", "odds": "4.50" if number == 1 else "1.90",
                      "bookmaker": BOOK, "membership_required": "PRO", "source": "The Odds API", "result_status": "pending",
                      "updated_at": NOW.isoformat(), "raw_json": json.dumps({"odds_updated_at": NOW.isoformat()})})
        payload = {"bookmakers": [{"title": BOOK, "key": "synthetic", "last_update": NOW.isoformat(),
                                   "markets": [{"key": "h2h", "last_update": NOW.isoformat()}]}]}
        quotes.append({"id": "q" + str(number), "match_id": row["id"], "market": "h2h", "bookmaker": BOOK, "source": "The Odds API",
                       "home_team": row["home_team"], "away_team": row["away_team"], "home_price": "1.60" if number == 2 else "1.90",
                       "draw_price": "3.20", "away_price": "4.50", "created_at": NOW.isoformat(), "payload_json": json.dumps(payload)})
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY,membership TEXT,role TEXT,membership_expires_at TEXT)")
        conn.executemany("INSERT INTO users VALUES (?,?,?,?)", [("elite", "ELITE", "ELITE", ""), ("pro", "PRO", "PRO", ""), ("free", "FREE", "FREE", "")])
        for table, records in (("matches", rows), ("picks", picks), ("odds_snapshots", quotes)):
            columns = tuple(records[0])
            conn.execute("CREATE TABLE " + table + "(" + ",".join('"' + name + '" TEXT' for name in columns) + ")")
            conn.executemany("INSERT INTO " + table + " VALUES (" + ",".join("?" for _ in columns) + ")", [tuple(record[name] for name in columns) for record in records])
        conn.execute("CREATE TABLE competitions(key TEXT PRIMARY KEY,name TEXT,country TEXT,source TEXT,external_id TEXT)")
        conn.execute("INSERT INTO competitions VALUES ('laliga','La Liga','Spain','API_FOOTBALL','140')")
    return {"path": str(path), "rows": rows, "quotes": quotes,
            "direct": [choice_id(quotes[0], "1"), choice_id(quotes[1], "2"), choice_id(quotes[2], "1")]}


def reject(path, values, code="DUPLICATE_EVENT", user="elite"):
    with pytest.raises(advisor.CombiError) as caught:
        store.make_preview(path, user, values, now=NOW)
    assert caught.value.code == code


@pytest.mark.parametrize("kind", ["direct", "editorial", "mixed"])
def test_verified_alias_fixture_rejected_across_all_selection_paths(case, kind):
    ids = case["direct"][:2] if kind == "direct" else ["p0", "p1"] if kind == "editorial" else ["p0", case["direct"][1]]
    before = hashlib.sha256(open(case["path"], "rb").read()).hexdigest()
    reject(case["path"], {"pick_ids": ids, "stake": "0.10"})
    assert hashlib.sha256(open(case["path"], "rb").read()).hexdigest() == before


def test_distinct_verified_fixtures_preserve_each_original_price_and_ids(case):
    ids = [case["direct"][0], case["direct"][2]]
    result = store.make_preview(case["path"], "elite", {"pick_ids": ids, "stake": "0.10"}, now=NOW)
    assert [leg["id"] for leg in result["legs"]] == ids
    assert [leg["match_id"] for leg in result["legs"]] == ["api-one", "api-other"]
    assert [leg["quote_id"] for leg in result["legs"]] == ["q0", "q2"]
    assert [leg["odds"] for leg in result["legs"]] == ["1.90", "1.60"]
    assert result["total_odds"] == "3.0400" and result["probability"] is None
    assert all(not any("verified_fixture" in field for field in leg) for leg in result["legs"])


def test_suggest_dedupes_full_existing_pool_before_count_and_never_pads(case):
    reject(case["path"], {"mode": "suggest", "count": 3, "stake": "0.10"}, "INSUFFICIENT_EVIDENCE")


def test_suggest_returns_two_distinct_fixtures_and_manual_revision_remains_equal(case):
    result = store.make_preview(case["path"], "elite", {"mode": "suggest", "count": 2, "stake": "0.10"}, now=NOW)
    mids = {leg["match_id"] for leg in result["legs"]}
    assert "api-other" in mids and len(mids & {"api-one", "sports-one"}) == 1
    ids = [leg["id"] for leg in result["legs"]]
    manual = store.make_preview(case["path"], "elite", {"pick_ids": ids, "stake": "0.10"}, now=NOW)
    assert manual["revision"] == result["revision"]
    assert all(not any("verified_fixture" in field for field in leg) for leg in result["legs"])


def test_client_proof_metadata_is_ignored_and_cannot_authorize_the_pair(case):
    reject(case["path"], {"pick_ids": case["direct"][:2], "stake": "0.10",
                         "verified_fixture_key": "client-distinct", "fixture_groups": ["a", "b"], "event_key": "client"})


def test_unknown_foo_labels_are_not_verified_and_preview_warns_without_probability(case):
    with closing(sqlite3.connect(case["path"])) as conn, conn:
        conn.execute("UPDATE matches SET competition_key='foo',competition_id='',raw_json='{}' WHERE id IN ('api-one','sports-one')")
    result = store.make_preview(case["path"], "elite", {"pick_ids": case["direct"][:2], "stake": "0.10"}, now=NOW)
    assert result["probability"] is None
    assert any("identidad" in message.lower() for message in result["warnings"])
    assert all(not any("verified_fixture" in field for field in leg) for leg in result["legs"])


def test_reference_read_failure_is_explicit_and_not_silent_unverified_fallback(case):
    with closing(sqlite3.connect(case["path"])) as conn, conn:
        conn.execute("DROP TABLE competitions")
    reject(case["path"], {"pick_ids": [case["direct"][0], case["direct"][2]], "stake": "0.10"}, "IDENTITY_EVIDENCE_UNAVAILABLE")


def test_original_country_conflict_does_not_become_verified_duplicate(case):
    with closing(sqlite3.connect(case["path"])) as conn, conn:
        conn.execute("UPDATE matches SET country='England',raw_json='{}' WHERE id='sports-one'")
    result = store.make_preview(case["path"], "elite", {"pick_ids": case["direct"][:2], "stake": "0.10"}, now=NOW)
    assert len(result["legs"]) == 2
    assert any("identidad" in message.lower() for message in result["warnings"])


def test_old_draft_revalidates_current_identity_and_ignores_saved_proof(case):
    with store.connection(case["path"]) as conn:
        legs = store.candidates(conn, {"id": "elite", "membership": "ELITE"}, NOW, case["direct"][:2])
    old = advisor.preview(legs, "0.10", user={"membership": "ELITE"}, now=NOW)
    for index, leg in enumerate(old["legs"]):
        leg["verified_fixture_key"] = "forged-saved-" + str(index)
    draft = "a" * 32
    encoded = json.dumps(old)
    with closing(sqlite3.connect(case["path"])) as conn, conn:
        conn.execute("CREATE TABLE client_combi_drafts(id TEXT PRIMARY KEY,user_id TEXT,request_id TEXT,revision TEXT,payload_json TEXT,created_at TEXT)")
        conn.execute("INSERT INTO client_combi_drafts VALUES (?,?,?,?,?,?)", (draft, "elite", "b" * 32, old["revision"], encoded, NOW.isoformat()))
    before = open(case["path"], "rb").read()
    reviewed = review_draft(case["path"], "elite", draft, now=NOW)
    assert not reviewed["can_prepare"] and reviewed["preview"] is None
    assert "mismo partido" in reviewed["reason"]
    assert open(case["path"], "rb").read() == before


def test_native_own_proof_without_requested_pk_needs_no_catalogue_read(case):
    replacement = match("sports-one", "60001")
    replacement["competition_key"] = ""
    with closing(sqlite3.connect(case["path"])) as conn, conn:
        columns = tuple(replacement)
        conn.execute("UPDATE matches SET " + ",".join('"' + field + '"=?' for field in columns) + " WHERE id='sports-one'", tuple(replacement.values()))
        conn.execute("UPDATE matches SET competition_key='' WHERE id='api-one'")
        conn.execute("UPDATE odds_snapshots SET home_team='Granada CF',away_team='Real Valladolid' WHERE id='q1'")
        conn.execute("UPDATE picks SET home_team='Granada CF',away_team='Real Valladolid' WHERE id='p1'")
        conn.execute("DROP TABLE competitions")
        current = dict(zip([field[0] for field in conn.execute("SELECT * FROM odds_snapshots LIMIT 0").description], conn.execute("SELECT * FROM odds_snapshots WHERE id='q1'").fetchone()))
    ids = [case["direct"][0], choice_id(current, "2")]
    reject(case["path"], {"pick_ids": ids, "stake": "0.10"})


@pytest.mark.parametrize("body,user,code", [({"pick_ids": ["p0", "p2"], "stake": "0.10"}, "free", "PLAN_REQUIRED"),
                                           ({"mode": "suggest", "count": 2}, "pro", "PLAN_REQUIRED")])
def test_existing_plan_gates_remain(case, body, user, code):
    reject(case["path"], body, code, user)
