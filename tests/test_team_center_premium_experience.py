from __future__ import annotations

import ast
import inspect
from pathlib import Path

import engines.sports_graph_foundation_engine as graph_module
import engines.team_center_engine as team_center_module
from engines.sentinel_autopilot_engine import build_team_center_experience_contract_snapshot
from engines.sports_graph_foundation_engine import SPORTS_GRAPH_FOUNDATION_CONTRACT
from engines.sports_knowledge_layer_engine import SPORTS_KNOWLEDGE_LAYER_CONTRACT
from engines.sports_domain_model_engine import SPORTS_DOMAIN_MODEL_CONTRACT
from engines.team_center_engine import TEAM_CENTER_CONTRACT, build_team_center_context, team_center_snapshot

ROOT = Path(__file__).resolve().parents[1]


def _match(match_id: str, home_score: int | None, away_score: int | None, *, date: str, opponent: str) -> dict:
    return {
        "id": match_id,
        "match_id": match_id,
        "external_id": match_id,
        "competition_id": "140",
        "competition_name": "Liga Real",
        "league_name": "Liga Real",
        "country": "Spain",
        "season": "2026",
        "home_team": "Club Local",
        "away_team": opponent,
        "safe_home": "Club Local",
        "safe_away": opponent,
        "home_logo": "/team-crest.svg?name=Club+Local",
        "away_logo": "/team-crest.svg?name=" + opponent.replace(" ", "+"),
        "match_date": date,
        "kickoff_time": "20:30",
        "kickoff_iso": date + "T20:30:00+02:00",
        "status": "FT" if home_score is not None else "NS",
        "home_score": home_score,
        "away_score": away_score,
        "score": f"{home_score}-{away_score}" if home_score is not None else "",
        "source": "api_football_cache",
        "updated_at": date + "T22:30:00+02:00",
        "timeline": [
            {
                "id": match_id + "-goal-1",
                "match_id": match_id,
                "elapsed": 12,
                "event_type": "Goal",
                "team_name": "Club Local",
                "player_id": "101",
                "player_name": "Jugador Uno",
                "source": "api_football_cache",
            }
        ],
    }


def _detail() -> dict:
    recent = [
        _match("m-1", 2, 0, date="2026-07-20", opponent="Union Norte"),
        _match("m-2", 1, 1, date="2026-07-17", opponent="Deportivo Centro"),
        _match("m-3", 0, 1, date="2026-07-13", opponent="Atletico Sur"),
    ]
    upcoming = [_match("m-4", None, None, date="2026-07-31", opponent="Racing Este")]
    return {
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
        "key": "club-local",
        "name": "Club Local",
        "identity": {"display_name": "Club Local", "crest_url": "/team-crest.svg?name=Club+Local"},
        "upcoming": upcoming,
        "recent": recent,
        "live": [],
        "picks": [{"id": "pick-1", "match_id": "m-4", "selection": "Club Local", "odds": "1.80", "source": "picks"}],
        "is_favorite": False,
        "stats": {"upcoming": 1, "recent": 3, "live": 0, "picks": 1},
        "shark_context": "Contexto SHARK con datos reales cacheados.",
    }


def test_team_center_context_uses_sports_core_contracts_and_graph():
    context = build_team_center_context(_detail(), observed_at_madrid="2026-07-28T10:00:00+02:00")

    assert context["contract"] == TEAM_CENTER_CONTRACT
    assert context["source_domain_contract"] == SPORTS_DOMAIN_MODEL_CONTRACT
    assert context["sports_knowledge_contract"] == SPORTS_KNOWLEDGE_LAYER_CONTRACT
    assert context["sports_graph_contract"] == SPORTS_GRAPH_FOUNDATION_CONTRACT
    assert context["no_fake_data"] is True
    assert context["diagnostics"]["database_writes"] == 0
    assert context["diagnostics"]["external_calls"] == 0
    assert context["diagnostics"]["telegram_sends"] == 0
    assert context["metrics"]["upcoming"] == 1
    assert context["metrics"]["recent"] == 3
    assert context["form"]["sample_size"] == 3
    assert context["form"]["wins"] == 1
    assert context["form"]["draws"] == 1
    assert context["form"]["losses"] == 1
    assert "Estadio no disponible: ninguna fuente lo confirma." in context["missing_information"]
    assert "Fundación no disponible: ninguna fuente lo confirma." in context["missing_information"]

    relationships = set(context["sports_graph"]["relationships"])
    assert "match_has_team" in relationships
    assert "team_has_match" in relationships
    assert "match_belongs_to_competition" in relationships
    assert "team_competes_in_competition" in relationships
    assert "match_belongs_to_season" in relationships
    assert "match_has_timeline_event" in relationships
    assert "pick_references_match" in relationships
    assert "telegram_context_mentions_match" in relationships
    assert "shark_context_analyzes_match" in relationships


def test_empty_team_center_does_not_invent_profile_data():
    detail = _detail()
    detail["recent"] = []
    detail["upcoming"] = []
    detail["picks"] = []
    context = build_team_center_context(detail, observed_at_madrid="2026-07-28T10:00:00+02:00")

    assert context["team"]["stadium"] == "No disponible"
    assert context["team"]["founded"] == "No disponible"
    assert context["form"]["available"] is False
    assert context["strengths"] == []
    assert context["weaknesses"] == []
    assert context["metrics"]["graph_edges"] == 0
    assert context["shark_context"]["state"] == "INSUFFICIENT_DATA"


def test_team_center_template_uses_canonical_match_card_and_transparency_markers():
    template = (ROOT / "templates" / "team_detail.html").read_text(encoding="utf-8")

    assert "data-team-center-contract" in template
    assert "data-sports-domain-model" in template
    assert "data-sports-knowledge-contract" in template
    assert "data-sports-graph-contract" in template
    assert "match_card(match, true, true)" in template
    assert "class=\"card match-card\"" not in template
    assert "V540" not in template
    assert "form.items" not in template
    assert "No disponible" in template
    assert "Ninguna fuente lo confirma" in template


def test_team_center_sentinel_contract_passes():
    snapshot = build_team_center_experience_contract_snapshot(ROOT, "V939_TEST")
    assert snapshot["validation_result"] == "PASS"
    assert snapshot["evidence"]["violations"] == []


def test_team_center_and_sports_graph_engines_are_read_only():
    for module in (team_center_module, graph_module):
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

    snapshot = team_center_snapshot()
    assert snapshot["contract"] == TEAM_CENTER_CONTRACT
    assert snapshot["guardrails"]["database_writes"] == 0
    assert snapshot["guardrails"]["external_calls"] == 0
    assert snapshot["guardrails"]["telegram_sends"] == 0