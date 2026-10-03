from __future__ import annotations

import inspect
from pathlib import Path

from engines import competition_center_engine, match_context_engine, team_center_engine
from engines.sports_entity_navigation_engine import (
    entity_href,
    entity_navigation_contract,
    public_entity_route_id,
)

ROOT = Path(__file__).resolve().parents[1]


def test_public_entity_routes_are_canonical_and_encoded():
    assert entity_href("team", "133602", "Real Madrid") == "/team/Real%20Madrid"
    assert entity_href("player", "thesportsdb:player:34145937", "Jugador") == "/player/34145937"
    assert entity_href("competition", "thesportsdb:competition:4335", "LaLiga") == "/competition/4335"
    assert entity_href("match", "event/123") == "/match/event%2F123"


def test_prepared_entities_fail_closed_until_public_route_exists():
    stadium = entity_navigation_contract("stadium", "bernabeu", "Santiago Bernabéu")
    referee = entity_navigation_contract("referee", "official-1", "Árbitro")
    assert stadium["state"] == "PREPARED"
    assert referee["state"] == "PREPARED"
    assert stadium["href"] is None
    assert referee["href"] is None


def test_route_id_normalization_does_not_guess_cross_provider_identity():
    assert public_entity_route_id("player", "sportsdb:player:123", "Nombre") == "123"
    assert public_entity_route_id("competition", "sportsdb:competition:4335", "LaLiga") == "4335"
    assert public_entity_route_id("team", "sportsdb:team:133602", "Real Madrid") == "Real Madrid"
    assert public_entity_route_id("competition", "", "LaLiga") == "LaLiga"


def test_sports_centers_use_shared_navigation_contract():
    match_source = inspect.getsource(match_context_engine)
    team_source = inspect.getsource(team_center_engine)
    competition_source = inspect.getsource(competition_center_engine)

    assert "sports_entity_navigation_engine" in match_source
    assert "sports_entity_navigation_engine" in team_source
    assert "sports_entity_navigation_engine" in competition_source
    assert "def _entity_href(" not in match_source


def test_shared_cards_and_match_center_expose_contextual_links():
    cards = (ROOT / "templates" / "components" / "v933_ui.html").read_text(encoding="utf-8")
    match_center = (ROOT / "templates" / "components" / "v944_match_center.html").read_text(encoding="utf-8")
    team_detail = (ROOT / "templates" / "team_detail.html").read_text(encoding="utf-8")

    assert "sports_entity_href('team'" in cards
    assert "sports_entity_href('competition'" in cards
    assert 'data-entity-contract="team"' in cards
    assert 'data-entity-contract="competition"' in cards

    assert "team.get('href')" in match_center
    assert "related_player_href" in match_center
    assert "h2h_home_href" in match_center
    assert 'data-entity-contract="player"' in match_center

    assert "links.competition_center" in team_detail
    assert 'data-entity-contract="stadium"' in team_detail
    assert "sports_entity_navigation('stadium'" in team_detail
