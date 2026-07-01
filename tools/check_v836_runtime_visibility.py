#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V836_AUTONOMOUS_REFERENCE_VISUAL_REVIEW_FINAL_QA"


def main() -> int:
    os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v836_check_runtime.db"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v836-secret")
    os.environ.setdefault("SECRET_KEY", "codex-v836-secret-key")
    os.environ.setdefault("DISABLE_SCHEDULER", "1")
    sys.path.insert(0, str(ROOT))
    import app as nemesis_app  # noqa: WPS433

    response = nemesis_app.app.test_client().get("/api/runtime-version")
    data = response.get_json() or {}
    required = [
        "has_v836_shell",
        "has_v836_css",
        "has_v833_visual_completion",
        "has_v832_visual_workflow",
        "has_v830_bottom_nav_fix",
        "has_v829_mobile_linked_ecosystem",
        "has_v827_design_system",
        "has_v826_full_screen",
        "has_v825_shark_identity",
        "has_v822_stability",
        "has_v821_hotfix",
        "has_v820_crests",
        "has_v819_dedup",
        "has_v818_automation",
    ]
    missing = [key for key in required if not data.get(key)]
    ok = response.status_code == 200 and data.get("app_version") == VERSION and data.get("version_txt") == VERSION and not missing
    print(json.dumps({"ok": ok, "status": response.status_code, "version": data.get("app_version"), "missing": missing}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
