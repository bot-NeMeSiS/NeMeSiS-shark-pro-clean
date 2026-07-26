from __future__ import annotations

import ast
import inspect

import engines.match_intelligence_engine as match_intelligence_module
from engines.match_intelligence_engine import (
    MATCH_INTELLIGENCE_CONSUMERS,
    MATCH_INTELLIGENCE_CONTRACT,
    build_match_intelligence,
    build_match_intelligence_consumer_view,
    build_shark_match_intelligence_state,
    match_intelligence_snapshot,
)
from engines.shark_ai_product_assistant_engine import (
    answer_shark_question,
    build_shark_context as build_product_shark_context,
)
from engines.shark_context_presentation_engine import build_shark_context_state
from engines.shark_engine import build_shark_context
from engines.sports_platform_contracts import build_assistant_context


def _match() -> dict:
    return {
        "id": "match-intelligence-1",
        "home_team": "Club Local",
        "away_team": "Union Visitante",
        "home_team_id": "10",
        "away_team_id": "20",
        "competition_id": "140",
        "competition_name": "Liga Real",
        "status": "2H",
        "minute": 68,
        "home_score": 1,
        "away_score": 0,
        "source": "api_football_live",
        "updated_at": "2026-07-26T21:58:00+02:00",
    }


def _timeline() -> list[dict]:
    return [
        {
            "id": "goal-1",
            "type": "goal",
            "label": "Gol",
            "minute": 12,
            "minute_label": "12'",
            "team": "Club Local",
            "player_id": "101",
            "player": "Jugador Uno",
            "source": "api_football",
            "is_key_event": True,
        },
        {
            "id": "red-1",
            "type": "red_card",
            "label": "Tarjeta roja",
            "minute": 64,
            "minute_label": "64'",
            "team": "Union Visitante",
            "player_id": "202",
            "player": "Jugador Dos",
            "source": "api_football",
            "is_key_event": True,
        },
    ]


def _tracker() -> dict:
    return {
        "provider": "api_football",
        "updated_at": "2026-07-26T21:58:00+02:00",
        "quality": {
            "evidence": ["estadisticas", "eventos", "presion"],
        },
        "pressure": {
            "available": True,
            "label": "Club Local presiona",
            "home_pct": 64,
            "away_pct": 36,
            "source": "estadisticas_api_football",
        },
        "field_state": {
            "available": True,
            "headline": "Presion de Club Local",
            "dominant_team": "Club Local",
            "dominant_side": "home",
        },
        "game_flow": {
            "available": True,
            "phase": "Dominio claro",
            "event_count": 2,
            "recent_event_count": 1,
            "latest_minute": 64,
        },
    }


def _statistics() -> dict:
    return {
        "available": True,
        "source": "api_football",
        "updated_at": "2026-07-26T21:58:00+02:00",
        "items": [
            {
                "key": "possession",
                "label": "Posesion",
                "home": "58%",
                "away": "42%",
            },
            {
                "key": "shots_on_goal",
                "label": "Tiros a puerta",
                "home": "6",
                "away": "2",
            },
        ],
    }


def _snapshot(*, stale: bool = False) -> dict:
    lifecycle = {
        "key": "2H",
        "label": "En directo",
        "minute": 68,
        "is_stale": stale,
    }
    return build_match_intelligence(
        _match(),
        [],
        lifecycle=lifecycle,
        score={"home": 1, "away": 0, "label": "1-0", "confirmed": True},
        timeline=_timeline(),
        statistics=_statistics(),
        tracker=_tracker(),
        competition={"id": "140", "name": "Liga Real"},
        observed_at_madrid="2026-07-26T21:58:00+02:00",
    )


def test_match_intelligence_contract_is_structured_and_explainable():
    snapshot = _snapshot()
    expected = {
        "estado_partido",
        "ritmo",
        "presion",
        "dominador",
        "equilibrio",
        "fase",
        "riesgo",
        "eventos_clave",
        "tendencias",
        "cambios_recientes",
    }

    assert snapshot["contract"] == MATCH_INTELLIGENCE_CONTRACT
    assert set(snapshot["conclusions"]) == expected
    for key, conclusion in snapshot["conclusions"].items():
        assert conclusion["key"] == key
        assert "state" in conclusion
        assert "evidence_ids" in conclusion
        assert "missing_information" in conclusion
        assert conclusion["method"]
        assert "limitations" in conclusion

    assert snapshot["conclusions"]["presion"]["state"] == "PARTIALLY_VERIFIED"
    assert snapshot["conclusions"]["dominador"]["value"]["team"] == "Club Local"
    assert snapshot["conclusions"]["riesgo"]["value"]["flags"] == [
        {
            "kind": "red_card_observed",
            "event_id": "red-1",
            "minute_label": "64'",
            "team": "Union Visitante",
        }
    ]
    assert snapshot["conclusions"]["tendencias"]["state"] == "INSUFFICIENT_DATA"
    assert snapshot["conclusions"]["cambios_recientes"]["value"]["count"] == 1
    assert snapshot["quality"]["numeric_confidence_score"] is None
    assert snapshot["quality"]["quality_is_not_sport_probability"] is True
    assert snapshot["no_fake_data"] is True


def test_all_consumers_reuse_one_read_only_snapshot():
    snapshot = _snapshot()

    assert set(snapshot["consumer_contracts"]) == set(
        MATCH_INTELLIGENCE_CONSUMERS
    )
    for consumer in MATCH_INTELLIGENCE_CONSUMERS:
        view = build_match_intelligence_consumer_view(snapshot, consumer)
        assert view == snapshot["consumer_views"][consumer]
        assert view["contract"] == MATCH_INTELLIGENCE_CONTRACT
        assert view["external_action_authorized"] is False
        assert view["database_write_authorized"] is False

    assert snapshot["entity_context"]["entities"]["home_team"]["id"] == "10"
    assert snapshot["entity_context"]["entities"]["competition"]["id"] == "140"
    assert snapshot["entity_context"]["sports_graph_write_authorized"] is False


def test_generic_live_status_uses_confirmed_minute_for_phase():
    snapshot = build_match_intelligence(
        _match(),
        [],
        lifecycle={
            "key": "LIVE",
            "label": "En directo",
            "minute": 68,
            "is_stale": False,
        },
        score={"home": 1, "away": 0, "label": "1-0", "confirmed": True},
        timeline=_timeline(),
        statistics=_statistics(),
        tracker=_tracker(),
        competition={"id": "140", "name": "Liga Real"},
        observed_at_madrid="2026-07-26T21:58:00+02:00",
    )

    phase = snapshot["conclusions"]["fase"]
    assert phase["value"]["key"] == "second_half"
    assert phase["method"] == "confirmed_match_minute"


def test_shark_and_telegram_envelopes_receive_the_same_intelligence():
    snapshot = _snapshot()
    shark_view = build_shark_match_intelligence_state(snapshot)
    shark_envelope = build_assistant_context(
        "shark",
        match_intelligence=snapshot,
        evidence_state=snapshot["certification_state"],
    ).to_dict()
    telegram_envelope = build_assistant_context(
        "telegram",
        match_intelligence=snapshot,
        evidence_state=snapshot["certification_state"],
    ).to_dict()
    presentation = build_shark_context_state(
        {
            "match_intelligence": snapshot,
            "evidence_state": snapshot["certification_state"],
        }
    )

    assert shark_view["available"] is True
    assert shark_view["consumer_view"] == snapshot["consumer_views"]["shark"]
    assert shark_envelope["match_intelligence"] == snapshot
    assert telegram_envelope["match_intelligence"] == snapshot
    assert shark_envelope["external_action_authorized"] is False
    assert telegram_envelope["external_action_authorized"] is False
    assert presentation["context_envelope"]["match_intelligence"] == snapshot

    legacy_context = build_shark_context(
        match=_match(),
        match_intelligence=snapshot,
    )
    product_context = build_product_shark_context(
        {"membership": "PRO"},
        match=_match(),
        match_intelligence=snapshot,
        openai_configured=False,
    )
    answer = answer_shark_question("Que ocurre en el partido", product_context)
    assert legacy_context["match_intelligence"] == snapshot
    assert product_context["match_intelligence"] == snapshot
    assert "Contexto Match Intelligence:" in answer["answer"]
    assert "no es una prediccion" in answer["answer"]


def test_stale_or_missing_inputs_never_become_sporting_intelligence():
    stale = _snapshot(stale=True)
    empty = build_match_intelligence()

    assert stale["certification_state"] == "STALE"
    assert stale["conclusions"]["presion"]["state"] == "STALE"
    assert stale["shark_context"]["available"] is False
    assert empty["certification_state"] == "INSUFFICIENT_DATA"
    assert empty["shark_context"]["available"] is False
    assert all(
        conclusion["state"] == "INSUFFICIENT_DATA"
        for conclusion in empty["conclusions"].values()
    )


def test_engine_has_no_io_or_generative_dependencies():
    source = inspect.getsource(match_intelligence_module)
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )

    assert imported_roots <= {"__future__", "typing"}
    assert "sqlite3" not in source
    assert "requests" not in source
    assert "urlopen" not in source
    assert "openai" not in source.lower()
    assert match_intelligence_snapshot()["diagnostics"] == {
        "external_calls": 0,
        "database_writes": 0,
        "generative_ai_calls": 0,
    }
