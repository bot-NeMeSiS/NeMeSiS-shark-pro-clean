#!/usr/bin/env python3
"""V744 Telegram certification: configuration and diagnostics only, no sending."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nemesis_v744_telegram_") as tmp:
        os.environ.setdefault("SECRET_KEY", "v744-telegram-check")
        os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
        os.environ.setdefault("SCHEDULER_ENABLED", "false")
        os.environ["DB_PATH"] = str(Path(tmp) / "database.db")
        import app as app_module  # noqa: WPS433

        diagnostics = app_module.telegram_diagnostics_safe()
        result = {
            "ok": True,
            "bot_configured": app_module.env_present("TELEGRAM_BOT_TOKEN"),
            "channel_configured": app_module.env_present("TELEGRAM_CHAT_ID"),
            "auto_enabled": app_module.telegram_env_auto_enabled(),
            "diagnostics_keys": sorted(list(diagnostics.keys()))[:20],
            "no_real_send": True,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
