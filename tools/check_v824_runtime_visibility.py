#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V824_RENDER_VIDEO_PIXEL_MATCH_FINAL_APP_EXPERIENCE"
CURRENT_VERSION = "V825_SHARK_IDENTITY_FLOATING_BACKGROUND_REFERENCE_FINAL"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    app = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    checks = {
        "version_txt_current_or_v824": read("VERSION.txt").strip() in {VERSION, CURRENT_VERSION},
        "app_version_current_or_v824": any(token in app for token in [
            f"APP_VERSION = '{VERSION}'", f'APP_VERSION = "{VERSION}"',
            f"APP_VERSION = '{CURRENT_VERSION}'", f'APP_VERSION = "{CURRENT_VERSION}"',
        ]),
        "base_meta_current_or_v824": f'name="nemesis-version" content="{VERSION}"' in base or f'name="nemesis-version" content="{CURRENT_VERSION}"' in base,
        "base_cache_current_or_v824": f"?v={VERSION}" in base or f"?v={CURRENT_VERSION}" in base,
        "base_shell_v824": 'data-v824-shell="true"' in base,
        "base_comment_v824": "NEMESIS V824 RENDER VIDEO PIXEL MATCH FINAL APP EXPERIENCE ACTIVE" in base,
        "css_marker_v824": "V824 RENDER VIDEO PIXEL MATCH FINAL APP EXPERIENCE START" in css,
        "runtime_keys_v824": all(key in app for key in ["has_v824_shell", "has_v824_css", "has_v823_visual", "has_v822_stability"]),
        "v823_preserved": "data-v823-shell" in base and "V823 RENDER VIDEO REFERENCE REAL CRESTS PIXEL EXPERIENCE START" in css,
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
