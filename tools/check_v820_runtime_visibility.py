#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V820_REAL_CRESTS_REFERENCE_VISUAL_PIXEL_POLISH_FINAL"
CURRENT = "V821_PRODUCTION_502_CRESTS_RUNTIME_HOTFIX"
CURRENT_V822 = "V822_PRODUCTION_STABILITY_RUNTIME_AUTOMATION_CRESTS_FINAL"
CURRENT_V823 = "V823_RENDER_VIDEO_REFERENCE_REAL_CRESTS_PIXEL_EXPERIENCE_FINAL"
CURRENT_V824 = "V824_RENDER_VIDEO_PIXEL_MATCH_FINAL_APP_EXPERIENCE"
CURRENT_V825 = "V826_FULL_REFERENCE_APP_EXPERIENCE_SCREEN_COMPLETION_FINAL"
ACCEPTED_ACTIVE = {VERSION, CURRENT, CURRENT_V822, CURRENT_V823, CURRENT_V824, CURRENT_V825}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    app = read("app.py")
    base = read("templates/base.html")
    css_bytes = (ROOT / "static" / "app.css").read_bytes()
    css = css_bytes.decode("utf-8", errors="replace")
    version_txt = read("VERSION.txt").strip()
    checks = {
        "version_txt_v820_or_newer": version_txt in ACCEPTED_ACTIVE,
        "app_version_v820_or_newer": any(
            f"APP_VERSION = '{value}'" in app or f'APP_VERSION = "{value}"' in app
            for value in ACCEPTED_ACTIVE
        ),
        "runtime_reports_v820": "has_v820_shell" in app and "has_v820_css" in app,
        "runtime_reports_v819": "has_v819_shell" in app and "has_v819_css" in app,
        "runtime_flags": all(key in app for key in ["automation_secret_configured", "api_football_configured", "the_odds_configured", "telegram_configured"]),
        "meta_v820_or_newer": any(f'name="nemesis-version" content="{value}"' in base for value in ACCEPTED_ACTIVE),
        "body_v820": 'data-v820-shell="true"' in base,
        "comment_v820": "NEMESIS V820 REAL CRESTS REFERENCE VISUAL PIXEL POLISH ACTIVE" in base,
        "cache_busting_v820_or_newer": any(f"?v={value}" in base for value in ACCEPTED_ACTIVE),
        "css_v820": "V820 REAL CRESTS REFERENCE VISUAL PIXEL POLISH START" in css and "data-v820-shell" in css,
    }
    failed = [k for k, v in checks.items() if not v]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks, "css_hash": hashlib.sha256(css_bytes).hexdigest()[:16]}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
