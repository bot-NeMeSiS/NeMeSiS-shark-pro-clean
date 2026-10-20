from engines.competition_presentation_engine import (
    competition_presentation_group,
    competition_presentation_sections,
)


def test_domestic_competitions_stay_with_their_country_even_when_region_is_europe():
    group = competition_presentation_group({
        "name": "Premier League",
        "country": "England",
        "region": "Europe",
        "scope": "domestic",
    })
    assert group["kind"] == "country"
    assert group["label"] == "Inglaterra"


def test_continental_and_global_cups_share_one_international_section():
    rows = [
        {"key": "uefa-champions-league", "name": "UEFA Champions League", "country": "Europe", "region": "UEFA", "scope": "continental"},
        {"key": "uefa-europa-league", "name": "UEFA Europa League", "country": "Europe", "region": "UEFA", "scope": "continental"},
        {"key": "fifa-world-cup", "name": "FIFA World Cup", "country": "World", "scope": "international"},
    ]
    sections = competition_presentation_sections(rows)
    assert len(sections) == 1
    assert sections[0]["kind"] == "international"
    assert {item["key"] for item in sections[0]["competitions"]} == {
        "uefa-champions-league", "uefa-europa-league", "fifa-world-cup"
    }


def test_domestic_cups_remain_in_country_and_unknown_country_is_not_guessed():
    rows = [
        {"key": "copa-del-rey", "name": "Copa del Rey", "country": "Spain", "region": "Europe", "scope": "domestic-cup"},
        {"key": "unknown", "name": "Regional Cup", "country": "", "scope": ""},
    ]
    sections = competition_presentation_sections(rows)
    assert [section["kind"] for section in sections] == ["country", "unknown"]
    assert sections[0]["label"] == "España"
    assert sections[1]["label"] == "País sin confirmar"
    assert sum(section["count"] for section in sections) == len(rows)


def test_country_sections_sort_spain_first_then_other_countries():
    rows = [
        {"name": "Primeira Liga", "country": "Portugal", "scope": "domestic"},
        {"name": "LaLiga", "country": "Spain", "scope": "domestic"},
        {"name": "Serie A", "country": "Italy", "scope": "domestic"},
    ]
    sections = competition_presentation_sections(rows)
    assert [section["label"] for section in sections] == ["España", "Italia", "Portugal"]
