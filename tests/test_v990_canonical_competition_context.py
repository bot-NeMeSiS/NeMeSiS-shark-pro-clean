"""Memory-only contract tests for the canonical context prototype."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import unittest
from engines.canonical_competition_context import prepare_context

def row(key=None, **extra):
    data = {"id":"fixture-qa", "source":"Local", "odds":2.0,
            "competition_name":"Display label only", "safe_country":"Global"}
    if key is not None:
        data["competition_key"] = key
    data.update(extra)
    return data

def records_for(keys):
    return [{"key":key,"name":"Canonical " + key,"country":"Spain"} for key in keys]

class Reader:
    def __init__(self, records=None, error=False):
        self.records, self.error, self.calls = records, error, []
    def __call__(self, keys):
        self.calls.append(keys)
        if self.error:
            raise RuntimeError("synthetic_sql_read_error")
        return records_for(keys) if self.records is None else self.records

class CanonicalContextTests(unittest.TestCase):
    def test_1200_observations_35_keys_keep_800_400_cohorts_and_originals(self):
        today = [row("league-%02d" % (i % 35), id="today-%d" % i, odds=2.0) for i in range(800)]
        history = [row("league-%02d" % (i % 35), id="history-%d" % i, odds=99.0) for i in range(400)]
        before = deepcopy((today, history))
        reader = Reader()
        batch = prepare_context({"today":today,"history":history},reader)
        self.assertEqual((len(batch.cohorts["today"]),len(batch.cohorts["history"])),(800,400))
        self.assertEqual(len(batch.queried_keys),35)
        self.assertEqual(reader.calls,[batch.queried_keys])
        for name, inputs in (("today",today),("history",history)):
            for i, original in enumerate(inputs):
                self.assertEqual(batch.at(name,i).canonical_key,original["competition_key"])
                self.assertEqual(batch.for_row(original),batch.at(name,i))
                self.assertEqual(batch.at(name,i).state,"RESOLVED")
        self.assertEqual((today,history),before)
        self.assertEqual(len(reader.calls),1)

    def test_800_400_reordered_cohorts_share_only_same_reference_plan(self):
        first = [row("k%02d" % (i%35), id="a%d" % i) for i in range(800)]
        second = [row("k%02d" % (i%35), id="b%d" % i) for i in range(400)]
        a,b = Reader(),Reader()
        one = prepare_context({"today":first,"history":second},a)
        two = prepare_context({"history":reversed(second),"today":reversed(first)},b)
        self.assertEqual(one.queried_keys,two.queried_keys)
        self.assertEqual(one.required_sets,two.required_sets)
        self.assertEqual(two.cohorts["today"],tuple(reversed(one.cohorts["today"])))
        self.assertEqual(two.cohorts["history"],tuple(reversed(one.cohorts["history"])))
        self.assertEqual(a.calls,b.calls)

    def test_over_500_references_uncovered_is_not_absent_and_plan_is_order_independent(self):
        inputs = [row("c%04d" % i) for i in range(505)]
        a,b = Reader([]),Reader([])
        first=prepare_context({"x":inputs},a)
        second=prepare_context({"x":reversed(inputs)},b)
        self.assertEqual(first.queried_keys,tuple("c%04d" % i for i in range(500)))
        self.assertEqual(first.queried_keys,second.queried_keys)
        self.assertEqual(len(a.calls),1)
        self.assertEqual(first.at("x",499).state,"UNKNOWN_REFERENCE_ABSENT")
        self.assertEqual(first.at("x",500).state,"UNKNOWN_NOT_COVERED")
        self.assertEqual(first.at("x",504).state,"UNKNOWN_NOT_COVERED")
        self.assertEqual(first.not_covered_sets,second.not_covered_sets)

    def test_required_reference_set_is_never_partially_admitted(self):
        inputs=[row("a%03d" % i) for i in range(499)]
        inputs.append(row("z-pk",source="TheSportsDB",league_id="4335"))
        reader=Reader()
        batch=prepare_context({"x":inputs},reader)
        self.assertEqual(len(batch.queried_keys),499)
        self.assertNotIn("z-pk",batch.queried_keys)
        self.assertNotIn("laliga",batch.queried_keys)
        self.assertEqual(batch.at("x",499).state,"UNKNOWN_NOT_COVERED")
        self.assertEqual(batch.at("x",499).required_keys,("laliga","z-pk"))
        self.assertIn("CONFLICT_PK_MAPPING",batch.at("x",499).issues)

    def test_zero_budget_retains_every_row_without_lookup(self):
        reader=Reader()
        batch=prepare_context({"x":[row("one"),row("two")]},reader,max_keys=0)
        self.assertEqual(len(batch.cohorts["x"]),2)
        self.assertEqual(reader.calls,[])
        self.assertTrue(all(item.state=="UNKNOWN_NOT_COVERED" for item in batch.cohorts["x"]))

    def test_four_namespaces_do_not_share_native_ids(self):
        inputs=[
            row(source="TheSportsDB",league_id="4335"),
            row(source="The Odds API",league_id="soccer_spain_la_liga"),
            row(source="API-Football",league_id="4335"),
            row(source="Other Vendor",league_id="4335")]
        reader=Reader([{"key":"laliga","name":"LaLiga EA Sports","country":"Spain"}])
        batch=prepare_context({"x":inputs},reader)
        self.assertEqual([item.state for item in batch.cohorts["x"]],
            ["RESOLVED","RESOLVED","UNKNOWN","UNKNOWN"])
        self.assertEqual(batch.queried_keys,("laliga",))
        self.assertEqual(len(reader.calls),1)

    def test_api_140_without_mapping_stays_unknown_even_with_explicit_pk(self):
        batch=prepare_context({"x":[row("laliga",source="API-Football",league_id="140",country="Spain")]},Reader())
        self.assertEqual(batch.at("x",0).state,"UNKNOWN")
        self.assertIn("UNKNOWN_UNVERIFIED_ID",batch.at("x",0).issues)

    def test_provider_and_league_conflicts_are_not_hidden_by_precedence(self):
        inputs=[
            row("laliga",source="TheSportsDB",provider="API-Football",league_id="4335"),
            row(source="TheSportsDB",competition_id="4335",league_id="4328")]
        reader=Reader([{"key":"laliga","name":"LaLiga","country":"Spain"},
                       {"key":"premier-league","name":"Premier League","country":"England"}])
        batch=prepare_context({"x":inputs},reader)
        self.assertEqual([item.state for item in batch.cohorts["x"]],["CONFLICT","CONFLICT"])
        self.assertIn("CONFLICT_NAMESPACE",batch.at("x",0).issues)
        self.assertIn("CONFLICT_LEAGUE_ID",batch.at("x",1).issues)

    def test_explicit_pk_conflicting_with_authorized_provider_mapping_is_conflict(self):
        reader=Reader([{"key":"laliga","name":"LaLiga","country":"Spain"},
                       {"key":"premier-league","name":"Premier League","country":"England"}])
        batch=prepare_context({"x":[row("laliga",source="TheSportsDB",league_id="4328")]},reader)
        self.assertEqual(batch.queried_keys,("laliga","premier-league"))
        self.assertEqual(batch.at("x",0).state,"CONFLICT")
        self.assertIn("CONFLICT_PK_MAPPING",batch.at("x",0).issues)

    def test_ambiguous_authorized_mapping_never_takes_first(self):
        registry=({"key":"a","country":"Spain","sportsdb_id":"9"},
                  {"key":"b","country":"Spain","sportsdb_id":"9"})
        reader=Reader()
        batch=prepare_context({"x":[row(source="TheSportsDB",league_id="9")]},reader,registry=registry)
        self.assertEqual(batch.queried_keys,("a","b"))
        self.assertEqual(batch.at("x",0).state,"AMBIGUOUS")

    def test_duplicate_reference_rows_are_ambiguous(self):
        reader=Reader([{"key":"a","name":"A","country":"Spain"},
                       {"key":"a","name":"A","country":"Spain"}])
        self.assertEqual(prepare_context({"x":[row("a")]},reader).at("x",0).state,"AMBIGUOUS")

    def test_sql_error_is_unknown_unavailable_without_retry_or_fake_absence(self):
        reader=Reader(error=True)
        batch=prepare_context({"x":[row("a"),row("b")]},reader)
        self.assertEqual(len(reader.calls),1)
        self.assertEqual(batch.read_state,"UNAVAILABLE")
        self.assertTrue(all(item.state=="UNKNOWN_READ_UNAVAILABLE" for item in batch.cohorts["x"]))

    def test_queried_absence_is_distinct_from_malformed_read(self):
        missing=prepare_context({"x":[row("a")]},Reader([]))
        malformed=prepare_context({"x":[row("a")]},lambda _keys:None)
        foreign=prepare_context({"x":[row("a")]},Reader([{"key":"not-requested","name":"X","country":"Spain"}]))
        self.assertEqual(missing.at("x",0).state,"UNKNOWN_REFERENCE_ABSENT")
        self.assertEqual(malformed.at("x",0).state,"UNKNOWN_READ_UNAVAILABLE")
        self.assertEqual(foreign.at("x",0).state,"UNKNOWN_READ_CONTRACT")

    def test_display_country_and_labels_never_create_reference(self):
        reader=Reader()
        batch=prepare_context({"x":[row(safe_country="Global",competition_name="LaLiga"),
                                   row(safe_country="Spain",competition_name="LaLiga",country="Spain")]},reader)
        self.assertEqual(reader.calls,[])
        self.assertTrue(all(item.state=="UNKNOWN_NO_REFERENCE" for item in batch.cohorts["x"]))

    def test_country_row_payload_and_reference_use_consensus(self):
        inputs=[
            row("laliga",source="TheSportsDB",league_id="4335",country="Portugal",
                raw_json={"idLeague":"4335","strLeague":"LaLiga","strCountry":"Spain"}),
            row("laliga",source="TheSportsDB",league_id="4335",country="Spain",
                raw_json={"idLeague":"4335","strLeague":"LaLiga","strCountry":"Portugal"}),
            row("laliga",source="TheSportsDB",league_id="4335",country="Espa\u00f1a",
                raw_json={"idLeague":"4335","strLeague":"LaLiga","strCountry":"Spain"}),
            row("laliga",country="unknown",safe_country="Global")]
        reader=Reader([{"key":"laliga","name":"LaLiga EA Sports","country":"Spain"}])
        batch=prepare_context({"x":inputs},reader)
        self.assertEqual([item.state for item in batch.cohorts["x"]],
            ["CONFLICT","CONFLICT","RESOLVED","RESOLVED"])

    def test_wrong_payload_league_id_does_not_supply_a_country(self):
        inp=row("laliga",source="TheSportsDB",league_id="4335",country="Spain",
            raw_json={"idLeague":"999","strLeague":"LaLiga","strCountry":"Portugal"})
        batch=prepare_context({"x":[inp]},Reader([{"key":"laliga","name":"LaLiga","country":"Spain"}]))
        self.assertEqual(batch.at("x",0).state,"RESOLVED")
        self.assertEqual(batch.at("x",0).country_evidence,("espana",))

    def test_world_europe_real_references_are_preserved(self):
        records=[{"key":"world-cup","name":"World Cup","country":"World"},
                 {"key":"europe-cup","name":"Europe Cup","country":"Europe"}]
        inputs=[row("world-cup",country="World"),row("europe-cup",country="Europe")]
        batch=prepare_context({"x":inputs},Reader(records))
        self.assertEqual([item.state for item in batch.cohorts["x"]],["RESOLVED","RESOLVED"])
        self.assertNotEqual(batch.at("x",0).country_key,batch.at("x",1).country_key)

    def test_immutable_context_and_pure_access_do_not_requery_or_mutate_observations(self):
        inp=row("a",odds=99.0)
        before=deepcopy(inp)
        reader=Reader()
        batch=prepare_context({"x":[inp]},reader)
        with self.assertRaises(FrozenInstanceError):
            batch.at("x",0).state="FORGED"
        with self.assertRaises(TypeError):
            batch.cohorts["new"]=()
        for _ in range(50):
            self.assertEqual(batch.for_row(inp).state,"RESOLVED")
        self.assertEqual(reader.calls,[("a",)])
        self.assertEqual(inp,before)
        inp["country"]="Portugal"
        self.assertEqual(batch.for_row(inp).country_key,"espana")
        self.assertEqual(batch.for_row(row("a")).state,"UNKNOWN_NOT_PREPARED")

    def test_invalid_observation_is_retained_and_empty_cohort_is_retained(self):
        reader=Reader()
        batch=prepare_context({"x":[None,row()], "empty":[]},reader)
        self.assertEqual(len(batch.cohorts["x"]),2)
        self.assertEqual(batch.cohorts["empty"],())
        self.assertEqual(batch.at("x",0).state,"UNKNOWN")
        self.assertEqual(reader.calls,[])

    def test_overrun_read_is_unknown_contract_not_silent_truncation(self):
        reader=Reader([{"key":"a","name":"A","country":"Spain"}]*3)
        batch=prepare_context({"x":[row("a")]},reader)
        self.assertEqual(batch.at("x",0).state,"UNKNOWN_READ_CONTRACT")
        self.assertEqual(len(reader.calls),1)

    def test_incomplete_canonical_reference_does_not_borrow_country_from_label(self):
        reader=Reader([{"key":"a","name":"Spanish League","country":""}])
        batch=prepare_context({"x":[row("a",country="Spain")]},reader)
        self.assertEqual(batch.at("x",0).state,"UNKNOWN_REFERENCE_INCOMPLETE")

    def test_nonempty_invalid_league_id_is_unknown_not_silently_ignored(self):
        for field_name in ("competition_id","league_id"):
            for value in (True, [], {}, 4335.0):
                with self.subTest(field=field_name,value=value):
                    inp=row("laliga",country="Spain",**{field_name:value})
                    before=deepcopy(inp)
                    reader=Reader()
                    context=prepare_context({"x":[inp]},reader).at("x",0)
                    self.assertEqual(context.state,"UNKNOWN")
                    self.assertIn("UNKNOWN_INVALID_LEAGUE_ID",context.issues)
                    self.assertEqual(inp,before)
                    self.assertEqual(len(reader.calls),1)
