
"""SHARK Intelligence Core — V570.

Capa defensiva y persistente para convertir SHARK en copiloto del ecosistema.
No llama APIs externas directamente: usa datos ya cacheados en SQLite/app.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Iterable, List


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value or default))
    except Exception:
        return default


def score_from_signals(signals: Dict[str, Any]) -> int:
    """Score SHARK simple, transparente y no engañoso.

    No pretende ser predicción garantizada. Resume calidad de datos/contexto.
    """
    score = 45
    if signals.get("has_odds"):
        score += 15
    if signals.get("has_live"):
        score += 8
    if signals.get("has_recommendations"):
        score += 12
    if signals.get("has_picks"):
        score += 10
    if signals.get("has_favorites"):
        score += 5
    if signals.get("priority_competition"):
        score += 5
    return max(0, min(100, score))


def classify_priority(score: int) -> str:
    if score >= 82:
        return "ALTA"
    if score >= 65:
        return "MEDIA"
    return "BAJA"


def build_quick_questions(membership: str = "FREE") -> List[Dict[str, str]]:
    base = [
        {"label": "Pick de hoy", "question": "¿Qué pick ves mejor hoy?"},
        {"label": "Favoritos", "question": "¿Qué partidos de mis favoritos juegan?"},
        {"label": "Live", "question": "Resume el live"},
        {"label": "Oportunidades", "question": "Dime oportunidades de hoy"},
    ]
    if str(membership or "").upper() in {"PRO", "ELITE", "ADMIN"}:
        base.append({"label": "Riesgo", "question": "Ordéname picks por riesgo y confianza"})
    if str(membership or "").upper() in {"ELITE", "ADMIN"}:
        base.append({"label": "Combinada", "question": "Hazme una combinada segura"})
    return base


def build_daily_briefing(
    favorites: Iterable[Dict[str, Any]] = (),
    recommendations: Iterable[Dict[str, Any]] = (),
    picks: Iterable[Dict[str, Any]] = (),
    live_matches: Iterable[Dict[str, Any]] = (),
    upcoming: Iterable[Dict[str, Any]] = (),
    membership: str = "FREE",
) -> Dict[str, Any]:
    favorites = list(favorites or [])
    recommendations = list(recommendations or [])
    picks = list(picks or [])
    live_matches = list(live_matches or [])
    upcoming = list(upcoming or [])

    top_rec = recommendations[0] if recommendations else None
    top_pick = picks[0] if picks else None
    highlighted = top_pick or top_rec or (upcoming[0] if upcoming else None)

    signals = {
        "has_odds": any((r.get("odds") or r.get("odds_home") or r.get("price")) for r in recommendations),
        "has_live": bool(live_matches),
        "has_recommendations": bool(recommendations),
        "has_picks": bool(picks),
        "has_favorites": bool(favorites),
        "priority_competition": any(str((m.get("competition_name") or m.get("league_name") or "")).lower() in {
            "laliga", "premier league", "uefa champions league", "serie a", "bundesliga", "ligue 1"
        } for m in upcoming[:10]),
    }
    score = score_from_signals(signals)

    if top_pick:
        main_message = "Hay picks publicados para revisar hoy."
    elif top_rec:
        main_message = "SHARK ha detectado oportunidades para analizar."
    elif live_matches:
        main_message = "Hay partidos en directo que merecen seguimiento."
    elif upcoming:
        main_message = "Hay próximos partidos preparados para análisis."
    else:
        main_message = "SHARK está esperando datos deportivos suficientes para generar análisis útil."

    return {
        "generated_at": now_iso(),
        "membership": str(membership or "FREE").upper(),
        "score": score,
        "priority": classify_priority(score),
        "main_message": main_message,
        "top_pick": top_pick,
        "top_recommendation": top_rec,
        "highlighted_match": highlighted,
        "counts": {
            "favorites": len(favorites),
            "recommendations": len(recommendations),
            "picks": len(picks),
            "live": len(live_matches),
            "upcoming": len(upcoming),
        },
        "quick_questions": build_quick_questions(membership),
        "signals": signals,
    }


def memory_event_payload(event_type: str, context: Dict[str, Any] | None = None) -> str:
    return json.dumps({"event_type": event_type, "context": context or {}, "created_at": now_iso()}, ensure_ascii=False)
