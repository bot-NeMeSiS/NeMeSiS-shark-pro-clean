"""C1 reviewed-reference contracts; synthetic data, no App, network or live DB.

The public ID/key pair below reproduces the retained two-PK readonly evidence.
It is not a fresh provider response and supplies no team bridge or Odds season.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json

import pytest

from engines.canonical_competition_context import prepare_context
from engines.competition_reference_registry import CURATED_COMPETITION_REFERENCES
from engines.fixture_snapshot_read_model import prepare_fixture_snapshot
from engines.v935_launch_trust_engine import match_kickoff_madrid


def observation(**changes):
    row = {
        "id": "af-1570431", "external_id": "1570431", "source": "api_football_live",
        "competition_id": "140", "competition_key": "la-liga-spain",
        "competition_name": "La Liga", "country": "Spain", "sport_key": "soccer",
        "season": "2026", "kickoff_iso": "2026-10-26T21:00:00+01:00", "status": "NS",
        "home_team": "Sevilla", "away_team": "Osasuna",
        "home_team_id": "536", "away_team_id": "727",
        "last_synced_at": "2026-10-26T14:15:14Z", "quote": {"price": 2.0},
        "raw_json": {
            "fixture": {"id": 1570431, "date": "2026-10-26T21:00:00+01:00"},
            "league": {"id": 140, "name": "La Liga", "country": "Spain", "season": 2026},
            "teams": {"home": {"id": 536, "name": "Sevilla"},
                      "away": {"id": 727, "name": "Osasuna"}},
        },
    }
    row.update(changes)
    return row


def catalogue(**changes):
    result = {"key": "laliga", "name": "LaLiga", "country": "Spain",
              "source": "population_engine", "external_id": "4335"}
    result.update(changes)
    return result


def prepare(rows=None, records=None, **kwargs):
    rows = [observation()] if rows is None else rows
    records = [catalogue()] if records is None else records
    calls = []
    def read(keys):
        calls.append(keys)
        return [dict(record) for record in records if record["key"] in keys]
    return prepare_context({"actual": rows}, read, **kwargs), calls


def test_reviewed_reference_is_immutable_versioned_and_cites_independent_sources():
    reference, = CURATED_COMPETITION_REFERENCES
    assert (reference.provider, reference.native_id, reference.canonical_key) == ("api-football", "140", "laliga")
    assert reference.observed_keys == ("la-liga-spain",)
    assert (reference.sport, reference.country, reference.gender) == ("Soccer", "Spain", "Male")
    assert reference.counterpart_ids == (("sportsdb", "4335"),)
    assert reference.season_policy == "API_START_YEAR_REQUIRED"
    assert reference.version == "2026-10-26.laliga.1"
    assert "NOT_DIRECT_CROSS_ID" in reference.inference
    assert len(reference.sources) == 3
    assert all(url.startswith("https://") for url, fact in reference.sources)
    with pytest.raises(FrozenInstanceError):
        reference.native_id = "141"


@pytest.mark.parametrize("source", ["api_football_live", "API_FOOTBALL_PRIMARY", "API_SPORTS", "API-Football"])
def test_historical_api140_observed_key_resolves_via_both_exact_pks(source):
    row = observation(source=source)
    before = deepcopy(row)
    batch, calls = prepare([row])
    context = batch.at("actual", 0)
    assert context.state == "RESOLVED"
    assert context.canonical_key == "laliga"
    assert context.country_key == "espana"
    assert context.required_keys == ("la-liga-spain", "laliga")
    assert context.issues == ()
    assert calls == [("la-liga-spain", "laliga")]
    assert row == before
    assert batch.for_row(dict(row)).state == "UNKNOWN_NOT_PREPARED"


@pytest.mark.parametrize("source,native", [("API_FOOTBALL", "140"), ("TheSportsDB", "4335"), ("population_engine", "4335")])
def test_catalogue_canonical_native_identity_is_checked(source, native):
    batch, _ = prepare(records=[catalogue(source=source, external_id=native)])
    assert batch.at("actual", 0).state == "RESOLVED"


@pytest.mark.parametrize("changes,issue", [
    ({"country": "Portugal"}, "CONFLICT_COUNTRY"),
    ({"sport_key": "basketball"}, "CONFLICT_REFERENCE_SPORT"),
    ({"sport_name": "Tennis"}, "CONFLICT_REFERENCE_SPORT"),
    ({"gender": "Female"}, "CONFLICT_REFERENCE_GENDER"),
    ({"competition_name": "La Liga Women"}, "CONFLICT_REFERENCE_GENDER"),
    ({"category": "reserves"}, "CONFLICT_REFERENCE_CATEGORY"),
    ({"age_group": "U21"}, "CONFLICT_REFERENCE_CATEGORY"),
    ({"league_id": "141"}, "CONFLICT_LEAGUE_ID"),
    ({"provider": "TheSportsDB"}, "CONFLICT_NAMESPACE"),
])
def test_observation_scope_collisions_cannot_be_resolved(changes, issue):
    row = observation(**changes)
    batch, _ = prepare([row])
    context = batch.at("actual", 0)
    assert context.state == "CONFLICT"
    assert context.canonical_key == ""
    assert issue in context.issues


@pytest.mark.parametrize("changes", [
    {"competition_key": "la-liga-spain-women"}, {"competition_key": "La-Liga-Spain"},
    {"competition_key": "la-liga"}, {"competition_id": "141"},
    {"source": "NotAPI_FOOTBALL"}, {"source": "TheSportsDB"}, {"source": ""},
])
def test_no_name_fuzzy_key_or_provider_id_only_blessing(changes):
    batch, _ = prepare([observation(**changes)])
    assert batch.at("actual", 0).state != "RESOLVED"
    assert batch.at("actual", 0).canonical_key == ""


@pytest.mark.parametrize("changes,issue", [
    ({"sport_key": ""}, "UNKNOWN_REFERENCE_SCOPE_SPORT"),
    ({"country": ""}, "UNKNOWN_REFERENCE_SCOPE_COUNTRY"),
    ({"season": ""}, "UNKNOWN_REFERENCE_SCOPE_SEASON"),
    ({"season": "2026-2027"}, "UNKNOWN_REFERENCE_SCOPE_SEASON"),
    ({"season": True}, "UNKNOWN_REFERENCE_SCOPE_SEASON"),
    ({"gender": "Mixed"}, "UNKNOWN_REFERENCE_SCOPE_GENDER"),
])
def test_new_relation_requires_scope_and_never_completes_missing_seasons(changes, issue):
    batch, _ = prepare([observation(**changes)])
    assert batch.at("actual", 0).state != "RESOLVED"
    assert issue in batch.at("actual", 0).issues


@pytest.mark.parametrize("field,value,issue", [
    ("id", 141, "CONFLICT_REFERENCE_PAYLOAD_ID"),
    ("country", "France", "CONFLICT_COUNTRY"),
    ("season", 2025, "CONFLICT_REFERENCE_SEASON"),
    ("season", "2026-2027", "CONFLICT_REFERENCE_SEASON"),
    ("name", "Primera Division Femenina", "CONFLICT_REFERENCE_GENDER"),
])
def test_raw_league_contradictions_are_preserved(field, value, issue):
    row = observation()
    row["raw_json"]["league"][field] = value
    before = deepcopy(row)
    batch, _ = prepare([row])
    assert batch.at("actual", 0).state == "CONFLICT"
    assert issue in batch.at("actual", 0).issues
    assert row == before


def test_raw_payload_json_text_is_not_replaced():
    row = observation()
    row["raw_json"] = json.dumps(row["raw_json"])
    original = row["raw_json"]
    batch, _ = prepare([row])
    assert batch.at("actual", 0).state == "RESOLVED"
    assert row["raw_json"] is original


def test_malformed_raw_season_is_not_silently_ignored():
    row = observation()
    row["raw_json"]["league"]["season"] = True
    batch, _ = prepare([row])
    assert batch.at("actual", 0).state == "UNKNOWN"
    assert "UNKNOWN_REFERENCE_PAYLOAD_SEASON" in batch.at("actual", 0).issues


@pytest.mark.parametrize("path,value", [
    (("sport_key",), "basketball"), (("gender",), "Female"), (("category",), "U21"),
    (("raw_json", "league", "id"), 141), (("raw_json", "league", "name"), "La Liga Women"),
    (("raw_json", "league", "country"), "France"), (("raw_json", "league", "season"), 2025),
])
def test_every_new_scope_input_is_already_guarded_after_snapshot_preparation(path, value):
    row = observation()
    snapshot = prepare_fixture_snapshot({"actual": [row]}, lambda keys: [catalogue()],
                                        kickoff_for=match_kickoff_madrid)
    assert snapshot.context_for(row).state == "RESOLVED"
    target = row
    for field in path[:-1]:
        target = target[field]
    target[path[-1]] = value
    assert snapshot.context_for(row).state == "UNKNOWN_IDENTITY_CHANGED"
    assert snapshot.select("actual").count == 1
    assert snapshot.select("actual").confirmed_count == 0


@pytest.mark.parametrize("changes,issue", [
    ({"external_id": "999", "source": "API_FOOTBALL"}, "CONFLICT_REFERENCE_NATIVE_ID"),
    ({"external_id": "999", "source": "TheSportsDB"}, "CONFLICT_REFERENCE_NATIVE_ID"),
    ({"country": "Portugal"}, "CONFLICT_COUNTRY"),
    ({"sport": "Basketball"}, "CONFLICT_REFERENCE_SPORT"),
    ({"gender": "Female"}, "CONFLICT_REFERENCE_GENDER"),
    ({"name": "La Liga Women"}, "CONFLICT_REFERENCE_GENDER"),
])
def test_conflicting_canonical_catalogue_reference_remains_conflict(changes, issue):
    batch, _ = prepare(records=[catalogue(**changes)])
    assert batch.at("actual", 0).state == "CONFLICT"
    assert issue in batch.at("actual", 0).issues


@pytest.mark.parametrize("changes,state,issue", [
    ({"source": "API_FOOTBALL", "external_id": "140"}, "RESOLVED", None),
    ({"source": "API_FOOTBALL", "external_id": "141"}, "CONFLICT", "CONFLICT_REFERENCE_NATIVE_ID"),
    ({"source": "TheSportsDB", "external_id": "4335"}, "CONFLICT", "CONFLICT_ALIAS_REFERENCE_NAMESPACE"),
    ({"source": "unreviewed", "external_id": "140"}, "UNKNOWN", "UNKNOWN_ALIAS_REFERENCE"),
    ({"source": "API_FOOTBALL", "external_id": "140", "country": "France"}, "CONFLICT", "CONFLICT_COUNTRY"),
])
def test_existing_observed_pk_is_verified_and_never_hidden(changes, state, issue):
    alternative = catalogue(key="la-liga-spain", **changes)
    batch, calls = prepare(records=[catalogue(), alternative])
    assert batch.at("actual", 0).state == state
    if issue:
        assert issue in batch.at("actual", 0).issues
    assert calls == [("la-liga-spain", "laliga")]


def test_duplicate_existing_observed_pk_is_ambiguous():
    alternative = catalogue(key="la-liga-spain", source="API_FOOTBALL", external_id="140")
    batch, _ = prepare(records=[catalogue(), alternative, alternative])
    assert batch.at("actual", 0).state == "AMBIGUOUS"


def test_no_canonical_catalogue_identity_is_manufactured_from_static_mapping():
    for records in ([], [catalogue(source="", external_id="")]):
        batch, _ = prepare(records=records)
        assert batch.at("actual", 0).state != "RESOLVED"


def test_alias_and_canonical_reads_form_one_indivisible_bounded_group():
    batch, calls = prepare(max_keys=1)
    assert calls == []
    assert batch.queried_keys == ()
    assert batch.at("actual", 0).state == "UNKNOWN_NOT_COVERED"
    assert batch.not_covered_sets == (("la-liga-spain", "laliga"),)


def test_matching_explicit_api_registry_declaration_remains_resolved():
    registry = ({"key": "laliga", "country": "Spain", "api_football_id": "140", "sportsdb_id": "4335"},)
    batch, calls = prepare(registry=registry)
    assert batch.at("actual", 0).state == "RESOLVED"
    assert calls == [("la-liga-spain", "laliga")]


@pytest.mark.parametrize("also_matching", [False, True])
def test_explicit_registry_collision_cannot_be_overruled_by_curated_reference(also_matching):
    registry = [{"key": "other-catalogue-key", "country": "Spain", "api_football_id": "140"}]
    if also_matching:
        registry.append({"key": "laliga", "country": "Spain", "api_football_id": "140"})
    batch, calls = prepare(registry=registry, records=[catalogue(), catalogue(key="other-catalogue-key")])
    context = batch.at("actual", 0)
    assert context.state == "CONFLICT"
    assert "CONFLICT_CURATED_MAPPING" in context.issues
    assert context.canonical_key == ""
    assert context.required_keys == ("la-liga-spain", "laliga", "other-catalogue-key")
    assert calls == [("la-liga-spain", "laliga", "other-catalogue-key")]


def test_registry_collision_does_not_take_a_partial_read_when_budget_is_two():
    registry = ({"key": "other-catalogue-key", "country": "Spain", "api_football_id": "140"},)
    batch, calls = prepare(registry=registry, max_keys=2)
    assert calls == []
    assert batch.at("actual", 0).state == "UNKNOWN_NOT_COVERED"
    assert "CONFLICT_CURATED_MAPPING" in batch.at("actual", 0).issues


def test_unavailable_reference_read_is_not_a_verified_absence():
    def unavailable(keys):
        raise RuntimeError("isolated read failed")
    batch = prepare_context({"actual": [observation()]}, unavailable)
    assert batch.at("actual", 0).state == "UNKNOWN_READ_UNAVAILABLE"


def test_historical_two_pk_case_keeps_odds_season_team_identity_clocks_and_favorites_intact():
    api = observation()
    odds = observation(id="odds-19e6172e4b4ebb188d", external_id="85e464708d03287f24590e1478aeca31",
                       source="The Odds API", competition_id="soccer_spain_la_liga",
                       competition_key="laliga", country="España", season="", away_team="CA Osasuna",
                       home_team_id="", away_team_id="", raw_json={}, last_synced_at="",
                       updated_at="2026-10-11T19:15:33+02:00")
    rows = [api, odds]
    originals = deepcopy(rows)
    favorites = {api["id"], odds["id"]}
    calls = []
    def reader(keys):
        calls.append(keys)
        return [catalogue()]
    snapshot = prepare_fixture_snapshot({"actual": rows}, reader, kickoff_for=match_kickoff_madrid)
    assert [snapshot.context_for(row).state for row in rows] == ["RESOLVED", "RESOLVED"]
    assert snapshot.select("actual").count == 2
    assert snapshot.select("actual").groups == ((api,), (odds,))
    assert set(snapshot.select("actual").fixture_ids) == favorites
    assert rows == originals
    assert odds["season"] == ""
    assert odds["away_team_id"] == ""
    assert calls == [("la-liga-spain", "laliga")]
