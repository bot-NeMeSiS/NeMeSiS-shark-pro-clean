#!/usr/bin/env python3
"""V745 top app readiness route/context check."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nemesis_v745_ready_", ignore_cleanup_errors=True) as tmp:
        os.environ.setdefault("SECRET_KEY", "v745-ready-check")
        os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
        os.environ.setdefault("SCHEDULER_ENABLED", "false")
        os.environ["DB_PATH"] = str(Path(tmp) / "database.db")
        import app as app_module  # noqa: WPS433

        context = app_module.v745_top_app_readiness_context()
        required = ["data_vault", "production", "match_intelligence", "video_highlights", "alerts", "payments", "sale_ready"]
        result = {"ok": all(key in context for key in required), "version": context.get("version"), "status": context.get("status")}
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
