#!/usr/bin/env python3
"""V744 protected route smoke checks."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nemesis_v744_routes_") as tmp:
        os.environ.setdefault("SECRET_KEY", "v744-routes-check")
        os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
        os.environ.setdefault("SCHEDULER_ENABLED", "false")
        os.environ["DB_PATH"] = str(Path(tmp) / "database.db")
        import app as app_module  # noqa: WPS433

        client = app_module.app.test_client()
        routes = ["/api/runtime-version", "/api/health", "/api/startup-check"]
        statuses = {route: client.get(route).status_code for route in routes}
        result = {"ok": all(code == 200 for code in statuses.values()), "statuses": statuses}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
