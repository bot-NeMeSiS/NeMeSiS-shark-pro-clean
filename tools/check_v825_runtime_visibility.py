#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V825_SHARK_IDENTITY_FLOATING_BACKGROUND_REFERENCE_FINAL"
CURRENT_VERSION = "V826_FULL_REFERENCE_APP_EXPERIENCE_SCREEN_COMPLETION_FINAL"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    app = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    checks = {
        "version_txt_current_or_v825": read("VERSION.txt").strip() in {VERSION, CURRENT_VERSION},
        "app_version_current_or_v825": any(token in app for token in [
            f"APP_VERSION = '{VERSION}'", f'APP_VERSION = "{VERSION}"',
            f"APP_VERSION = '{CURRENT_VERSION}'", f'APP_VERSION = "{CURRENT_VERSION}"',
        ]),
        "base_meta_current_or_v825": f'name="nemesis-version" content="{VERSION}"' in base or f'name="nemesis-version" content="{CURRENT_VERSION}"' in base,
        "base_cache_current_or_v825": f"?v={VERSION}" in base or f"?v={CURRENT_VERSION}" in base,
        "base_shell_v825": 'data-v825-shell="true"' in base,
        "base_comment_v825": "NEMESIS V825 SHARK IDENTITY FLOATING BACKGROUND REFERENCE ACTIVE" in base,
        "css_marker_v825": "V825 SHARK IDENTITY FLOATING BACKGROUND REFERENCE START" in css,
        "runtime_keys_v825": all(key in app for key in ["has_v825_shell", "has_v825_css", "has_v824_visual", "has_v823_visual", "has_v822_stability"]),
        "v824_preserved": "data-v824-shell" in base and "V824 RENDER VIDEO PIXEL MATCH FINAL APP EXPERIENCE START" in css,
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
