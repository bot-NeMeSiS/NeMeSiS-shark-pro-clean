"""Portable exact-alias contracts. Synthetic observations; no App/SQL/providers.

Producer provenance is recorded separately by the guarded review runner. This
suite requires no league crosswalk, catalogue mutation or raw-prefix inference.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import unittest

from engines.canonical_competition_context import _namespace, prepare_context
from engines.fixture_snapshot_read_model import prepare_fixture_snapshot
from engines.v935_launch_trust_engine import match_kickoff_madrid

REAL_SOURCE = "api_football_live"
KICKOFF = "2099-01-01T20:00:00+01:00"
PRODUCER_SLUG_EXAMPLE = "la-liga-spain"


def api_observation(local_id="af-1001", *, source=REAL_SOURCE, provider=None):
    row = {"id": local_id, "source": source, "external_id": "1001", "sport_key": "soccer",
           "competition_id": "140", "competition_name": "La Liga", "league_name": "La Liga",
           "country": "Spain", "season": "2098", "kickoff_iso": KICKOFF,
           "home_team": "Granada CF", "away_team": "Real Valladolid",
           "home_team_id": "11", "away_team_id": "22", "status": "NS",
           "last_synced_at": "2026-10-25T08:00:00Z", "quote": {"id": "quote-" + local_id, "price": 2.0},
           "provider_quota": {"remaining": 37, "calls": 0}}
    if provider is not None:
        row["provider"] = provider
    row["raw_json"] = {"fixture": {"id": 1001, "date": KICKOFF, "status": {"short": "NS"}},
                       "league": {"id": 140, "name": "La Liga", "country": "Spain", "season": 2098},
                       "teams": {"home": {"id": 11, "name": "Granada CF"},
                                 "away": {"id": 22, "name": "Real Valladolid"}}}
    return row


def api_pair(**kwargs):
    rows = [api_observation(**kwargs), api_observation("other-local-1001", **kwargs)]
    rows[1]["last_synced_at"] = "2026-10-25T08:01:00Z"
    return rows


def catalogue_record(*, source="API_FOOTBALL", external_id="140", key="laliga"):
    return {"key": key, "name": "La Liga", "country": "Spain", "source": source, "external_id": external_id}


def prepare(rows, records=()):
    calls = []
    def reader(keys):
        calls.append(tuple(keys))
        # Exact PK lookup contract: unrelated reference records are not returned.
        return [dict(record) for record in records if record["key"] in keys]
    snapshot = prepare_fixture_snapshot({"actual": rows}, reader, kickoff_for=match_kickoff_madrid)
    return snapshot, calls


def sportsdb_observation():
    row = api_observation("sportsdb-2001", source="TheSportsDB")
    row.update(external_id="2001", competition_id="4335", competition_key="laliga",
               home_team_id="33", away_team_id="44")
    row["raw_json"] = {"idEvent": "2001", "idLeague": "4335", "idHomeTeam": "33", "idAwayTeam": "44",
                       "strHomeTeam": row["home_team"], "strAwayTeam": row["away_team"], "strLeague": "La Liga",
                       "strCountry": "Spain", "strSeason": "2098", "strSport": "Soccer",
                       "strTimestamp": datetime.fromisoformat(KICKOFF).astimezone(timezone.utc).replace(tzinfo=None).isoformat()}
    return row


class RealSourceExactAliasContracts(unittest.TestCase):
    def test_real_producer_tag_is_one_exact_known_alias(self):
        self.assertEqual(_namespace(REAL_SOURCE), "api-football")
        for variant in ("API_FOOTBALL_LIVE", "api-football-live", "API.FOOTBALL.LIVE"):
            self.assertEqual(_namespace(variant), "api-football")
        self.assertEqual(_namespace("api_football_live_alt"), "api-football-live-alt")
        self.assertNotEqual(_namespace("api_football_live_alt"), "api-football")

    def test_two_local_ids_same_own_native_fixture_group_without_canonical_reference(self):
        rows = api_pair()
        before = deepcopy(rows)
        raw_ids = [row["raw_json"] for row in rows]
        quotes = [row["quote"] for row in rows]
        quotas = [row["provider_quota"] for row in rows]
        snapshot, calls = prepare(rows)
        self.assertEqual([snapshot.context_for(row).state for row in rows], ["UNKNOWN", "UNKNOWN"])
        selected = snapshot.select("actual")
        self.assertEqual(selected.count, 1)
        self.assertEqual(selected.identity_basis, ("PROVIDER_NATIVE_FIXTURE",))
        self.assertEqual(selected.native_fixture_groups, 1)
        self.assertEqual(selected.confirmed_count, 0)
        self.assertEqual(selected.unresolved_observations, 2)
        self.assertEqual(selected.groups, (tuple(rows),))
        self.assertEqual(set(selected.fixture_ids), {"af-1001", "other-local-1001"})
        self.assertIs(selected.rows[0], rows[1])
        self.assertEqual(calls, [])
        self.assertEqual(rows, before)
        for number, row in enumerate(rows):
            self.assertIs(row["raw_json"], raw_ids[number])
            self.assertIs(row["quote"], quotes[number])
            self.assertIs(row["provider_quota"], quotas[number])

    def test_native_own_json_text_payload_from_producer_is_accepted_intact(self):
        rows = api_pair()
        for row in rows:
            row["raw_json"] = json.dumps(row["raw_json"])
        originals = [row["raw_json"] for row in rows]
        snapshot, calls = prepare(rows)
        selected = snapshot.select("actual")
        self.assertEqual(selected.count, 1)
        self.assertEqual(selected.identity_basis, ("PROVIDER_NATIVE_FIXTURE",))
        self.assertEqual(calls, [])
        for row, raw in zip(rows, originals):
            self.assertIs(row["raw_json"], raw)

    def test_known_source_provider_aliases_are_compatible_with_real_tag(self):
        rows = [api_observation(provider="API_SPORTS"),
                api_observation("other-local-1001", source="API_FOOTBALL_PRIMARY", provider=REAL_SOURCE)]
        snapshot, calls = prepare(rows)
        self.assertEqual([snapshot.context_for(row).state for row in rows], ["UNKNOWN", "UNKNOWN"])
        self.assertTrue(all("CONFLICT_NAMESPACE" not in snapshot.context_for(row).issues for row in rows))
        self.assertEqual(snapshot.select("actual").identity_basis, ("PROVIDER_NATIVE_FIXTURE",))
        self.assertEqual(snapshot.select("actual").count, 1)
        self.assertEqual(calls, [])

    def test_lookalike_source_does_not_group_even_with_api_id_prefix_and_raw_shape(self):
        rows = api_pair(source="api_football_live_alt")
        snapshot, calls = prepare(rows)
        self.assertEqual(snapshot.select("actual").count, 2)
        self.assertEqual(snapshot.select("actual").native_fixture_groups, 0)
        self.assertTrue(all(snapshot.context_for(row).state != "RESOLVED" for row in rows))
        self.assertEqual(calls, [])

    def test_explicit_contradictory_namespace_blocks_native_grouping(self):
        rows = api_pair(provider="TheSportsDB")
        snapshot, calls = prepare(rows)
        self.assertEqual([snapshot.context_for(row).state for row in rows], ["CONFLICT", "CONFLICT"])
        self.assertTrue(all("CONFLICT_NAMESPACE" in snapshot.context_for(row).issues for row in rows))
        self.assertEqual(snapshot.select("actual").count, 2)
        self.assertEqual(snapshot.select("actual").native_fixture_groups, 0)
        self.assertEqual(calls, [])

    def test_payload_fixture_id_cannot_override_another_original_external_id(self):
        rows = api_pair()
        rows[1]["raw_json"]["fixture"]["id"] = 1002
        before = deepcopy(rows)
        selected = prepare(rows)[0].select("actual")
        self.assertEqual(selected.count, 2)
        self.assertEqual(selected.groups, tuple((row,) for row in rows))
        # The intact first observation retains native proof as a singleton;
        # this counter records evidence basis, not only successful pair merges.
        self.assertEqual(selected.native_fixture_groups, 1)
        self.assertEqual(rows, before)

    def test_explicit_pk_and_matching_api_140_catalogue_reference_resolve(self):
        row = api_observation()
        row["competition_key"] = "laliga"
        snapshot, calls = prepare([row], [catalogue_record()])
        context = snapshot.context_for(row)
        self.assertEqual(context.state, "RESOLVED")
        self.assertEqual(context.canonical_key, "laliga")
        self.assertNotIn("UNKNOWN_UNVERIFIED_ID", context.issues)
        self.assertEqual(calls, [("laliga",)])

    def test_api_140_explicit_pk_with_sportsdb_reference_does_not_verify_api_id(self):
        row = api_observation()
        row["competition_key"] = "laliga"
        snapshot, calls = prepare([row], [catalogue_record(source="TheSportsDB", external_id="4335")])
        context = snapshot.context_for(row)
        self.assertEqual(context.state, "UNKNOWN")
        self.assertEqual(context.canonical_key, "")
        self.assertIn("UNKNOWN_UNVERIFIED_ID", context.issues)
        self.assertEqual(calls, [("laliga",)])

    def test_matching_namespace_with_different_catalogue_native_id_is_conflict(self):
        row = api_observation()
        row["competition_key"] = "laliga"
        snapshot, _calls = prepare([row], [catalogue_record(external_id="141")])
        self.assertEqual(snapshot.context_for(row).state, "CONFLICT")
        self.assertIn("CONFLICT_REFERENCE_NATIVE_ID", snapshot.context_for(row).issues)

    def test_reviewed_producer_slug_and_canonical_pk_are_both_queried_literally(self):
        row = api_observation()
        row["competition_key"] = PRODUCER_SLUG_EXAMPLE
        snapshot, calls = prepare([row], [catalogue_record()])
        context = snapshot.context_for(row)
        self.assertEqual(calls, [(PRODUCER_SLUG_EXAMPLE, "laliga")])
        self.assertEqual(context.required_keys, (PRODUCER_SLUG_EXAMPLE, "laliga"))
        self.assertEqual(context.state, "RESOLVED")
        self.assertEqual(context.canonical_key, "laliga")

    def test_country_and_same_labels_do_not_bridge_unknown_api_slug_to_sportsdb_pk(self):
        api = api_observation()
        api["competition_key"] = PRODUCER_SLUG_EXAMPLE + "-unreviewed"
        sports = sportsdb_observation()
        rows = [api, sports]
        before = deepcopy(rows)
        snapshot, calls = prepare(rows, [catalogue_record(source="TheSportsDB", external_id="4335")])
        self.assertNotEqual(snapshot.context_for(api).state, "RESOLVED")
        self.assertEqual(snapshot.context_for(sports).state, "RESOLVED")
        self.assertEqual(snapshot.select("actual").count, 2)
        self.assertEqual(snapshot.select("actual").groups, tuple((row,) for row in rows))
        self.assertEqual(snapshot.select("actual").native_fixture_groups, 1)
        self.assertEqual(calls, [(PRODUCER_SLUG_EXAMPLE + "-unreviewed", "laliga")])
        self.assertEqual(rows, before)

    def test_missing_row_or_raw_native_ids_does_not_claim_same_provider_native_guarantee(self):
        for field in ("external_id", "competition_id", "home_team_id", "away_team_id", "raw_json"):
            with self.subTest(field=field):
                rows = api_pair()
                for row in rows:
                    row.pop(field)
                snapshot, calls = prepare(rows)
                self.assertEqual(snapshot.select("actual").count, 2)
                self.assertEqual(snapshot.select("actual").native_fixture_groups, 0)
                self.assertEqual(calls, [])
        for path in (("fixture", "id"), ("fixture", "date"), ("league", "id"),
                     ("teams", "home", "id"), ("teams", "away", "id")):
            with self.subTest(raw_path=path):
                rows = api_pair()
                for row in rows:
                    value = row["raw_json"]
                    for key in path[:-1]:
                        value = value[key]
                    value.pop(path[-1])
                snapshot, calls = prepare(rows)
                self.assertEqual(snapshot.select("actual").count, 2)
                self.assertEqual(snapshot.select("actual").native_fixture_groups, 0)
                self.assertEqual(calls, [])

    def test_textual_native_id_is_not_guessed_into_a_numeric_fixture_id(self):
        rows = [api_observation("legacy-one"), api_observation("legacy-two")]
        for row in rows:
            row["external_id"] = "fixture-1001"
            row["raw_json"]["fixture"]["id"] = "fixture-1001"
        snapshot, calls = prepare(rows)
        self.assertEqual(snapshot.select("actual").count, 2)
        self.assertEqual(snapshot.select("actual").native_fixture_groups, 0)
        self.assertEqual(calls, [])

    def test_c1_explicit_real_pk_can_resolve_without_native_league_id_proof(self):
        # Document the existing C1 boundary. RESOLVED can mean PK evidence only;
        # neither this alias nor C1 promises a native-ID guarantee when absent.
        row = api_observation()
        row.pop("competition_id")
        row["competition_key"] = "laliga"
        records = [catalogue_record(source="TheSportsDB", external_id="4335")]
        batch = prepare_context({"actual": [row]}, lambda keys: records)
        self.assertEqual(batch.for_row(row).state, "RESOLVED")
        self.assertEqual(batch.for_row(row).canonical_key, "laliga")
        self.assertNotIn("UNKNOWN_UNVERIFIED_ID", batch.for_row(row).issues)


if __name__ == "__main__":
    unittest.main(verbosity=2)
