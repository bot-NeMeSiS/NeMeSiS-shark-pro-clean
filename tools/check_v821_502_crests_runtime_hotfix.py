#!/usr/bin/env python3
"""V821 production 502/runtime hotfix checks for crest/logo handling."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VERSION = "V821_PRODUCTION_502_CRESTS_RUNTIME_HOTFIX"
CURRENT = "V822_PRODUCTION_STABILITY_RUNTIME_AUTOMATION_CRESTS_FINAL"
ACCEPTED_ACTIVE = {VERSION, CURRENT}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    app = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    engine = read("engines/crest_engine.py")
    from engines.crest_engine import safe_get_league_logo, safe_get_team_logo, safe_crest_context

    team_fallback = safe_get_team_logo(None, team_name="Costa de Marfil")
    league_fallback = safe_get_league_logo(None, league_name="LaLiga")
    context_fallback = safe_crest_context(None, team_name="Equipo Test")
    apply_block = app.split("def apply_team_identities_to_match", 1)[1].split("def thesportsdb_key", 1)[0]

    checks = {
        "version_txt_v821_or_newer": read("VERSION.txt").strip() in ACCEPTED_ACTIVE,
        "app_version_v821_or_newer": any(f"APP_VERSION = '{value}'" in app or f'APP_VERSION = "{value}"' in app for value in ACCEPTED_ACTIVE),
        "runtime_reports_v821": all(key in app for key in ["has_v821_shell", "last_502_hotfix", "crest_engine_loaded", "logo_cache_tables_ok", "logo_routes_ok"]),
        "base_cache_busting_v821_or_newer": any(f"?v={value}" in base for value in ACCEPTED_ACTIVE),
        "base_v821_marker": 'data-v821-shell="true"' in base and "NEMESIS V821 PRODUCTION 502 CRESTS RUNTIME HOTFIX ACTIVE" in base,
        "css_v821_marker": "V821 PRODUCTION 502 CRESTS RUNTIME HOTFIX START" in css,
        "asset_routes_light": '"asset_team_logo"' in app and '"asset_league_logo"' in app and 'request.path.startswith("/asset/")' in app,
        "asset_routes_no_schema_migration": "ensure_crest_logo_schema(conn)" not in app.split('def asset_team_logo', 1)[1].split('def team_identity_diagnostics', 1)[0],
        "render_no_logo_cache_writes": "upsert_team_logo_cache" not in apply_block and "upsert_league_logo_cache" not in apply_block,
        "engine_safe_helpers": all(name in engine for name in ["safe_get_team_logo", "safe_get_league_logo", "safe_crest_context", "fallback_crest_svg", "ensure_logo_tables_once"]),
        "engine_no_network_download": all(token not in engine for token in ["urlopen(", "requests.", "httpx."]),
        "team_fallback_valid": team_fallback.get("crest_url", "").startswith("/team-crest.svg") and team_fallback.get("is_fallback") is True,
        "league_fallback_valid": league_fallback.get("crest_url", "").startswith("/team-crest.svg") and league_fallback.get("is_fallback") is True,
        "context_fallback_valid": context_fallback.get("crest_url", "").startswith("/team-crest.svg"),
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
