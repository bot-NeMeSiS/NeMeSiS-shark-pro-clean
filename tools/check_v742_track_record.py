#!/usr/bin/env python3
"""QA for V742 Track Record without inventing results."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    os.environ.setdefault("SECRET_KEY", "v742-track-record-check")
    os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
    os.environ.setdefault("SCHEDULER_ENABLED", "false")
    os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v742_track_record_check.db"))
    import app as app_module  # noqa: WPS433

    context = app_module.v742_track_record_context()
    checks = {
        "has_status": bool(context.get("status")),
        "roi_safe": "roi" in context,
        "no_fake_note": bool(context.get("commercial_note")),
        "recent_list": isinstance(context.get("recent_results"), list),
    }
    result = {"ok": all(checks.values()), "version": app_module.APP_VERSION, "checks": checks, "track_record": context}
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    try:
        Path(os.environ["DB_PATH"]).unlink(missing_ok=True)
    except Exception:
        pass
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
