#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V828_REFERENCE_PIXEL_PARITY_FULL_ECOSYSTEM_FINAL"


def fail(message: str) -> int:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False, indent=2))
    return 1


def main() -> int:
    os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v828_check_runtime.db"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v828-secret")
    sys.path.insert(0, str(ROOT))
    import app as nemesis_app  # noqa: WPS433

    client = nemesis_app.app.test_client()
    response = client.get("/api/runtime-version")
    if response.status_code != 200:
        return fail(f"/api/runtime-version devolviÃ³ {response.status_code}")
    data = response.get_json() or {}
    required_true = [
        "has_v828_shell",
        "has_v828_css",
        "has_v827_design_system",
        "has_v826_full_screen",
        "has_v825_shark_identity",
        "has_v824_visual",
        "has_v823_visual",
        "has_v822_stability",
        "has_v821_hotfix",
        "has_v820_crests",
        "has_v819_dedup",
        "has_v818_automation",
    ]
    missing = [key for key in required_true if not data.get(key)]
    if data.get("app_version") != VERSION:
        return fail(f"app_version inesperada: {data.get('app_version')}")
    if data.get("version_txt") != VERSION:
        return fail(f"version_txt inesperada: {data.get('version_txt')}")
    if missing:
        return fail(f"flags runtime ausentes: {', '.join(missing)}")
    print(json.dumps({"ok": True, "version": data.get("app_version"), "checked": required_true}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

