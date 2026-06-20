#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    app = read("app.py")
    css = read("static/app.css")
    crest = read("engines/crest_engine.py")
    checks = {
        "asset_routes_present": all(token in app for token in ["/asset/team-logo/", "/asset/league-logo/", "/team-crest.svg"]),
        "asset_routes_short_timeout": "timeout=0.2" in app,
        "no_network_download_in_crest_engine": all(token not in crest for token in ["urlopen(", "requests.get(", "httpx."]),
        "fallback_svg_present": "fallback_crest_svg" in crest,
        "v824_crest_css_sizes": all(token in css for token in [".v799-scoreboard .crest", ".v812-row .crest", "object-fit:contain"]),
        "no_runtime_write_policy_broken": "apply_team_identities_to_match" in app and "team_logo_cache_count" in app,
    }
    failed = [key for key, ok in checks.items() if not ok]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


