"""Betting Recommendation Engine for NeMeSiS SHARK PRO.

Genera recomendaciones desde datos reales persistidos: partidos proximos,
cuotas cacheadas y picks publicados. No inventa picks reales: produce analisis
pre-pick que el admin puede convertir en pick publicado.
"""
from __future__ import annotations

from datetime import datetime


def _to_float(value, default=0.0):
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _to_int(value, default=0):
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return default


def _norm(value):
    return str(value or "").strip()


def pick_best_market(match: dict, odds: dict | None = None) -> dict:
    """Devuelve seleccion sugerida basada en cuotas reales si existen.

    Sin cuotas, devuelve WATCHLIST: analisis, no pick real.
    """
    home = _norm(match.get("home_team"))
    away = _norm(match.get("away_team"))
    odds = odds or {}
    options = []
    for key, label in (("home_price", home), ("draw_price", "Empate"), ("away_price", away)):
        price = _to_float(odds.get(key), 0)
        if price > 1.01:
            options.append((price, label, key))
    if not options:
        return {
            "market": "Análisis pre-pick",
            "selection": "Esperar cuotas confirmadas",
            "odds": 0.0,
            "bookmaker": "",
            "source": "calendar",
            "has_real_odds": False,
        }
    # Preferir cuota de valor razonable, evitando extremos muy bajos o altos.
    options.sort(key=lambda item: (abs(item[0] - 1.85), item[0]))
    price, label, key = options[0]
    return {
        "market": "1X2",
        "selection": label,
        "odds": round(price, 2),
        "bookmaker": odds.get("bookmaker") or "The Odds API",
        "source": odds.get("source") or "odds_cache",
        "has_real_odds": True,
        "price_key": key,
    }


def score_recommendation(match: dict, selection: dict, live_state: str = "UPCOMING") -> dict:
    priority = _to_int(match.get("priority"), 50)
    odds = _to_float(selection.get("odds"), 0)
    has_odds = bool(selection.get("has_real_odds"))
    status = _norm(match.get("status") or match.get("live_state") or live_state).upper()
    finished = status in {"FT", "FINAL", "FINALIZADO", "FINISHED"}
    live = status in {"LIVE", "DIRECTO", "1H", "2H", "HT", "DESCANSO"}
    base = 48 + min(22, max(0, priority - 55) / 2)
    if has_odds:
        if 1.55 <= odds <= 2.35:
            base += 18
        elif 1.25 <= odds < 1.55:
            base += 7
        elif 2.35 < odds <= 3.2:
            base += 9
        else:
            base -= 7
    else:
        base -= 12
    if live:
        base -= 10
    if finished:
        base = 0
    confidence = max(1, min(96, round(base)))
    if confidence >= 74 and has_odds:
        risk = "BAJO"
    elif confidence >= 60:
        risk = "MEDIO"
    else:
        risk = "ALTO"
    value = "HOT" if confidence >= 78 and has_odds else "VALUE" if has_odds and confidence >= 64 else "WATCHLIST"
    return {"score": confidence, "confidence": confidence, "risk_level": risk, "badge": value}


def build_reasoning(match: dict, selection: dict, score: dict) -> tuple[str, str]:
    league = _norm(match.get("competition_name") or match.get("league_name") or "competición")
    date = _norm(match.get("match_date") or match.get("kickoff_iso") or "fecha por confirmar")
    if selection.get("has_real_odds"):
        reason = (
            f"Recomendación pre-pick basada en partido próximo real de {league}, "
            f"cuota cacheada {selection.get('odds')} y prioridad interna del calendario. "
            f"Revisar once, bajas y movimiento de cuota antes de publicar."
        )
    else:
        reason = (
            f"Partido real detectado para {date} en {league}, pero aún sin cuota cacheada suficiente. "
            "Se marca como seguimiento para que SHARK/Odds lo analicen antes de convertirlo en pick."
        )
    warning = (
        "No es garantía de beneficio. Validar cuota actual, estado del partido y stake antes de apostar. "
        "Si el partido está live o finalizado no debe publicarse como pick prepartido."
    )
    if score.get("risk_level") == "ALTO":
        warning = "Riesgo alto: usar stake bajo o esperar confirmación adicional de cuota/equipo. " + warning
    return reason, warning


def recommendation_payload(match: dict, odds: dict | None = None, live_state: str = "UPCOMING") -> dict:
    selection = pick_best_market(match, odds)
    score = score_recommendation(match, selection, live_state=live_state)
    reason, warning = build_reasoning(match, selection, score)
    return {
        "match_id": match.get("id") or "",
        "league_name": match.get("competition_name") or match.get("league_name") or "",
        "home_team": match.get("home_team") or "",
        "away_team": match.get("away_team") or "",
        "match_date": match.get("match_date") or "",
        "kickoff_time": match.get("kickoff_time") or match.get("match_time") or "",
        "status": match.get("status") or live_state,
        "market": selection["market"],
        "selection": selection["selection"],
        "odds": selection["odds"],
        "bookmaker": selection.get("bookmaker") or "",
        "source": selection.get("source") or "betting_engine",
        "has_real_odds": bool(selection.get("has_real_odds")),
        "confidence": score["confidence"],
        "score": score["score"],
        "risk_level": score["risk_level"],
        "badge": score["badge"],
        "reasoning": reason,
        "warning_reason": warning,
        "membership_required": "PRO" if score["confidence"] >= 72 else "FREE",
        "created_at": datetime.utcnow().isoformat(timespec="seconds"),
    }
