"""V845 SHARK AI product assistant.

Local, defensive assistant layer for NeMeSiS SHARK PRO. It does not call
external AI providers by itself; it turns real app context into safe answers.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List


FORBIDDEN_CLAIMS = (
    "garantizado",
    "apuesta segura",
    "seguro al 100",
    "fija",
    "pick fijo",
    "sin riesgo",
)


def _text(value: Any, default: str = "") -> str:
    value = "" if value is None else str(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or default


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except Exception:
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value or default))
    except Exception:
        return default


def _first(*values: Any, default: str = "") -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return default


def _match_title(match: Dict[str, Any]) -> str:
    home = _first(match.get("home_team"), match.get("safe_home"), default="Equipo local")
    away = _first(match.get("away_team"), match.get("safe_away"), default="Equipo visitante")
    return f"{home} vs {away}"


def _pick_title(pick: Dict[str, Any]) -> str:
    home = _first(pick.get("home_team"), default="Equipo local")
    away = _first(pick.get("away_team"), default="Equipo visitante")
    return f"{home} vs {away}"


def _competition(item: Dict[str, Any]) -> str:
    return _first(item.get("competition_name"), item.get("league_name"), item.get("competition"), default="Competición pendiente")


def _time_label(item: Dict[str, Any]) -> str:
    return _first(
        item.get("client_full_datetime_label"),
        item.get("display_datetime"),
        item.get("kickoff_iso"),
        item.get("match_date"),
        default="Hora Madrid pendiente",
    )


def _status_label(item: Dict[str, Any]) -> str:
    return _first(item.get("client_status_label"), item.get("status_label"), item.get("status"), default="Estado pendiente")


def _odds_label(item: Dict[str, Any]) -> str:
    odds = _num(item.get("odds") or item.get("price"), 0)
    return f"{odds:.2f}" if odds > 1 else "Cuotas pendientes"


def _risk_label(item: Dict[str, Any]) -> str:
    return _first(item.get("risk_level"), item.get("risk"), default="Riesgo pendiente")


def build_shark_context(user: Dict[str, Any] | None, match: Dict[str, Any] | None = None, pick: Dict[str, Any] | None = None, page: str | None = None, **extra: Any) -> Dict[str, Any]:
    user = user or {}
    membership = _first(user.get("membership"), user.get("role"), default="FREE").upper()
    context = {
        "user": {
            "id": _text(user.get("id")),
            "name": _first(user.get("name"), user.get("username"), default="Cliente SHARK"),
            "membership": membership,
        },
        "match": match or {},
        "pick": pick or {},
        "page": _text(page, "shark"),
        "recent_picks": list(extra.get("recent_picks") or [])[:8],
        "recent_matches": list(extra.get("recent_matches") or [])[:8],
        "telegram_quality": extra.get("telegram_quality") or {},
        "briefing": extra.get("briefing") or {},
        "openai_configured": bool(extra.get("openai_configured")),
        "fallback_mode": not bool(extra.get("openai_configured")),
    }
    context["data_state"] = build_shark_empty_state(context)
    return context


def explain_match(match: Dict[str, Any] | None) -> str:
    match = match or {}
    if not match:
        return "No hay un partido seleccionado. Puedo ayudarte a revisar partidos, directo o picks publicados."
    title = _match_title(match)
    comp = _competition(match)
    time = _time_label(match)
    status = _status_label(match)
    score = _first(match.get("client_score_label"), match.get("score"), default="")
    parts = [
        f"Partido: {title}",
        f"Competición: {comp}",
        f"Hora Madrid: {time}",
        f"Estado: {status}",
    ]
    if score:
        parts.append(f"Marcador: {score}")
    else:
        parts.append("Marcador: Resultado pendiente")
    parts.append("Lectura SHARK: reviso solo datos disponibles. Si faltan cuota, minuto o estadísticas, no los invento.")
    return "\n".join(parts)


def explain_pick(pick: Dict[str, Any] | None) -> str:
    pick = pick or {}
    if not pick:
        return "No hay pick real seleccionado. Sin pick publicado, SHARK no crea una apuesta artificial."
    selection = _first(pick.get("client_selection_label"), pick.get("selection_display"), pick.get("selection"), default="Selección pendiente")
    market = _first(pick.get("market"), default="Mercado pendiente")
    reason = _first(pick.get("analysis_summary"), pick.get("reasoning"), default="Motivo pendiente en los datos del pick.")
    stake = _first(pick.get("stake_units"), pick.get("stake"), default="Stake pendiente")
    confidence = _first(pick.get("confidence"), pick.get("quality_score"), default="Confianza pendiente")
    return "\n".join([
        f"Pick real: {_pick_title(pick)}",
        f"Mercado: {market}",
        f"Selección: {selection}",
        f"Cuota: {_odds_label(pick)}",
        f"Stake: {stake}",
        f"Confianza: {confidence}",
        f"Riesgo: {_risk_label(pick)}",
        f"Motivo: {reason}",
    ])


def explain_risk(match_or_pick: Dict[str, Any] | None) -> str:
    item = match_or_pick or {}
    risk = _risk_label(item)
    odds = _odds_label(item)
    warnings = [
        f"Riesgo: {risk}.",
        "Ninguna entrada elimina el riesgo.",
        "Si faltan alineaciones, cuota real o contexto suficiente, lo prudente es esperar.",
    ]
    if odds == "Cuotas pendientes":
        warnings.append("La cuota todavía no está confirmada, así que no debe tratarse como entrada cerrada.")
    return " ".join(warnings)


def explain_no_bet_reason(match_or_pick: Dict[str, Any] | None) -> str:
    item = match_or_pick or {}
    reasons = []
    if _odds_label(item) == "Cuotas pendientes":
        reasons.append("cuotas pendientes")
    if not _first(item.get("selection"), item.get("selection_display"), item.get("client_selection_label")):
        reasons.append("sin selección real publicada")
    if not _first(item.get("kickoff_iso"), item.get("match_date"), item.get("client_full_datetime_label")):
        reasons.append("hora no fiable")
    if not reasons:
        reasons.append("faltan evidencias suficientes para elevarlo a entrada premium")
    return "No recomiendo forzar una entrada: " + ", ".join(reasons) + "."


def suggest_next_actions(context: Dict[str, Any]) -> List[Dict[str, str]]:
    actions = [
        {"label": "Ver partidos", "url": "/partidos"},
        {"label": "Ver picks", "url": "/picks"},
        {"label": "Abrir directo", "url": "/live"},
        {"label": "Conectar Telegram", "url": "/telegram"},
        {"label": "Soporte", "url": "/support"},
    ]
    match = context.get("match") or {}
    pick = context.get("pick") or {}
    if match.get("id"):
        actions.insert(0, {"label": "Ver partido", "url": f"/match/{match.get('id')}"})
    if pick.get("match_id"):
        actions.insert(0, {"label": "Partido del pick", "url": f"/match/{pick.get('match_id')}"})
    return actions[:5]


def build_shark_empty_state(context: Dict[str, Any]) -> Dict[str, str]:
    pick = context.get("pick") or {}
    match = context.get("match") or {}
    return {
        "odds": "Cuotas pendientes" if _odds_label(pick or match) == "Cuotas pendientes" else "Cuotas disponibles",
        "pick": "Sin picks activos" if not pick else "Pick real seleccionado",
        "provider": "Esperando proveedor" if not (match or pick) else "Datos reales disponibles parcialmente",
        "result": "Resultado pendiente" if not _first((match or {}).get("client_score_label"), (match or {}).get("score")) else "Resultado disponible",
    }


def sanitize_ai_answer(answer: str) -> str:
    answer = _text(answer)
    replacements = {
        "apuesta segura": "entrada de riesgo controlado",
        "garantizado": "no garantizado",
        "pick fijo": "pick a revisar",
        "sin riesgo": "con riesgo",
    }
    lowered = answer.lower()
    for bad, good in replacements.items():
        if bad in lowered:
            answer = re.sub(re.escape(bad), good, answer, flags=re.IGNORECASE)
            lowered = answer.lower()
    return answer


def enforce_no_invented_data(answer: str, context: Dict[str, Any]) -> str:
    answer = sanitize_ai_answer(answer)
    pick = context.get("pick") or {}
    match = context.get("match") or {}
    guardrails = []
    if _odds_label(pick or match) == "Cuotas pendientes":
        guardrails.append("Cuotas pendientes")
    if not pick:
        guardrails.append("Sin pick real publicado")
    if not _first(match.get("client_score_label"), match.get("score")):
        guardrails.append("Resultado pendiente")
    if guardrails:
        answer += "\n\nDatos no inventados: " + " · ".join(dict.fromkeys(guardrails)) + "."
    if "riesgo" not in answer.lower():
        answer += "\n\nRiesgo: apuesta responsable; no hay resultados asegurados."
    return sanitize_ai_answer(answer)


def _membership_note(membership: str) -> str:
    membership = _text(membership, "FREE").upper()
    if membership == "ELITE" or membership == "ADMIN":
        return "Modo ELITE: lectura más profunda cuando existan datos reales, Telegram prioritario y explicación avanzada sin inventar métricas."
    if membership == "PRO":
        return "Modo PRO: explicación completa de picks, riesgos y próximos pasos."
    return "Modo FREE: lectura básica y clara. Para señales premium, revisa PRO o ELITE sin presión comercial."


def _intent(question: str) -> str:
    q = _text(question).lower()
    if any(x in q for x in ("pick", "apuesta", "pronóstico", "pronostico", "selección", "seleccion")):
        return "pick"
    if any(x in q for x in ("riesgo", "peligro", "no tocar", "evitar")):
        return "risk"
    if any(x in q for x in ("telegram", "canal", "mensaje")):
        return "telegram"
    if any(x in q for x in ("partido", "match", "equipo", "directo", "live")):
        return "match"
    if any(x in q for x in ("plan", "free", "pro", "elite", "membres")):
        return "membership"
    return "summary"


def answer_shark_question(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    question = _text(question, "resumen")
    intent = _intent(question)
    match = context.get("match") or {}
    pick = context.get("pick") or {}
    membership = (context.get("user") or {}).get("membership", "FREE")
    body_parts: List[str] = ["🦈 SHARK responde con datos reales."]
    focus = intent
    if intent == "pick":
        body_parts.append(explain_pick(pick))
        if not pick:
            body_parts.append(explain_no_bet_reason(match))
    elif intent == "risk":
        body_parts.append(explain_risk(pick or match))
        body_parts.append(explain_no_bet_reason(pick or match))
    elif intent == "telegram":
        tq = context.get("telegram_quality") or {}
        if tq:
            status = "apto" if tq.get("allowed") else "bloqueado"
            body_parts.append(f"Telegram V844 lo marcaría como {status}: {_first(tq.get('reason'), tq.get('code'), default='sin motivo técnico visible')}.")
        else:
            body_parts.append("Telegram solo debe enviar contenido top: fútbol relevante, picks reales y sin relleno.")
    elif intent == "match":
        body_parts.append(explain_match(match))
        if pick:
            body_parts.append("Pick relacionado:\n" + explain_pick(pick))
        else:
            body_parts.append(explain_no_bet_reason(match))
    elif intent == "membership":
        body_parts.append(_membership_note(membership))
    else:
        briefing = context.get("briefing") or {}
        summary = briefing.get("summary") or {}
        body_parts.append(
            "Resumen del producto: partidos reales, directo, picks publicados, Telegram y soporte están conectados para ayudarte a decidir con calma."
        )
        if summary:
            body_parts.append(
                f"Hoy: {summary.get('matches_today', 0)} partidos, {summary.get('live_now', 0)} en directo y {summary.get('picks_ready', 0)} picks listos."
            )
        if pick:
            body_parts.append("Pick principal:\n" + explain_pick(pick))
        elif match:
            body_parts.append("Partido seleccionado:\n" + explain_match(match))
        else:
            body_parts.append("No hay contexto específico seleccionado. Puedes abrir un partido o un pick y pedirme una lectura concreta.")
    body_parts.append(_membership_note(membership))
    answer = enforce_no_invented_data("\n\n".join(body_parts), context)
    return {
        "question": question,
        "focus": focus,
        "answer": answer,
        "context": context,
        "risk_note": "SHARK informa y ordena datos; no asegura resultados ni recomienda apostar sin control.",
        "actions": suggest_next_actions(context),
        "next_action": "Revisa el partido, el pick o Telegram antes de decidir. Si faltan datos, espera.",
        "next_url": (suggest_next_actions(context)[0] or {}).get("url", "/app"),
        "legal_policy": "NeMeSiS ofrece análisis deportivo responsable. No hay resultados asegurados.",
        "fallback_mode": bool(context.get("fallback_mode")),
    }


def build_fallback_answer(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    payload = answer_shark_question(question, context)
    payload["answer"] = "Modo análisis interno activo.\n\n" + payload["answer"]
    payload["fallback_mode"] = True
    return payload
