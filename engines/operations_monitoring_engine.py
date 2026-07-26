"""Read-only monitoring and dead-man policy for V938 Operations Center."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


try:
    MADRID_TZ = ZoneInfo("Europe/Madrid")
except ZoneInfoNotFoundError:
    MADRID_TZ = datetime.now().astimezone().tzinfo


def madrid_now_iso() -> str:
    return datetime.now(MADRID_TZ).isoformat(timespec="seconds")


def _monitor(item: dict[str, Any], stale_after_minutes: int, external: bool = False) -> dict[str, Any]:
    evidence = str(item.get("evidence_state") or "NO_CERTIFICADO")
    status = str(item.get("status") or "UNKNOWN")
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "status": status,
        "evidence_state": evidence,
        "stale_after_minutes": stale_after_minutes,
        "external_monitor_required": external,
        "alert_policy": "admin_only",
        "automatic_action": "record_and_dedupe",
        "human_action": "review" if evidence != "CONFIRMADO" or status not in {"PASS", "HEALTHY", "READY"} else "none",
    }


def build_operations_monitoring(snapshot: dict[str, Any]) -> dict[str, Any]:
    systems = snapshot.get("systems") or []
    cadence = {
        "runtime": 5,
        "render": 5,
        "database": 5,
        "backups": 360,
        "cron": 15,
        "telegram": 30,
        "stripe": 60,
        "sports_data": 15,
        "shark": 15,
        "security": 60,
        "continuity": 360,
    }
    monitors = [
        _monitor(item, cadence.get(str(item.get("id")), 60), external=str(item.get("id")) in {"runtime", "render", "cron"})
        for item in systems
    ]
    external_missing = [item["id"] for item in monitors if item.get("external_monitor_required") and item.get("evidence_state") != "CONFIRMADO"]
    return {
        "ok": not external_missing,
        "checked_at_madrid": madrid_now_iso(),
        "monitors": monitors,
        "dead_man": {
            "status": "READY" if not external_missing else "NOT_CERTIFIED",
            "external_checks_missing": external_missing,
            "destination": "admin_or_internal_only",
            "customer_alerts_enabled": False,
            "safe_message": "Un monitor fuera de Render debe confirmar que runtime, deploy y Cron siguen respondiendo.",
        },
        "dangerous_actions_executed": False,
    }
