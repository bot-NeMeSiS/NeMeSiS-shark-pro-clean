from __future__ import annotations

import inspect
import sqlite3
from pathlib import Path

from engines import sports_history_engine as history
from engines import sports_history_adapters as adapters

ROOT = Path(__file__).resolve().parents[1]


def _team(stadium_id="9001"):
    return {
        "idTeam": "133602",
        "strTeam": "Real Madrid",
        "idLeague": "4335",
        "strLeague": "Spanish La Liga",
        "strCountry": "Spain",
        "intFormedYear": "1902",
        "strStadium": "Santiago Bernabeu",
        "idVenue": stadium_id,
        "strStadiumLocation": "Madrid",
        "intStadiumCapacity": "81044",
        "strBadge": "https://example.invalid/real-madrid.png",
        "strManager": "Entrenador confirmado",
    }


def _player():
    return {
        "idPlayer": "34145937",
        "strPlayer": "Jugador Confirmado",
        "idTeam": "133602",
        "strTeam": "Real Madrid",
        "strPosition": "Forward",
        "strNumber": "9",
        "strNationality": "Spain",
        "dateBorn": "2000-01-02",
        "strHeight": "1.84 m",
        "strSide": "Right",
        "strThumb": "https://example.invalid/player.png",
    }


def test_sportsdb_team_and_roster_are_persistent_idempotent_and_related(tmp_path):
    db_path = tmp_path / "sports.sqlite"
    with sqlite3.connect(db_path) as conn:
        history.ensure_schema(conn)
        team_id = adapters.ingest_sportsdb_team_profile(conn, _team())
        first_player = adapters.ingest_sportsdb_player_profile(conn, _player())
        second_player = adapters.ingest_sportsdb_player_profile(conn, _player())
        conn.commit()

        assert first_player == second_player
        assert conn.execute(
            "SELECT COUNT(*) FROM sports_history_entities WHERE kind='player'"
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM sports_history_entity_links "
            "WHERE source_id=? AND relation='team_has_player' AND target_id=?",
            (team_id, first_player),
        ).fetchone()[0] == 1

    team = history.team_profile(str(db_path), "133602", source="thesportsdb")
    roster = history.team_roster(str(db_path), "133602", source="thesportsdb")
    assert team["facts"]["stadium_name"] == "Santiago Bernabeu"
    assert team["facts"]["formed_year"] == "1902"
    assert team["facts"]["coach"] == "Entrenador confirmado"
    assert len(roster) == 1
    assert roster[0]["facts"]["name"] == "Jugador Confirmado"
    assert roster[0]["external_calls"] == 0


def test_stadium_name_without_provider_id_stays_a_team_fact(tmp_path):
    db_path = tmp_path / "sports.sqlite"
    with sqlite3.connect(db_path) as conn:
        history.ensure_schema(conn)
        adapters.ingest_sportsdb_team_profile(conn, _team(stadium_id=""))
        conn.commit()
        assert conn.execute(
            "SELECT COUNT(*) FROM sports_history_entities WHERE kind='stadium'"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM sports_history_entity_links WHERE relation='team_uses_stadium'"
        ).fetchone()[0] == 0

    card = history.team_profile(str(db_path), "133602", source="thesportsdb")
    assert card["facts"]["stadium_name"] == "Santiago Bernabeu"


def test_known_provider_aliases_share_one_namespace():
    assert history.provider_name("sportsdb") == "thesportsdb"
    assert history.provider_name("TheSportsDB API") == "thesportsdb"
    assert history.provider_name("The SportsDB Premium") == "thesportsdb"
    assert history.provider_name("API-Football") == "api_football"
    assert history.provider_name("The Odds API") == "the_odds_api"


def test_same_numeric_id_from_different_providers_is_not_auto_merged():
    conn = sqlite3.connect(":memory:")
    try:
        history.ensure_schema(conn)
        sportsdb = history.entity(conn, "player", "thesportsdb", "123", {"name": "One"})
        api_football = history.entity(conn, "player", "api_football", "123", {"name": "One"})
        assert sportsdb != api_football
        assert history.entity_id(conn, "player", "thesportsdb", "123") == sportsdb
        assert history.entity_id(conn, "player", "api_football", "123") == api_football
    finally:
        conn.close()


def test_entity_links_require_existing_canonical_entities():
    conn = sqlite3.connect(":memory:")
    try:
        history.ensure_schema(conn)
        team = history.entity(conn, "team", "thesportsdb", "1", {"name": "Team"})
        try:
            history.link_entities(conn, team, "team_has_player", "missing", "thesportsdb")
        except ValueError as exc:
            assert "existing canonical entities" in str(exc)
        else:
            raise AssertionError("Missing target must not create a relationship")
    finally:
        conn.close()


def test_product_read_paths_use_history_cache_and_not_entity_sync():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    team_start = app_source.index("def team_page_data")
    team_end = app_source.index("\n\ndef _competition_route_candidates", team_start)
    player_start = app_source.index("def player_page_data")
    player_end = app_source.index("\ndef shark_context_summary", player_start)

    team_block = app_source[team_start:team_end]
    player_block = app_source[player_start:player_end]

    assert "_sports_history_team_context" in team_block
    assert "_sports_history_players_for_team" in team_block
    assert "sync_sportsdb_entity_memory" not in team_block
    assert "_sports_history_player_fact" in player_block
    assert "sync_sportsdb_entity_memory" not in player_block


def test_entity_sync_is_automation_owned_and_bounded():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    automation_source = (ROOT / "engines" / "daily_automation_engine.py").read_text(encoding="utf-8")
    scheduler_source = (ROOT / "engines" / "scheduler_engine.py").read_text(encoding="utf-8")

    assert "def sync_sportsdb_entity_memory(limit_teams=6" in app_source
    assert '"sports_entities_sync": lambda: v818_callback_result' in app_source
    assert '"sports_entities_sync": "07:10"' in automation_source
    assert '"sports_entities_sync": ("thesportsdb", 6)' in automation_source
    assert '"sports_entities"' in scheduler_source
    assert "SPORTS_ENTITIES_SYNC_HOURS" in scheduler_source


def test_admin_summary_exposes_entity_and_relation_counts(tmp_path):
    db_path = tmp_path / "sports.sqlite"
    with sqlite3.connect(db_path) as conn:
        history.ensure_schema(conn)
        adapters.ingest_sportsdb_team_profile(conn, _team())
        adapters.ingest_sportsdb_player_profile(conn, _player())
        conn.commit()

    summary = history.history_summary(str(db_path))
    entity_counts = {item["kind"]: item["count"] for item in summary["entity_counts"]}
    relations = {item["relation"]: item["count"] for item in summary["relation_counts"]}
    assert entity_counts["team"] >= 1
    assert entity_counts["player"] == 1
    assert relations["team_has_player"] == 1
    assert summary["external_calls"] == 0


def test_team_center_copy_no_longer_claims_roster_is_only_from_lineups():
    source = (ROOT / "engines" / "team_center_engine.py").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "team_detail.html").read_text(encoding="utf-8")
    assert "Plantilla disponible desde fuente deportiva confirmada." in source
    assert "Plantilla disponible desde alineaciones confirmadas." not in source
    assert 'data-entity-contract="coach"' in template
    assert 'data-entity-contract="stadium"' in template
