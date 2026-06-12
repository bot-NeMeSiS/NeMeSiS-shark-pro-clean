"""Standings/deep data experience foundation."""
from __future__ import annotations


def standings_snapshot(rows: list[dict] | None = None) -> dict:
    rows = rows or []
    return {
        "ok": True,
        "status": "STANDINGS_FOUNDATION_READY" if rows else "PENDIENTE_SINCRONIZACION",
        "rows": rows[:40],
        "message": "Clasificación basada en fuente sincronizada." if rows else "Datos pendientes de sincronización.",
        "no_fake_data": True,
    }
