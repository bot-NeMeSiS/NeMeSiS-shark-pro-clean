"""V892 Telegram quality watch for Autonomous Company Sentinel."""
from __future__ import annotations

from typing import Any


SENTINEL_TELEGRAM_QUALITY_WATCH_VERSION = "V892_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL"


def build_telegram_quality_watch(
    runtime: dict[str, Any] | None = None,
    latest_telegram: dict[str, Any] | None = None,
    render_runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = runtime or {}
    latest_telegram = latest_telegram or {}
    render_runtime = render_runtime or {}
    local_configured = bool(runtime.get("telegram_configured") or (runtime.get("flags") or {}).get("telegram_configured"))
    render_configured = bool(render_runtime.get("telegram_configured") or (render_runtime.get("flags") or {}).get("telegram_configured"))
    configured = local_configured or render_configured
    issues = []
    if not local_configured and render_configured:
        issues.append({
            "title": "Telegram no configurado en entorno local",
            "area": "telegram",
            "severity": "info",
            "evidence": "local_env_status.telegram_configured=false; render_runtime_status.telegram_configured=true",
            "recommendation": "No crear crítico local si producción sí confirma Telegram. Mantener no filler/dedupe.",
        })
    elif not configured:
        issues.append({
            "title": "Telegram no configurado",
            "area": "telegram",
            "severity": "info",
            "evidence": "Runtime no confirma Telegram configurado.",
            "recommendation": "Mostrar estado No configurado y no prometer envios reales.",
        })
    if "QUEUE_SKIPPED" not in str(runtime) and latest_telegram.get("queue_state") == "undefined":
        issues.append({
            "title": "Estado de cola Telegram indefinido",
            "area": "telegram",
            "severity": "high",
            "evidence": "queue_state undefined",
            "recommendation": "Preservar hotfix QUEUE_SKIPPED y revalidar cron.",
        })
    return {
        "engine_version": SENTINEL_TELEGRAM_QUALITY_WATCH_VERSION,
        "configured": configured,
        "local_env_status": {"telegram_configured": local_configured},
        "render_runtime_status": {"telegram_configured": render_configured, "available": bool(render_runtime)},
        "no_filler_policy": True,
        "dedupe_required": True,
        "real_send_allowed": False,
        "issues": issues,
    }
