"""Adversarial native fixture proof contracts; no app/providers/real database."""
from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engines.fixture_snapshot_read_model import prepare_fixture_snapshot
from engines.fixture_identity_read_model import unique_provider_fixtures
from engines.v935_launch_trust_engine import match_kickoff_madrid

def payload(row):
    if row["source"]=="TheSportsDB":
        return {"idEvent":row["external_id"],"idLeague":row["competition_id"],
                "idHomeTeam":row["home_team_id"],"idAwayTeam":row["away_team_id"],
                "strHomeTeam":row["home_team"],"strAwayTeam":row["away_team"],
                "strLeague":row["competition_name"],"strCountry":row.get("country",""),
                "strSeason":row["season"],"strSport":"Soccer",
                "strTimestamp":datetime.fromisoformat(row["kickoff_iso"]).astimezone(timezone.utc).replace(tzinfo=None).isoformat()}
    return {"fixture":{"id":int(row["external_id"]),"date":row["kickoff_iso"],"status":{"short":row["status"]}},
            "league":{"id":int(row["competition_id"]),"name":row["competition_name"],
                      "country":row.get("country",""),"season":int(row["season"])},
            "teams":{"home":{"id":int(row["home_team_id"]),"name":row["home_team"]},
                     "away":{"id":int(row["away_team_id"]),"name":row["away_team"]}},
            "goals":{"home":row.get("home_score"),"away":row.get("away_score")}}

def observation(local="local-a",*,provider="API_FOOTBALL",native="1001",clock="2026-10-24T18:00:00Z",**extra):
    row={"id":local,"source":provider,"external_id":native,
         "competition_id":"9999" if provider=="TheSportsDB" else "140",
         "competition_name":"Unmapped League","country":"Spain","sport_key":"soccer",
         "home_team":"Granada CF","away_team":"Real Valladolid","home_team_id":"11","away_team_id":"22",
         "kickoff_iso":"2099-01-01T20:00:00+01:00","status":"NS","season":"2098",
         "provider_updated_at":clock,"bookmaker":"Book "+local,"quote":{"id":"quote-"+local,"price":2.0},
         "provider_quota":{"remaining":37,"calls":0},"has_pick":False,"is_favorite":False}
    row.update(extra)
    row["raw_json"]=payload(row)
    return row

def pair(provider="API_FOOTBALL"):
    return [observation("local-a",provider=provider),
            observation("local-b",provider=provider,clock="2026-10-24T18:01:00Z")]

def prepare(rows,reader=None):
    calls=[]
    def read(keys):
        calls.append(keys)
        return [] if reader is None else reader(keys)
    result=prepare_fixture_snapshot({"actual":rows},read,kickoff_for=match_kickoff_madrid)
    return result,calls

class NativeFixtureProofContracts(unittest.TestCase):
    def test_api_same_native_fixture_without_catalog_groups_whole_originals(self):
        rows=pair()
        before=deepcopy(rows)
        snapshot,calls=prepare(rows)
        selection=snapshot.select("actual",rank_for=lambda row:row["id"]=="local-a")
        self.assertEqual(selection.count,1)
        self.assertEqual(selection.groups,(tuple(rows),))
        self.assertIs(selection.rows[0],rows[1])
        self.assertEqual(selection.native_fixture_groups,1)
        self.assertEqual(selection.identity_basis,("PROVIDER_NATIVE_FIXTURE",))
        self.assertEqual(selection.confirmed_count,0)
        self.assertEqual(selection.unresolved_observations,2)
        self.assertEqual({item.state for item in snapshot.context.cohorts["actual"]},{"UNKNOWN"})
        self.assertEqual(calls,[])
        self.assertEqual(set(selection.fixture_ids),{"local-a","local-b"})
        self.assertEqual(rows,before)

    def test_sportsdb_same_native_fixture_without_catalog_and_utc_naive_payload(self):
        rows=pair("TheSportsDB")
        snapshot,calls=prepare(rows)
        selection=snapshot.select("actual")
        self.assertEqual(selection.count,1)
        self.assertEqual(selection.native_fixture_groups,1)
        self.assertEqual(calls,[])

    def test_json_text_payloads_are_verified_without_changing_original_strings(self):
        for provider in ("API_FOOTBALL","TheSportsDB"):
            with self.subTest(provider=provider):
                rows=pair(provider)
                for row in rows:
                    row["raw_json"]=json.dumps(row["raw_json"])
                before=deepcopy(rows)
                selection=prepare(rows)[0].select("actual")
                self.assertEqual(selection.count,1)
                self.assertEqual(rows,before)

    def test_native_identity_does_not_invent_country_or_canonical_competition(self):
        rows=pair()
        for row in rows:
            row.pop("country")
            row["safe_country"]="Global"
            row["raw_json"]["league"]["country"]=""
        snapshot,_=prepare(rows)
        selected=snapshot.select("actual")
        self.assertEqual(selected.count,1)
        for context in snapshot.context.cohorts["actual"]:
            self.assertEqual(context.country_evidence,())
            self.assertEqual(context.canonical_key,"")
            self.assertNotEqual(context.state,"RESOLVED")

    def test_excessive_native_claimants_stay_visible_without_pairwise_work(self):
        rows=[observation("alias-"+str(i)) for i in range(65)]
        snapshot,_=prepare(rows)
        with patch("engines.fixture_identity_read_model._compatible",side_effect=AssertionError("overloaded native anchor")):
            selected=snapshot.select("actual")
        self.assertEqual(selected.count,65)
        self.assertEqual(selected.native_fixture_groups,0)
        self.assertEqual(set(selected.identity_basis),{"UNRESOLVED_NATIVE_OVERLOAD"})

    def test_complete_native_payload_must_belong_to_each_original_observation(self):
        for provider in ("API_FOOTBALL","TheSportsDB"):
            for missing in ("raw_json","external_id","competition_id","home_team_id","away_team_id","kickoff_iso"):
                with self.subTest(provider=provider,missing=missing):
                    rows=pair(provider)
                    rows[1].pop(missing)
                    snapshot,_=prepare(rows)
                    self.assertEqual(snapshot.select("actual").count,2)
            for raw in ({},[],None,"broken-json"):
                with self.subTest(provider=provider,raw=raw):
                    rows=pair(provider)
                    rows[1]["raw_json"]=raw
                    self.assertEqual(prepare(rows)[0].select("actual").count,2)

    def test_missing_original_native_fields_do_not_borrow_other_payload(self):
        paths=(("fixture","id"),("fixture","date"),("league","id"),
               ("teams","home","id"),("teams","away","id"))
        for path in paths:
            with self.subTest(path=path):
                rows=pair()
                target=rows[1]["raw_json"]
                for key in path[:-1]:
                    target=target[key]
                target.pop(path[-1])
                self.assertEqual(prepare(rows)[0].select("actual").count,2)

    def test_exact_known_namespace_and_source_provider_consensus_are_mandatory(self):
        for change in ({"source":"NotAPI_FOOTBALL"},{"provider":"TheSportsDB"},
                       {"source":"API_FOOTBALL fake mirror"}):
            with self.subTest(change=change):
                rows=pair()
                rows[1].update(change)
                self.assertEqual(prepare(rows)[0].select("actual").count,2)
        rows=pair()
        rows[1]["raw_json"]=payload(observation(provider="TheSportsDB"))
        self.assertEqual(prepare(rows)[0].select("actual").count,2)

    def test_same_numeric_fixture_id_does_not_cross_provider_namespace(self):
        rows=[observation("api"),observation("sports",provider="TheSportsDB")]
        self.assertEqual(prepare(rows)[0].select("actual").count,2)

    def test_same_provider_different_native_fixture_id_stays_separate(self):
        rows=[observation("one"),observation("two",native="1002")]
        self.assertEqual(prepare(rows)[0].select("actual").count,2)

    def test_borrowed_or_contradictory_payload_ids_never_group(self):
        paths=(("fixture","id"),("league","id"),("teams","home","id"),("teams","away","id"))
        for path in paths:
            with self.subTest(path=path):
                rows=pair()
                target=rows[1]["raw_json"]
                for key in path[:-1]:
                    target=target[key]
                target[path[-1]]=99999
                self.assertEqual(prepare(rows)[0].select("actual").count,2)
        rows=pair()
        rows[1].update(id="af-99999")
        self.assertEqual(prepare(rows)[0].select("actual").count,2)

    def test_explicit_league_country_season_sport_side_category_and_time_conflicts_block(self):
        changes=({"competition_id":"141"},{"country":"Portugal"},{"season":"2099"},
                 {"sport_key":"basketball"},{"home_team_id":"999"},{"home_team":"Granada CF B"},
                 {"kickoff_iso":"2099-01-01T20:00:01+01:00"},
                 {"home_team":"Real Valladolid","away_team":"Granada CF","home_team_id":"22","away_team_id":"11"})
        for change in changes:
            with self.subTest(change=change):
                rows=pair()
                rows[1].update(change)
                rows[1]["raw_json"]=payload(rows[1])
                self.assertEqual(prepare(rows)[0].select("actual").count,2)
        rows=pair()
        rows[1]["league_id"]="141"
        self.assertEqual(prepare(rows)[0].select("actual").count,2)
        rows=pair()
        rows[1]["status_conflict"]=True
        self.assertEqual(prepare(rows)[0].select("actual").count,2)

    def test_conflicting_confirmed_finals_never_merge_even_with_later_clock(self):
        rows=pair()
        rows[0].update(status="FT",home_score=0,away_score=0)
        rows[1].update(status="FT",home_score=1,away_score=0)
        for row in rows:
            row["raw_json"]=payload(row)
        self.assertEqual(prepare(rows)[0].select("actual").count,2)

    def test_three_claimants_with_explicit_conflict_remain_all_visible(self):
        rows=pair()
        third=observation("local-c",country="Portugal")
        rows.append(third)
        snapshot,_=prepare(rows)
        selection=snapshot.select("actual")
        self.assertEqual(selection.count,3)
        self.assertEqual(selection.native_fixture_groups,0)
        self.assertEqual(set(selection.identity_basis),{"CONFLICT_NATIVE_OBSERVATIONS"})

    def test_context_conflict_cannot_be_overridden_by_native_proof(self):
        rows=pair()
        for row in rows:
            row["competition_key"]="api-league"
        reader=lambda keys:[{"key":"api-league","name":"League","country":"Spain","source":"API_FOOTBALL","external_id":"999"}]
        snapshot,calls=prepare(rows,reader)
        self.assertEqual({item.state for item in snapshot.context.cohorts["actual"]},{"CONFLICT"})
        self.assertEqual(snapshot.select("actual").count,2)
        self.assertEqual(len(calls),1)

    def test_canonical_and_native_confirmation_bases_are_not_double_counted(self):
        rows=pair()
        for row in rows:
            row["competition_key"]="api-league"
        reader=lambda keys:[{"key":"api-league","name":"League","country":"Spain","source":"API_FOOTBALL","external_id":"140"}]
        snapshot,_=prepare(rows,reader)
        selected=snapshot.select("actual")
        self.assertEqual((selected.count,selected.confirmed_count,selected.native_fixture_groups),(1,1,0))
        self.assertEqual(selected.identity_basis,("CANONICAL_COMPETITION",))

    def test_native_exception_does_not_enable_crossprovider_nominal_bridge(self):
        rows=pair()
        rows.append(observation("sports",provider="TheSportsDB"))
        snapshot,_=prepare(rows)
        selection=snapshot.select("actual")
        self.assertEqual(selection.count,2)
        self.assertEqual(sorted(len(group) for group in selection.groups),[1,2])
        self.assertEqual(selection.confirmed_count,0)

    def test_native_anchor_never_transitively_bridges_unknown_into_crossprovider_group(self):
        rows=pair()
        rows[0]["competition_key"]="laliga"
        third=observation("sports",provider="TheSportsDB",competition_id="4335",competition_key="laliga")
        rows.append(third)
        reader=lambda keys:[{"key":"laliga","name":"LaLiga","country":"Spain","source":"API_FOOTBALL","external_id":"140"}]
        snapshot,calls=prepare(rows,reader)
        selected=snapshot.select("actual")
        self.assertEqual(selected.count,3)
        self.assertEqual(selected.native_fixture_groups,0)
        self.assertEqual(set(selected.identity_basis),{"AMBIGUOUS_FIXTURE_COMPONENT"})
        self.assertEqual(len(calls),1)

    def test_unprepared_clone_and_invalid_namespace_never_gain_native_proof(self):
        rows=pair()
        snapshot,_=prepare(rows)
        self.assertEqual(snapshot.select_rows([dict(row) for row in rows]).count,2)

    def test_post_prepare_identity_mutation_never_reuses_resolved_context(self):
        changes=({"source":"TheSportsDB"},{"external_id":"1002"},{"competition_key":"other-pk"},
                 {"competition_id":"141"},{"league_id":"141"},{"country":"Portugal"})
        for change in changes:
            with self.subTest(change=change):
                rows=pair()
                for row in rows:
                    row["competition_key"]="api-league"
                reader=lambda keys:[{"key":"api-league","name":"League","country":"Spain","source":"API_FOOTBALL","external_id":"140"}]
                snapshot,_=prepare(rows,reader)
                self.assertEqual(snapshot.context.for_row(rows[0]).state,"RESOLVED")
                rows[0].update(change)
                selection=snapshot.select("actual")
                self.assertEqual(selection.count,2)
                self.assertEqual(selection.unresolved_observations,1)
                direct=unique_provider_fixtures(rows,kickoff_for=match_kickoff_madrid,
                    context_for=snapshot.context_for,rank_for=lambda row:row["id"])
                self.assertEqual(len(direct),2)

    def test_post_prepare_presentation_flags_do_not_change_identity_proof(self):
        rows=pair()
        snapshot,_=prepare(rows)
        rows[0].update(is_favorite=True,has_pick=True)
        self.assertEqual(snapshot.select("actual").count,1)

    def test_post_prepare_raw_identity_mutation_is_rejected_without_payload_copy(self):
        for path,bad in ((("league","country"),"Portugal"),(("fixture","id"),99999),
                         (("teams","home","id"),99999),(("fixture","date"),"2099-01-01T20:00:01+01:00")):
            with self.subTest(path=path):
                rows=pair()
                for row in rows:
                    row["competition_key"]="api-league"
                    row.pop("country")
                reader=lambda keys:[{"key":"api-league","name":"League","country":"Spain","source":"API_FOOTBALL","external_id":"140"}]
                snapshot,_=prepare(rows,reader)
                original_payload=rows[0]["raw_json"]
                target=original_payload
                for key in path[:-1]:
                    target=target[key]
                target[path[-1]]=bad
                selected=snapshot.select("actual")
                self.assertEqual(snapshot.context_for(rows[0]).state,"UNKNOWN_IDENTITY_CHANGED")
                self.assertEqual(selected.count,2)
                self.assertEqual(selected.unresolved_observations,1)
                self.assertIs(snapshot.cohorts["actual"][0]["raw_json"],original_payload)

    def test_filter_precedes_native_group_and_limit_preserves_alternate_actions(self):
        rows=pair()
        rows[0]["is_favorite"]=True
        rows[0]["has_pick"]=True
        third=observation("other",native="1002")
        rows.append(third)
        snapshot,_=prepare(rows)
        selected=snapshot.select("actual",predicate=lambda row:row["is_favorite"],limit=1)
        self.assertIs(selected.rows[0],rows[0])
        selected=snapshot.select("actual",limit=2)
        self.assertEqual(selected.count,2)
        self.assertEqual(len(selected.rows),2)
        self.assertEqual({row["id"] for group in selected.groups for row in group},{"local-a","local-b","other"})

    def test_latest_provider_observation_wins_whole_row_over_visual_rank(self):
        rows=pair()
        before=deepcopy(rows)
        snapshot,_=prepare(rows)
        selected=snapshot.select("actual",rank_for=lambda row:100 if row["id"]=="local-a" else 0)
        self.assertIs(selected.rows[0],rows[1])
        direct=unique_provider_fixtures(rows,kickoff_for=match_kickoff_madrid,
            context_for=snapshot.context_for,rank_for=lambda row:row["id"]=="local-a")
        self.assertIs(direct[0],rows[1])
        self.assertEqual(rows,before)

    def test_invalid_priority_clock_never_borrows_a_newer_fallback_clock(self):
        rows=pair()
        rows[1]["live_updated_at"]="invalid-priority-clock"
        snapshot,_=prepare(rows)
        selected=snapshot.select("actual",rank_for=lambda row:row["id"]=="local-b")
        self.assertIs(selected.rows[0],rows[0])

    def test_untimed_final_never_rolls_back_to_live_and_originals_remain(self):
        rows=pair()
        rows[0].update(status="FT",home_score=0,away_score=0)
        rows[0].pop("provider_updated_at")
        rows[1].update(status="LIVE",home_score=0,away_score=0)
        for row in rows:
            row["raw_json"]=payload(row)
        snapshot,_=prepare(rows)
        selected=snapshot.select("actual",rank_for=lambda row:row["id"]=="local-b")
        self.assertEqual(selected.count,1)
        self.assertIs(selected.rows[0],rows[0])
        self.assertEqual(len(selected.groups[0]),2)
