#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def main() -> int:
    target_templates = [
        "base.html", "home.html", "client_app_center.html", "calendar.html", "live.html", "picks.html",
        "match_detail.html", "shark.html", "profile.html", "telegram.html", "support.html", "favorites.html",
        "track_record.html", "combis.html", "betting_markets.html", "highlights.html", "admin_dashboard.html",
        "admin_daily_automation.html", "admin_telegram_command_center.html", "admin_data_center.html",
        "admin_users.html", "admin_memberships.html", "admin_payments.html",
    ]
    hrefs: set[str] = set()
    text = ""
    for name in target_templates:
        path = TEMPLATES / name
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
            text += "\n" + content
            hrefs.update(re.findall(r'href=["\']([^"\']+)["\']', content))
    required = ["/app", "/calendar", "/partidos", "/live", "/picks", "/shark", "/profile", "/telegram", "/support", "/favorites", "/track-record", "/combis", "/mercados", "/highlights", "/logout"]
    missing = [href for href in required if not any(h == href or h.startswith(href + "?") for h in hrefs)]
    bad_literals = [needle for needle in ["{{ title or", "Lorem", "Espa?", "Andaluc?", "mundal"] if needle.lower() in text.lower()]
    ok = not missing and not bad_literals
    print(json.dumps({"ok": ok, "missing_required_links": missing, "bad_literals": bad_literals, "href_count": len(hrefs)}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

