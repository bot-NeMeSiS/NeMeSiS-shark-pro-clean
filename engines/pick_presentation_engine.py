"""V856 pick presentation helpers."""
from __future__ import annotations

from typing import Any


def build_pick_presentation_state(pick: dict[str, Any] | None = None) -> dict[str, Any]:
    if not pick:
        state = "Sin picks activos"
    else:
        state = pick.get("state") or pick.get("status") or "Pick en revisión"
    odds = (pick or {}).get("odds") or (pick or {}).get("price") or "Cuotas pendientes"
    selection = (pick or {}).get("selection") or "Selección pendiente"
    return {
        "state": state,
        "selection_label": selection,
        "odds_label": odds,
        "risk_label": (pick or {}).get("risk") or "Riesgo pendiente de datos reales",
        "cta_shark": "Explicar con SHARK",
        "cta_match": "Ver partido",
        "buckets": ["Listos", "En revisión", "Archivados", "Liga baja relevancia"],
        "css_flags": ["v856-pick-card", "v856-pick-quality"],
    }
