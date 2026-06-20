#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "templates" / "base.html"
TEMPLATES = ROOT / "templates"


def main() -> int:
    base = BASE.read_text(encoding="utf-8", errors="replace")
    all_templates = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in TEMPLATES.glob("*.html"))
    bottom = re.search(r'<nav class="bottom-nav bottom-nav-clean".*?</nav>', base, re.S)
    bottom_html = bottom.group(0) if bottom else ""
    checks = {
        "bottom_nav_five_client_links": all(h in bottom_html for h in ['href="/app"', 'href="/partidos"', 'href="/live"', 'href="/picks"', 'href="/shark"']),
        "client_secondary_links": all(h in all_templates for h in ['href="/profile"', 'href="/telegram"', 'href="/support"', 'href="/favorites"', 'href="/track-record"']),
        "sports_links": all(h in all_templates for h in ['href="/partidos"', 'href="/live"', 'href="/picks"', 'href="/shark"']),
        "admin_links": all(h in all_templates for h in ['href="/admin/dashboard"', 'href="/admin/data-center"', 'href="/admin/telegram/command-center"', 'href="/admin/users"', 'href="/admin/memberships"']),
        "logout_present": 'href="/logout"' in all_templates,
        "no_empty_href": 'href=""' not in all_templates,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
