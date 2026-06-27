"""Presentation helpers for V855 membership value across the app.

This module does not change payments, users, sessions or entitlements. It only
describes how each plan should be presented safely in UI and reports.
"""
from __future__ import annotations


SAFE_LOCKED_COPY = {
    "free": "Disponible en PRO",
    "pro": "Disponible en ELITE",
    "elite": "Incluido en ELITE",
    "eliteplus": "Acceso prioritario",
    "admin": "Command center total",
}


def normalize_plan(plan: str | None) -> str:
    value = (plan or "FREE").strip().upper()
    if value in {"ELITE+", "ELITE_PLUS"}:
        return "eliteplus"
    if value == "ADMIN":
        return "admin"
    if value == "ELITE":
        return "elite"
    if value == "PRO":
        return "pro"
    return "free"


def build_membership_value(plan: str | None = None) -> dict:
    key = normalize_plan(plan)
    matrix = build_membership_experience_matrix()
    return matrix.get(key, matrix["free"])


def build_membership_experience_matrix() -> dict:
    return {
        "free": {
            "label": "FREE",
            "tone": "entrada útil",
            "accent": "cyan",
            "summary": "Acceso inicial a partidos, estados reales y SHARK básico sin datos inventados.",
            "unlocks": ["Partidos", "Directo", "Estados reales", "SHARK básico"],
            "cta": "Subir a PRO",
            "locked_copy": SAFE_LOCKED_COPY["free"],
        },
        "pro": {
            "label": "PRO",
            "tone": "valor premium",
            "accent": "blue",
            "summary": "Más SHARK, mejores explicaciones de picks y Telegram como canal de avisos top.",
            "unlocks": ["Picks explicados", "Telegram premium", "Track record", "Soporte prioritario"],
            "cta": "Ver ELITE",
            "locked_copy": SAFE_LOCKED_COPY["pro"],
        },
        "elite": {
            "label": "ELITE",
            "tone": "experiencia top",
            "accent": "gold",
            "summary": "Lectura avanzada con SHARK, señales de más calidad y mayor contexto de proveedor real.",
            "unlocks": ["SHARK avanzado", "Telegram top", "Análisis ampliado", "Prioridad visual"],
            "cta": "Mantener ELITE",
            "locked_copy": SAFE_LOCKED_COPY["elite"],
        },
        "eliteplus": {
            "label": "ELITE+",
            "tone": "máxima prioridad",
            "accent": "platinum",
            "summary": "Capa máxima de producto para acceso prioritario y profundidad cuando hay datos reales.",
            "unlocks": ["Acceso prioritario", "Contexto completo", "Soporte máximo", "SHARK profundo"],
            "cta": "Gestionar ELITE+",
            "locked_copy": SAFE_LOCKED_COPY["eliteplus"],
        },
        "admin": {
            "label": "ADMIN",
            "tone": "command center",
            "accent": "cyan",
            "summary": "Control total de datos, Telegram, SHARK, usuarios, pagos, runtime y automatización.",
            "unlocks": ["Datos", "Telegram", "SHARK", "Usuarios", "Pagos", "Master tick"],
            "cta": "Abrir command center",
            "locked_copy": SAFE_LOCKED_COPY["admin"],
        },
    }


def build_locked_feature_state(required_plan: str, current_plan: str | None = None) -> dict:
    current = normalize_plan(current_plan)
    required = normalize_plan(required_plan)
    return {
        "current_plan": build_membership_value(current)["label"],
        "required_plan": build_membership_value(required)["label"],
        "state": SAFE_LOCKED_COPY.get(current, "Disponible al mejorar el plan"),
        "safe_copy": "Desbloquea análisis avanzado cuando haya datos reales suficientes.",
    }
