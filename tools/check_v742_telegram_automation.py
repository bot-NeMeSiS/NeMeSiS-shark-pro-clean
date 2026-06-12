#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    app = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    engine = (ROOT / "engines" / "telegram_reliability_engine.py").read_text(encoding="utf-8", errors="replace")
    required_statuses = [
        "READY_TO_SEND", "MISSING_BOT_TOKEN", "MISSING_CHAT_ID",
        "BLOCKED_BY_AUTOMATION_DISABLED", "BLOCKED_BY_TELEGRAM_DISABLED",
        "BOT_NOT_IN_GROUP_OR_CHANNEL", "BOT_NOT_ADMIN_IN_CHANNEL",
        "TELEGRAM_PARSE_MODE_ERROR", "MESSAGE_TOO_LONG",
    ]
    checks = {
        "cron_tick_route": "/api/automation/telegram/tick" in app,
        "daily_route": "/api/automation/daily/run" in app,
        "secret_required": "automation_cron_access_allowed" in app and "automation_json_forbidden" in app,
        "status_fields": all(field in app for field in ["manual_send_status", "auto_tick_status", "daily_run_status", "channel_status"]),
        "diagnostic_statuses": all(status in engine for status in required_statuses),
        "no_real_send_in_check": True,
    }
    ok = all(checks.values())
    lines = [
        "# V742 Telegram Automation Fix Report",
        "",
        f"- Estado: {'OK' if ok else 'REVISAR'}",
        "- Manual y automático quedan separados en diagnóstico.",
        "- Cron mantiene secret obligatorio.",
        "- No se envía ningún mensaje desde este check.",
        "- Si Render no tiene variables reales, el bloqueo se explica en Command Center.",
    ]
    (ROOT / "V742_TELEGRAM_AUTOMATION_FIX_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "checks": checks, "required_statuses": required_statuses}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
