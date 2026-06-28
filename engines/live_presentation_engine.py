"""V856 live presentation helpers."""
from __future__ import annotations

from typing import Any


def build_live_presentation_state(matches: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    live_matches = matches or []
    return {
        "count": len(live_matches),
        "title": "Directo",
        "empty_state": "" if live_matches else "Sin directos reales ahora mismo",
        "provider_state": "Datos cacheados o esperando proveedor",
        "ordering": ["en_directo", "top_competition", "hora_madrid"],
        "card_labels": {
            "status": "En directo",
            "minute_missing": "Minuto no disponible",
            "score_missing": "Resultado pendiente",
        },
        "css_flags": ["v856-live-strip", "v856-live-card"],
    }
