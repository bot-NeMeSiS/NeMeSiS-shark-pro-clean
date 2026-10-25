"""Guard correction contracts, written before implementation; no App/SQL/providers."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
sys.path.insert(0,str(APP/"tests"))
from test_v990_canonical_post_prepare_regression import two_distinct_resolved_observations
from test_v990_native_fixture_proof import pair
from engines.fixture_snapshot_read_model import prepare_fixture_snapshot
from engines.fixture_identity_read_model import unique_provider_fixtures
from engines.v935_launch_trust_engine import match_kickoff_madrid

def prepared(rows,kickoff=match_kickoff_madrid):
    calls=[]
    def read(keys):
        calls.append(keys)
        return [{"key":"laliga","name":"LaLiga","country":"Spain","source":"API_FOOTBALL","external_id":"140"}]
    snapshot=prepare_fixture_snapshot({"actual":rows},read,kickoff_for=kickoff)
    return snapshot,calls

def assert_rejected(test,snapshot,rows,kickoff=match_kickoff_madrid):
    test.assertEqual([snapshot.context_for(row).state for row in rows],
                     ["UNKNOWN_IDENTITY_CHANGED","UNKNOWN_IDENTITY_CHANGED"])
    test.assertEqual(snapshot.select("actual").count,2)
    direct=unique_provider_fixtures(rows,kickoff_for=kickoff,context_for=snapshot.context_for,
                                   rank_for=lambda row:row["id"])
    test.assertEqual(len(direct),2)

class CompleteIdentityProjectionGuardTests(unittest.TestCase):
    def test_added_canonical_ids_are_part_of_actual_identity_projection(self):
        rows=two_distinct_resolved_observations()
        snapshot,_=prepared(rows)
        self.assertEqual(snapshot.select("actual").count,2)
        for row in rows:
            row["home_canonical_team_id"]="same-home"
            row["away_canonical_team_id"]="same-away"
        assert_rejected(self,snapshot,rows)

    def test_in_place_provider_id_maps_are_tracked_by_value(self):
        rows=two_distinct_resolved_observations()
        for row in rows:
            row["home_provider_team_ids"]={}
            row["away_provider_team_ids"]={}
        snapshot,_=prepared(rows)
        for row in rows:
            row["home_provider_team_ids"]["verified-third-provider"]="same-home"
            row["away_provider_team_ids"]["verified-third-provider"]="same-away"
        assert_rejected(self,snapshot,rows)

    def test_alias_lists_are_tracked_by_value(self):
        rows=two_distinct_resolved_observations()
        for row in rows:
            row["home_team_aliases"]=[]
            row["away_team_aliases"]=[]
        snapshot,_=prepared(rows)
        for row in rows:
            row["home_team_aliases"].append("Shared Harbor")
            row["away_team_aliases"].append("Shared Ridge")
        assert_rejected(self,snapshot,rows)

    def test_nested_entity_canonical_and_provider_ids_are_tracked(self):
        for variant in ("canonical","provider_ids","aliases"):
            with self.subTest(variant=variant):
                rows=two_distinct_resolved_observations()
                for row in rows:
                    for side in ("home","away"):
                        row[side+"_team_entity"]={"canonical_team_id":"","provider_team_ids":{},"aliases":[]}
                snapshot,_=prepared(rows)
                for row in rows:
                    for side in ("home","away"):
                        nested=row[side+"_team_entity"]
                        if variant=="canonical":
                            nested["canonical_team_id"]="same-"+side
                        elif variant=="provider_ids":
                            nested["provider_team_ids"]["verified-third-provider"]="same-"+side
                        else:
                            nested["aliases"].append("Shared "+side)
                assert_rejected(self,snapshot,rows)

    def test_mapping_teams_and_lateral_categories_are_tracked(self):
        rows=two_distinct_resolved_observations()
        for row in rows:
            for side in ("home","away"):
                row[side+"_team"]={"official_name":row[side+"_team"],"canonical_team_id":""}
        snapshot,_=prepared(rows)
        for row in rows:
            row["home_team"]["canonical_team_id"]="same-home"
            row["away_team"]["canonical_team_id"]="same-away"
        assert_rejected(self,snapshot,rows)
        for field in ("home_gender","home_team_gender","home_category","home_team_category",
                      "home_age_group","home_team_age_group"):
            with self.subTest(field=field):
                rows=two_distinct_resolved_observations()
                snapshot,_=prepared(rows)
                for row in rows:
                    row[field]="women" if "gender" in field else "U19"
                assert_rejected(self,snapshot,rows)

    def test_all_explicit_and_callback_fallback_kickoffs_are_guarded(self):
        for field in ("kickoff_iso_madrid","madrid_dt_iso","start_time","datetime","date_time"):
            with self.subTest(field=field):
                rows=two_distinct_resolved_observations()
                for row in rows:
                    row[field]=row.pop("kickoff_iso")
                kickoff=lambda row,field=field:datetime.fromisoformat(row[field])
                snapshot,_=prepared(rows,kickoff)
                for row in rows:
                    row[field]="2099-01-01T20:00:01+01:00"
                assert_rejected(self,snapshot,rows,kickoff)
        rows=two_distinct_resolved_observations()
        for row in rows:
            row.pop("kickoff_iso")
            row["match_date"]="2099-01-01"
            row["time"]="20:00"
        kickoff=lambda row:datetime.fromisoformat(row["match_date"]+"T"+row["time"]+":00+01:00")
        snapshot,_=prepared(rows,kickoff)
        for row in rows:
            row["time"]="20:01"
        assert_rejected(self,snapshot,rows,kickoff)

    def test_clock_terminal_and_nested_status_inputs_are_not_opaque(self):
        changes=({"provider_updated_at":"2026-10-24T18:02:00Z"},
                 {"status_short":"FT","home_score":0,"away_score":0},
                 {"status_info":{"is_finished":True},"score":"0-0"})
        for change in changes:
            with self.subTest(change=change):
                rows=two_distinct_resolved_observations()
                snapshot,_=prepared(rows)
                for row in rows:
                    row.update(change)
                assert_rejected(self,snapshot,rows)

    def test_limits_and_unsupported_inputs_block_native_fallback_before_normalization(self):
        cases=("aliases","provider_ids","label","raw_json","unsupported_alias")
        for case in cases:
            with self.subTest(case=case):
                rows=pair()
                for row in rows:
                    if case=="aliases": row["home_team_aliases"]=["Alias "+str(i) for i in range(8)]
                    elif case=="provider_ids": row["home_provider_team_ids"]={"vendor"+str(i):str(i) for i in range(17)}
                    elif case=="label": row["home_team"]="x"*1025
                    elif case=="raw_json": row["raw_json"]="x"*131073
                    else: row["home_team_aliases"]=[{"unsupported":"mapping"}]
                with patch("engines.fixture_identity_read_model._team",side_effect=AssertionError("unbounded team normalization")):
                    snapshot,calls=prepared(rows)
                    self.assertEqual([snapshot.context_for(row).state for row in rows],
                                     ["UNKNOWN_IDENTITY_LIMIT","UNKNOWN_IDENTITY_LIMIT"])
                    selected=snapshot.select("actual")
                self.assertEqual(selected.count,2)
                self.assertEqual(selected.native_fixture_groups,0)
                self.assertEqual(calls,[])

    def test_oversized_raw_is_not_sent_to_context_payload_parser(self):
        rows=pair()
        for row in rows:
            row["raw_json"]="x"*131073
        with patch("engines.canonical_competition_context.provider_competition_facts",
                   side_effect=AssertionError("unsupported raw parser")) as parser:
            snapshot,calls=prepared(rows)
            self.assertEqual([snapshot.context_for(row).state for row in rows],
                             ["UNKNOWN_IDENTITY_LIMIT","UNKNOWN_IDENTITY_LIMIT"])
            self.assertEqual(snapshot.select("actual").count,2)
        self.assertEqual(parser.call_count,0)
        self.assertEqual(calls,[])

    def test_alias_text_segments_and_recursive_status_are_bounded(self):
        for case in ("long_alias","recursive_status"):
            with self.subTest(case=case):
                rows=pair()
                for row in rows:
                    if case=="long_alias":
                        row["home_team_aliases"]="x"*1025
                    else:
                        status={}
                        status["status"]=status
                        row["status_info"]=status
                with patch("engines.fixture_identity_read_model._team",side_effect=AssertionError("unsupported normalization")):
                    snapshot,calls=prepared(rows)
                    self.assertEqual([snapshot.context_for(row).state for row in rows],
                                     ["UNKNOWN_IDENTITY_LIMIT","UNKNOWN_IDENTITY_LIMIT"])
                    self.assertEqual(snapshot.select("actual").count,2)
                    direct=unique_provider_fixtures(rows,kickoff_for=match_kickoff_madrid,
                        context_for=snapshot.context_for,rank_for=lambda row:row["id"])
                    self.assertEqual(len(direct),2)
                self.assertEqual(calls,[])

    def test_unsupported_identifier_never_runs_string_or_rank_normalization(self):
        class UnsupportedIdentifier:
            def __str__(self):
                raise AssertionError("unsupported identifier conversion")
        rows=pair()
        for row in rows:
            row["id"]=UnsupportedIdentifier()
        snapshot,calls=prepared(rows)
        self.assertEqual([snapshot.context_for(row).state for row in rows],
                         ["UNKNOWN_IDENTITY_LIMIT","UNKNOWN_IDENTITY_LIMIT"])
        def forbidden_rank(row):
            raise AssertionError("unverifiable singleton rank")
        self.assertEqual(snapshot.select("actual",rank_for=forbidden_rank).count,2)
        direct=unique_provider_fixtures(rows,kickoff_for=match_kickoff_madrid,
                                       context_for=snapshot.context_for,rank_for=forbidden_rank)
        self.assertEqual(len(direct),2)
        self.assertEqual(calls,[])

    def test_presentation_fields_are_excluded_without_changing_original_quotes(self):
        rows=pair()
        for row in rows:
            row["home_team_entity"]={"logo_url":"old","color":"blue"}
        before=deepcopy(rows)
        snapshot,_=prepared(rows)
        for row in rows:
            row["is_favorite"]=True
            row["has_pick"]=True
            row["home_team_entity"]["logo_url"]="new"
            row["home_team_entity"]["color"]="red"
        self.assertEqual(snapshot.select("actual").count,1)
        for row,original in zip(rows,before):
            self.assertEqual(row["quote"],original["quote"])
            self.assertEqual(row["provider_quota"],original["provider_quota"])
            self.assertEqual(row["raw_json"],original["raw_json"])
