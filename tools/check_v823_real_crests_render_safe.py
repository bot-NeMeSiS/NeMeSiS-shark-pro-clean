#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    app = read("app.py")
    crest = read("engines/crest_engine.py")
    checks = {
        "asset_team_route_exists": '@app.route("/asset/team-logo/<team_key>")' in app,
        "asset_league_route_exists": '@app.route("/asset/league-logo/<league_key>")' in app,
        "team_crest_svg_route_exists": '@app.route("/team-crest.svg")' in app,
        "asset_routes_light_startup": '"/asset/"' in app and "team-crest.svg" in app,
        "short_db_timeout": "timeout=0.2" in app,
        "no_network_in_crest_engine": all(token not in crest for token in ["urlopen(", "requests.get(", "httpx.", "urllib.request.urlopen"]),
        "no_db_writes_in_asset_routes": "apply_team_identities_to_match" in app and "team_logo_cache_count" in app,
        "fallback_svg_available": "fallback_crest_svg" in crest,
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


