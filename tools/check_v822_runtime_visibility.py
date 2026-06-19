#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V822_PRODUCTION_STABILITY_RUNTIME_AUTOMATION_CRESTS_FINAL"
CURRENT_VERSION = "V823_RENDER_VIDEO_REFERENCE_REAL_CRESTS_PIXEL_EXPERIENCE_FINAL"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    app = read("app.py")
    base = read("templates/base.html")
    css_bytes = (ROOT / "static" / "app.css").read_bytes()
    css = css_bytes.decode("utf-8", errors="replace")
    checks = {
        "version_txt_current_or_v822": read("VERSION.txt").strip() in {VERSION, CURRENT_VERSION},
        "app_version_current_or_v822": any(token in app for token in [
            f"APP_VERSION = '{VERSION}'", f'APP_VERSION = "{VERSION}"',
            f"APP_VERSION = '{CURRENT_VERSION}'", f'APP_VERSION = "{CURRENT_VERSION}"',
        ]),
        "base_meta_current_or_v822": any(token in base for token in [
            f'name="nemesis-version" content="{VERSION}"',
            f'name="nemesis-version" content="{CURRENT_VERSION}"',
        ]),
        "base_cache_current_or_v822": f"?v={VERSION}" in base or f"?v={CURRENT_VERSION}" in base,
        "base_shell_v822": 'data-v822-shell="true"' in base,
        "base_comment_v822": "NEMESIS V822 PRODUCTION STABILITY RUNTIME AUTOMATION CRESTS ACTIVE" in base,
        "css_marker_v822": "V822 PRODUCTION STABILITY RUNTIME AUTOMATION CRESTS START" in css,
        "runtime_v822_keys": all(key in app for key in [
            "has_v822_shell", "has_v822_css", "has_v821_hotfix", "has_v820_crests",
            "has_v819_dedup", "has_v818_automation", "runtime_stability",
        ]),
        "runtime_config_keys": all(key in app for key in [
            "automation_secret_configured", "api_football_configured", "the_odds_configured",
            "telegram_configured", "crest_engine_loaded", "logo_cache_tables_ok", "logo_routes_ok",
        ]),
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks, "css_hash": hashlib.sha256(css_bytes).hexdigest()[:16]}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
