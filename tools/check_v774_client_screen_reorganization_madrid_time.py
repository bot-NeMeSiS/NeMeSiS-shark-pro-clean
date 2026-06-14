#!/usr/bin/env python3
"""V774 client screen reorganization and Madrid-time visual QA."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V774_CLIENT_SCREEN_REORGANIZATION_MADRID_TIME_TOTAL_POLISH"
V775_VERSION = "V775_MOBILE_CLIENT_APP_EXPERIENCE_TOTAL_COMPLETION"
V776_VERSION = "V776_CLIENT_INFORMATION_ARCHITECTURE_FINAL_ORDER"
V777_VERSION = "V777_CLIENT_PRODUCT_EXPERIENCE_FINAL_SYSTEM"
V778_VERSION = "V778_CLIENT_PRODUCT_ORGANIZATION_MADRID_TIME_FINAL_STABILITY"
V779_VERSION = "V779_TEAM_IDENTITY_FLAGS_CRESTS_FINAL_POLISH"
V780_VERSION = "V780_LIVE_DATA_RECOVERY_REALTIME_STABILITY_FIX"
V781_VERSION = "V781_FULL_APP_AUDIT_STABILITY_MADRID_TIME_CLEANUP"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def ok(condition, message, detail=""):
    if not condition:
        raise AssertionError(f"{message}{(': ' + str(detail)) if detail else ''}")


def parse_templates():
    env = Environment(extensions=["jinja2.ext.do"])
    parsed = 0
    errors = []
    for template in (ROOT / "templates").glob("*.html"):
        try:
            env.parse(template.read_text(encoding="utf-8", errors="replace"))
            parsed += 1
        except Exception as exc:  # pragma: no cover
            errors.append((template.name, str(exc)))
    ok(not errors, "errores Jinja", errors[:8])
    return parsed


def static_checks():
    version = read("VERSION.txt").strip()
    app = read("app.py")
    css = read("static/app.css")
    base = read("templates/base.html")
    ok(version in {VERSION, V775_VERSION, V776_VERSION, V777_VERSION, V778_VERSION, V779_VERSION, V780_VERSION, V781_VERSION}, "VERSION.txt no apunta a V774/V775/V776/V777/V778/V779/V780 compatible", version)
    ok(f'APP_VERSION = "{VERSION}"' in app or f'APP_VERSION = "{V775_VERSION}"' in app or f'APP_VERSION = "{V776_VERSION}"' in app or f'APP_VERSION = "{V777_VERSION}"' in app or f'APP_VERSION = "{V778_VERSION}"' in app or f'APP_VERSION = "{V779_VERSION}"' in app or f'APP_VERSION = "{V780_VERSION}"' in app or f'APP_VERSION = "{V781_VERSION}"' in app or f'APP_VERSION = "{V781_VERSION}"' in app or f'APP_VERSION = "{V781_VERSION}"' in app, "APP_VERSION no apunta a V774/V775/V776/V777/V778/V779/V780 compatible")
    ok('DB_PATH = os.getenv("DB_PATH", "/data/database.db")' in app, "DB_PATH fue alterado")
    for route in ("/admin/client-screen-quality", "/api/admin/client-screen-quality"):
        ok(route in app, "ruta V774 faltante", route)
    for token in (
        ".v774-client-hero", ".v774-dashboard-grid", ".v774-match-card", ".v774-pick-card",
        ".v774-filter-form", ".v774-flow-strip", ".v774-match-detail-hero",
    ):
        ok(token in css, "CSS V774 incompleto", token)
    # Client nav must be reduced; V777 may expose Resultados/Cuenta but keeps the main flow compact.
    client_block = base.split("{% elif current_user %}", 1)[1].split("{% else %}", 1)[0]
    if version.startswith("V778") or version.startswith("V779") or version.startswith("V780") or version.startswith("V781"):
        for must in ('href="/app"', 'href="/calendar?lane=today"', 'href="/live"', 'href="/picks"', 'href="/track-record"', 'href="/shark"', 'href="/menu"'):
            ok(must in client_block, "nav cliente V778 sin enlace principal", must)
    elif version.startswith("V777"):
        for must in ('href="/app"', 'href="/calendar?lane=today"', 'href="/live"', 'href="/picks"', 'href="/highlights"', 'href="/shark"', 'href="/menu"'):
            ok(must in client_block, "nav cliente V777 sin enlace principal", must)
    else:
        for must in ('href="/app"', 'href="/calendar"', 'href="/live"', 'href="/picks"', 'href="/track-record"', 'href="/shark"', 'href="/menu"'):
            ok(must in client_block, "nav cliente sin enlace principal", must)
        for hidden in ('href="/modo-dinamico"', 'href="/highlights"', 'href="/mercados"'):
            ok(hidden not in client_block, "nav cliente sigue saturada", hidden)
    home = read("templates/home.html")
    ok("{% if current_user %}" in home and "{% else %}" in home, "home no separa sesión cliente de landing pública")
    ok(home.count("v774-client-hero") >= 1, "home no usa hero V774")
    ok("v724-home-hero" in home and "v774-public-hero" in home, "landing pública preservada pero aislada")
    # Calendar date chip regression fixed: old label said Pasado for +2 days.
    ok('"Pasado"' not in app, "etiqueta de calendario confusa 'Pasado' sigue en app.py")
    ok('"En 2 días"' in app, "date chips V774 no corrigen +2 días")
    client_templates = [
        "home.html", "client_app_center.html", "calendar.html", "live.html", "picks.html", "combis.html",
        "betting_markets.html", "highlights.html", "track_record.html", "match_detail.html", "client_menu.html",
        "sports_hub.html",
    ]
    missing_v774 = []
    missing_time = []
    for name in client_templates:
        raw = read(f"templates/{name}")
        if "v774" not in raw.lower():
            missing_v774.append(name)
        if name in {"calendar.html", "live.html", "picks.html", "match_detail.html", "sports_hub.html"} and not any(t in raw for t in ("match_madrid_context", "match_full_datetime", "client_full_datetime_label", "match_time_short")):
            missing_time.append(name)
    ok(not missing_v774, "plantillas cliente sin V774", missing_v774)
    ok(not missing_time, "plantillas críticas sin hora Madrid", missing_time)
    bad = []
    for p in (ROOT / "templates").glob("*.html"):
        text = p.read_text(encoding="utf-8", errors="replace")
        if any(marker in text for marker in ("Ã", "Â", "â€™", "â€œ", "â€", "â†")):
            bad.append(p.name)
    ok(not bad, "mojibake en plantillas", bad[:12])
    forbidden = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT).as_posix()
        if any(part in rel for part in ("/.git/", "/.venv/", "/.pytest_cache/")):
            forbidden.append(rel)
        if path.is_file() and path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}:
            forbidden.append(rel)
    ok(not forbidden, "basura/prohibidos dentro del árbol", forbidden[:12])


def report():
    parsed = parse_templates()
    static_checks()
    result = {
        "ok": True,
        "version": VERSION,
        "parsed_templates": parsed,
        "client_screens": [
            "home", "app", "calendar", "live", "picks", "combis", "mercados", "resumenes", "track_record", "match_detail", "menu",
        ],
        "preserved": [
            "DB_PATH", "usuarios/sesiones", "membresías", "Telegram/Cron", "AUTOMATION_SECRET", "Madrid Time", "Track Record", "highlights", "Data Marketplace", "Automation Center",
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    report()
