"""Pure regressions for shared cross-provider presentation identity."""
from copy import deepcopy
from datetime import datetime, timezone
from itertools import permutations
import json

import pytest

from engines import fixture_identity_read_model as identity


def fixture(identifier, source="TheSportsDB API", home="Granada", away="Real Valladolid", **extra):
    return {
        "id": identifier, "source": source, "home_team": home, "away_team": away,
        "competition_name": "Segunda División", "country": "Spain",
        "kickoff_iso": "2026-10-23T20:30:00+02:00", "match_date": "2026-10-23",
        "kickoff_time": "20:30", "status": "NS", **extra,
    }


def kickoff(row):
    text = row.get("kickoff_iso") or f"{row['match_date']}T{row['kickoff_time']}"
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def prefer(row):
    return (bool(row.get("has_pick")), row["source"] == "API_FOOTBALL", row["id"])


def unique(rows, **callbacks):
    return identity.unique_provider_fixtures(
        rows, kickoff_for=callbacks.get("kickoff_for", kickoff),
        rank_for=callbacks.get("rank_for", prefer),
    )


@pytest.mark.parametrize("home1,away1,home2,away2", [
    ("Granada", "Real Valladolid", "Granada CF", "Valladolid"),
    ("Deportivo Alavés", "Málaga", "Alaves", "Malaga"),
    ("Valencia C.F.", "Sevilla F.C.", "Valencia", "Sevilla"),
    ("FC Porto", "Braga Football Club", "Porto", "Braga"),
    ("Riverbank Football Club", "FC Meadowtown", "Riverbank", "Meadowtown"),
    ("Real Aurora", "Deportivo Horizonte", "Aurora CF", "Horizonte FC"),
    ("C.D. Costa Verde", "Club de Fútbol Norte", "Costa Verde", "Norte"),
    ("Atlético Madrid", "Athletic Bilbao", "Atlético de Madrid", "Athletic Club"),
    ("Tottenham Hotspur", "Coventry City", "Tottenham", "Coventry"),
])
def test_general_club_forms_collapse_complete_fixtures(home1, away1, home2, away2):
    alternate = fixture("sportsdb-1", home=home1, away=away1)
    primary = fixture("af-2", "API_FOOTBALL", home2, away2)
    before = deepcopy([alternate, primary])
    result = unique([alternate, primary])
    assert result == [primary]
    assert result[0] is primary
    assert [alternate, primary] == before


def test_selected_row_keeps_its_prices_scores_and_links_without_blending():
    alternate = fixture("s", has_pick=True, odds=1.9, home_score=1, away_score=0,
                        team_url="/team/sportsdb:team:133721", nested={"source": "s"})
    primary = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid", odds=2.1,
                      home_score=2, away_score=0, team_url="/team/api_football:team:715")
    original = deepcopy([alternate, primary])
    assert unique([alternate, primary])[0] is alternate
    assert [alternate, primary] == original


def test_output_keeps_input_order_of_winners_and_ties_prefer_first():
    a = fixture("a")
    unrelated = fixture("other", home="Different Club", away="Another Side")
    b = fixture("b", "API_FOOTBALL", "Granada CF", "Valladolid")
    assert unique([a, unrelated, b]) == [unrelated, b]
    assert unique([a, unrelated, b], rank_for=lambda _row: 0) == [a, unrelated]


@pytest.mark.parametrize("extra", [
    {"country": "Portugal"}, {"competition_name": "Copa del Rey"},
    {"season": "2027"}, {"sport": "Rugby"},
    {"kickoff_iso": "2026-10-24T20:30:00+02:00"},
    {"kickoff_iso": "2026-10-23T20:32:00+02:00"},
    {"kickoff_iso": "2026-10-23T20:30:01+02:00"},
    {"home_team": "Valladolid", "away_team": "Granada CF"},
])
def test_incompatible_fixture_context_stays_separate(extra):
    first = fixture("s", season="2026", sport="Soccer")
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid",
                     season="2026", sport="Football")
    second.update(extra)
    assert unique([first, second]) == [first, second]


@pytest.mark.parametrize("qualified", [
    "Granada B", "Granada II", "Granada III", "Granada Reserves", "Granada U19",
    "Granada U21", "Granada Under-23", "Granada Sub 20", "Granada Women",
    "Granada W", "Granada Femenino", "Granada Academy", "Granada Juvenil",
])
def test_category_names_are_never_folded_into_the_unqualified_team(qualified):
    first = fixture("s")
    second = fixture("a", "API_FOOTBALL", qualified, "Valladolid")
    assert unique([first, second]) == [first, second]


def test_equivalent_explicit_categories_and_club_designators_can_match():
    first = fixture("s", home="Granada C.F. B", away="Valladolid Women U19")
    second = fixture("a", "API_FOOTBALL", "Granada B", "Valladolid W Under-19")
    assert unique([first, second]) == [second]


@pytest.mark.parametrize("field,value", [
    ("home_gender", "female"), ("away_team_category", "U19"),
    ("gender", "female"), ("home_category", "reserves"),
])
def test_explicit_category_metadata_prevents_name_only_merge(field, value):
    first = fixture("s")
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid", **{field: value})
    assert unique([first, second]) == [first, second]


@pytest.mark.parametrize("missing", ["source", "country", "competition_name", "home_team", "away_team", "id"])
def test_incomplete_identity_is_preserved(missing):
    first = fixture("s")
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid")
    second.pop(missing)
    assert unique([first, second]) == [first, second]


@pytest.mark.parametrize("home", ["", "Equipo local", "TBD", "Football Club", "CF", "Real"])
def test_placeholder_or_designator_only_team_cannot_be_merged(home):
    first = fixture("s", home=home)
    second = fixture("a", "API_FOOTBALL", home, "Valladolid")
    assert unique([first, second]) == [first, second]


def test_date_without_explicit_time_is_not_inferred_by_callback():
    first = fixture("s")
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid")
    second.pop("kickoff_iso")
    second.pop("kickoff_time")
    assert unique([first, second], kickoff_for=lambda _row: kickoff(first)) == [first, second]


def test_invalid_kickoff_callback_and_non_mapping_rows_are_preserved():
    first = fixture("s")
    malformed = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid",
                        kickoff_iso="2026-99-23T20:30:00+02:00")
    assert unique([None, first, malformed, {}]) == [None, first, malformed, {}]


def test_madrid_naive_and_utc_represent_the_same_instant():
    first = fixture("s", kickoff_iso="2026-10-23T20:30:00")
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid",
                     kickoff_iso="2026-10-23T18:30:00Z")
    assert unique([first, second]) == [second]


def test_country_season_and_football_labels_use_existing_normalization():
    first = fixture("s", competition_name="Spanish La Liga 2", season="2026-2027", sport="Soccer")
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid",
                     country="España", season="2026", sport="Football")
    assert unique([first, second]) == [second]


def test_distinct_fixture_ids_from_same_provider_are_never_collapsed():
    first = fixture("af-1", "API_FOOTBALL")
    second = fixture("af-2", "API-Sports", "Granada CF", "Valladolid")
    assert unique([first, second]) == [first, second]


def test_two_same_provider_ids_make_a_cross_provider_component_ambiguous():
    rows = [fixture("af-1", "API_FOOTBALL"), fixture("af-2", "API_FOOTBALL"), fixture("sportsdb-3")]
    for order in permutations(rows):
        assert unique(order) == list(order)


def test_short_name_bridge_does_not_merge_two_distinct_longer_names():
    rows = [fixture("a", "API_FOOTBALL", "Real Aurora", "Rival"),
            fixture("s", "TheSportsDB", "Aurora", "Rival"),
            fixture("o", "The Odds API", "Deportivo Aurora", "Rival")]
    for order in permutations(rows):
        assert unique(order) == list(order)


def test_unknown_season_cannot_bridge_conflicting_known_seasons():
    rows = [fixture("a", "API_FOOTBALL", season="2026"),
            fixture("s", "TheSportsDB"), fixture("o", "The Odds API", season="2027")]
    assert unique(rows) == rows


def test_shared_provider_team_id_conflict_overrules_names():
    first = fixture("s", home_provider_team_ids={"API_FOOTBALL": "715"})
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid", home_team_id="999")
    assert unique([first, second]) == [first, second]


def test_internally_contradictory_team_ids_leave_the_row_unresolved():
    first = fixture("s", home_team_id="133721", home_provider_team_ids={"sportsdb": "99"})
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid")
    assert unique([first, second]) == [first, second]


def test_provider_namespaced_canonical_ids_do_not_conflict_across_providers():
    first = fixture("s", home_canonical_team_id="sportsdb:team:133721")
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid",
                     home_canonical_team_id="api_football:team:715")
    assert unique([first, second]) == [second]


def test_explicit_canonical_team_pair_can_match_without_guessing_aliases():
    first = fixture("s", home="Known Full Name", away="Other Known Name",
                    home_canonical_team_id="canonical-1", away_canonical_team_id="canonical-2")
    second = fixture("a", "API_FOOTBALL", "Established Alias", "Second Alias",
                     home_canonical_team_id="canonical-1", away_canonical_team_id="canonical-2")
    assert unique([first, second]) == [second]


def test_explicit_aliases_are_used_but_do_not_remove_category_markers():
    first = fixture("s", home="Established Name", home_team_aliases=["Granada"])
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid")
    assert unique([first, second]) == [second]
    first["home_team"] = "Established Name B"
    assert unique([first, second]) == [first, second]


@pytest.mark.parametrize("score_fields", [{"home_score": 0, "away_score": 0}, {"score": "0-0"}])
def test_conflicting_confirmed_final_results_remain_visible(score_fields):
    first = fixture("s", status="FT", **score_fields)
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid",
                     status="Match Finished", home_score=1, away_score=0)
    assert unique([first, second]) == [first, second]


def test_matching_confirmed_zero_scores_can_collapse():
    first = fixture("s", status="FT", home_score=0, away_score=0)
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid",
                     status="FINALIZADO", home_score="0", away_score="0")
    assert unique([first, second]) == [second]


def test_read_model_only_compares_candidate_pairs_not_the_whole_snapshot(monkeypatch):
    calls = []
    original = identity._compatible

    def counted(left, right):
        calls.append((left.identifier, right.identifier))
        return original(left, right)

    monkeypatch.setattr(identity, "_compatible", counted)
    rows = []
    for number in range(1000):
        rows.extend([fixture(f"s-{number}", home=f"Riverbank {number}", away=f"Meadowtown {number}"),
                     fixture(f"a-{number}", "API_FOOTBALL", f"FC Riverbank {number}", f"Meadowtown {number} CF")])
    assert len(unique(rows)) == 1000
    assert len(calls) == 1000


def test_excessive_name_collisions_stay_unresolved_without_quadratic_work(monkeypatch):
    def no_comparison(*_args):
        raise AssertionError("Overloaded identity must remain unresolved")

    monkeypatch.setattr(identity, "_compatible", no_comparison)
    rows = [fixture(f"s-{number}") for number in range(2000)]
    assert unique(rows) == rows


def test_generator_and_empty_inputs_are_supported():
    first = fixture("s")
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid")
    assert unique(iter([first, second])) == [second]
    assert unique(None) == []


def provider_payload(row, mapped_id=None):
    """Small original provider payloads, with no external data or API access."""
    if identity.provider_family(row["source"]) == "sportsdb":
        return {
            "idEvent": row["external_id"], "idAPIfootball": mapped_id,
            "idLeague": row["competition_id"], "strLeague": row["competition_name"],
            "strCountry": row["country"], "strSeason": row.get("season"), "strSport": "Soccer",
            "idHomeTeam": row["home_team_id"], "idAwayTeam": row["away_team_id"],
            "strHomeTeam": row["home_team"], "strAwayTeam": row["away_team"],
            "strTimestamp": kickoff(row).astimezone(timezone.utc).replace(tzinfo=None).isoformat(),
        }
    return {
        "fixture": {"id": int(row["external_id"]), "date": row["kickoff_iso"]},
        "league": {"id": int(row["competition_id"]), "name": row["competition_name"],
                   "country": row["country"], "season": row.get("season")},
        "teams": {"home": {"id": int(row["home_team_id"]), "name": row["home_team"]},
                  "away": {"id": int(row["away_team_id"]), "name": row["away_team"]}},
    }


def mapped_pair(home="Ipswich Town", alias="Ipswich", away="Nottingham Forest", away_alias=None):
    first = fixture("sportsdb-1", home=home, away=away, external_id="1001",
                    competition_id="9991", home_team_id="133622", away_team_id="133720",
                    season="2026-2027", sport_key="soccer")
    second = fixture("af-1002", "API_FOOTBALL", alias, away_alias or away,
                     external_id="1002", competition_id="9992", home_team_id="57", away_team_id="65",
                     season="2026", sport_key="soccer")
    first["raw_json"] = provider_payload(first, "1002")
    second["raw_json"] = provider_payload(second)
    return first, second


@pytest.mark.parametrize("home,alias,away,away_alias", [
    ("Ipswich Town", "Ipswich", "Nottingham Forest", "Nottingham Forest"),
    ("Stuttgart", "VfB Stuttgart", "Borussia Mönchengladbach", "Borussia Mönchengladbach"),
    ("Brest", "Stade Brestois 29", "Nice", "Nice"),
    ("Vitória de Guimarães", "Vitória SC", "Marítimo", "Maritimo"),
    ("Unlisted Town", "Established Alias", "Some Opponent", "Some Opponent"),
])
def test_verified_provider_event_mapping_can_resolve_non_structural_aliases(home, alias, away, away_alias):
    first, second = mapped_pair(home, alias, away, away_alias)
    original = deepcopy([first, second])
    assert unique([first, second]) == [second]
    assert unique([second, first]) == [second]
    assert [first, second] == original
    first["raw_json"] = json.dumps(first["raw_json"])
    second["raw_json"] = json.dumps(second["raw_json"])
    assert unique([first, second])[0] is second


@pytest.mark.parametrize("field,bad", [
    ("idEvent", "9999"), ("idHomeTeam", "9999"), ("idAwayTeam", "9999"),
    ("idLeague", "9999"), ("strHomeTeam", "Another Club"), ("strAwayTeam", "Another Club"),
    ("strTimestamp", "2026-10-23T18:32:00"), ("strSeason", "2027"), ("strSport", "Basketball"),
    ("strCountry", "Portugal"), ("strLeague", "Copa del Rey"),
])
def test_provider_mapping_rejects_borrowed_or_contradictory_source_payload(field, bad):
    first, second = mapped_pair()
    first["raw_json"][field] = bad
    assert unique([first, second]) == [first, second]


@pytest.mark.parametrize("path", [("fixture", "id"), ("league", "id"),
                                  ("teams", "home", "id"), ("teams", "away", "id")])
def test_provider_mapping_requires_matching_destination_payload(path):
    first, second = mapped_pair()
    target = second["raw_json"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = 9999
    assert unique([first, second]) == [first, second]


@pytest.mark.parametrize("side,missing", [
    (0, "external_id"), (0, "home_team_id"), (0, "away_team_id"), (0, "competition_id"),
    (1, "external_id"), (1, "home_team_id"), (1, "away_team_id"), (1, "competition_id"),
    (0, "raw_json"), (1, "raw_json"),
])
def test_provider_mapping_does_not_fill_missing_provenance(side, missing):
    rows = list(mapped_pair())
    rows[side].pop(missing)
    assert unique(rows) == rows


def test_provider_mapping_conflict_blocks_structural_name_match_even_without_target_payload():
    first, second = mapped_pair("Granada", "Granada CF", "Real Valladolid", "Valladolid")
    first["raw_json"]["idAPIfootball"] = "9999"
    second.pop("raw_json")
    assert unique([first, second]) == [first, second]


@pytest.mark.parametrize("extra", [
    {"country": "Portugal"}, {"competition_name": "Copa del Rey"}, {"season": "2027"},
    {"sport_key": "basketball"}, {"kickoff_iso": "2026-10-23T20:32:00+02:00"},
    {"home_team": "Ipswich B"}, {"away_team": "Nottingham Forest U19"},
    {"home_team": "Nottingham Forest", "away_team": "Ipswich"},
])
def test_provider_mapping_never_overrides_context_category_or_side_conflicts(extra):
    first, second = mapped_pair()
    second.update(extra)
    second["raw_json"] = provider_payload(second)
    assert unique([first, second]) == [first, second]


def test_provider_mapping_never_overrides_explicit_team_id_conflicts():
    first, second = mapped_pair()
    first["home_provider_team_ids"] = {"api_football": "9999"}
    assert unique([first, second]) == [first, second]


def test_provider_mapping_never_hides_conflicting_confirmed_final_scores():
    first, second = mapped_pair()
    first.update(status="FT", home_score=0, away_score=0)
    second.update(status="FT", home_score=1, away_score=0)
    assert unique([first, second]) == [first, second]


def test_provider_mapping_requires_one_independently_known_ordered_team():
    first, second = mapped_pair("Long Name", "Unrelated Alias", "Another Name", "Other Alias")
    assert unique([first, second]) == [first, second]


def test_without_mapping_non_structural_name_parts_are_not_removed():
    for home, alias in [("Ipswich Town", "Ipswich"), ("Unlisted United", "Unlisted"),
                        ("Aurora City", "Aurora"), ("Brest", "Stade Brestois 29")]:
        first, second = mapped_pair(home, alias)
        first["raw_json"].pop("idAPIfootball")
        assert unique([first, second]) == [first, second]


def test_sport_key_is_a_strong_sport_conflict_without_other_sport_fields():
    first = fixture("s", sport_key="soccer")
    second = fixture("a", "API_FOOTBALL", "Granada CF", "Valladolid", sport_key="basketball")
    assert unique([first, second]) == [first, second]


def test_provider_mapping_does_not_discard_personalized_alternate_row():
    first, second = mapped_pair()
    first["has_pick"] = True
    assert unique([first, second])[0] is first


@pytest.mark.parametrize("country,display,original,sportsdb_id,api_id", [
    ("Germany", "Bundesliga", "German Bundesliga", "4331", "78"),
    ("France", "Ligue 1", "French Ligue 1", "4334", "61"),
    ("Portugal", "Primeira Liga", "Portuguese Primeira Liga", "4344", "94"),
])
def test_existing_registered_league_ids_resolve_provider_competition_labels(country, display, original, sportsdb_id, api_id):
    first, second = mapped_pair()
    first.update(country=country, competition_name=display, competition_id=sportsdb_id)
    second.update(country=country, competition_name=display, competition_id=api_id)
    first["raw_json"] = provider_payload(first, "1002")
    first["raw_json"]["strLeague"] = original
    second["raw_json"] = provider_payload(second)
    assert unique([first, second]) == [second]


def test_provider_groups_preserve_original_rows_and_include_unknown_singletons():
    first, second = mapped_pair()
    other = fixture("other", home="Different", away="Opponent")
    rows = [first, None, other, second, {}]
    original = deepcopy(rows)
    groups = identity.provider_fixture_groups(rows, kickoff_for=kickoff)
    assert groups == [[first, second], [None], [other], [{}]]
    assert groups[0][0] is first and groups[0][1] is second
    assert rows == original


def test_ambiguous_provider_mapping_keeps_every_row_in_its_own_group():
    first, second = mapped_pair()
    another = deepcopy(first)
    another.update(id="sportsdb-3", external_id="1003")
    another["raw_json"] = provider_payload(another, "1002")
    for rows in permutations([first, second, another]):
        assert identity.provider_fixture_groups(rows, kickoff_for=kickoff) == [[row] for row in rows]
        assert unique(rows) == list(rows)


def test_provider_groups_do_not_join_a_short_name_bridge():
    rows = [fixture("a", "API_FOOTBALL", "Real Aurora", "Rival"),
            fixture("s", "TheSportsDB", "Aurora", "Rival"),
            fixture("o", "The Odds API", "Deportivo Aurora", "Rival")]
    assert identity.provider_fixture_groups(rows, kickoff_for=kickoff) == [[row] for row in rows]


def test_conflicting_same_provider_external_fixture_ids_stay_visible():
    first = fixture("same", external_id="1001")
    second = fixture("same", external_id="1002")
    assert unique([first, second]) == [first, second]


def test_provider_groups_accept_empty_inputs_and_generators():
    first, second = mapped_pair()
    assert identity.provider_fixture_groups(iter([first, second]), kickoff_for=kickoff) == [[first, second]]
    assert identity.provider_fixture_groups(None, kickoff_for=kickoff) == []


def test_legacy_external_id_repeating_the_app_id_does_not_block_existing_aliases():
    first = fixture("sportsdb-levante-athletic", home="Levante UD", away="Athletic Club",
                    external_id="sportsdb-levante-athletic")
    second = fixture("af-1570389", "API_FOOTBALL", "Levante UD", "Athletic Bilbao",
                     external_id="af-1570389")
    assert unique([first, second]) == [second]


def test_legacy_external_app_id_is_not_proof_for_a_provider_event_mapping():
    first, second = mapped_pair()
    second["external_id"] = second["id"]
    assert unique([first, second]) == [first, second]


def test_legacy_external_app_id_still_allows_structural_matching_with_raw_payload():
    first, second = mapped_pair("Granada", "Granada CF", "Real Valladolid", "Valladolid")
    second["external_id"] = second["id"]
    assert unique([first, second]) == [second]


def test_numeric_external_id_conflicting_with_the_api_fixture_id_stays_visible():
    first = fixture("sportsdb-1")
    second = fixture("af-1570389", "API_FOOTBALL", "Granada CF", "Valladolid", external_id="9999")
    assert unique([first, second]) == [first, second]
