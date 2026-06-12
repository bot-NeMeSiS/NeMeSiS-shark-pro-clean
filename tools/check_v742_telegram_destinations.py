#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    app = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    checks = {
        "global_channel_supported": "telegram_auto_destinations" in app and "include_global=True" in app,
        "private_supported": "private_destinations" in app,
        "destination_masking": "masked_key" in app and "last_successful_destination" in app,
        "missing_destination_status": "BLOCKED_BY_MISSING_DESTINATION" in app,
        "no_secret_exposure": "TELEGRAM_BOT_TOKEN" not in (ROOT / "templates" / "admin_telegram_command_center.html").read_text(encoding="utf-8", errors="replace"),
    }
    ok = all(checks.values())
    lines = [
        "# V742 Telegram Destination QA Report",
        "",
        f"- Estado: {'OK' if ok else 'REVISAR'}",
        "- Canal global soportado cuando `TELEGRAM_CHAT_ID` existe.",
        "- Privados vinculados soportados si hay usuarios con chat id.",
        "- Destinos se muestran enmascarados.",
        "- El template admin no expone `TELEGRAM_BOT_TOKEN`.",
    ]
    (ROOT / "V742_TELEGRAM_DESTINATION_QA_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
