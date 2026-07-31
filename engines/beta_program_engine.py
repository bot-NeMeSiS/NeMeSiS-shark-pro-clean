"""Closed beta feedback and metrics contracts for NeMeSiS.

The Beta Program layer is not a sports module and not an AI system. It defines
privacy-first feedback collection, reproducible bug reports, feature requests,
satisfaction signals and transparent beta metrics. It never calls external
providers, sends Telegram, uses Stripe, deploys, pushes or modifies production.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
BETA_PROGRAM_CONTRACT = "NEMESIS-BETA-PROGRAM-V1"
FEEDBACK_PLATFORM_CONTRACT = "NEMESIS-FEEDBACK-PLATFORM-V1"
BETA_METRICS_CONTRACT = "NEMESIS-BETA-METRICS-V1"

FEEDBACK_TYPES = {
    "bug": "Bug reproducible",
    "feature_request": "Solicitud de mejora",
    "satisfaction": "Satisfacci?n",
    "general": "Feedback general",
}

FEEDBACK_CATEGORIES = {
    "home": "Inicio",
    "calendar": "Calendario",
    "match_center": "Centro de partido",
    "team_center": "Centro de equipo",
    "competition_center": "Centro de competici?n",
    "player_center": "Centro de jugador",
    "shark": "SHARK",
    "telegram": "Telegram",
    "memberships": "Membres?as",
    "action_platform": "Action Platform",
    "user_intelligence": "Inteligencia de usuario",
    "mobile": "M?vil",
    "account": "Cuenta",
    "support": "Soporte",
    "other": "Otro",
}

SEVERITIES = {
    "low": "Baja",
    "medium": "Media",
    "high": "Alta",
    "blocking": "Bloqueante",
}

DEVICES = {
    "desktop": "Desktop",
    "tablet": "Tablet",
    "mobile": "M?vil",
    "unknown": "No indicado",
}

SENSITIVE_RE = re.compile(
    r"(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})"
    r"|(?:\b(?:password|contrasena|contrase.a|token|api[_ -]?key|secret|stripe|card|tarjeta|cvv|telefono|tel.fono)\b)"
    r"|(?:\+?\d[\d\s().-]{7,}\d)"
    r"|(?:\b\d[\d\s-]{12,}\d\b)",
    re.IGNORECASE,
)

CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def madrid_now() -> str:
    return datetime.now(MADRID).isoformat(timespec="seconds")


def clean_text(value: Any, limit: int = 600) -> str:
    text = str(value or "")
    text = CONTROL_RE.sub(" ", text)
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def choice(value: Any, allowed: Mapping[str, str], default: str) -> str:
    candidate = clean_text(value, 80).lower()
    return candidate if candidate in allowed else default


def bool_choice(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "si", "s?", "on", "checked"}


def safe_internal_route(value: Any) -> str:
    text = clean_text(value, 160)
    if not text:
        return "No especificada"
    text = text.split("?", 1)[0].split("#", 1)[0]
    if not text.startswith("/") or "//" in text:
        return "No especificada"
    return text[:120]


def pseudonymized_user_ref(user: Mapping[str, Any] | None) -> str:
    if not user:
        return "anonimo"
    raw = clean_text(user.get("id") or user.get("username") or user.get("email") or "", 160)
    if not raw:
        return "anonimo"
    digest = hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"usr_{digest}"


def contains_sensitive_text(*values: Any) -> bool:
    return any(SENSITIVE_RE.search(str(value or "")) for value in values)


def sanitize_beta_feedback_payload(form: Mapping[str, Any], user: Mapping[str, Any] | None = None) -> tuple[dict[str, Any], list[str]]:
    feedback_type = choice(form.get("feedback_type"), FEEDBACK_TYPES, "general")
    category = choice(form.get("category"), FEEDBACK_CATEGORIES, "other")
    severity = choice(form.get("severity"), SEVERITIES, "medium")
    device = choice(form.get("device_context"), DEVICES, "unknown")
    satisfaction_score = None
    raw_score = clean_text(form.get("satisfaction_score"), 8)
    if feedback_type == "satisfaction":
        try:
            satisfaction_score = int(raw_score)
        except ValueError:
            satisfaction_score = None
    if satisfaction_score is not None and satisfaction_score not in {1, 2, 3, 4, 5}:
        satisfaction_score = None

    payload = {
        "created_at_madrid": madrid_now(),
        "user_ref": pseudonymized_user_ref(user),
        "feedback_type": feedback_type,
        "category": category,
        "severity": severity,
        "surface": clean_text(form.get("surface"), 120) or FEEDBACK_CATEGORIES.get(category, "Otro"),
        "route": safe_internal_route(form.get("route")),
        "device_context": device,
        "title": clean_text(form.get("title"), 140),
        "message": clean_text(form.get("message"), 900),
        "steps_to_reproduce": clean_text(form.get("steps_to_reproduce"), 900),
        "expected_result": clean_text(form.get("expected_result"), 420),
        "actual_result": clean_text(form.get("actual_result"), 420),
        "satisfaction_score": satisfaction_score,
        "allow_beta_metrics": bool_choice(form.get("allow_beta_metrics")),
        "status": "open",
        "source": "beta_center_form",
    }

    errors: list[str] = []
    text_values = [payload["title"], payload["message"], payload["steps_to_reproduce"], payload["expected_result"], payload["actual_result"]]
    if contains_sensitive_text(*text_values):
        errors.append("Retira correos, tel?fonos, tarjetas, contrase?as, tokens o claves antes de enviar el feedback.")
    if not payload["title"]:
        errors.append("Anade un titulo breve para clasificar el feedback.")
    if not payload["message"]:
        errors.append("Describe que has visto y que esperabas que ocurriera.")
    if feedback_type == "bug":
        if not payload["steps_to_reproduce"]:
            errors.append("Para reportar un bug necesitamos pasos para reproducirlo.")
        if not payload["expected_result"] or not payload["actual_result"]:
            errors.append("Para reportar un bug indica resultado esperado y resultado real.")
    if feedback_type == "satisfaction" and satisfaction_score is None:
        errors.append("La satisfacci?n debe tener una puntuacion de 1 a 5.")
    return payload, errors


def metric_definition(key: str, label: str, value: Any, source: str, definition: str, limitation: str, enabled: bool = True) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "value": value,
        "source": source,
        "definition": definition,
        "limitation": limitation,
        "transparent": True,
        "user_disable_supported": enabled,
    }


def build_beta_program_snapshot(
    *,
    counts: Mapping[str, Any] | None = None,
    recent_feedback: list[dict[str, Any]] | None = None,
    source_contracts: Mapping[str, Any] | None = None,
    generated_at_madrid: str | None = None,
) -> dict[str, Any]:
    counts = dict(counts or {})
    recent_feedback = list(recent_feedback or [])
    source_contracts = dict(source_contracts or {})
    generated_at = generated_at_madrid or madrid_now()
    feedback_total = int(counts.get("feedback_total") or 0)
    bug_total = int(counts.get("bug_total") or 0)
    feature_total = int(counts.get("feature_total") or 0)
    satisfaction_count = int(counts.get("satisfaction_count") or 0)
    metrics_enabled = int(counts.get("metrics_enabled") or 0)
    metrics_disabled = int(counts.get("metrics_disabled") or 0)
    open_items = int(counts.get("open_items") or 0)
    satisfaction_average = counts.get("satisfaction_average")

    platform_score = 70
    if feedback_total:
        platform_score += min(10, feedback_total * 2)
    if bug_total or feature_total:
        platform_score += 6
    if satisfaction_count:
        platform_score += 6
    if metrics_disabled or metrics_enabled:
        platform_score += 4
    if open_items > 20:
        platform_score -= 10
    platform_score = max(0, min(100, platform_score))

    return {
        "contract": BETA_PROGRAM_CONTRACT,
        "feedback_contract": FEEDBACK_PLATFORM_CONTRACT,
        "metrics_contract": BETA_METRICS_CONTRACT,
        "generated_at_madrid": generated_at,
        "environment": "local_read_write_for_beta_feedback_only",
        "status": "READY_FOR_CLOSED_BETA_LOCAL",
        "platform_score": platform_score,
        "score_explanation": [
            "Base 70 por infraestructura local de beta y privacidad.",
            "Suma solo se?ales explicitas de feedback, bugs, solicitudes, satisfacci?n y consentimiento de m?tricas.",
            "No mide ?xito comercial ni satisfacci?n real si no existen respuestas suficientes.",
        ],
        "metrics": [
            metric_definition("feedback_total", "Feedback recibido", feedback_total, "beta_feedback", "Total de envios explicitos realizados desde el Beta Center.", "No incluye conversaciones externas ni mensajes no registrados."),
            metric_definition("bug_total", "Bugs reportados", bug_total, "beta_feedback", "Envios clasificados como bug con estructura reproducible.", "Un bug reportado no equivale a bug confirmado hasta revision humana."),
            metric_definition("feature_total", "Solicitudes", feature_total, "beta_feedback", "Envios clasificados como solicitud de mejora.", "No implica aprobaci?n de roadmap."),
            metric_definition("satisfaction_average", "Satisfacci?n media", satisfaction_average if satisfaction_average is not None else "No certificada", "beta_feedback", "Media de puntuaciones 1-5 enviadas voluntariamente.", "No se interpreta con muestras peque?as."),
            metric_definition("metrics_enabled", "Metricas aceptadas", metrics_enabled, "beta_feedback", "Envios donde el usuario permite usar el feedback para m?tricas agregadas.", "El usuario puede desactivar esta medici?n en cada envio."),
            metric_definition("metrics_disabled", "Metricas desactivadas", metrics_disabled, "beta_feedback", "Envios donde el usuario no permite uso agregado para m?tricas.", "El feedback se conserva para soporte si se envio, pero no se usa en m?tricas agregadas."),
        ],
        "feedback_sections": [
            {"key": "bug", "title": "Bug Reporter", "purpose": "Registrar errores reproducibles con pasos, resultado esperado y resultado real."},
            {"key": "feature_request", "title": "Feature Requests", "purpose": "Estructurar sugerencias sin convertirlas autom?ticamente en roadmap."},
            {"key": "satisfaction", "title": "Satisfaction", "purpose": "Medir percepcion voluntaria y agregada con posibilidad de desactivar metrica."},
            {"key": "general", "title": "Feedback Center", "purpose": "Recoger claridad, friccion, valor percibido y problemas no tecnicos."},
        ],
        "privacy_controls": {
            "stores_sensitive_information": False,
            "stores_email": False,
            "stores_phone": False,
            "stores_tokens": False,
            "uses_pseudonymous_user_ref": True,
            "metrics_can_be_disabled_per_submission": True,
            "external_calls": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
        },
        "reproducibility_contract": {
            "bug_requires_steps": True,
            "bug_requires_expected_result": True,
            "bug_requires_actual_result": True,
            "route_is_sanitized": True,
            "free_text_sensitive_guard": True,
        },
        "recent_feedback": recent_feedback[:12],
        "counts": counts,
        "source_contracts": source_contracts,
        "next_action": "Invitar un grupo pequeno de usuarios beta, recoger feedback estructurado y revisar el dashboard antes de decidir nuevas mejoras.",
        "production_modified": False,
        "deploy_executed": False,
        "push_executed": False,
    }


__all__ = [
    "BETA_METRICS_CONTRACT",
    "BETA_PROGRAM_CONTRACT",
    "FEEDBACK_PLATFORM_CONTRACT",
    "FEEDBACK_CATEGORIES",
    "FEEDBACK_TYPES",
    "SEVERITIES",
    "build_beta_program_snapshot",
    "contains_sensitive_text",
    "sanitize_beta_feedback_payload",
]
