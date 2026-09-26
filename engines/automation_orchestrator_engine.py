"""V773 admin automation center helpers."""
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

MADRID_TZ = ZoneInfo("Europe/Madrid")


def _bool_env(env: dict, key: str, default: bool = False) -> bool:
    value = env.get(key)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _present(env: dict, key: str) -> bool:
    return bool(str(env.get(key) or "").strip())


def _masked(value: str) -> str:
    value = str(value or "")
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:3]}…{value[-3:]}"


def _job(name, label, endpoint, command, enabled, configured, last=None, cadence=""):
    last = last or {}
    status = "READY" if enabled and configured else ("CONFIG_REVIEW" if enabled else "DISABLED")
    return {
        "name": name,
        "label": label,
        "endpoint": endpoint,
        "command": command,
        "cadence": cadence,
        "enabled": bool(enabled),
        "configured": bool(configured),
        "status": status,
        "last_run": last.get("time") or last.get("created_at") or last.get("madrid_time") or "",
        "last_result": (last.get("result") or {}).get("status") if isinstance(last.get("result"), dict) else last.get("status") or "",
        "safe_note": "Protegido por AUTOMATION_SECRET" if endpoint and "secret" in endpoint else "Admin only",
    }


def build_automation_center_summary(db_path: str, app_version: str = "", env: dict | None = None, state: dict | None = None) -> dict:
    """Canonical schedule: only jobs actually intended to exist in Render."""
    env = dict(env or os.environ)
    state = state or {}
    automation_secret = _present(env, "AUTOMATION_SECRET")
    public_base = _present(env, "PUBLIC_BASE_URL")
    db_ok = bool(db_path)
    telegram_ready = _present(env, "TELEGRAM_BOT_TOKEN") and _present(env, "TELEGRAM_CHAT_ID")
    backup_enabled = _bool_env(env, "DATA_BACKUP_ENABLED", False)

    master = _job(
        "master_tick",
        "Cron maestro",
        "/api/automation/telegram/tick + /api/automation/continuous-evolution/tick",
        "python tools/render_cron_master_tick.py",
        True,
        automation_secret and public_base and db_ok,
        state.get("last_cron_telegram_call"),
        "cada 10 min",
    )
    master["description"] = "Incluye sincronización deportiva, cuotas, evaluación de pronósticos, Telegram y revisión diaria segura."
    master["included_flows"] = ["sports_sync", "odds", "pick_grading", "telegram", "continuous_evolution"]
    backup = _job(
        "data_backup",
        "Backup diario",
        "/api/automation/data-backup/run",
        "python tools/render_cron_data_backup.py",
        backup_enabled,
        automation_secret and public_base and db_ok,
        state.get("last_cron_data_backup_call"),
        "02:30 UTC · diario (03:30/04:30 Madrid)",
    )
    backup["description"] = "Copia diaria de la base persistente con retención del Data Vault."

    jobs = [master, backup]
    ready = len([job for job in jobs if job["status"] == "READY"])
    warnings = []
    if not automation_secret:
        warnings.append("Falta AUTOMATION_SECRET: ningún cron protegido debe ejecutarse.")
    if not public_base:
        warnings.append("PUBLIC_BASE_URL no está configurada para los runners de Render.")
    if not telegram_ready:
        warnings.append("Telegram no está completamente configurado; el cron maestro puede sincronizar datos, pero no debe afirmar entrega Telegram.")
    if not backup_enabled:
        warnings.append("Backup diario desactivado. DATA_BACKUP_ENABLED debe estar activo en producción.")

    return {
        "version": app_version,
        "generated_at_madrid": datetime.now(MADRID_TZ).isoformat(timespec="seconds"),
        "enabled": _bool_env(env, "AUTOMATION_CENTER_ENABLED", True),
        "policy": "ONE_OPERATIONAL_MASTER_PLUS_DAILY_BACKUP",
        "scheduled_job_count": len(jobs),
        "readiness_score": min(100, 70 + ready * 12 + (6 if not warnings else 0)),
        "jobs_ready": ready,
        "jobs_total": len(jobs),
        "jobs": jobs,
        "manual_only": [
            "scheduler_engine legacy tasks",
            "daily_run V818",
            "highlights sync",
            "standalone pick grading",
            "standalone sports sync",
            "Sentinel scans",
            "visual/browser QA workers",
        ],
        "environment": {
            "automation_secret_configured": automation_secret,
            "public_base_url_configured": public_base,
            "public_base_url": env.get("PUBLIC_BASE_URL") or "",
            "db_path_configured": db_ok,
            "telegram_token_masked": _masked(env.get("TELEGRAM_BOT_TOKEN", "")),
            "telegram_chat_masked": _masked(env.get("TELEGRAM_CHAT_ID", "")),
            "timezone_ok": (env.get("TZ") == "Europe/Madrid" or env.get("APP_TIMEZONE") == "Europe/Madrid"),
            "legacy_scheduler_enabled": _bool_env(env, "SCHEDULER_ENABLED", False) or _bool_env(env, "ENABLE_AUTO_SYNC", False),
            "legacy_startup_sync_enabled": _bool_env(env, "AUTO_SYNC_ON_STARTUP", False),
            "legacy_daily_automation_enabled": _bool_env(env, "DAILY_AUTOMATION_ENABLED", False),
        },
        "warnings": warnings,
        "next_actions": [
            "Mantener un único cron operativo cada 10 minutos.",
            "Mantener un único backup diario a las 02:30 UTC de Render (03:30/04:30 Madrid según horario).",
            "Ejecutar highlights, Sentinel, QA visual y jobs legacy solo bajo demanda.",
        ],
    }
