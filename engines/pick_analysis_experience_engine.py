"""Client-facing pick analysis helpers for NeMeSiS SHARK PRO.

This module does not invent statistics. It turns the fields already present in a
pick (selection, market, odds, confidence, SHARK quality, risk and notes) into a
clear Spanish explanation that the client can understand.
"""
from __future__ import annotations

import re
from typing import Any


def _text(value: Any, default: str = "") -> str:
    return str(value if value is not None else default).strip()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).replace("%", "").strip()))
    except Exception:
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", ".").strip())
    except Exception:
        return default


def _clean_sentence(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    if text[-1:] not in ".!?":
        text += "."
    return text


def detect_selection_team(pick: dict[str, Any]) -> str:
    """Return the team explicitly favoured by the selection when it is clear."""
    home = _text(pick.get("home_team"), "Equipo local")
    away = _text(pick.get("away_team"), "Equipo visitante")
    selection = _text(pick.get("selection_display") or pick.get("selection") or pick.get("_raw_selection"))
    selection_norm = selection.lower()
    for team in (home, away):
        if team and team.lower() in selection_norm:
            return team
    if selection_norm.startswith("gana "):
        return selection[5:].strip()
    if selection_norm in {"local", "home", "1"}:
        return home
    if selection_norm in {"visitante", "away", "2"}:
        return away
    return ""


def pick_analysis_payload(pick: dict[str, Any]) -> dict[str, Any]:
    pick = dict(pick or {})
    home = _text(pick.get("home_team"), "Equipo local")
    away = _text(pick.get("away_team"), "Equipo visitante")
    competition = _text(pick.get("competition_name") or pick.get("league_name"), "Competición")
    selection = _text(pick.get("selection_display") or pick.get("selection"), "Selección pendiente")
    market = _text(pick.get("market") or pick.get("pick_type"), "Mercado principal")
    confidence = _int(pick.get("confidence"), 0)
    quality = _int(pick.get("quality_score") or pick.get("shark_score") or confidence, confidence)
    odds = _float(pick.get("odds"), 0.0)
    risk = _text(pick.get("risk_level"), "Medio").upper()
    stake = _text(pick.get("stake_units"), "1")
    favoured = detect_selection_team(pick)

    original_reason = _clean_sentence(pick.get("reasoning") or pick.get("reason") or pick.get("analysis_reason"))
    warning = _clean_sentence(pick.get("warning_reason") or pick.get("risk_reason"))

    reasons: list[str] = []
    if original_reason and "datos disponibles" not in original_reason.lower():
        reasons.append(original_reason)
    if favoured:
        reasons.append(
            f"SHARK encuentra más argumentos a favor de {favoured} dentro del mercado seleccionado, sin tratarlo como apuesta segura."
        )
    else:
        reasons.append(
            f"La selección se apoya en el mercado {market.lower()} para el partido {home} vs {away}."
        )
    if confidence >= 85:
        reasons.append(f"La confianza del modelo es alta ({confidence}%), por encima del umbral normal de publicación.")
    elif confidence >= 70:
        reasons.append(f"La confianza del modelo es buena ({confidence}%), pero requiere stake controlado.")
    elif confidence > 0:
        reasons.append(f"La confianza es moderada ({confidence}%); conviene leer el riesgo antes de entrar.")
    if quality >= 85:
        reasons.append(f"La calidad SHARK del pick es fuerte ({quality}/100) por coherencia entre selección, cuota y riesgo.")
    elif quality >= 65:
        reasons.append(f"La calidad SHARK es correcta ({quality}/100), suficiente para estudio o entrada prudente.")
    if odds > 1:
        reasons.append(f"La cuota real disponible es {odds:g}; no se muestra como premium si la cuota está pendiente.")
    if stake:
        reasons.append(f"El stake sugerido es {stake}u para mantener control de banca.")

    # Deduplicate while preserving order.
    deduped: list[str] = []
    seen = set()
    for reason in reasons:
        key = reason.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(reason)

    risks: list[str] = []
    if warning:
        risks.append(warning)
    if risk in {"ALTO", "HIGH", "AGRESIVO"}:
        risks.append("Riesgo alto: solo tendría sentido con stake mínimo o como parte de una estrategia muy controlada.")
    elif risk in {"BAJO", "LOW", "CONTROLADO"}:
        risks.append("Riesgo más controlado, pero nunca garantizado: el fútbol puede cambiar por un gol, roja o rotaciones.")
    else:
        risks.append("Riesgo medio: entrada razonable solo si respetas stake y no persigues pérdidas.")
    if odds <= 1:
        risks.append("Cuota pendiente o no confirmada: no debe tratarse como entrada cerrada hasta verla en mercado real.")

    headline = (
        f"SHARK favorece {selection} porque la señal combina mercado, confianza y control de riesgo."
        if selection and selection != "Selección pendiente"
        else "SHARK mantiene esta señal en revisión hasta tener selección cerrada."
    )
    if favoured:
        headline = f"SHARK ve a {favoured} mejor posicionado para esta lectura, con entrada recomendada: {selection}."

    conclusion = (
        f"Conclusión: entrada válida solo con cuota confirmada, stake {stake}u y gestión responsable. "
        f"Si la cuota cambia mucho o falta información, mejor esperar."
    )
    if risk in {"ALTO", "HIGH", "AGRESIVO"}:
        conclusion = "Conclusión: pick agresivo. Puede tener valor, pero no es para stake alto ni para recuperar pérdidas."
    elif odds <= 1:
        conclusion = "Conclusión: esperar. Sin cuota real confirmada, SHARK no debería vender este pick como definitivo."

    return {
        "favoured_team": favoured,
        "analysis_headline": headline,
        "analysis_summary": headline,
        "analysis_reasons": deduped[:5],
        "analysis_risks": risks[:3],
        "analysis_conclusion": conclusion,
        "analysis_badge": "Fuerte" if quality >= 85 else ("Controlado" if quality >= 65 else "En estudio"),
        "analysis_context": f"{competition} · {home} vs {away} · {market}",
    }


def enrich_pick_analysis(pick: dict[str, Any]) -> dict[str, Any]:
    item = dict(pick or {})
    item.update(pick_analysis_payload(item))
    if not item.get("reasoning"):
        item["reasoning"] = item.get("analysis_headline") or "Lectura SHARK disponible."
    return item
