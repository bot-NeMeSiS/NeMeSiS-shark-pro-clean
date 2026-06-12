#!/usr/bin/env python3
"""V744 production readiness context check."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nemesis_v744_ready_", ignore_cleanup_errors=True) as tmp:
        os.environ.setdefault("SECRET_KEY", "v744-ready-check")
        os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
        os.environ.setdefault("SCHEDULER_ENABLED", "false")
        os.environ["DB_PATH"] = str(Path(tmp) / "database.db")
        import app as app_module  # noqa: WPS433

        context = app_module.v744_render_runtime_context()
        required = ["render", "cron", "telegram", "data_vault"]
        result = {"ok": all(key in context for key in required), "version": context.get("version"), "keys": sorted(context.keys())}
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
