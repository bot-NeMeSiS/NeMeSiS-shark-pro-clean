#!/usr/bin/env python3
"""V819 client reference shell checks."""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TEMPLATES = {
    "home.html": "home",
    "client_login.html": "client_login",
    "client_app_center.html": "client_app_center",
    "calendar.html": "calendar",
    "live.html": "live",
    "picks.html": "picks",
    "match_detail.html": "match_detail",
    "shark.html": "shark",
    "profile.html": "profile",
    "telegram.html": "telegram",
}


def main() -> int:
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
    template_checks = {}
    for filename, marker in REQUIRED_TEMPLATES.items():
        text = (ROOT / "templates" / filename).read_text(encoding="utf-8", errors="replace")
        template_checks[filename] = f'data-v819-template="{marker}"' in text or "data-v819-template=" in text

    checks = {
        "templates_marked": all(template_checks.values()),
        "v819_screen_class": "v819-certified-screen" in css,
        "client_backdrop_kept": "v815-client-shark-backdrop" in base and "v815-client-shark-backdrop" in css,
        "old_layers_neutralized": ".v811-top-actions" in css and ".v797-session-pills" in css,
        "bottom_nav_single": len(re.findall(r'<nav[^>]+class="[^"]*bottom-nav-clean', base)) == 1,
        "floating_shark_single": base.count("sharkWidget") >= 1 and base.count('class="shark-widget"') == 1,
        "shark_not_duplicated_on_shark_page": 'data-ns-route="/shark"' in css,
        "technical_words_not_in_client_shell": "Traceback" not in base and "sqlite" not in base.lower(),
    }
    failed = [name for name, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "templates": template_checks, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


