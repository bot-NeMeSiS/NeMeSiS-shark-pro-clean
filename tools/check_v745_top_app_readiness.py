#!/usr/bin/env python3
"""V745+ top app readiness route/context check.

Falls back to static validation when Flask is unavailable in a lightweight build sandbox.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def static_fallback(reason: str) -> int:
    app_text = (ROOT / "app.py").read_text(encoding="utf-8", errors="ignore")
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8", errors="ignore").strip()
    required = [
        "v745_top_app_readiness_context",
        "/admin/top-app-readiness",
        "/api/admin/top-app-readiness",
        "match_intelligence",
        "video_highlights",
        "alerts",
        "payments",
        "sale_ready",
    ]
    missing = [token for token in required if token not in app_text]
    result = {
        "ok": not missing and version.startswith(("V745_", "V746_", "V747_")),
        "version": version,
        "status": "STATIC_OK" if not missing else "STATIC_MISSING",
        "fallback_reason": reason,
        "missing": missing,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["ok"] else 1


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nemesis_v745_ready_", ignore_cleanup_errors=True) as tmp:
        os.environ.setdefault("SECRET_KEY", "v745-ready-check")
        os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
        os.environ.setdefault("SCHEDULER_ENABLED", "false")
        os.environ["DB_PATH"] = str(Path(tmp) / "database.db")
        try:
            import app as app_module  # noqa: WPS433
        except ModuleNotFoundError as exc:
            if exc.name == "flask":
                return static_fallback("flask_not_installed")
            raise

        context = app_module.v745_top_app_readiness_context()
        required = ["data_vault", "production", "match_intelligence", "video_highlights", "alerts", "payments", "sale_ready"]
        result = {"ok": all(key in context for key in required), "version": context.get("version"), "status": context.get("status")}
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
