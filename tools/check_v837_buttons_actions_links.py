#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (ROOT / "templates").rglob("*.html"))

LINKS = [
    "/app", "/partidos", "/calendar", "/live", "/picks", "/shark", "/profile", "/telegram", "/support",
    "/favorites", "/track-record", "/combis", "/mercados", "/highlights", "/logout",
    "/admin/dashboard", "/admin/daily-automation", "/admin/automation-os", "/admin/telegram/command-center",
    "/admin/data-center", "/admin/users", "/admin/memberships", "/admin/payments",
]


def has_href(href: str) -> bool:
    return re.search(rf'href=["\']{re.escape(href)}(?:[?"\'])', TEXT) is not None


def main() -> int:
    missing = [href for href in LINKS if not has_href(href)]
    literal = "{{ title or" in TEXT
    dead = 'href="#"' in TEXT or "href='javascript" in TEXT.lower()
    print(json.dumps({"ok": not missing and not literal and not dead, "missing": missing, "literal_jinja": literal, "dead_href": dead}, ensure_ascii=False, indent=2))
    return 0 if not missing and not literal and not dead else 1


if __name__ == "__main__":
    raise SystemExit(main())
