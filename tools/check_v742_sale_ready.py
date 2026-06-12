#!/usr/bin/env python3
"""QA for V742 sale-ready control panel."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    os.environ.setdefault("SECRET_KEY", "v742-sale-ready-check")
    os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
    os.environ.setdefault("SCHEDULER_ENABLED", "false")
    os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v742_sale_ready_check.db"))
    import app as app_module  # noqa: WPS433

    context = app_module.v742_sale_ready_context()
    required = ["live", "calendar", "picks", "track_record", "telegram", "render", "data_memory"]
    checks = {key: key in context for key in required}
    checks["status"] = bool(context.get("status"))
    result = {"ok": all(checks.values()), "version": app_module.APP_VERSION, "checks": checks, "sale_ready": context}
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    try:
        Path(os.environ["DB_PATH"]).unlink(missing_ok=True)
    except Exception:
        pass
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
