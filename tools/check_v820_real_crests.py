#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    app = read("app.py")
    engine = read("engines/crest_engine.py")
    partial = read("templates/partials/team_identity.html")
    css = read("static/app.css")
    checks = {
        "engine_exists": (ROOT / "engines" / "crest_engine.py").exists(),
        "schema_tables": "team_logo_cache" in engine and "league_logo_cache" in engine and "ensure_crest_logo_schema" in engine,
        "no_blocking_downloads": "urlopen" not in engine and "requests." not in engine,
        "safe_url": "safe_logo_url" in engine and "javascript:" in engine,
        "fallback_exists": "fallback_crest_url" in engine and "/team-crest.svg" in engine,
        "resolver_exists": "resolve_team_crest_payload" in engine and "resolve_league_logo_payload" in engine,
        "app_imports_engine": "resolve_team_crest_payload" in app and "ensure_crest_logo_schema" in app,
        "asset_routes": "/asset/team-logo/<team_key>" in app and "/asset/league-logo/<league_key>" in app,
        "templates_use_central_partial": "v820-crest" in partial and "data-real-logo" in partial,
        "image_fallback_not_broken": "crest-image-error" in partial and "this.remove()" in partial,
        "css_real_crest": ".crest.v820-crest.crest-logo" in css,
        "css_fallback_crest": ".crest.v820-crest.crest-fallback" in css,
    }
    sample_logo = __import__("engines.crest_engine", fromlist=["resolve_team_crest_payload"]).resolve_team_crest_payload("Real Madrid", "https://media.api-sports.io/football/teams/541.png")
    sample_fallback = __import__("engines.crest_engine", fromlist=["resolve_team_crest_payload"]).resolve_team_crest_payload("Equipo Test", "")
    checks["sample_real_logo"] = sample_logo.get("has_real_logo") is True and sample_logo.get("crest_mode") == "logo"
    checks["sample_fallback"] = sample_fallback.get("is_fallback") is True and sample_fallback.get("crest_url", "").startswith("/team-crest.svg")
    failed = [k for k, v in checks.items() if not v]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks, "sample_logo": sample_logo, "sample_fallback": sample_fallback}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

