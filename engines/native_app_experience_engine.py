"""Native app feel and microinteraction checks for NeMeSiS SHARK PRO V737.

Read-only engine. It verifies that the global premium visual layer is enhanced
with app-like navigation, active states, microinteractions, touch polish and
mobile-safe UI without changing business logic, memberships, Telegram, Cron or payments.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATIC_CSS = ROOT / "static" / "app.css"
BASE_TEMPLATE = ROOT / "templates" / "base.html"

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

REQUIRED_BASE_MARKERS = [
    "data-ns-route",
    "data-ns-plan",
    "ns-route-glow",
    "nsScrollTop",
    "nsToastHost",
    "nsAppEnhance",
    "is-active",
    "ns-ready",
]

REQUIRED_CSS_MARKERS = [
    "V737 Native App Feel",
    "ns-route-glow",
    "is-active",
    "ns-scroll-top",
    "ns-toast-host",
    "ns-touch",
    "is-loading",
    "safe-area-inset-bottom",
    "prefers-reduced-motion",
    "touch-action:manipulation",
]

EXPERIENCE_PILLARS = [
    {
        "name": "Navegación activa",
        "description": "El cliente sabe siempre en qué pantalla está gracias a estados activos en nav superior e inferior.",
    },
    {
        "name": "Sensación app nativa",
        "description": "Microinteracciones de pulsación, estados de carga y scroll rápido sin tocar lógica crítica.",
    },
    {
        "name": "Móvil premium",
        "description": "Mejor soporte para zonas seguras, navegación inferior y pantallas pequeñas.",
    },
    {
        "name": "Accesibilidad visual",
        "description": "Respeta reduced-motion, mejora focus-visible y evita animaciones invasivas.",
    },
    {
        "name": "Consistencia por membresía",
        "description": "Mantiene FREE, PRO, ELITE y ELITE+ con la energía visual global de V736.",
    },
]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except Exception:
        return ""


def _status(ok: bool) -> str:
    return "OK" if ok else "REVISAR"


def native_app_experience_snapshot(app_version: str = "") -> dict[str, Any]:
    css = _read(STATIC_CSS)
    base = _read(BASE_TEMPLATE)
    template_dir = ROOT / "templates"

    base_checks = [
        {"marker": marker, "ok": marker in base, "status": _status(marker in base)}
        for marker in REQUIRED_BASE_MARKERS
    ]
    css_checks = [
        {"marker": marker, "ok": marker in css, "status": _status(marker in css)}
        for marker in REQUIRED_CSS_MARKERS
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
                "covered_by_native_app_feel": bool(path.exists() and extends_base),
                "status": _status(path.exists() and extends_base),
            }
        )

    all_checks = base_checks + css_checks
    total_checks = len(all_checks) + len(template_checks)
    ok_checks = sum(1 for item in all_checks if item["ok"]) + sum(
        1 for item in template_checks if item["covered_by_native_app_feel"]
    )
    score = round((ok_checks / total_checks) * 100) if total_checks else 0

    risks = []
    if score < 95:
        risks.append("La capa app-feel necesita revisar algún marcador CSS/base o plantilla crítica.")
    if "window.nsToast" not in base:
        risks.append("Sistema de avisos visuales no detectado.")
    if "aria-current" not in base:
        risks.append("Estados activos de navegación sin aria-current detectado.")
    if "prefers-reduced-motion" not in css:
        risks.append("Reduced-motion no está cubierto en CSS.")

    return {
        "version": app_version,
        "score": score,
        "status": "NATIVE_APP_FEEL_READY" if score >= 95 else "APP_FEEL_REVIEW_NEEDED",
        "summary": "Capa global V737 para que la app se sienta más nativa, rápida, clara y premium sin tocar la lógica.",
        "pillars": EXPERIENCE_PILLARS,
        "base_checks": base_checks,
        "css_checks": css_checks,
        "template_checks": template_checks,
        "covered_templates": sum(1 for item in template_checks if item["covered_by_native_app_feel"]),
        "total_templates": len(template_checks),
        "risks": risks,
        "safe_scope": [
            "No cambia picks, cuotas ni selección de apuestas.",
            "No toca Telegram, Cron ni webhooks.",
            "No activa pagos reales ni cambia membresías.",
            "No modifica DB_PATH ni secrets.",
            "Solo añade experiencia visual/app-feel, admin QA y checks.",
        ],
        "next_steps": [
            "Probar V737 en móvil real con FREE, PRO y ELITE.",
            "Revisar navegación activa en Inicio, Directo, Picks, Combi, Perfil y Más.",
            "Validar que los formularios muestran carga sin bloquear flujos legítimos.",
        ],
    }
