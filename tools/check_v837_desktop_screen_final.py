#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")


def main() -> int:
    checks = {
        "desktop_media": "@media(min-width:1024px)" in CSS,
        "client_rail_desktop": "v828-client-rail" in BASE and "display:flex!important" in CSS,
        "admin_command_center": "v808-admin-dock" in BASE and "v808-admin-rail" in BASE,
        "bottom_nav_hidden_desktop": "bottom-nav-clean" in CSS and "display:none!important" in CSS,
        "main_width_control": "width:min(100% - 40px,1480px)" in CSS,
        "admin_cards": ".ns-admin" in CSS and "v837-certified-screen" in CSS,
    }
    missing = [k for k, v in checks.items() if not v]
    print(json.dumps({"ok": not missing, "missing": missing}, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
