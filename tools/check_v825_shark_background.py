#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    base = read("templates/base.html")
    css = read("static/app.css")
    checks = {
        "background_layer_markup": 'class="v825-shark-background"' in base,
        "dot_watermark_markup": "shark-dot-watermark" in base,
        "grid_texture_markup": "shark-grid-texture" in base,
        "glow_orbs_markup": base.count("shark-glow-orb") >= 2,
        "client_only_condition": "current_user.role != 'ADMIN'" in base,
        "pointer_events_none": ".v825-shark-background" in css and "pointer-events:none" in css,
        "local_svg_background": "url('/static/img/shark-logo.svg')" in css,
        "admin_background_sober": ".ns-admin .v825-shark-background" in css,
        "mobile_opacity_guard": "@media(max-width:560px)" in css and "opacity:.07" in css,
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

