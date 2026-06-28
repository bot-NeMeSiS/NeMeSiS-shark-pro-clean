"""V856 match presentation helpers."""
from __future__ import annotations

from typing import Any


def _value(match: dict[str, Any] | None, *names: str) -> Any:
    if not match:
        return None
    for name in names:
        value = match.get(name)
        if value not in (None, "", "None", "null", "undefined"):
            return value
    return None


def build_match_presentation_state(match: dict[str, Any] | None = None) -> dict[str, Any]:
    status = _value(match, "status_label", "status") or "Esperando proveedor"
    score = _value(match, "score", "score_label") or "Resultado pendiente"
    minute = _value(match, "minute", "elapsed") or "Minuto no disponible"
    has_real_pick = bool(_value(match, "pick_id", "has_pick", "real_pick"))
    return {
        "status_label": status,
        "score_label": score,
        "minute_label": minute,
        "cta_detail": "Ver partido",
        "cta_shark": "Analizar con SHARK",
        "cta_pick": "Ver pick" if has_real_pick else "Sin pick real publicado",
        "empty_state": "Esperando proveedor" if not match else "",
        "css_flags": ["v856-match-card", "v856-real-data-state"],
    }
