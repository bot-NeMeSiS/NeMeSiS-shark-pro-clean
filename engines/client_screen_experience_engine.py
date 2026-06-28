"""V856 client presentation helpers.

Pure presentation layer: no provider calls, no database writes, no invented data.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


SAFE_EMPTY_STATES = {
    "no_real_data": "Sin datos reales",
    "waiting_provider": "Esperando proveedor",
    "no_live": "Sin directos reales",
    "no_picks": "Sin picks activos",
    "pending_odds": "Cuotas pendientes",
    "pending_result": "Resultado pendiente",
    "not_configured": "No configurado",
}

PRIMARY_CLIENT_ROUTES = [
    ("/app", "Inicio"),
    ("/partidos", "Partidos"),
    ("/live", "Directo"),
    ("/picks", "Picks"),
    ("/shark", "SHARK"),
    ("/telegram", "Telegram"),
    ("/profile", "Perfil"),
    ("/support", "Soporte"),
]


@dataclass(frozen=True)
class ClientScreenState:
    route: str
    plan: str
    title: str
    objective: str
    visual_density: str
    primary_ctas: list[dict[str, str]]
    empty_states: dict[str, str]
    mobile_rules: list[str]
    desktop_rules: list[str]
    css_flags: list[str]


def _title_for_route(route: str) -> str:
    titles = {
        "/app": "Centro NeMeSiS",
        "/inicio": "Centro NeMeSiS",
        "/panel-cliente": "Centro NeMeSiS",
        "/partidos": "Partidos",
        "/calendar": "Calendario",
        "/live": "Directo",
        "/directo": "Directo",
        "/picks": "Picks",
        "/shark": "SHARK",
        "/telegram": "Telegram",
        "/profile": "Perfil",
        "/support": "Soporte",
        "/track-record": "Histórico",
    }
    return titles.get(route, "NeMeSiS SHARK PRO")


def build_client_screen_state(route: str = "/app", plan: str = "FREE") -> dict[str, Any]:
    normalized_plan = (plan or "FREE").upper()
    ctas = [
        {"label": "Ver partidos", "href": "/partidos"},
        {"label": "Abrir SHARK", "href": "/shark"},
        {"label": "Conectar Telegram", "href": "/telegram"},
    ]
    if normalized_plan in {"PRO", "ELITE", "ELITE+"}:
        ctas.insert(1, {"label": "Ver picks", "href": "/picks"})
    state = ClientScreenState(
        route=route,
        plan=normalized_plan,
        title=_title_for_route(route),
        objective="Mostrar datos reales, acciones claras y estado premium sin relleno.",
        visual_density="compact-premium",
        primary_ctas=ctas,
        empty_states=SAFE_EMPTY_STATES,
        mobile_rules=[
            "bottom_nav_max_5",
            "safe_area_enabled",
            "cards_compact",
            "no_horizontal_scroll",
            "floating_shark_not_on_shark_page",
        ],
        desktop_rules=[
            "dashboard_grid",
            "shark_context_visible",
            "telegram_value_visible",
            "membership_value_visible",
        ],
        css_flags=["v856-client-premium", f"v856-plan-{normalized_plan.lower()}"],
    )
    return asdict(state)
