#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
TEMPLATES = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (ROOT / "templates").rglob("*.html"))

CLIENT_LINKS = [
    "/app",
    "/partidos",
    "/calendar",
    "/live",
    "/picks",
    "/shark",
    "/profile",
    "/telegram",
    "/support",
    "/favorites",
    "/track-record",
    "/combis",
    "/mercados",
    "/highlights",
    "/logout",
]
ADMIN_LINKS = [
    "/admin/control-center",
    "/admin/dashboard",
    "/admin/map",
    "/admin/daily-automation",
    "/admin/automation-os",
    "/admin/telegram/command-center",
    "/admin/data-center",
    "/admin/users",
    "/admin/memberships",
    "/admin/payments",
]


def href_exists(href: str) -> bool:
    pattern = rf'href=["\']{re.escape(href)}(?:[?"\'])'
    return re.search(pattern, TEMPLATES) is not None


def main() -> int:
    missing_client = [href for href in CLIENT_LINKS if not href_exists(href)]
    missing_admin = [href for href in ADMIN_LINKS if not href_exists(href)]
    literal_jinja = "{{ title or" in TEMPLATES
    ok = not missing_client and not missing_admin and not literal_jinja and BASE.count("bottom-nav-clean") >= 1
    print(json.dumps({"ok": ok, "missing_client": missing_client, "missing_admin": missing_admin, "literal_jinja": literal_jinja}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
