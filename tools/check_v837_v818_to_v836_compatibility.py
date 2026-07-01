#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V837_REFERENCE_PHOTO_PERFECTION_REAL_QA_FINAL"


def main() -> int:
    os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v837_compat.db"))
    os.environ.setdefault("SECRET_KEY", "codex-v837-compat-secret")
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v837-secret")
    os.environ.setdefault("DISABLE_SCHEDULER", "1")
    sys.path.insert(0, str(ROOT))
    import app as nemesis_app  # noqa: WPS433

    client = nemesis_app.app.test_client()
    runtime = client.get("/api/runtime-version").get_json() or {}
    required = [
        "has_v818_automation", "has_v819_dedup", "has_v820_crests", "has_v821_hotfix", "has_v822_stability",
        "has_v825_shark_identity", "has_v826_full_screen", "has_v827_design_system", "has_v829_mobile_linked_ecosystem",
        "has_v830_bottom_nav_fix", "has_v832_visual_workflow", "has_v833_visual_completion", "has_v836_autonomous_qa",
        "has_v837_shell", "has_v837_css",
    ]
    missing = [key for key in required if not runtime.get(key)]
    master_forbidden = client.get("/api/automation/master-tick").status_code == 403
    health = client.get("/api/automation/health-check?secret=codex-v837-secret").status_code
    ok = runtime.get("app_version") == VERSION and not missing and master_forbidden and health == 200
    print(json.dumps({"ok": ok, "missing": missing, "master_tick_without_secret_403": master_forbidden, "health_status": health}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
