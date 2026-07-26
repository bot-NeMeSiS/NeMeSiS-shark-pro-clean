"""V856 SHARK context presentation helpers."""
from __future__ import annotations

from typing import Any

from engines.sports_platform_contracts import build_assistant_context


FORBIDDEN_BETTING_PROMISES = ["seguro", "fijo", "garantizado", "sin riesgo", "apuesta segura"]


def build_shark_context_state(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    envelope = build_assistant_context(
        "shark",
        match_context=context.get("match_context"),
        sports_metrics=context.get("sports_metrics"),
        evidence_state=context.get("evidence_state") or "REQUIRES_REVIEW",
        limitations=context.get("limitations") or [],
    )
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
        "context_envelope": envelope.to_dict(),
        "css_flags": ["v856-shark-star", "v856-shark-safe-ai"],
    }
