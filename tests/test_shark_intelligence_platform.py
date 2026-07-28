from __future__ import annotations

import ast
import inspect
from pathlib import Path

import engines.shark_intelligence_platform_engine as shark_platform_module
from engines.match_context_engine import build_match_context
from engines.sentinel_autopilot_engine import build_shark_intelligence_platform_contract_snapshot
from engines.shark_intelligence_platform_engine import (
    SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
    build_shark_intelligence_platform_snapshot,
    shark_intelligence_platform_snapshot,
)
from engines.sports_graph_foundation_engine import SPORTS_GRAPH_FOUNDATION_CONTRACT
from engines.sports_knowledge_layer_engine import SPORTS_KNOWLEDGE_LAYER_CONTRACT
from engines.sports_platform_contracts import build_sports_platform_contract_registry

ROOT = Path(__file__).resolve().parents[1]


def _match() -> dict:
    return {
        "id": "m-shark-1",
        "match_id": "m-shark-1",
        "competition_id": "140",
        "competition_key": "liga-real",
        "competition_name": "Liga Real",
        "league_name": "Liga Real",
        "country": "Spain",
        "season": "2026",
        "round": "Jornada 12",
        "home_team": "Club Norte",
        "away_team": "Club Sur",
        "home_team_id": "club-norte",
        "away_team_id": "club-sur",
        "match_date": "2026-07-28",
        "kickoff_time": "20:30",
        "kickoff_iso": "2026-07-28T20:30:00+02:00",
        "status": "2H",
        "minute": 68,
        "home_score": 1,
        "away_score": 0,
        "score": "1-0",
        "source": "api_football_cache",
        "updated_at": "2026-07-28T21:58:00+02:00",
    }


def _timeline() -> list[dict]:
    return [
        {
            "id": "goal-1",
            "match_id": "m-shark-1",
            "elapsed": 12,
            "event_type": "Goal",
            "team_name": "Club Norte",
            "player_id": "101",
            "player_name": "Jugador Uno",
            "source": "api_football_cache",
        },
        {
            "id": "red-1",
            "match_id": "m-shark-1",
            "elapsed": 64,
            "event_type": "Card",
            "detail": "Red Card",
            "team_name": "Club Sur",
            "player_id": "202",
            "player_name": "Jugador Dos",
            "source": "api_football_cache",
        },
    ]


def _match_context() -> dict:
    return build_match_context(
        {
            "match": _match(),
            "timeline": _timeline(),
            "related_picks": [
                {
                    "id": "pick-shark-1",
                    "match_id": "m-shark-1",
                    "selection": "Club Norte",
                    "odds": "1.90",
                    "source": "picks_cache",
                }
            ],
        },
        madrid_context={
            "client_full_datetime_label": "martes, 28 de julio de 2026, 20:30",
            "machine_iso": "2026-07-28T20:30:00+02:00",
        },
        live_context={
            "provider": "api_football_cache",
            "updated_at": "2026-07-28T21:58:00+02:00",
            "events": _timeline(),
            "statistics": {
                "available": True,
                "source": "api_football_cache",
                "items": [
                    {"key": "possession", "label": "Posesion", "home": "58%", "away": "42%"},
                    {"key": "shots_on_goal", "label": "Tiros a puerta", "home": "6", "away": "2"},
                ],
            },
        },
    )


def _team_center() -> dict:
    return {
        "contract": "TEAM-CENTER-PREMIUM-CLUB-EXPERIENCE-V1",
        "team": {"display_name": "Club Norte", "source": "api_football_cache"},
        "metrics": {"recent": 3, "upcoming": 1, "picks": 1},
        "data_quality": {"state": "PARTIALLY_VERIFIED", "label": "Datos parciales", "source": "api_football_cache"},
        "freshness": {"label": "Actualizado 2026-07-28", "state": "fresh"},
        "available_information": ["Forma reciente", "Proximo partido"],
        "missing_information": ["Fundacion no disponible."],
        "sports_graph": {"edge_count": 8, "relationships": ["team_has_match", "team_competes_in_competition"]},
        "diagnostics": {"database_writes": 0, "external_calls": 0},
        "no_fake_data": True,
    }


def _competition_center() -> dict:
    return {
        "contract": "COMPETITION-CENTER-LEAGUE-INTELLIGENCE-PLATFORM-V1",
        "competition": {"name": "Liga Real", "source": "api_football_cache"},
        "metrics": {"teams": 4, "matches": 2, "standings": 4},
        "data_quality": {"state": "PARTIALLY_VERIFIED", "label": "Clasificacion parcial", "source": "api_football_cache"},
        "freshness": {"label": "Actualizado 2026-07-28", "state": "fresh"},
        "available_information": ["Clasificacion", "Calendario"],
        "missing_information": ["Fase no disponible."],
        "sports_graph": {"edge_count": 12, "relationships": ["competition_has_team", "match_belongs_to_competition"]},
        "diagnostics": {"database_writes": 0, "external_calls": 0},
        "no_fake_data": True,
    }


def test_shark_intelligence_platform_consumes_existing_contracts_only():
    snapshot = build_shark_intelligence_platform_snapshot(
        match_context=_match_context(),
        team_center=_team_center(),
        competition_center=_competition_center(),
        sports_summary={"totals": {"today": 2, "live": 1, "upcoming": 1}, "source": "sports_metrics_v1"},
        sports_metrics={"contract": "sports-metrics-v1", "matches_today": 2, "live": 1},
        observed_at_madrid="2026-07-28T22:00:00+02:00",
    )

    assert snapshot["contract"] == SHARK_INTELLIGENCE_PLATFORM_CONTRACT
    assert snapshot["source_contracts"]["sports_knowledge"] == SPORTS_KNOWLEDGE_LAYER_CONTRACT
    assert snapshot["source_contracts"]["sports_graph"] == SPORTS_GRAPH_FOUNDATION_CONTRACT
    assert snapshot["no_fake_data"] is True
    assert snapshot["no_predictions"] is True
    assert snapshot["read_only"] is True
    assert snapshot["diagnostics"]["database_writes"] == 0
    assert snapshot["diagnostics"]["external_calls"] == 0
    assert snapshot["diagnostics"]["telegram_sends"] == 0
    assert snapshot["diagnostics"]["stripe_calls"] == 0
    assert snapshot["diagnostics"]["generative_ai_calls"] == 0
    assert snapshot["transparency"]["all_claims_traceable"] is True
    assert len(snapshot["claims"]) >= 4
    assert {item["key"] for item in snapshot["modules"]} >= {
        "match_center",
        "match_intelligence",
        "team_center",
        "competition_center",
    }
    for claim in snapshot["claims"]:
        assert claim["source"]
        assert claim["evidence"]
        assert claim["freshness"]
        assert claim["quality"]
        assert "limitations" in claim


def test_shark_intelligence_platform_does_not_turn_missing_data_into_facts():
    snapshot = build_shark_intelligence_platform_snapshot(
        match_context={},
        team_center={},
        competition_center={},
        sports_summary={},
        sports_metrics={},
        observed_at_madrid="2026-07-28T22:00:00+02:00",
    )

    assert snapshot["certification_state"] == "INSUFFICIENT_DATA"
    assert snapshot["summary"]["headline"] == "Sin evidencia suficiente"
    assert snapshot["missing_information"]
    assert snapshot["transparency"]["all_claims_traceable"] is True
    assert snapshot["sports_graph"]["edge_count"] == 0
    assert snapshot["assistant_preparation"]["generative_ai_enabled"] is False


def test_shark_intelligence_platform_registry_template_and_sentinel_pass():
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry.get("capabilities") or []}
    template = (ROOT / "templates" / "shark_intelligence_center.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "v933-product.css").read_text(encoding="utf-8")
    sentinel = build_shark_intelligence_platform_contract_snapshot(ROOT, "TEST")

    assert capabilities["shark_intelligence_platform"]["state"] == "INTEGRATED"
    assert capabilities["shark_intelligence_platform"]["contract"] == SHARK_INTELLIGENCE_PLATFORM_CONTRACT
    assert "data-shark-intelligence-contract" in template
    assert "data-sports-knowledge-contract" in template
    assert "data-sports-graph-contract" in template
    assert "No hay conversacion IA" in template
    assert "SHARK INTELLIGENCE PLATFORM V1" in css
    assert sentinel["validation_result"] == "PASS"
    assert sentinel["evidence"]["violations"] == []


def test_shark_intelligence_platform_engine_is_read_only():
    source = inspect.getsource(shark_platform_module)
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
    metadata = shark_intelligence_platform_snapshot()
    assert metadata["guardrails"]["database_writes"] == 0
    assert metadata["guardrails"]["external_calls"] == 0
    assert metadata["guardrails"]["telegram_sends"] == 0
    assert metadata["guardrails"]["stripe_calls"] == 0
    assert metadata["guardrails"]["generative_ai_calls"] == 0
