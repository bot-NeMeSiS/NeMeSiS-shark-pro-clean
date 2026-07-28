from __future__ import annotations

import ast
import inspect
from pathlib import Path

import engines.competition_center_engine as competition_center_module
import engines.sports_graph_foundation_engine as graph_module
from engines.competition_center_engine import (
    COMPETITION_CENTER_CONTRACT,
    build_competition_center_context,
    competition_center_snapshot,
)
from engines.sentinel_autopilot_engine import build_competition_center_experience_contract_snapshot
from engines.sports_domain_model_engine import SPORTS_DOMAIN_MODEL_CONTRACT
from engines.sports_graph_foundation_engine import SPORTS_GRAPH_FOUNDATION_CONTRACT
from engines.sports_knowledge_layer_engine import SPORTS_KNOWLEDGE_LAYER_CONTRACT

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
        "competition_key": "liga-real",
        "competition_name": "Liga Real",
        "league_name": "Liga Real",
        "country": "Spain",
        "season": "2026",
        "round": "Jornada 12",
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
        ],
    }


def _detail() -> dict:
    return {
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
            _match("m-1", "Club Norte", "Club Sur", "FT", date="2026-07-20", score="2-0"),
            _match("m-2", "Club Este", "Club Oeste", "NS", date="2026-07-31"),
        ],
        "teams": [
            {"key": "club-norte", "name": "Club Norte", "country": "Spain", "league": "Liga Real", "source": "api_football_cache"},
            {"key": "club-sur", "name": "Club Sur", "country": "Spain", "league": "Liga Real", "source": "api_football_cache"},
        ],
        "standings": [
            {
                "rank": 1,
                "team_id": "club-norte",
                "team_name": "Club Norte",
                "played": 12,
                "wins": 8,
                "draws": 2,
                "losses": 2,
                "goals_for": 24,
                "goals_against": 10,
                "points": 26,
                "form": "VVEVV",
                "description": "Champion",
                "source": "api_football_standings_deep",
            },
            {
                "rank": 2,
                "team_id": "club-sur",
                "team_name": "Club Sur",
                "played": 12,
                "wins": 7,
                "draws": 3,
                "losses": 2,
                "goals_for": 19,
                "goals_against": 11,
                "points": 24,
                "form": "EVVVV",
                "description": "Europa",
                "source": "api_football_standings_deep",
            },
        ],
        "picks": [{"id": "pick-1", "match_id": "m-2", "selection": "Club Este", "odds": "1.90", "source": "picks"}],
    }


def test_competition_center_uses_sports_core_knowledge_and_graph():
    context = build_competition_center_context(_detail(), observed_at_madrid="2026-07-28T10:00:00+02:00")

    assert context["contract"] == COMPETITION_CENTER_CONTRACT
    assert context["source_domain_contract"] == SPORTS_DOMAIN_MODEL_CONTRACT
    assert context["sports_knowledge_contract"] == SPORTS_KNOWLEDGE_LAYER_CONTRACT
    assert context["sports_graph_contract"] == SPORTS_GRAPH_FOUNDATION_CONTRACT
    assert context["no_fake_data"] is True
    assert context["diagnostics"]["database_writes"] == 0
    assert context["diagnostics"]["external_calls"] == 0
    assert context["diagnostics"]["telegram_sends"] == 0
    assert context["diagnostics"]["stripe_calls"] == 0
    assert context["metrics"]["matches"] == 2
    assert context["metrics"]["standings"] == 2
    assert context["metrics"]["teams"] >= 2
    assert context["standings"]["available"] is True
    assert context["standings"]["rows"][0]["goal_difference"] == 14
    assert context["calendar"]["current_round"] == "Jornada 12"
    assert context["shark_context"]["state"] == "PARTIALLY_VERIFIED"

    relationships = set(context["sports_graph"]["relationships"])
    assert "match_has_team" in relationships
    assert "team_has_match" in relationships
    assert "match_belongs_to_competition" in relationships
    assert "team_competes_in_competition" in relationships
    assert "competition_has_team" in relationships
    assert "match_has_timeline_event" in relationships
    assert "pick_references_match" in relationships
    assert "telegram_context_mentions_match" in relationships
    assert "shark_context_analyzes_match" in relationships


def test_competition_center_does_not_invent_missing_competition_data():
    detail = _detail()
    detail["competition"] = {"key": "liga-real", "name": "Liga Real", "source": "local_cache"}
    detail["matches"] = []
    detail["teams"] = []
    detail["standings"] = []
    detail["picks"] = []

    context = build_competition_center_context(detail, observed_at_madrid="2026-07-28T10:00:00+02:00")

    assert context["competition"]["season"] == "No disponible"
    assert context["competition"]["type"] == "No disponible"
    assert context["standings"]["available"] is False
    assert context["metrics"]["teams"] == 0
    assert context["metrics"]["matches"] == 0
    assert context["metrics"]["graph_edges"] == 0
    assert context["shark_context"]["state"] == "INSUFFICIENT_DATA"
    assert "Temporada no disponible." in context["missing_information"]
    assert "No hay partidos asociados a esta competicion." in context["missing_information"]


def test_competition_center_template_uses_canonical_match_card_and_transparency_markers():
    template = (ROOT / "templates" / "competition_detail.html").read_text(encoding="utf-8")

    assert "data-competition-center-contract" in template
    assert "data-sports-domain-model" in template
    assert "data-sports-knowledge-contract" in template
    assert "data-sports-graph-contract" in template
    assert "data-competition-center-section=\"standings\"" in template
    assert "data-competition-center-section=\"teams\"" in template
    assert "match_card(match, true, true)" in template
    assert "class=\"card match-card\"" not in template
    assert "No disponible" in template
    assert "Ninguna fuente confirma" in template
    assert "No crea clasificaciones" in template


def test_competition_center_sentinel_contract_passes():
    snapshot = build_competition_center_experience_contract_snapshot(ROOT, "TEST")
    assert snapshot["validation_result"] == "PASS"
    assert snapshot["evidence"]["violations"] == []


def test_competition_center_engines_are_read_only():
    for module in (competition_center_module, graph_module):
        source = inspect.getsource(module)
        tree = ast.parse(source)
        imported_roots = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert {"sqlite3", "requests", "urllib", "flask", "stripe"} & imported_roots == set()
        assert "TELEGRAM_BOT_TOKEN" not in source
        assert "STRIPE_SECRET_KEY" not in source
        assert "OPENAI_API_KEY" not in source

    snapshot = competition_center_snapshot()
    assert snapshot["contract"] == COMPETITION_CENTER_CONTRACT
    assert snapshot["guardrails"]["database_writes"] == 0
    assert snapshot["guardrails"]["external_calls"] == 0
    assert snapshot["guardrails"]["telegram_sends"] == 0
