#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")

def main() -> int:
    checks = {
        "one_client_topbar_template": base.count('class="top ns-topbar"') == 1,
        "one_bottom_nav_template": base.count('class="bottom-nav bottom-nav-clean"') == 1,
        "one_authenticated_shark_widget": base.count('id="sharkWidget"') == 1 and base.count('id="sharkFab"') == 1,
        "public_floating_once": base.count('v825-public-floating-shark') >= 1,
        "shark_page_hides_floating": '[data-ns-route="/shark"] .shark-widget' in css and '[data-ns-route="/shark"] .v825-public-floating-shark' in css,
        "admin_without_client_floating": '.ns-admin .v825-public-floating-shark' in css and '.ns-admin .shark-widget' in css,
        "client_has_shark_background": 'v825-shark-background' in base and 'shark-dot-watermark' in css,
        "v826_css_present": 'V826 FULL REFERENCE EXPERIENCE START' in css,
        "no_obvious_client_technical_text": all(x not in (ROOT / 'templates' / name).read_text(encoding='utf-8', errors='replace').lower() for name in ['home.html','client_app_center.html','calendar.html','live.html','picks.html','telegram.html','profile.html'] for x in ['traceback_full','database locked','sqlite error']),
    }
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0

if __name__ == '__main__':
    raise SystemExit(main())


