"""Telegram environment audit helpers.

Read-only helpers: never expose full secrets and never mutate application state.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse


OFFICIAL_AUTO_FLAGS = (
    "ENABLE_TELEGRAM_AUTO",
    "AUTO_SEND_TELEGRAM_PICKS",
    "TELEGRAM_AUTO_SEND_ENABLED",
    "ENABLE_TELEGRAM_AUTOMATION",
)

WEB_SERVICE_REQUIRED = (
    "AUTOMATION_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "TELEGRAM_BOT_USERNAME",
    *OFFICIAL_AUTO_FLAGS,
    "AUTO_GENERATE_PICKS",
    "TZ",
    "APP_TIMEZONE",
    "PUBLIC_BASE_URL",
)

CRON_REQUIRED = ("PUBLIC_BASE_URL", "AUTOMATION_SECRET")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y", "si", "sí"}


def _present(name: str) -> bool:
    return bool(str(os.getenv(name) or "").strip())


def _mask(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= 4:
        return "***"
    return f"***{text[-4:]}"


def is_telegram_auto_enabled() -> dict:
    required_flags = {name: _env_bool(name, False) for name in OFFICIAL_AUTO_FLAGS}
    blocking_flags = [name for name, enabled in required_flags.items() if not enabled]
    legacy_flags = {
        "TELEGRAM_ENABLED": _env_bool("TELEGRAM_ENABLED", False),
        "RUN_DAILY_AUTOMATION": _env_bool("RUN_DAILY_AUTOMATION", False),
        "SCHEDULER_ENABLED": _env_bool("SCHEDULER_ENABLED", False),
        "DAILY_AUTOMATION_ENABLED": _env_bool("DAILY_AUTOMATION_ENABLED", False),
    }
    return {
        "enabled": not blocking_flags,
        "required_flags": required_flags,
        "blocking_flags": blocking_flags,
        "legacy_flags": legacy_flags,
    }


def get_telegram_environment_audit(expected_base_url: str = "https://bot-apuestas-crgf.onrender.com") -> dict:
    missing = [name for name in WEB_SERVICE_REQUIRED if not _present(name)]
    warnings = []
    conflicts = []
    masked = {
        "AUTOMATION_SECRET": _mask(os.getenv("AUTOMATION_SECRET", "")),
        "TELEGRAM_BOT_TOKEN": _mask(os.getenv("TELEGRAM_BOT_TOKEN", "")),
        "TELEGRAM_CHAT_ID": _mask(os.getenv("TELEGRAM_CHAT_ID", "")),
    }
    public_base_url = str(os.getenv("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    parsed = urlparse(public_base_url)
    if public_base_url and parsed.scheme not in {"http", "https"}:
        warnings.append("PUBLIC_BASE_URL no parece una URL http/https válida.")
    if public_base_url and expected_base_url and public_base_url != expected_base_url.rstrip("/"):
        warnings.append("PUBLIC_BASE_URL no coincide con la URL pública esperada.")
    if not public_base_url:
        warnings.append("PUBLIC_BASE_URL falta en el entorno.")

    tz = str(os.getenv("TZ") or "").strip()
    app_tz = str(os.getenv("APP_TIMEZONE") or "").strip()
    timezone_ok = tz == "Europe/Madrid" and app_tz == "Europe/Madrid"
    if tz and tz != "Europe/Madrid":
        warnings.append("TZ no está configurado como Europe/Madrid.")
    if app_tz and app_tz != "Europe/Madrid":
        warnings.append("APP_TIMEZONE no está configurado como Europe/Madrid.")

    auto = is_telegram_auto_enabled()
    if auto["blocking_flags"]:
        warnings.append("Faltan flags oficiales de Telegram automático en true: " + ", ".join(auto["blocking_flags"]))

    if _env_bool("TELEGRAM_AUTO_ENABLED", False) and not auto["enabled"]:
        conflicts.append("TELEGRAM_AUTO_ENABLED legacy está activo, pero no sustituye a los cuatro flags oficiales.")

    return {
        "ok": not missing and timezone_ok and auto["enabled"] and not conflicts,
        "telegram_bot_token_present": _present("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id_present": _present("TELEGRAM_CHAT_ID"),
        "telegram_bot_username_present": _present("TELEGRAM_BOT_USERNAME"),
        "automation_secret_present": _present("AUTOMATION_SECRET"),
        "public_base_url": public_base_url,
        "public_base_url_ok": bool(public_base_url and parsed.scheme in {"http", "https"}),
        "timezone_ok": timezone_ok,
        "auto_flags_ok": auto["enabled"],
        "auto": auto,
        "web_service_required": {name: _present(name) for name in WEB_SERVICE_REQUIRED},
        "cron_required": {name: _present(name) for name in CRON_REQUIRED},
        "missing": missing,
        "warnings": warnings,
        "conflicts": conflicts,
        "masked": masked,
    }
