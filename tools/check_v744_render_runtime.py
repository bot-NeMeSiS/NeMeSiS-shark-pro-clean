#!/usr/bin/env python3
"""V744 Render/runtime endpoint QA without external network calls."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nemesis_v744_runtime_") as tmp:
        os.environ.setdefault("SECRET_KEY", "v744-runtime-check")
        os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
        os.environ.setdefault("SCHEDULER_ENABLED", "false")
        os.environ.setdefault("DATA_BACKUP_ENABLED", "false")
        os.environ["AUTOMATION_SECRET"] = "v744-secret"
        os.environ["DB_PATH"] = str(Path(tmp) / "database.db")
        import app as app_module  # noqa: WPS433

        client = app_module.app.test_client()
        runtime = client.get("/api/runtime-version")
        forbidden = client.get("/api/automation/data-backup/run")
        allowed = client.get("/api/automation/data-backup/run?secret=v744-secret")
        result = {
            "ok": runtime.status_code == 200 and forbidden.status_code == 403 and allowed.status_code == 200,
            "runtime_status": runtime.status_code,
            "cron_without_secret": forbidden.status_code,
            "cron_with_secret": allowed.status_code,
            "cron_payload": allowed.get_json(silent=True) or {},
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
