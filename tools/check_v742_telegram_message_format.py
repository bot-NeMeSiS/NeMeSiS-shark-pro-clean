#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    app = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    engines = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (ROOT / "engines").glob("*telegram*.py"))
    checks = {
        "preview_endpoint": "/api/admin/telegram/preview-next" in app,
        "dry_run_endpoint": "/api/admin/telegram/dry-run" in app,
        "safe_preview": "safe_preview_text" in engines,
        "parse_mode_fallback_status": "TELEGRAM_PARSE_MODE_ERROR" in engines,
        "message_length_status": "MESSAGE_TOO_LONG" in engines,
        "responsible_language": "responsable" in engines.lower() or "Juego responsable" in app,
    }
    ok = all(checks.values())
    lines = [
        "# V742 Telegram Production Runbook",
        "",
        "## Render Cron",
        "- Tick: `/api/automation/telegram/tick?secret=VALOR_DE_AUTOMATION_SECRET` cada 15 minutos.",
        "- Daily: `/api/automation/daily/run?secret=VALOR_DE_AUTOMATION_SECRET` cada hora o 10:00 Europe/Madrid.",
        "- Sin secret debe devolver 403.",
        "- Con secret debe devolver 200 con JSON compacto.",
        "",
        "## Diagnóstico",
        "- Revisar `/admin/telegram/command-center`.",
        "- Revisar `/api/admin/telegram/status` con sesión admin.",
        "- Usar dry-run y preview antes de un test real.",
        "- Si Telegram dice `forbidden` o `chat not found`, revisar permisos/destino del bot.",
    ]
    (ROOT / "V742_TELEGRAM_PRODUCTION_RUNBOOK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
