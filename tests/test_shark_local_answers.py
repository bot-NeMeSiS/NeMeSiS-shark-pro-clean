import pytest

from engines.shark_ai_product_assistant_engine import build_shark_context, answer_shark_question
from engines.shark_local_answers import intent


@pytest.mark.parametrize("question,focus", [("partidos en directo", "live"), ("live matches", "live"), ("matchs en direct", "live"), ("mis favoritos", "favorites"), ("my favorites", "favorites"), ("mes favoris", "favorites"), ("riesgo del pronóstico", "risk"), ("mi plan", "membership"), ("my membership", "membership"), ("mon abonnement", "membership"), ("calendario", "agenda"), ("fixtures", "agenda"), ("problema", "summary")])
def test_intents_are_functional_and_do_not_match_pro_inside_problem(question, focus):
    assert intent(question) == focus


@pytest.mark.parametrize("locale,question,expected", [("es", "plan", "Tu plan efectivo: PRO"), ("en", "my plan", "Your effective plan: PRO"), ("fr", "mon offre", "Votre offre effective : PRO")])
def test_plan_reads_effective_limits_and_postadmission_usage_once(locale, question, expected):
    context = build_shark_context({"membership": "PRO"}, locale=locale, openai_configured=True,
        plan={"membership": "PRO", "limits": {"daily_picks": 8, "combi_matches": 3}, "usage": {"used": 1, "limit": 20, "remaining": 19}})
    response = answer_shark_question(question, context)
    assert expected in response["answer"] and response["answer"].count(expected) == 1
    assert "1/20" in response["answer"] and "19" in response["answer"]
    assert response["execution_source"] == "LOCAL" and response["external_calls"] == 0
    assert response["fallback_mode"] is True and context["fallback_mode"] is True
    assert response["generation_enabled"] is False and response["external_verification"] == "NOT_RUN"


def _live(**changes):
    frame = {"contract": "NEMESIS-REALTIME-STATE-V1", "is_live": True, "is_stale": False, "status_conflict": False,
             "score_home": 0, "score_away": 0, "minute": 0}
    frame.update(changes)
    return {"id": "qa-live", "home_team": "QA Norte", "away_team": "QA Sur", "realtime_state": frame}


def test_live_preserves_real_zero_and_missing_minute_without_filling():
    context = build_shark_context({}, collections={"live": {"state": "AVAILABLE", "matches": [_live()], "total": 1}})
    response = answer_shark_question("directo", context)
    assert response["focus"] == "live" and "0–0" in response["answer"] and "Minuto confirmado: 0" in response["answer"]
    context["collections"]["live"]["matches"] = [_live(minute=None)]
    assert "Minuto confirmado: Pendiente" in answer_shark_question("directo", context)["answer"]


@pytest.mark.parametrize("changes", [{"is_stale": True}, {"status_conflict": True}, {"is_live": False}, {"contract": "UNKNOWN"}])
def test_stale_unverified_or_conflicting_rows_never_become_a_live_answer(changes):
    row = _live(**changes)
    row["home_team"] = "DO_NOT_PRESENT_AS_LIVE"
    context = build_shark_context({}, collections={"live": {"state": "AVAILABLE", "matches": [row], "total": 1}})
    answer = answer_shark_question("directo", context)["answer"]
    assert "DO_NOT_PRESENT_AS_LIVE" not in answer and "Directos confirmados en esta lectura: 1" not in answer
    assert "No se ha podido confirmar" in answer


@pytest.mark.parametrize("state,copy", [("UNAVAILABLE", "No se ha podido confirmar"), ("EMPTY", "Todavía no tienes favoritos"), ("NO_MATCHES", "Tus favoritos están guardados")])
def test_favorite_empty_unavailable_and_no_fixtures_are_distinct(state, copy):
    context = build_shark_context({}, collections={"favorites": {"state": state, "matches": [], "total": None}})
    assert copy in answer_shark_question("favoritos", context)["answer"]


def test_missing_recorded_pick_fields_do_not_become_normalization_defaults():
    context = build_shark_context({"membership": "PRO"}, pick={"id": "qa-pick", "reasoning": "QA recorded reason"})
    answer = answer_shark_question("pronóstico", context)["answer"]
    assert "Stake registrado (unidades): Pendiente" in answer
    assert "Índice interno registrado (no probabilidad de acierto): Pendiente" in answer
    assert "Riesgo registrado: Pendiente" in answer
    assert "QA recorded reason" in answer


def test_missing_summary_counts_are_not_reported_as_zero():
    context = build_shark_context({}, briefing={"summary": {"snapshot_id": "qa-only"}})
    answer = answer_shark_question("resumen", context)["answer"]
    assert "0 partidos" not in answer and "0 en directo" not in answer


def test_summary_uses_established_collection_totals_without_missing_count_defaults():
    context = build_shark_context({}, collections={"agenda": {"state": "AVAILABLE", "total": 18}, "live": {"state": "UNAVAILABLE", "total": None}})
    answer = answer_shark_question("resumen", context)["answer"]
    assert "Partidos disponibles en esta lectura: 18" in answer and "Directos confirmados" not in answer


@pytest.mark.parametrize("pair,expected", [((2, 1), "2–1"), ((2, None), "Pendiente")])
def test_selected_match_and_live_never_resurrect_conflicting_display_score(pair, expected):
    row = _live(score_home=pair[0], score_away=pair[1], status_canonical="LIVE")
    row.update(score="9-9", client_score_label="9-9")
    context = build_shark_context({}, match=row, collections={"live": {"state": "AVAILABLE", "matches": [row], "total": 1}})
    for question in ("este partido", "directo"):
        answer = answer_shark_question(question, context)["answer"]
        assert "Marcador: " + expected in answer and "9-9" not in answer


@pytest.mark.parametrize("locale,question,heading,closing", [("en", "this match", "Match Intelligence context:", "not a prediction"), ("fr", "ce match", "Contexte Match Intelligence :", "pas un pronostic")])
def test_selected_match_intelligence_localizes_constructed_copy(locale, question, heading, closing):
    intelligence = {"contract": "MATCH-INTELLIGENCE-EVIDENCE-V1", "conclusions": {"fase": {"state": "VERIFIED", "value": {"key": "second_half"}}}}
    row = _live(status_canonical="LIVE")
    context = build_shark_context({}, locale=locale, match=row, match_intelligence=intelligence)
    answer = answer_shark_question(question, context)["answer"]
    assert heading in answer and closing in answer
    assert "Cada lectura" not in answer and "Contexto Match Intelligence:" not in answer
    assert "Estado registrado" not in answer and "En directo" not in answer
