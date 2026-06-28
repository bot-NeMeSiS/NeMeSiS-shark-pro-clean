"""V856 Telegram presentation helpers."""
from __future__ import annotations

from typing import Any


def build_telegram_presentation_state(configured: bool = False, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = summary or {}
    return {
        "configured": bool(configured),
        "status_label": "Conectado" if configured else "No configurado",
        "last_send": summary.get("last_send") or "Sin envíos registrados",
        "quality_policy": "Solo contenido top, sin relleno",
        "blocked_reason_label": "Descartado por baja calidad" if summary.get("blocked") else "Sin descartes registrados",
        "cta": "Conectar Telegram" if not configured else "Ver canal premium",
        "css_flags": ["v856-telegram-premium", "v856-no-filler"],
    }
