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
    env = dict(env or os.environ)
    state = state or {}
    automation_secret = _present(env, "AUTOMATION_SECRET")
    public_base = _present(env, "PUBLIC_BASE_URL")
    db_ok = bool(db_path)
    telegram_ready = _present(env, "TELEGRAM_BOT_TOKEN") and _present(env, "TELEGRAM_CHAT_ID")
    highlights_enabled = _bool_env(env, "HIGHLIGHTS_SYNC_ENABLED", True) or _present(env, "THESPORTSDB_API_KEY")
    grading_enabled = _bool_env(env, "ENABLE_PICK_GRADING_AUTOMATION", True)
    backup_enabled = _bool_env(env, "DATA_BACKUP_ENABLED", False)
    daily_enabled = _bool_env(env, "DAILY_AUTOMATION_ENABLED", True) or _bool_env(env, "SCHEDULER_ENABLED", False)
    telegram_enabled = _bool_env(env, "ENABLE_TELEGRAM_AUTOMATION", True) or _bool_env(env, "TELEGRAM_AUTO_SEND_ENABLED", True)
    jobs = [
        _job("telegram_tick", "Telegram automático", "/api/automation/telegram/tick?secret=AUTOMATION_SECRET", "python tools/render_cron_telegram_tick.py", telegram_enabled, automation_secret and public_base and telegram_ready, state.get("last_cron_telegram_call"), "*/10 * * * *"),
        _job("daily_run", "Automatización diaria", "/api/automation/daily/run?secret=AUTOMATION_SECRET", "HTTP Render Cron", daily_enabled, automation_secret and db_ok, state.get("last_cron_daily_call"), "0 * * * *"),
        _job("pick_grading", "Grading de picks", "/api/automation/picks/grade?secret=AUTOMATION_SECRET", "HTTP Render Cron", grading_enabled, automation_secret and db_ok, state.get("last_cron_pick_grading"), "cada 6h"),
        _job("highlights_sync", "Highlights / resúmenes", "/api/automation/highlights/sync?secret=AUTOMATION_SECRET", "python tools/render_cron_highlights_sync.py", highlights_enabled, automation_secret and db_ok, state.get("last_cron_highlights_sync"), "cada 6-12h"),
        _job("data_backup", "Data Vault backup", "/api/automation/data-backup/run?secret=AUTOMATION_SECRET", "HTTP Render Cron", backup_enabled, automation_secret and db_ok, state.get("last_cron_data_backup_call"), "diario"),
    ]
    ready = len([j for j in jobs if j["status"] == "READY"])
    warnings = []
    if not automation_secret:
        warnings.append("Falta AUTOMATION_SECRET: los cron protegidos no deben ejecutarse sin secret.")
    if telegram_enabled and not telegram_ready:
        warnings.append("Telegram automático activado pero faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID.")
    if not public_base:
        warnings.append("PUBLIC_BASE_URL no está configurada; Render Cron debe apuntar a la URL pública correcta.")
    return {
        "version": app_version,
        "generated_at_madrid": datetime.now(MADRID_TZ).isoformat(timespec="seconds"),
        "enabled": _bool_env(env, "AUTOMATION_CENTER_ENABLED", True),
        "readiness_score": min(100, 50 + ready * 9 + (5 if not warnings else 0)),
        "jobs_ready": ready,
        "jobs_total": len(jobs),
        "jobs": jobs,
        "environment": {
            "automation_secret_configured": automation_secret,
            "public_base_url_configured": public_base,
            "public_base_url": env.get("PUBLIC_BASE_URL") or "",
            "db_path_configured": db_ok,
            "telegram_token_masked": _masked(env.get("TELEGRAM_BOT_TOKEN", "")),
            "telegram_chat_masked": _masked(env.get("TELEGRAM_CHAT_ID", "")),
            "timezone_ok": (env.get("TZ") == "Europe/Madrid" or env.get("APP_TIMEZONE") == "Europe/Madrid"),
        },
        "warnings": warnings,
        "next_actions": [
            "Confirmar en Render que Cron usa el mismo AUTOMATION_SECRET que el Web Service.",
            "Revisar Command Center Telegram después de cada deploy.",
            "Lanzar grading/highlights solo con datos reales disponibles.",
        ],
    }
