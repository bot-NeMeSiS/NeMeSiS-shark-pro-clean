"""V758 adaptive desktop/mobile experience helpers.

Pure presentation/data shaping. Does not touch Telegram, Cron, DB_PATH or external APIs.
"""
from __future__ import annotations
from typing import Any

MOBILE_MARKERS = ("iphone", "android", "mobile", "opera mini", "windows phone")
TABLET_MARKERS = ("ipad", "tablet", "kindle", "silk")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _txt(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _num(value: Any, fallback: int = 0) -> int:
    try:
        return int(float(str(value or "0").replace(",", ".")))
    except Exception:
        return fallback


def infer_device(user_agent: str = "", viewport: str = "") -> dict[str, Any]:
    ua = str(user_agent or "").lower()
    width = 0
    try:
        width = int(str(viewport or "").split("x", 1)[0] or 0)
    except Exception:
        width = 0
    if any(m in ua for m in TABLET_MARKERS) or (760 <= width <= 1180):
        kind = "tablet"
    elif any(m in ua for m in MOBILE_MARKERS) or (width and width < 760):
        kind = "mobile"
    else:
        kind = "desktop"
    return {
        "kind": kind,
        "is_mobile": kind == "mobile",
        "is_tablet": kind == "tablet",
        "is_desktop": kind == "desktop",
        "label": {"mobile": "Móvil", "tablet": "Tablet", "desktop": "PC"}.get(kind, "Adaptativo"),
        "density": "compacta" if kind == "mobile" else "amplia" if kind == "desktop" else "equilibrada",
        "nav_hint": "barra inferior y tarjetas táctiles" if kind == "mobile" else "panel ancho, tablas y acciones visibles" if kind == "desktop" else "vista híbrida táctil",
    }


def _counts(data: dict[str, Any]) -> dict[str, Any]:
    hub = _dict(data.get("match_hub"))
    counts = _dict(hub.get("counts"))
    picks = _list(data.get("picks"))
    return {
        "today": counts.get("today", counts.get("upcoming", "—")),
        "live": counts.get("live", "—"),
        "picks": len(picks) if picks else counts.get("picks", "—"),
        "favorites": counts.get("favorites", "—"),
    }


def build_v758_adaptive_experience(data: dict[str, Any] | None = None, user: dict[str, Any] | None = None, path: str = "", user_agent: str = "", viewport: str = "") -> dict[str, Any]:
    data = _dict(data)
    user = _dict(user)
    device = infer_device(user_agent, viewport)
    counts = _counts(data)
    plan = _txt(user.get("membership") or user.get("role"), "FREE").upper()
    path = _txt(path, "/")
    is_mobile = device["kind"] == "mobile"
    quick_actions = [
        {"label": "Inicio", "href": "/app", "badge": "Centro", "icon": "⌂"},
        {"label": "Partidos", "href": "/calendar?lane=today", "badge": "Hoy", "icon": "📅"},
        {"label": "Directo", "href": "/live", "badge": "Live", "icon": "⚡"},
        {"label": "Picks", "href": "/picks", "badge": "SHARK", "icon": "🎯"},
        {"label": "Histórico", "href": "/track-record", "badge": "Real", "icon": "📊"},
        {"label": "Telegram", "href": "/telegram", "badge": "Auto", "icon": "✈️"},
    ]
    pc_layout = [
        {"title": "Panel ancho", "body": "KPIs, tabla de partidos y acciones visibles sin hacer scroll excesivo.", "status": "Activo"},
        {"title": "Comparación rápida", "body": "Picks, calendario, directo y track record conectados en filas claras.", "status": "PC"},
        {"title": "Menos ruido", "body": "La interfaz prioriza datos reales y oculta lo técnico al cliente.", "status": "Pro"},
    ]
    mobile_layout = [
        {"title": "Tarjetas táctiles", "body": "Botones grandes, barra inferior y foco en una acción por pantalla.", "status": "Activo"},
        {"title": "Scroll limpio", "body": "Bloques compactos para consultar picks y partidos rápido desde el móvil.", "status": "Móvil"},
        {"title": "Acceso rápido", "body": "Inicio, partidos, directo y picks siempre a un toque.", "status": "App"},
    ]
    recommendations = mobile_layout if is_mobile else pc_layout
    return {
        "version_tag": "V758_ADAPTIVE_DESKTOP_MOBILE_TOP_APP_EXPERIENCE",
        "device": device,
        "mode_label": f"Modo {device['label']}",
        "device_hint": device["nav_hint"],
        "headline": "Experiencia adaptativa PC/Móvil",
        "subtitle": "NeMeSiS ajusta densidad, navegación, tarjetas y lectura según el dispositivo sin tocar Telegram ni datos reales.",
        "plan": plan,
        "current_path": path,
        "counts": counts,
        "kpis": [
            {"label": "Modo", "value": device["label"], "hint": device["density"], "href": "/experiencia"},
            {"label": "Partidos", "value": counts["today"], "hint": "agenda", "href": "/calendar"},
            {"label": "Directo", "value": counts["live"], "hint": "en vivo", "href": "/live"},
            {"label": "Picks", "value": counts["picks"], "hint": "señales", "href": "/picks"},
        ],
        "quick_actions": quick_actions,
        "recommendations": recommendations,
        "pc_layout": pc_layout,
        "mobile_layout": mobile_layout,
        "safe_note": "No se inventan picks, marcadores ni ROI. La capa V758 solo mejora cómo se ve y se navega.",
    }


def build_v758_device_api_payload(data: dict[str, Any] | None = None, user: dict[str, Any] | None = None, path: str = "", user_agent: str = "", viewport: str = "") -> dict[str, Any]:
    adaptive = build_v758_adaptive_experience(data=data, user=user, path=path, user_agent=user_agent, viewport=viewport)
    return {
        "adaptive": adaptive,
        "device": adaptive.get("device"),
        "quick_actions": adaptive.get("quick_actions", []),
        "recommendations": adaptive.get("recommendations", []),
    }
