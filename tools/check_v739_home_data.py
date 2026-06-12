#!/usr/bin/env python3
"""Validate V739 sale-ready home data production fix without running Flask."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_VERSION = "V739_SALE_READY_HOME_DATA_PRODUCTION_FIX"


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def main() -> int:
    app = read(ROOT / "app.py")
    home = read(ROOT / "templates" / "home.html")
    css = read(ROOT / "static" / "app.css")
    version_txt = read(ROOT / "VERSION.txt").strip()
    checks = [
        {"name": "version_txt", "ok": version_txt == BASE_VERSION or version_txt.startswith("V740_"), "value": version_txt},
        {"name": "app_version", "ok": f'APP_VERSION = "{version_txt}"' in app or f'APP_VERSION = "{BASE_VERSION}"' in app},
        {"name": "home_live_summary_function", "ok": "def home_live_summary_data" in app},
        {"name": "home_no_static_zero_counts", "ok": '"upcoming": 0' not in app[app.find('def home_light_data'):app.find('@app.route("/")')] if 'def home_light_data' in app else False},
        {"name": "home_queries_matches", "ok": "SELECT COUNT(*) FROM matches" in app},
        {"name": "home_queries_picks", "ok": "SELECT COUNT(*) FROM picks" in app},
        {"name": "home_pending_sync_message", "ok": "PENDIENTE_SINCRONIZACION" in app and "data_message" in home},
        {"name": "home_template_avoids_fake_zero", "ok": "home_has_data" in home and "else '—'" in home},
        {"name": "css_v739_marker", "ok": "V739 Sale Ready Home Data Production Fix" in css},
        {"name": "no_external_api_in_home", "ok": "sportsdb_v1" not in app[app.find('def home_live_summary_data'):app.find('@app.route("/")')]},
    ]
    failures = [c for c in checks if not c["ok"]]
    report = {"ok": not failures, "version": version_txt, "checks_total": len(checks), "failures": failures, "checks": checks}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
