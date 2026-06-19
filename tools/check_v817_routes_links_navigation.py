from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V817_REFERENCE_PIXEL_POLISH_CLIENT_ADMIN_FINAL"
CURRENT_VERSION = "V818_DAILY_AUTOMATION_OPERATING_SYSTEM_FINAL"
CLIENT_ROUTES = [
    "/", "/cliente-login", "/app", "/calendar", "/partidos", "/live", "/directo",
    "/picks", "/match/<match_id>", "/shark", "/shark-core", "/profile", "/telegram",
    "/favorites", "/track-record", "/support",
]
ADMIN_ROUTES = [
    "/admin/dashboard", "/admin/map", "/admin/control-center",
    "/admin/telegram/command-center", "/admin/telegram/pro-preview",
    "/admin/users", "/admin/memberships", "/admin/matches-sync",
    "/admin/data-center", "/admin/automation-center",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def route_exists(app_py: str, route: str) -> bool:
    escaped = re.escape(route)
    return re.search(rf'@app\.route\(["\']{escaped}["\'](?:,|\))', app_py) is not None


def main() -> None:
    app_py = read(ROOT / "app.py")
    base = read(ROOT / "templates" / "base.html")
    css = read(ROOT / "static" / "app.css")
    templates = "\n".join(read(p) for p in (ROOT / "templates").glob("*.html"))

    route_results = {route: route_exists(app_py, "/match/<match_id>") if "<match_id>" in route else route_exists(app_py, route) for route in CLIENT_ROUTES}
    admin_results = {route: route_exists(app_py, route) for route in ADMIN_ROUTES}
    hrefs = re.findall(r'''href=["']([^"']+)["']''', base + templates)
    malformed = [
        href for href in hrefs
        if "{{" not in href and "}}" not in href and "{%" not in href and "%}" not in href and href.startswith("/") and (" " in href or href.count("?") > 1 or href.startswith("//") or "None" in href or "undefined" in href.lower())
    ]
    checks = {
        "version": read(ROOT / "VERSION.txt").strip() in {VERSION, CURRENT_VERSION},
        "client_routes_exist": all(route_results.values()),
        "admin_routes_exist": all(admin_results.values()),
        "base_links_core": all(link in base for link in ["/app", "/calendar", "/live", "/picks", "/support"]),
        "admin_links_core": all(link in base for link in ["/admin/control-center", "/admin/map"]),
        "no_malformed_hrefs": not malformed,
        "single_shark_widget": base.count('class="shark-widget"') == 1,
        "v817_css_active": VERSION in css and "data-v817-shell" in css,
        "css_cache_busting": f"?v={VERSION}" in base or f"?v={CURRENT_VERSION}" in base,
        "runtime_v817": "has_v817_shell" in app_py and "has_v817_css" in app_py,
    }
    failed = [name for name, ok in checks.items() if not ok]
    print(json.dumps({
        "ok": not failed,
        "version": VERSION,
        "checks": checks,
        "routes": route_results,
        "admin": admin_results,
        "malformed_hrefs": malformed[:20],
        "failed": failed,
    }, ensure_ascii=False, indent=2))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
