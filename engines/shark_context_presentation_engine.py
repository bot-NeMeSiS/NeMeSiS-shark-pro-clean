"""V856 SHARK context presentation helpers."""
from __future__ import annotations

from typing import Any


FORBIDDEN_BETTING_PROMISES = ["seguro", "fijo", "garantizado", "sin riesgo", "apuesta segura"]


def build_shark_context_state(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    return {
        "title": "SHARK",
        "mode": "Análisis interno",
        "data_state": context.get("data_state") or "No hay datos suficientes",
        "safe_answer_hint": "No recomiendo forzar una entrada sin datos suficientes.",
        "next_actions": [
            {"label": "Ver partidos", "href": "/partidos"},
            {"label": "Ver picks", "href": "/picks"},
            {"label": "Conectar Telegram", "href": "/telegram"},
            {"label": "Soporte", "href": "/support"},
        ],
        "forbidden_promises": FORBIDDEN_BETTING_PROMISES,
        "css_flags": ["v856-shark-star", "v856-shark-safe-ai"],
    }
