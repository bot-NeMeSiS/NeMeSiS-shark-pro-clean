#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V823_RENDER_VIDEO_REFERENCE_REAL_CRESTS_PIXEL_EXPERIENCE_FINAL"
CURRENT_VERSION = "V825_SHARK_IDENTITY_FLOATING_BACKGROUND_REFERENCE_FINAL"
PREVIOUS_VERSION_V824 = "V824_RENDER_VIDEO_PIXEL_MATCH_FINAL_APP_EXPERIENCE"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    app = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    checks = {
        "version_txt_current_or_v823": read("VERSION.txt").strip() in {VERSION, PREVIOUS_VERSION_V824, CURRENT_VERSION},
        "app_version_current_or_v823": any(token in app for token in [
            f"APP_VERSION = '{VERSION}'", f'APP_VERSION = "{VERSION}"',
            f"APP_VERSION = '{PREVIOUS_VERSION_V824}'", f'APP_VERSION = "{PREVIOUS_VERSION_V824}"',
            f"APP_VERSION = '{CURRENT_VERSION}'", f'APP_VERSION = "{CURRENT_VERSION}"',
        ]),
        "base_meta_current_or_v823": any(token in base for token in [
            f'name="nemesis-version" content="{VERSION}"',
            f'name="nemesis-version" content="{PREVIOUS_VERSION_V824}"',
            f'name="nemesis-version" content="{CURRENT_VERSION}"',
        ]),
        "base_cache_current_or_v823": f"?v={VERSION}" in base or f"?v={PREVIOUS_VERSION_V824}" in base or f"?v={CURRENT_VERSION}" in base,
        "base_shell_v823": 'data-v823-shell="true"' in base,
        "base_comment_v823": "NEMESIS V823 RENDER VIDEO REFERENCE REAL CRESTS PIXEL EXPERIENCE ACTIVE" in base,
        "css_marker_v823": "V823 RENDER VIDEO REFERENCE REAL CRESTS PIXEL EXPERIENCE START" in css,
        "runtime_keys_v823": all(key in app for key in ["has_v823_shell", "has_v823_css", "has_v822_stability"]),
        "v822_preserved": all(key in app for key in ["v822_runtime_stability_snapshot", "has_v822_shell", "has_v822_css"]),
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
