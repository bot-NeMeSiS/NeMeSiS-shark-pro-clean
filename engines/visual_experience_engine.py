"""Global client visual membership experience checks for NeMeSiS SHARK PRO V736.

This engine is read-only. It does not change memberships, send Telegram messages,
charge users, or inspect secrets. It verifies that the global visual system is
present and that critical client/admin templates are covered by the premium skin.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATIC_CSS = ROOT / "static" / "app.css"
BASE_TEMPLATE = ROOT / "templates" / "base.html"

THEMES = {
    "FREE": {
        "name": "Ocean Blue",
        "primary": "#22d3ff",
        "accent": "#2f6bff",
        "description": "Azul limpio para empezar con la misma información esencial.",
    },
    "PRO": {
        "name": "Cyber Green",
        "primary": "#2ef28f",
        "accent": "#16a34a",
        "description": "Verde premium para usuarios activos y picks PRO.",
    },
    "ELITE": {
        "name": "Golden Shark",
        "primary": "#f7c65d",
        "accent": "#d69a16",
        "description": "Dorado de máximo valor para análisis avanzado.",
    },
    "ELITE+": {
        "name": "Neon Purple",
        "primary": "#c45cff",
        "accent": "#7c3aed",
        "description": "Morado ultra premium para administración, pruebas y futuras capas superiores.",
    },
}

CRITICAL_CLIENT_TEMPLATES = [
    "home.html",
    "sports_hub.html",
    "live.html",
    "calendar.html",
    "picks.html",
    "combis.html",
    "favorites.html",
    "match_detail.html",
    "match_hub.html",
    "team_detail.html",
    "shark.html",
    "telegram.html",
    "profile.html",
    "membership.html",
    "track_record.html",
    "client_success.html",
]

REQUIRED_CSS_MARKERS = [
    "V736 Global Client Visual Membership Experience",
    "ns-tier-free",
    "ns-tier-pro",
    "ns-tier-elite",
    "ns-tier-eliteplus",
    "--tier-primary",
    "--tier-gradient",
    "tier-badge",
    "membership-energy-bar",
    "v736-visual-grid",
]

REQUIRED_BASE_MARKERS = [
    "ns-app",
    "ns-tier-{{ _visual_tier }}",
    "tier-badge",
    "membership-energy-bar",
    "ns-main-shell",
]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except Exception:
        return ""


def _status(ok: bool) -> str:
    return "OK" if ok else "REVISAR"


def visual_experience_snapshot(app_version: str = "") -> dict[str, Any]:
    css = _read(STATIC_CSS)
    base = _read(BASE_TEMPLATE)
    template_dir = ROOT / "templates"

    css_checks = [
        {"marker": marker, "ok": marker in css, "status": _status(marker in css)}
        for marker in REQUIRED_CSS_MARKERS
    ]
    base_checks = [
        {"marker": marker, "ok": marker in base, "status": _status(marker in base)}
        for marker in REQUIRED_BASE_MARKERS
    ]
    template_checks = []
    for name in CRITICAL_CLIENT_TEMPLATES:
        path = template_dir / name
        text = _read(path)
        extends_base = '{% extends "base.html" %}' in text or "{% extends 'base.html' %}" in text
        template_checks.append(
            {
                "template": name,
                "exists": path.exists(),
                "extends_base": extends_base,
                "covered_by_global_skin": bool(path.exists() and extends_base),
                "status": _status(path.exists() and extends_base),
            }
        )

    total_checks = len(css_checks) + len(base_checks) + len(template_checks)
    ok_checks = sum(1 for item in css_checks + base_checks if item["ok"]) + sum(
        1 for item in template_checks if item["covered_by_global_skin"]
    )
    score = round((ok_checks / total_checks) * 100) if total_checks else 0

    risks = []
    if score < 90:
        risks.append("Algún marcador visual global o plantilla crítica necesita revisión.")
    if not all(item["ok"] for item in css_checks):
        risks.append("CSS global V736 incompleto.")
    if not all(item["ok"] for item in base_checks):
        risks.append("Base global sin todos los anclajes de membresía.")

    return {
        "version": app_version,
        "score": score,
        "status": "GLOBAL_VISUAL_READY" if score >= 95 else "VISUAL_REVIEW_NEEDED",
        "summary": "Sistema visual global por membresía activo para las pantallas que extienden base.html.",
        "themes": THEMES,
        "css_checks": css_checks,
        "base_checks": base_checks,
        "template_checks": template_checks,
        "covered_templates": sum(1 for item in template_checks if item["covered_by_global_skin"]),
        "total_templates": len(template_checks),
        "risks": risks,
        "safe_scope": [
            "No cambia lógica de picks.",
            "No toca Cron ni Telegram.",
            "No modifica pagos ni membresías reales.",
            "No expone secrets.",
            "Solo añade capa visual global, admin QA y checks.",
        ],
        "next_steps": [
            "Probar V736 en móvil real con FREE, PRO y ELITE.",
            "Revisar capturas de Live, Picks, Calendar, Match Detail, SHARK y Perfil.",
            "Ajustar microespacios solo si alguna pantalla queda cargada o demasiado grande.",
        ],
    }
