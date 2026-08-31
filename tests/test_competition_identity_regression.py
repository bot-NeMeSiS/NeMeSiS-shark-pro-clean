from __future__ import annotations

from engines.football_population_engine import PRIORITY_COMPETITIONS
from engines.match_sync_engine import IMPORTANT_COMPETITIONS
from engines.spanish_localization_engine import spanish_competition_name


def _match(
    match_id: str,
    competition_id: str,
    competition_key: str,
    competition_name: str,
    country: str,
) -> dict:
    return {
        "id": match_id,
        "match_id": match_id,
        "match_date": "2026-08-31",
        "kickoff_time": "21:00",
        "kickoff_iso": "2026-08-31T19:00:00Z",
        "competition_id": competition_id,
        "competition_key": competition_key,
        "competition_name": competition_name,
        "league_name": competition_name,
        "country": country,
        "home_team": f"Local {match_id}",
        "away_team": f"Visitante {match_id}",
        "status": "NS",
        "source": "TheSportsDB API",
    }


def test_competition_localization_is_exact_and_does_not_collapse_generic_names():
    assert spanish_competition_name("Spanish La Liga") == "LaLiga EA Sports"
    assert spanish_competition_name("Spanish La Liga 2") == "Segunda División"
    assert spanish_competition_name("LaLiga Hypermotion") == "Segunda División"
    assert spanish_competition_name("Ukrainian Premier League") == "Ukrainian Premier League"
    assert spanish_competition_name("Germany Women Bundesliga") == "Germany Women Bundesliga"
    assert spanish_competition_name("Copa de la Liga Profesional") == "Copa de la Liga Profesional"


def test_sportsdb_registry_keeps_primera_segunda_and_ligue_2_ids_distinct():
    population = {item["key"]: item["sportsdb_id"] for item in PRIORITY_COMPETITIONS}
    sync = {item["key"]: item["sportsdb_id"] for item in IMPORTANT_COMPETITIONS}

    assert population["laliga"] == "4335"
    assert population["segunda-division"] == "4400"
    assert sync["laliga"] == "4335"
    assert sync["segunda-division"] == "4400"
    assert sync["ligue-2"] == "4401"
    assert len({sync["laliga"], sync["segunda-division"], sync["ligue-2"]}) == 3


def test_cross_surface_contract_keeps_primera_and_segunda_distinct(app_module):
    primera = _match("primera", "4335", "spanish-la-liga", "Spanish La Liga", "Spain")
    segunda = _match("segunda", "4400", "spanish-la-liga-2", "Spanish La Liga 2", "Spain")

    primera_client = app_module.client_match_display_context(primera)
    segunda_client = app_module.client_match_display_context(segunda)
    primera_surface = app_module.canonical_match_surface_contract(primera_client)
    segunda_surface = app_module.canonical_match_surface_contract(segunda_client)

    assert primera_client["client_competition"] == "LaLiga EA Sports"
    assert segunda_client["client_competition"] == "Segunda División"
    assert primera_client["client_competition_id"] != segunda_client["client_competition_id"]
    assert primera_surface["canonical_competition_id"] == primera_client["client_competition_id"]
    assert segunda_surface["canonical_competition_id"] == segunda_client["client_competition_id"]
    assert primera_surface["competition_identity_contract"] == "CROSS-SURFACE-COMPETITION-IDENTITY-V1"


def test_all_calendar_groupers_use_canonical_competition_identity(app_module):
    matches = [
        _match("primera", "4335", "spanish-la-liga", "Spanish La Liga", "Spain"),
        _match("segunda", "4400", "spanish-la-liga-2", "Spanish La Liga 2", "Spain"),
    ]

    home_groups = app_module.group_matches_by_league(matches)
    legacy_calendar_groups = app_module.grouped_match_calendar(matches)[0]["leagues"]
    prepared = [app_module.client_match_display_context(item) for item in matches]
    for item in prepared:
        item["calendar_competition"] = item["client_competition"]
        item["calendar_competition_id"] = item["client_competition_id"]
    product_calendar_groups = app_module._calendar_group(prepared)[0]["leagues"]

    for groups in (home_groups, legacy_calendar_groups, product_calendar_groups):
        assert len(groups) == 2
        assert {group["name"] for group in groups} == {"LaLiga EA Sports", "Segunda División"}
        assert len({group["competition_id"] for group in groups}) == 2
        assert {group["identity_contract"] for group in groups} == {"CROSS-SURFACE-COMPETITION-IDENTITY-V1"}


def test_same_generic_display_name_remains_country_scoped(app_module):
    england = _match("england", "", "", "Premier League", "England")
    ukraine = _match("ukraine", "", "", "Premier League", "Ukraine")

    groups = app_module.group_matches_by_league([england, ukraine])

    assert len(groups) == 2
    assert {group["country"] for group in groups} == {"Inglaterra", "Ucrania"}
    assert len({group["competition_id"] for group in groups}) == 2


def test_competition_center_lookup_and_match_query_accept_provider_id(app_module, monkeypatch):
    observed = []

    def fake_one(query, params=()):
        observed.append((query, params))
        if "FROM competitions" in query:
            return None
        return {
            "key": "spanish-la-liga-2",
            "name": "Spanish La Liga 2",
            "country": "Spain",
            "external_id": "4400",
            "source": "TheSportsDB API",
        }

    monkeypatch.setattr(app_module, "one", fake_one)
    competition = app_module.competition_lookup("4400")
    assert competition["external_id"] == "4400"
    assert competition["name"] == "Segunda División"
    assert any("competition_id" in query for query, _params in observed)

    captured = {}

    def fake_rows(query, params=()):
        captured["query"] = query
        captured["params"] = params
        return []

    monkeypatch.setattr(app_module, "rows", fake_rows)
    assert app_module._competition_matches_for(competition, "4400") == []
    assert "competition_id" in captured["query"]
    assert "4400" in captured["params"]
