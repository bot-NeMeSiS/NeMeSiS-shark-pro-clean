from __future__ import annotations

import ast
import inspect
import sqlite3
from pathlib import Path

import engines.player_center_engine as player_center_module
import engines.sports_graph_foundation_engine as graph_module
from engines.player_center_engine import PLAYER_CENTER_CONTRACT, build_player_center_context, player_center_snapshot
from engines.sentinel_autopilot_engine import build_player_center_experience_contract_snapshot
from engines.shark_intelligence_platform_engine import SHARK_INTELLIGENCE_PLATFORM_CONTRACT
from engines.sports_domain_model_engine import SPORTS_DOMAIN_MODEL_CONTRACT
from engines.sports_graph_foundation_engine import SPORTS_GRAPH_FOUNDATION_CONTRACT
from engines.sports_knowledge_layer_engine import PLAYER_KNOWLEDGE_CONTRACT, SPORTS_KNOWLEDGE_LAYER_CONTRACT
from engines.user_intelligence_platform_engine import USER_INTELLIGENCE_PLATFORM_CONTRACT

ROOT = Path(__file__).resolve().parents[1]


def _match(match_id: str, home: str, away: str, status: str, *, date: str, score: str = "") -> dict:
    home_score = None
    away_score = None
    if "-" in score:
        left, right = score.split("-", 1)
        home_score = int(left)
        away_score = int(right)
    return {
        "id": match_id,
        "match_id": match_id,
        "external_id": match_id,
        "competition_id": "140",
        "competition_name": "Liga Real",
        "league_name": "Liga Real",
        "country": "Spain",
        "season": "2026",
        "round": "Jornada QA",
        "home_team": home,
        "away_team": away,
        "safe_home": home,
        "safe_away": away,
        "home_logo": "/team-crest.svg?name=" + home.replace(" ", "+"),
        "away_logo": "/team-crest.svg?name=" + away.replace(" ", "+"),
        "match_date": date,
        "kickoff_time": "20:30",
        "kickoff_iso": date + "T20:30:00+02:00",
        "status": status,
        "home_score": home_score,
        "away_score": away_score,
        "score": score,
        "source": "api_football_cache",
        "updated_at": date + "T22:30:00+02:00",
        "timeline": [
            {
                "id": match_id + "-goal-1",
                "match_id": match_id,
                "elapsed": 12,
                "event_type": "Goal",
                "team_name": home,
                "player_id": "101",
                "player_name": "Jugador Uno",
                "source": "api_football_cache",
            }
        ] if status == "FT" else [],
    }


def _detail() -> dict:
    return {
        "player": {
            "player_id": "101",
            "id": "101",
            "player_name": "Jugador Uno",
            "name": "Jugador Uno",
            "team_id": "club-local",
            "team_name": "Club Local",
            "position": "Delantero",
            "number": "9",
            "shirt_number": "9",
            "country": "Spain",
            "source": "api_football_cache",
        },
        "team": {
            "id": "club-local",
            "key": "club-local",
            "name": "Club Local",
            "official_name": "Club Local FC",
            "country": "Spain",
            "league": "Liga Real",
            "competition_id": "140",
            "source": "api_football_cache",
        },
        "competition": {
            "key": "liga-real",
            "external_id": "140",
            "name": "Liga Real",
            "country": "Spain",
            "season": "2026",
            "scope": "League",
            "source": "api_football_cache",
        },
        "matches": [
            _match("m-1", "Club Local", "Union Norte", "FT", date="2026-07-20", score="2-0"),
            _match("m-2", "Club Local", "Racing Este", "NS", date="2026-07-31"),
        ],
        "events": [
            {
                "id": "m-1-goal-1",
                "match_id": "m-1",
                "elapsed": 12,
                "event_type": "Goal",
                "detail": "Gol confirmado por proveedor cacheado",
                "team_name": "Club Local",
                "player_id": "101",
                "player_name": "Jugador Uno",
                "source": "api_football_cache",
            }
        ],
        "lineups": [
            {
                "fixture_id": "m-1",
                "player_id": "101",
                "player_name": "Jugador Uno",
                "team_name": "Club Local",
                "position": "Delantero",
                "number": "9",
                "is_starting": 1,
                "source": "api_football_cache",
            }
        ],
        "injuries": [],
        "picks": [{"id": "pick-1", "match_id": "m-2", "selection": "Club Local", "odds": "1.80", "source": "picks"}],
    }


def test_player_center_uses_sports_core_knowledge_graph_shark_and_user_intelligence():
    context = build_player_center_context(_detail(), observed_at_madrid="2026-07-28T10:00:00+02:00")

    assert context["contract"] == PLAYER_CENTER_CONTRACT
    assert context["source_domain_contract"] == SPORTS_DOMAIN_MODEL_CONTRACT
    assert context["sports_knowledge_contract"] == SPORTS_KNOWLEDGE_LAYER_CONTRACT
    assert context["player_knowledge_contract"] == PLAYER_KNOWLEDGE_CONTRACT
    assert context["sports_graph_contract"] == SPORTS_GRAPH_FOUNDATION_CONTRACT
    assert context["shark_intelligence_contract"] == SHARK_INTELLIGENCE_PLATFORM_CONTRACT
    assert context["user_intelligence_contract"] == USER_INTELLIGENCE_PLATFORM_CONTRACT
    assert context["no_fake_data"] is True
    assert context["diagnostics"]["database_writes"] == 0
    assert context["diagnostics"]["external_calls"] == 0
    assert context["diagnostics"]["telegram_sends"] == 0
    assert context["diagnostics"]["stripe_calls"] == 0
    assert context["diagnostics"]["generative_ai_calls"] == 0
    assert context["metrics"]["matches"] == 2
    assert context["metrics"]["upcoming"] == 1
    assert context["metrics"]["events"] >= 1
    assert context["participation"]["goals"] == 1
    assert context["participation"]["starts"] == 1
    assert context["shark_context"]["state"] == "PARTIALLY_VERIFIED"
    assert context["user_intelligence"]["home_modified"] is False
    assert context["player"]["photo"] in (None, "")
    assert "Fotografia no disponible: ninguna fuente legal lo confirma." in context["missing_information"]

    relationships = set(context["sports_graph"]["relationships"])
    assert "player_has_match" in relationships
    assert "match_has_player" in relationships
    assert "player_linked_to_team" in relationships
    assert "team_has_player" in relationships
    assert "player_competes_in_competition" in relationships
    assert "player_appears_in_event" in relationships
    assert "event_has_player" in relationships
    assert "player_context_uses_match_intelligence" in relationships
    assert "shark_context_mentions_player" in relationships
    assert "user_intelligence_observes_player" in relationships


def test_player_center_does_not_invent_missing_player_data():
    context = build_player_center_context({"player": {}, "matches": [], "events": [], "lineups": [], "injuries": [], "picks": []}, observed_at_madrid="2026-07-28T10:00:00+02:00")

    assert context["player"]["official_name"] == "No disponible"
    assert context["player"]["position"] == "No disponible"
    assert context["player"]["shirt_number"] == "No disponible"
    assert context["metrics"]["matches"] == 0
    assert context["metrics"]["events"] == 0
    assert context["participation"]["available"] is False
    assert context["shark_context"]["state"] == "INSUFFICIENT_DATA"
    assert "Eventos personales no disponibles." in context["missing_information"]
    assert context["no_fake_data"] is True


def test_player_center_template_uses_canonical_cards_and_transparency_markers():
    template = (ROOT / "templates" / "player_detail.html").read_text(encoding="utf-8")

    assert "data-player-center-contract" in template
    assert "data-sports-domain-model" in template
    assert "data-sports-knowledge-contract" in template
    assert "data-player-knowledge-contract" in template
    assert "data-sports-graph-contract" in template
    assert "data-shark-intelligence-contract" in template
    assert "data-user-intelligence-contract" in template
    assert "data-player-center-section=\"shark-context\"" in template
    assert "data-player-center-section=\"sports-graph\"" in template
    assert "data-player-center-section=\"user-intelligence\"" in template
    assert "match_card(match, true, true)" in template
    assert "class=\"card match-card\"" not in template
    assert "No disponible" in template
    assert "Ninguna fuente confirma" in template


def test_player_center_sentinel_contract_passes():
    snapshot = build_player_center_experience_contract_snapshot(ROOT, "TEST")
    assert snapshot["validation_result"] == "PASS"
    assert snapshot["evidence"]["violations"] == []


def test_player_center_engines_are_read_only():
    for module in (player_center_module, graph_module):
        source = inspect.getsource(module)
        tree = ast.parse(source)
        imported_roots = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert {"sqlite3", "requests", "urllib", "flask", "stripe", "openai"} & imported_roots == set()
        assert "TELEGRAM_BOT_TOKEN" not in source
        assert "STRIPE_SECRET_KEY" not in source
        assert "OPENAI_API_KEY" not in source

    snapshot = player_center_snapshot()
    assert snapshot["contract"] == PLAYER_CENTER_CONTRACT
    assert snapshot["guardrails"]["database_writes"] == 0
    assert snapshot["guardrails"]["external_calls"] == 0
    assert snapshot["guardrails"]["telegram_sends"] == 0
    assert snapshot["guardrails"]["stripe_calls"] == 0
    assert snapshot["guardrails"]["generative_ai_calls"] == 0

def test_player_center_api_handles_optional_provider_columns_missing(tmp_path, monkeypatch):
    import app as app_module

    db_path = tmp_path / "player-center-optional-columns.sqlite"
    monkeypatch.setattr(app_module, "DB_PATH", str(db_path), raising=False)
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", None, raising=False)
    monkeypatch.setattr(app_module, "_SEEDING_DB_PATH", None, raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    app_module.init_db()

    def insert_row(connection: sqlite3.Connection, table: str, payload: dict) -> None:
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        data = {key: value for key, value in payload.items() if key in columns}
        keys = list(data)
        placeholders = ",".join("?" for _ in keys)
        connection.execute(
            f"INSERT OR REPLACE INTO {table} ({','.join(keys)}) VALUES ({placeholders})",
            [data[key] for key in keys],
        )

    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE api_football_live_events (
            id TEXT PRIMARY KEY,
            fixture_id TEXT,
            match_id TEXT,
            player_id TEXT,
            player_name TEXT,
            team_id TEXT,
            team_name TEXT,
            event_type TEXT,
            type TEXT,
            detail TEXT,
            elapsed INTEGER,
            minute INTEGER,
            source TEXT,
            captured_at TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE api_football_lineups_deep (
            id TEXT PRIMARY KEY,
            fixture_id TEXT,
            match_id TEXT,
            player_id TEXT,
            player_name TEXT,
            team_id TEXT,
            team_name TEXT,
            position TEXT,
            number TEXT,
            is_starting INTEGER,
            source TEXT,
            captured_at TEXT
        )
        """
    )
    insert_row(
        connection,
        "competitions",
        {
            "key": "liga-real",
            "external_id": "140",
            "name": "Liga Real",
            "country": "Spain",
            "source": "test_temp_db",
            "updated_at": "2026-07-28T10:00:00+02:00",
        },
    )
    insert_row(
        connection,
        "teams",
        {
            "key": "club-local",
            "external_id": "club-local",
            "name": "Club Local",
            "country": "Spain",
            "league": "Liga Real",
            "source": "test_temp_db",
            "updated_at": "2026-07-28T10:00:00+02:00",
        },
    )
    insert_row(
        connection,
        "matches",
        {
            "id": "m-1",
            "external_id": "m-1",
            "match_date": "2026-07-20",
            "kickoff_time": "20:30",
            "kickoff_iso": "2026-07-20T20:30:00+02:00",
            "competition_id": "140",
            "competition_key": "liga-real",
            "competition_name": "Liga Real",
            "league_name": "Liga Real",
            "home_team": "Club Local",
            "away_team": "Union Norte",
            "home_team_id": "club-local",
            "status": "FT",
            "score": "2-0",
            "home_score": "2",
            "away_score": "0",
            "source": "test_temp_db",
            "updated_at": "2026-07-20T22:30:00+02:00",
        },
    )
    insert_row(
        connection,
        "api_football_live_events",
        {
            "id": "event-1",
            "fixture_id": "m-1",
            "match_id": "m-1",
            "player_id": "101",
            "player_name": "Jugador Uno",
            "team_id": "club-local",
            "team_name": "Club Local",
            "event_type": "Goal",
            "type": "Goal",
            "detail": "Gol confirmado por fixture temporal",
            "elapsed": 12,
            "minute": 12,
            "source": "test_temp_db",
            "captured_at": "2026-07-20T22:30:00+02:00",
        },
    )
    insert_row(
        connection,
        "api_football_lineups_deep",
        {
            "id": "lineup-1",
            "fixture_id": "m-1",
            "match_id": "m-1",
            "player_id": "101",
            "player_name": "Jugador Uno",
            "team_id": "club-local",
            "team_name": "Club Local",
            "position": "Delantero",
            "number": "9",
            "is_starting": 1,
            "source": "test_temp_db",
            "captured_at": "2026-07-20T22:30:00+02:00",
        },
    )
    connection.commit()
    connection.close()

    with app_module.app.test_client() as client:
        response = client.get("/api/players/101/detail")

    assert response.status_code == 200
    payload = response.get_json()
    center = payload["player"]["player_center"]
    assert center["contract"] == PLAYER_CENTER_CONTRACT
    assert center["metrics"]["events"] == 1
    assert center["participation"]["starts"] == 1
    assert center["diagnostics"]["database_writes"] == 0


