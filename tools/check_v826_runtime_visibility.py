#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V826_FULL_REFERENCE_APP_EXPERIENCE_SCREEN_COMPLETION_FINAL"

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

def main() -> int:
    app = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    checks = {
        "version_txt_v826": (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip() == VERSION,
        "app_version_v826": f"APP_VERSION = '{VERSION}'" in app or f'APP_VERSION = "{VERSION}"' in app,
        "base_meta_v826": f'name="nemesis-version" content="{VERSION}"' in base,
        "base_cache_v826": f"?v={VERSION}" in base,
        "base_shell_v826": 'data-v826-shell="true"' in base,
        "base_comment_v826": "NEMESIS V826 FULL REFERENCE APP EXPERIENCE SCREEN COMPLETION ACTIVE" in base,
        "css_marker_v826": "V826 FULL REFERENCE EXPERIENCE START" in css and "V826 FULL REFERENCE EXPERIENCE END" in css,
        "runtime_keys_v826": all(k in app for k in ["has_v826_shell", "has_v826_css", "has_v825_shark_identity", "has_v824_visual", "has_v818_automation"]),
        "v825_preserved": 'data-v825-shell="true"' in base and "V825 SHARK IDENTITY FLOATING BACKGROUND REFERENCE START" in css,
    }
    failed = [k for k,v in checks.items() if not v]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
