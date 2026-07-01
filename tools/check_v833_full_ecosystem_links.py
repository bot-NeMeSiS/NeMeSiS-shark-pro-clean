#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
BASE = TEMPLATES / "base.html"


def main() -> int:
    base = BASE.read_text(encoding="utf-8", errors="replace")
    templates = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in TEMPLATES.glob("*.html"))
    bottom = re.search(r'<nav class="bottom-nav bottom-nav-clean".*?</nav>', base, re.S)
    bottom_html = bottom.group(0) if bottom else ""
    checks = {
        "client_bottom_links": all(h in bottom_html for h in ['href="/app"', 'href="/partidos"', 'href="/live"', 'href="/picks"', 'href="/shark"']),
        "client_core_links": all(h in templates for h in ['href="/profile"', 'href="/telegram"', 'href="/support"', 'href="/favorites"', 'href="/track-record"', 'href="/combis"', 'href="/mercados"']),
        "sports_to_shark_links": 'href="/shark"' in templates and 'href="/picks"' in templates and 'href="/partidos"' in templates,
        "admin_core_links": all(h in templates for h in ['href="/admin/dashboard"', 'href="/admin/data-center"', 'href="/admin/telegram/command-center"', 'href="/admin/users"', 'href="/admin/memberships"', 'href="/admin/payments"']),
        "logout": 'href="/logout"' in templates,
        "no_empty_href": 'href=""' not in templates,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
