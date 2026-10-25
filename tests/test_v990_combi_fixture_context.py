"""V990 isolated combi integration checks: synthetic SQLite, no app or providers."""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines import client_combi_store as store
from engines import combi_match_catalogue as catalogue

NOW = datetime(2026, 10, 25, 18, 0, tzinfo=timezone.utc)
FIELDS = (
    "id", "external_id", "sport_key", "match_date", "kickoff_iso", "competition_id",
    "competition_key", "competition_name", "league_name", "country", "home_team",
    "away_team", "home_team_id", "away_team_id", "source", "status", "last_synced_at",
    "raw_json", "bookmaker", "odds_h2h_json",
)
QUOTE_FIELDS = (
    "id", "match_id", "market", "bookmaker", "source", "home_team", "away_team",
    "home_price", "draw_price", "away_price", "created_at", "payload_json",
)

def fixture(index=0, *, api=False, **extra):
    kickoff = NOW + timedelta(days=1, minutes=index)
    native = str((1000 if api else 2000) + index)
    row = dict.fromkeys(FIELDS, "")
    row.update(
        id=("af-" if api else "sportsdb-") + native,
        external_id=native,
        sport_key="soccer",
        match_date=kickoff.date().isoformat(),
        kickoff_iso=kickoff.isoformat(),
        competition_id="140" if api else "4335",
        competition_key="laliga",
        competition_name="LaLiga EA Sports" if api else "Spanish La Liga",
        league_name="LaLiga",
        country="Spain",
        home_team="Granada CF" if index == 0 and api else "Granada" if index == 0 else "Home " + str(index),
        away_team="Real Valladolid" if index == 0 else "Away " + str(index),
        home_team_id=str((300 if api else 100) + index),
        away_team_id=str((700 if api else 500) + index),
        source="API_FOOTBALL" if api else "TheSportsDB API",
        status="NS",
        last_synced_at=NOW.isoformat(),
        raw_json="{}",
        bookmaker="Match-only " + native,
        odds_h2h_json=json.dumps({"original_match_id":native,"price":7.0 if api else 9.0}),
    )
    row.update(extra)
    return row

def reference(**extra):
    result = dict(key="laliga", name="LaLiga EA Sports", country="Spain",
                  source="API_FOOTBALL", external_id="140")
    result.update(extra)
    return result

def quote_for(row, ident, bookmaker, *, home_price="1.80", minute=0):
    stamp=(NOW+timedelta(minutes=minute)).isoformat()
    raw={"original_match_id":row["id"],
         "bookmakers":[{"title":bookmaker,"key":bookmaker,"last_update":stamp,
                       "markets":[{"key":"h2h","last_update":stamp}]}]}
    return dict(id=ident, match_id=row["id"], market="h2h", bookmaker=bookmaker,
                source="The Odds API", home_team=row["home_team"], away_team=row["away_team"],
                home_price=home_price, draw_price="3.20", away_price="4.50",
                created_at=stamp, payload_json=json.dumps(raw,sort_keys=True))

class CombiFixtureContextIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix="nemesis-v990-combi-")
        self.path=Path(self.temporary.name)/"synthetic-combis.db"
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("CREATE TABLE matches("+",".join('"'+key+'" TEXT' for key in FIELDS)+")")
            conn.execute("CREATE TABLE competitions(key TEXT PRIMARY KEY,name TEXT,country TEXT,source TEXT,external_id TEXT)")
            conn.execute("CREATE TABLE odds_snapshots("+",".join('"'+key+'" TEXT' for key in QUOTE_FIELDS)+")")
        self.trace=[]

    def tearDown(self):
        self.temporary.cleanup()

    def seed(self, rows, *, references=(), quotes=()):
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.executemany("INSERT INTO matches VALUES("+",".join("?" for _ in FIELDS)+")",
                             [[row.get(key,"") for key in FIELDS] for row in rows])
            conn.executemany("INSERT INTO competitions VALUES(?,?,?,?,?)",
                             [[row.get(key,"") for key in ("key","name","country","source","external_id")] for row in references])
            conn.executemany("INSERT INTO odds_snapshots VALUES("+",".join("?" for _ in QUOTE_FIELDS)+")",
                             [[row.get(key,"") for key in QUOTE_FIELDS] for row in quotes])

    def read(self, filters=None):
        self.trace=[]
        with store.connection(self.path) as conn:
            conn.set_trace_callback(self.trace.append)
            return catalogue.read_catalogue(conn,{"membership":"ELITE"},filters=filters or {},now=NOW)

    def reference_reads(self):
        return [sql for sql in self.trace
                if re.search(r'FROM\s+["`]?competitions\b',sql,re.I)]

    def test_verified_real_pk_collapses_pair_and_preserves_each_quote_link(self):
        sports,api=fixture(),fixture(api=True)
        observations=[quote_for(sports,"q-sports","Sports Book",home_price="1.70"),
                      quote_for(api,"q-api","API Book",home_price="1.90")]
        self.seed([sports,api],references=[reference()],quotes=observations)
        before=hashlib.sha256(self.path.read_bytes()).hexdigest()
        result=self.read()
        self.assertEqual(result["total"],1)
        self.assertEqual(len(result["matches"]),1)
        books={group["bookmaker"]:group for group in result["matches"][0]["groups"]}
        self.assertEqual(set(books),{"API Book","Sports Book"})
        for book,original,qid,price in (
            ("API Book",api,"q-api","1.90"),("Sports Book",sports,"q-sports","1.70")):
            choices=books[book]["choices"]
            self.assertEqual(len(choices),3)
            self.assertEqual({choice["match_id"] for choice in choices},{original["id"]})
            self.assertTrue(all(choice["id"].startswith("market:"+qid+":") for choice in choices))
            self.assertTrue(all(choice["home"]==original["home_team"] for choice in choices))
            self.assertEqual(next(choice["odds"] for choice in choices if choice["selection"]=="1"),price)
        self.assertEqual(len(self.reference_reads()),1)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),before)
        with store.connection(self.path) as conn:
            resolved=catalogue.resolve_choices(conn,{"membership":"ELITE"},NOW,
                       [books["API Book"]["choices"][0]["id"],books["Sports Book"]["choices"][0]["id"]])
        self.assertEqual({choice["match_id"] for choice in resolved},{api["id"],sports["id"]})

    def test_missing_country_and_pk_tottenham_coventry_remain_two_unknown_observations(self):
        sports=fixture(home_team="Tottenham",away_team="Coventry",competition_name="LaLiga",
                       country="",competition_key="",competition_id="")
        api=fixture(api=True,home_team="Tottenham Hotspur",away_team="Coventry City",
                    competition_name="LaLiga",country="",competition_key="",competition_id="")
        self.seed([sports,api])
        result=self.read()
        self.assertEqual(result["total"],2)
        self.assertEqual({row["id"] for row in result["matches"]},{sports["id"],api["id"]})
        self.assertEqual(self.reference_reads(),[])

    def test_country_conflict_prevents_cross_provider_collapse(self):
        self.seed([fixture(country="Portugal"),fixture(api=True)],references=[reference()])
        self.assertEqual(self.read()["total"],2)
        self.assertEqual(len(self.reference_reads()),1)

    def test_existing_same_namespace_catalog_id_conflict_keeps_both_rows(self):
        self.seed([fixture(),fixture(api=True,competition_id="141")],references=[reference()])
        self.assertEqual(self.read()["total"],2)
        self.assertEqual(len(self.reference_reads()),1)

    def test_distinct_native_fixture_ids_from_same_provider_never_collapse(self):
        first=fixture(api=True)
        second=fixture(api=True,id="af-9999",external_id="9999")
        self.seed([first,second],references=[reference()])
        self.assertEqual(self.read()["total"],2)

    def test_actual_pk_can_supply_missing_country_without_guessing_from_label(self):
        self.seed([fixture(country=""),fixture(api=True,country="")],references=[reference()])
        result=self.read()
        self.assertEqual(result["total"],1)
        # Display still uses the intact selected row; this integration does not
        # forge country in the stored/provider match dictionary.
        self.assertEqual(result["matches"][0]["country"],"")

    def test_league_and_team_search_filter_original_members_before_group_selection(self):
        sports,api=fixture(),fixture(api=True)
        self.seed([sports,api],references=[reference()],
                  quotes=[quote_for(sports,"q-sports","Sports Book"),quote_for(api,"q-api","API Book")])
        by_league=self.read({"league":"Spanish La Liga"})
        self.assertEqual(by_league["total"],1)
        self.assertEqual([row["id"] for row in by_league["matches"]],[sports["id"]])
        self.assertEqual({group["bookmaker"] for group in by_league["matches"][0]["groups"]},{"Sports Book"})
        self.assertEqual(len(self.reference_reads()),1)
        by_team=self.read({"q":"Granada CF"})
        self.assertEqual(by_team["total"],1)
        self.assertEqual([row["id"] for row in by_team["matches"]],[api["id"]])
        self.assertEqual(len(self.reference_reads()),1)

    def test_grouping_precedes_page_limit_and_target_keeps_all_member_quote_ids(self):
        rows=[]
        for index in range(25):
            rows.extend([fixture(index),fixture(index,api=True)])
        target=fixture(24,api=True)
        self.seed(rows,references=[reference()],quotes=[quote_for(target,"q-last","Target Book")])
        page_one=self.read()
        self.assertEqual((page_one["total"],page_one["pages"],len(page_one["matches"])),(25,2,24))
        self.assertEqual(len(self.reference_reads()),1)
        page_two=self.read({"page":2})
        self.assertEqual((page_two["total"],len(page_two["matches"])),(25,1))
        target_page=self.read({"target":target["id"]})
        card=target_page["matches"][0]
        self.assertEqual(card["home"],target["home_team"])
        self.assertEqual(card["groups"][0]["choices"][0]["match_id"],target["id"])
        self.assertTrue(card["groups"][0]["choices"][0]["id"].startswith("market:q-last:"))

    def test_search_precedes_existing_scan_guard_without_changing_it(self):
        self.seed([fixture(index,api=True) for index in range(4)],references=[reference()])
        with patch.object(catalogue,"SCAN_LIMIT",2):
            bounded=self.read()
            self.assertTrue(bounded["truncated"])
            self.assertEqual(bounded["scan_limit"],2)
            self.assertEqual(bounded["total"],2)
            searched=self.read({"q":"Home 3"})
            self.assertFalse(searched["truncated"])
            self.assertEqual([row["home"] for row in searched["matches"]],["Home 3"])

    def test_existing_quote_limit_stays_explicit_and_never_assesses_truncated_prices(self):
        row=fixture(api=True)
        observations=[quote_for(row,"q-"+str(i),"Book "+str(i)) for i in range(4001)]
        self.seed([row],references=[reference()],quotes=observations)
        result=self.read()
        self.assertTrue(result["quote_truncated"])
        self.assertEqual(result["total"],1)
        self.assertTrue(result["matches"][0]["groups"])
        self.assertTrue(all(group["choices"]==[] for group in result["matches"][0]["groups"]))
        self.assertTrue(all(group["market_reading"]["state"]=="QUOTE_WINDOW_LIMIT"
                            for group in result["matches"][0]["groups"]))
        self.assertEqual(len(self.reference_reads()),1)

    def test_missing_competition_table_fails_unknown_without_losing_fixture_rows(self):
        self.seed([fixture(),fixture(api=True)])
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("DROP TABLE competitions")
        result=self.read()
        self.assertEqual(result["total"],2)

    def test_no_app_import_is_needed_for_the_real_catalogue_path(self):
        self.seed([fixture(api=True)],references=[reference()])
        import builtins
        import importlib
        attempts = []
        original_import = builtins.__import__
        original_import_module = importlib.import_module

        def guarded_import(name, *args, **kwargs):
            if name == "app" or name.startswith("app."):
                attempts.append(name)
                raise AssertionError("catalogue must not import App")
            return original_import(name, *args, **kwargs)

        def guarded_import_module(name, package=None):
            if (name == "app" or name.startswith("app.")
                    or (name.startswith(".") and (package == "app" or str(package).startswith("app.")))):
                attempts.append(name)
                raise AssertionError("catalogue must not import App")
            return original_import_module(name, package)

        # Other full-suite tests legitimately imported App earlier. Block it for
        # this read instead of asserting unrelated process-wide import history.
        previous = sys.modules.get("app")
        was_loaded = "app" in sys.modules
        with patch.dict(sys.modules, {"app": None}), \
                patch.object(builtins, "__import__", guarded_import), \
                patch.object(importlib, "import_module", guarded_import_module):
            for invoke in (lambda: __import__("app"), lambda: importlib.import_module("app")):
                with self.assertRaisesRegex(AssertionError, "catalogue must not import App"):
                    invoke()
            self.assertEqual(attempts, ["app", "app"])
            attempts.clear()
            result = self.read()
        self.assertEqual(attempts, [])
        self.assertEqual(result["external_calls"], 0)
        self.assertEqual(result["total"], 1)
        self.assertEqual(len(self.reference_reads()), 1)
        self.assertEqual("app" in sys.modules, was_loaded)
        if was_loaded:
            self.assertIs(sys.modules["app"], previous)

if __name__=="__main__":
    unittest.main(verbosity=2)
