"""V741 calendar/search experience QA engine.

This module is intentionally read-only and dependency-light. It checks that the
client calendar has the pieces needed for a premium match discovery experience
without touching data providers, Telegram, payments or memberships.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_TEMPLATE_MARKERS = {
    "templates/calendar.html": [
        "calendar-command-center",
        "calendar-search-form",
        "calendar-date-rail",
        "calendar-league-rail",
        "calendar-day-group",
        "calendar-match-card",
        "calendar-crest",
        "calendar-empty-state",
    ],
    "static/app.css": [
        "V741 CALENDAR SEARCH EXPERIENCE PERFECTION",
        ".calendar-command-center",
        ".calendar-search-grid",
        ".calendar-match-card",
        ".calendar-team-name",
        ".calendar-competition-pill",
        ".calendar-mobile-safe",
    ],
    "app.py": [
        "calendar_experience_data",
        "_calendar_apply_filters",
        "_calendar_group",
        "@app.route(\"/partidos\")",
        "@app.route(\"/api/calendar\")",
    ],
}

SELL_READY_POINTS = [
    "Pantalla Partidos convertida en calendario buscable.",
    "Filtros por día, liga, equipo, país, directo, favoritos y picks.",
    "Agrupación por fecha y competición con prioridad de ligas.",
    "Escudos/fallbacks protegidos en tarjetas de calendario.",
    "Textos de competición pasan por castellano.",
    "CSS anti-solape para nombres largos, ligas y móvil.",
]


def _read(relative: str) -> str:
    path = ROOT / relative
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")
    except Exception:
        return ""


def calendar_experience_snapshot(app_version: str = "") -> dict:
    checks = []
    missing_total = 0
    for relative, markers in REQUIRED_TEMPLATE_MARKERS.items():
        content = _read(relative)
        missing = [marker for marker in markers if marker not in content]
        missing_total += len(missing)
        checks.append({
            "file": relative,
            "ok": not missing,
            "missing": missing,
            "markers_checked": len(markers),
        })
    score = max(0, 100 - missing_total * 8)
    if missing_total == 0:
        status = "CALENDARIO_PREMIUM_LISTO"
    elif score >= 75:
        status = "CALENDARIO_REVISAR_DETALLES"
    else:
        status = "CALENDARIO_INCOMPLETO"
    return {
        "version": app_version,
        "status": status,
        "score": score,
        "checks": checks,
        "sell_ready_points": SELL_READY_POINTS,
        "notes": [
            "No llama APIs externas ni inventa partidos; trabaja sobre la base local sincronizada.",
            "La validación visual final debe hacerse en móvil y Render real con datos reales.",
        ],
    }
