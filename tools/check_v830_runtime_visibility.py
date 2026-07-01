#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V830_MOBILE_BOTTOM_NAV_PIXEL_QA_REFERENCE_FINAL"
CURRENT_VERSION = "V833_REFERENCE_ECOSYSTEM_VISUAL_COMPLETION_FINAL"


def main() -> int:
    os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v830_check_runtime.db"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v830-secret")
    os.environ.setdefault("SECRET_KEY", "codex-v830-secret-key")
    sys.path.insert(0, str(ROOT))
    import app as nemesis_app  # noqa: WPS433

    response = nemesis_app.app.test_client().get("/api/runtime-version")
    data = response.get_json() or {}
    required = [
        "has_v830_shell",
        "has_v830_css",
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
    ok = response.status_code == 200 and data.get("app_version") in {VERSION, CURRENT_VERSION} and data.get("version_txt") in {VERSION, CURRENT_VERSION} and not missing
    print(json.dumps({"ok": ok, "status": response.status_code, "version": data.get("app_version"), "missing": missing}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
