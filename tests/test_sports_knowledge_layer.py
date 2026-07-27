from __future__ import annotations

import ast
import inspect

import engines.sports_knowledge_layer_engine as knowledge_module
from engines.match_context_engine import build_match_context
from engines.match_intelligence_engine import MATCH_INTELLIGENCE_CONTRACT
from engines.sports_domain_model_engine import (
    SPORTS_DOMAIN_MODEL_CONTRACT,
    build_unified_domain_snapshot,
)
from engines.sports_knowledge_layer_engine import (
    COMPETITION_KNOWLEDGE_CONTRACT,
    MATCH_KNOWLEDGE_CONTRACT,
    SEASON_KNOWLEDGE_CONTRACT,
    SPORTS_KNOWLEDGE_CONSUMERS,
    SPORTS_KNOWLEDGE_LAYER_CONTRACT,
    TEAM_KNOWLEDGE_CONTRACT,
    build_sports_knowledge_snapshot,
    sports_knowledge_layer_snapshot,
)


def _match_row() -> dict:
    return {
        "id": "knowledge-match-1",
        "external_id": "777",
        "sport_key": "soccer",
        "competition_id": "140",
        "competition_name": "Liga Real",
        "league_name": "Liga Real",
        "country": "Spain",
        "season": "2026",
        "round": "Jornada 9",
        "home_team_id": "10",
        "away_team_id": "20",
        "home_team": "Club Local",
        "away_team": "Union Visitante",
        "kickoff_iso": "2026-07-26T20:30:00+02:00",
        "status": "LIVE",
        "minute": 68,
        "home_score": 1,
        "away_score": 0,
        "score": "1-0",
        "venue": "Estadio Central",
        "referee": "Arbitro Principal",
        "source": "api_football",
        "updated_at": "2026-07-26T21:58:00+02:00",
    }


def _events() -> list[dict]:
    return [
        {
            "id": "goal-1",
            "elapsed": 12,
            "event_type": "Goal",
            "detail": "Normal Goal",
            "team_name": "Club Local",
            "player_id": "101",
            "player_name": "Jugador Uno",
            "source": "api_football",
            "captured_at": "2026-07-26T21:58:00+02:00",
        },
        {
            "id": "red-1",
            "elapsed": 64,
            "event_type": "Card",
            "detail": "Red Card",
            "team_name": "Union Visitante",
            "player_id": "202",
            "player_name": "Jugador Dos",
            "source": "api_football",
            "captured_at": "2026-07-26T21:58:00+02:00",
        },
    ]


def _domain() -> dict:
    return build_unified_domain_snapshot(
        _match_row(),
        live_context={
            "provider": "api_football",
            "updated_at": "2026-07-26T21:58:00+02:00",
            "events": _events(),
        },
        timeline_events=_events(),
        picks=({"id": "pick-1", "match_id": "knowledge-match-1", "selection": "Club Local"},),
        now_madrid="2026-07-26T22:00:00+02:00",
    )


def test_sports_knowledge_contracts_are_read_only_and_evidence_backed():
    domain = _domain()
    snapshot = build_sports_knowledge_snapshot(
        domain_model=domain,
        timeline_events=domain["timeline_events"],
        related_picks=({"id": "pick-1", "match_id": "knowledge-match-1", "selection": "Club Local"},),
        now_madrid="2026-07-26T22:00:00+02:00",
    )

    assert snapshot["contract"] == SPORTS_KNOWLEDGE_LAYER_CONTRACT
    assert snapshot["source_domain_contract"] == SPORTS_DOMAIN_MODEL_CONTRACT
    assert snapshot["match_knowledge"]["contract"] == MATCH_KNOWLEDGE_CONTRACT
    assert snapshot["team_knowledge"]["home"]["contract"] == TEAM_KNOWLEDGE_CONTRACT
    assert snapshot["competition_knowledge"]["contract"] == COMPETITION_KNOWLEDGE_CONTRACT
    assert snapshot["season_knowledge"]["contract"] == SEASON_KNOWLEDGE_CONTRACT
    assert snapshot["chronological_knowledge"]["facts"]["timeline_event_count"] == 2
    assert snapshot["match_knowledge"]["facts"]["venue"] == "Estadio Central"

    for contract in (
        snapshot["match_knowledge"],
        snapshot["competition_knowledge"],
        snapshot["season_knowledge"],
        snapshot["team_knowledge"]["home"],
        snapshot["team_knowledge"]["away"],
    ):
        assert contract["read_only"] is True
        assert "source" in contract
        assert "evidence" in contract
        assert "freshness" in contract
        assert "limitations" in contract
        assert "quality" in contract
        assert contract["database_write_authorized"] is False
        assert contract["external_action_authorized"] is False

    diagnostics = snapshot["diagnostics"]
    assert diagnostics["database_queries"] == 0
    assert diagnostics["database_writes"] == 0
    assert diagnostics["external_calls"] == 0
    assert diagnostics["telegram_sends"] == 0
    assert diagnostics["stripe_calls"] == 0
    assert diagnostics["single_domain_snapshot"] is True
    assert snapshot["no_fake_data"] is True


def test_future_consumers_are_prepared_without_enabling_actions():
    snapshot = build_sports_knowledge_snapshot(domain_model=_domain())

    assert set(snapshot["future_consumers"]) == set(SPORTS_KNOWLEDGE_CONSUMERS)
    for consumer, contract in snapshot["future_consumers"].items():
        assert contract["consumer"] == consumer
        assert contract["contract"] == SPORTS_KNOWLEDGE_LAYER_CONTRACT
        assert contract["implementation_state"] == "prepared_not_enabled"
        assert contract["database_write_authorized"] is False
        assert contract["external_action_authorized"] is False
        assert contract["telegram_send_authorized"] is False


def test_missing_knowledge_stays_insufficient_instead_of_invented():
    snapshot = build_sports_knowledge_snapshot()

    assert snapshot["contract"] == SPORTS_KNOWLEDGE_LAYER_CONTRACT
    assert snapshot["match_knowledge"]["certification_state"] == "INSUFFICIENT_DATA"
    assert snapshot["competition_knowledge"]["certification_state"] == "INSUFFICIENT_DATA"
    assert snapshot["season_knowledge"]["certification_state"] == "INSUFFICIENT_DATA"
    assert snapshot["rivalry_knowledge"]["facts"]["head_to_head_available"] is False
    assert "Head-to-head history is not supplied to this layer." in snapshot["limitations"]
    assert snapshot["quality"]["numeric_confidence_score"] is None


def test_match_context_embeds_sports_knowledge_without_extra_effects():
    context = build_match_context(
        {"match": _match_row(), "related_picks": []},
        madrid_context={
            "client_full_datetime_label": "domingo, 26 de julio - 20:30",
            "client_date_label": "domingo, 26 de julio",
            "client_time_label": "20:30",
            "client_score_label": "1-0",
        },
        live_context={
            "provider": "api_football",
            "updated_at": "2026-07-26T21:58:00+02:00",
            "events": _events(),
        },
    )

    assert context["sports_knowledge"]["contract"] == SPORTS_KNOWLEDGE_LAYER_CONTRACT
    assert context["sports_knowledge"]["source_intelligence_contract"] == MATCH_INTELLIGENCE_CONTRACT
    assert context["sports_knowledge"]["source_domain_contract"] == SPORTS_DOMAIN_MODEL_CONTRACT
    assert context["diagnostics"]["sports_knowledge_contract"] == SPORTS_KNOWLEDGE_LAYER_CONTRACT
    assert context["diagnostics"]["sports_knowledge_database_writes"] == 0
    assert context["diagnostics"]["sports_knowledge_external_calls"] == 0
    assert any(item["name"] == "Sports Knowledge" for item in context["prepared_integrations"])


def test_sports_knowledge_module_has_no_io_network_or_framework_dependency():
    source = inspect.getsource(knowledge_module)
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

    metadata = sports_knowledge_layer_snapshot()
    assert metadata["contract"] == SPORTS_KNOWLEDGE_LAYER_CONTRACT
    assert metadata["guardrails"]["database_writes"] == 0
    assert metadata["guardrails"]["external_calls"] == 0
