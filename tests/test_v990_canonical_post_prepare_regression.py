"""Required regression for the independent mutation review; intentionally red."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import sys
import unittest

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from engines.fixture_snapshot_read_model import prepare_fixture_snapshot
from engines.v935_launch_trust_engine import match_kickoff_madrid

def two_distinct_resolved_observations():
    kickoff="2099-01-01T20:00:00+01:00"
    common={"competition_key":"laliga","competition_name":"LaLiga","country":"Spain","season":"2098",
            "sport_key":"soccer","kickoff_iso":kickoff,"status":"NS","provider_updated_at":"2026-10-24T18:00:00Z"}
    api=dict(common,id="api-distinct",source="API_FOOTBALL",external_id="1001",competition_id="140",
             home_team="Granada CF",away_team="Real Valladolid",home_team_id="11",away_team_id="22",
             bookmaker="API Book",quote={"id":"api-quote","price":2.0})
    api["raw_json"]={"fixture":{"id":1001,"date":kickoff},"league":{"id":140,"name":"LaLiga","country":"Spain","season":2098},
                     "teams":{"home":{"id":11,"name":"Granada CF"},"away":{"id":22,"name":"Real Valladolid"}}}
    sports=dict(common,id="sports-distinct",source="TheSportsDB",external_id="2001",competition_id="4335",
                home_team="Sevilla FC",away_team="Real Betis",home_team_id="33",away_team_id="44",
                bookmaker="Sports Book",quote={"id":"sports-quote","price":3.0})
    sports["raw_json"]={"idEvent":"2001","idLeague":"4335","idHomeTeam":"33","idAwayTeam":"44",
                        "strHomeTeam":"Sevilla FC","strAwayTeam":"Real Betis","strLeague":"LaLiga",
                        "strCountry":"Spain","strSeason":"2098","strSport":"Soccer",
                        "strTimestamp":datetime.fromisoformat(kickoff).astimezone(timezone.utc).replace(tzinfo=None).isoformat()}
    return [api,sports]

def reproduce():
    rows=two_distinct_resolved_observations()
    reader_calls=[]
    def reader(keys):
        reader_calls.append(keys)
        return [{"key":"laliga","name":"LaLiga","country":"Spain","source":"API_FOOTBALL","external_id":"140"}]
    snapshot=prepare_fixture_snapshot({"actual":rows},reader,kickoff_for=match_kickoff_madrid)
    before=snapshot.select("actual")
    before_states=[snapshot.context_for(row).state for row in rows]
    originals=deepcopy(rows)
    for row in rows:
        row["home_canonical_team_id"]="injected-home"
        row["away_canonical_team_id"]="injected-away"
    after=snapshot.select("actual")
    after_states=[snapshot.context_for(row).state for row in rows]
    original_fields_unchanged=all(all(row.get(key)==value for key,value in original.items())
                                  for row,original in zip(rows,originals))
    observation={"before":{"states":before_states,"count":before.count,
                           "groups":[[row["id"] for row in group] for group in before.groups]},
                 "after":{"states":after_states,"count":after.count,
                          "groups":[[row["id"] for row in group] for group in after.groups],
                          "identity_basis":list(after.identity_basis)},
                 "reader_calls":[list(keys) for keys in reader_calls],
                 "source_fields_payloads_quotes_unchanged":original_fields_unchanged,
                 "added_fields":["home_canonical_team_id","away_canonical_team_id"],
                 "new_values":["injected-home","injected-away"]}
    return snapshot,rows,before,after,observation

class CanonicalPostPrepareMutationRegression(unittest.TestCase):
    def test_context_for_rejects_post_prepare_added_canonical_team_ids(self):
        snapshot,rows,before,after,observation=reproduce()
        self.assertEqual(observation["before"]["states"],["RESOLVED","RESOLVED"])
        self.assertEqual(before.count,2)
        self.assertTrue(observation["source_fields_payloads_quotes_unchanged"])
        self.assertEqual([snapshot.context_for(row).state for row in rows],
                         ["UNKNOWN_IDENTITY_CHANGED","UNKNOWN_IDENTITY_CHANGED"])

    def test_distinct_crossprovider_fixtures_remain_two_after_canonical_id_injection(self):
        snapshot,rows,before,after,observation=reproduce()
        self.assertEqual(before.count,2)
        self.assertEqual(len(observation["reader_calls"]),1)
        self.assertEqual(after.count,2)
