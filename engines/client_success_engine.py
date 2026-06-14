"""Client success/onboarding readiness helpers for NeMeSiS SHARK PRO.

Read-only helpers used by V733. They do not send Telegram, do not write to the
DB and do not require Flask. The goal is to make the client journey clear:
partidos, directo, picks, combis, SHARK, Telegram, soporte and responsible play.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

VERSION = "V733_CLIENT_SUCCESS_ONBOARDING_SUPPORT_POLISH"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except Exception:
        return default


def _project_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root).resolve()
    return Path(__file__).resolve().parents[1]


def _template_exists(root: Path, name: str) -> bool:
    return (root / "templates" / name).exists()


def _static_success_checks(root: Path) -> dict:
    templates = {
        "client_success": _template_exists(root, "client_success.html"),
        "admin_client_success": _template_exists(root, "admin_client_success.html"),
        "onboarding": _template_exists(root, "onboarding.html"),
        "support": _template_exists(root, "support.html"),
        "telegram": _template_exists(root, "telegram.html"),
        "sports_hub": _template_exists(root, "sports_hub.html"),
        "calendar": _template_exists(root, "calendar.html"),
        "live": _template_exists(root, "live.html"),
        "picks": _template_exists(root, "picks.html"),
        "combis": _template_exists(root, "combis.html"),
        "shark": _template_exists(root, "shark.html"),
    }
    css = root / "static" / "app.css"
    css_text = ""
    try:
        css_text = css.read_text(encoding="utf-8-sig")
    except Exception:
        pass
    return {
        "templates": templates,
        "css": {
            "exists": css.exists(),
            "client_success_layer": "V733 Client Success" in css_text,
            "mobile_media": "@media" in css_text and "max-width" in css_text,
            "bottom_nav": ".bottom-nav" in css_text,
            "shark_widget": ".shark-widget" in css_text,
        },
    }


def client_success_snapshot(stats: dict | None = None, root: str | Path | None = None) -> dict:
    stats = dict(stats or {})
    project = _project_root(root)
    membership = str(stats.get("membership") or "FREE").upper()
    favorites_count = _safe_int(stats.get("favorites_count"))
    picks_visible = _safe_int(stats.get("picks_visible"))
    live_count = _safe_int(stats.get("live_count"))
    upcoming_count = _safe_int(stats.get("upcoming_count"))
    telegram_configured = bool(stats.get("telegram_configured"))
    telegram_football_only = bool(stats.get("telegram_football_only", True))
    madrid_time_ready = bool(stats.get("madrid_time_ready", True))
    support_ready = bool(stats.get("support_ready", True))

    pillars = [
        {
            "key": "matches",
            "title": "Partidos y calendario",
            "status": "OK" if upcoming_count > 0 else "PREPARANDO",
            "value": upcoming_count,
            "label": "próximos detectados",
            "body": "Calendario en hora Madrid con filtros Hoy, Mañana, Semana, Favoritos y Con pick.",
            "href": "/calendar",
            "cta": "Ver calendario",
        },
        {
            "key": "live",
            "title": "Directo y resultados",
            "status": "OK" if live_count > 0 else "EN ESPERA",
            "value": live_count,
            "label": "directos ahora",
            "body": "Si hay partido en vivo, SHARK muestra minuto, marcador y estado sin inventar datos.",
            "href": "/live",
            "cta": "Abrir directo",
        },
        {
            "key": "picks",
            "title": "Picks premium",
            "status": "OK" if picks_visible > 0 else "EN ESTUDIO",
            "value": picks_visible,
            "label": "picks visibles",
            "body": "Solo se muestran como premium señales con selección clara y cuota real.",
            "href": "/picks",
            "cta": "Ver picks",
        },
        {
            "key": "combis",
            "title": "Combis inteligentes",
            "status": "LISTO",
            "value": 15,
            "label": "máximo selecciones",
            "body": "Combi prudente, media y larga con aviso de riesgo y stake responsable.",
            "href": "/combis",
            "cta": "Crear combi",
        },
        {
            "key": "shark",
            "title": "SHARK AI Advisor",
            "status": "LISTO",
            "value": "PRO",
            "label": "asesor activo",
            "body": "Preguntas rápidas para interpretar picks, value, directo, favoritos y qué no tocar.",
            "href": "/shark",
            "cta": "Preguntar",
        },
        {
            "key": "telegram",
            "title": "Telegram PRO",
            "status": "CONFIGURADO" if telegram_configured else "POR CONECTAR",
            "value": "Fútbol" if telegram_football_only else "Mixto",
            "label": "modo activo",
            "body": "Alertas de fútbol, resumen diario y picks sin cuotas pendientes ni ruido técnico.",
            "href": "/telegram",
            "cta": "Conectar Telegram",
        },
    ]

    next_actions = []
    if not madrid_time_ready:
        next_actions.append({"priority": "crítica", "title": "Revisar horarios Madrid", "href": "/calendar"})
    if upcoming_count <= 0:
        next_actions.append({"priority": "alta", "title": "Revisar partidos de hoy", "href": "/sports-hub"})
    if picks_visible <= 0:
        next_actions.append({"priority": "media", "title": "Consultar picks en estudio", "href": "/picks"})
    if favorites_count <= 0:
        next_actions.append({"priority": "media", "title": "Añadir favoritos", "href": "/favorites"})
    if not telegram_configured:
        next_actions.append({"priority": "alta", "title": "Conectar Telegram", "href": "/telegram"})
    if not next_actions:
        next_actions.append({"priority": "ok", "title": "Revisar el directo y picks de hoy", "href": "/sports-hub"})

    static = _static_success_checks(project)
    static_score = sum(1 for ok in static["templates"].values() if ok) + sum(1 for ok in static["css"].values() if ok)
    static_max = len(static["templates"]) + len(static["css"])
    journey_score = 55
    journey_score += 8 if madrid_time_ready else -20
    journey_score += 8 if support_ready else -10
    journey_score += min(8, upcoming_count // 5)
    journey_score += 5 if live_count > 0 else 0
    journey_score += 8 if picks_visible > 0 else 0
    journey_score += 6 if favorites_count > 0 else 0
    journey_score += 8 if telegram_configured else 0
    journey_score += round((static_score / max(1, static_max)) * 12)
    journey_score = max(0, min(100, journey_score))

    return {
        "version": VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "membership": membership,
        "score": journey_score,
        "status": "OK" if journey_score >= 80 else ("REVISAR" if journey_score >= 60 else "ATENCIÓN"),
        "pillars": pillars,
        "next_actions": next_actions[:5],
        "stats": {
            "favorites_count": favorites_count,
            "picks_visible": picks_visible,
            "live_count": live_count,
            "upcoming_count": upcoming_count,
            "telegram_configured": telegram_configured,
            "telegram_football_only": telegram_football_only,
            "madrid_time_ready": madrid_time_ready,
            "support_ready": support_ready,
        },
        "static_checks": static,
        "support_channels": [
            {"title": "Partidos o calendario", "body": "Indica equipo, competición y hora visible en la app."},
            {"title": "Telegram", "body": "Indica última hora recibida, canal o mensaje privado, sin compartir secrets."},
            {"title": "Picks y combis", "body": "Indica partido, selección, cuota y si aparece en premium o estudio."},
            {"title": "Cuenta", "body": "Indica plan actual, acceso y pantalla donde se produce el problema."},
        ],
        "responsible_note": "NeMeSiS SHARK PRO ofrece análisis deportivo y señales de valor; no garantiza resultados.",
    }
