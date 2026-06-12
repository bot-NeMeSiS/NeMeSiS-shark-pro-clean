"""Diagnostico seguro de fiabilidad Telegram para NeMeSiS SHARK PRO.

Este modulo no envia mensajes y no conoce secrets reales. Recibe datos ya
mascarados o banderas booleanas desde app.py y devuelve una explicacion clara.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")

READY_TO_SEND = "READY_TO_SEND"
NO_CANDIDATES = "NO_CANDIDATES"
NO_FOOTBALL_CANDIDATES = "NO_FOOTBALL_CANDIDATES"
NO_PREMIUM_PICKS = "NO_PREMIUM_PICKS"
ALL_DISCARDED_NO_ODDS = "ALL_DISCARDED_NO_ODDS"
ALL_DISCARDED_LOW_QUALITY = "ALL_DISCARDED_LOW_QUALITY"
ALL_ALREADY_SENT = "ALL_ALREADY_SENT"
BLOCKED_BY_HOURLY_LIMIT = "BLOCKED_BY_HOURLY_LIMIT"
BLOCKED_BY_DAILY_LIMIT = "BLOCKED_BY_DAILY_LIMIT"
BLOCKED_BY_QUIET_HOURS = "BLOCKED_BY_QUIET_HOURS"
MISSING_BOT_TOKEN = "MISSING_BOT_TOKEN"
MISSING_CHAT_ID = "MISSING_CHAT_ID"
TELEGRAM_API_ERROR = "TELEGRAM_API_ERROR"
DB_ERROR = "DB_ERROR"
DATA_MEMORY_ERROR = "DATA_MEMORY_ERROR"
UNKNOWN_ERROR = "UNKNOWN_ERROR"


def madrid_now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _count(reason_counts: dict, key: str) -> int:
    return int(reason_counts.get(key) or 0)


def _severity(status: str) -> str:
    if status in {READY_TO_SEND, NO_CANDIDATES, NO_PREMIUM_PICKS, ALL_ALREADY_SENT}:
        return "info"
    if status in {BLOCKED_BY_HOURLY_LIMIT, BLOCKED_BY_DAILY_LIMIT, BLOCKED_BY_QUIET_HOURS, ALL_DISCARDED_NO_ODDS, ALL_DISCARDED_LOW_QUALITY, NO_FOOTBALL_CANDIDATES}:
        return "warning"
    return "critical"


def _normal(status: str) -> bool:
    return status in {
        READY_TO_SEND,
        NO_CANDIDATES,
        NO_PREMIUM_PICKS,
        ALL_ALREADY_SENT,
        BLOCKED_BY_HOURLY_LIMIT,
        BLOCKED_BY_DAILY_LIMIT,
        BLOCKED_BY_QUIET_HOURS,
    }


def explain_telegram_state(snapshot: dict) -> dict:
    """Return a human diagnostic from a compact Telegram snapshot."""
    env = snapshot.get("env") or {}
    counts = snapshot.get("counts") or {}
    reason_counts = snapshot.get("reason_counts") or {}
    limits = snapshot.get("limits") or {}
    last_error = snapshot.get("last_error") or {}
    data_memory = snapshot.get("data_memory") or {}

    status = UNKNOWN_ERROR
    explanation = "Telegram no tiene un diagnostico suficiente con los datos actuales."
    action = "Revisar logs, cola y diagnostico admin."

    if not env.get("bot_token_configured"):
        status = MISSING_BOT_TOKEN
        explanation = "Telegram no puede enviar porque falta TELEGRAM_BOT_TOKEN."
        action = "Configurar TELEGRAM_BOT_TOKEN en Render y redeployar."
    elif not env.get("chat_id_configured"):
        status = MISSING_CHAT_ID
        explanation = "Telegram no puede enviar al canal global porque falta TELEGRAM_CHAT_ID."
        action = "Configurar TELEGRAM_CHAT_ID o CHANNEL_ID en Render."
    elif int(counts.get("failed_today") or 0) > 0 and (last_error.get("status") in {"ERROR", "FAILED", "failed", "error"} or last_error.get("message")):
        status = TELEGRAM_API_ERROR
        explanation = "Hay un error reciente de Telegram registrado en logs o cola."
        action = "Revisar ultimo error, permisos del bot y chat/channel usado."
    elif data_memory.get("errors"):
        status = DATA_MEMORY_ERROR
        explanation = "Data Memory registro errores relacionados con Telegram o picks."
        action = "Revisar tabla data_memory_errors y telegram_delivery_memory."
    elif limits.get("quiet_hours_active"):
        status = BLOCKED_BY_QUIET_HOURS
        explanation = "Telegram esta dentro del horario silencioso profesional."
        action = "Esperar a la ventana de envio o ejecutar dry-run; no forzar envios masivos."
    elif int(limits.get("sent_last_hour") or 0) >= int(limits.get("max_per_hour") or 999):
        status = BLOCKED_BY_HOURLY_LIMIT
        explanation = f"Telegram alcanzo el limite horario de {limits.get('max_per_hour')} mensajes."
        action = "Esperar a la siguiente hora o revisar si el limite es demasiado estricto."
    elif int(limits.get("sent_today") or 0) >= int(limits.get("max_per_day") or 999):
        status = BLOCKED_BY_DAILY_LIMIT
        explanation = f"Telegram alcanzo el limite diario de {limits.get('max_per_day')} mensajes."
        action = "Esperar al siguiente dia o ajustar TELEGRAM_MAX_MESSAGES_PER_DAY."
    elif int(counts.get("candidate_picks") or 0) <= 0:
        status = NO_CANDIDATES
        explanation = "Telegram no envia porque no hay picks publicados/candidatos revisables."
        action = "Ejecutar Daily Automation y revisar generacion de picks."
    elif int(counts.get("football_candidates") or 0) <= 0:
        status = NO_FOOTBALL_CANDIDATES
        explanation = "Hay candidatos, pero el filtro football_only descarta todos como no futbol."
        action = "Revisar competiciones/deporte de los candidatos y el filtro de futbol."
    elif int(counts.get("premium_eligible") or 0) <= 0:
        if _count(reason_counts, "sin_cuota_real") >= int(counts.get("football_candidates") or 0):
            status = ALL_DISCARDED_NO_ODDS
            explanation = "Hay futbol, pero los picks no tienen cuota real valida."
            action = "Revisar sincronizacion de cuotas y mercados antes de enviar."
        elif _count(reason_counts, "calidad_insuficiente") or _count(reason_counts, "score_bajo"):
            status = ALL_DISCARDED_LOW_QUALITY
            explanation = "Hay picks, pero SHARK/PRO los descarta por calidad o score insuficiente."
            action = "Revisar min_score, riesgo y calidad de picks; no bajar calidad sin criterio."
        elif int(counts.get("already_sent") or 0) >= int(counts.get("football_candidates") or 0):
            status = ALL_ALREADY_SENT
            explanation = "Los candidatos validos ya tienen dedupe o envio registrado hoy."
            action = "No reenviar salvo que haya picks nuevos; revisar dedupe si parece excesivo."
        else:
            status = NO_PREMIUM_PICKS
            explanation = "Hay candidatos, pero ninguno cumple todos los requisitos premium de Telegram."
            action = "Revisar razones de descarte en el Command Center."
    else:
        status = READY_TO_SEND
        explanation = f"Telegram tiene {counts.get('premium_eligible')} pick(s) premium elegible(s)."
        action = "Render Cron puede procesar el tick; usar dry-run/preview antes de test manual."

    return {
        "status": status,
        "severity": _severity(status),
        "normal": _normal(status),
        "explanation": explanation,
        "action": action,
        "madrid_now": snapshot.get("madrid_now") or madrid_now(),
        "data": {
            "counts": counts,
            "reason_counts": reason_counts,
            "limits": limits,
            "env": env,
        },
    }


def safe_preview_text(text: str, limit: int = 1200) -> str:
    text = str(text or "")
    forbidden = ("token", "secret", "api_key", "password")
    lines = []
    for line in text.splitlines():
        low = line.lower()
        if any(word in low for word in forbidden):
            continue
        lines.append(line)
    clean = "\n".join(lines).strip()
    return clean[:limit]
