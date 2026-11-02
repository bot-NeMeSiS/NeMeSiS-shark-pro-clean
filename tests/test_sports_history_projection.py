"""Owned SQLite leaf tests only: no App import, provider call or real database."""
from __future__ import annotations
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from engines import api_exploitation_engine as engine
from engines.cron_request_budget import CronRequestBudget

RUN_ROOT=Path(os.environ["OWNED_SPORTS_LEAF_ROOT"])
CAPABILITIES=("fixtures","events","lineups","players","stats","standings","h2h","injuries")
TABLES={"fixtures":"api_football_fixture_index","events":"api_football_live_events",
        "lineups":"api_football_lineups_deep","stats":"api_football_match_stats_history",
        "standings":"api_football_standings_deep","h2h":"api_football_h2h_history",
        "injuries":"api_football_injuries_history"}
FINISHED="2026-10-01T01:02:03+00:00"

def owned_database(path, *, sample=True, populated=True):
    engine.ensure_api_exploitation_schema(str(path))
    with closing(sqlite3.connect(str(path))) as c, c:
        c.execute("CREATE TABLE api_football_live_events(id TEXT)")
        c.execute("CREATE TABLE player_profiles(player_id TEXT)")
        if populated:
            for n,(capability,table) in enumerate(TABLES.items(),1):
                c.executemany(f"INSERT INTO {table}(id) VALUES(?)",[(f"owned-{i}",) for i in range(n)])
            c.executemany("INSERT INTO player_profiles VALUES(?)",[(None,),("",),(" ",),("p",),("p",)])
        if sample:
            add_sample(c,FINISHED,ok=True)
    return path

def add_sample(c,finished,*,ok=True):
    payload={"account":{"ok":ok,"http_status":200 if ok else 401,"configured":True,
               "plan":"OWNED_HISTORY","quota":{"daily_limit":123,"daily_remaining":99}},
             "capabilities":{name:{"requested":True,"received":i+1,"normalized":i}
                             for i,name in enumerate(CAPABILITIES)},
             "selected_fixture_ids":["owned-fixture"]}
    c.execute("INSERT INTO api_exploitation_runs(started_at,finished_at,status,external_calls,error_message,payload_json) "
              "VALUES(?,?,?,?,?,?)",(finished,finished,"OK" if ok else "ERROR",1,"owned error",json.dumps(payload)))

class ProjectionContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=RUN_ROOT,prefix="p")
        self.base=Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def read(self,path,seconds=5):
        with CronRequestBudget(seconds=seconds) as budget:
            return engine.api_exploitation_summary(str(path),budget),budget

    def test_nominal_projection_equals_all_consumed_admin_values(self):
        path=owned_database(self.base/"nominal.sqlite")
        full=engine.api_exploitation_summary(str(path))
        actual,budget=self.read(path)
        for key in ("latest_run","latest_account","continuity"):
            self.assertEqual(actual[key],full[key],key)
        self.assertTrue(actual["ok"])
        self.assertEqual(actual["sports_read_state"]["state"],"COMPLETE")
        self.assertEqual(actual["sports_read_state"]["unknown_capabilities"],[])
        self.assertEqual({x["capability"]:x["persisted"] for x in actual["continuity"]}["players"],3)
        self.assertFalse(budget.deferred)
        for key in ("recent_runs","top_form","top_movements","readiness_score","recommended_env","api_football_configured"):
            self.assertNotIn(key,actual)

    def test_zero_is_emitted_only_after_completed_counts(self):
        path=owned_database(self.base/"zero.sqlite",sample=False,populated=False)
        full=engine.api_exploitation_summary(str(path))
        actual,_=self.read(path)
        self.assertEqual(actual["continuity"],full["continuity"])
        self.assertEqual(len(actual["continuity"]),8)
        self.assertTrue(all(row["persisted"]==0 for row in actual["continuity"]))
        self.assertEqual(actual["sports_read_state"]["state"],"COMPLETE")

    def test_readonly_no_schema_provider_or_admin_queries_and_file_unchanged(self):
        path=owned_database(self.base/"readonly.sqlite")
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        native=sqlite3.connect
        queries=[]; modes=[]
        def traced(*a,**kw):
            modes.append((a,kw))
            c=native(*a,**kw); c.set_trace_callback(queries.append); return c
        with patch.object(engine,"ensure_api_exploitation_schema",side_effect=AssertionError("NO DDL")), \
             patch.object(engine,"_api_get",side_effect=AssertionError("NO PROVIDER")), \
             patch.object(engine,"_api_football_key",side_effect=AssertionError("NO KEY READ")), \
             patch.object(engine,"_api_football_enabled",side_effect=AssertionError("NO CONFIG READ")), \
             patch.object(sqlite3,"connect",traced):
            actual,_=self.read(path)
        self.assertTrue(actual["ok"])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
        self.assertEqual(len(modes),1)
        self.assertTrue(modes[0][1]["uri"])
        self.assertTrue(modes[0][0][0].endswith("?mode=ro"))
        statements=[q.upper() for q in queries]
        self.assertFalse(any(any(word in q for word in ("CREATE ","ALTER ","INSERT ","UPDATE ","DELETE ","DERIVED_SIGNALS","LIMIT 8")) for q in statements))
        self.assertEqual(sum(q.startswith("SELECT COUNT(*)") for q in statements),8)
        self.assertEqual(sum("ORDER BY ID DESC LIMIT 1" in q for q in statements),1)
        self.assertIn("BEGIN",statements)
        self.assertIn("ROLLBACK",statements)

    def test_missing_database_is_unknown_and_is_not_created(self):
        path=self.base/"absent.sqlite"
        actual,_=self.read(path)
        self.assertFalse(path.exists())
        self.assertFalse(actual["ok"])
        self.assertEqual(actual["sports_read_state"]["state"],"UNAVAILABLE")
        self.assertEqual(actual["sports_read_state"]["unknown_capabilities"],list(CAPABILITIES))
        self.assertEqual(actual["latest_account"],{})
        self.assertEqual(actual["continuity"],[])

    def test_missing_latest_table_is_unknown_not_empty_historical_auth(self):
        path=self.base/"no-schema.sqlite"
        with closing(sqlite3.connect(str(path))) as c, c:
            c.execute("CREATE TABLE marker(x)")
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        actual,_=self.read(path)
        self.assertEqual(actual["sports_read_state"]["state"],"UNAVAILABLE")
        self.assertFalse(actual["sports_read_state"]["latest_run_observed"])
        self.assertEqual(actual["latest_account"],{})
        self.assertEqual(actual["continuity"],[])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)

    def test_missing_count_keeps_completed_history_and_omits_entire_unknown_row(self):
        path=owned_database(self.base/"missing-count.sqlite")
        with closing(sqlite3.connect(str(path))) as c, c:
            c.execute("DROP TABLE player_profiles")
        actual,_=self.read(path)
        self.assertFalse(actual["ok"])
        self.assertEqual(actual["sports_read_state"]["state"],"PARTIAL")
        self.assertEqual(actual["sports_read_state"]["unknown_capabilities"],["players"])
        self.assertEqual({row["capability"] for row in actual["continuity"]},set(CAPABILITIES)-{"players"})
        self.assertNotIn("players",actual["persisted_totals"])
        self.assertTrue(actual["latest_account"]["ok"])
        self.assertEqual(actual["sports_read_state"]["account_observed_at"],FINISHED)
        self.assertFalse(actual["sports_read_state"]["account_is_current"])
        self.assertTrue(all(row["persisted"] is not None for row in actual["continuity"]))

    def test_actual_progress_deadline_interrupt_never_yields_unknown_zero(self):
        path=owned_database(self.base/"deadline.sqlite")
        with closing(sqlite3.connect(str(path))) as c, c:
            c.execute("DROP TABLE player_profiles")
            c.execute("CREATE VIEW player_profiles AS WITH RECURSIVE seq(x) AS "
                      "(VALUES(1) UNION ALL SELECT x+1 FROM seq WHERE x<100000000) "
                      "SELECT CAST(x AS TEXT) AS player_id FROM seq")
        started=time.monotonic()
        actual,budget=self.read(path,seconds=.29)
        self.assertTrue(budget.deferred)
        self.assertFalse(actual["ok"])
        self.assertEqual(actual["sports_read_state"]["state"],"DEFERRED")
        self.assertEqual(actual["sports_read_state"]["reason"],"TIME_BUDGET")
        self.assertTrue(actual["sports_read_state"]["query_interrupted"])
        self.assertNotIn("players",actual["persisted_totals"])
        self.assertNotIn("players",{row["capability"] for row in actual["continuity"]})
        self.assertIn("players",actual["sports_read_state"]["unknown_capabilities"])
        self.assertTrue(actual["latest_account"]["ok"])  # Completed HISTORICAL observation only.
        self.assertEqual(actual["sports_read_state"]["account_observed_at"],FINISHED)
        self.assertFalse(actual["sports_read_state"]["account_is_current"])
        self.assertLess(time.monotonic()-started,2)  # Cleanup sanity, not a production latency claim.

    def test_expired_and_nested_parent_budget_do_not_open_database(self):
        path=owned_database(self.base/"expired.sqlite")
        with CronRequestBudget(seconds=0):
            with CronRequestBudget(seconds=100) as budget:
                with patch.object(sqlite3,"connect",side_effect=AssertionError("EXPIRED MUST NOT OPEN")):
                    actual=engine.api_exploitation_summary(str(path),budget)
        self.assertTrue(budget.deferred)
        self.assertEqual(actual["sports_read_state"]["state"],"DEFERRED")
        self.assertEqual(actual["latest_run"],{})
        self.assertEqual(actual["latest_account"],{})
        self.assertEqual(actual["continuity"],[])
        self.assertEqual(actual["sports_read_state"]["snapshot_scope"],"NOT_ESTABLISHED")

    def test_lock_wait_uses_remaining_budget_not_five_second_default(self):
        path=owned_database(self.base/"locked.sqlite")
        writer=sqlite3.connect(str(path))
        try:
            writer.execute("BEGIN EXCLUSIVE")
            started=time.monotonic()
            actual,budget=self.read(path,seconds=.30)
            self.assertFalse(actual["ok"])
            self.assertEqual(actual["continuity"],[])
            self.assertEqual(actual["latest_account"],{})
            self.assertIn(actual["sports_read_state"]["state"],{"UNAVAILABLE","DEFERRED"})
            self.assertLess(time.monotonic()-started,1)
        finally:
            writer.rollback();writer.close()

    def test_next_committed_sample_and_counts_use_new_own_frame_no_old_cache(self):
        path=owned_database(self.base/"new-commit.sqlite")
        first,_=self.read(path)
        later="2031-01-01T00:00:00+00:00"
        with closing(sqlite3.connect(str(path))) as c, c:
            add_sample(c,later,ok=False)
            c.execute("INSERT INTO api_football_fixture_index(id) VALUES('owned-next')")
        second,_=self.read(path)
        self.assertEqual(second["latest_run"]["id"],first["latest_run"]["id"]+1)
        self.assertFalse(second["latest_account"]["ok"])
        self.assertEqual(second["sports_read_state"]["account_observed_at"],later)
        self.assertFalse(second["sports_read_state"]["account_is_current"])
        self.assertEqual(second["persisted_totals"]["fixtures"],first["persisted_totals"]["fixtures"]+1)

    def test_invalid_budget_does_not_fall_through_to_admin_schema(self):
        with patch.object(engine,"ensure_api_exploitation_schema",side_effect=AssertionError("NO ADMIN FALLBACK")):
            actual=engine.api_exploitation_summary(str(self.base/"unopened.sqlite"),True)
        self.assertEqual(actual["sports_read_state"]["reason"],"INVALID_REQUEST_BUDGET")
        self.assertEqual(actual["continuity"],[])

    def test_nonmapping_trace_is_unknown_not_false_zero(self):
        path=owned_database(self.base/"invalid-trace.sqlite")
        with closing(sqlite3.connect(str(path))) as c, c:
            c.execute("UPDATE api_exploitation_runs SET payload_json=?",(json.dumps({
                "account":{"ok":True,"http_status":200},
                "capabilities":{"players":["invalid"]}}),))
        actual,_=self.read(path)
        self.assertFalse(actual["ok"])
        self.assertEqual(actual["sports_read_state"]["state"],"PARTIAL")
        self.assertIn("players",actual["sports_read_state"]["unknown_capabilities"])
        self.assertNotIn("players",{row["capability"] for row in actual["continuity"]})
        self.assertEqual(actual["persisted_totals"]["players"],3)  # Separately completed exact count.

    def test_actual_malformed_json_is_not_complete_or_empty_valid_payload(self):
        path=owned_database(self.base/"malformed-json.sqlite")
        for raw in ("{not-json",b"\\xff"):
            with self.subTest(raw=repr(raw)):
                with closing(sqlite3.connect(str(path))) as c, c:
                    c.execute("UPDATE api_exploitation_runs SET payload_json=?",(raw,))
                actual,_=self.read(path)
                self.assertFalse(actual["ok"])
                self.assertEqual(actual["sports_read_state"]["state"],"PARTIAL")
                self.assertEqual(actual["sports_read_state"]["reason"],"INVALID_PERSISTED_SAMPLE")
                self.assertEqual(actual["sports_read_state"]["unknown_capabilities"],list(CAPABILITIES))
                self.assertEqual(actual["latest_account"],{})
                self.assertEqual(actual["continuity"],[])
                self.assertEqual(actual["persisted_totals"]["players"],3)

    def test_absent_and_empty_valid_json_keep_nominal_legacy_projection(self):
        path=owned_database(self.base/"empty-json.sqlite")
        for raw in (None,"","{}","null","[]"):
            with self.subTest(raw=raw):
                with closing(sqlite3.connect(str(path))) as c, c:
                    c.execute("UPDATE api_exploitation_runs SET payload_json=?",(raw,))
                full=engine.api_exploitation_summary(str(path))
                actual,_=self.read(path)
                self.assertTrue(actual["ok"])
                self.assertEqual(actual["sports_read_state"]["state"],"COMPLETE")
                for key in ("latest_run","latest_account","continuity"):
                    self.assertEqual(actual[key],full[key])

    def test_ordinary_sqlite_cleanup_errors_preserve_successful_observations(self):
        path=owned_database(self.base/"cleanup.sqlite")
        expected=engine.api_exploitation_summary(str(path))
        native=sqlite3.connect
        for failure in ("reset","rollback","close"):
            opened=[]
            class CleanupProxy:
                def __init__(self,c):object.__setattr__(self,"real",c)
                def __getattr__(self,name):return getattr(self.real,name)
                def __setattr__(self,name,value):setattr(self.real,name,value)
                def set_progress_handler(self,callback,n):
                    self.real.set_progress_handler(callback,n)
                    if failure=="reset" and callback is None:raise sqlite3.OperationalError("OWNED_PRIVATE_CLEANUP_ERROR")
                def rollback(self):
                    self.real.rollback()
                    if failure=="rollback":raise sqlite3.OperationalError("OWNED_PRIVATE_CLEANUP_ERROR")
                def close(self):
                    self.real.close()
                    if failure=="close":raise sqlite3.OperationalError("OWNED_PRIVATE_CLEANUP_ERROR")
            def connect(*a,**kw):
                c=native(*a,**kw);opened.append(c);return CleanupProxy(c)
            with self.subTest(failure=failure):
                try:
                    with patch.object(sqlite3,"connect",connect):
                        actual,_=self.read(path)
                    self.assertFalse(actual["ok"])
                    self.assertEqual(actual["sports_read_state"]["state"],"PARTIAL")
                    self.assertEqual(actual["sports_read_state"]["reason"],"SQL_CLEANUP_UNAVAILABLE")
                    self.assertTrue(actual["sports_read_state"]["cleanup_failed"])
                    self.assertEqual(actual["continuity"],expected["continuity"])
                    self.assertEqual(actual["latest_account"],expected["latest_account"])
                    self.assertEqual(actual["sports_read_state"]["account_observed_at"],FINISHED)
                    self.assertNotIn("OWNED_PRIVATE_CLEANUP_ERROR",json.dumps(actual))
                finally:
                    for c in opened:c.close()  # Fixture cleanup also on the expected RED source.

    def test_deferred_after_all_eight_completed_counts_does_not_invent_unknowns(self):
        path=owned_database(self.base/"completed-late.sqlite")
        expected=engine.api_exploitation_summary(str(path))
        native=sqlite3.connect;clock=[0.]
        class AfterClose:
            def __init__(self,c):object.__setattr__(self,"real",c)
            def __getattr__(self,name):return getattr(self.real,name)
            def __setattr__(self,name,value):setattr(self.real,name,value)
            def close(self):
                self.real.close();clock[0]=2.
        def connect(*a,**kw):return AfterClose(native(*a,**kw))
        with CronRequestBudget(seconds=1,clock=lambda:clock[0]) as budget:
            with patch.object(sqlite3,"connect",connect):
                actual=engine.api_exploitation_summary(str(path),budget)
        self.assertTrue(budget.deferred)
        self.assertEqual(actual["sports_read_state"]["state"],"DEFERRED")
        self.assertEqual(actual["sports_read_state"]["unknown_capabilities"],[])
        self.assertEqual(actual["continuity"],expected["continuity"])
        framed=engine.project_sports_history_read_state(actual["sports_read_state"])
        self.assertEqual(framed["state"],"DEFERRED")
        self.assertEqual(framed["unknown_capabilities"],[])

    def test_completed_count_survives_pause_but_unvalidated_sample_does_not(self):
        native=sqlite3.connect
        for stage in ("count","sample"):
            with self.subTest(stage=stage):
                path=owned_database(self.base/(stage+"-pause.sqlite"))
                if stage=="sample":
                    with closing(native(str(path))) as c, c:
                        c.execute("UPDATE api_exploitation_runs SET payload_json=?",(json.dumps({
                            "account":{},"capabilities":{"account":{"requested":True}}}),))
                paused=[False];queries=[]
                class Fetched:
                    def __init__(self,cursor):self.cursor=cursor
                    def __getattr__(self,name):return getattr(self.cursor,name)
                    def fetchone(self):
                        row=self.cursor.fetchone()  # REAL completed native fetch.
                        paused[0]=True
                        time.sleep(.30)  # Own-test descheduling, no global/fake clock.
                        return row
                class Connection:
                    def __init__(self,c):object.__setattr__(self,"real",c)
                    def __getattr__(self,name):return getattr(self.real,name)
                    def __setattr__(self,name,value):setattr(self.real,name,value)
                    def execute(self,sql,*args):
                        queries.append(sql)
                        cursor=self.real.execute(sql,*args)
                        target=("SELECT COUNT(*) AS total FROM api_football_fixture_index" if stage=="count"
                                else "SELECT * FROM api_exploitation_runs")
                        return Fetched(cursor) if sql.startswith(target) else cursor
                def connect(*a,**kw):return Connection(native(*a,**kw))
                with patch.object(sqlite3,"connect",connect):
                    actual,budget=self.read(path,seconds=.5)
                self.assertTrue(paused[0])
                self.assertTrue(budget.deferred)
                self.assertFalse(actual["ok"])
                self.assertEqual(actual["sports_read_state"]["state"],"DEFERRED")
                if stage=="count":
                    self.assertEqual(actual["persisted_totals"].get("fixtures"),1)
                    self.assertEqual([row["capability"] for row in actual["continuity"]],["fixtures"])
                    self.assertEqual(actual["continuity"][0]["persisted"],1)
                    self.assertEqual(actual["sports_read_state"]["unknown_capabilities"],list(CAPABILITIES[1:]))
                    self.assertTrue(actual["sports_read_state"]["latest_run_observed"])
                    self.assertEqual(actual["sports_read_state"]["account_observed_at"],FINISHED)
                    self.assertFalse(actual["sports_read_state"]["account_is_current"])
                else:
                    self.assertEqual(actual["latest_run"],{})
                    self.assertEqual(actual["latest_account"],{})
                    self.assertEqual(actual["continuity"],[])
                    self.assertFalse(actual["sports_read_state"]["latest_run_observed"])
                    self.assertEqual(actual["sports_read_state"]["snapshot_scope"],"NOT_ESTABLISHED")
                    self.assertFalse(any("SELECT COUNT(*)" in query for query in queries))

    def test_lost_transaction_stops_without_new_frame_after_real_writer_commit(self):
        path=owned_database(self.base/"lost-frame.sqlite")
        native=sqlite3.connect
        with closing(native(str(path))) as c:
            old_stats=c.execute("SELECT COUNT(*) FROM api_football_match_stats_history").fetchone()[0]
        counted=[];writer_committed=[False]
        class Connection:
            def __init__(self,c):object.__setattr__(self,"real",c)
            def __getattr__(self,name):return getattr(self.real,name)
            def __setattr__(self,name,value):setattr(self.real,name,value)
            def execute(self,sql,*args):
                if sql.startswith("SELECT COUNT(*) AS total FROM "):
                    name=sql.split(" FROM ",1)[1].split()[0]
                    counted.append(name)
                    if name=="api_football_live_events":
                        self.real.rollback()  # REAL end of the original read transaction.
                        with closing(native(str(path))) as writer, writer:
                            writer.execute("INSERT INTO api_football_match_stats_history(id) VALUES('owned-later-frame')")
                        writer_committed[0]=True
                        raise sqlite3.OperationalError("OWNED_ROLLBACK_FAILURE")
                return self.real.execute(sql,*args)
        def connect(*a,**kw):return Connection(native(*a,**kw))
        with patch.object(sqlite3,"connect",connect):
            actual,_=self.read(path)
        self.assertTrue(writer_committed[0])
        with closing(native(str(path))) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM api_football_match_stats_history").fetchone()[0],old_stats+1)
        self.assertEqual(counted,["api_football_fixture_index","api_football_live_events"])
        self.assertFalse(actual["ok"])
        self.assertEqual(actual["sports_read_state"]["state"],"PARTIAL")
        self.assertEqual(actual["sports_read_state"]["reason"],"SQL_READ_UNAVAILABLE")
        self.assertTrue(actual["sports_read_state"]["snapshot_lost"])
        self.assertEqual(actual["persisted_totals"],{"fixtures":1})
        self.assertEqual([row["capability"] for row in actual["continuity"]],["fixtures"])
        self.assertNotIn("stats",actual["persisted_totals"])
        self.assertEqual(actual["sports_read_state"]["unknown_capabilities"],list(CAPABILITIES[1:]))
        self.assertEqual(actual["sports_read_state"]["account_observed_at"],FINISHED)

    def test_invalid_account_with_account_trace_is_not_a_validated_sample(self):
        path=owned_database(self.base/"invalid-account.sqlite")
        with closing(sqlite3.connect(str(path))) as c, c:
            c.execute("UPDATE api_exploitation_runs SET payload_json=?",(json.dumps({
                "account":"invalid","capabilities":{"account":{"requested":True,"http_status":200}}}),))
        actual,_=self.read(path)
        self.assertFalse(actual["ok"])
        self.assertEqual(actual["sports_read_state"]["state"],"PARTIAL")
        self.assertEqual(actual["sports_read_state"]["reason"],"INVALID_PERSISTED_SAMPLE")
        self.assertFalse(actual["sports_read_state"]["latest_run_observed"])
        self.assertEqual(actual["latest_run"],{})
        self.assertEqual(actual["latest_account"],{})
        self.assertEqual(actual["continuity"],[])
        self.assertEqual(actual["sports_read_state"]["account_observed_at"],"")
        self.assertEqual(actual["persisted_totals"]["players"],3)  # Independent exact COUNT remains known.

class ReadStateBoundaryContracts(unittest.TestCase):
    def test_closed_block_filters_foreign_identifiers_secret_error_and_current_claim(self):
        raw={"state":"COMPLETE","reason":"PRIVATE_ERROR_SQL_USERS_TOKEN",
             "unknown_capabilities":["players","foreign_fixture_123","stats"],
             "latest_run_observed":True,"account_observed_at":FINISHED,"account_is_current":True,
             "snapshot_scope":"ONE_READ_TRANSACTION","query_interrupted":True,
             "sql":"PRIVATE SELECT","account":{"key":"PRIVATE_KEY"}}
        result=engine.project_sports_history_read_state(raw)
        self.assertEqual(result["state"],"PARTIAL")
        self.assertEqual(result["unknown_capabilities"],["players","stats"])
        self.assertEqual(result["account_observed_at"],FINISHED)
        self.assertFalse(result["account_is_current"])
        self.assertNotIn("PRIVATE",json.dumps(result))
        self.assertNotIn("foreign_fixture",json.dumps(result))
        self.assertEqual(engine.project_sports_history_read_state(result),result)

    def test_malformed_metadata_is_unknown_not_complete(self):
        for raw in (None,{"state":[],"reason":{}},{"state":"COMPLETE","unknown_capabilities":["players"]*9},
                    {"state":"COMPLETE","unknown_capabilities":[]},
                    {"state":"PARTIAL","unknown_capabilities":[],"account_observed_at":"SECRET_VALUE"}):
            with self.subTest(raw=raw):
                result=engine.project_sports_history_read_state(raw)
                self.assertNotEqual(result["state"],"COMPLETE")
                self.assertFalse(result["account_is_current"])
                self.assertEqual(result["account_observed_at"],"")
                self.assertNotIn("SECRET_VALUE",json.dumps(result))

    def test_master_revalidates_metadata_independent_of_current_coverage(self):
        from tools.render_cron_master_tick import sanitized_sports_pipeline
        read={"state":"DEFERRED","reason":"TIME_BUDGET","unknown_capabilities":["players"],
              "latest_run_observed":True,"account_observed_at":FINISHED,"account_is_current":False,
              "snapshot_scope":"ONE_READ_TRANSACTION","query_interrupted":True}
        pipeline={"history_read":read,"coverage":{"source":"CURRENT_DEEP_RUN","capabilities":{
                  "stats":{"state":"RECEIVED","persisted":0,"received":1,"requested":True}}},
                  "provider_access":{"is_current":True,"freshness":"CURRENT_DEEP_RUN"}}
        actual=sanitized_sports_pipeline({"sports_pipeline":pipeline},"own-secret")
        self.assertEqual(actual["history_read"],read)
        self.assertEqual(actual["coverage"]["source"],"CURRENT_DEEP_RUN")
        self.assertEqual(actual["coverage"]["capabilities"]["stats"]["persisted"],0)
        self.assertNotIn("players",actual["coverage"]["capabilities"])
        self.assertTrue(actual["provider_access"]["is_current"])
        pipeline["history_read"]={**read,"reason":"own-secret","unknown_capabilities":["players","sql_users"]}
        filtered=sanitized_sports_pipeline({"sports_pipeline":pipeline},"own-secret")["history_read"]
        self.assertEqual(filtered["reason"],"UNKNOWN")
        self.assertEqual(filtered["unknown_capabilities"],["players"])
        self.assertNotIn("own-secret",json.dumps(filtered))
        self.assertNotIn("sql_users",json.dumps(filtered))

    def test_complete_requires_coherent_success_not_budget_or_interruption(self):
        complete={"state":"COMPLETE","reason":"READ_COMPLETE","unknown_capabilities":[],
                  "latest_run_observed":True,"snapshot_scope":"ONE_READ_TRANSACTION",
                  "query_interrupted":False,"account_is_current":False,"account_observed_at":FINISHED}
        self.assertEqual(engine.project_sports_history_read_state(complete)["state"],"COMPLETE")
        for change in ({"reason":"TIME_BUDGET"},{"query_interrupted":True},{"cleanup_failed":True},
                       {"reason":"SQL_READ_UNAVAILABLE"},{"snapshot_lost":True}):
            with self.subTest(change=change):
                self.assertNotEqual(engine.project_sports_history_read_state({**complete,**change})["state"],"COMPLETE")
        deferred=engine.project_sports_history_read_state({**complete,"state":"DEFERRED","reason":"TIME_BUDGET"})
        self.assertEqual(deferred["state"],"DEFERRED")
        self.assertEqual(deferred["unknown_capabilities"],[])

    def test_legacy_master_does_not_add_an_unrequested_history_claim(self):
        from tools.render_cron_master_tick import sanitized_sports_pipeline
        actual=sanitized_sports_pipeline({"sports_pipeline":{"coverage":{"source":"NONE","capabilities":{}}}},"")
        self.assertNotIn("history_read",actual)


if __name__=="__main__":
    unittest.main()
