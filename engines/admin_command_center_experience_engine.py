"""V856 admin command center presentation helpers."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


ADMIN_SECTIONS = [
    ("Sistema", "/api/runtime-version", "Estado del sistema"),
    ("Datos", "/admin/data-center", "API-SPORTS, The Odds API y sincronización"),
    ("Telegram", "/admin/telegram/command-center", "Filtro premium, dedupe y no filler"),
    ("SHARK", "/admin/shark-ai", "IA, fallback y reglas anti-invención"),
    ("Automatización", "/admin/daily-automation", "Master tick, cron y health-check"),
    ("Usuarios", "/admin/users", "Clientes y sesiones"),
    ("Membresías", "/admin/memberships", "Planes y límites"),
    ("Pagos", "/admin/payments", "Pagos y estados"),
]


@dataclass(frozen=True)
class AdminCommandCenterState:
    title: str
    sections: list[dict[str, str]]
    blocked_client_ui: list[str]
    safe_states: list[str]
    css_flags: list[str]


def build_admin_command_center_state() -> dict[str, Any]:
    state = AdminCommandCenterState(
        title="Command Center",
        sections=[{"label": label, "href": href, "description": description} for label, href, description in ADMIN_SECTIONS],
        blocked_client_ui=["bottom-nav", "floating-shark", "client-scroll-top"],
        safe_states=["No configurado", "Ultimo sync no disponible", "Sin errores registrados", "Accion pendiente"],
        css_flags=["v856-admin-command-center", "v856-admin-dense-grid"],
    )
    return asdict(state)
