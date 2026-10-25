"""Required next-version checks, intentionally exposing current prototype gaps."""
import unittest
from engines.canonical_competition_context import prepare_context

class RequiredContextGapTests(unittest.TestCase):
    def test_unknown_substring_provider_cannot_acquire_sportsdb_identity(self):
        batch=prepare_context({"today":[{"source":"NotTheSportsDB","league_id":"4335"}]},
                              lambda keys:[{"key":"laliga","name":"LaLiga","country":"Spain","source":"TheSportsDB","external_id":"4335"}])
        self.assertEqual(batch.at("today",0).state,"UNKNOWN")
        self.assertEqual(batch.at("today",0).canonical_key,"")

    def test_existing_exact_api_catalog_reference_verifies_native_id(self):
        row={"competition_key":"api-la-liga","source":"API_FOOTBALL","league_id":"140","country":"Spain"}
        batch=prepare_context({"today":[row]},lambda keys:[
            {"key":"api-la-liga","name":"LaLiga","country":"Spain","source":"API_FOOTBALL","external_id":"140"}])
        self.assertEqual(batch.at("today",0).state,"RESOLVED")

    def test_existing_reference_native_id_conflict_remains_explicit_conflict(self):
        row={"competition_key":"api-la-liga","source":"API_FOOTBALL","league_id":"140","country":"Spain"}
        batch=prepare_context({"today":[row]},lambda keys:[
            {"key":"api-la-liga","name":"LaLiga","country":"Spain","source":"API_FOOTBALL","external_id":"999"}])
        self.assertEqual(batch.at("today",0).state,"CONFLICT")

    def test_static_mapping_does_not_hide_same_namespace_catalog_id_conflict(self):
        row={"competition_key":"laliga","source":"TheSportsDB","league_id":"4335","country":"Spain"}
        batch=prepare_context({"today":[row]},lambda keys:[
            {"key":"laliga","name":"LaLiga","country":"Spain","source":"TheSportsDB","external_id":"999"}])
        self.assertEqual(batch.at("today",0).state,"CONFLICT")

    def test_tottenham_coventry_with_labels_but_no_country_or_verified_pk_stays_unknown(self):
        row={"id":"tottenham-coventry","source":"API_FOOTBALL","competition_name":"LaLiga",
             "safe_country":"Global","home_team":"Tottenham Hotspur","away_team":"Coventry City"}
        calls=[]
        batch=prepare_context({"today":[row]},lambda keys:calls.append(keys) or [])
        self.assertEqual(batch.at("today",0).state,"UNKNOWN_NO_REFERENCE")
        self.assertEqual(calls,[])
