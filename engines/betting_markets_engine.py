"""Client-safe betting markets and combi experience helpers for NeMeSiS SHARK PRO.

This module is intentionally pure-Python and read-only. It does not call external APIs,
charge payments, send Telegram messages, or write to the production database.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Tuple

BASIC_MARKETS: List[Dict[str, Any]] = [
    {
        "key": "1x2",
        "label": "1X2",
        "title": "Ganador del partido",
        "client_label": "Local / Empate / Visitante",
        "description": "El mercado más básico: eliges si gana el local, hay empate o gana el visitante.",
        "risk": "Medio",
        "plan": "FREE",
        "examples": ["Local gana", "Empate", "Visitante gana"],
        "combi_use": "Muy útil para combis simples si la cuota y la lectura son claras.",
    },
    {
        "key": "double_chance",
        "label": "Doble oportunidad",
        "title": "Dos resultados cubiertos",
        "client_label": "1X / X2 / 12",
        "description": "Cubre dos de los tres resultados posibles. Suele ser más prudente que 1X2.",
        "risk": "Bajo-Medio",
        "plan": "PRO",
        "examples": ["1X", "X2", "12"],
        "combi_use": "Buena para combis controladas cuando no buscamos una cuota enorme.",
    },
    {
        "key": "dnb",
        "label": "Empate no apuesta",
        "title": "DNB / Draw No Bet",
        "client_label": "Gana equipo · empate devuelve",
        "description": "Si el partido acaba empate, normalmente la apuesta queda nula según la casa.",
        "risk": "Medio",
        "plan": "PRO",
        "examples": ["Local empate no apuesta", "Visitante empate no apuesta"],
        "combi_use": "Útil para proteger combis cuando hay favorito pero el empate preocupa.",
    },
    {
        "key": "over_under_15",
        "label": "Más/Menos 1.5 goles",
        "title": "Línea básica de goles",
        "client_label": "+1.5 / -1.5 goles",
        "description": "Mercado sencillo de goles. Más 1.5 necesita al menos 2 goles en total.",
        "risk": "Bajo-Medio",
        "plan": "FREE",
        "examples": ["Más de 1.5 goles", "Menos de 1.5 goles"],
        "combi_use": "Mercado muy entendible para combis prudentes si el partido acompaña.",
    },
    {
        "key": "over_under_25",
        "label": "Más/Menos 2.5 goles",
        "title": "Línea principal de goles",
        "client_label": "+2.5 / -2.5 goles",
        "description": "Más 2.5 necesita 3 goles o más. Menos 2.5 gana con 0, 1 o 2 goles.",
        "risk": "Medio",
        "plan": "PRO",
        "examples": ["Más de 2.5 goles", "Menos de 2.5 goles"],
        "combi_use": "Buena para combis mixtas, pero no conviene mezclar demasiadas líneas agresivas.",
    },
    {
        "key": "btts",
        "label": "Ambos marcan",
        "title": "Los dos equipos anotan",
        "client_label": "Sí / No",
        "description": "Apuestas a si ambos equipos marcarán al menos un gol.",
        "risk": "Medio-Alto",
        "plan": "ELITE",
        "examples": ["Ambos marcan: Sí", "Ambos marcan: No"],
        "combi_use": "Solo para combis pequeñas o cuando SHARK detecte contexto favorable.",
    },
]

_MARKET_ALIASES: List[Tuple[str, str]] = [
    ("btts|ambos marcan|both teams|marcan ambos", "btts"),
    ("over 2.5|over2.5|más de 2.5|mas de 2.5|+2.5|alta 2.5", "over_under_25"),
    ("under 2.5|menos de 2.5|-2.5|baja 2.5", "over_under_25"),
    ("over 1.5|más de 1.5|mas de 1.5|+1.5", "over_under_15"),
    ("under 1.5|menos de 1.5|-1.5", "over_under_15"),
    ("draw no bet|dnb|empate no apuesta|sin empate", "dnb"),
    ("double chance|doble oportunidad|1x|x2|12", "double_chance"),
    ("h2h|1x2|match winner|ganador|gana|empate|local|visitante", "1x2"),
]


def _txt(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return _txt(value).lower()


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except Exception:
        return default


def market_family_from_text(*parts: Any) -> str:
    text = " ".join(_norm(p) for p in parts if p is not None)
    if not text:
        return "unknown"
    for pattern, key in _MARKET_ALIASES:
        if re.search(pattern, text):
            return key
    return "unknown"


def market_catalog(plan: str = "FREE") -> List[Dict[str, Any]]:
    plan = _txt(plan).upper() or "FREE"
    rank = {"FREE": 0, "PRO": 1, "ELITE": 2, "ELITE+": 3, "ADMIN": 3}.get(plan, 0)
    result = []
    for item in BASIC_MARKETS:
        required = item.get("plan") or "FREE"
        needed = {"FREE": 0, "PRO": 1, "ELITE": 2, "ELITE+": 3, "ADMIN": 3}.get(required, 0)
        enriched = dict(item)
        enriched["available"] = rank >= needed
        enriched["locked_reason"] = "" if enriched["available"] else f"Disponible desde {required}"
        result.append(enriched)
    return result


def enrich_pick_market_context(pick: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(pick or {})
    key = market_family_from_text(item.get("market"), item.get("pick_type"), item.get("selection"), item.get("reasoning"))
    catalog = {m["key"]: m for m in BASIC_MARKETS}
    meta = catalog.get(key, {})
    odds = _float(item.get("odds"), 0.0)
    confidence = _int(item.get("confidence"), 50)
    item["v765_market_key"] = key
    item["v765_market_label"] = meta.get("label") or "Mercado pendiente"
    item["v765_market_title"] = meta.get("title") or "Mercado pendiente de confirmar"
    item["v765_client_market_summary"] = (
        f"{meta.get('label')} · {meta.get('client_label')}" if meta else "Mercado pendiente de confirmar"
    )
    item["v765_has_clear_market"] = key != "unknown"
    item["v765_has_odds"] = odds > 1.0
    item["v765_ready_for_combi"] = bool(key != "unknown" and odds > 1.0 and confidence >= 55)
    item["v765_combi_warning"] = "" if item["v765_ready_for_combi"] else (
        "Falta mercado claro, cuota real o confianza suficiente para meterlo en combi."
    )
    return item


def _safe_pick_title(pick: Dict[str, Any]) -> str:
    home = _txt(pick.get("client_home") or pick.get("home_team") or pick.get("safe_home"))
    away = _txt(pick.get("client_away") or pick.get("away_team") or pick.get("safe_away"))
    if home and away:
        return f"{home} vs {away}"
    return _txt(pick.get("client_match_label") or pick.get("match") or "Partido pendiente")


def build_combi_strategy_context(picks: Iterable[Dict[str, Any]], matches: Iterable[Dict[str, Any]] = (), requested_count: int = 3) -> Dict[str, Any]:
    enriched = [enrich_pick_market_context(dict(p or {})) for p in (picks or [])]
    ready = [p for p in enriched if p.get("v765_ready_for_combi")]
    one_x_two = [p for p in ready if p.get("v765_market_key") == "1x2"]
    goals = [p for p in ready if p.get("v765_market_key") in {"over_under_15", "over_under_25", "btts"}]
    safer = [p for p in ready if p.get("v765_market_key") in {"double_chance", "dnb", "over_under_15"}]
    requested_count = max(2, min(_int(requested_count, 3), 15))

    def _legs(source: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
        return [{
            "id": p.get("id"),
            "match": _safe_pick_title(p),
            "selection": _txt(p.get("client_selection_label") or p.get("selection_display") or p.get("selection") or "Selección pendiente"),
            "market": p.get("v765_market_label") or "Mercado",
            "odds": _float(p.get("odds"), 0.0),
            "confidence": _int(p.get("confidence"), 0),
            "warning": p.get("v765_combi_warning") or "",
        } for p in source[:n]]

    strategies = [
        {
            "key": "1x2_controlada",
            "title": "Combi 1X2 controlada",
            "label": "Básica",
            "description": "Combina selecciones sencillas de ganador/empate solo cuando haya cuota real y confianza suficiente.",
            "legs": _legs(one_x_two, min(requested_count, 4)),
            "risk": "Medio",
            "href": "/combis?tipo=1x2&partidos=3",
        },
        {
            "key": "goles_basica",
            "title": "Combi de goles básica",
            "label": "Goles",
            "description": "Mezcla +1.5, +2.5 o ambos marcan solo si SHARK tiene contexto real; no fuerza mercados.",
            "legs": _legs(goals, min(requested_count, 4)),
            "risk": "Medio-Alto",
            "href": "/combis?tipo=goles&partidos=3",
        },
        {
            "key": "mixta_responsable",
            "title": "Combi mixta responsable",
            "label": "Mixta",
            "description": "Prioriza doble oportunidad, DNB, +1.5 y 1X2 con pocas selecciones y stake bajo.",
            "legs": _legs((safer + one_x_two + goals), requested_count),
            "risk": "Controlado" if requested_count <= 3 else "Medio",
            "href": f"/combis?tipo=mixta&partidos={requested_count}",
        },
    ]
    for s in strategies:
        s["available_legs"] = len(s["legs"])
        s["ready"] = s["available_legs"] >= 2
        total = 1.0
        for leg in s["legs"]:
            total *= leg["odds"] if leg["odds"] > 1 else 1
        s["total_odds_preview"] = round(total, 2) if total > 1 else 0
        if not s["ready"]:
            s["empty_message"] = "Aún no hay suficientes picks reales con mercado y cuota para esta combi."
    return {
        "requested_count": requested_count,
        "published_picks": len(enriched),
        "ready_picks": len(ready),
        "markets": {
            "1x2": len(one_x_two),
            "goals": len(goals),
            "safer": len(safer),
        },
        "strategies": strategies,
        "notice": "Las combis solo usan picks reales ya publicados. Si falta cuota, mercado o confianza, queda en estudio.",
        "responsible_note": "Combis largas = más riesgo. SHARK recomienda pocas selecciones, stake bajo y no perseguir pérdidas.",
    }


def build_betting_markets_snapshot(picks: Iterable[Dict[str, Any]] = (), matches: Iterable[Dict[str, Any]] = (), plan: str = "FREE") -> Dict[str, Any]:
    enriched = [enrich_pick_market_context(dict(p or {})) for p in (picks or [])]
    counts = {m["key"]: 0 for m in BASIC_MARKETS}
    unknown = 0
    for p in enriched:
        key = p.get("v765_market_key") or "unknown"
        if key in counts:
            counts[key] += 1
        else:
            unknown += 1
    ready = [p for p in enriched if p.get("v765_has_clear_market") and p.get("v765_has_odds")]
    study = [p for p in enriched if not p.get("v765_has_clear_market") or not p.get("v765_has_odds")]
    return {
        "catalog": market_catalog(plan),
        "counts": counts,
        "unknown": unknown,
        "ready_count": len(ready),
        "study_count": len(study),
        "matches_count": len(list(matches or [])) if not isinstance(matches, list) else len(matches),
        "ready_picks": ready[:10],
        "study_picks": study[:10],
        "client_message": "Mercados básicos claros: 1X2, doble oportunidad, DNB, goles y ambos marcan. Sin cuota real, se avisa; no se inventa.",
    }
