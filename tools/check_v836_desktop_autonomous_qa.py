#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")


def main() -> int:
    required = {
        "client_rail": "v828-client-rail" in BASE and ".v828-client-rail" in CSS,
        "admin_rail": "v808-admin-rail" in BASE and ".v808-admin-rail" in CSS,
        "desktop_hides_bottom_nav": "min-width:1024px" in CSS and "bottom-nav-clean" in CSS and "display:none!important" in CSS,
        "admin_no_client_floating": ".ns-admin" in CSS and ".shark-widget" in CSS,
        "desktop_width_guard": "width:min(100% - 36px,1480px)" in CSS,
        "command_center_style": "v808-admin-dock" in BASE and "command center" in CSS.lower(),
    }
    missing = [name for name, ok in required.items() if not ok]
    print(json.dumps({"ok": not missing, "missing": missing}, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
