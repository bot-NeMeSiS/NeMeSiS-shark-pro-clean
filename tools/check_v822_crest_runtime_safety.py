#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    app = read("app.py")
    engine = read("engines/crest_engine.py")
    apply_block = app.split("def apply_team_identities_to_match", 1)[1].split("def thesportsdb_key", 1)[0]
    asset_block = app.split('def asset_team_logo', 1)[1].split('def team_identity_diagnostics', 1)[0]
    from engines.crest_engine import safe_get_team_logo, safe_get_league_logo

    start = time.perf_counter()
    team = safe_get_team_logo(None, team_name="Costa de Marfil")
    league = safe_get_league_logo(None, league_name="LaLiga")
    elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
    checks = {
        "asset_routes_light_startup": '"asset_team_logo"' in app and '"asset_league_logo"' in app and 'request.path.startswith("/asset/")' in app,
        "asset_routes_no_migrations": "ensure_crest_logo_schema" not in asset_block and "ensure_logo_tables_once" not in asset_block,
        "asset_routes_no_db_write": "INSERT " not in asset_block and "UPDATE " not in asset_block and "upsert_" not in asset_block,
        "asset_routes_short_timeout": "timeout=0.2" in asset_block,
        "render_cards_no_db_write": "upsert_team_logo_cache" not in apply_block and "upsert_league_logo_cache" not in apply_block,
        "engine_safe_helpers": all(name in engine for name in ["safe_get_team_logo", "safe_get_league_logo", "safe_crest_context", "fallback_crest_svg", "ensure_logo_tables_once"]),
        "engine_no_network_download": all(token not in engine for token in ["urlopen(", "requests.", "httpx."]),
        "team_fallback_valid": team.get("crest_url", "").startswith("/team-crest.svg") and team.get("is_fallback") is True,
        "league_fallback_valid": league.get("crest_url", "").startswith("/team-crest.svg") and league.get("is_fallback") is True,
        "fallback_fast": elapsed_ms < 100,
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "elapsed_ms": elapsed_ms, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

